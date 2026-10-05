"""
SafeBite AI - Headless REST API
Exposes the deterministic clinical safety engines, OCR extraction,
CGM glucose simulation, and smart food swaps to external clients
(Mobile apps, Chrome extensions, third-party integrations).
"""

import os
import io
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Core SafeBite Engines
from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    ClinicalStatus, Evidence, SourceConfidence
)
from clinical_engine import ClinicalRuleEngine
from allergen_engine import AllergenEngine
from indian_engine import (
    FssaiComplianceEngine,
    IndianDietaryGuardrail,
    AyurvedicEngine
)
from cgm_simulator import (
    CgmGlucosePredictor,
    NovaProcessingScorer,
    SmartSafeSwapEngine
)
from nutrition_extractor import NutritionExtractor
from ocr_engine import OcrEngine
from recommendations import recommend_safe_products
import supabase_client

app = FastAPI(
    title="SafeBite AI — Headless Clinical Food Safety API",
    description="Autonomous clinical food intelligence: deterministic safety audits, CGM simulation, multimodal OCR, and safe product swaps.",
    version="2.0.0"
)

# Enable CORS for Chrome extensions, mobile frontends, and external web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# Request & Response Models
# =========================================================================

class NutritionInput(BaseModel):
    calories: Optional[float] = 0.0
    carbohydrates_g: Optional[float] = 0.0
    added_sugars_g: Optional[float] = 0.0
    fiber_g: Optional[float] = 0.0
    protein_g: Optional[float] = 0.0
    total_fat_g: Optional[float] = 0.0
    saturated_fat_g: Optional[float] = 0.0
    trans_fat_g: Optional[float] = 0.0
    sodium_mg: Optional[float] = 0.0
    serving_size_g: Optional[float] = 100.0


class AuditRequest(BaseModel):
    product_name: str
    brand: Optional[str] = ""
    ingredients_text: Optional[str] = ""
    nutrition: Optional[NutritionInput] = None
    barcode: Optional[str] = None
    user_id: Optional[str] = "default_user"
    medical_history: Optional[str] = "Type 2 Diabetes (Strict No Added Sugar)"
    allergies: Optional[List[str]] = Field(default_factory=list)
    dietary_preferences: Optional[str] = ""
    save_to_history: Optional[bool] = True


class CgmRequest(BaseModel):
    carbohydrates_g: float
    fiber_g: Optional[float] = 0.0
    added_sugars_g: Optional[float] = 0.0
    protein_g: Optional[float] = 0.0
    fat_g: Optional[float] = 0.0
    baseline_glucose: Optional[float] = 95.0
    glycemic_index: Optional[float] = None
    duration_mins: Optional[int] = 180


class SwapRequest(BaseModel):
    category: Optional[str] = "snacks"
    avoid_allergens: Optional[List[str]] = Field(default_factory=list)
    max_sugar_g: Optional[float] = 5.0
    max_sodium_mg: Optional[float] = 140.0
    medical_condition: Optional[str] = "Diabetes"


# =========================================================================
# API Endpoints
# =========================================================================

@app.get("/")
def root():
    return {
        "service": "SafeBite AI Clinical Intelligence API",
        "version": "2.0.0",
        "documentation": "/docs",
        "endpoints": [
            "/api/v1/audit",
            "/api/v1/ocr",
            "/api/v1/cgm/simulate",
            "/api/v1/swaps",
            "/api/v1/health"
        ]
    }


@app.get("/api/v1/health")
def health_check():
    supabase_status = supabase_client.test_supabase_connection()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "engines": {
            "clinical_engine": "ready",
            "allergen_engine": "ready",
            "indian_fssai_engine": "ready",
            "cgm_predictor": "ready",
            "ocr_engine": "ready"
        },
        "supabase": supabase_status
    }


