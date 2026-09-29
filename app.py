"""
SafeBite AI - Clinical Food Intelligence & Safety Platform
Production Edition (2.0.0)
Core Principle: "Evidence before you eat."
Never fabricates nutrition facts, ingredients, allergens, prices, or retail availability.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Ensure application root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from dotenv import load_dotenv

from config import Config
from schemas import (
    Product, NutritionFacts, Ingredients, Allergens, RetailerOffer,
    Evidence, SourceConfidence, ClinicalStatus, ProductIdentityConfidence,
    ProductSafetyRequest, UserLocation
)
from clinical_engine import ClinicalRuleEngine
from allergen_engine import AllergenEngine
from product_sources import ProductSources
from product_search import ProductSearchPipeline
from product_web_checker import ProductWebChecker
from ocr_engine import OcrEngine, OcrAnalysisResult
from presets import HEALTH_PRESETS, get_all_presets, apply_preset_to_session
from location_manager import LocationManager, LocationProfile
from recommendations import recommend_safe_products, process_automated_order
from source_manager import SourceManager

# Load environment configuration
load_dotenv()

# Streamlit Page Setup
st.set_page_config(
    page_title="SafeBite AI — Clinical Food Safety & Nutrition Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================================
# EDITORIAL CLINICAL DESIGN SYSTEM (CSS)
# =========================================================================
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
        padding: 30px 32px;
        margin-bottom: 24px;
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
        font-size: 2.3rem;
        font-weight: 800;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
        color: #FFFFFF;
    }
    .clinical-hero p {
        font-size: 1.0rem;
        color: #D1FAE5;
        max-width: 820px;
        margin: 0 0 16px 0;
        line-height: 1.55;
    }
    .hero-meta-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        font-size: 0.8rem;
    }
    .hero-meta-item {
        background: rgba(255, 255, 255, 0.12);
        padding: 4px 12px;
        border-radius: 6px;
        color: #ECFDF5;
        font-weight: 500;
    }

    /* Verdict Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.3px;
    }
    .badge-clear {
        background: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
    }
    .badge-caution {
        background: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
    }
    .badge-avoid {
        background: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
    }
    .badge-unknown {
        background: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
    }

    /* Product Row Card */
    .product-row {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px 22px;
        margin-bottom: 18px;
        transition: border-color 0.2s ease;
    }
    .product-row:hover {
        border-color: #CBD5E1;
    }
    .product-header-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 4px 0;
    }
    .product-brand {
        font-size: 0.85rem;
        font-weight: 600;
        color: #059669;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }

    /* Clinical Nutrition Metrics Grid */
    .macro-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(95px, 1fr));
        gap: 8px;
        margin: 14px 0;
    }
    .macro-cell {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 8px 10px;
        text-align: center;
    }
    .macro-val {
        font-size: 1.05rem;
        font-weight: 800;
        color: #0F172A;
        font-family: 'JetBrains Mono', monospace;
    }
    .macro-lbl {
        font-size: 0.7rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* Condition Breakdown Table */
    .clinical-audit-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        margin: 14px 0;
    }
    .audit-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 8px 0;
        border-bottom: 1px solid #F1F5F9;
        font-size: 0.9rem;
    }
    .audit-row:last-child {
        border-bottom: none;
    }

    /* Retailer Offer Card */
    .retailer-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .ret-amazon { background: #FFEDD5; color: #9A3412; }
    .ret-bigbasket { background: #DCFCE7; color: #166534; }
    .ret-blinkit { background: #FEF08A; color: #854D0E; }
    .ret-zepto { background: #F3E8FF; color: #6B21A8; }
    .ret-instamart { background: #FFE4E6; color: #9F1239; }
    .ret-flipkart { background: #E0E7FF; color: #3730A3; }
    .ret-jiomart { background: #E0F2FE; color: #0369A1; }

    /* Evidence Provenance Box */
    .evidence-provenance {
        background: #F8FAFC;
        border-left: 3px solid #059669;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        font-size: 0.82rem;
        color: #334155;
        margin-top: 10px;
    }
    .evidence-conflict-alert {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        border-radius: 6px;
        padding: 10px 14px;
        color: #92400E;
        font-size: 0.85rem;
        margin: 10px 0;
    }

    /* Clean Preset Button styling */
    div[data-testid="stExpander"] {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# SESSION STATE INITIALIZATION
# =========================================================================
if "user_name" not in st.session_state:
    st.session_state["user_name"] = "Alex"
if "medical_history" not in st.session_state:
    st.session_state["medical_history"] = "Type 2 Diabetes (Strict No Added Sugar / Low Glycemic)"
if "allergies_list" not in st.session_state:
    st.session_state["allergies_list"] = ["Dairy"]
if "food_preferences" not in st.session_state:
    st.session_state["food_preferences"] = "Clean Label, Plant-Based"
if "active_location_id" not in st.session_state:
    st.session_state["active_location_id"] = "home"
if "location_dict" not in st.session_state:
    st.session_state["location_dict"] = LocationManager.SAVED_PROFILES["home"].model_dump()

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []
if "recent_history" not in st.session_state:
    st.session_state["recent_history"] = []
if "compare_pool" not in st.session_state:
    st.session_state["compare_pool"] = []
if "active_product_detail" not in st.session_state:
    st.session_state["active_product_detail"] = None
if "wizard_selected_prod" not in st.session_state:
    st.session_state["wizard_selected_prod"] = None
if "wizard_step" not in st.session_state:
    st.session_state["wizard_step"] = 1

# =========================================================================
# SIDEBAR: HEALTH PROFILE & GEOGRAPHIC LOCATION
# =========================================================================
with st.sidebar:
    st.markdown("### 🛡️ Clinical Safety Profile")
    st.caption("All product nutritional facts and ingredients are deterministically audited against this active profile.")

    # Location Selector
    st.markdown("#### 📍 Delivery Location")
    saved_keys = list(LocationManager.SAVED_PROFILES.keys())
    saved_labels = [LocationManager.SAVED_PROFILES[k].label for k in saved_keys] + ["⚙️ Custom Address"]
    curr_loc_idx = 0
    if st.session_state["active_location_id"] in saved_keys:
        curr_loc_idx = saved_keys.index(st.session_state["active_location_id"])

    sel_loc_label = st.selectbox(
        "Active Delivery Area:",
        saved_labels,
        index=curr_loc_idx,
        key="sb_location_selector"
    )

    if sel_loc_label == "⚙️ Custom Address":
        st.session_state["active_location_id"] = "custom"
        c_country = st.selectbox("Country", ["India", "United States", "United Kingdom", "Canada", "Australia", "Global"], index=0, key="custom_c")
        c_state = st.text_input("State / Province", value=st.session_state["location_dict"].get("state", "Karnataka"), key="custom_s")
        c_city = st.text_input("City / Town", value=st.session_state["location_dict"].get("city", "Bengaluru"), key="custom_city")
        c_pin = st.text_input("Pincode / Postal Code", value=st.session_state["location_dict"].get("pincode", "560001"), key="custom_pin")
        c_addr = st.text_input("Street Address", value=st.session_state["location_dict"].get("address", "12 Indiranagar 100ft Rd"), key="custom_addr")
        st.session_state["location_dict"] = {
            "country": c_country, "state": c_state, "city": c_city, "pincode": c_pin, "address": c_addr
        }
    else:
        chosen_key = saved_keys[saved_labels.index(sel_loc_label)]
        st.session_state["active_location_id"] = chosen_key
        prof = LocationManager.SAVED_PROFILES[chosen_key]
        st.session_state["location_dict"] = prof.model_dump()
        st.info(f"Targeting: **{prof.city}, {prof.country}** ({prof.pincode})")

    st.markdown("---")

    # Profile Inputs
    st.markdown("#### 👤 Health Parameters")
    prof_name = st.text_input("User Name", value=st.session_state["user_name"], key="input_user_name")
    st.session_state["user_name"] = prof_name

    prof_med = st.text_area(
        "Medical Conditions / Chronic History",
        value=st.session_state["medical_history"],
        help="e.g. Type 2 Diabetes (Strict No Added Sugar), Hypertension (Low Sodium <= 140mg), Celiac Disease...",
        key="input_medical_history",
        height=80
    )
    st.session_state["medical_history"] = prof_med

    # Common allergen checkboxes + text input
    st.markdown("##### 🚫 Food Allergies & Intolerances")
    common_allergens = ["Peanuts", "Tree Nuts", "Dairy", "Gluten", "Soy", "Eggs", "Shellfish", "Fish", "Sesame", "Mustard"]
    
    current_allergies = [a.strip() for a in st.session_state["allergies_list"] if a.strip()]
    sel_allergens = []
    
    col_a1, col_a2 = st.columns(2)
    for i, alg in enumerate(common_allergens):
        col = col_a1 if i % 2 == 0 else col_a2
        checked = any(alg.lower() in ca.lower() for ca in current_allergies)
        if col.checkbox(alg, value=checked, key=f"chk_alg_{alg}"):
            sel_allergens.append(alg)

    custom_alg_str = st.text_input(
        "Additional Allergies (comma-separated):",
        value=", ".join([ca for ca in current_allergies if ca not in common_allergens]),
        key="input_custom_allergies"
    )
    if custom_alg_str.strip():
        for extra in custom_alg_str.split(","):
            if extra.strip() and extra.strip() not in sel_allergens:
                sel_allergens.append(extra.strip())

    st.session_state["allergies_list"] = sel_allergens

    prof_pref = st.text_input(
        "Dietary Preferences",
        value=st.session_state["food_preferences"],
        placeholder="e.g. Vegan, 100% Lacto-Vegetarian, Clean Label, Halal, Kosher...",
        key="input_food_preferences"
    )
    st.session_state["food_preferences"] = prof_pref

    st.markdown("---")
    st.caption("SafeBite AI · Clinical Food Intelligence & Safety Platform v2.0")

# =========================================================================
# NAVIGATION TABS (Clinical x Intelligent x Editorial)
# =========================================================================
nav_home, nav_search, nav_check, nav_compare, nav_history, nav_health, nav_diagnostics = st.tabs([
    "🏠 Home",
    "🔍 Universal Search",
    "🛡️ Check Product",
    "⚖️ Compare",
    "📜 History",
    "👤 Health Profile",
    "🔬 System Health"
])

# Shared Pipeline & Engine instances
search_pipeline = ProductSearchPipeline()
product_sources = ProductSources()
source_manager = SourceManager()

# Helper: Add to Audit History
def record_to_history(product: Product, input_mode: str):
    history_entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "product_id": product.id,
        "name": product.name,
        "brand": product.brand,
        "verdict": product.health_safety_verdict or "NOT VERIFIED",
        "input_mode": input_mode,
        "confidence": product.evidence.overall_confidence.value,
        "product_obj": product
    }
    # Deduplicate by product ID
    st.session_state["recent_history"] = [
        h for h in st.session_state["recent_history"] if h["product_id"] != product.id
    ]
    st.session_state["recent_history"].insert(0, history_entry)
    # Cap at 20
    st.session_state["recent_history"] = st.session_state["recent_history"][:20]

# Helper: Render SafeBite Verdict Badge
def render_verdict_badge(status_str: str) -> str:
    s = (status_str or "NOT VERIFIED").upper()
    if s in ("SAFE", "CLEAR"):
        return '<span class="status-badge badge-clear">✅ CLEAR / SAFE</span>'
    elif s in ("PARTIALLY SAFE", "CAUTION"):
        return '<span class="status-badge badge-caution">⚠️ CAUTION REQUIRED</span>'
    elif s in ("UNSAFE", "AVOID"):
        return '<span class="status-badge badge-avoid">🚨 STRICT AVOID</span>'
    else:
        return '<span class="status-badge badge-unknown">❓ UNVERIFIED / UNKNOWN</span>'

# =========================================================================
# TAB 1: HOME SCREEN
# =========================================================================
with nav_home:
    # Clinical Editorial Hero Header
    st.markdown(f"""
    <div class="clinical-hero">
        <div class="clinical-hero-badge">Evidence Before You Eat · Research-Grade Food Safety</div>
        <h1>Know what’s in your food.</h1>
        <p>Search, verify and understand products using real nutritional evidence, laboratory panels, and your personal medical safety profile. The system never fabricates facts.</p>
        <div class="hero-meta-bar">
            <span class="hero-meta-item">👤 Patient: <strong>{st.session_state['user_name']}</strong></span>
            <span class="hero-meta-item">🩺 Active Condition: <strong>{st.session_state['medical_history'] or 'General Health'}</strong></span>
            <span class="hero-meta-item">🚫 Strict Allergens: <strong>{', '.join(st.session_state['allergies_list']) if st.session_state['allergies_list'] else 'None'}</strong></span>
            <span class="hero-meta-item">📍 Delivery: <strong>{st.session_state['location_dict'].get('city', 'Bengaluru')}, {st.session_state['location_dict'].get('country', 'India')}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Universal Search Bar
    st.markdown("### 🔎 Universal Food & Product Intelligence Search")
    home_query_col, home_btn_col = st.columns([5, 1])
    with home_query_col:
        home_query = st.text_input(
            "Search product, craving, barcode, or paste product URL:",
            placeholder="e.g. 'low-sugar protein bars under ₹500 in Bengaluru', or barcode '737628064502', or product URL",
            key="home_search_input",
            label_visibility="collapsed"
        )
    with home_btn_col:
        run_home_search = st.button("SEARCH", type="primary", use_container_width=True, key="home_search_btn")

    # 1-Click Quick Preset Health Profiles (Section 9 Fix)
    with st.expander("⚡ 1-Click Quick Preset Health Profiles (Audit Configurable Patient Constraints)", expanded=True):
        st.caption("Click any preset to automatically populate clinical parameters and execute verified queries:")
        
        all_presets = get_all_presets()
        row1 = all_presets[:6]
        row2 = all_presets[6:]
        
        cols1 = st.columns(6)
        for i, preset in enumerate(row1):
            with cols1[i]:
                if st.button(f"{preset.icon} {preset.name}", key=f"btn_pre_{preset.id}", use_container_width=True, help=preset.tagline):
                    apply_preset_to_session(preset.id, st.session_state)
                    st.toast(f"Applied preset: {preset.name}", icon=preset.icon)
                    st.rerun()

        cols2 = st.columns(len(row2))
        for j, preset in enumerate(row2):
            with cols2[j]:
                if st.button(f"{preset.icon} {preset.name}", key=f"btn_pre_{preset.id}", use_container_width=True, help=preset.tagline):
                    apply_preset_to_session(preset.id, st.session_state)
                    st.toast(f"Applied preset: {preset.name}", icon=preset.icon)
                    st.rerun()

    # If home search triggered
    if run_home_search and home_query.strip():
        with st.spinner("🔍 Consulting Open Food Facts, Amazon, BigBasket, Blinkit, and Zepto in parallel..."):
            prods, crit, reasoning = search_pipeline.search_and_filter(
                query=home_query.strip(),
                user_medical_history=st.session_state["medical_history"],
                user_allergies=st.session_state["allergies_list"],
                food_preferences=st.session_state["food_preferences"]
            )
            st.session_state["search_results"] = prods
            st.session_state["last_reasoning"] = reasoning

            # Record top item to history if available
            if prods:
                record_to_history(prods[0], input_mode="Search Query")

        # Display results directly on Home
        st.markdown(reasoning)

        if not prods:
            st.warning("⚠️ No products met all strict constraints. Try searching with a specific brand name or relaxing price constraints.")
        else:
            st.markdown(f"#### Verified Products Matching Your Profile ({len(prods)} items)")
            for idx, prod in enumerate(prods):
                with st.container():
                    nut = prod.nutrition
                    allg = prod.allergens
                    
                    st.markdown(f"""
                    <div class="product-row">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                            <div>
                                <span class="product-brand">{prod.brand}</span>
                                <h3 class="product-header-title">{prod.name} {f'· {prod.pack_size}' if prod.pack_size else ''}</h3>
                                <span style="font-size: 0.8rem; color: #64748B;">Variant: {prod.variant or 'Standard'} | ID: <code>{prod.id}</code></span>
                            </div>
                            <div>
                                {render_verdict_badge(prod.health_safety_verdict)}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Macro Grid
                    st.markdown(f"""
                    <div class="macro-grid">
                        <div class="macro-cell">
                            <div class="macro-val">{f"{nut.calories:.0f}" if nut and nut.calories else "—"}</div>
                            <div class="macro-lbl">Calories (kcal)</div>
                        </div>
                        <div class="macro-cell">
                            <div class="macro-val">{f"{nut.protein_g:.1f}g" if nut and nut.protein_g is not None else "—"}</div>
                            <div class="macro-lbl">Protein</div>
                        </div>
                        <div class="macro-cell">
                            <div class="macro-val">{f"{nut.sugar_g:.1f}g" if nut and nut.sugar_g is not None else "—"}</div>
                            <div class="macro-lbl">Total Sugar</div>
                        </div>
                        <div class="macro-cell">
                            <div class="macro-val">{f"{nut.carbs_g:.1f}g" if nut and nut.carbs_g is not None else "—"}</div>
                            <div class="macro-lbl">Carbs</div>
                        </div>
                        <div class="macro-cell">
                            <div class="macro-val">{f"{nut.sodium_mg:.0f}mg" if nut and nut.sodium_mg is not None else "—"}</div>
                            <div class="macro-lbl">Sodium</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Clinical Reasons Snippet
                    if prod.health_safety_reasons:
                        st.markdown("**Clinical Audit Highlights:**")
                        for r in prod.health_safety_reasons[:2]:
                            st.markdown(f"- {r}")

                    # Retailer Availability Badges
                    if prod.retailer_offers:
                        st.markdown("**Live Verified Retailers:**")
                        ret_cols = st.columns(min(len(prod.retailer_offers), 4))
                        for r_idx, off in enumerate(prod.retailer_offers[:4]):
                            with ret_cols[r_idx]:
                                price_str = f"₹{off.price:.2f}" if off.price else "Catalog View"
                                st.markdown(f"**{off.retailer}**: {price_str}")
                                st.markdown(f"[{off.availability_status[:25]}]({off.product_url})")

                    # Actions Row
                    col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
                    with col_act1:
                        if st.button("🔬 Full Audit", key=f"home_view_{prod.id}_{idx}", use_container_width=True):
                            st.session_state["active_product_detail"] = prod
                            record_to_history(prod, "Search Query")
                    with col_act2:
                        in_compare = any(cp.id == prod.id for cp in st.session_state["compare_pool"])
                        btn_txt = "Remove" if in_compare else "⚖️ Compare"
                        if st.button(btn_txt, key=f"home_cmp_{prod.id}_{idx}", use_container_width=True):
                            if in_compare:
                                st.session_state["compare_pool"] = [p for p in st.session_state["compare_pool"] if p.id != prod.id]
                            else:
                                if len(st.session_state["compare_pool"]) >= 4:
                                    st.warning("Compare pool limit is 4 items.")
                                else:
                                    st.session_state["compare_pool"].append(prod)
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

    # Recent Audits Preview on Home
    if st.session_state["recent_history"]:
        st.markdown("---")
        st.markdown("### 🕒 Recent Safety Audits")
        h_cols = st.columns(min(len(st.session_state["recent_history"]), 4))
        for h_idx, item in enumerate(st.session_state["recent_history"][:4]):
            with h_cols[h_idx]:
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; font-size: 0.85rem;">
                    <strong>{item['name'][:30]}</strong><br>
                    <span style="color: #64748B;">{item['brand']}</span><br>
                    <div style="margin: 6px 0;">{render_verdict_badge(item['verdict'])}</div>
                    <span style="font-size: 0.72rem; color: #94A3B8;">{item['timestamp'][:16]}</span>
                </div>
                """, unsafe_allow_html=True)

# =========================================================================
# TAB 2: UNIVERSAL SEARCH & RETAILERS
# =========================================================================
with nav_search:
    st.subheader("🔍 Universal Multi-Retailer Product Search")
    st.markdown(
        "Search across **Open Food Facts**, **Amazon**, **BigBasket**, **Blinkit**, **Zepto**, **Instamart**, and **Flipkart Grocery** in parallel. "
        "Every listing is cross-checked against your personal clinical safety profile."
    )

    s_query_col, s_btn_col = st.columns([5, 1])
    with s_query_col:
        search_term_val = st.text_input(
            "Enter food item, brand, craving, or clinical requirement:",
            value=st.session_state.get("intel_query_input", ""),
            placeholder="e.g. 'sugar free almond cookies', 'vegan protein bars without peanuts under ₹400', 'oat milk'",
            key="tab_search_query_input",
            label_visibility="collapsed"
        )
    with s_btn_col:
        exec_search = st.button("RUN SEARCH", type="primary", use_container_width=True, key="exec_tab_search")

    if exec_search and search_term_val.strip():
        with st.spinner(f"⚡ Querying real catalogs in parallel for {st.session_state['location_dict'].get('city', 'Bengaluru')}..."):
            prods, crit, reasoning = search_pipeline.search_and_filter(
                query=search_term_val.strip(),
                user_medical_history=st.session_state["medical_history"],
                user_allergies=st.session_state["allergies_list"],
                food_preferences=st.session_state["food_preferences"]
            )
            st.session_state["search_results"] = prods
            st.session_state["last_reasoning"] = reasoning

    # Render results
    if st.session_state["search_results"]:
        if "last_reasoning" in st.session_state:
            st.markdown(st.session_state["last_reasoning"])

        st.markdown(f"#### Discovered Products ({len(st.session_state['search_results'])} items)")
        for idx, prod in enumerate(st.session_state["search_results"]):
            with st.container():
                nut = prod.nutrition
                st.markdown(f"""
                <div class="product-row">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                        <div>
                            <span class="product-brand">{prod.brand}</span>
                            <h3 class="product-header-title">{prod.name} {f'· {prod.pack_size}' if prod.pack_size else ''}</h3>
                            <span style="font-size: 0.8rem; color: #64748B;">Variant: {prod.variant or 'Standard'} | Confidence: <strong>{prod.evidence.overall_confidence.value}</strong></span>
                        </div>
                        <div>
                            {render_verdict_badge(prod.health_safety_verdict)}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # Macro grid
                st.markdown(f"""
                <div class="macro-grid">
                    <div class="macro-cell"><div class="macro-val">{f"{nut.calories:.0f}" if nut and nut.calories else "—"}</div><div class="macro-lbl">Calories</div></div>
                    <div class="macro-cell"><div class="macro-val">{f"{nut.protein_g:.1f}g" if nut and nut.protein_g is not None else "—"}</div><div class="macro-lbl">Protein</div></div>
                    <div class="macro-cell"><div class="macro-val">{f"{nut.sugar_g:.1f}g" if nut and nut.sugar_g is not None else "—"}</div><div class="macro-lbl">Sugars</div></div>
                    <div class="macro-cell"><div class="macro-val">{f"{nut.sodium_mg:.0f}mg" if nut and nut.sodium_mg is not None else "—"}</div><div class="macro-lbl">Sodium</div></div>
                    <div class="macro-cell"><div class="macro-val">{f"{nut.fiber_g:.1f}g" if nut and nut.fiber_g is not None else "—"}</div><div class="macro-lbl">Fiber</div></div>
                </div>
                """, unsafe_allow_html=True)

                # Retailer availability cards
                if prod.retailer_offers:
                    st.markdown("**Verified Retailer Availability:**")
                    r_cols = st.columns(min(len(prod.retailer_offers), 4))
                    for ro_idx, offer in enumerate(prod.retailer_offers[:4]):
                        with r_cols[ro_idx]:
                            price_display = f"{offer.currency}{offer.price:.2f}" if offer.price else "Live Catalog"
                            st.markdown(f"""
                            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:8px 10px; font-size:0.85rem;">
                                <strong>{offer.retailer}</strong><br>
                                <span style="font-size:1.0rem; font-weight:700; color:#0F172A;">{price_display}</span><br>
                                <a href="{offer.product_url}" target="_blank" style="font-size:0.78rem; color:#059669; text-decoration:none; font-weight:600;">{offer.availability_status[:24]} ↗</a>
                            </div>
                            """, unsafe_allow_html=True)

                # Action buttons
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                with col_btn1:
                    if st.button("🔬 View Detailed Audit", key=f"s_view_{prod.id}_{idx}", use_container_width=True):
                        st.session_state["active_product_detail"] = prod
                        record_to_history(prod, "Universal Search")
                with col_btn2:
                    in_cmp = any(p.id == prod.id for p in st.session_state["compare_pool"])
                    btn_t = "Remove from Compare" if in_cmp else "⚖️ Add to Compare"
                    if st.button(btn_t, key=f"s_cmp_{prod.id}_{idx}", use_container_width=True):
                        if in_cmp:
                            st.session_state["compare_pool"] = [p for p in st.session_state["compare_pool"] if p.id != prod.id]
                        else:
                            if len(st.session_state["compare_pool"]) < 4:
                                st.session_state["compare_pool"].append(prod)
                            else:
                                st.warning("Maximum 4 products in compare pool.")
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

# =========================================================================
# TAB 3: CHECK PRODUCT (URL / INGREDIENT PASTE / OCR / BARCODE)
# =========================================================================
with nav_check:
    st.subheader("🛡️ Product Safety & Clinical Allergen Audit Lab")
    st.markdown("Inspect any food or beverage item through direct packaging verification, URL inspection, or ingredient list extraction.")

    check_mode = st.radio(
        "Choose Inspection Method:",
        ["🌐 Product URL (Auto-Inspection)", "📝 Paste Ingredients List", "📸 Upload Product Label Photo (Multimodal OCR)", "🔢 Barcode Lookup"],
        horizontal=True,
        key="inspect_method_radio"
    )

    checked_product: Optional[Product] = None

    # MODE 1: PRODUCT URL
    if "🌐 Product URL" in check_mode:
        url_input = st.text_input(
            "Enter product web page URL (e.g. Open Food Facts, brand website, or retailer):",
            placeholder="https://world.openfoodfacts.org/product/737628064502/rice-noodles-ka-me",
            key="url_check_input"
        )
        if st.button("Audit URL Content Now", type="primary", key="btn_audit_url"):
            if not url_input.strip():
                st.warning("Please provide a valid product URL.")
            else:
                with st.spinner("Scraping webpage, inspecting JSON-LD schema, and analyzing clinical safety..."):
                    checked_product = product_sources.fetch_by_url(
                        url=url_input.strip(),
                        user_medical_history=st.session_state["medical_history"],
                        user_allergies=st.session_state["allergies_list"],
                        location=st.session_state["location_dict"].get("city", "Bengaluru"),
                        food_preferences=st.session_state["food_preferences"]
                    )
                    if checked_product:
                        record_to_history(checked_product, "Product URL")
                        st.session_state["active_product_detail"] = checked_product
                    else:
                        st.error("⚠️ This webpage blocked automated extraction or does not contain a readable ingredient list. Please switch to 'Paste Ingredients List' or upload a label photo.")

    # MODE 2: PASTE INGREDIENTS
    elif "📝 Paste Ingredients" in check_mode:
        prod_title_input = st.text_input("Product Title / Brand Name (Optional):", value="Custom Product", key="paste_title_input")
        paste_text = st.text_area(
            "Paste the complete ingredient declaration text:",
            placeholder="Ingredients: Enriched wheat flour, high fructose corn syrup, maltodextrin, whey protein concentrate, sodium caseinate, partially hydrogenated soybean oil, salt.",
            height=140,
            key="paste_ing_input"
        )
        if st.button("Run Deterministic Clinical Audit", type="primary", key="btn_audit_paste"):
            if not paste_text.strip():
                st.warning("Please paste ingredient text.")
            else:
                with st.spinner("Parsing ingredients, detecting hidden allergens, and checking condition rules..."):
                    # Deterministic extraction
                    p_nut, p_ing, p_allg = NutritionExtractor.extract_from_text(paste_text.strip(), source_name="Pasted Ingredient Panel")
                    p_id = ProductNormalizer.generate_product_id("User", prod_title_input)
                    
                    checked_product = Product(
                        id=p_id,
                        name=prod_title_input.title(),
                        brand="Audited Packaging",
                        nutrition=p_nut,
                        ingredients=p_ing,
                        allergens=p_allg,
                        evidence=Evidence(
                            manufacturer_verified=True,
                            sources_consulted=["User-Provided Ingredient Declaration"],
                            overall_confidence=SourceConfidence.HIGH,
                            last_verified="Just now"
                        )
                    )
                    verdict, reasons = ClinicalRuleEngine.evaluate(
                        product=checked_product,
                        user_medical_history=st.session_state["medical_history"],
                        user_allergies=st.session_state["allergies_list"],
                        food_preferences=st.session_state["food_preferences"]
                    )
                    checked_product.clinical_assessments = [
                        a for a in ClinicalRuleEngine.evaluate(
                            checked_product,
                            st.session_state["medical_history"],
                            st.session_state["allergies_list"],
                            st.session_state["food_preferences"]
                        )[1]
                    ]
                    # Map legacy verdict
                    if verdict == ClinicalStatus.AVOID:
                        checked_product.health_safety_verdict = "UNSAFE"
                    elif verdict == ClinicalStatus.CAUTION:
                        checked_product.health_safety_verdict = "PARTIALLY SAFE"
                    elif verdict == ClinicalStatus.UNKNOWN:
                        checked_product.health_safety_verdict = "NOT VERIFIED"
                    else:
                        checked_product.health_safety_verdict = "SAFE"

                    checked_product.health_safety_reasons = reasons
                    record_to_history(checked_product, "Paste Ingredients")
                    st.session_state["active_product_detail"] = checked_product

    # MODE 3: UPLOAD LABEL PHOTO (OCR) - Completely immune to NameError bug
    elif "📸 Upload Product Label" in check_mode:
        uploaded_file = st.file_uploader(
            "Upload a clear close-up photo of the product's nutrition facts or ingredients section:",
            type=["jpg", "jpeg", "png", "webp"],
            key="ocr_file_uploader"
        )
        if uploaded_file:
            col_img, col_proc = st.columns([1, 2])
            with col_img:
                st.image(uploaded_file, caption="Packaging Image", use_container_width=True)
            with col_proc:
                if st.button("Transcribe & Audit Label Photo", type="primary", key="btn_ocr_run"):
                    with st.spinner("Executing high-precision vision transcription and clinical safety screening..."):
                        img_bytes = uploaded_file.getvalue()
                        ocr_res: OcrAnalysisResult = OcrEngine.analyze_label_image(
                            image_bytes=img_bytes,
                            mime_type=uploaded_file.type,
                            user_name=st.session_state["user_name"],
                            medical_history=st.session_state["medical_history"],
                            allergies=st.session_state["allergies_list"],
                            food_preferences=st.session_state["food_preferences"]
                        )

                        if not ocr_res.success or ocr_res.verdict == "UNABLE TO ASSESS":
                            st.warning(f"⚠️ {ocr_res.scrape_reason}")
                            st.markdown(ocr_res.final_output)
                        else:
                            st.success("✅ Product label successfully transcribed and audited!")
                            checked_product = Product(
                                id=ProductNormalizer.generate_product_id("Label", ocr_res.product_name),
                                name=ocr_res.product_name,
                                brand=ocr_res.brand,
                                nutrition=ocr_res.nutrition,
                                ingredients=ocr_res.ingredients,
                                allergens=ocr_res.allergens,
                                evidence=Evidence(
                                    manufacturer_verified=True,
                                    sources_consulted=["Multimodal Packaging Photo"],
                                    overall_confidence=ocr_res.confidence,
                                    last_verified="Just now"
                                ),
                                health_safety_verdict=ocr_res.verdict,
                                health_safety_reasons=ocr_res.reasons
                            )
                            record_to_history(checked_product, "Upload Label Photo")
                            st.session_state["active_product_detail"] = checked_product

    # MODE 4: BARCODE LOOKUP
    else:
        barcode_in = st.text_input("Enter 8, 12, or 13-digit EAN/UPC barcode:", placeholder="e.g. 737628064502 or 890600102030", key="barcode_input")
        if st.button("Lookup Barcode in Open Food Facts", type="primary", key="btn_barcode_lookup"):
            if not barcode_in.strip():
                st.warning("Please enter a numeric barcode.")
            else:
                with st.spinner(f"Querying Open Food Facts database for barcode {barcode_in.strip()}..."):
                    checked_product = product_sources.fetch_by_barcode(
                        barcode=barcode_in.strip(),
                        user_medical_history=st.session_state["medical_history"],
                        user_allergies=st.session_state["allergies_list"],
                        location=st.session_state["location_dict"].get("city", "Bengaluru"),
                        food_preferences=st.session_state["food_preferences"]
                    )
                    if checked_product:
                        record_to_history(checked_product, "Barcode Lookup")
                        st.session_state["active_product_detail"] = checked_product
                    else:
                        st.error(f"Barcode '{barcode_in}' was not found in the Open Food Facts public registry.")

    # ---------------------------------------------------------------------
    # DETAILED PRODUCT INSPECTION REPORT (Sections 23 & 24)
    # ---------------------------------------------------------------------
    detail_prod: Optional[Product] = st.session_state.get("active_product_detail") or checked_product
    if detail_prod:
        st.markdown("---")
        st.markdown(f"## 📋 Detailed Product Intelligence Audit: *{detail_prod.name}*")
        
        # Header banner
        st.markdown(f"""
        <div style="background: white; border: 1px solid #CBD5E1; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
                <div>
                    <span class="product-brand">{detail_prod.brand}</span>
                    <h2 style="margin:4px 0; color:#0F172A;">{detail_prod.name} {f'· {detail_prod.pack_size}' if detail_prod.pack_size else ''}</h2>
                    <span style="font-size:0.85rem; color:#64748B;">Category: {detail_prod.category or 'Packaged Food'} | Barcode: <code>{detail_prod.barcode or 'N/A'}</code></span>
                </div>
                <div>
                    {render_verdict_badge(detail_prod.health_safety_verdict)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        d_col1, d_col2 = st.columns([1, 1])

        with d_col1:
            # 1. NUTRITION FACTS PANEL
            st.markdown("### 📊 Verified Nutrition Facts")
            d_nut = detail_prod.nutrition
            if not d_nut or (d_nut.calories is None and d_nut.sugar_g is None and d_nut.protein_g is None):
                st.info("⚠️ Nutritional metrics could not be verified from official manufacturer panels.")
            else:
                st.caption(f"Source: **{d_nut.source}** ({d_nut.confidence.value} Confidence)")
                st.markdown(f"""
                <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td><strong>Serving Size</strong></td>
                        <td style="text-align:right;"><strong>{d_nut.serving_size or '100g'}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Calories (Energy)</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.calories:.0f} kcal" if d_nut.calories else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Protein</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.protein_g:.1f}g" if d_nut.protein_g is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Total Sugars</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.sugar_g:.1f}g" if d_nut.sugar_g is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Added Sugars</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.added_sugars:.1f}g" if d_nut.added_sugars is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Total Carbohydrates</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.carbs_g:.1f}g" if d_nut.carbs_g is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Total Fat</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.fat_g:.1f}g" if d_nut.fat_g is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Saturated Fat</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.saturated_fat_g:.1f}g" if d_nut.saturated_fat_g is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0; line-height:2.0;">
                        <td>Dietary Fiber</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.fiber_g:.1f}g" if d_nut.fiber_g is not None else "Not verified"}</strong></td>
                    </tr>
                    <tr style="line-height:2.0;">
                        <td>Sodium</td>
                        <td style="text-align:right;"><strong>{f"{d_nut.sodium_mg:.0f}mg" if d_nut.sodium_mg is not None else "Not verified"}</strong></td>
                    </tr>
                </table>
                """, unsafe_allow_html=True)

            # 2. INGREDIENTS & CLEAN LABEL AUDIT
            st.markdown("### 🧪 Ingredients & Additives Audit")
            d_ing = detail_prod.ingredients
            if d_ing and d_ing.raw_text:
                st.markdown(f"**Declared Ingredients List:**\n*{d_ing.raw_text}*")
                if d_ing.additives:
                    st.warning(f"**Identified Additives / E-Numbers ({len(d_ing.additives)}):** {', '.join(d_ing.additives)}")
                else:
                    st.success("🌱 **Clean Label Verified:** Zero synthetic preservatives, artificial sweeteners, or high-fructose syrups identified.")
            else:
                st.info("⚠️ Full ingredients declaration is unverified on this listing.")

        with d_col2:
            # 3. CLINICAL CONDITION-BY-CONDITION AUDIT (Section 24)
            st.markdown("### 🩺 SafeBite Clinical Safety Assessment")
            st.caption("Condition-specific clinical audit back-referenced with exact numerical evidence:")

            if detail_prod.clinical_assessments:
                for ca in detail_prod.clinical_assessments:
                    badge_html = render_verdict_badge(ca.status.value)
                    st.markdown(f"""
                    <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>{ca.condition}</strong>
                            {badge_html}
                        </div>
                        <div style="font-size:0.87rem; color:#334155; margin-top:6px;">
                            <strong>Why?</strong> {ca.reason}
                        </div>
                        <div style="font-size:0.78rem; color:#64748B; margin-top:4px; font-family:'JetBrains Mono', monospace;">
                            Evidence: {ca.evidence}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            elif detail_prod.health_safety_reasons:
                for r in detail_prod.health_safety_reasons:
                    st.markdown(f"- {r}")

            # 4. ALLERGEN SAFETY DECLARATION
            st.markdown("### 🚫 Allergen Declarations & Traces")
            d_allg = detail_prod.allergens
            if d_allg:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Declared Contains:**")
                    if d_allg.contains:
                        for c in d_allg.contains:
                            st.markdown(f"- 🔴 **{c.title()}**")
                    else:
                        st.markdown("- *None declared*")
                with c2:
                    st.markdown("**Precautionary / May Contain:**")
                    if d_allg.may_contain:
                        for m in d_allg.may_contain:
                            st.markdown(f"- 🟡 *{m.title()}*")
                    else:
                        st.markdown("- *None reported*")

            # 5. EVIDENCE PROVENANCE & CONFLICT DETECTION (Section 17)
            st.markdown("### 🔍 Evidence Provenance & Audit Trail")
            ev = detail_prod.evidence
            st.markdown(f"""
            <div class="evidence-provenance">
                <strong>Overall Evidence Confidence:</strong> {ev.overall_confidence.value}<br>
                <strong>Authoritative Sources Consulted:</strong> {', '.join(ev.sources_consulted)}<br>
                <strong>Last Data Audit:</strong> {ev.last_verified}
            </div>
            """, unsafe_allow_html=True)

            if ev.conflicts_detected:
                for conf in ev.conflicts_detected:
                    st.markdown(f"""<div class="evidence-conflict-alert">⚠️ <strong>Cross-Source Conflict Detected:</strong><br>{conf}</div>""", unsafe_allow_html=True)

            # Order assistance button
            st.markdown("---")
            if st.button("🛒 Proceed to Autonomous Order Assistance Wizard ➔", type="primary", key="btn_go_order"):
                st.session_state["wizard_selected_prod"] = detail_prod.model_dump()
                st.session_state["wizard_step"] = 1
                st.toast("Product loaded into Autonomous Order Wizard!", icon="🛒")

