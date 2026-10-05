"""
SafeBite AI - Page 5: Personal Health Profile & Medical Presets
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
from views.profile_view import render_profile_view

st.set_page_config(
    page_title="Health Profile — SafeBite AI",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_styles()
render_sidebar()
render_profile_view()
