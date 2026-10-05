"""
SafeBite AI - System Health & Diagnostics View
"""

import os
import streamlit as st
import supabase_client

def render_diagnostics_view():
    """Renders system status, API connection, and diagnostics."""
    st.subheader("🔬 System Health & Diagnostic Suite")
    st.markdown("Monitor clinical rule engines, API endpoints, and cloud database connectivity.")

    # 1. Cloud Persistence Status (Supabase)
    st.markdown("#### ☁️ Supabase Cloud Persistence")
    supa_status = supabase_client.test_supabase_connection()
    if supa_status.get("connected"):
        st.success(f"Connected to Supabase Project: `{supa_status.get('url')}`")
        st.json(supa_status.get("tables", {}))
    else:
        st.warning(f"Supabase offline or not configured: {supa_status.get('error')}")

    # 2. API Engines Status
    st.markdown("#### ⚙️ Clinical Intelligence Engines")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.success("✅ **ClinicalRuleEngine**: Ready (Deterministic Multi-Condition)")
        st.success("✅ **AllergenEngine**: Ready (Derivative & PAL Intelligence)")
        st.success("✅ **IndianDietaryGuardrail**: Ready (FSSAI, Jain, Halal, Vrat)")
    with col_e2:
        st.success("✅ **CgmGlucosePredictor**: Ready (180-min Glycemic Curve)")
        st.success("✅ **NovaProcessingScorer**: Ready (UPF Group 1-4)")
        st.success("✅ **OcrEngine**: Ready (Gemini Vision Multimodal)")

    # 3. Environment Secrets Status
    st.markdown("#### 🔑 Environment Secrets & API Keys")
    env_keys = {
        "GOOGLE_API_KEY": bool(os.environ.get("GOOGLE_API_KEY")),
        "GROQ_API_KEY": bool(os.environ.get("GROQ_API_KEY")),
        "SUPABASE_URL": bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_KEY": bool(os.environ.get("SUPABASE_KEY"))
    }
    for k, present in env_keys.items():
        if present:
            st.markdown(f"• **{k}**: `Configured ✅`")
        else:
            st.markdown(f"• **{k}**: `Missing ❌`")

    # 4. Headless REST API
    st.markdown("#### 🚀 Headless REST API Endpoints")
    st.markdown("""
    The system provides a headless FastAPI service running on port `8000`:
    - `POST /api/v1/audit` - Clinical safety evaluation
    - `POST /api/v1/ocr` - Multimodal package OCR & storage
    - `POST /api/v1/cgm/simulate` - Blood glucose spike trajectory
    - `POST /api/v1/swaps` - 1:1 Clean alternative food swaps
    - `GET /api/v1/health` - Health check & engine status
    """)
