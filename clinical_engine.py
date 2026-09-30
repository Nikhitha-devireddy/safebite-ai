"""
SafeBite AI - Deterministic Clinical Safety & Verdict Engine
Provides research-grade, rule-based clinical evaluations across chronic diseases,
allergies, metabolic conditions, and dietary preferences.
Strict Rule: Lack of evidence MUST return UNKNOWN. Lack of evidence is NEVER assumed SAFE.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    ClinicalAssessment, ClinicalStatus, SourceConfidence
)
from allergen_engine import AllergenEngine, AllergenDetectionType
from config import Config

class ClinicalRuleEngine:
    """
    Extensible, deterministic clinical reasoning engine.
    Audits nutritional composition and chemical ingredient profiles against patient conditions.
    """

    @classmethod
    def _get_product_confidence(cls, product: Product) -> SourceConfidence:
        if product and product.evidence and product.evidence.overall_confidence:
            return product.evidence.overall_confidence
        return SourceConfidence.LOW

    @classmethod
    def evaluate(
        cls,
        product: Product,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        food_preferences: str = ""
    ) -> Tuple[ClinicalStatus, List[ClinicalAssessment], List[str]]:
        """
        Executes complete condition-by-condition clinical assessment.
        Returns:
            (overall_status, assessments_list, human_readable_reasons)
        """
        assessments: List[ClinicalAssessment] = []
        user_allergies = user_allergies or []
        cleaned_allergies = [a.strip() for a in user_allergies if a.strip() and a.lower() != "none"]
        med_lower = (user_medical_history or "").lower()
        pref_lower = (food_preferences or "").lower()

        nutrition = product.nutrition
        ingredients = product.ingredients
        allergens = product.allergens

        # Global Evidence Sanity Check: If product lacks all nutrition, ingredients, and allergens
        has_any_nutrition = nutrition and (nutrition.calories is not None or nutrition.sugar_g is not None or nutrition.protein_g is not None)
        has_any_ingredients = ingredients and bool(ingredients.raw_text or ingredients.ingredient_list)
        has_any_allergens = allergens and bool(allergens.contains or allergens.may_contain or allergens.free_from)

        # -------------------------------------------------------------
        # 1. EVALUATE ALLERGIES (STRICT SCREENING)
        # -------------------------------------------------------------
        if cleaned_allergies:
            if not has_any_ingredients and not has_any_allergens:
                for ua in cleaned_allergies:
                    assessments.append(ClinicalAssessment(
                        condition=f"{ua.title()} Allergy",
                        status=ClinicalStatus.UNKNOWN,
                        reason=f"Cannot verify absence of '{ua}' because ingredient panel and allergen statements are missing.",
                        evidence="Data source provides no ingredient declarations or packaging lab panel.",
                        matched_factors=[],
                        confidence=SourceConfidence.UNVERIFIED,
                        source="Packaging Audit"
                    ))
            else:
                allergen_hits = AllergenEngine.screen_product(product, cleaned_allergies)
                hits_by_user_allergy: Dict[str, list] = {}
                for h in allergen_hits:
                    hits_by_user_allergy.setdefault(h.user_declared_allergy.lower(), []).append(h)

                for ua in cleaned_allergies:
                    ua_hits = hits_by_user_allergy.get(ua.lower(), [])
                    if not ua_hits:
                        # Verified clean
                        assessments.append(ClinicalAssessment(
                            condition=f"{ua.title()} Allergy",
                            status=ClinicalStatus.CLEAR,
                            reason=f"Verified 100% free of '{ua}' and known derivatives in official ingredient list.",
                            evidence=f"Audited {len(ingredients.ingredient_list) if ingredients else 0} ingredients; zero triggers identified.",
                            matched_factors=[],
                            confidence=cls._get_product_confidence(product),
                            source="Ingredient Panel Audit"
                        ))
                    else:
                        has_direct = any(h.detection_type in (AllergenDetectionType.DIRECT, AllergenDetectionType.DERIVATIVE) for h in ua_hits)
                        if has_direct:
                            direct_tokens = [h.matched_token for h in ua_hits if h.detection_type in (AllergenDetectionType.DIRECT, AllergenDetectionType.DERIVATIVE)]
                            evidence_snips = "; ".join([h.evidence_snippet for h in ua_hits[:2]])
                            assessments.append(ClinicalAssessment(
                                condition=f"{ua.title()} Allergy",
                                status=ClinicalStatus.AVOID,
                                reason=f"🚨 STRICT ALLERGEN TRIGGER: Product contains '{', '.join(direct_tokens)}', matching your declared allergy to {ua}.",
                                evidence=evidence_snips,
                                matched_factors=direct_tokens,
                                confidence=SourceConfidence.HIGH,
                                source="Ingredient Declaration"
                            ))
                        else:
                            # Precautionary / Cross-contact
                            trace_tokens = [h.matched_token for h in ua_hits]
                            evidence_snips = "; ".join([h.evidence_snippet for h in ua_hits[:2]])
                            assessments.append(ClinicalAssessment(
                                condition=f"{ua.title()} Allergy",
                                status=ClinicalStatus.CAUTION,
                                reason=f"CROSS-CONTACT WARNING: Manufacturer statement indicates product may contain traces of {', '.join(trace_tokens)}.",
                                evidence=evidence_snips,
                                matched_factors=trace_tokens,
                                confidence=SourceConfidence.HIGH,
                                source="Precautionary Statement (PAL)"
                            ))

        # -------------------------------------------------------------
        # 2. EVALUATE CHRONIC MEDICAL CONDITIONS
        # -------------------------------------------------------------
        # DIABETES / PRE-DIABETES / INSULIN RESISTANCE
        if any(d in med_lower for d in ["diabetes", "diabetic", "glycemic", "blood sugar", "insulin"]):
            cls._evaluate_diabetes(product, assessments)

        # HYPERTENSION / HIGH BLOOD PRESSURE / LOW SODIUM
        if any(h in med_lower for h in ["hypertension", "blood pressure", "sodium", "cardiac", "heart"]):
            cls._evaluate_hypertension(product, assessments)

        # CELIAC DISEASE / GLUTEN ENTEROPATHY
        if any(c in med_lower for c in ["celiac", "coeliac", "gluten sensitive", "sprue"]):
            cls._evaluate_celiac(product, assessments)

        # LACTOSE INTOLERANCE
        if any(l in med_lower for l in ["lactose", "milk intolerance"]):
            cls._evaluate_lactose(product, assessments)

        # CHRONIC CONSTIPATION / GI FIBER
        if any(cf in med_lower for cf in ["constipation", "gut health", "high fiber", "bowel"]):
            cls._evaluate_constipation(product, assessments)

        # GOUT / HYPERURICEMIA / KIDNEY
        if any(g in med_lower for g in ["gout", "uric acid", "kidney", "renal"]):
            cls._evaluate_renal_gout(product, assessments)

        # -------------------------------------------------------------
        # 3. EVALUATE DIETARY / LIFESTYLE PREFERENCES
        # -------------------------------------------------------------
        # VEGAN
        if "vegan" in pref_lower or "vegan" in med_lower:
            cls._evaluate_vegan(product, assessments)
        # VEGETARIAN (if not already evaluating Vegan)
        elif "vegetarian" in pref_lower or "vegetarian" in med_lower:
            cls._evaluate_vegetarian(product, assessments)

        # HIGH PROTEIN PREFERENCE
        if "high protein" in pref_lower or "high protein" in med_lower:
            cls._evaluate_high_protein(product, assessments)

        # LOW SUGAR PREFERENCE
        if "low sugar" in pref_lower or "sugar free" in pref_lower or "zero sugar" in pref_lower:
            if not any(a.condition == "Type 2 Diabetes / Glycemic Safety" for a in assessments):
                cls._evaluate_low_sugar(product, assessments)

        # -------------------------------------------------------------
        # 4. COMPUTE OVERALL STATUS & COMPILED REASONS
        # -------------------------------------------------------------
        overall_status = ClinicalStatus.CLEAR
        compiled_reasons: List[str] = []

        if not assessments:
            # If no health criteria were specified by user
            if not has_any_nutrition and not has_any_ingredients:
                overall_status = ClinicalStatus.UNKNOWN
                compiled_reasons.append("⚠️ Nutrition facts and ingredient details are unverified from official databases.")
            else:
                overall_status = ClinicalStatus.CLEAR
                item_count = len(ingredients.ingredient_list) if (ingredients and ingredients.ingredient_list) else 1
                compiled_reasons.append(f"✅ Verified {item_count} declared ingredients against general food safety guidelines.")
                assessments.append(ClinicalAssessment(
                    condition="Ingredient & Additive Screening",
                    status=ClinicalStatus.CLEAR if (ingredients and ingredients.is_clean_label) else ClinicalStatus.CAUTION,
                    reason=f"Parsed {item_count} declared ingredients." + (f" Identified additives/syrups: {', '.join(ingredients.additives)}." if (ingredients and ingredients.additives) else " Free from synthetic preservatives, artificial sweeteners, and high-fructose syrups."),
                    evidence=f"Audited ingredients: {', '.join(ingredients.ingredient_list[:6]) if ingredients and ingredients.ingredient_list else 'Declared'}",
                    matched_factors=ingredients.additives if ingredients else [],
                    confidence=cls._get_product_confidence(product),
                    source="Ingredient Declaration Audit"
                ))
        else:
            has_avoid = any(a.status == ClinicalStatus.AVOID for a in assessments)
            has_caution = any(a.status == ClinicalStatus.CAUTION for a in assessments)
            has_unknown = any(a.status == ClinicalStatus.UNKNOWN for a in assessments)

            if has_avoid:
                overall_status = ClinicalStatus.AVOID
            elif has_unknown:
                overall_status = ClinicalStatus.UNKNOWN
            elif has_caution:
                overall_status = ClinicalStatus.CAUTION
            else:
                overall_status = ClinicalStatus.CLEAR

            for a in assessments:
                if a.status == ClinicalStatus.AVOID:
                    compiled_reasons.append(f"{a.reason}")
                elif a.status == ClinicalStatus.CAUTION:
                    compiled_reasons.append(f"⚠️ [{a.condition}] CAUTION: {a.reason}")
                elif a.status == ClinicalStatus.UNKNOWN:
                    compiled_reasons.append(f"❓ [{a.condition}] UNKNOWN: {a.reason}")
                elif a.status == ClinicalStatus.CLEAR:
                    compiled_reasons.append(f"✅ [{a.condition}] CLEAR: {a.reason}")

            if overall_status == ClinicalStatus.CLEAR:
                compiled_reasons.append("✅ Clinically cleared: Verified 100% free of declared personal allergens and compliant with your medical profile.")

        # Check for cross-source discrepancies from evidence engine
        if product.evidence.conflicts_detected:
            if overall_status == ClinicalStatus.CLEAR:
                overall_status = ClinicalStatus.CAUTION
            for conf in product.evidence.conflicts_detected:
                compiled_reasons.append(f"⚠️ Data Discrepancy: {conf}")

        return overall_status, assessments, compiled_reasons

    # =========================================================================
    # CONDITION-SPECIFIC EVALUATORS
    # =========================================================================

    @classmethod
    def _evaluate_diabetes(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        nut = product.nutrition
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        # Comprehensive glycemic sweetener triggers in ingredients (deduplicating generic sugar)
        glycemic_sugars = [
            "high fructose corn syrup", "corn syrup", "glucose syrup",
            "maltodextrin", "dextrose", "invert sugar", "liquid glucose",
            "granulated sugar", "cane sugar", "brown sugar", "powdered sugar",
            "sucrose", "fructose", "maltose", "molasses", "honey", "agave",
            "maple syrup", "malt syrup", "rice syrup"
        ]
        found_sugars = []
        temp_ing = raw_ing
        for s in glycemic_sugars:
            if re.search(r"\b" + re.escape(s) + r"\b", temp_ing):
                found_sugars.append(s)
                temp_ing = re.sub(r"\b" + re.escape(s) + r"\b", " ", temp_ing)
        if re.search(r"\bsugar\b", temp_ing):
            found_sugars.append("sugar")

        diabetic_friendly_sweeteners = [
            "stevia", "monk fruit", "erythritol", "allulose", "xylitol", "sucralose"
        ]
        found_friendly = [df for df in diabetic_friendly_sweeteners if re.search(r"\b" + re.escape(df) + r"\b", raw_ing)]

        # If nutritional sugar_g is available, use exact lab threshold
        if nut and nut.sugar_g is not None:
            sugar = nut.sugar_g
            added_sugar = nut.added_sugars
            high_spike_syrups = ["high fructose corn syrup", "corn syrup", "glucose syrup", "maltodextrin", "dextrose", "invert sugar"]
            has_spike = any(s in found_sugars for s in high_spike_syrups)

            if sugar > Config.DIABETES_MAX_TOTAL_SUGAR_G or (added_sugar is not None and added_sugar > 5.0) or (has_spike and sugar > 5.0):
                reasons = [f"⚠️ HIGH GLYCEMIC RISK: Contains {sugar}g sugars per serving (exceeds safe limit of 5-10g for diabetes)."]
                if found_sugars:
                    reasons.append(f"Sweeteners detected in ingredients: {', '.join(found_sugars[:3])}.")
                assessments.append(ClinicalAssessment(
                    condition="Type 2 Diabetes / Glycemic Safety",
                    status=ClinicalStatus.AVOID,
                    reason=" ".join(reasons),
                    evidence=f"Total Sugars: {sugar}g, Ingredients: {found_sugars[:3]}",
                    matched_factors=[f"Sugar: {sugar}g"] + found_sugars,
                    confidence=nut.confidence,
                    source=nut.source
                ))
            elif sugar > Config.DIABETES_CAUTION_SUGAR_G:
                assessments.append(ClinicalAssessment(
                    condition="Type 2 Diabetes / Glycemic Safety",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Contains moderate sugar ({sugar}g). Consume in portion context.",
                    evidence=f"Total Sugars: {sugar}g (Threshold: {Config.DIABETES_CAUTION_SUGAR_G}g).",
                    matched_factors=[f"Sugar: {sugar}g"] + found_sugars,
                    confidence=nut.confidence,
                    source=nut.source
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="Type 2 Diabetes / Glycemic Safety",
                    status=ClinicalStatus.CLEAR,
                    reason=f"Verified low glycemic impact ({sugar}g sugars). Safe for diabetic blood sugar management.",
                    evidence=f"Lab nutrition confirms {sugar}g sugars per serving (<= {Config.DIABETES_CAUTION_SUGAR_G}g).",
                    matched_factors=[],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            return

        # Ingredient-based evaluation (when nutritional table is absent or not provided)
        if found_sugars:
            high_risk_syrups = ["high fructose corn syrup", "corn syrup", "glucose syrup", "maltodextrin", "dextrose", "invert sugar"]
            has_spike_syrup = any(s in found_sugars for s in high_risk_syrups)
            
            if has_spike_syrup or len(found_sugars) >= 2:
                assessments.append(ClinicalAssessment(
                    condition="Type 2 Diabetes / Glycemic Safety",
                    status=ClinicalStatus.AVOID,
                    reason=f"High Glycemic Risk: Ingredients declare rapid-spike sweeteners ({', '.join(found_sugars[:3])}). Unsuitable for blood sugar regulation.",
                    evidence=f"Audited ingredients declare: {', '.join(found_sugars[:3])}.",
                    matched_factors=found_sugars,
                    confidence=SourceConfidence.HIGH,
                    source="Ingredient Formulation Audit"
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="Type 2 Diabetes / Glycemic Safety",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Contains declared added sugar ({found_sugars[0]}). Diabetic individuals should monitor portion size.",
                    evidence=f"Audited ingredients declare: {found_sugars[0]}.",
                    matched_factors=found_sugars,
                    confidence=SourceConfidence.HIGH,
                    source="Ingredient Formulation Audit"
                ))
        elif found_friendly:
            assessments.append(ClinicalAssessment(
                condition="Type 2 Diabetes / Glycemic Safety",
                status=ClinicalStatus.CLEAR,
                reason=f"Diabetic-Friendly Sweetener: Formulated with {', '.join(found_friendly)}. Free from added sucrose or corn syrups.",
                evidence=f"Sweetener: {', '.join(found_friendly)}.",
                matched_factors=[],
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        elif raw_ing:
            assessments.append(ClinicalAssessment(
                condition="Type 2 Diabetes / Glycemic Safety",
                status=ClinicalStatus.CLEAR,
                reason="Verified Low Glycemic: Declared ingredients are free from added sugars, syrups, and refined sweeteners.",
                evidence=f"Audited {len(ing.ingredient_list) if ing else 0} ingredients; zero added sugars or glycemic syrups identified.",
                matched_factors=[],
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="Type 2 Diabetes / Glycemic Safety",
                status=ClinicalStatus.UNKNOWN,
                reason="Sugar and glycemic composition cannot be verified; ingredient list is missing.",
                evidence="No ingredients declaration provided.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Ingredient Audit"
            ))

    @classmethod
    def _evaluate_hypertension(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        nut = product.nutrition
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        sodium_ingredients = [
            "monosodium glutamate", "msg", "sodium benzoate", "disodium phosphate",
            "sodium nitrite", "sodium nitrate", "sodium chloride", "sea salt", "rock salt",
            "baking soda", "sodium bicarbonate", "sodium citrate", "sodium caseinate",
            "soy sauce", "brine", "salt"
        ]
        found_sodium = [s for s in sodium_ingredients if re.search(r"\b" + re.escape(s) + r"\b", raw_ing)]

        # If nutritional sodium_mg is available, evaluate exact threshold
        if nut and nut.sodium_mg is not None:
            sodium = nut.sodium_mg
            if sodium > Config.HYPERTENSION_MAX_SODIUM_MG:
                assessments.append(ClinicalAssessment(
                    condition="Hypertension / Sodium Safety",
                    status=ClinicalStatus.AVOID,
                    reason=f"High sodium formulation ({sodium}mg per serving; exceeds clinical limit of {Config.HYPERTENSION_MAX_SODIUM_MG}mg).",
                    evidence=f"Reported Sodium: {sodium}mg/serving.",
                    matched_factors=[f"Sodium: {sodium}mg"] + found_sodium,
                    confidence=nut.confidence,
                    source=nut.source
                ))
            elif sodium > Config.HYPERTENSION_LOW_SODIUM_MG or found_sodium:
                assessments.append(ClinicalAssessment(
                    condition="Hypertension / Sodium Safety",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Moderate sodium ({sodium}mg per serving). Safe in moderation.",
                    evidence=f"Reported Sodium: {sodium}mg/serving (Low sodium benchmark is <= {Config.HYPERTENSION_LOW_SODIUM_MG}mg).",
                    matched_factors=[f"Sodium: {sodium}mg"] + found_sodium,
                    confidence=nut.confidence,
                    source=nut.source
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="Hypertension / Sodium Safety",
                    status=ClinicalStatus.CLEAR,
                    reason=f"Verified clinical low sodium ({sodium}mg per serving, <= {Config.HYPERTENSION_LOW_SODIUM_MG}mg).",
                    evidence=f"Reported Sodium: {sodium}mg/serving.",
                    matched_factors=[],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            return

        # Ingredient-based evaluation (when nutritional table is absent or not provided)
        if found_sodium:
            is_heavy_sodium = any(s in found_sodium for s in ["monosodium glutamate", "msg", "brine", "soy sauce"]) or len(found_sodium) >= 2
            assessments.append(ClinicalAssessment(
                condition="Hypertension / Sodium Safety",
                status=ClinicalStatus.AVOID if is_heavy_sodium else ClinicalStatus.CAUTION,
                reason=f"Contains sodium-bearing ingredients ({', '.join(found_sodium)}). High blood pressure patients should consume cautiously.",
                evidence=f"Ingredients declare: {', '.join(found_sodium)}.",
                matched_factors=found_sodium,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        elif raw_ing:
            assessments.append(ClinicalAssessment(
                condition="Hypertension / Sodium Safety",
                status=ClinicalStatus.CLEAR,
                reason="Verified Low Sodium: Declared ingredients are free from added salt, MSG, or sodium-based preservatives.",
                evidence=f"Audited {len(ing.ingredient_list) if ing else 0} ingredients; zero sodium compounds identified.",
                matched_factors=[],
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="Hypertension / Sodium Safety",
                status=ClinicalStatus.UNKNOWN,
                reason="Sodium presence cannot be evaluated; ingredient list is missing.",
                evidence="No ingredients declaration provided.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Ingredient Audit"
            ))

    @classmethod
    def _evaluate_celiac(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        ing = product.ingredients
        allg = product.allergens
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        gluten_grains = ["wheat", "barley", "rye", "spelt", "kamut", "triticale", "semolina", "atta", "maida", "durum"]
        found_grains = [g for g in gluten_grains if re.search(r"\b" + re.escape(g) + r"\b", raw_ing)]

        is_certified_free = allg and ("gluten free" in [f.lower() for f in allg.free_from])

        if found_grains:
            assessments.append(ClinicalAssessment(
                condition="Celiac Disease / Gluten Safety",
                status=ClinicalStatus.AVOID,
                reason=f"Strict Contraindication: Product contains gluten-bearing grains ({', '.join(found_grains)}).",
                evidence=f"Ingredients explicitly declare {', '.join(found_grains)}.",
                matched_factors=found_grains,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Panel"
            ))
        elif is_certified_free:
            assessments.append(ClinicalAssessment(
                condition="Celiac Disease / Gluten Safety",
                status=ClinicalStatus.CLEAR,
                reason="Certified Gluten-Free: Zero gluten grains or cross-contamination detected.",
                evidence="Product packaging carries official gluten-free certification claim.",
                matched_factors=[],
                confidence=allg.confidence,
                source="Product Certifications"
            ))
        elif not raw_ing and (not allg or not allg.contains):
            assessments.append(ClinicalAssessment(
                condition="Celiac Disease / Gluten Safety",
                status=ClinicalStatus.UNKNOWN,
                reason="Gluten status is unverified; no ingredient declaration found.",
                evidence="Cannot confirm absence of wheat or cross-contamination.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Allergen Audit"
            ))
        else:
            # Check for may contain gluten
            traces = [t for t in (allg.may_contain if allg else []) if "gluten" in t.lower() or "wheat" in t.lower()]
            if traces:
                assessments.append(ClinicalAssessment(
                    condition="Celiac Disease / Gluten Safety",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Cross-contamination warning: Label warns '{traces[0]}'. May not be safe for severe Celiac.",
                    evidence=f"Precautionary statement: {traces[0]}",
                    matched_factors=traces,
                    confidence=allg.confidence,
                    source="Precautionary Statement"
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="Celiac Disease / Gluten Safety",
                    status=ClinicalStatus.CLEAR,
                    reason="No gluten-containing grains detected in audited ingredient list.",
                    evidence=f"Audited {len(ing.ingredient_list) if ing else 0} ingredients; zero wheat/barley/rye identified.",
                    matched_factors=[],
                    confidence=cls._get_product_confidence(product),
                    source="Ingredient Panel"
                ))

    @classmethod
    def _evaluate_lactose(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        lactose_triggers = ["lactose", "milk", "skim milk", "whole milk", "milk powder", "whey", "curd", "paneer"]
        # Filter plant butters
        filtered = re.sub(r"\b(?:cocoa|cacao|peanut|almond|cashew|shea|apple|mango|coconut)\s+butter\b", " ", raw_ing)
        found = [t for t in lactose_triggers if re.search(r"\b" + re.escape(t) + r"\b", filtered)]

        if found:
            assessments.append(ClinicalAssessment(
                condition="Lactose Intolerance",
                status=ClinicalStatus.AVOID,
                reason=f"Contains lactose-bearing dairy ingredients: {', '.join(found)}.",
                evidence=f"Ingredients declare {', '.join(found)}.",
                matched_factors=found,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Panel"
            ))
        elif not raw_ing:
            assessments.append(ClinicalAssessment(
                condition="Lactose Intolerance",
                status=ClinicalStatus.UNKNOWN,
                reason="Lactose presence cannot be verified from available product records.",
                evidence="Ingredient list is unverified.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="Lactose Intolerance",
                status=ClinicalStatus.CLEAR,
                reason="Verified dairy and lactose free in audited ingredients.",
                evidence="Zero milk or lactose solids declared.",
                matched_factors=[],
                confidence=cls._get_product_confidence(product),
                source="Ingredient Panel"
            ))

    @classmethod
    def _evaluate_constipation(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        nut = product.nutrition
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        fiber_ingredients = [
            "psyllium", "psyllium husk", "flaxseed", "chia", "chia seeds", "oats", "oat bran",
            "wheat bran", "inulin", "chicory root", "lentils", "beans", "chickpeas",
            "whole wheat", "brown rice", "quinoa", "barley"
        ]
        found_fiber = [f for f in fiber_ingredients if re.search(r"\b" + re.escape(f) + r"\b", raw_ing)]
        refined_ingredients = ["refined wheat flour", "maida", "corn starch", "white flour"]
        found_refined = [r for r in refined_ingredients if re.search(r"\b" + re.escape(r) + r"\b", raw_ing)]

        if nut and nut.fiber_g is not None:
            fiber = nut.fiber_g
            if fiber >= Config.HIGH_FIBER_MIN_G:
                assessments.append(ClinicalAssessment(
                    condition="GI / Fiber Optimization",
                    status=ClinicalStatus.CLEAR,
                    reason=f"Excellent high fiber formulation ({fiber}g per serving; >= {Config.HIGH_FIBER_MIN_G}g). Supports digestive motility.",
                    evidence=f"Reported Dietary Fiber: {fiber}g.",
                    matched_factors=[f"Fiber: {fiber}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            elif fiber >= 2.0:
                assessments.append(ClinicalAssessment(
                    condition="GI / Fiber Optimization",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Moderate fiber ({fiber}g). Supplement with whole vegetables or chia/flax.",
                    evidence=f"Reported Dietary Fiber: {fiber}g.",
                    matched_factors=[f"Fiber: {fiber}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="GI / Fiber Optimization",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Low fiber ({fiber}g per serving). Highly refined composition may exacerbate sluggish transit.",
                    evidence=f"Reported Dietary Fiber: {fiber}g.",
                    matched_factors=[f"Fiber: {fiber}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            return

        # Ingredient-based evaluation (when numerical nutrition table is absent)
        if found_fiber:
            assessments.append(ClinicalAssessment(
                condition="GI / Fiber Optimization",
                status=ClinicalStatus.CLEAR,
                reason=f"Digestive Fiber Potential: Contains dietary fiber sources ({', '.join(found_fiber)}). Supports healthy GI motility.",
                evidence=f"Ingredients declare: {', '.join(found_fiber)}.",
                matched_factors=found_fiber,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        elif found_refined:
            assessments.append(ClinicalAssessment(
                condition="GI / Fiber Optimization",
                status=ClinicalStatus.CAUTION,
                reason=f"Refined Starch Base: Formulated with {', '.join(found_refined)} without whole grain fiber.",
                evidence=f"Ingredients declare: {', '.join(found_refined)}.",
                matched_factors=found_refined,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        elif raw_ing:
            assessments.append(ClinicalAssessment(
                condition="GI / Fiber Optimization",
                status=ClinicalStatus.CLEAR,
                reason="Standard whole-food ingredient formulation.",
                evidence=f"Audited {len(ing.ingredient_list) if ing else 0} ingredients.",
                matched_factors=[],
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="GI / Fiber Optimization",
                status=ClinicalStatus.UNKNOWN,
                reason="Fiber status cannot be assessed; ingredient list is missing.",
                evidence="No ingredients declaration provided.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))

    @classmethod
    def _evaluate_renal_gout(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        purine_triggers = ["anchovies", "sardines", "organ meat", "liver", "yeast extract", "brewer's yeast", "scallops"]
        found = [p for p in purine_triggers if p in raw_ing]

        if found:
            assessments.append(ClinicalAssessment(
                condition="Gout / Renal Health",
                status=ClinicalStatus.AVOID,
                reason=f"High purine ingredients identified: {', '.join(found)}. High risk of uric acid elevation.",
                evidence=f"Ingredients declare {', '.join(found)}.",
                matched_factors=found,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Panel"
            ))
        elif not raw_ing:
            assessments.append(ClinicalAssessment(
                condition="Gout / Renal Health",
                status=ClinicalStatus.UNKNOWN,
                reason="Purine and additive profile is unverified.",
                evidence="Ingredient declaration missing.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="Gout / Renal Health",
                status=ClinicalStatus.CLEAR,
                reason="Free from high-purine ingredients and artificial phosphate binders.",
                evidence="Zero yeast extracts or high-purine animal byproducts.",
                matched_factors=[],
                confidence=cls._get_product_confidence(product),
                source="Ingredient Panel"
            ))

    @classmethod
    def _evaluate_vegan(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        animal_byproducts = [
            "milk", "whey", "casein", "lactose", "ghee", "butter", "cheese", "curd",
            "egg", "eggs", "albumin", "honey", "beeswax", "gelatin", "gelatine",
            "carmine", "cochineal", "tallow", "lard", "isinglass", "shellac"
        ]
        filtered = re.sub(r"\b(?:cocoa|cacao|peanut|almond|cashew|shea|apple|mango|coconut)\s+butter\b", " ", raw_ing)
        found = [b for b in animal_byproducts if re.search(r"\b" + re.escape(b) + r"\b", filtered)]

        if found:
            assessments.append(ClinicalAssessment(
                condition="100% Vegan Compliance",
                status=ClinicalStatus.AVOID,
                reason=f"Non-Vegan: Contains animal-derived ingredients ({', '.join(found)}).",
                evidence=f"Ingredients declare {', '.join(found)}.",
                matched_factors=found,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Panel"
            ))
        elif not raw_ing:
            assessments.append(ClinicalAssessment(
                condition="100% Vegan Compliance",
                status=ClinicalStatus.UNKNOWN,
                reason="Vegan suitability unverified; full ingredients missing.",
                evidence="Cannot confirm absence of hidden animal byproducts.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="100% Vegan Compliance",
                status=ClinicalStatus.CLEAR,
                reason="Verified 100% plant-based: Zero dairy, eggs, honey, or animal derivatives.",
                evidence="All audited ingredients are plant or mineral derived.",
                matched_factors=[],
                confidence=cls._get_product_confidence(product),
                source="Ingredient Panel"
            ))

    @classmethod
    def _evaluate_vegetarian(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        non_veg = [
            "chicken", "beef", "pork", "mutton", "fish", "salmon", "tuna", "shrimp",
            "prawn", "crab", "gelatin", "gelatine", "carmine", "cochineal", "tallow",
            "lard", "animal rennet", "isinglass"
        ]
        found = [v for v in non_veg if re.search(r"\b" + re.escape(v) + r"\b", raw_ing)]

        if found:
            assessments.append(ClinicalAssessment(
                condition="Vegetarian Compliance",
                status=ClinicalStatus.AVOID,
                reason=f"Non-Vegetarian: Contains animal tissue or slaughter byproducts ({', '.join(found)}).",
                evidence=f"Ingredients declare {', '.join(found)}.",
                matched_factors=found,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Panel"
            ))
        elif not raw_ing:
            assessments.append(ClinicalAssessment(
                condition="Vegetarian Compliance",
                status=ClinicalStatus.UNKNOWN,
                reason="Vegetarian status unverified; ingredients not accessible.",
                evidence="Cannot audit for hidden gelatin or animal enzymes.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="Vegetarian Compliance",
                status=ClinicalStatus.CLEAR,
                reason="Verified Lacto-Vegetarian: Free from meat, fish, slaughter rennet, and gelatin.",
                evidence="All audited ingredients comply with vegetarian dietary standards.",
                matched_factors=[],
                confidence=cls._get_product_confidence(product),
                source="Ingredient Panel"
            ))

    @classmethod
    def _evaluate_high_protein(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        nut = product.nutrition
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        protein_sources = [
            "whey protein", "pea protein", "soy protein", "egg white", "collagen",
            "casein", "lentils", "chicken", "salmon", "tofu", "paneer", "almonds",
            "peanuts", "hemp protein", "rice protein", "soy protein isolate"
        ]
        found_protein = [p for p in protein_sources if re.search(r"\b" + re.escape(p) + r"\b", raw_ing)]

        if nut and nut.protein_g is not None:
            prot = nut.protein_g
            if prot >= Config.HIGH_PROTEIN_MIN_G:
                assessments.append(ClinicalAssessment(
                    condition="High Protein Criterion",
                    status=ClinicalStatus.CLEAR,
                    reason=f"Verified High Protein: Delivers {prot}g protein per serving (>= {Config.HIGH_PROTEIN_MIN_G}g).",
                    evidence=f"Reported Protein: {prot}g/serving.",
                    matched_factors=[f"Protein: {prot}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="High Protein Criterion",
                    status=ClinicalStatus.CAUTION,
                    reason=f"Delivers {prot}g protein per serving (Falls below high-protein threshold of {Config.HIGH_PROTEIN_MIN_G}g).",
                    evidence=f"Reported Protein: {prot}g/serving.",
                    matched_factors=[f"Protein: {prot}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            return

        # Ingredient-based evaluation
        if found_protein:
            assessments.append(ClinicalAssessment(
                condition="High Protein Criterion",
                status=ClinicalStatus.CLEAR,
                reason=f"Protein-Rich Formulation: Contains declared protein sources ({', '.join(found_protein)}).",
                evidence=f"Ingredients declare: {', '.join(found_protein)}.",
                matched_factors=found_protein,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        elif raw_ing:
            assessments.append(ClinicalAssessment(
                condition="High Protein Criterion",
                status=ClinicalStatus.CAUTION,
                reason="Standard formulation: Does not declare concentrated protein isolates or protein-dense legumes in ingredients.",
                evidence=f"Audited {len(ing.ingredient_list) if ing else 0} ingredients.",
                matched_factors=[],
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="High Protein Criterion",
                status=ClinicalStatus.UNKNOWN,
                reason="Protein presence cannot be evaluated; ingredient declaration missing.",
                evidence="No ingredients declaration provided.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))

    @classmethod
    def _evaluate_low_sugar(cls, product: Product, assessments: List[ClinicalAssessment]) -> None:
        nut = product.nutrition
        ing = product.ingredients
        raw_ing = (ing.raw_text or "").lower() if ing else ""

        added_sugars = [
            "granulated sugar", "cane sugar", "brown sugar", "powdered sugar",
            "corn syrup", "glucose syrup", "maltodextrin", "dextrose", "invert sugar",
            "sucrose", "fructose", "molasses", "honey", "agave", "sugar"
        ]
        found_sugars = [s for s in added_sugars if re.search(r"\b" + re.escape(s) + r"\b", raw_ing)]

        if nut and nut.sugar_g is not None:
            sug = nut.sugar_g
            if sug <= Config.LOW_SUGAR_MAX_G:
                assessments.append(ClinicalAssessment(
                    condition="Low Sugar Criterion",
                    status=ClinicalStatus.CLEAR,
                    reason=f"Verified Low Sugar: Only {sug}g sugars per serving (<= {Config.LOW_SUGAR_MAX_G}g).",
                    evidence=f"Reported Sugars: {sug}g/serving.",
                    matched_factors=[f"Sugar: {sug}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            else:
                assessments.append(ClinicalAssessment(
                    condition="Low Sugar Criterion",
                    status=ClinicalStatus.AVOID,
                    reason=f"Exceeds low-sugar limit: Contains {sug}g sugars per serving (Cap is {Config.LOW_SUGAR_MAX_G}g).",
                    evidence=f"Reported Sugars: {sug}g/serving.",
                    matched_factors=[f"Sugar: {sug}g"],
                    confidence=nut.confidence,
                    source=nut.source
                ))
            return

        # Ingredient-based evaluation
        if found_sugars:
            assessments.append(ClinicalAssessment(
                condition="Low Sugar Criterion",
                status=ClinicalStatus.AVOID,
                reason=f"Contains declared added sugars ({', '.join(found_sugars[:3])}). Fails low-sugar criteria.",
                evidence=f"Ingredients declare: {', '.join(found_sugars[:3])}.",
                matched_factors=found_sugars,
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        elif raw_ing:
            assessments.append(ClinicalAssessment(
                condition="Low Sugar Criterion",
                status=ClinicalStatus.CLEAR,
                reason="Verified Low Sugar: Declared ingredients are free from added sucrose, syrups, or refined sugars.",
                evidence=f"Audited {len(ing.ingredient_list) if ing else 0} ingredients; zero added sugars identified.",
                matched_factors=[],
                confidence=SourceConfidence.HIGH,
                source="Ingredient Formulation Audit"
            ))
        else:
            assessments.append(ClinicalAssessment(
                condition="Low Sugar Criterion",
                status=ClinicalStatus.UNKNOWN,
                reason="Sugar status cannot be assessed; ingredient declaration missing.",
                evidence="No ingredients declaration provided.",
                matched_factors=[],
                confidence=SourceConfidence.UNVERIFIED,
                source="Packaging Audit"
            ))
