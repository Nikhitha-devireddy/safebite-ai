"""
SafeBite AI - Centralized Editorial Clinical Design System (CSS)
Provides typography, color palette, responsive cards, and clinical status badges.
"""

import streamlit as st

def apply_custom_styles():
    """Injects editorial clinical CSS styles into the Streamlit app."""
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
    }

    /* Top Clinical Header */
    .clinical-hero {
        background: #064E3B; /* Deep Emerald */
        border-radius: 12px;
        padding: 26px 28px;
        margin-bottom: 20px;
        color: white;
        border: 1px solid #047857;
        box-shadow: 0 4px 12px rgba(6, 78, 59, 0.15);
    }
    .clinical-hero-badge {
        display: inline-block;
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(110, 231, 183, 0.35);
        color: #A7F3D0;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        padding: 4px 12px;
        border-radius: 9999px;
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    .clinical-hero h1 {
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
        color: #FFFFFF;
    }
    .clinical-hero p {
        font-size: 0.98rem;
        color: #D1FAE5;
        max-width: 820px;
        margin: 0 0 14px 0;
        line-height: 1.55;
    }

    /* Clinical Status Badges */
    .badge-clear {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-caution {
        background-color: #FFFBEB;
        color: #92400E;
        border: 1px solid #FDE68A;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-avoid {
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-unknown {
        background-color: #F8FAFC;
        color: #475569;
        border: 1px solid #E2E8F0;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Product & Evidence Cards */
    .card-panel {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .card-panel h3 {
        margin-top: 0;
        color: #0F172A;
        font-weight: 700;
    }

    /* Alert / Conflict Box */
    .alert-conflict {
        background: #FFF7ED;
        border-left: 4px solid #EA580C;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 14px;
        color: #9A3412;
        font-size: 0.9rem;
    }

    /* Provenance pill */
    .provenance-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #64748B;
        background: #F1F5F9;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #E2E8F0;
    }

    /* Metric Callout Card */
    .metric-callout {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .metric-callout .val {
        font-size: 1.4rem;
        font-weight: 800;
        color: #0F172A;
    }
    .metric-callout .lbl {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)
