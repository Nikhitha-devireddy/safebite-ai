"""
SafeBite AI - Multimodal OCR & Nutrition Vision Engine
Extracts nutrition facts, ingredient lists, and allergen declarations from packaging photos.
Flow:
IMAGE -> VALIDATION -> VISION EXTRACTION -> DETERMINISTIC EXTRACTION -> NORMALIZATION -> CLINICAL AUDIT
Guarantees a predictable, typed OcrAnalysisResult object without undefined variable bugs.
"""

import io
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from PIL import Image

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    Evidence, SourceConfidence, ProductSafetyRequest, ClinicalStatus
)
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer
from clinical_engine import ClinicalRuleEngine
from llm_service import generate_clinical_assessment
from config import Config

class OcrAnalysisResult(BaseModel):
    """Predictable result schema for multimodal label analysis."""
    success: bool = Field(default=False)
    raw_text: str = Field(default="")
    product_name: str = Field(default="Uploaded Product Label")
    brand: str = Field(default="Audited Brand")
    nutrition: Optional[NutritionFacts] = None
    ingredients: Optional[Ingredients] = None
    allergens: Optional[Allergens] = None
    verdict: str = Field(default="UNABLE TO ASSESS")
    reasons: List[str] = Field(default_factory=list)
    provider_used: str = Field(default="SafeBite Multimodal OCR Engine")
    scrape_reason: str = Field(default="")
    final_output: str = Field(default="")
    confidence: SourceConfidence = Field(default=SourceConfidence.UNVERIFIED)
    error_message: Optional[str] = None