@app.post("/api/v1/audit")
def audit_product(req: AuditRequest):
    """
    Performs a deterministic clinical safety audit against the product's nutrition,
    ingredients, and chemical derivatives based on the user's medical history and allergies.
    """
    nutr_data = req.nutrition.model_dump() if req.nutrition else {}
    nutrition_obj = NutritionFacts(
        calories=nutr_data.get("calories", 0.0),
        carbs_g=nutr_data.get("carbohydrates_g", 0.0),
        sugar_g=nutr_data.get("added_sugars_g", 0.0),
        fiber_g=nutr_data.get("fiber_g", 0.0),
        protein_g=nutr_data.get("protein_g", 0.0),
        fat_g=nutr_data.get("total_fat_g", 0.0),
        saturated_fat_g=nutr_data.get("saturated_fat_g", 0.0),
        trans_fat_g=nutr_data.get("trans_fat_g", 0.0),
        sodium_mg=nutr_data.get("sodium_mg", 0.0),
        serving_size_g=nutr_data.get("serving_size_g", 100.0)
    )

    ing_tokens = [i.strip() for i in (req.ingredients_text or "").split(",") if i.strip()]
    ingredients_obj = Ingredients(
        raw_text=req.ingredients_text or "",
        ingredient_list=ing_tokens
    )

    product_obj = Product(
        id=req.barcode or f"prod_{abs(hash(req.product_name)) % 100000}",
        name=req.product_name,
        brand=req.brand or "",
        barcode=req.barcode,
        nutrition=nutrition_obj,
        ingredients=ingredients_obj,
        allergens=Allergens(),
        evidence=Evidence(
            overall_confidence=SourceConfidence.HIGH if req.nutrition else SourceConfidence.MEDIUM,
            sources_consulted=["Direct API / Lab Input"],
            last_verified=datetime.now(timezone.utc).isoformat()
        )
    )

    # 1. Allergen Intelligence
    user_allergens = req.allergies or []
    allergen_hits = AllergenEngine.screen_product(product_obj, user_allergens)
    detected_allergens = list({h.allergen_category for h in allergen_hits})
    derivatives_found = [h.matched_token for h in allergen_hits if h.detection_type.value == "DERIVATIVE"]

    # 2. Deterministic Clinical Evaluation
    overall_status, assessments, human_reasons = ClinicalRuleEngine.evaluate(
        product=product_obj,
        user_medical_history=req.medical_history or "",
        user_allergies=user_allergens,
        food_preferences=req.dietary_preferences or ""
    )

    # 3. FSSAI & Cultural Guardrails
    fssai_logo = FssaiComplianceEngine.detect_fssai_logos(req.product_name, req.ingredients_text or "")
    hfss_data = FssaiComplianceEngine.calculate_hfss(nutrition_obj)
    jain_audit = IndianDietaryGuardrail.evaluate_jain(req.ingredients_text or "")
    vrat_audit = IndianDietaryGuardrail.evaluate_vrat(req.ingredients_text or "")

    # 4. NOVA Processing Classification
    nova_info = NovaProcessingScorer.evaluate_nova(
        product_name=req.product_name,
        ingredients_text=req.ingredients_text or ""
    )

    # 5. Ayurvedic Viruddha Ahara
    ayurvedic_conflicts = AyurvedicEngine.evaluate_viruddha_ahara(req.ingredients_text or "")

    verdict_str = overall_status.value if hasattr(overall_status, "value") else str(overall_status)

    result = {
        "product_name": req.product_name,
        "brand": req.brand,
        "verdict": verdict_str,
        "clinical_reasons": human_reasons,
        "assessments": [a.model_dump() for a in assessments],
        "allergens_detected": detected_allergens,
        "allergen_derivatives": derivatives_found,
        "nova_group": nova_info.get("nova_group", 0),
        "nova_title": nova_info.get("nova_title", "Unclassified"),
        "clean_label_score": nova_info.get("clean_label_score", 100),
        "fssai_compliance": {
            "logo": fssai_logo,
            "hfss": hfss_data
        },
        "dietary_guardrails": {
            "jain": jain_audit,
            "vrat": vrat_audit
        },
        "ayurvedic_conflicts": ayurvedic_conflicts
    }


    # Optional: Save to Supabase scan history
    if req.save_to_history:
        supabase_client.save_scan_history({
            "user_id": req.user_id,
            "product_id": req.barcode or req.product_name,
            "name": req.product_name,
            "brand": req.brand or "",
            "verdict": verdict_str,
            "confidence": "HIGH" if req.nutrition else "MEDIUM",
            "input_mode": "api",
            "nutrition_facts": nutr_data,
            "ingredients": req.ingredients_text or "",
            "allergens": allergen_res.get("detected_allergens", []),
            "clinical_reasons": clinical_reasons
        })

    return result


