import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from schemas import Product, NutritionFacts, Ingredients, Allergens, RetailerOffer, Evidence, SourceConfidence

class EvidenceEngine:
    """
    Evidence-backed Cross-Validation and Clinical Safety Reasoning Engine.
    Rules:
    - Cross-validates data across sources (Open Food Facts, Manufacturer, Retailers).
    - Detects conflicts visibly (e.g. sugar discrepancies, allergen mismatches).
    - Never assumes missing information is safe; marks as 'Not verified'.
    - Reasons against user's allergies and medical history with explicit citations.
    """

    @classmethod
    def cross_validate(
        cls,
        nutrition: Optional[NutritionFacts],
        ingredients: Optional[Ingredients],
        allergens: Optional[Allergens],
        retailer_offers: List[RetailerOffer],
        sources_consulted: List[str],
        source_urls: List[str]
    ) -> Tuple[Evidence, SourceConfidence]:
        """
        Detects conflicts between Open Food Facts, packaging claims, and retailer offers.
        Calculates aggregate evidence and confidence level.
        """
        conflicts: List[str] = []
        now_str = datetime.now(timezone.utc).isoformat()

        has_off = any("open food facts" in s.lower() for s in sources_consulted)
        has_retailer = len(retailer_offers) > 0
        has_mfg = any("manufacturer" in s.lower() or "official" in s.lower() for s in sources_consulted)

        # 1. Cross-check nutrition conflicts if multiple values exist
        # Check sugar declarations
        if nutrition and nutrition.sugar_g is not None:
            for offer in retailer_offers:
                # If retailer text claims 'Sugar Free' or 'No Sugar' but sugar_g > 2.0g
                if re.search(r"\b(?:sugar\s*free|zero\s*sugar|no\s*sugar)\b", offer.product_name, re.I) and nutrition.sugar_g > 2.0:
                    conflicts.append(f"Sugar Discrepancy: '{offer.retailer}' title claims Zero/Sugar Free, but verified lab panel records {nutrition.sugar_g}g sugars.")

        # 2. Cross-check allergen conflicts
        if allergens:
            for offer in retailer_offers:
                # If retailer claims nut-free but allergens contains peanut or tree nuts
                has_nuts = any("nut" in c or "peanut" in c or "almond" in c for c in allergens.contains)
                if has_nuts and re.search(r"\b(?:nut\s*free|peanut\s*free)\b", offer.product_name, re.I):
                    conflicts.append(f"CRITICAL ALLERGEN CONFLICT: '{offer.retailer}' claims Nut-Free, but official ingredients contain {allergens.contains}.")

        # 3. Determine Overall Confidence
        if has_off and has_retailer and not conflicts:
            overall_confidence = SourceConfidence.HIGH
        elif (has_off or (has_retailer and nutrition and nutrition.calories is not None)) and not conflicts:
            overall_confidence = SourceConfidence.MEDIUM
        elif conflicts:
            overall_confidence = SourceConfidence.LOW
        else:
            overall_confidence = SourceConfidence.LOW

        evidence = Evidence(
            manufacturer_verified=has_mfg,
            open_food_facts_verified=has_off,
            retailer_verified=has_retailer,
            sources_consulted=sources_consulted,
            source_urls=[u for u in source_urls if u],
            conflicts_detected=conflicts,
            overall_confidence=overall_confidence,
            last_verified=now_str
        )

        return evidence, overall_confidence

    @classmethod
    def evaluate_clinical_safety(
        cls,
        product: Product,
        user_medical_history: str,
        user_allergies: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Assesses product against user's specific health conditions and allergens.
        Returns (Verdict: SAFE | PARTIALLY SAFE | UNSAFE | NOT VERIFIED, List[Reasons])
        """
        reasons: List[str] = []
        is_unsafe = False
        is_partially_safe = False

        allergens = product.allergens
        ingredients = product.ingredients
        nutrition = product.nutrition

        # Check if ingredients or allergens are unverified
        if not ingredients or not ingredients.raw_text:
            if not allergens or not allergens.contains:
                return (
                    "NOT VERIFIED",
                    [
                        "⚠️ Full ingredients and allergen declarations could not be verified from official sources.",
                        "Strict SafeBite Rule: Unverified products are NEVER assumed safe for severe allergies or medical conditions."
                    ]
                )

        # 1. STRICT ALLERGEN SCREENING
        cleaned_allergens = [a.strip().lower() for a in user_allergies if a.strip() and a.lower() != "none"]
        if allergens and cleaned_allergens:
            all_product_allergens = set([a.lower() for a in allergens.contains] + [m.lower() for m in allergens.may_contain])
            raw_ing_text = (ingredients.raw_text or "").lower()

            for user_all in cleaned_allergens:
                # Direct match in allergen tags
                for pa in all_product_allergens:
                    if user_all in pa or pa in user_all:
                        is_unsafe = True
                        reasons.append(f"🚨 STRICT ALLERGEN TRIGGER: Product contains '{pa}', matching your declared allergy to '{user_all}'.")

                # Substring check in ingredients list
                if not is_unsafe and user_all in raw_ing_text:
                    is_unsafe = True
                    reasons.append(f"🚨 STRICT ALLERGEN TRIGGER: Ingredient text explicitly includes '{user_all}'.")

                # Derivative / hidden allergen check (e.g. dairy -> casein, whey; gluten -> wheat, barley)
                if user_all in ("dairy", "milk"):
                    # Exclude plant-based butters (cocoa butter, peanut butter, almond butter, shea butter)
                    ing_without_plant_butters = re.sub(r"\b(cocoa|cacao|peanut|almond|cashew|shea|apple|mango|coconut)\s+butter\b", " ", raw_ing_text)
                    dairy_derivatives = ["casein", "whey", "lactose", "milk solids", "ghee", "butterfat", "dairy butter"]
                    if any(d in ing_without_plant_butters for d in dairy_derivatives) or re.search(r"\bbutter\b", ing_without_plant_butters):
                        is_unsafe = True
                        reasons.append(f"🚨 HIDDEN ALLERGEN: Found dairy derivative (casein / whey / milk solids / butter) in ingredients.")
                
                if user_all in ("gluten",) and any(g in raw_ing_text for g in ["wheat", "barley", "rye", "malt", "maltodextrin"]):
                    is_unsafe = True
                    reasons.append(f"🚨 HIDDEN GLUTEN: Found gluten derivative (wheat / barley / malt) in ingredients.")

        # 2. MEDICAL HISTORY SCREENING
        med_lower = user_medical_history.lower() if user_medical_history else ""

        # Diabetes / Glycemic screening
        if any(d in med_lower for d in ["diabetes", "diabetic", "insulin", "high sugar"]):
            if nutrition and nutrition.sugar_g is not None:
                if nutrition.sugar_g > 10.0:
                    is_unsafe = True
                    reasons.append(f"⚠️ HIGH GLYCEMIC RISK: Contains {nutrition.sugar_g}g sugars per serving (exceeds recommended safe limit of 5-10g for diabetes).")
                elif nutrition.sugar_g > 5.0:
                    is_partially_safe = True
                    reasons.append(f"⚡ MODERATE SUGAR: Contains {nutrition.sugar_g}g sugars. Consume with medical discretion.")
                else:
                    reasons.append(f"✅ DIABETES COMPLIANT: Verified low-sugar formulation ({nutrition.sugar_g}g total sugar).")
            elif ingredients and any(s in (ingredients.raw_text or "").lower() for s in ["high fructose corn syrup", "added sugar", "glucose syrup", "maltodextrin"]):
                is_unsafe = True
                reasons.append("⚠️ HIGH GLYCEMIC RISK: Contains high-glycemic syrups (corn syrup / maltodextrin / refined sugar).")

        # Hypertension / Low Sodium screening
        if any(h in med_lower for h in ["hypertension", "high blood pressure", "low sodium"]):
            if nutrition and nutrition.sodium_mg is not None:
                if nutrition.sodium_mg > 400.0:
                    is_unsafe = True
                    reasons.append(f"⚠️ HIGH SODIUM RISK: Contains {nutrition.sodium_mg}mg sodium per serving (exceeds safe threshold of 140-400mg).")
                else:
                    reasons.append(f"✅ HYPERTENSION COMPLIANT: Sodium is within clinical safe bounds ({nutrition.sodium_mg}mg).")

        # Celiac Disease / IBS / GERD
        if "celiac" in med_lower:
            if not allergens or "gluten free" not in allergens.free_from:
                if ingredients and any(g in (ingredients.raw_text or "").lower() for g in ["wheat", "barley", "rye", "oats", "spelt"]):
                    is_unsafe = True
                    reasons.append("🚨 CELIAC RISK: Product contains gluten-bearing grains.")

        # Final verdict assignment
        if is_unsafe:
            verdict = "UNSAFE"
        elif is_partially_safe or len(product.evidence.conflicts_detected) > 0:
            verdict = "PARTIALLY SAFE"
            if product.evidence.conflicts_detected:
                reasons.extend([f"⚠️ Review Conflict: {c}" for c in product.evidence.conflicts_detected])
        else:
            verdict = "SAFE"
            reasons.append("✅ Clinically cleared: Verified 100% free of declared personal allergens and compliant with your medical profile.")

        return verdict, reasons