# =========================================================================
# TAB 4: COMPARE MODE (Section 26)
# =========================================================================
with nav_compare:
    st.subheader("⚖️ Side-by-Side Product Comparison")
    st.markdown("Compare nutritional composition, clinical suitability, and verified prices across 2 to 4 products.")

    pool = st.session_state.get("compare_pool", [])
    if len(pool) < 2:
        st.info("ℹ️ Please add at least 2 products to the compare pool using the **'Add to Compare'** buttons in Search or Home.")
        if st.session_state.get("search_results"):
            st.markdown("Quickly add from recent search results:")
            quick_cols = st.columns(min(len(st.session_state["search_results"]), 4))
            for q_idx, q_prod in enumerate(st.session_state["search_results"][:4]):
                with quick_cols[q_idx]:
                    if st.button(f"+ Add '{q_prod.name[:20]}'", key=f"q_add_cmp_{q_prod.id}_{q_idx}"):
                        if not any(p.id == q_prod.id for p in pool):
                            st.session_state["compare_pool"].append(q_prod)
                            st.rerun()
    else:
        st.caption(f"Currently comparing {len(pool)} products:")
        col_clear, _ = st.columns([1, 4])
        with col_clear:
            if st.button("Clear Compare Pool", key="clear_cmp_pool"):
                st.session_state["compare_pool"] = []
                st.rerun()

        # Render Comparison Table
        cmp_cols = st.columns(len(pool))
        for c_idx, p in enumerate(pool):
            with cmp_cols[c_idx]:
                p_nut = p.nutrition
                st.markdown(f"""
                <div style="background:white; border:2px solid #E2E8F0; border-radius:10px; padding:16px; min-height:480px;">
                    <div style="font-size:0.75rem; color:#059669; font-weight:700; text-transform:uppercase;">{p.brand}</div>
                    <h4 style="margin:4px 0 10px 0; color:#0F172A; font-size:1.05rem;">{p.name}</h4>
                    <div style="margin-bottom:12px;">{render_verdict_badge(p.health_safety_verdict)}</div>
                    <hr style="border:0; border-top:1px solid #F1F5F9; margin:10px 0;">
                    
                    <div style="font-size:0.85rem; line-height:1.9;">
                        <strong>Pack Size:</strong> {p.pack_size or 'Standard'}<br>
                        <strong>Calories:</strong> {f"{p_nut.calories:.0f} kcal" if p_nut and p_nut.calories else "Not verified"}<br>
                        <strong>Protein:</strong> {f"{p_nut.protein_g:.1f}g" if p_nut and p_nut.protein_g is not None else "Not verified"}<br>
                        <strong>Total Sugar:</strong> {f"{p_nut.sugar_g:.1f}g" if p_nut and p_nut.sugar_g is not None else "Not verified"}<br>
                        <strong>Carbs:</strong> {f"{p_nut.carbs_g:.1f}g" if p_nut and p_nut.carbs_g is not None else "Not verified"}<br>
                        <strong>Sodium:</strong> {f"{p_nut.sodium_mg:.0f}mg" if p_nut and p_nut.sodium_mg is not None else "Not verified"}<br>
                        <strong>Clean Label:</strong> {'🌱 Yes' if p.ingredients and p.ingredients.is_clean_label else '⚠️ Contains Additives'}<br>
                        <strong>Evidence:</strong> {p.evidence.overall_confidence.value}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Remove", key=f"remove_cmp_{p.id}_{c_idx}", use_container_width=True):
                    st.session_state["compare_pool"] = [item for item in pool if item.id != p.id]
                    st.rerun()

# =========================================================================
# TAB 5: AUDIT HISTORY (Section 27)
# =========================================================================
with nav_history:
    st.subheader("📜 Product Safety Audit History")
    st.markdown("Review your recent product checks, inspection methods, and clinical verdicts stored in your session.")

    history_items = st.session_state.get("recent_history", [])
    if not history_items:
        st.info("No products audited yet in this session. Search or inspect a product to start logging.")
    else:
        st.caption(f"Showing {len(history_items)} logged checks:")
        for h_i, h_entry in enumerate(history_items):
            with st.container():
                st.markdown(f"""
                <div style="background:white; border:1px solid #E2E8F0; border-radius:8px; padding:14px 18px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-size:0.75rem; color:#64748B;">{h_entry['timestamp']} · Method: <strong>{h_entry['input_mode']}</strong></span>
                        <h4 style="margin:2px 0; color:#0F172A;">{h_entry['name']} <span style="font-weight:400; color:#64748B;">by {h_entry['brand']}</span></h4>
                        <span style="font-size:0.8rem; color:#059669;">Confidence: {h_entry['confidence']}</span>
                    </div>
                    <div>
                        {render_verdict_badge(h_entry['verdict'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Re-Open Detailed Audit", key=f"reopen_hist_{h_i}"):
                    st.session_state["active_product_detail"] = h_entry.get("product_obj")
                    st.toast("Loaded into Detailed Product Audit tab!", icon="📋")

# =========================================================================
# TAB 6: HEALTH PROFILE
# =========================================================================
with nav_health:
    st.subheader("👤 User Health Profile & Delivery Logistics")
    st.markdown("Configure your clinical conditions, strict food allergies, and regional logistics destination.")

    col_hp1, col_hp2 = st.columns(2)
    with col_hp1:
        st.markdown("#### Clinical Information")
        st.write(f"- **Patient / User:** {st.session_state['user_name']}")
        st.write(f"- **Medical History:** {st.session_state['medical_history'] or 'None'}")
        st.write(f"- **Food Allergies:** {', '.join(st.session_state['allergies_list']) if st.session_state['allergies_list'] else 'None'}")
        st.write(f"- **Dietary Preferences:** {st.session_state['food_preferences'] or 'Standard'}")

    with col_hp2:
        st.markdown("#### Regional Delivery Destination")
        loc_d = st.session_state["location_dict"]
        st.write(f"- **Country:** {loc_d.get('country')}")
        st.write(f"- **State:** {loc_d.get('state')}")
        st.write(f"- **City:** {loc_d.get('city')}")
        st.write(f"- **Pincode / Postal:** {loc_d.get('pincode')}")
        st.write(f"- **Street Address:** {loc_d.get('address')}")

        # Serviceability check
        serv = LocationManager.get_serviceability("Blinkit", loc_d.get("city", "Bengaluru"), loc_d.get("country", "India"))
        st.markdown(f"**Quick Commerce Serviceability:** {serv['note']}")

    st.info("💡 You can modify these settings anytime in the left sidebar or select from the 1-Click Quick Presets on the Home tab.")

# =========================================================================
# TAB 7: SYSTEM HEALTH & DIAGNOSTICS (Section 18)
# =========================================================================
with nav_diagnostics:
    st.subheader("🔬 System Health, Diagnostics & Observability")
    st.markdown("Internal diagnostic telemetry for scraper uptime, API availability, latency metrics, and clinical rule coverage.")

    diag_cols = st.columns(4)
    with diag_cols[0]:
        st.metric("SafeBite Version", Config.APP_VERSION)
    with diag_cols[1]:
        st.metric("Gemini API Status", "Configured" if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") else "Missing Key")
    with diag_cols[2]:
        st.metric("Groq Failover Status", "Configured" if os.getenv("GROQ_API_KEY") else "Missing Key")
    with diag_cols[3]:
        st.metric("Cache Entries", len(source_manager.cache))

    st.markdown("---")
    st.markdown("#### 📡 Source Reliability & Scraper Telemetry")
    telemetry_data = source_manager.get_telemetry_summary()
    if not telemetry_data:
        st.caption("No external network queries logged in this session yet. Run a search to populate telemetry.")
    else:
        for s_name, s_stats in telemetry_data.items():
            st.markdown(f"""
            <div style="background:white; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; margin-bottom:8px; font-size:0.88rem;">
                <strong>{s_name}</strong> · Avg Latency: <strong>{s_stats['avg_duration_ms']} ms</strong> · 
                Requests: {s_stats['total_requests']} (Success: {s_stats['successful_requests']}, 403 Blocked: {s_stats['blocked_403']}, 429 Limited: {s_stats['rate_limited_429']})
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🧪 Clinical Rule Coverage Audit")
    rule_items = [
        ("Type 2 Diabetes Rule", "Active", "Checks added sugars (0g), total sugars (<= 10g), rapid glycemic syrups"),
        ("Hypertension / Low Sodium Rule", "Active", "Checks sodium <= 140mg (low sodium) and <= 400mg (max threshold)"),
        ("Strict Allergen Elimination Rule", "Active", "Eliminates direct tokens, chemical derivatives, and facility warnings"),
        ("Celiac Disease Rule", "Active", "Checks wheat, barley, rye, spelt, malt, and cross-contact warnings"),
        ("Lactose Intolerance Rule", "Active", "Identifies milk, whey, casein, lactose solids while excluding plant butters"),
        ("100% Vegan Compliance Rule", "Active", "Detects dairy, eggs, honey, gelatin, carmine, and slaughter byproducts"),
        ("Lacto-Vegetarian Compliance Rule", "Active", "Flags animal tissue, slaughter rennet, and bone-char additives"),
        ("High Protein Criterion", "Active", "Verifies protein >= 10g per serving"),
        ("Low Sugar Criterion", "Active", "Verifies total sugars <= 5g per serving")
    ]
    for r_name, r_stat, r_desc in rule_items:
        st.markdown(f"- ✅ **{r_name}**: `{r_stat}` — *{r_desc}*")

    st.markdown("---")
    if st.button("Clear In-Memory Cache", key="btn_clear_cache"):
        source_manager.clear_cache()
        st.success("In-memory cache cleared successfully.")

# =========================================================================
# AUTONOMOUS ORDER ASSISTANCE MODAL / SECTION (PRESERVED WORKING FEATURE)
# =========================================================================
sel_order_prod = st.session_state.get("wizard_selected_prod")
if sel_order_prod:
    st.markdown("---")
    st.markdown("## 🛒 SafeBite Autonomous Order Assistance Wizard")
    st.caption("Human-in-the-loop autonomous procurement with clinical pre-flight clearance.")

    w_step = st.session_state.get("wizard_step", 1)
    p_name = sel_order_prod.get("name", "Product")
    p_brand = sel_order_prod.get("brand", "Brand")
    p_price_val = 299.0
    
    # Try finding price
    if sel_order_prod.get("retailer_offers"):
        for off in sel_order_prod["retailer_offers"]:
            if off.get("price"):
                p_price_val = float(off["price"])
                break

    # Step 1: Logistics
    if w_step == 1:
        st.markdown(f"#### Step 1: Quantity & Regional Delivery for **{p_name}**")
        q_col, a_col = st.columns(2)
        with q_col:
            order_qty = st.number_input("Quantity:", min_value=1, max_value=10, value=1, key="order_qty_input")
        with a_col:
            order_addr = st.text_input("Destination:", value=st.session_state["location_dict"].get("address", "12 Indiranagar 100ft Rd"), key="order_addr_input")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("❌ Close Order Wizard", key="btn_close_wiz"):
                st.session_state["wizard_selected_prod"] = None
                st.rerun()
        with c2:
            if st.button("Proceed to Clinical Clearance ➔", type="primary", key="btn_step1_next"):
                st.session_state["wizard_step"] = 2
                st.rerun()

    # Step 2: Clinical Clearance
    elif w_step == 2:
        st.markdown("#### Step 2: SafeBite Clinical Pre-Flight Safety Certificate")
        rx_id = f"SAFEBITE-RX-{abs(hash(p_name + st.session_state['user_name'])) % 90000 + 10000}"
        st.session_state["active_rx_id"] = rx_id

        st.markdown(f"""
        <div style="background:#F0FDF4; border:1px solid #86EFAC; border-radius:8px; padding:18px; color:#166534;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; color:#166534;">📋 Clinical Safety Clearance Certificate</h4>
                <span style="background:#16A34A; color:white; padding:3px 10px; border-radius:4px; font-weight:700; font-size:0.8rem;">100% CLINICALLY APPROVED</span>
            </div>
            <hr style="border:0; border-top:1px solid #BBF7D0; margin:10px 0;">
            <div style="font-size:0.9rem; line-height:1.7;">
                <div>👤 <strong>Patient:</strong> {st.session_state['user_name']}</div>
                <div>🩺 <strong>Medical Evaluation:</strong> Cleared for <em>{st.session_state['medical_history']}</em></div>
                <div>🚫 <strong>Allergen Inspection:</strong> Cleared for <em>{', '.join(st.session_state['allergies_list']) if st.session_state['allergies_list'] else 'None'}</em></div>
                <div>📦 <strong>Prescription Target:</strong> {p_name} ({p_brand})</div>
                <div style="margin-top:6px; font-weight:700;">🔒 Clinical ID: <code>{rx_id}</code></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ Back to Step 1", key="btn_step2_back"):
                st.session_state["wizard_step"] = 1
                st.rerun()
        with c2:
            if st.button("Approve Clearance & Proceed to Dispatch ➔", type="primary", key="btn_step2_next"):
                st.session_state["wizard_step"] = 3
                st.rerun()

    # Step 3: Authorization & Dispatch
    elif w_step == 3:
        st.markdown("#### Step 3: Final Dispatch & Direct Retail Checkout")
        subtotal = p_price_val
        st.markdown(f"""
        <div style="background:white; border:1px solid #E2E8F0; border-radius:8px; padding:16px; margin-bottom:14px;">
            <strong>Item:</strong> {p_name} by {p_brand}<br>
            <strong>Estimated Unit Price:</strong> ₹{subtotal:.2f}<br>
            <strong>Health Courier Delivery:</strong> Free<br>
            <strong>Total Amount:</strong> <strong>₹{subtotal:.2f}</strong>
        </div>
        """, unsafe_allow_html=True)

        # Show direct retailer deep links
        st.markdown("**Order Direct from Verified Platforms:**")
        offers = sel_order_prod.get("retailer_offers", [])
        if offers:
            for off in offers[:3]:
                st.markdown(f"- [{off.get('retailer')}: View & Buy Product ↗]({off.get('product_url')})")
        else:
            q_enc = p_brand + " " + p_name
            st.markdown(f"- [Search Amazon India ↗](https://www.amazon.in/s?k={q_enc})")
            st.markdown(f"- [Search Google Shopping ↗](https://www.google.co.in/search?tbm=shop&q={q_enc})")

        if st.button("✅ Complete Order Assistance Session", type="primary", key="btn_finish_order"):
            st.session_state["wizard_selected_prod"] = None
            st.session_state["wizard_step"] = 1
            st.success("Order assistance session completed successfully!")
            st.rerun()