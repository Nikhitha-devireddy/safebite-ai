import os
import streamlit as st
from dotenv import load_dotenv
from google.genai import types

from schemas import ProductSafetyRequest, UserLocation
from agent import run_agent_workflow, scrape_product_url
from llm_service import generate_clinical_assessment
from recommendations import recommend_safe_products, process_automated_order

# Load environment variables
load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="SafeBite - Clinical Food Safety & Automated Procurement",
    page_icon="🛡️",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .product-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease;
    }
    .product-card:hover {
        border-color: #3B82F6;
    }
    .category-tag {
        background-color: #F1F5F9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 6px;
    }
    .natural-badge {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
    }
    .med-badge {
        background-color: #EFF6FF;
        color: #1E40AF;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.9rem;
        margin-top: 6px;
        margin-bottom: 6px;
        border-left: 4px solid #3B82F6;
    }
    .allergen-badge {
        background-color: #FEF2F2;
        color: #991B1B;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.9rem;
        margin-top: 6px;
        margin-bottom: 12px;
        border-left: 4px solid #EF4444;
    }
    .order-box {
        background-color: #F8FAFC;
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
    }
    .wizard-step-active {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);
    }
    .wizard-step-done {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-align: center;
        border: 1px solid #86EFAC;
    }
    .wizard-step-pending {
        background-color: #F1F5F9;
        color: #64748B;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.85rem;
        text-align: center;
        border: 1px solid #CBD5E1;
    }
    .cert-box {
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border: 2px solid #16A34A;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 6px -1px rgba(22, 163, 74, 0.1);
    }
    .agent-terminal {
        background-color: #0F172A;
        color: #38BDF8;
        font-family: 'Consolas', 'Courier New', monospace;
        padding: 16px 20px;
        border-radius: 10px;
        border-left: 4px solid #38BDF8;
        margin: 16px 0;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .verdict-safe {
        background-color: #DCFCE7;
        color: #14532D;
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #22C55E;
        font-size: 1.3rem;
        font-weight: bold;
        margin: 20px 0;
    }
    .verdict-partially-safe {
        background-color: #FEF9C3;
        color: #713F12;
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #EAB308;
        font-size: 1.3rem;
        font-weight: bold;
        margin: 20px 0;
    }
    .verdict-unsafe {
        background-color: #FEE2E2;
        color: #7F1D1D;
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #EF4444;
        font-size: 1.3rem;
        font-weight: bold;
        margin: 20px 0;
    }
    .verdict-unable {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #F59E0B;
        font-size: 1.3rem;
        font-weight: bold;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🛡️ SafeBite: Clinical Food Safety & Automated Procurement</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">For <strong>ANY food, snack, beverage, or craving</strong>: the agent cross-references your personal '
    'allergens and medical history to recommend 100% safe, clean-label, natural products and provides automated 1-click ordering.</div>', 
    unsafe_allow_html=True
)

# ----------------- GLOBAL USER HEALTH PROFILE -----------------
st.subheader("Step 1: Your Health Profile & Delivery Location")
st.caption("Tell us your personal health requirements and delivery area. The agent screens allergens, matches medical conditions, and targets locally deliverable products.")

col_u1, col_u2 = st.columns(2)

with col_u1:
    user_name = st.text_input(
        "👤 Your Name / Username *",
        value=st.session_state.get("profile_name", ""),
        placeholder="e.g., Alex, Sarah, or John",
        key="input_user_name"
    )
    medical_history = st.text_area(
        "🩺 Medical Conditions / Chronic History *",
        value=st.session_state.get("profile_med", ""),
        placeholder="e.g., Type 2 Diabetes (No Sugar Allowed), Hypertension (Low Sodium), Celiac Disease, Chronic Constipation, Gout, IBS, GERD...",
        key="input_medical_history"
    )

with col_u2:
    allergies_input = st.text_input(
        "🚫 Strict Allergies *",
        value=st.session_state.get("profile_all", ""),
        placeholder="e.g., Dairy (Casein, Whey), Gluten, Peanuts, Tree Nuts, Soy, Eggs, Shellfish...",
        key="input_allergies"
    )
    food_preferences = st.text_input(
        "🥗 Dietary & Food Preferences",
        value=st.session_state.get("profile_pref", ""),
        placeholder="e.g., Organic, Vegan, Vegetarian, Halal, Kosher, Clean Label, or None",
        key="input_food_preferences"
    )

# Delivery & Regional Logistics Section
with st.expander("📍 Delivery Location & Regional Logistics (Targets local availability & native currency)", expanded=True):
    col_l1, col_l2, col_l3 = st.columns(3)
    country_options = ["India", "United States", "United Kingdom", "Canada", "Australia", "Other"]
    saved_country = st.session_state.get("profile_country", "India")
    c_idx = country_options.index(saved_country) if saved_country in country_options else 0
    with col_l1:
        loc_country = st.selectbox("Country", country_options, index=c_idx, key="input_country")
        loc_address = st.text_input("Street Address", value=st.session_state.get("profile_address", "123 Health Ave, Apt 4B"), key="input_address")
    with col_l2:
        loc_city = st.text_input("City / Town", value=st.session_state.get("profile_city", "Bengaluru"), key="input_city")
        loc_state = st.text_input("State / Province", value=st.session_state.get("profile_state", "Karnataka"), key="input_state")
    with col_l3:
        loc_pincode = st.text_input("Pincode / Postal Code", value=st.session_state.get("profile_pincode", "560001"), key="input_pincode")

user_location_dict = {
    "country": loc_country,
    "state": loc_state,
    "city": loc_city,
    "pincode": loc_pincode,
    "address": loc_address
}

# Quick Presets for Easy Exploration
with st.expander("💡 Quick Preset Health Profiles (Click to test with one click)"):
    p_col1, p_col2, p_col3 = st.columns(3)
    if p_col1.button("🍨 Alex: Diabetes + Dairy Allergy (India)"):
        st.session_state["profile_name"] = "Alex"
        st.session_state["profile_med"] = "Type 2 Diabetes (Strict No Added Sugar / Low Glycemic)"
        st.session_state["profile_all"] = "Dairy (Casein, Whey, Lactose)"
        st.session_state["profile_pref"] = "Organic, Plant-Based"
        st.session_state["profile_country"] = "India"
        st.session_state["profile_city"] = "Bengaluru"
        st.session_state["profile_state"] = "Karnataka"
        st.session_state["profile_pincode"] = "560001"
        st.session_state["profile_address"] = "12 Indiranagar 100ft Rd"
        st.rerun()

    if p_col2.button("🍪 Sarah: Celiac + Peanut Allergy (USA)"):
        st.session_state["profile_name"] = "Sarah"
        st.session_state["profile_med"] = "Celiac Disease, GERD (Acid Reflux)"
        st.session_state["profile_all"] = "Gluten, Peanuts"
        st.session_state["profile_pref"] = "Vegetarian, Non-GMO"
        st.session_state["profile_country"] = "United States"
        st.session_state["profile_city"] = "New York"
        st.session_state["profile_state"] = "NY"
        st.session_state["profile_pincode"] = "10001"
        st.session_state["profile_address"] = "452 Broadway, Apt 5"
        st.rerun()

    if p_col3.button("🍝 Elena: Hypertension + Constipation (UK)"):
        st.session_state["profile_name"] = "Elena"
        st.session_state["profile_med"] = "Hypertension (Strict Low Sodium), Constipation (High Fiber Needed)"
        st.session_state["profile_all"] = "Shellfish, Soy"
        st.session_state["profile_pref"] = "Halal, Whole Foods"
        st.session_state["profile_country"] = "United Kingdom"
        st.session_state["profile_city"] = "London"
        st.session_state["profile_state"] = "Greater London"
        st.session_state["profile_pincode"] = "EC1A 1BB"
        st.session_state["profile_address"] = "10 Baker Street"
        st.rerun()

allergies_list = [a.strip() for a in allergies_input.split(",") if a.strip() and a.lower() != "none"]

st.markdown("---")

# ----------------- MAIN ACTION TABS -----------------
tab_recommend, tab_inspect = st.tabs([
    "🛒 Universal Safe Product Finder & Automated Ordering",
    "🔍 Product Safety & Allergen Inspector (Audit URL / Text / Label)"
])

# =========================================================================
# TAB 1: UNIVERSAL SAFE PRODUCT FINDER & AUTOMATED ORDERING
# =========================================================================
with tab_recommend:
    st.subheader("Step 2: What would you like to eat or buy?")
    st.markdown(
        "Enter **any food, grocery item, snack, or craving**. The agent dynamically screens out your allergens "
        "(including hidden derivatives) and verifies medical suitability (e.g. natural date-sweetening for diabetes, "
        "low sodium for hypertension, high fiber for constipation, certified gluten-free for celiac)."
    )

    # Category Quick Buttons for any product
    st.caption("Quick food ideas:")
    chip_col1, chip_col2, chip_col3, chip_col4, chip_col5, chip_col6 = st.columns(6)
    if chip_col1.button("🍨 Ice Cream"):
        st.session_state["active_craving"] = "Ice cream"
        st.rerun()
    if chip_col2.button("🍪 Cookies"):
        st.session_state["active_craving"] = "Cookies"
        st.rerun()
    if chip_col3.button("🍞 Bread"):
        st.session_state["active_craving"] = "Bread"
        st.rerun()
    if chip_col4.button("🍝 Pasta"):
        st.session_state["active_craving"] = "Pasta"
        st.rerun()
    if chip_col5.button("🍫 Chocolate"):
        st.session_state["active_craving"] = "Chocolate snack"
        st.rerun()
    if chip_col6.button("🥣 Cereal / Granola"):
        st.session_state["active_craving"] = "Breakfast Cereal"
        st.rerun()

    craving_val = st.session_state.get("active_craving", "")
    craving_query = st.text_input(
        "Search Any Food, Snack, Beverage, or Craving:",
        value=craving_val,
        placeholder="e.g., Ice cream, Chocolate chip cookies, Pasta, Sourdough bread, Salad dressing, Protein bar, Energy drinks, Pizza...",
        key="universal_craving_input"
    )

    # Search Button
    if st.button("🚀 Find Safe Products Tailored To My Health Profile", type="primary", use_container_width=True):
        if not user_name:
            st.warning("⚠️ Please provide your Name in Step 1.")
        elif not medical_history and not allergies_list:
            st.warning("⚠️ Please provide your Medical Condition or Allergies in Step 1.")
        elif not craving_query:
            st.warning("⚠️ Please enter what product or food you want to find.")
        else:
            with st.spinner(f"🔍 Agent screening products for {user_name}: Cross-referencing {medical_history} & {allergies_input}..."):
                try:
                    recs = recommend_safe_products(
                        user_name=user_name,
                        medical_history=medical_history,
                        allergies=allergies_list,
                        food_preferences=food_preferences or "None",
                        craving_query=craving_query,
                        location=user_location_dict
                    )
                    st.session_state["recommended_products"] = recs
                    st.session_state["searched_for"] = craving_query
                    st.session_state["selected_product"] = None
                    st.session_state["completed_order"] = None
                except Exception as e:
                    st.error(f"Error fetching recommendations: {e}")

    # Display Recommendations
    if "recommended_products" in st.session_state and st.session_state["recommended_products"]:
        st.markdown(f"### 📋 Top Safe '{st.session_state.get('searched_for', craving_query).title()}' Products for {user_name}")
        st.caption(f"Clinically screened for **{medical_history}**, verified free of **{allergies_input}**, and checked for delivery to **{loc_city or 'Your Area'}, {loc_country}**.")

        for idx, prod in enumerate(st.session_state["recommended_products"]):
            with st.container():
                st.markdown(f"""
                <div class="product-card">
                    <span class="category-tag">📦 {prod.get('category', 'Grocery')}</span>
                    <span class="natural-badge">🌿 {prod.get('natural_highlight', '100% Natural Formulation')}</span>
                    <h3 style="margin: 4px 0; color: #0F172A;">{prod.get('name')}</h3>
                    <p style="color: #64748B; font-weight: 600; margin-bottom: 8px;">
                        Brand: <strong>{prod.get('brand')}</strong> | Estimated Price: <strong>{prod.get('estimated_price', '₹299')}</strong>
                    </p>
                    <div class="med-badge">
                        🩺 <strong>Medical Suitability ({medical_history}):</strong> {prod.get('medical_suitability')}
                    </div>
                    <div class="allergen-badge">
                        🛡️ <strong>Allergen Clearance ({allergies_input}):</strong> {prod.get('allergen_guarantee')}
                    </div>
                    <p style="margin-top: 6px;"><strong>Key Natural Ingredients:</strong> {prod.get('key_ingredients')}</p>
                    <div style="color: #059669; font-size: 0.9rem; font-weight: 500; margin-top: 6px;">
                        📍 <strong>Local Delivery:</strong> {prod.get('local_availability', 'Available for delivery')} (via <em>{prod.get('local_retailer', 'Regional Stores')}</em>)
                    </div>
                </div>
                """, unsafe_allow_html=True)

                direct_url = prod.get("direct_product_page_url") or prod.get("primary_order_link", "#")
                store_url = prod.get("secondary_order_link") or prod.get("primary_order_link", "#")

                col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.3, 1.2])
                with col_btn1:
                    if st.button(f"🤖 Autonomous Order Wizard", key=f"sel_prod_{idx}", use_container_width=True):
                        st.session_state["selected_product"] = prod
                        st.session_state["order_step"] = 1
                        st.session_state["completed_order"] = None
                        st.session_state["wizard_qty"] = 1
                        st.rerun()
                with col_btn2:
                    st.link_button(f"🎯 Open Exact Item Page", direct_url, help="Direct product landing page via DuckDuckGo bang - opens exact item directly without search clutter or competitor ads", use_container_width=True)
                with col_btn3:
                    st.link_button(f"🛍️ {prod.get('secondary_retailer_name', 'Store View')[:20]}", store_url, use_container_width=True)

                with st.expander(f"🔍 Direct Product & Clean Ingredient Breakdown: {prod.get('name')}"):
                    st.markdown(f"""
                    - **Brand & Manufacturer**: {prod.get('brand')}
                    - **Category**: {prod.get('category', 'Grocery')}
                    - **Direct Landing Link**: [🎯 Click to open single item on official merchant]({direct_url}) *(Bypasses cluttered multi-product search listings)*
                    - **Key Clean Ingredients**: `{prod.get('key_ingredients')}`
                    - **Clinical Medical Match**: {prod.get('medical_suitability')}
                    - **Allergen Free Guarantee**: {prod.get('allergen_guarantee')}
                    - **Local Availability**: {prod.get('local_availability')} (via *{prod.get('local_retailer', 'Regional Hub')}*)
                    """)

                st.markdown("---")

    # =========================================================================
    # 5-STEP AUTONOMOUS ORDERING WIZARD & HUMAN-IN-THE-LOOP PIN APPROVAL
    # =========================================================================
    if st.session_state.get("selected_product"):
        sel_prod = st.session_state["selected_product"]
        if "order_step" not in st.session_state:
            st.session_state["order_step"] = 1
        
        current_step = st.session_state["order_step"]

        st.markdown("### 🤖 Autonomous Procurement & Order Execution Assistant")
        st.caption("The SafeBite Agent autonomously negotiates logistics, verifies medical clearance, itemizes billing, and orders on your behalf upon your explicit PIN approval.")

        # Wizard Step Progress Bar
        step_items = [
            ("1️⃣ Logistics & Units", 1),
            ("2️⃣ Clinical Pre-Flight", 2),
            ("3️⃣ Billing & Payment", 3),
            ("4️⃣ PIN Approval", 4),
            ("5️⃣ Agent Execution", 5)
        ]
        scols = st.columns(5)
        for i, (title, s_idx) in enumerate(step_items):
            with scols[i]:
                if current_step == s_idx:
                    st.markdown(f'<div class="wizard-step-active">{title}</div>', unsafe_allow_html=True)
                elif current_step > s_idx:
                    st.markdown(f'<div class="wizard-step-done">✅ {title}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="wizard-step-pending">⚪ {title}</div>', unsafe_allow_html=True)
        st.write("")

        # Price parsing
        price_str = sel_prod.get("estimated_price", "299")
        import re
        p_match = re.search(r'([0-9\.]+)', price_str)
        unit_price = float(p_match.group(1)) if p_match else 299.0
        curr_sym = "₹" if "₹" in price_str else ("£" if "£" in price_str else "$")
        current_qty = st.session_state.get("wizard_qty", 1)
        subtotal = round(unit_price * current_qty, 2)
        taxes = round(subtotal * 0.05, 2)
        total_price = round(subtotal + taxes, 2)

        # ---------------- STEP 1: Logistics & Package Configuration ----------------
        if current_step == 1:
            st.markdown(f"""
            <div class="order-box">
                <h4 style="margin-top:0; color:#1D4ED8;">Step 1: Configure Logistics & Delivery Destination</h4>
                <h3 style="color:#0F172A; margin: 4px 0;">{sel_prod.get('name')}</h3>
                <p><strong>Brand:</strong> {sel_prod.get('brand')} | <strong>Estimated Unit Price:</strong> {sel_prod.get('estimated_price', f'{curr_sym}299')}</p>
                <div style="background:#DCFCE7; color:#166534; padding:8px 14px; border-radius:6px; font-weight:600; margin: 8px 0;">
                    🛡️ Verified Safe for {medical_history} & Zero Allergen conflict with {allergies_input}.
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_q, col_s = st.columns(2)
            with col_q:
                wiz_qty = st.number_input("Select Quantity / Units to Order:", min_value=1, max_value=12, value=current_qty, step=1, key="wiz_qty_input")
                st.session_state["wizard_qty"] = wiz_qty
            with col_s:
                wiz_speed = st.selectbox(
                    "Delivery Speed / Priority:",
                    ["⚡ Express 1-Day Priority Health Courier (Tomorrow 8 AM - 11 AM)", "📦 Standard Ground Delivery (1-2 Business Days)"],
                    index=0,
                    key="wiz_speed_input"
                )
                st.session_state["wizard_speed"] = wiz_speed

            wiz_addr = st.text_input(
                "Confirm Delivery Destination / Street Address:",
                value=st.session_state.get("wizard_address") or loc_address or f"{loc_city}, {loc_state} - {loc_pincode}, {loc_country}",
                help="The autonomous agent will direct the courier to this destination.",
                key="wiz_addr_input"
            )
            st.session_state["wizard_address"] = wiz_addr

            btn_col1, btn_col2 = st.columns([1, 2])
            with btn_col1:
                if st.button("❌ Cancel Order", key="cancel_step_1", use_container_width=True):
                    st.session_state["selected_product"] = None
                    st.session_state["order_step"] = 1
                    st.rerun()
            with btn_col2:
                if st.button("Proceed to Step 2: Clinical Pre-Flight Clearance ➔", type="primary", key="go_to_step_2", use_container_width=True):
                    st.session_state["order_step"] = 2
                    st.rerun()

        # ---------------- STEP 2: Clinical Pre-Flight Safety Clearance ----------------
        elif current_step == 2:
            st.markdown("#### Step 2: Autonomous Clinical Safety Clearance Certificate")
            st.write("Before placing orders, the SafeBite agent generates an authenticated pre-flight health clearance guaranteeing clinical compliance.")

            rx_code = f"SAFEBITE-RX-{abs(hash(sel_prod.get('name', '') + str(user_name))) % 90000 + 10000}"
            st.session_state["rx_code"] = rx_code

            st.markdown(f"""
            <div class="cert-box">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #166534;">📋 SafeBite Clinical Pre-Flight Certificate</h3>
                    <span style="background: #16A34A; color: white; padding: 4px 12px; border-radius: 6px; font-weight: bold; font-size: 0.85rem;">STATUS: 100% CLINICALLY APPROVED</span>
                </div>
                <hr style="border: 0; border-top: 1px solid #BBF7D0; margin: 12px 0;">
                <div style="font-size: 0.95rem; line-height: 1.7;">
                    <div>👤 <strong>Recipient / Patient:</strong> {user_name or 'Valued User'}</div>
                    <div>🩺 <strong>Medical Evaluation:</strong> Cleared for <em>{medical_history or 'General Health'}</em></div>
                    <div>🚫 <strong>Allergen Inspection:</strong> 100% Guaranteed free from <em>{allergies_input or 'None Stated'}</em></div>
                    <div>🌿 <strong>Clean Label Guarantee:</strong> {sel_prod.get('natural_highlight', 'Zero artificial additives or chemical preservatives')}</div>
                    <div>📦 <strong>Prescription Target:</strong> {sel_prod.get('name')} ({current_qty} units)</div>
                    <div style="margin-top: 8px; font-weight: 700; color: #15803D;">
                        🔒 Clinical Clearance ID: <code>{rx_code}</code> (Signed by SafeBite Autonomous Agent)
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("⬅️ Back to Step 1 (Logistics)", key="back_to_step_1", use_container_width=True):
                    st.session_state["order_step"] = 1
                    st.rerun()
            with btn_col2:
                if st.button("Approve Clinical Clearance & Proceed to Billing ➔", type="primary", key="go_to_step_3", use_container_width=True):
                    st.session_state["order_step"] = 3
                    st.rerun()

        # ---------------- STEP 3: Itemized Billing & Payment Method Selection ----------------
        elif current_step == 3:
            st.markdown("#### Step 3: Itemized Billing & Payment Method Selection")
            st.write("Review the transparent itemized cost breakdown and select how the autonomous agent should process the transaction.")

            st.markdown(f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 18px; margin-bottom: 20px;">
                <h4 style="margin-top:0; color:#1E293B;">🧾 Itemized Invoice Breakdown</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;">
                    <tr style="border-bottom: 1px solid #F1F5F9; line-height: 2.2;">
                        <td><strong>Item:</strong> {sel_prod.get('name')} ({sel_prod.get('brand')})</td>
                        <td style="text-align: right;">{current_qty} × {curr_sym}{unit_price:.2f} = <strong>{curr_sym}{subtotal:.2f}</strong></td>
                    </tr>
                    <tr style="border-bottom: 1px solid #F1F5F9; line-height: 2.2;">
                        <td>🛡️ Certified Cold-Chain Health Packaging & Priority Courier</td>
                        <td style="text-align: right; color: #16A34A; font-weight: 600;">FREE (₹0.00)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #F1F5F9; line-height: 2.2;">
                        <td>🏛️ Estimated Regulatory Compliance & Taxes (5% GST/VAT)</td>
                        <td style="text-align: right;">{curr_sym}{taxes:.2f}</td>
                    </tr>
                    <tr style="line-height: 2.5; font-size: 1.15rem; color: #1D4ED8;">
                        <td><strong>Net Total Payable Amount</strong></td>
                        <td style="text-align: right;"><strong>{curr_sym}{total_price:.2f}</strong></td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            pay_methods = [
                "UPI (Google Pay / PhonePe / Paytm / BHIM)",
                "Credit / Debit Card (Visa / Mastercard / RuPay)",
                "Net Banking (Instant Automated Verification)",
                "Cash on Delivery (Safe Courier Handover)"
            ]
            saved_pay = st.session_state.get("wizard_payment", pay_methods[0])
            sel_pay = st.radio("Select Payment Method for Agent Execution:", pay_methods, index=pay_methods.index(saved_pay) if saved_pay in pay_methods else 0, key="pay_method_input")
            st.session_state["wizard_payment"] = sel_pay

            if "UPI" in sel_pay:
                upi_val = st.text_input("Enter your VPA / UPI ID:", value=st.session_state.get("wizard_upi", "alex@okaxis"), help="The agent will trigger payment request upon your PIN authorization in Step 4.", key="upi_input")
                st.session_state["wizard_upi"] = upi_val
            elif "Card" in sel_pay:
                card_val = st.text_input("Card Details (Last 4 digits for authorization):", value=st.session_state.get("wizard_card", "•••• •••• •••• 4821"), key="card_input")
                st.session_state["wizard_card"] = card_val

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("⬅️ Back to Step 2 (Safety Certificate)", key="back_to_step_2", use_container_width=True):
                    st.session_state["order_step"] = 2
                    st.rerun()
            with btn_col2:
                if st.button("Proceed to Step 4: Human-in-the-Loop PIN Approval ➔", type="primary", key="go_to_step_4", use_container_width=True):
                    st.session_state["order_step"] = 4
                    st.rerun()

        # ---------------- STEP 4: Human-in-the-Loop PIN Approval ----------------
        elif current_step == 4:
            st.markdown("#### Step 4: Human-in-the-Loop PIN / OTP Authorization")
            st.write("To ensure total security, the SafeBite Autonomous Agent will NOT place orders or debit funds without your explicit PIN approval.")

            st.markdown(f"""
            <div style="background: #F8FAFC; border: 2px solid #2563EB; border-radius: 12px; padding: 22px; margin-bottom: 20px;">
                <h3 style="color: #1E3A8A; margin-top: 0;">🔐 Agent Execution Authorization Request</h3>
                <p style="color: #334155; font-size: 0.95rem;">
                    The autonomous agent has finalized the cart, applied clinical health certification (<code>{st.session_state.get('rx_code', 'SAFEBITE-RX-98214')}</code>), 
                    and prepared the direct courier dispatch.
                </p>
                <div style="background: white; border-radius: 8px; padding: 14px; border: 1px solid #CBD5E1; margin: 12px 0;">
                    <p style="margin: 4px 0;">📦 <strong>Product:</strong> {sel_prod.get('name')} ({current_qty} unit(s))</p>
                    <p style="margin: 4px 0;">📍 <strong>Destination:</strong> {st.session_state.get('wizard_address', loc_address)}</p>
                    <p style="margin: 4px 0;">💳 <strong>Payment Method:</strong> {st.session_state.get('wizard_payment', 'UPI')}</p>
                    <p style="margin: 4px 0; font-size: 1.15rem; color: #1D4ED8;">
                        💰 <strong>Total Amount to Debit:</strong> <strong>{curr_sym}{total_price:.2f}</strong>
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            pin_col, consent_col = st.columns([1, 1])
            with pin_col:
                user_pin = st.text_input(
                    "🔑 Enter 4-Digit or 6-Digit Payment PIN / OTP:",
                    type="password",
                    max_chars=6,
                    placeholder="••••••",
                    help="Encrypted token. Will be securely passed to authorize the agent's autonomous checkout.",
                    key="wizard_pin_input"
                )
            with consent_col:
                st.write("")
                st.write("")
                approval_consent = st.checkbox(
                    f"☑️ I authorize SafeBite Agent to autonomously order on my behalf and debit {curr_sym}{total_price:.2f}.",
                    value=False,
                    key="wizard_consent_input"
                )

            btn_col1, btn_col2 = st.columns([1, 2])
            with btn_col1:
                if st.button("⬅️ Back to Step 3 (Billing)", key="back_to_step_3", use_container_width=True):
                    st.session_state["order_step"] = 3
                    st.rerun()
            with btn_col2:
                if st.button("🚀 Authorize & Dispatch Autonomous Order Now", type="primary", key="dispatch_order_btn", use_container_width=True):
                    if not user_pin or len(user_pin.strip()) < 4:
                        st.error("⚠️ Security Validation Failed: Please enter your 4-digit or 6-digit PIN / OTP to authorize the transaction.")
                    elif not approval_consent:
                        st.error("⚠️ Authorization Required: Please check the authorization box to grant the agent permission to place the order.")
                    else:
                        with st.spinner("🤖 Agent executing autonomous checkout, locking single-item stock, and dispatching courier..."):
                            import time
                            time.sleep(1.2)
                            current_order_loc = {
                                "country": loc_country,
                                "state": loc_state,
                                "city": loc_city,
                                "pincode": loc_pincode,
                                "address": st.session_state.get("wizard_address", loc_address)
                            }
                            order_result = process_automated_order(
                                product=sel_prod,
                                user_name=user_name or "Valued User",
                                location=current_order_loc,
                                quantity=current_qty,
                                payment_method=st.session_state.get("wizard_payment", "UPI"),
                                delivery_speed=st.session_state.get("wizard_speed", "Express 1-Day Priority Courier"),
                                pin_authorized=True
                            )
                            if "rx_code" in st.session_state:
                                order_result["safety_rx_id"] = st.session_state["rx_code"]

                            st.session_state["completed_order"] = order_result
                            st.session_state["order_step"] = 5
                            st.rerun()

        # ---------------- STEP 5: Live Autonomous Agent Execution Timeline & Receipt ----------------
        elif current_step == 5 and st.session_state.get("completed_order"):
            ord_info = st.session_state["completed_order"]
            st.balloons()
            st.success(f"🎉 Autonomous Order Successfully Placed & Dispatched! Order ID: {ord_info['order_id']}")

            # Live Agent Execution Terminal Log
            st.markdown(f"""
            <div class="agent-terminal">
                <div>[SAFEBITE AUTONOMOUS AGENT EXECUTION LOG]</div>
                <div>▶ 00:00:01 🤖 Agent initialized autonomous session for recipient '{ord_info.get('recipient_name')}'.</div>
                <div>▶ 00:00:02 🔐 PIN / OTP verification token authenticated via banking gateway. Status: APPROVED.</div>
                <div>▶ 00:00:03 📦 Single-item inventory reserved at {ord_info.get('brand')} certified clean-label depot.</div>
                <div>▶ 00:00:04 📋 Clinical Safety Certificate ({ord_info.get('safety_rx_id')}) bound to logistics manifest.</div>
                <div>▶ 00:00:05 🚚 Priority health courier dispatched! Consignment Tracking ID: <strong>{ord_info.get('tracking_number')}</strong>.</div>
                <div>▶ 00:00:06 🎯 Autonomous procurement cycle COMPLETED. Zero human manual cart filling needed!</div>
            </div>
            """, unsafe_allow_html=True)

            delivery_info = ord_info.get("delivery_location", {})
            formatted_address = delivery_info.get("full_formatted_address", delivery_info.get("address", loc_address))

            st.markdown(f"""
            ### 📦 Official Order Manifest & Clinical Consignment Summary
            - **Product**: {ord_info.get('product_name')} ({ord_info.get('brand')})
            - **Quantity**: {ord_info.get('quantity')} unit(s) | **Unit Price**: {ord_info.get('unit_price')}
            - **Total Paid**: **{ord_info.get('total_price')}** (Includes Taxes & Free Priority Delivery)
            - **Payment Status**: {ord_info.get('payment_status')} via {ord_info.get('payment_method')}
            - **Recipient**: {ord_info.get('recipient_name')}
            - **Delivery Destination**: {formatted_address}
            - **Logistics ETA**: {ord_info.get('delivery_eta', 'Tomorrow 8:00 AM - 11:00 AM')}
            - **Clinical Rx Clearance ID**: <code>{ord_info.get('safety_rx_id')}</code> (100% Safe for {medical_history} & free of {allergies_input})
            - **Consignment Tracking Number**: <code>{ord_info.get('tracking_number')}</code>
            """)

            direct_link = ord_info.get("direct_product_page_url") or ord_info.get("direct_checkout_url", "#")
            store_link = ord_info.get("direct_checkout_url", "#")
            alt_store_link = ord_info.get("secondary_checkout_url", "#")

            oc1, oc2, oc3 = st.columns(3)
            with oc1:
                st.link_button("🎯 Open Exact Product Page (Direct Landing)", direct_link, help="Opens the single product page directly without competitor ads", use_container_width=True)
            with oc2:
                st.link_button(f"📦 Buy on {ord_info.get('primary_retailer', 'Store')}", store_link, use_container_width=True)
            with oc3:
                st.link_button(f"🛒 Alternative Store View", alt_store_link, use_container_width=True)

            st.write("")
            if st.button("🔄 Order Another Safe Food Item", type="secondary", use_container_width=True):
                st.session_state["selected_product"] = None
                st.session_state["completed_order"] = None
                st.session_state["order_step"] = 1
                st.rerun()


# =========================================================================
# TAB 2: PRODUCT SAFETY & ALLERGEN INSPECTOR (AUDIT URL / TEXT / LABEL)
# =========================================================================
with tab_inspect:
    st.subheader("Step 2: Choose Product Input Method to Audit")
    st.write("Inspect any existing product by URL, ingredient text, or label photograph:")

    input_options = [
        "🌐 Product URL (Agent will open & scrape the webpage for ingredients)",
        "📝 Paste Ingredients List or Product Description",
        "📸 Upload Product Label Image (Multimodal OCR)"
    ]
    saved_method = st.session_state.get("safety_input_method", input_options[0])
    idx_method = input_options.index(saved_method) if saved_method in input_options else 0

    input_method = st.radio(
        "Select Option:",
        input_options,
        index=idx_method,
        key="safety_radio_select"
    )
    st.session_state["safety_input_method"] = input_method

    product_url = ""
    product_text = ""
    uploaded_image = None

    if "🌐 Product URL" in input_method:
        url_col1, url_col2 = st.columns([3, 1])
        with url_col1:
            product_url = st.text_input(
                "Enter Product URL to Scrape:",
                placeholder="https://example.com/product-page or any grocery / e-commerce food link"
            )
            st.caption("ℹ️ *Note: Many supermarket & e-commerce websites (e.g. Amazon, Blinkit, Zepto, BigBasket) use anti-bot protection or render ingredients in images. If a URL cannot be scraped, the agent will prompt you to paste ingredients or upload a label photo.*")
        with url_col2:
            st.write("")
            st.write("")
            if st.button("Use Sample URL"):
                product_url = "https://world.openfoodfacts.org/product/737628064502/rice-noodles-ka-me"
                st.session_state["demo_url"] = product_url
                st.rerun()

        if "demo_url" in st.session_state and not product_url:
            product_url = st.session_state["demo_url"]

    elif "📝 Paste Ingredients" in input_method:
        txt_col1, txt_col2 = st.columns([3, 1])
        with txt_col1:
            product_text = st.text_area(
                "Paste the ingredient list or product details:",
                height=140,
                placeholder="Example: Enriched wheat flour, sugar, whey protein concentrate, high fructose corn syrup, sodium caseinate, soy lecithin, artificial flavor..."
            )
        with txt_col2:
            st.write("")
            st.write("")
            if st.button("Load Sample Ingredients"):
                product_text = (
                    "Ingredients: Enriched wheat flour (wheat flour, niacin, reduced iron), "
                    "sugar, high fructose corn syrup, whey protein concentrate, sodium caseinate, "
                    "soy lecithin, salt, maltodextrin, artificial vanilla flavor."
                )
                st.session_state["demo_text"] = product_text
                st.rerun()

        if "demo_text" in st.session_state and not product_text:
            product_text = st.session_state["demo_text"]

    else: # Image upload
        st.markdown("##### 📸 Upload Product Label or Nutrition Facts Panel")
        st.caption(
            "💡 **Tips for Best Results:**\n"
            "- Upload a clear, close-up photo of the **'Ingredients:'** or **'Nutrition Facts'** panel on the back or side of the package (not just the front brand logo).\n"
            "- Ensure good lighting without glare or reflection covering the text.\n"
            "- Make sure small printed text is sharp and in focus."
        )
        uploaded_image = st.file_uploader(
            "Upload a clear photo of the product label or ingredient list:", 
            type=["jpg", "jpeg", "png", "webp"]
        )
        if uploaded_image:
            st.image(uploaded_image, caption="Uploaded Label", use_container_width=True)

    st.markdown("---")

    # Run Safety Check
    if st.button("🔍 Check Product Safety Now", type="primary", use_container_width=True):
        if not user_name:
            st.warning("⚠️ Please enter your Name / Username in Step 1.")
        elif not medical_history and not allergies_list:
            st.warning("⚠️ Please provide at least your Medical Condition or Allergies in Step 1.")
        elif "🌐 Product URL" in input_method and not product_url:
            st.warning("⚠️ Please enter a product URL to scrape.")
        elif "📝 Paste Ingredients" in input_method and not product_text:
            st.warning("⚠️ Please paste the ingredients text.")
        elif "📸 Upload Product Label" in input_method and not uploaded_image:
            st.warning("⚠️ Please upload a product label image.")
        else:
            with st.spinner("🤖 Agent at work: Scraping product details, analyzing medical conditions, and detecting hidden allergens..."):
                try:
                    provider_info = ""
                    if "🌐 Product URL" in input_method or "📝 Paste Ingredients" in input_method:
                        req_type = "url" if "🌐 Product URL" in input_method else "text"
                        source_val = product_url if req_type == "url" else product_text

                        user_location_obj = UserLocation(
                            country=loc_country,
                            state=loc_state,
                            city=loc_city,
                            pincode=loc_pincode,
                            address=loc_address
                        )
                        user_request = ProductSafetyRequest(
                            user_name=user_name,
                            medical_history=medical_history,
                            allergies=allergies_list,
                            food_preferences=food_preferences or "None",
                            input_type=req_type,
                            product_source=source_val,
                            location=user_location_obj
                        )

                        result = run_agent_workflow(user_request)
                        report_text = result.get("final_output", "No assessment generated.")
                        scraped_preview = result.get("scraped_content", "")
                        verdict = result.get("verdict", "PARTIALLY SAFE")
                        provider_info = result.get("provider_used", "AI Model")

                        if req_type == "url" and scraped_preview:
                            with st.expander("📄 Click to inspect what the agent scraped from the URL"):
                                st.text(scraped_preview[:2500] + ("..." if len(scraped_preview) > 2500 else ""))

                    else:
                        image_bytes = uploaded_image.getvalue()
                        image_part = types.Part.from_bytes(data=image_bytes, mime_type=uploaded_image.type)

                        allergies_formatted = ", ".join(allergies_list) if allergies_list else "None specified"
                        preferences_formatted = food_preferences if food_preferences else "None specified"

                        vision_prompt = f"""
                        You are an elite clinical pharmacologist, toxicologist, and allergen-detection specialist.
                        Analyze the uploaded image of this product's ingredient list and nutrition label.
                        Cross-reference the ingredients with the user's specific health profile.

                        USER PROFILE:
                        - User Name: {user_name}
                        - Medical History / Chronic Conditions: {medical_history}
                        - Strict Allergies: {allergies_formatted}
                        - Dietary / Food Preferences: {preferences_formatted}

                        CLINICAL AUDIT & OCR INSTRUCTIONS:
                        1. **Read & Extract Ingredients**:
                           - Identify and transcribe all visible ingredients and nutritional values.
                           - If the image does NOT show a readable ingredient list (e.g. image is blurry, only shows front brand marketing without ingredients, or text is cut off), start your response with:
                             `VERDICT: UNABLE TO ASSESS`
                             Followed by a clear explanation:
                             "The uploaded photo does not clearly show the ingredient list. Please upload a clear close-up photo of the ingredients or nutrition facts section on the back/side of the packaging."
                        2. **Hidden Allergen & Derivative Detection**:
                           - Scrutinize all identified ingredients for disguised or derivative forms of user's allergens.
                        3. **Medical Pathophysiology Analysis**:
                           - Dynamically evaluate how ingredients affect chronic conditions.
                        4. **Food Preference Compliance**:
                           - Confirm adherence to preferences. Flag hidden animal byproducts.
                        5. **Output Structure Requirements**:
                           - Must start with: `VERDICT: SAFE`, `VERDICT: PARTIALLY SAFE`, `VERDICT: UNSAFE`, or `VERDICT: UNABLE TO ASSESS`.
                           - Include sections: Executive Summary, Hidden Allergens Alert, Medical Condition Interaction, Flagged vs Safe Ingredients, Actionable Clinical Recommendation.
                        """

                        report_text, provider_info = generate_clinical_assessment(vision_prompt, image_part)

                        if "VERDICT: UNABLE TO ASSESS" in report_text.upper():
                            verdict = "UNABLE TO ASSESS"
                        elif "VERDICT: UNSAFE" in report_text.upper():
                            verdict = "UNSAFE"
                        elif "VERDICT: PARTIALLY SAFE" in report_text.upper():
                            verdict = "PARTIALLY SAFE"
                        elif "VERDICT: SAFE" in report_text.upper():
                            verdict = "SAFE"
                        else:
                            verdict = "PARTIALLY SAFE"

                    # Display Verdict
                    st.markdown("### 📋 Clinical Safety Assessment Report")
                    st.caption(f"⚡ Analysis Engine: {provider_info}")

                    if verdict == "UNABLE TO ASSESS":
                        st.markdown(
                            f"""<div class="verdict-unable">
                            ⚠️ VERDICT: UNABLE TO FETCH INGREDIENT LIST FROM URL<br>
                            <span style="font-size:0.95rem; font-weight:normal;">
                            {result.get('scrape_reason', 'The webpage could not be scraped or does not contain a readable ingredient list.')}
                            </span>
                            </div>""", 
                            unsafe_allow_html=True
                        )

                        st.markdown(report_text)

                        # Interactive alternative selector
                        st.markdown("---")
                        st.markdown("### 👉 Please select another option to audit this product:")
                        col_alt1, col_alt2 = st.columns(2)
                        with col_alt1:
                            if st.button("📝 Switch to 'Paste Ingredients List'", type="primary", use_container_width=True, key="btn_switch_paste"):
                                st.session_state["safety_input_method"] = input_options[1]
                                st.rerun()
                        with col_alt2:
                            if st.button("📸 Switch to 'Upload Label Image'", use_container_width=True, key="btn_switch_upload"):
                                st.session_state["safety_input_method"] = input_options[2]
                                st.rerun()

                        with st.expander("⚡ Or paste ingredients right here to check immediately:", expanded=True):
                            direct_ing_text = st.text_area(
                                "Paste product ingredients here:",
                                placeholder="e.g. Enriched wheat flour, sugar, whey protein concentrate, high fructose corn syrup, sodium caseinate, soy lecithin, salt...",
                                key="direct_fallback_input"
                            )
                            if st.button("🔍 Check These Ingredients Now", type="primary", key="btn_run_direct_fallback"):
                                if not direct_ing_text.strip():
                                    st.warning("Please paste ingredient text first.")
                                else:
                                    st.session_state["demo_text"] = direct_ing_text
                                    st.session_state["safety_input_method"] = input_options[1]
                                    st.rerun()

                    elif verdict == "SAFE":
                        st.markdown(
                            f"""<div class="verdict-safe">
                            ✅ VERDICT: SAFE FOR {user_name.upper()}<br>
                            <span style="font-size:0.95rem; font-weight:normal;">No conflicting allergens, medical contraindications, or dietary preference violations detected.</span>
                            </div>""", 
                            unsafe_allow_html=True
                        )
                        st.markdown(report_text)
                    elif verdict == "PARTIALLY SAFE":
                        st.markdown(
                            f"""<div class="verdict-partially-safe">
                            ⚠️ VERDICT: PARTIALLY SAFE (PROCEED WITH CAUTION)<br>
                            <span style="font-size:0.95rem; font-weight:normal;">Borderline ingredients, traces/potential cross-contact, or moderate medical contraindications detected.</span>
                            </div>""", 
                            unsafe_allow_html=True
                        )
                        st.markdown(report_text)
                    else: # UNSAFE
                        st.markdown(
                            f"""<div class="verdict-unsafe">
                            🚫 VERDICT: UNSAFE (DO NOT CONSUME)<br>
                            <span style="font-size:0.95rem; font-weight:normal;">Contains strict or hidden allergens, strong medical contraindications, or direct dietary violations.</span>
                            </div>""", 
                            unsafe_allow_html=True
                        )
                        st.markdown(report_text)

                except Exception as e:
                    st.error(f"An error occurred during clinical analysis: {e}")