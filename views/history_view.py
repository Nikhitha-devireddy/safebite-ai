"""
SafeBite AI - Audit History View
Displays chronologically audited products, query logs, and clinical verdicts
retrieved from Supabase PostgreSQL or session state.
"""

import streamlit as st
from components.cards import render_verdict_badge
import supabase_client

def render_history_view():
    """Renders the product audit history."""
    st.subheader("📜 Product Safety & Scan Audit History")
    st.markdown("Review previous food safety checks, OCR label scans, and clinical clearance verdicts.")

    # Retrieve history entries
    history_items = []

    if supabase_client.is_supabase_enabled():
        remote_history = supabase_client.get_scan_history(limit=30)
        if remote_history:
            history_items = remote_history

    # Fallback to session history if remote returned nothing
    if not history_items:
        history_items = st.session_state.get("recent_history", [])

    if not history_items:
        st.info("No audit history recorded yet. Scan a food item in **🔍 Live Scanner** to generate your first audit.")
        return

    st.markdown(f"**Found {len(history_items)} recorded audits:**")

    for idx, item in enumerate(history_items):
        prod_name = item.get("product_name") or item.get("name", "Unknown Product")
        brand = item.get("brand", "")
        verdict = item.get("verdict", "UNKNOWN")
        input_mode = item.get("input_mode", "Manual")
        ts = item.get("created_at") or item.get("timestamp", "Recent")
        reasons = item.get("clinical_reasons", [])

        with st.container():
            st.markdown(f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-size:0.75rem; color:#64748B; text-transform:uppercase; font-weight:700;">{brand} · {input_mode}</span>
                        <h4 style="margin:2px 0 4px 0; color:#0F172A;">{prod_name}</h4>
                        <span style="font-size:0.78rem; color:#94A3B8;">Audited: {ts}</span>
                    </div>
                    <div>
                        {render_verdict_badge(verdict)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
