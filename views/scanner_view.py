"""
SafeBite AI - Live Scanner & Product Inspection View
Supports:
1. Live Camera Scanner (Direct Packaging OCR)
2. Photo Upload (Gemini Vision OCR + Supabase Storage)
3. Barcode Lookup (Open Food Facts + Retail Inventory)
4. Product Web URL Inspector
5. Paste Ingredients Text
6. Voice Query Assistant
"""

import os
import re
import streamlit as st
from typing import Optional
from schemas import Product, Evidence, SourceConfidence, ClinicalStatus
from product_sources import ProductSources
from ocr_engine import OcrEngine
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer
from clinical_engine import ClinicalRuleEngine
from components.cards import render_verdict_badge
import supabase_client

def record_to_history(product: Product, input_mode: str):
    """Helper to record product to session and Supabase history."""
    if "recent_history" not in st.session_state:
        st.session_state["recent_history"] = []

    history_entry = {
        "timestamp": "Just now",
        "product_id": product.id,
        "name": product.name,
        "brand": product.brand,
        "verdict": product.health_safety_verdict or "NOT VERIFIED",
        "input_mode": input_mode,
        "confidence": product.evidence.overall_confidence.value if (product.evidence and product.evidence.overall_confidence) else "UNVERIFIED",
        "product_obj": product
    }
    st.session_state["recent_history"] = [
        h for h in st.session_state["recent_history"] if h["product_id"] != product.id
    ]
    st.session_state["recent_history"].insert(0, history_entry)

    # Persist to Supabase if connected
    if supabase_client.is_supabase_enabled():
        supabase_client.save_scan_history({
            "user_id": st.session_state.get("user_name", "user").lower().replace(" ", "_"),
            "product_id": product.id,
            "name": product.name,
            "brand": product.brand,
            "verdict": product.health_safety_verdict or "UNKNOWN",
            "confidence": history_entry["confidence"],
            "input_mode": input_mode,
            "ingredients": product.ingredients.raw_text if product.ingredients else "",
            "clinical_reasons": product.health_safety_reasons or []
        })


