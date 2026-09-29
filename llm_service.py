import os
from typing import Tuple, Optional
from dotenv import load_dotenv
from google import genai
import groq

# Load environment variables
load_dotenv()

def get_api_key(key_name: str) -> Optional[str]:
    """
    Retrieves API key from Streamlit secrets (for Streamlit Cloud deployment)
    or from local environment variables (.env).
    Strips accidental surrounding quotes and whitespace.
    """
    # 1. Check Streamlit Cloud Secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key_name in st.secrets:
            val = str(st.secrets[key_name]).strip().strip('"').strip("'")
            if val:
                return val
    except Exception:
        pass

    # 2. Check OS environment variables
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

# Prioritized list of Google Gemini models with vision and reasoning capabilities
GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
]

def generate_clinical_assessment(prompt: str, image_part: Optional[any] = None) -> Tuple[str, str]:
    """
    Executes clinical product safety evaluation.
    Primary: Google Gemini model cascade (gemini-3.7-flash, gemini-3.5-flash, gemini-3.8-flash, gemini-flash-latest).
    Fallback (for text): Groq (openai/gpt-oss-120b / qwen/qwen3.8-27b).
    
    Returns:
        (report_text, provider_info)
    """
    gemini_client = get_gemini_client()
    groq_client = get_groq_client()

    # Multimodal image path: Requires Gemini Vision
    if image_part is not None:
        last_vision_err = None
        if gemini_client:
            for model_name in GEMINI_MODELS:
                try:
                    response = gemini_client.models.generate_content(
                        model=model_name,
                        contents=[prompt, image_part]
                    )
                    if response and hasattr(response, "text") and response.text:
                        return response.text, f"Google Gemini Vision ({model_name})"
                except Exception as e:
                    last_vision_err = e
                    print(f"[Warning] Gemini Vision ({model_name}) call failed ({e}). Trying next vision model...")

        # If all Gemini vision models were unavailable, provide clear feedback rather than calling a text-only LLM
        return (
            "VERDICT: UNABLE TO ASSESS\n\n"
            "### ⚠️ Could Not Read Product Image\n\n"
            f"The image analysis engine encountered a temporary service issue ({last_vision_err or 'Vision models busy'}).\n\n"
            "**Recommended Action:**\n"
            "1. Please switch to **'Paste Ingredients List'** and paste the ingredients directly.\n"
            "2. Or ensure your image is a clear, high-contrast, close-up photo of the **Ingredients / Nutrition Facts** panel and try uploading again."
        ), "Vision Failover Guardrail"

    # Standard Text / Scraped URL path
    # Try Primary: Gemini Cascade
    if gemini_client:
        for model_name in GEMINI_MODELS:
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text, f"Google Gemini ({model_name})"
            except Exception as gemini_err:
                print(f"[Notice] Gemini ({model_name}) error ({gemini_err}). Trying next model...")

    # Fallback to Groq
    if groq_client:
        try:
            print("[Notice] Using Groq Fallback API (openai/gpt-oss-120b)...")
            resp = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are an elite clinical pharmacologist, toxicologist, and allergen-detection specialist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return resp.choices[0].message.content, "Groq Fallback (openai/gpt-oss-120b)"
        except Exception as groq_err_1:
            print(f"[Warning] Groq model openai/gpt-oss-120b failed ({groq_err_1}). Trying qwen/qwen3.8-27b...")
            try:
                resp = groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": "You are an elite clinical pharmacologist, toxicologist, and allergen-detection specialist."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                return resp.choices[0].message.content, "Groq Fallback (qwen/qwen3.8-27b)"
            except Exception as groq_err_2:
                raise RuntimeError(f"Both Gemini cascade and Groq fallback failed. Groq: {groq_err_2}")
    
    raise RuntimeError(
        "No available LLM provider could fulfill the request. "
        "Please check that GOOGLE_API_KEY and GROQ_API_KEY are properly configured in .env (for local run) "
        "or in App Settings -> Secrets (for Streamlit Community Cloud)."
    )
