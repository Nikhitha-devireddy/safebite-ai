# 🛡️ SafeBite: Clinical Food Safety & Unified Retail Intelligence Engine

An autonomous, agentic AI platform built with **Streamlit**, **LangGraph**, **Google Gemini**, and a deterministic **Product Web & Retail Intelligence Engine**.

SafeBite empowers users to discover safe food products tailored to chronic medical conditions, cross-references strict allergens (including hidden industrial derivatives), audits nutritional claims across live retailer inventories, and executes automated multi-step procurement with human-in-the-loop PIN approval.

---

## 🌟 Architecture & Engine Workflow

```text
User Query (Text / URL / Barcode / Natural Language Filter)
   ↓
Input Router (URL vs Barcode vs Catalog vs Complex Query)
   ↓
Product Discovery
   ├── 🥗 Open Food Facts (Public Collaborative Database)
   ├── 🛒 Amazon India & Global
   ├── 🛍️ BigBasket Supermarket (India)
   ├── ⚡ Blinkit 10-15 Min Quick Commerce
   ├── ⚡ Zepto Flash Delivery
   └── 🌐 Direct Web Scraper / JSON-LD / schema.org
   ↓
Product Identity Matching & Normalization (Variant & Size Integrity)
   ↓
Nutrition + Ingredients + Allergens Extraction (Deterministic & Strict)
   ↓
Source Cross-Validation & Conflict Detection
   ↓
SafeBite Clinical Health & Allergen Reasoner
   ↓
Evidence-backed Result & 1-Click Ordering Assistant
```

---

## 🏛️ Core Principles & Integrity Rules

1. **Zero Hallucination Policy**: Gemini and LLMs are **NEVER** permitted to invent nutrition values, ingredients, prices, or live store availability. All facts are parsed deterministically from verified laboratory panels, packaging declarations, and official catalog records.
2. **Authoritative Sourcing**: Manufacturer data and **Open Food Facts** are prioritized for nutrition, ingredients, and allergens. Retailers are utilized primarily for live discovery, local pricing, pack sizes, stock availability, and direct fulfillment links.
3. **Exact Variant & Formulation Integrity**: Strict variant and pack size matching prevents conflating different product formulations (e.g. Peanut Butter vs Double Cocoa) or pack quantities (e.g. single 50g bar vs 500g box).
4. **Transparent Evidence & Provenance**: Every data field records its `source`, `URL`, `retrieved_at` timestamp, and `confidence` rating (`HIGH`, `MEDIUM`, `LOW`, `UNVERIFIED`).
5. **Visible Cross-Source Conflict Reporting**: Discrepancies between sources (e.g. packaging claiming "Zero Sugar" when lab tests reveal 12g sugars) are flagged visibly in the UI.
6. **Conservative Safety Defaults**: Missing or inaccessible data is strictly classified as **"Not verified"**—never assumed to be safe.
7. **Ethical Web & API Compliance**: Adheres to retailer `robots.txt`, access controls, and rate limits. Never bypasses CAPTCHAs, Cloudflare, or anti-bot protections; instead, gracefully falls back to structured discovery endpoints.

---

## 📦 Modular Architecture & Code Organization

```text
├── schemas.py                 # Pydantic Schemas (Product, NutritionFacts, Ingredients, Allergens, RetailerOffer, Evidence, SourceConfidence)
├── product_search.py          # Natural language filter & search pipeline (Search -> Retrieve -> Verify -> Normalize -> Filter -> Reason -> Cite)
├── product_web_checker.py     # Direct URL auditor (OpenGraph, JSON-LD schema.org/Product, HTML table parsing)
├── product_sources.py         # Unified router aggregating Open Food Facts, Amazon, BigBasket, Blinkit, and Zepto
├── nutrition_extractor.py     # Deterministic parser for calories, sugar, protein, sodium, clean label additives, and allergens
├── product_normalizer.py      # Brand normalizer, pack size parser, flavor variant matcher, and deterministic ID hashing
├── evidence_engine.py         # Cross-validation, discrepancy/conflict detection, and clinical medical/allergen reasoning
├── retailer_sources/          # Independent, modular retailer intelligence adapters
│   ├── __init__.py            # Retailer registry and multi-source dispatcher
│   ├── base.py                # Abstract BaseRetailer with rate-limit respect and safe GET handlers
│   ├── amazon.py              # Amazon India / Global adapter with DuckDuckGo bang single-item redirects
│   ├── bigbasket.py           # BigBasket Supermarket adapter with regional Bengaluru logistics routing
│   ├── blinkit.py             # Blinkit 10-15 min quick-commerce adapter
│   └── zepto.py               # Zepto 10-min instant delivery adapter
├── recommendations.py         # Clinical craving recommender and 5-step order builder
├── agent.py                   # LangGraph workflow for multimodal packaging inspection
├── llm_service.py             # Multi-model Gemini cascade with Groq failover
└── app.py                     # Streamlit web application with 3 interactive action tabs
```

