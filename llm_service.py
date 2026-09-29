"""
SafeBite AI - Resilient LLM Routing & Failover Service
Primary: Google Gemini Multimodal cascade (gemini-3.7-flash, gemini-3.5-flash, gemini-3.8-flash).
Fallback: Groq High-Throughput Inference (openai/gpt-oss-120b, qwen/qwen3.8-27b, llama-3.3-70b-versatile).
Fast Failover: If Gemini quota/429 is encountered, immediately failover to Groq without waiting sequentially through 5 models.
In-Memory Cache: Identical prompt evaluations are cached to eliminate redundant API latency.
"""

import os
import time
import hashlib
from typing import Tuple, Optional, Dict, Any
from dotenv import load_dotenv
from google import genai
import groq

from config import Config

# Load environment variables
load_dotenv()

# In-memory prompt cache: hash(prompt) -> (timestamp, (response, provider))
_LLM_CACHE: Dict[str, Tuple[float, Tuple[str, str]]] = {}
_CACHE_TTL = 3600 # 1 hour

def get_api_key(key_name: str) -> Optional[str]:
    """
    Retrieves API key from Streamlit secrets (for Streamlit Cloud deployment)
    or from local environment variables (.env).
    Strips accidental surrounding quotes and whitespace.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key_name in st.secrets:
            val = str(st.secrets[key_name]).strip().strip('"').strip("'")
            if val:
                return val
    except Exception:
        pass

    val = os.getenv(key_name)
    if val:
        val = str(val).strip().strip('"').strip("'")
        if val:
            return val

    return None

def get_gemini_client() -> Optional[genai.Client]:
    key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
    if key:
        try:
            return genai.Client(api_key=key)
        except Exception as e:
            print(f"[Warning] Failed to initialize Gemini Client: {e}")
    return None

def get_groq_client() -> Optional[groq.Groq]:
    key = get_api_key("GROQ_API_KEY")
    if key:
        try:
            return groq.Groq(api_key=key)
        except Exception as e:
            print(f"[Warning] Failed to initialize Groq Client: {e}")
    return None

def _is_quota_exhausted(err_str: str) -> bool:
    """Detects project-level quota / rate limit errors."""
    lower = err_str.lower()
    return "429" in lower or "resource_exhausted" in lower or "quota exceeded" in lower

def generate_clinical_assessment(prompt: str, image_part: Optional[Any] = None) -> Tuple[str, str]:
    """
    Executes clinical product safety evaluation with rapid failover and caching.
    
    Returns:
        (report_text, provider_info)
    """
    # Check cache for pure text requests
    if image_part is None:
        p_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
        if p_hash in _LLM_CACHE:
            ts, cached_res = _LLM_CACHE[p_hash]
            if time.time() - ts < _CACHE_TTL:
                return cached_res

    gemini_client = get_gemini_client()
    groq_client = get_groq_client()

    # 1. Multimodal image path (Requires Gemini Vision)
    if image_part is not None:
        last_vision_err = None
        if gemini_client:
            for model_name in Config.GEMINI_MODELS:
                try:
                    response = gemini_client.models.generate_content(
                        model=model_name,
                        contents=[prompt, image_part]
                    )
                    if response and hasattr(response, "text") and response.text:
                        return response.text, f"Google Gemini Vision ({model_name})"
                except Exception as e:
                    last_vision_err = e
                    err_s = str(e)
                    print(f"[Warning] Gemini Vision ({model_name}) error: {err_s[:120]}")
                    if Config.FAST_FAILOVER_ON_429 and _is_quota_exhausted(err_s):
                        print("[Notice] Gemini project quota reached. Skipping remaining Gemini models.")
                        break

        # Safe fallback message if vision models are busy
        return (
            "VERDICT: UNABLE TO ASSESS\n\n"
            "### ⚠️ Could Not Read Product Image\n\n"
            f"The image analysis engine encountered a temporary service issue ({last_vision_err or 'Vision models busy'}).\n\n"
            "**Recommended Action:**\n"
            "1. Please switch to **'Paste Ingredients List'** and paste the ingredients directly.\n"
            "2. Or ensure your image is a clear, high-contrast, close-up photo of the **Ingredients / Nutrition Facts** panel and try uploading again."
        ), "Vision Failover Guardrail"

    # 2. Standard Text Path
    # Try Gemini Cascade with Fast-Failover
    if gemini_client:
        for model_name in Config.GEMINI_MODELS:
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and hasattr(response, "text") and response.text:
                    res = (response.text, f"Google Gemini ({model_name})")
                    _LLM_CACHE[p_hash] = (time.time(), res)
                    return res
            except Exception as gemini_err:
                err_s = str(gemini_err)
                print(f"[Notice] Gemini ({model_name}) notice: {err_s[:120]}")
                if Config.FAST_FAILOVER_ON_429 and _is_quota_exhausted(err_s):
                    print("[Notice] Gemini project quota reached. Fast-failover to Groq...")
                    break

    # Fallback to Groq API
    if groq_client:
        for groq_m in Config.GROQ_MODELS:
            try:
                resp = groq_client.chat.completions.create(
                    model=groq_m,
                    messages=[
                        {"role": "system", "content": "You are an elite clinical pharmacologist, toxicologist, and allergen-detection specialist."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                if resp.choices and resp.choices[0].message.content:
                    res = (resp.choices[0].message.content, f"Groq Fallback ({groq_m})")
                    _LLM_CACHE[p_hash] = (time.time(), res)
                    return res
            except Exception as groq_err:
                print(f"[Warning] Groq ({groq_m}) failed: {groq_err}. Trying next Groq model...")

    raise RuntimeError(
        "No available LLM provider could fulfill the request. "
        "Please check that GOOGLE_API_KEY and GROQ_API_KEY are configured in .env or Streamlit Secrets."
    )
