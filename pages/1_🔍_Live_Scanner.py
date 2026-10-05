"""
SafeBite AI - Page 1: Live Scanner & Product Inspection
"""

import sys
from pathlib import Path

# Ensure root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from components.styles import apply_custom_styles
from components.sidebar import render_sidebar
from views.scanner_view import render_scanner_view
from product_sources import ProductSources

st.set_page_config(
    page_title="Live Scanner — SafeBite AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_styles()
render_sidebar()

product_sources = ProductSources()
render_scanner_view(product_sources)