class OcrEngine:
    """
    Multimodal packaging and label OCR engine with deterministic clinical reasoning.
    """

    @classmethod
    def validate_image(cls, image_bytes: bytes) -> Tuple[bool, str]:
        """Validates image integrity and format before attempting inference."""
        if not image_bytes or len(image_bytes) < 100:
            return False, "Uploaded image file is empty or corrupted."
        if len(image_bytes) > 15 * 1024 * 1024:
            return False, "Image size exceeds 15MB limit. Please upload a compressed photo."
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            return True, "Valid image format."
        except Exception as e:
            return False, f"Could not decode image file ({str(e)})."

    @classmethod
    def analyze_label_image(
        cls,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        user_name: str = "User",
        medical_history: str = "",
        allergies: Optional[List[str]] = None,
        food_preferences: str = ""
    ) -> OcrAnalysisResult:
        """
        Executes complete packaging analysis flow:
        Image -> Validation -> Vision OCR -> Deterministic Extraction -> Clinical Rule Engine.
        Always returns a structured OcrAnalysisResult object.
        """
        allergies = allergies or []
        is_valid, val_msg = cls.validate_image(image_bytes)
        if not is_valid:
            return OcrAnalysisResult(
                success=False,
                verdict="UNABLE TO ASSESS",
                reasons=[f"Label photo validation failed: {val_msg}"],
                scrape_reason=f"Photo could not be processed: {val_msg}",
                final_output=f"### ⚠️ Could Not Read Product Image\n\n{val_msg}\n\nPlease upload a clear, high-resolution photo of the ingredients or nutrition label.",
                error_message=val_msg
            )

        allergies_str = ", ".join(allergies) if allergies else "None specified"
        pref_str = food_preferences if food_preferences else "None specified"

        vision_prompt = f"""
        You are a clinical food safety and nutrition extraction specialist.
        Transcribe the text on this product label photo with extreme accuracy.

        REQUIRED EXTRACTION SECTIONS:
        1. **Product & Brand**: Identify the brand and product title.
        2. **Ingredient Declaration**: Transcribe every single visible ingredient verbatim.
        3. **Nutrition Facts Table**: Transcribe serving size, calories, total sugar, added sugar, protein, total fat, saturated fat, sodium, fiber.
        4. **Allergens & Traces**: Transcribe any 'Contains:' or 'May Contain:' or 'Manufactured on equipment...' statements.

        IMPORTANT SAFETY RULE:
        - If the photo is too blurry, dark, low resolution, or does NOT contain readable ingredients/nutrition, state:
          `VERDICT: UNABLE TO ASSESS`
          followed by: "The uploaded photo does not clearly show the ingredient list or nutrition panel. Please upload a clear, well-lit photo."
        """

        try:
            from google.genai import types
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        except Exception:
            image_part = None

        try:
            report_text, provider_info = generate_clinical_assessment(vision_prompt, image_part)
        except Exception as e:
            return OcrAnalysisResult(
                success=False,
                raw_text="",
                verdict="UNABLE TO ASSESS",
                reasons=[f"Vision model inference unavailable: {str(e)}"],
                provider_used="SafeBite Vision Guardrail",
                scrape_reason="Vision model inference unavailable. Please ensure GOOGLE_API_KEY is configured in your environment or Streamlit Secrets.",
                final_output=f"### ⚠️ Multimodal Vision Engine Unavailable\n\nCould not connect to vision intelligence provider: {e}\n\nPlease verify your `GOOGLE_API_KEY` is configured in Streamlit secrets or switch to **📝 Paste Ingredients List** to perform deterministic clinical audits offline.",
                error_message=str(e),
                confidence=SourceConfidence.UNVERIFIED
            )

        # Check if vision model flagged label as unreadable
        if "VERDICT: UNABLE TO ASSESS" in report_text.upper():
            return OcrAnalysisResult(
                success=False,
                raw_text=report_text,
                verdict="UNABLE TO ASSESS",
                reasons=["The uploaded image could not be reliably transcribed or did not show readable ingredient text."],
                provider_used=provider_info,
                scrape_reason="The label image was blurry, low-resolution, or did not display a readable ingredients or nutrition facts section.",
                final_output=report_text,
                confidence=SourceConfidence.UNVERIFIED
            )

        # Deterministically parse nutrition and ingredients from transcribed OCR text
        parsed_nut, parsed_ing, parsed_allg = NutritionExtractor.extract_from_text(
            report_text,
            source_name="Product Label Photo (Multimodal OCR)"
        )

        # Create canonical product model
        prod_id = ProductNormalizer.generate_product_id("Label", "Uploaded Product")
        product = Product(
            id=prod_id,
            name="Uploaded Product Label",
            brand="Audited Brand",
            nutrition=parsed_nut,
            ingredients=parsed_ing,
            allergens=parsed_allg,
            evidence=Evidence(
                manufacturer_verified=True,
                sources_consulted=["Direct Product Packaging Photo"],
                overall_confidence=SourceConfidence.HIGH if parsed_ing.raw_text else SourceConfidence.MEDIUM,
                last_verified="Just now"
            )
        )

        # Evaluate clinical rules deterministically
        overall_status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=product,
            user_medical_history=medical_history,
            user_allergies=allergies,
            food_preferences=food_preferences
        )
        product.clinical_assessments = assessments

        # Map status to verdict string
        if overall_status == ClinicalStatus.AVOID:
            verdict = "UNSAFE"
        elif overall_status == ClinicalStatus.CAUTION:
            verdict = "PARTIALLY SAFE"
        elif overall_status == ClinicalStatus.UNKNOWN:
            verdict = "UNABLE TO ASSESS"
        else:
            verdict = "SAFE"

        return OcrAnalysisResult(
            success=True,
            raw_text=report_text,
            product_name=product.name,
            brand=product.brand,
            nutrition=parsed_nut,
            ingredients=parsed_ing,
            allergens=parsed_allg,
            verdict=verdict,
            reasons=reasons,
            provider_used=provider_info,
            scrape_reason="Product label successfully transcribed and clinically analyzed.",
            final_output=report_text,
            confidence=SourceConfidence.HIGH if parsed_nut.calories is not None else SourceConfidence.MEDIUM
        )