def render_scanner_view(product_sources: ProductSources):
    """Renders the multi-mode scanner interface."""
    st.subheader("🛡️ Product Safety & Clinical Allergen Audit Lab")
    st.markdown("Inspect any food or beverage item through live camera, label photo upload, barcode lookup, or direct ingredient text.")

    check_mode = st.radio(
        "Choose Inspection Method:",
        [
            "📷 Live Camera Scanner",
            "📸 Upload Label Photo",
            "🔢 Barcode Lookup",
            "🌐 Product URL (Auto-Inspection)",
            "📝 Paste Ingredients List",
            "🎙️ Voice Query Assistant"
        ],
        horizontal=True,
        key="inspect_method_radio"
    )

    checked_product: Optional[Product] = None

    # MODE 1: LIVE CAMERA SCANNER
    if "📷 Live Camera" in check_mode:
        st.markdown("##### 📷 Point Camera at Food Packaging (Ingredients or Nutrition Table)")
        cam_photo = st.camera_input("Capture Label via Camera", key="cam_scanner_input")
        if cam_photo is not None:
            image_bytes = cam_photo.getvalue()
            with st.spinner("Analyzing camera frame with Multimodal Vision OCR..."):
                # Optional: Upload to Supabase Storage
                img_url = None
                if supabase_client.is_supabase_enabled():
                    img_url = supabase_client.upload_label_scan(image_bytes, filename=f"camera_{cam_photo.name}")

                ocr_result = OcrEngine.analyze_image_bytes(
                    image_bytes=image_bytes,
                    user_name=st.session_state.get("user_name", "User"),
                    medical_history=st.session_state.get("medical_history", ""),
                    allergies=st.session_state.get("allergies_list", []),
                    food_preferences=st.session_state.get("food_preferences", "")
                )

                if ocr_result and (ocr_result.ingredients_text or ocr_result.raw_text):
                    p_id = ProductNormalizer.generate_product_id(ocr_result.brand or "Live", ocr_result.product_name or "CameraScan")
                    checked_product = Product(
                        id=p_id,
                        name=ocr_result.product_name or "Live Scanned Product",
                        brand=ocr_result.brand or "Packaging Label",
                        nutrition=ocr_result.nutrition_facts,
                        ingredients=ocr_result.ingredients,
                        allergens=ocr_result.allergens,
                        evidence=Evidence(
                            manufacturer_verified=True,
                            sources_consulted=["Live Packaging Camera OCR"],
                            overall_confidence=SourceConfidence.HIGH if ocr_result.confidence > 0.8 else SourceConfidence.MEDIUM,
                            last_verified="Just now"
                        )
                    )
                    verdict, assessments, reasons = ClinicalRuleEngine.evaluate(
                        product=checked_product,
                        user_medical_history=st.session_state.get("medical_history", ""),
                        user_allergies=st.session_state.get("allergies_list", []),
                        food_preferences=st.session_state.get("food_preferences", "")
                    )
                    checked_product.clinical_assessments = assessments
                    checked_product.health_safety_reasons = reasons
                    checked_product.health_safety_verdict = verdict.value if hasattr(verdict, "value") else str(verdict)
                    record_to_history(checked_product, "Live Camera OCR")
                    st.session_state["active_product_detail"] = checked_product
                    st.success(f"Scanned: {checked_product.name}")
                else:
                    st.warning("Could not read text clearly from camera. Ensure proper lighting and focus on the ingredient panel.")

    # MODE 2: UPLOAD LABEL PHOTO
    elif "📸 Upload Label" in check_mode:
        uploaded_file = st.file_uploader("Upload front or back packaging label (JPG/PNG):", type=["jpg", "jpeg", "png"], key="upload_label_input")
        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
            st.image(image_bytes, caption="Uploaded Packaging Image", width=280)
            if st.button("Extract & Run Clinical Audit", type="primary", key="btn_audit_upload"):
                with st.spinner("Executing Multimodal OCR and clinical rule evaluation..."):
                    img_url = None
                    if supabase_client.is_supabase_enabled():
                        img_url = supabase_client.upload_label_scan(image_bytes, filename=f"upload_{uploaded_file.name}")

                    ocr_result = OcrEngine.analyze_image_bytes(
                        image_bytes=image_bytes,
                        user_name=st.session_state.get("user_name", "User"),
                        medical_history=st.session_state.get("medical_history", ""),
                        allergies=st.session_state.get("allergies_list", []),
                        food_preferences=st.session_state.get("food_preferences", "")
                    )

                    if ocr_result and (ocr_result.ingredients_text or ocr_result.raw_text):

                        p_id = ProductNormalizer.generate_product_id(ocr_result.brand or "Label", ocr_result.product_name or "UploadedScan")
                        checked_product = Product(
                            id=p_id,
                            name=ocr_result.product_name or "Scanned Product",
                            brand=ocr_result.brand or "Packaging Label",
                            nutrition=ocr_result.nutrition_facts,
                            ingredients=ocr_result.ingredients,
                            allergens=ocr_result.allergens,
                            evidence=Evidence(
                                manufacturer_verified=True,
                                sources_consulted=["Packaging Label OCR"],
                                overall_confidence=SourceConfidence.HIGH,
                                last_verified="Just now"
                            )
                        )
                        verdict, assessments, reasons = ClinicalRuleEngine.evaluate(
                            product=checked_product,
                            user_medical_history=st.session_state.get("medical_history", ""),
                            user_allergies=st.session_state.get("allergies_list", []),
                            food_preferences=st.session_state.get("food_preferences", "")
                        )
                        checked_product.clinical_assessments = assessments
                        checked_product.health_safety_reasons = reasons
                        checked_product.health_safety_verdict = verdict.value if hasattr(verdict, "value") else str(verdict)
                        record_to_history(checked_product, "Uploaded Photo OCR")
                        st.session_state["active_product_detail"] = checked_product
                        st.success(f"Analyzed: {checked_product.name}")
                    else:
                        st.error("Failed to detect clear ingredient text. Please try a higher-resolution photo.")

    # MODE 3: BARCODE LOOKUP
    elif "🔢 Barcode" in check_mode:
        bc_col1, bc_col2 = st.columns([3, 1])
        with bc_col1:
            barcode_input = st.text_input("Enter 8, 12, or 13-digit EAN/UPC Barcode:", placeholder="e.g. 737628064502 or 8901030383152", key="barcode_lookup_input")
        with bc_col2:
            st.write("")
            st.write("")
            btn_bc = st.button("Lookup Barcode", type="primary", use_container_width=True, key="btn_lookup_bc")

        if btn_bc and barcode_input.strip():
            with st.spinner(f"Querying Open Food Facts & retail repositories for barcode {barcode_input.strip()}..."):
                checked_product = product_sources.fetch_by_barcode(
                    barcode=barcode_input.strip(),
                    user_medical_history=st.session_state.get("medical_history", ""),
                    user_allergies=st.session_state.get("allergies_list", []),
                    location=st.session_state.get("location_dict", {}).get("city", "Bengaluru"),
                    food_preferences=st.session_state.get("food_preferences", "")
                )
                if checked_product:
                    record_to_history(checked_product, "Barcode Lookup")
                    st.session_state["active_product_detail"] = checked_product
                    st.success(f"Found product: {checked_product.name} ({checked_product.brand})")
                else:
                    st.warning(f"Barcode '{barcode_input.strip()}' not found in verified lab databases.")

    # MODE 4: PRODUCT URL
    elif "🌐 Product URL" in check_mode:
        url_input = st.text_input("Enter product web page URL:", placeholder="https://world.openfoodfacts.org/product/...", key="url_check_input")
        if st.button("Audit URL Content Now", type="primary", key="btn_audit_url"):
            clean_url = url_input.strip()
            if clean_url:
                if not clean_url.startswith(("http://", "https://")):
                    clean_url = "https://" + clean_url
                with st.spinner("Inspecting product webpage and extracting JSON-LD schema..."):
                    checked_product = product_sources.fetch_by_url(
                        url=clean_url,
                        user_medical_history=st.session_state.get("medical_history", ""),
                        user_allergies=st.session_state.get("allergies_list", []),
                        location=st.session_state.get("location_dict", {}).get("city", "Bengaluru"),
                        food_preferences=st.session_state.get("food_preferences", "")
                    )
                    if checked_product:
                        record_to_history(checked_product, "Product URL")
                        st.session_state["active_product_detail"] = checked_product
                        st.success(f"Audited: {checked_product.name}")
                    else:
                        st.error("Could not extract ingredient data from this URL. Use 'Paste Ingredients List' instead.")

    # MODE 5: PASTE INGREDIENTS
    elif "📝 Paste Ingredients" in check_mode:
        prod_title_input = st.text_input("Product Title / Brand Name:", value="Custom Food Item", key="paste_title_input")
        paste_text = st.text_area("Paste Ingredient Declaration:", placeholder="Ingredients: Wheat flour, sugar, palm oil, whey...", height=120, key="paste_ing_input")
        if st.button("Run Deterministic Clinical Audit", type="primary", key="btn_audit_paste"):
            if paste_text.strip():
                with st.spinner("Evaluating ingredients, hidden derivatives, and clinical rules..."):
                    p_nut, p_ing, p_allg = NutritionExtractor.extract_from_text(paste_text.strip(), source_name="Pasted Panel")
                    p_id = ProductNormalizer.generate_product_id("User", prod_title_input)
                    checked_product = Product(
                        id=p_id,
                        name=prod_title_input.title(),
                        brand="Audited Packaging",
                        nutrition=p_nut,
                        ingredients=p_ing,
                        allergens=p_allg,
                        evidence=Evidence(
                            manufacturer_verified=True,
                            sources_consulted=["User-Provided Ingredient Declaration"],
                            overall_confidence=SourceConfidence.HIGH,
                            last_verified="Just now"
                        )
                    )
                    verdict, assessments, reasons = ClinicalRuleEngine.evaluate(
                        product=checked_product,
                        user_medical_history=st.session_state.get("medical_history", ""),
                        user_allergies=st.session_state.get("allergies_list", []),
                        food_preferences=st.session_state.get("food_preferences", "")
                    )
                    checked_product.clinical_assessments = assessments
                    checked_product.health_safety_reasons = reasons
                    checked_product.health_safety_verdict = verdict.value if hasattr(verdict, "value") else str(verdict)
                    record_to_history(checked_product, "Paste Ingredients")
                    st.session_state["active_product_detail"] = checked_product
                    st.success(f"Audit completed: {checked_product.name}")

    # MODE 6: VOICE QUERY ASSISTANT
    else:
        st.markdown("##### 🎙️ Hands-Free Natural Voice Assistant")
        voice_query = st.text_input("Speak or Type Question:", placeholder="e.g. 'Can I eat Haldiram Bhujia with Hypertension?'", key="voice_query_text")
        if st.button("Ask SafeBite Assistant ➔", type="primary", key="btn_run_voice") and voice_query.strip():
            clean_q = re.sub(r"(?i)^(can i eat|is|check if|does)\s*", "", voice_query).replace("safe", "").strip()
            with st.spinner(f"Analyzing '{clean_q}'..."):
                target_prod = product_sources.fetch_by_query(
                    query=clean_q,
                    user_medical_history=st.session_state.get("medical_history", ""),
                    user_allergies=st.session_state.get("allergies_list", []),
                    location=st.session_state.get("location_dict", {}).get("city", "Bengaluru"),
                    food_preferences=st.session_state.get("food_preferences", "")
                )
                if target_prod:
                    record_to_history(target_prod, "Voice Query Assistant")
                    st.session_state["active_product_detail"] = target_prod
                    st.success(f"Assistant Verdict: {target_prod.health_safety_verdict}")
                else:
                    st.warning("Could not find product matching voice query.")

    # Active Product Guidance Banner
    active_p = st.session_state.get("active_product_detail")
    if active_p:
        portion = getattr(active_p, "recommended_portion", None)
        if not portion:
            portion = ClinicalRuleEngine.calculate_recommended_portion(
                active_p,
                st.session_state.get("medical_history", ""),
                ClinicalStatus.CLEAR
            )
            active_p.recommended_portion = portion

        p_limit = portion.get("portion_limit", "1 Standard Serving")
        p_action = portion.get("action", "Clinical Guidance")
        p_rat = portion.get("rationale", "")
        p_badge_color = portion.get("badge_color", "#059669")

        st.markdown(f"""
        <div style="background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 10px; padding: 16px 20px; margin-top: 18px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom: 8px;">
                <div style="font-size: 1.05rem; font-weight: 800; color: #14532D;">
                    👉 Active Audit: {active_p.name}
                </div>
                <div style="background: {p_badge_color}; color: white; padding: 3px 12px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase;">
                    {p_action}
                </div>
            </div>
            <div style="font-size: 0.95rem; color: #166534; font-weight: 600; margin-bottom: 4px;">
                ⚖️ Recommended Quantity for Your Medical History: <span style="background: white; padding: 2px 8px; border-radius: 4px; border: 1px solid #BBF7D0; color: #0F172A;">{p_limit}</span>
            </div>
            <div style="font-size: 0.86rem; color: #374151; margin-bottom: 8px; line-height: 1.45;">
                <em>{p_rat}</em>
            </div>
            <div style="font-size: 0.82rem; color: #059669; font-weight: 600;">
                Navigate to <strong>🩺 Clinical Audit</strong> for comprehensive analysis or <strong>📈 CGM Simulator</strong> for glycemic spike forecasts.
            </div>
        </div>
        """, unsafe_allow_html=True)