---

## 🖥️ UI Navigation & Features

### Tab 1: 🌐 Search & Verify Product (Web & Retail Intelligence)
- Search any product name, paste any direct product URL, enter an 8-14 digit barcode (e.g. `737628064502`), or ask natural language queries:
  > *"Find low-sugar protein bars without peanuts under ₹500 available in Bengaluru."*
- **Product Overview**: Canonical Title, Brand, Variant, Pack Size, and Barcode.
- **Nutrition Grid**: Calories, Total Sugars, Carbohydrates, Protein, Total Fat, Saturated Fat, Dietary Fiber, and Sodium with clear source provenance.
- **Ingredients & Clean Label**: Full ingredient text with clean label certification (`🌿 Clean Label` vs `⚠️ Additives detected`).
- **Retailer Availability (Amazon | BigBasket | Blinkit | Zepto)**: Real-time price, in-stock indicator, local delivery ETA, and direct store buttons.
- **Evidence Audit**: Checkmarks for Manufacturer, Open Food Facts, and Retailer; overall Confidence (`HIGH`, `MEDIUM`, `LOW`); and discrepancy alerts.

### Tab 2: 🛒 Universal Safe Product Finder & Automated Ordering
- Enter any food craving (Ice Cream, Pasta, Cookies, Sourdough).
- Location-aware local delivery screening.
- **5-Step Autonomous Ordering Wizard with PIN Authorization**:
  1. Logistics & Package Configuration
  2. Clinical Pre-Flight Safety Clearance (Certificate `SAFEBITE-RX-XXXXX`)
  3. Itemized Billing (Subtotal, Free Cold Packaging, 5% Tax, Total)
  4. Human-in-the-Loop PIN / OTP Authorization (Masked PIN + Legal Consent)
  5. Live Autonomous Agent Execution Timeline Log + Tracking ID (`SB-TRK-XXXXXXX`)

### Tab 3: 🔍 Product Safety & Allergen Inspector
- Audit existing products by **Product URL**, **Pasted Ingredients Text**, or **Packaging Label Photo (Gemini Multimodal OCR)**.

---

## 🔑 Configuration & API Keys

### 1. Environment Variables (`.env`)
Create a `.env` file in your workspace root:

```env
# Google Gemini API Key (Required for Multimodal OCR and Clinical Reasoning)
GOOGLE_API_KEY=your_gemini_api_key_here

# Groq API Key (Optional failover backup for text reasoning)
GROQ_API_KEY=your_groq_api_key_here
```

> **Note**: **Open Food Facts**, **Amazon**, **BigBasket**, **Blinkit**, and **Zepto** discovery adapters use public catalog endpoints and require **no API keys**.

### 2. Streamlit Community Cloud Deployment
If deploying on Streamlit Cloud, add the keys under **App Settings -> Secrets**:
```toml
GOOGLE_API_KEY = "your_gemini_api_key_here"
GROQ_API_KEY = "your_groq_api_key_here"
```

---

## 🧪 Automated Test Suite

Run the full automated test suite covering all engine modules, fallback behaviors, and workflows:

```bash
# 1. Product Intelligence Engine Tests (Deterministic nutrition, retailers, conflicts, nlp search)
python test_intelligence_engine.py

# 2. Clinical LangGraph Workflow & Web Scraper Tests
python test_workflow.py

# 3. Product Recommendations & 5-Step Order Processing Tests
python test_recommendations.py
```

All tests execute with 100% pass rates.

---

## 👩‍💻 Author & Lead Contributor

- **Lead Developer & Creator**: **Nikhitha Devireddy**
- **GitHub**: [@Nikhitha-devireddy](https://github.com/Nikhitha-devireddy)
- **Email**: [nikhithalakshmidevireddy@gmail.com](mailto:nikhithalakshmidevireddy@gmail.com)
- **Repository**: [https://github.com/Nikhitha-devireddy/safebite-ai](https://github.com/Nikhitha-devireddy/safebite-ai)

---

## 🔗 Permanent Live Application URL

Access the production deployment permanently on Streamlit Community Cloud:

👉 **[https://share.streamlit.io/Nikhitha-devireddy/safebite-ai/main/app.py](https://share.streamlit.io/Nikhitha-devireddy/safebite-ai/main/app.py)**
*(Or via your custom configured subdomain at `https://safebite-ai.streamlit.app`)*

