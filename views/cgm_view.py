"""
SafeBite AI - CGM (Continuous Glucose Monitor) Simulator View
Simulates blood glucose trajectories, glycemic index, fiber buffering,
and side-by-side Safe Swap glycemic response comparisons.
"""

import streamlit as st
from schemas import NutritionFacts, Product
from cgm_simulator import CgmGlucosePredictor, SmartSafeSwapEngine
from components.cgm_chart import render_cgm_trajectory_chart

def render_cgm_view():
    """Renders the interactive CGM simulator view."""
    st.subheader("📈 Continuous Glucose Monitor (CGM) Simulation Lab")
    st.markdown("Predict postprandial glycemic spike trajectory over 180 minutes based on net carbohydrates, glycemic load, and gastric emptying buffer factors.")

    active_prod = st.session_state.get("active_product_detail")

    # Parameters selection
    col_ctrl1, col_ctrl2 = st.columns([1, 2])

    with col_ctrl1:
        st.markdown("#### ⚙️ Simulation Controls")
        is_diabetic = st.checkbox(
            "Diabetic Mode (Insulin Resistance Factor 1.65x)",
            value="diabet" in st.session_state.get("medical_history", "").lower(),
            key="cgm_diabetic_mode"
        )
        baseline_val = st.slider("Fasting Baseline Glucose (mg/dL):", 70.0, 140.0, 95.0, 5.0, key="cgm_baseline_slider")

        # Auto-fill from active product if present
        def_carbs = active_prod.nutrition.carbs_g if (active_prod and active_prod.nutrition and active_prod.nutrition.carbs_g) else 45.0
        def_fiber = active_prod.nutrition.fiber_g if (active_prod and active_prod.nutrition and active_prod.nutrition.fiber_g) else 2.0
        def_sugar = active_prod.nutrition.sugar_g if (active_prod and active_prod.nutrition and active_prod.nutrition.sugar_g) else 18.0
        def_protein = active_prod.nutrition.protein_g if (active_prod and active_prod.nutrition and active_prod.nutrition.protein_g) else 4.0
        def_fat = active_prod.nutrition.fat_g if (active_prod and active_prod.nutrition and active_prod.nutrition.fat_g) else 10.0

        carbs_in = st.number_input("Total Carbohydrates (g):", min_value=0.0, max_value=200.0, value=float(def_carbs), step=1.0)
        fiber_in = st.number_input("Dietary Fiber (g):", min_value=0.0, max_value=50.0, value=float(def_fiber), step=0.5)
        sugar_in = st.number_input("Total Sugars (g):", min_value=0.0, max_value=100.0, value=float(def_sugar), step=1.0)
        protein_in = st.number_input("Protein (g):", min_value=0.0, max_value=100.0, value=float(def_protein), step=1.0)
        fat_in = st.number_input("Total Fat (g):", min_value=0.0, max_value=100.0, value=float(def_fat), step=1.0)

    # Compute Simulation
    nutr_test = NutritionFacts(
        carbohydrates=carbs_in,
        dietary_fiber=fiber_in,
        sugars=sugar_in,
        protein=protein_in,
        total_fat=fat_in
    )

    cgm_result = CgmGlucosePredictor.simulate_glucose_curve(
        nutrition=nutr_test,
        is_diabetic=is_diabetic,
        baseline_mg_dl=baseline_val
    )

    # Compute comparison curve for recommended safe swap
    swap_nutr = NutritionFacts(
        carbohydrates=max(5.0, carbs_in * 0.35),
        dietary_fiber=fiber_in + 8.0,
        sugars=max(1.0, sugar_in * 0.15),
        protein=protein_in + 10.0,
        total_fat=fat_in
    )
    swap_cgm_result = CgmGlucosePredictor.simulate_glucose_curve(
        nutrition=swap_nutr,
        is_diabetic=is_diabetic,
        baseline_mg_dl=baseline_val
    )

    with col_ctrl2:
        st.markdown(f"#### 📊 Trajectory: {active_prod.name if active_prod else 'Custom Nutritional Profile'}")

        # Metrics bar
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Peak Glucose", f"{cgm_result['peak_glucose']:.1f} mg/dL")
        with m2:
            st.metric("Spike Delta (ΔG)", f"+{cgm_result['delta_peak']:.1f} mg/dL")
        with m3:
            st.metric("Time to Peak", f"{cgm_result['time_to_peak_min']} min")
        with m4:
            st.metric("Glycemic Load", f"{cgm_result['glycemic_load']:.1f}")

        # Interactive Plotly Chart with Side-by-Side Safe Swap Curve
        render_cgm_trajectory_chart(
            curve_data=cgm_result["curve"],
            baseline_mg_dl=baseline_val,
            peak_glucose=cgm_result["peak_glucose"],
            title=f"CGM Trajectory Comparison: Product vs Safe Swap",
            swap_curve_data=swap_cgm_result["curve"],
            swap_name="Safe Alternative (High-Fiber Swap)"
        )

        st.caption(f"ℹ️ **Physiological Summary:** {cgm_result['summary']}")
