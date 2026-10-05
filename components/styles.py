"""
SafeBite AI - Centralized Editorial Clinical Design System (CSS)
Provides typography, color palette, mobile-responsive layout, and clinical status badges.
Optimized for desktop, tablet (iPad), and mobile viewports (iOS Safari & Android Chrome).
"""

import streamlit as st

def apply_custom_styles():
    """Injects editorial clinical and responsive CSS styles into the Streamlit app."""
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
        -webkit-font-smoothing: antialiased;
    }

    /* -------------------------------------------------------------
       1. RESPONSIVE CONTAINER & VIEWPORT
       ------------------------------------------------------------- */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1200px;
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1.0rem !important;
            padding-bottom: 2.0rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            max-width: 100vw !important;
            overflow-x: hidden !important;
        }
    }

    /* -------------------------------------------------------------
       2. TOP CLINICAL HERO HEADER (RESPONSIVE)
       ------------------------------------------------------------- */
    .clinical-hero {
        background: #064E3B; /* Deep Emerald */
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 18px;
        color: white;
        border: 1px solid #047857;
        box-shadow: 0 4px 14px rgba(6, 78, 59, 0.15);
        box-sizing: border-box;
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
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .clinical-hero h1 {
        font-size: 2.0rem;
        font-weight: 800;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        line-height: 1.25;
    }
    .clinical-hero p {
        font-size: 0.95rem;
        color: #D1FAE5;
        max-width: 820px;
        margin: 0 0 12px 0;
        line-height: 1.5;
    }

    @media (max-width: 768px) {
        .clinical-hero {
            padding: 16px 16px !important;
            border-radius: 10px !important;
            margin-bottom: 14px !important;
        }
        .clinical-hero h1 {
            font-size: 1.45rem !important;
            line-height: 1.2 !important;
        }
        .clinical-hero p {
            font-size: 0.86rem !important;
            line-height: 1.4 !important;
            margin-bottom: 10px !important;
        }
        .clinical-hero-badge {
            font-size: 0.65rem !important;
            padding: 3px 8px !important;
            letter-spacing: 0.8px !important;
        }
    }

    /* -------------------------------------------------------------
       3. MOBILE-OPTIMIZED TAB BAR (HORIZONTAL SWIPE)
       ------------------------------------------------------------- */
    div[data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 16px;
    }

    @media (max-width: 768px) {
        div[data-baseweb="tab-list"] {
            overflow-x: auto !important;
            overflow-y: hidden !important;
            flex-wrap: nowrap !important;
            white-space: nowrap !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: none !important;
            gap: 4px !important;
            padding-bottom: 4px !important;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none !important;
        }
        button[data-baseweb="tab"] {
            flex-shrink: 0 !important;
            padding: 8px 12px !important;
            font-size: 0.84rem !important;
            min-height: 40px !important;
        }
    }

    /* -------------------------------------------------------------
       4. RESPONSIVE COLUMNS & GRID WRAPPING
       ------------------------------------------------------------- */
    @media (max-width: 768px) {
        /* Force multi-column sections on mobile to wrap nicely */
        div[data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 8px !important;
        }
        /* Ensure horizontal container blocks allow wrapping */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
    }

    /* -------------------------------------------------------------
       5. TOUCH-FRIENDLY BUTTONS & INPUTS (iOS ZOOM FIX)
       ------------------------------------------------------------- */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:active {
        transform: scale(0.98) !important;
    }

    @media (max-width: 768px) {
        .stButton > button {
            min-height: 44px !important;
            font-size: 0.88rem !important;
            padding: 8px 14px !important;
            touch-action: manipulation !important;
        }
        /* Prevent auto-zooming in on iOS Safari */
        input[type="text"], input[type="number"], select, textarea {
            font-size: 16px !important;
        }
    }

    /* -------------------------------------------------------------
       6. CLINICAL STATUS BADGES (RESPONSIVE WRAP)
       ------------------------------------------------------------- */
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
        white-space: nowrap;
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
        white-space: nowrap;
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
        white-space: nowrap;
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
        white-space: nowrap;
    }

    @media (max-width: 768px) {
        .badge-clear, .badge-caution, .badge-avoid, .badge-unknown {
            font-size: 0.74rem !important;
            padding: 3px 10px !important;
        }
    }

    /* -------------------------------------------------------------
       7. PRODUCT & EVIDENCE CARDS (RESPONSIVE)
       ------------------------------------------------------------- */
    .card-panel {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        box-sizing: border-box;
        max-width: 100%;
        overflow-wrap: break-word;
    }
    .card-panel h3 {
        margin-top: 0;
        color: #0F172A;
        font-weight: 700;
        font-size: 1.15rem;
    }

    @media (max-width: 768px) {
        .card-panel {
            padding: 14px !important;
            border-radius: 10px !important;
            margin-bottom: 10px !important;
        }
        .card-panel h3 {
            font-size: 1.05rem !important;
        }
    }

    /* -------------------------------------------------------------
       8. METRIC CALLOUT CARDS (RESPONSIVE 2X2 OR AUTO GRID)
       ------------------------------------------------------------- */
    .metric-callout {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 8px;
        text-align: center;
        box-sizing: border-box;
    }
    .metric-callout .val {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.2;
    }
    .metric-callout .lbl {
        font-size: 0.74rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 2px;
    }

    @media (max-width: 768px) {
        .metric-callout {
            padding: 8px 6px !important;
        }
        .metric-callout .val {
            font-size: 1.12rem !important;
        }
        .metric-callout .lbl {
            font-size: 0.68rem !important;
        }
    }

    /* -------------------------------------------------------------
       9. RESPONSIVE TABLES, CODE, IMAGES & CAMERAS
       ------------------------------------------------------------- */
    .table-responsive, [data-testid="stTable"] {
        display: block;
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    [data-testid="stImage"] img, [data-testid="stCameraInput"] video {
        max-width: 100% !important;
        height: auto !important;
        border-radius: 8px !important;
    }

    /* Provenance pill */
    .provenance-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #64748B;
        background: #F1F5F9;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #E2E8F0;
        display: inline-block;
        max-width: 100%;
        overflow-wrap: break-word;
    }

    /* Alert / Conflict Box */
    .alert-conflict {
        background: #FFF7ED;
        border-left: 4px solid #EA580C;
        padding: 12px 14px;
        border-radius: 4px;
        margin-bottom: 12px;
        color: #9A3412;
        font-size: 0.88rem;
        box-sizing: border-box;
    }
</style>
""", unsafe_allow_html=True)
