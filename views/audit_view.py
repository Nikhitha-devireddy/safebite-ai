"""
SafeBite AI - Clinical Audit View
Renders in-depth deterministic clinical safety audits, regulatory FSSAI compliance,
chemical allergen derivatives, NOVA processing scores, and Ayurvedic compatibility.
"""

import streamlit as st
from typing import Optional
from schemas import Product, ClinicalStatus
from indian_engine import (
    FssaiComplianceEngine,
    IndianAdulterationDetector,
    IndianDietaryGuardrail,
    AyurvedicEngine
)
from cgm_simulator import NovaProcessingScorer, ClinicalRadarMatrix
from components.cards import (
    render_verdict_badge,
    render_nutrition_summary_row,
    render_clinical_assessment_cards
)

def render_audit_view():
    """Renders the detailed clinical audit report for the active product."""
    st.subheader("🩺 Clinical Safety & Regulatory Audit Report")

    detail_prod: Optional[Product] = st.session_state.get("active_product_detail")

    if not detail_prod:
        st.info("ℹ️ No active product selected for audit. Use the **🔍 Live Scanner** to scan a product, or select one from history.")
        return

    # Header Card
    st.markdown(f"""
    <div style="background: white; border: 1px solid #CBD5E1; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
            <div>
                <span style="font-weight:700; color:#059669; text-transform:uppercase; font-size:0.8rem;">{detail_prod.brand}</span>
                <h2 style="margin:4px 0; color:#0F172A;">{detail_prod.name} {f'· {detail_prod.pack_size}' if detail_prod.pack_size else ''}</h2>
                <span style="font-size:0.85rem; color:#64748B;">Category: {detail_prod.category or 'Packaged Food'} | Barcode: <code>{detail_prod.barcode or 'N/A'}</code></span>
            </div>
            <div>
                {render_verdict_badge(detail_prod.health_safety_verdict)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Clinical Portion & Quantity Guidance
    portion_data = getattr(detail_prod, "recommended_portion", None)
    if not portion_data:
        from clinical_engine import ClinicalRuleEngine
        portion_data = ClinicalRuleEngine.calculate_recommended_portion(
            detail_prod,
            st.session_state.get("medical_history", ""),
            ClinicalStatus.CLEAR
        )
        detail_prod.recommended_portion = portion_data

    p_limit = portion_data.get("portion_limit", "1 Standard Serving")
    p_action = portion_data.get("action", "Clinical Guidance")
    p_rat = portion_data.get("rationale", "")
    p_tips = portion_data.get("guidance_tips", [])
    p_color = portion_data.get("badge_color", "#059669")

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 2px solid {p_color}; border-radius: 10px; padding: 18px 22px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom: 8px;">
            <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; display:flex; align-items:center; gap:8px;">
                ⚖️ <span>Recommended Clinical Quantity:</span> <span style="color:{p_color}; font-size:1.25rem;">{p_limit}</span>
            </div>
            <div style="background: {p_color}; color: white; padding: 4px 14px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase;">
                {p_action}
            </div>
        </div>
        <div style="font-size: 0.92rem; color: #334155; margin-bottom: 10px; line-height: 1.5;">
            <strong>Physiological Rationale for {st.session_state.get('user_name', 'Patient')} ({st.session_state.get('medical_history', 'General')}):</strong><br>
            {p_rat}
        </div>
        {('<div style="font-size: 0.86rem; color: #065F46; background: #ECFDF5; padding: 10px 14px; border-radius: 6px; border: 1px solid #A7F3D0;"><strong>💡 Safe Consumption Guidelines:</strong><ul style="margin: 4px 0 0 0; padding-left: 20px;">' + ''.join([f'<li>{tip}</li>' for tip in p_tips]) + '</ul></div>') if p_tips else ''}
    </div>
    """, unsafe_allow_html=True)

    raw_ing_text = detail_prod.ingredients.raw_text if detail_prod.ingredients else ""


    # 1. FSSAI & Packaging Regulatory Audit
    fssai_lic = FssaiComplianceEngine.validate_license(raw_ing_text + " " + (detail_prod.description or ""))
    fssai_logo = FssaiComplianceEngine.detect_fssai_logos(detail_prod.name, raw_ing_text)
    hfss_res = FssaiComplianceEngine.calculate_hfss(detail_prod.nutrition)

    # 2. Indian Adulteration & FMCG Masking Radar
    adulterant_res = IndianAdulterationDetector.audit_adulterants(detail_prod.name, raw_ing_text)

    # 3. NOVA Processing & Clean Label Toxicity
    additives_cnt = len(detail_prod.ingredients.additives) if (detail_prod.ingredients and detail_prod.ingredients.additives) else 0
    nova_res = NovaProcessingScorer.evaluate_nova(detail_prod.name, raw_ing_text, additives_count=additives_cnt)

    # 4. 6-Axis Clinical Radar Matrix
    radar_scores = ClinicalRadarMatrix.compute_radar_scores(detail_prod.nutrition, detail_prod.ingredients, detail_prod.allergens)

    # 5. Ayurvedic Viruddha Ahara
    viruddha_combos = AyurvedicEngine.evaluate_viruddha_ahara(raw_ing_text)

    # Regulatory Ribbon
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
            <strong>Regulatory Mark:</strong> <span style="font-size:0.9rem;">{fssai_logo['badge']}</span>
            {f" | <span style='font-size:0.85rem; color:#0284C7; font-weight:600;'>{fssai_logo['fortified_badge']}</span>" if fssai_logo.get('fortified_badge') else ""}
        </div>
        <div>
            <span style="font-size:0.85rem; color:#475569; font-weight:600;">{fssai_lic['formatted_badge']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs for structured clinical deep-dive
    tab_overview, tab_rules, tab_nova, tab_adulterants, tab_ayurveda = st.tabs([
        "📊 Nutrition & Macros",
        "🩺 Clinical Verdicts",
        "🏭 NOVA & UPF Processing",
        "🔎 Adulteration & FMCG Radar",
        "🌿 Ayurvedic Compatibility"
    ])

    with tab_overview:
        st.markdown("#### Laboratory Nutritional Panel")
        render_nutrition_summary_row(detail_prod.nutrition)
        st.markdown("---")
        st.markdown("#### Ingredient Declaration")
        st.write(raw_ing_text or "No ingredient declaration available.")

    with tab_rules:
        st.markdown("#### Condition-Specific Medical Assessments")
        if detail_prod.clinical_assessments:
            render_clinical_assessment_cards(detail_prod.clinical_assessments)
        elif detail_prod.health_safety_reasons:
            for r in detail_prod.health_safety_reasons:
                st.warning(f"• {r}")
        else:
            st.info("No clinical flags detected.")

    with tab_nova:
        st.markdown(f"#### {nova_res['nova_badge']}")
        st.info(nova_res['nova_desc'])
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            st.metric("NOVA Group", f"Group {nova_res['nova_group']}")
        with col_n2:
            st.metric("Clean Label Score", f"{nova_res['clean_label_score']}/100")
        if nova_res['upf_markers_found']:
            st.markdown("##### 🚨 Ultra-Processed Markers Detected:")
            for m in nova_res['upf_markers_found']:
                st.error(f"• {m}")

    with tab_adulterants:
        st.markdown("#### Indian FMCG Adulterant & Masking Audit")
        col_ad1, col_ad2 = st.columns(2)
        with col_ad1:
            st.metric("Packaging Purity Score", f"{adulterant_res['purity_score']}/100")
        with col_ad2:
            if adulterant_res['has_palm_oil']:
                st.error("🚨 Palm Oil / Palmolein Present")
            else:
                st.success("✅ Free from Palm Oil")

        if adulterant_res['atta_masking']:
            st.warning("⚠️ **Atta Masking Detected:** Front packaging markets 'Atta / Wheat', but ingredient list shows Refined Wheat Flour (Maida) as the predominant flour.")

        if adulterant_res['hidden_sugars']:
            st.warning(f"⚠️ **Hidden Sugars Detected:** {', '.join(adulterant_res['hidden_sugars'])}")

    with tab_ayurveda:
        st.markdown("#### Ayurvedic Viruddha Ahara (Food Incompatibility)")
        if viruddha_combos:
            for combo in viruddha_combos:
                st.error(f"**{combo['name']}**: {combo['risk']}")
        else:
            st.success("✅ No incompatible Ayurvedic food combinations (Viruddha Ahara) detected.")
