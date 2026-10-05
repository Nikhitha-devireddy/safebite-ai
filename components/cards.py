"""
SafeBite AI - Reusable UI Cards & Badges
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from schemas import Product, NutritionFacts, ClinicalStatus

def render_verdict_badge(status_str: str) -> str:
    """Returns styled HTML badge for clinical verdict."""
    s = (status_str or "UNKNOWN").upper()
    if "CLEAR" in s or "SAFE" in s:
        return '<span class="badge-clear">🟢 CLEAR / SAFE</span>'
    elif "CAUTION" in s or "WARN" in s:
        return '<span class="badge-caution">🟡 CAUTION / MONITOR</span>'
    elif "AVOID" in s or "DANGER" in s or "UNSAFE" in s:
        return '<span class="badge-avoid">🔴 AVOID / CLINICAL RISK</span>'
    else:
        return '<span class="badge-unknown">⚪ UNKNOWN / NOT VERIFIED</span>'


def render_nutrition_summary_row(nutrition: Optional[NutritionFacts]):
    """Renders 4 quick macronutrient callout metrics."""
    if not nutrition:
        st.info("Nutrition panel unverified or unavailable.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cal = f"{nutrition.calories:.0f}" if nutrition.calories is not None else "--"
        st.markdown(f'<div class="metric-callout"><div class="val">{cal}</div><div class="lbl">Calories (kcal)</div></div>', unsafe_allow_html=True)
    with c2:
        sug = f"{nutrition.sugar_g:.1f}g" if nutrition.sugar_g is not None else "--"
        st.markdown(f'<div class="metric-callout"><div class="val">{sug}</div><div class="lbl">Sugars</div></div>', unsafe_allow_html=True)
    with c3:
        prot = f"{nutrition.protein_g:.1f}g" if nutrition.protein_g is not None else "--"
        st.markdown(f'<div class="metric-callout"><div class="val">{prot}</div><div class="lbl">Protein</div></div>', unsafe_allow_html=True)
    with c4:
        sod = f"{nutrition.sodium_mg:.0f}mg" if nutrition.sodium_mg is not None else "--"
        st.markdown(f'<div class="metric-callout"><div class="val">{sod}</div><div class="lbl">Sodium</div></div>', unsafe_allow_html=True)


def render_clinical_assessment_cards(assessments: List[Any]):
    """Renders condition-by-condition clinical assessment cards."""
    if not assessments:
        st.write("No specific condition assessments recorded.")
        return

    for a in assessments:
        condition = getattr(a, "condition", "Condition")
        status = getattr(a, "status", ClinicalStatus.UNKNOWN)
        status_val = status.value if hasattr(status, "value") else str(status)
        reason = getattr(a, "reason", "")
        evidence = getattr(a, "evidence", "")

        badge = render_verdict_badge(status_val)
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; background: #FFFFFF; box-sizing: border-box;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 6px;">
                    <strong>{condition}</strong>
                    {badge}
                </div>
                <div style="font-size: 0.9rem; color: #334155; margin-bottom: 4px;">{reason}</div>
                {f'<div style="font-size: 0.8rem; color: #64748B;"><em>Evidence: {evidence}</em></div>' if evidence else ''}
            </div>
            """, unsafe_allow_html=True)
