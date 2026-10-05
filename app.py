"""
SafeBite AI - Clinical Food Intelligence & Safety Platform
Production Edition (2.0.0) - Modular Architecture
Core Principle: "Evidence before you eat."
Never fabricates nutrition facts, ingredients, allergens, prices, or retail availability.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure application root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

# Load environment configuration
load_dotenv()

# Streamlit Page Setup
st.set_page_config(
    page_title="SafeBite AI — Clinical Food Safety & Nutrition Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modular Components & Views
from components.styles import apply_custom_styles
from components.sidebar import render_sidebar
from views.home_view import render_home_view
from views.scanner_view import render_scanner_view
from views.audit_view import render_audit_view
from views.cgm_view import render_cgm_view
from views.swaps_view import render_swaps_view
from views.history_view import render_history_view
from views.profile_view import render_profile_view
from views.diagnostics_view import render_diagnostics_view

from product_sources import ProductSources
from product_search import ProductSearchPipeline

# Apply centralized styling and render sidebar
apply_custom_styles()
render_sidebar()

# Shared pipeline instances
product_sources = ProductSources()
search_pipeline = ProductSearchPipeline()

# Top-level Tabs Navigation (Unified Multi-View Interface)
nav_home, nav_scan, nav_audit, nav_cgm, nav_swaps, nav_history, nav_profile, nav_diag = st.tabs([
    "🏠 Home",
    "🔍 Live Scanner",
    "🩺 Clinical Audit",
    "📈 CGM Simulator",
    "🛒 Safe Swaps",
    "📜 Scan History",
    "👤 Health Profile",
    "🔬 System Health"
])

with nav_home:
    render_home_view(search_pipeline)

with nav_scan:
    render_scanner_view(product_sources)

with nav_audit:
    render_audit_view()

with nav_cgm:
    render_cgm_view()

with nav_swaps:
    render_swaps_view()

with nav_history:
    render_history_view()

with nav_profile:
    render_profile_view()

with nav_diag:
    render_diagnostics_view()