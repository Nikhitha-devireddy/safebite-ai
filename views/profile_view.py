"""
SafeBite AI - Health Profile & Medical Parameters View
Allows configuring chronic conditions, allergen exclusions, cultural rules,
and persistent cloud synchronization via Supabase PostgreSQL.
"""

import streamlit as st
from presets import HEALTH_PRESETS, get_all_presets, get_indian_presets, apply_preset_to_session
import supabase_client

def render_profile_view():
    """Renders the comprehensive user health profile interface."""
    st.subheader("👤 Personal Health & Medical Safety Profile")
    st.markdown("Configure your medical conditions, strict allergen triggers, and cultural dietary guardrails. All clinical rules strictly adhere to these parameters.")

    # Supabase Sync Panel
    is_cloud = supabase_client.is_supabase_enabled()
    with st.expander("☁️ Supabase Cloud Synchronization & Persistence", expanded=True):
        if is_cloud:
            st.success("🟢 Supabase Cloud Connection Active (`https://hwdteshkgrssiicehstn.supabase.co`)")
            col_sync1, col_sync2 = st.columns(2)
            with col_sync1:
                if st.button("📥 Load Profile from Supabase", key="btn_load_cloud_profile"):
                    u_id = st.session_state.get("user_name", "user").lower().replace(" ", "_")
                    remote_prof = supabase_client.get_user_profile(u_id)
                    if remote_prof:
                        st.session_state["user_name"] = remote_prof.get("user_name", "Alex")
                        st.session_state["medical_history"] = remote_prof.get("medical_history", "")
                        st.session_state["allergies_list"] = remote_prof.get("allergies", [])
                        st.session_state["food_preferences"] = remote_prof.get("food_preferences", "")
                        st.success("✅ Profile loaded from Supabase!")
                        st.rerun()
                    else:
                        st.info(f"No profile found in Supabase for user ID '{u_id}'. Save your current profile below.")
            with col_sync2:
                if st.button("💾 Save Profile to Supabase", key="btn_save_cloud_profile"):
                    u_id = st.session_state.get("user_name", "user").lower().replace(" ", "_")
                    saved = supabase_client.save_user_profile(
                        user_id=u_id,
                        profile_data={
                            "user_name": st.session_state.get("user_name", "Alex"),
                            "medical_history": st.session_state.get("medical_history", ""),
                            "allergies_list": st.session_state.get("allergies_list", []),
                            "food_preferences": st.session_state.get("food_preferences", "")
                        }
                    )
                    if saved:
                        st.success("✅ Profile saved to Supabase `user_profiles` table!")
                    else:
                        st.warning("⚠️ Could not save to Supabase. Check if schema tables are created.")
        else:
            st.info("ℹ️ Supabase not configured. User profile is stored in local session memory.")

    st.markdown("---")

    # Clinical Preset Quick Selector
    st.markdown("### ⚡ Apply Clinical Preset")
    all_presets = get_all_presets() + get_indian_presets()
    preset_dict = {f"{p.icon} {p.name}": p for p in all_presets}
    chosen_preset_label = st.selectbox("Choose a Preset to Auto-Configure:", ["-- Select --"] + list(preset_dict.keys()), key="profile_preset_select")
    if chosen_preset_label != "-- Select --":
        p_obj = preset_dict[chosen_preset_label]
        st.info(f"**{p_obj.name}**: {p_obj.tagline}")
        if st.button("Apply Selected Preset", key="btn_apply_profile_preset"):
            apply_preset_to_session(p_obj.id)
            st.success(f"Configured profile as: {p_obj.name}")
            st.rerun()

    st.markdown("---")

    # Form Fields
    st.markdown("### 📝 Detailed Medical & Dietary Form")
    u_name = st.text_input("Full Name:", value=st.session_state.get("user_name", "Alex"), key="prof_name_input")
    st.session_state["user_name"] = u_name

    u_med = st.text_area(
        "Medical Conditions / Chronic Diseases:",
        value=st.session_state.get("medical_history", "Type 2 Diabetes (Strict No Added Sugar / Low Glycemic)"),
        help="e.g. Type 2 Diabetes, Hypertension (Low Sodium <= 140mg), Celiac Disease, Chronic Kidney Disease (CKD)",
        height=90,
        key="prof_med_input"
    )
    st.session_state["medical_history"] = u_med

    # Allergies Checklist
    st.markdown("#### 🚫 Strict Allergens (Zero Tolerance)")
    common_allergens = ["Peanuts", "Tree Nuts", "Dairy", "Gluten", "Soy", "Eggs", "Shellfish", "Fish", "Sesame", "Mustard"]
    curr_algs = st.session_state.get("allergies_list", [])
    sel_algs = []

    col_al1, col_al2 = st.columns(2)
    for i, a in enumerate(common_allergens):
        col = col_al1 if i % 2 == 0 else col_al2
        is_checked = any(a.lower() in ca.lower() for ca in curr_algs)
        if col.checkbox(a, value=is_checked, key=f"prof_chk_{a}"):
            sel_algs.append(a)

    extra_algs = st.text_input("Additional Allergies (comma-separated):", key="prof_extra_algs")
    if extra_algs.strip():
        for item in extra_algs.split(","):
            if item.strip() and item.strip() not in sel_algs:
                sel_algs.append(item.strip())

    st.session_state["allergies_list"] = sel_algs

    u_pref = st.text_input("Dietary Preferences / Philosophy:", value=st.session_state.get("food_preferences", "Clean Label, Plant-Based"), key="prof_pref_input")
    st.session_state["food_preferences"] = u_pref
