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
    """Renders condition-by-condition clinical assessment cards with structured medical context and offending ingredients."""
    if not assessments:
        st.info("No specific condition assessments recorded.")
        return

    for a in assessments:
        condition = getattr(a, "condition", "Condition")
        status = getattr(a, "status", ClinicalStatus.UNKNOWN)
        status_val = status.value if hasattr(status, "value") else str(status)
        reason = getattr(a, "reason", "")
        evidence = getattr(a, "evidence", "")
        condition_overview = getattr(a, "condition_overview", "")
        offending_ingredients = getattr(a, "offending_ingredients", []) or []
        clinical_action = getattr(a, "clinical_action", "")
        source = getattr(a, "source", "")

        # Color schemes based on verdict
        if "AVOID" in status_val or "DANGER" in status_val or "UNSAFE" in status_val:
            border_color = "#F87171"
            card_bg = "#FFFFFF"
            accent_bar = "#EF4444"
        elif "CAUTION" in status_val or "WARN" in status_val:
            border_color = "#FBBF24"
            card_bg = "#FFFFFF"
            accent_bar = "#F59E0B"
        elif "CLEAR" in status_val or "SAFE" in status_val:
            border_color = "#86EFAC"
            card_bg = "#FFFFFF"
            accent_bar = "#10B981"
        else:
            border_color = "#CBD5E1"
            card_bg = "#FFFFFF"
            accent_bar = "#94A3B8"

        badge_html = render_verdict_badge(status_val)

        # Build Offending Ingredients Table HTML
        offending_html = ""
        if offending_ingredients:
            rows_html = ""
            for item in offending_ingredients:
                ing = item.get("ingredient", "Declared Item")
                issue = item.get("issue", "Health Conflict")
                sev = item.get("severity", "HIGH").upper()
                rat = item.get("rationale", "")

                sev_color = "#DC2626" if sev in ("CRITICAL", "HIGH") else "#D97706"
                sev_bg = "#FEE2E2" if sev in ("CRITICAL", "HIGH") else "#FEF3C7"

                rows_html += f"""
                <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 9px 12px; font-weight: 700; color: #7F1D1D; vertical-align: top;">
                        ❌ {ing}
                    </td>
                    <td style="padding: 9px 12px; vertical-align: top;">
                        <span style="background: {sev_bg}; color: {sev_color}; padding: 2px 7px; border-radius: 4px; font-size: 0.72rem; font-weight: 800; text-transform: uppercase;">{sev}</span>
                        <div style="font-weight: 600; color: #1E293B; font-size: 0.84rem; margin-top: 3px;">{issue}</div>
                    </td>
                    <td style="padding: 9px 12px; color: #475569; font-size: 0.83rem; line-height: 1.45; vertical-align: top;">
                        {rat}
                    </td>
                </tr>
                """

            offending_html = f"""
            <div style="margin: 12px 0; border: 1.5px solid #FECACA; border-radius: 8px; overflow: hidden; background: #FFF5F5;">
                <div style="background: #FEE2E2; padding: 8px 14px; font-size: 0.86rem; font-weight: 800; color: #991B1B; display: flex; align-items: center; gap: 6px;">
                    ⚠️ Offending Ingredients & Health Conflicts ({len(offending_ingredients)} Identified)
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.84rem; text-align: left; background: #FFFFFF;">
                        <thead>
                            <tr style="background: #F8FAFC; border-bottom: 1px solid #E2E8F0; color: #475569; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em;">
                                <th style="padding: 8px 12px; width: 28%;">Offending Ingredient</th>
                                <th style="padding: 8px 12px; width: 32%;">Specific Issue & Severity</th>
                                <th style="padding: 8px 12px; width: 40%;">Why It's Harmful (Physiological Mechanism)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
            """

        # Build Medical Condition Overview Callout
        overview_html = ""
        if condition_overview:
            overview_html = f"""
            <div style="background: #F0F9FF; border-left: 3.5px solid #0284C7; padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 10px 0; font-size: 0.86rem; color: #0C4A6E; line-height: 1.5;">
                <div style="font-weight: 700; color: #0369A1; margin-bottom: 2px; display: flex; align-items: center; gap: 5px;">
                    🩺 Medical Condition Context & Pathophysiology
                </div>
                {condition_overview}
            </div>
            """

        # Build Action Callout
        action_html = ""
        if clinical_action:
            action_html = f"""
            <div style="background: #ECFDF5; border-left: 3.5px solid #10B981; padding: 10px 14px; border-radius: 0 6px 6px 0; margin-top: 10px; font-size: 0.85rem; color: #065F46; line-height: 1.45;">
                <div style="font-weight: 700; color: #047857; margin-bottom: 2px; display: flex; align-items: center; gap: 5px;">
                    💡 Actionable Clinical Strategy & Safe Alternatives
                </div>
                {clinical_action}
            </div>
            """

        # Evidence / Source Snippet
        evidence_html = ""
        if evidence:
            src_text = f" · Source: {source}" if source else ""
            evidence_html = f"""
            <div style="font-size: 0.78rem; color: #64748B; margin-top: 8px; border-top: 1px dashed #E2E8F0; padding-top: 6px;">
                <strong>Lab Evidence:</strong> <em>{evidence}</em>{src_text}
            </div>
            """

        with st.container():
            st.markdown(f"""
            <div style="border: 1.5px solid {border_color}; border-left: 6px solid {accent_bar}; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; background: {card_bg}; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                    <div style="font-size: 1.02rem; font-weight: 800; color: #0F172A;">
                        {condition}
                    </div>
                    <div>
                        {badge_html}
                    </div>
                </div>
                <div style="font-size: 0.92rem; font-weight: 600; color: #1E293B; margin-bottom: 6px; line-height: 1.45;">
                    {reason}
                </div>
                {overview_html}
                {offending_html}
                {action_html}
                {evidence_html}
            </div>
            """, unsafe_allow_html=True)

