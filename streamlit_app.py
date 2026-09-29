"""
SafeBite AI - Streamlit Cloud Entrypoint Adapter
Ensures seamless deployment when Streamlit Cloud defaults to 'streamlit_app.py'.
Directly executes the primary application at app.py.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import the primary application
import app
