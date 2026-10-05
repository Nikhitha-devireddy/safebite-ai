"""
SafeBite AI - Home Dashboard View
"""

import streamlit as st
from presets import get_all_presets, get_indian_presets, apply_preset_to_session
from product_search import ProductSearchPipeline
from components.cards import render_verdict_badge, render_nutrition_summary_row

def render_home_view(search_pipeline: ProductSearchPipeline):
    """Renders the main SafeBite AI home dashboard."""
    # Clinical Editorial Hero Header
    st.markdown(f"""
    <div class="clinical-hero">
        <div class="clinical-hero-badge">Evidence Before You Eat · Research-Grade Food Safety</div>
        <h1>Know what’s in your food.</h1>
        <p>Search, verify and understand products using real nutritional evidence, laboratory panels, and your personal medical safety profile. The system never fabricates facts.</p>
        <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; font-size: 0.85rem; color: #D1FAE5;">
            <span>👤 Patient: <strong>{st.session_state.get('user_name', 'Alex')}</strong></span>
            <span>🩺 Condition: <strong>{st.session_state.get('medical_history', 'General Health') or 'General Health'}</strong></span>
            <span>🚫 Allergens: <strong>{', '.join(st.session_state.get('allergies_list', [])) if st.session_state.get('allergies_list') else 'None'}</strong></span>
            <span>📍 Location: <strong>{st.session_state.get('location_dict', {}).get('city', 'Bengaluru')}, {st.session_state.get('location_dict', {}).get('country', 'India')}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Universal Search Bar
    st.markdown("### 🔎 Universal Food & Product Intelligence Search")
    home_query_col, home_btn_col = st.columns([5, 1])
    with home_query_col:
        home_query = st.text_input(
            "Search product, craving, barcode, or paste product URL:",
            placeholder="e.g. 'low-sugar protein bars in Bengaluru', or barcode '737628064502', or product URL",
            key="home_search_input",
            label_visibility="collapsed"
        )
    with home_btn_col:
        run_home_search = st.button("SEARCH", type="primary", use_container_width=True, key="home_search_btn")

    # 1-Click Quick Preset Health Profiles
    with st.expander("⚡ 1-Click Quick Preset Health Profiles (Audit Configurable Patient Constraints)", expanded=True):
        st.caption("Click any preset to automatically populate clinical parameters and execute verified queries:")
        
        all_presets = get_all_presets()
        for i in range(0, len(all_presets), 3):
            chunk = all_presets[i:i+3]
            cols = st.columns(len(chunk))
            for idx, preset in enumerate(chunk):
                with cols[idx]:
                    if st.button(
                        f"{preset.icon} {preset.name}",
                        key=f"btn_pre_{preset.id}",
                        use_container_width=True,
                        help=preset.tagline
                    ):
                        apply_preset_to_session(preset.id)
                        st.toast(f"Applied preset: {preset.name}", icon=preset.icon)
                        st.rerun()

        st.markdown("---")
        st.markdown("##### 🇮🇳 Indian Cultural, Religious & Clinical Presets:")
        indian_presets = get_indian_presets()
        for j in range(0, len(indian_presets), 3):
            ind_chunk = indian_presets[j:j+3]
            cols_ind = st.columns(len(ind_chunk))
            for k, ipreset in enumerate(ind_chunk):
                with cols_ind[k]:
                    if st.button(
                        f"{ipreset.icon} {ipreset.name}",
                        key=f"btn_pre_ind_{ipreset.id}",
                        use_container_width=True,
                        help=ipreset.tagline
                    ):
                        apply_preset_to_session(ipreset.id)
                        st.toast(f"Applied preset: {ipreset.name}", icon=ipreset.icon)
                        st.rerun()

    # Search Execution
    if run_home_search and home_query.strip():
        with st.spinner("🔍 Consulting Open Food Facts, Amazon, BigBasket, Blinkit, and Zepto in parallel..."):
            prods, crit, reasoning = search_pipeline.search_and_filter(
                query=home_query.strip(),
                user_medical_history=st.session_state.get("medical_history", ""),
                user_allergies=st.session_state.get("allergies_list", []),
                food_preferences=st.session_state.get("food_preferences", "")
            )
            st.session_state["search_results"] = prods
            st.session_state["search_crit"] = crit
            st.session_state["search_reasoning"] = reasoning

        if prods:
            st.success(f"Found {len(prods)} evidence-backed products.")
            for p in prods[:5]:
                with st.expander(f"{p.brand} - {p.name} ({p.health_safety_verdict or 'Audit Pending'})"):
                    render_nutrition_summary_row(p.nutrition)
                    st.write(f"**Ingredients:** {p.ingredients.raw_text if p.ingredients else 'Not verified'}")
        else:
            st.warning("No verified products matched query under strict clinical evidence rules.")
