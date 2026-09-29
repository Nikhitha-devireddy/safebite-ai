# 🛡️ SafeBite: Clinical Food Safety & Automated Procurement Agent

An agentic AI application built with **LangGraph**, **Google Gemini**, and **Streamlit** that helps users discover safe food products, accommodates chronic medical conditions, cross-references strict allergens (including hidden derivatives), and provides 1-click grocery procurement tailored to the user's geographic location.

---

## 🌟 Key Features

1. **Universal Safe Product Finder & Craving Recommender**
   - Enter **ANY craving or food item** (e.g., Ice Cream, Pasta, Chocolate Chip Cookies, Sourdough Bread).
   - Dynamically audits ingredients against user health profiles:
     - **Diabetes / Metabolic**: Recommends 100% natural, date/monk-fruit sweetened products (zero refined sugars, zero maltodextrin/corn syrup).
     - **Hypertension / Cardiac**: Low-sodium formulations (<140mg/serving, no MSG or sodium nitrates).
     - **Celiac / Gluten Sensitivities**: Certified gluten-free alternatives.
     - **Constipation / GI Health**: High-fiber formulations, whole grains, non-binding.
   - **Location-Aware Retailer Routing**: Targets available delivery channels based on the user's country and city (e.g. Amazon.in, BigBasket, Blinkit, Zepto in India; Amazon Fresh, Instacart in the US; Ocado, Amazon UK in the UK).
   - **Autonomous 1-Click Ordering**: Generates order payloads with calculated pricing, logistics ETA, and direct checkout cart links.

2. **Multi-Input Clinical Safety Inspector**
   - **🌐 Web Scraper**: Audits product URLs with automated bot-protection detection and graceful fallback.
   - **📝 Paste Ingredients**: Deep pharmaceutical and allergen audit of raw ingredient text.
   - **📸 Multimodal Label Photo OCR**: High-precision packaging vision inspection using Google Gemini Multimodal Vision.

3. **High-Resilience LLM Architecture**
   - Primary: **Google Gemini Vision & Reasoning Cascade** (`gemini-3.5-flash`, `gemini-3.8-flash`, `gemini-flash-latest`).
   - Automated Failover: **Groq API** (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`).

---

## 🚀 Quickstart

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Nikhitha-devireddy/safebite-ai.git
cd safebite-ai
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Testing

Run automated integration tests:
```bash
python test_workflow.py
python test_recommendations.py
```
