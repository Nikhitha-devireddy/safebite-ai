"""
SafeBite AI - Reusable Sidebar Component
Handles Delivery Location, Health Parameters, Quick Presets, and Supabase Sync.
"""

import streamlit as st
from location_manager import LocationManager
from presets import HEALTH_PRESETS, get_all_presets, apply_preset_to_session
import supabase_client

def render_sidebar():
    """Renders the standard SafeBite AI sidebar and synchronizes session state."""
    with st.sidebar:
        st.markdown("### 🛡️ SafeBite AI")
        st.caption("Clinical Food Safety & Nutrition Platform")

        # 1. Supabase Cloud Status Indicator
        is_cloud_active = supabase_client.is_supabase_enabled()
        if is_cloud_active:
            st.markdown("""
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 6px 10px; margin-bottom: 12px; font-size: 0.78rem; color: #166534; display: flex; align-items: center; justify-content: space-between;">
                <span>🟢 <b>Cloud Connected</b> (Supabase)</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 6px 10px; margin-bottom: 12px; font-size: 0.78rem; color: #92400E;">
                <span>⚪ <b>Local Mode</b> (Session Only)</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # 2. Location Selector
        st.markdown("#### 📍 Delivery Location")
        saved_keys = list(LocationManager.SAVED_PROFILES.keys())
        saved_labels = [LocationManager.SAVED_PROFILES[k].label for k in saved_keys] + ["⚙️ Custom Address"]
        curr_loc_idx = 0
        active_loc_id = st.session_state.get("active_location_id", "home")
        if active_loc_id in saved_keys:
            curr_loc_idx = saved_keys.index(active_loc_id)

        if "sb_location_selector" not in st.session_state or st.session_state["sb_location_selector"] not in saved_labels:
            st.session_state["sb_location_selector"] = saved_labels[curr_loc_idx]

        sel_loc_label = st.selectbox(
            "Active Delivery Area:",
            saved_labels,
            key="sb_location_selector"
        )

        if sel_loc_label == "⚙️ Custom Address":
            st.session_state["active_location_id"] = "custom"
            loc_data = st.session_state.get("location_dict", {})
            c_country = st.selectbox("Country", ["India", "United States", "United Kingdom", "Canada", "Australia", "Global"], index=0, key="custom_c")
            c_state = st.text_input("State / Province", value=loc_data.get("state", "Karnataka"), key="custom_s")
            c_city = st.text_input("City / Town", value=loc_data.get("city", "Bengaluru"), key="custom_city")
            c_pin = st.text_input("Pincode / Postal Code", value=loc_data.get("pincode", "560001"), key="custom_pin")
            c_addr = st.text_input("Street Address", value=loc_data.get("address", "12 Indiranagar 100ft Rd"), key="custom_addr")
            st.session_state["location_dict"] = {
                "country": c_country, "state": c_state, "city": c_city, "pincode": c_pin, "address": c_addr
            }
        else:
            chosen_key = saved_keys[saved_labels.index(sel_loc_label)]
            st.session_state["active_location_id"] = chosen_key
            prof = LocationManager.SAVED_PROFILES[chosen_key]
            st.session_state["location_dict"] = prof.model_dump()
            st.caption(f"Targeting: **{prof.city}, {prof.country}** ({prof.pincode})")

        st.markdown("---")

        # 3. 1-Click Clinical Preset Loader
        st.markdown("#### ⚡ 1-Click Health Presets")
        preset_list = list(HEALTH_PRESETS.keys())
        preset_labels = ["-- Select Preset --"] + [f"{HEALTH_PRESETS[k].icon} {HEALTH_PRESETS[k].name}" for k in preset_list]
        selected_p = st.selectbox("Quick Apply Clinical Preset:", preset_labels, key="sidebar_preset_sel")
        if selected_p != "-- Select Preset --":
            chosen_p_idx = preset_labels.index(selected_p) - 1
            chosen_p_key = preset_list[chosen_p_idx]
            if st.button("Apply Preset Now", key="btn_apply_preset_sidebar"):
                apply_preset_to_session(chosen_p_key)
                st.success(f"Applied: {HEALTH_PRESETS[chosen_p_key].name}")
                st.rerun()

        st.markdown("---")

        # 4. Health Parameters & User Profile
        st.markdown("#### 👤 Health Parameters")
        if "input_user_name" not in st.session_state:
            st.session_state["input_user_name"] = st.session_state.get("user_name", "Alex")
        prof_name = st.text_input("User Name", key="input_user_name")
        st.session_state["user_name"] = prof_name

        if "input_medical_history" not in st.session_state:
            st.session_state["input_medical_history"] = st.session_state.get("medical_history", "Type 2 Diabetes (Strict No Added Sugar / Low Glycemic)")
        prof_med = st.text_area(
            "Medical Conditions / Chronic History",
            help="e.g. Type 2 Diabetes, Hypertension (Low Sodium <= 140mg), Celiac Disease...",
            key="input_medical_history",
            height=70
        )
        st.session_state["medical_history"] = prof_med

        # Food Allergies
        st.markdown("##### 🚫 Food Allergies")
        common_allergens = ["Peanuts", "Tree Nuts", "Dairy", "Gluten", "Soy", "Eggs", "Shellfish", "Fish", "Sesame", "Mustard"]
        current_allergies = [a.strip() for a in st.session_state.get("allergies_list", []) if a.strip()]
        sel_allergens = []

        col_a1, col_a2 = st.columns(2)
        for i, alg in enumerate(common_allergens):
            col = col_a1 if i % 2 == 0 else col_a2
            chk_key = f"chk_alg_{alg}"
            if chk_key not in st.session_state:
                st.session_state[chk_key] = any(alg.lower() in ca.lower() for ca in current_allergies)
            if col.checkbox(alg, key=chk_key):
                sel_allergens.append(alg)

        if "input_custom_allergies" not in st.session_state:
            st.session_state["input_custom_allergies"] = ", ".join([ca for ca in current_allergies if not any(alg.lower() in ca.lower() for alg in common_allergens)])
        custom_alg_str = st.text_input("Other Allergies (comma-separated):", key="input_custom_allergies")
        if custom_alg_str.strip():
            for extra in custom_alg_str.split(","):
                if extra.strip() and extra.strip() not in sel_allergens:
                    sel_allergens.append(extra.strip())

        st.session_state["allergies_list"] = sel_allergens

        if "input_food_preferences" not in st.session_state:
            st.session_state["input_food_preferences"] = st.session_state.get("food_preferences", "Clean Label, Plant-Based")
        prof_pref = st.text_input("Dietary Preferences", placeholder="e.g. Vegan, Jain, Halal, Clean Label...", key="input_food_preferences")
        st.session_state["food_preferences"] = prof_pref

        # Cloud Save Button
        if is_cloud_active:
            if st.button("💾 Save Profile to Supabase", key="btn_sync_profile_cloud"):
                saved = supabase_client.save_user_profile(
                    user_id=prof_name.lower().replace(" ", "_"),
                    profile_data={
                        "user_name": prof_name,
                        "medical_history": prof_med,
                        "allergies_list": sel_allergens,
                        "food_preferences": prof_pref
                    }
                )
                if saved:
                    st.success("✅ Profile synced to Supabase!")
                else:
                    st.info("Saved locally. Supabase tables pending initialization.")

        st.markdown("---")
        st.caption("SafeBite AI v2.0 · Modular Edition")
