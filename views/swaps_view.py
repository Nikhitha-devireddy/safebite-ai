"""
SafeBite AI - Safe Swaps & Food Craving Finder View
Recommends verified safe products, condition-tailored craving alternatives,
smart 1:1 clean swaps, and human-in-the-loop ordering.
"""

import streamlit as st
from typing import List, Dict, Any
from recommendations import recommend_safe_products, process_automated_order
from cgm_simulator import SmartSafeSwapEngine
from components.cards import render_verdict_badge, render_nutrition_summary_row

def render_swaps_view():
    """Renders the Safe Food Swaps & Craving Finder interface."""
    st.subheader("🛒 Universal Safe Food & Craving Finder")
    st.markdown("Find safe, condition-tailored products for any food craving or category. Every recommendation is clinically verified against your medical history.")

    c_loc_dict = st.session_state.get("location_dict", {})
    c_city = c_loc_dict.get("city", "Bengaluru")
    c_country = c_loc_dict.get("country", "India")
    c_user = st.session_state.get("user_name", "Alex")
    c_med = st.session_state.get("medical_history", "General Wellness")
    c_allergies = st.session_state.get("allergies_list", [])
    c_pref = st.session_state.get("food_preferences", "Clean Label")

    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:16px; font-size:0.87rem;">
        <span style="margin-right:16px;">👤 Patient: <strong>{c_user}</strong></span>
        <span style="margin-right:16px;">🩺 Medical Profile: <strong>{c_med or 'General'}</strong></span>
        <span style="margin-right:16px;">🚫 Strict Allergens: <strong>{', '.join(c_allergies) if c_allergies else 'None'}</strong></span>
        <span>📍 Delivery Area: <strong>{c_city}, {c_country}</strong></span>
    </div>
    """, unsafe_allow_html=True)

    # Popular Craving Chips
    st.markdown("##### ⚡ Popular Craving Categories (Click for 1-Click Clinical Screening):")
    chips = [
        ("🍫 85%+ Dark Chocolate", "dark chocolate"),
        ("🍪 Clean Protein Cookies", "cookies"),
        ("🍞 Sourdough Bread", "sourdough bread"),
        ("🍝 High-Fiber Pasta", "pasta"),
        ("🍿 Roasted Makhana", "savory snacks")
    ]

    cols_c = st.columns(5)
    for c_idx, (c_label, c_query) in enumerate(chips):
        with cols_c[c_idx]:
            if st.button(c_label, key=f"chip_swap_{c_idx}", use_container_width=True):
                with st.spinner(f"Screening catalog for '{c_query}'..."):
                    recs = recommend_safe_products(
                        user_name=c_user,
                        medical_history=c_med,
                        allergies=c_allergies,
                        food_preferences=c_pref,
                        craving_query=c_query,
                        location=c_loc_dict
                    )
                    st.session_state["craving_results"] = recs
                    st.session_state["craving_last_query"] = c_query
                st.rerun()

    st.markdown("---")

    # Custom Craving Search
    cr_col_in, cr_col_btn = st.columns([5, 1])
    with cr_col_in:
        custom_craving = st.text_input(
            "Search Craving or Food Category:",
            placeholder="e.g. 'sugar-free dark chocolate', 'dairy-free pasta', 'keto snack'...",
            key="custom_craving_input",
            label_visibility="collapsed"
        )
    with cr_col_btn:
        run_craving = st.button("FIND SAFE FOODS", type="primary", use_container_width=True, key="btn_run_craving")

    if run_craving and custom_craving.strip():
        with st.spinner(f"Searching verified safe products for '{custom_craving}'..."):
            recs = recommend_safe_products(
                user_name=c_user,
                medical_history=c_med,
                allergies=c_allergies,
                food_preferences=c_pref,
                craving_query=custom_craving.strip(),
                location=c_loc_dict
            )
            st.session_state["craving_results"] = recs
            st.session_state["craving_last_query"] = custom_craving.strip()

    # Results Display
    recs = st.session_state.get("craving_results")
    if recs:
        st.markdown(f"### 🎯 Clinically Approved Recommendations for *{st.session_state.get('craving_last_query', 'Craving')}*")
        for idx, r in enumerate(recs):
            if isinstance(r, dict):
                p_name = r.get("name") or r.get("product_name") or "Safe Alternative"
                p_brand = r.get("brand", "")
                p_status = r.get("clinical_status", "CLEAR / SAFE")
                p_just = r.get("medical_suitability") or r.get("clinical_justification") or ""
                p_high = r.get("natural_highlight") or r.get("clean_ingredient_highlights") or ""
                p_price = r.get("estimated_price", "")
                p_store = r.get("local_retailer", "")
            else:
                p_name = getattr(r, "product_name", getattr(r, "name", "Safe Alternative"))
                p_brand = getattr(r, "brand", "")
                p_status = getattr(r, "clinical_status", "CLEAR / SAFE")
                p_just = getattr(r, "clinical_justification", getattr(r, "medical_suitability", ""))
                p_high = getattr(r, "clean_ingredient_highlights", getattr(r, "natural_highlight", ""))
                p_price = getattr(r, "estimated_price", "")
                p_store = getattr(r, "local_retailer", "")

            with st.container():
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                        <h4 style="margin:0; color:#0F172A;">{p_name} <span style="font-size:0.85rem; color:#64748B;">by {p_brand}</span></h4>
                        <span class="badge-clear">🟢 {p_status}</span>
                    </div>
                    <div style="font-size:0.88rem; color:#475569; margin: 8px 0;">{p_just}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-top:6px;">
                        <div style="font-size:0.82rem; color:#059669; font-weight:600;">{p_high}</div>
                        {f'<div style="font-size:0.82rem; color:#0284C7; font-weight:700;">{p_price} · {p_store}</div>' if p_price else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)


    # 1:1 Smart Safe Swaps Table
    st.markdown("---")
    st.markdown("### 🔄 1:1 Direct Clean Ingredient Swaps")
    active_prod = st.session_state.get("active_product_detail")
    target_category = active_prod.name if active_prod else "snack"
    smart_swaps = SmartSafeSwapEngine.get_smart_swaps(target_category)

    col_s1, col_s2 = st.columns(2)
    for s_idx, swap in enumerate(smart_swaps[:2]):
        col = col_s1 if s_idx == 0 else col_s2
        with col:
            st.markdown(f"""
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:16px;">
                <div style="font-size:0.75rem; color:#15803D; font-weight:700;">1:1 CLEAN ALTERNATIVE</div>
                <h4 style="margin:4px 0; color:#166534;">{swap['swap_name']}</h4>
                <div style="display:flex; gap:10px; margin: 8px 0;">
                    <span style="background:#DCFCE7; color:#166534; padding:2px 8px; border-radius:4px; font-size:0.8rem; font-weight:700;">{swap['delta_sugar']}</span>
                    <span style="background:#DCFCE7; color:#166534; padding:2px 8px; border-radius:4px; font-size:0.8rem; font-weight:700;">{swap['delta_fiber']}</span>
                </div>
                <div style="font-size:0.82rem; color:#15803D;">{swap['clean_perks']}</div>
            </div>
            """, unsafe_allow_html=True)
