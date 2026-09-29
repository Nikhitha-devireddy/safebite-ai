"""
SafeBite AI - Streamlit Cloud Entrypoint Adapter
Ensures seamless deployment when Streamlit Cloud defaults to 'streamlit_app.py'.
Directly executes the primary application at app.py.
"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    app_file = Path(__file__).resolve().parent / "app.py"
    runpy.run_path(str(app_file), run_name="__main__")
