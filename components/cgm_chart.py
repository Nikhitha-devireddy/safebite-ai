"""
SafeBite AI - Interactive CGM (Continuous Glucose Monitor) Chart Component
Renders clinical blood glucose spike trajectories with dynamic risk zones
and optional side-by-side Safe Swap comparison curves using Plotly.
"""

import streamlit as st
from typing import List, Dict, Any, Optional

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def render_cgm_trajectory_chart(
    curve_data: List[Dict[str, Any]],
    baseline_mg_dl: float = 95.0,
    peak_glucose: float = 145.0,
    title: str = "180-Minute CGM Glycemic Trajectory",
    swap_curve_data: Optional[List[Dict[str, Any]]] = None,
    swap_name: Optional[str] = "Recommended Safe Swap"
):
    """
    Renders an interactive Plotly CGM trajectory curve with normal, caution,
    and spike danger thresholds.
    """
    if not PLOTLY_AVAILABLE or not curve_data:
        st.warning("CGM chart data unavailable or Plotly is not installed.")
        return

    times = [pt.get("time_min", 0) for pt in curve_data]
    glucose = [pt.get("glucose_mg_dl", baseline_mg_dl) for pt in curve_data]

    fig = go.Figure()

    # 1. Background Threshold Bands
    # Normal Range: 70 - 140 mg/dL (Green)
    fig.add_hrect(y0=70, y1=140, fillcolor="#ECFDF5", opacity=0.6, line_width=0, annotation_text="Target Range (<140 mg/dL)", annotation_position="top left", annotation_font_size=10, annotation_font_color="#047857")
    # Moderate Alert: 140 - 180 mg/dL (Amber)
    fig.add_hrect(y0=140, y1=180, fillcolor="#FFFBEB", opacity=0.6, line_width=0, annotation_text="Elevated (140-180 mg/dL)", annotation_position="top left", annotation_font_size=10, annotation_font_color="#B45309")
    # Critical Spike: > 180 mg/dL (Red)
    max_y = max(220, max(glucose) + 20)
    fig.add_hrect(y0=180, y1=max_y, fillcolor="#FEF2F2", opacity=0.5, line_width=0, annotation_text="Spike Danger (>180 mg/dL)", annotation_position="top left", annotation_font_size=10, annotation_font_color="#DC2626")

    # 2. Baseline line
    fig.add_hline(y=baseline_mg_dl, line_dash="dot", line_color="#94A3B8", annotation_text=f"Fasting Baseline ({baseline_mg_dl:.0f} mg/dL)", annotation_font_size=9)

    # 3. Main Product Trajectory
    line_color = "#DC2626" if peak_glucose > 180 else "#D97706" if peak_glucose > 140 else "#059669"
    fig.add_trace(go.Scatter(
        x=times,
        y=glucose,
        mode="lines+markers",
        name="Audited Product",
        line=dict(color=line_color, width=3.5),
        marker=dict(size=5, color=line_color),
        hovertemplate="Time: %{x} min<br>Glucose: <b>%{y:.1f} mg/dL</b><extra></extra>"
    ))

    # 4. Optional Safe Swap Curve for Side-by-Side Comparison
    if swap_curve_data:
        swap_times = [pt.get("time_min", 0) for pt in swap_curve_data]
        swap_glucose = [pt.get("glucose_mg_dl", baseline_mg_dl) for pt in swap_curve_data]
        fig.add_trace(go.Scatter(
            x=swap_times,
            y=swap_glucose,
            mode="lines+markers",
            name=f"🟢 {swap_name}",
            line=dict(color="#10B981", width=2.5, dash="dash"),
            marker=dict(size=4, color="#10B981"),
            hovertemplate="Time: %{x} min<br>Safe Swap: <b>%{y:.1f} mg/dL</b><extra></extra>"
        ))

    # Layout styling
    fig.update_layout(
        title=dict(text=title, font=dict(family="Plus Jakarta Sans", size=14, color="#0F172A")),
        xaxis=dict(title="Minutes Post-Prandial", dtick=30, range=[0, 185], gridcolor="#F1F5F9"),
        yaxis=dict(title="Glucose (mg/dL)", range=[65, max_y], gridcolor="#F1F5F9"),
        margin=dict(l=28, r=14, t=38, b=35),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=360
    )

    st.plotly_chart(fig, use_container_width=True, config={"responsive": True, "displayModeBar": False})
