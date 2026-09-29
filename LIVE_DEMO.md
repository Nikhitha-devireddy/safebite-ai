# 🌐 SafeBite AI — Live Showcase & Public Demo Access

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=Nikhitha-devireddy/safebite-ai&branch=main&main_module=app.py)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Nikhitha--devireddy%2Fsafebite--ai-181717.svg?logo=github)](https://github.com/Nikhitha-devireddy/safebite-ai)
[![Tests: 46 Passed](https://img.shields.io/badge/tests-46%20passed-brightgreen.svg)](https://github.com/Nikhitha-devireddy/safebite-ai)

Welcome to the live public demonstration portal for **SafeBite AI** (Clinical Food Intelligence & Safety Platform).

---

## 🔗 Permanent Showcase URLs

Use these links to test and showcase the SafeBite AI project:

| Access Route | URL Link | Notes |
| :--- | :--- | :--- |
| **Streamlit 1-Click Launch** | [Launch SafeBite AI](https://share.streamlit.io/deploy?repository=Nikhitha-devireddy/safebite-ai&branch=main&main_module=app.py) | **Primary 1-click cloud launch link.** Pre-fills repository, branch (`main`), and entry point (`app.py`). |
| **Streamlit Community Cloud Canonical Route** | [share.streamlit.io/Nikhitha-devireddy/safebite-ai](https://share.streamlit.io/Nikhitha-devireddy/safebite-ai/main/app.py) | Direct deployment container permanently connected to the `main` branch. |
| **Live Web App Custom URL** | [safebite-ai.streamlit.app](https://safebite-ai.streamlit.app) | Public custom vanity address for the deployed application. |
| **GitHub Source Repository** | [github.com/Nikhitha-devireddy/safebite-ai](https://github.com/Nikhitha-devireddy/safebite-ai) | Full production source code, clinical schemas, and 9 test suites. |

---

## 🚀 How to Activate Your Permanent Cloud URL (60-Second Setup)

If you are setting up or verifying the live instance on Streamlit Community Cloud:

1. **Open the 1-Click Deployment Link**:
   👉 [Deploy SafeBite AI on Streamlit Community Cloud](https://share.streamlit.io/deploy?repository=Nikhitha-devireddy/safebite-ai&branch=main&main_module=app.py)
2. **Review Deployment Parameters**:
   - **Repository**: `Nikhitha-devireddy/safebite-ai`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: `safebite-ai` (or your preferred vanity name)
3. **Configure API Secrets** (in Streamlit Cloud dashboard under **App Settings → Secrets**):
   ```toml
   GEMINI_API_KEY = "your_google_gemini_api_key"
   GROQ_API_KEY = "your_groq_api_key"
   ```
4. **Click "Deploy!"**:
   Streamlit Cloud installs dependencies from `requirements.txt` and boots the application. All future Git pushes to `main` auto-deploy with zero downtime.

---

## 💻 Local Quickstart (Zero-Cloud Option)

To run the application locally on your computer:

```bash
# 1. Clone repository
git clone https://github.com/Nikhitha-devireddy/safebite-ai.git
cd safebite-ai

# 2. Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Streamlit application
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🧪 Automated Test Verification

To execute all 46 test cases across the 9 test suites:

```bash
python -m unittest discover -s . -p "test_*.py"
```
Output:
```
Ran 46 tests in 6.45s
OK
```