@app.get("/api/v1/barcode/{barcode}")
async def lookup_barcode_endpoint(
    barcode: str,
    medical_history: str = Query("General Health", description="Patient medical history / chronic conditions"),
    allergies: str = Query("", description="Comma-separated declared patient allergies"),
    preferences: str = Query("", description="Dietary preferences or cultural guardrails"),
    location: str = Query("Bengaluru", description="User metro location")
):
    """
    Looks up a food product by 8, 12, or 13-digit barcode across
    Supabase cache, Open Food Facts, and live GS1/retail databases,
    returning deterministic clinical safety and portion recommendations.
    """
    from product_sources import ProductSources
    ps = ProductSources()
    allergies_list = [a.strip() for a in allergies.split(",") if a.strip()]
    product = ps.fetch_by_barcode(
        barcode=barcode,
        user_medical_history=medical_history,
        user_allergies=allergies_list,
        location=location,
        food_preferences=preferences
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Barcode '{barcode}' could not be resolved in verified lab or retail databases."
        )
    return product.model_dump()


@app.post("/api/v1/ocr")
async def ocr_packaging(
    image: UploadFile = File(...),
    upload_to_storage: bool = Form(False)
):
    """
    Extracts product name, brand, ingredients, and nutritional table from a food package photo.
    Optionally stores image in Supabase Object Storage.
    """
    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image file received.")

    image_url = None
    if upload_to_storage:
        image_url = supabase_client.upload_label_scan(
            image_bytes=contents,
            filename=f"scans/{image.filename}",
            content_type=image.content_type or "image/jpeg"
        )

    # Run OCR Engine
    ocr_result = OcrEngine.analyze_image_bytes(contents)

    return {
        "status": "success",
        "image_url": image_url,
        "product_name": ocr_result.product_name,
        "brand": ocr_result.brand,
        "ingredients_text": ocr_result.ingredients_text,
        "nutrition_facts": ocr_result.nutrition_facts.model_dump() if ocr_result.nutrition_facts else {},
        "raw_text": ocr_result.raw_text,
        "confidence": ocr_result.confidence
    }


@app.post("/api/v1/cgm/simulate")
def simulate_cgm(req: CgmRequest):
    """
    Simulates a Continuous Glucose Monitor (CGM) glycemic trajectory curve over 180 minutes.
    Computes peak glucose, spike rise, and buffering effects of fiber and protein.
    """
    nutr = NutritionFacts(
        carbohydrates=req.carbohydrates_g,
        dietary_fiber=req.fiber_g or 0.0,
        sugars=req.added_sugars_g or 0.0,
        protein=req.protein_g or 0.0,
        total_fat=req.fat_g or 0.0
    )

    cgm_result = CgmGlucosePredictor.simulate_glucose_curve(
        nutrition=nutr,
        is_diabetic=False,
        baseline_mg_dl=req.baseline_glucose or 95.0
    )

    return cgm_result


@app.post("/api/v1/swaps")
def get_safe_swaps(req: SwapRequest):
    """
    Returns healthier verified product alternatives tailored to clinical restrictions
    and user preferences.
    """
    swaps = SmartSafeSwapEngine.get_smart_swaps(
        product_name=req.category or "snack",
        category=req.category or ""
    )

    return {
        "category": req.category,
        "swaps_count": len(swaps),
        "recommendations": swaps
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
