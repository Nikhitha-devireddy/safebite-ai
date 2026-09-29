"""
SafeBite AI - Evidence Cross-Validation Engine
Detects cross-source discrepancies across Open Food Facts, official brand packaging,
and e-commerce retailer listings. Computes aggregate evidence provenance and confidence.
Delegates clinical safety evaluation to the deterministic ClinicalRuleEngine.
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    RetailerOffer, Evidence, SourceConfidence, ClinicalStatus
)
from clinical_engine import ClinicalRuleEngine

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
        # Check sugar declarations against marketing titles
        if nutrition and nutrition.sugar_g is not None:
            for offer in retailer_offers:
                # If retailer text claims 'Sugar Free' or 'No Sugar' but sugar_g > 2.0g
                if re.search(r"\b(?:sugar\s*free|zero\s*sugar|no\s*sugar)\b", offer.product_name, re.I) and nutrition.sugar_g > 2.0:
                    conflicts.append(f"Sugar Discrepancy: '{offer.retailer}' title claims Zero/Sugar Free, but verified lab panel records {nutrition.sugar_g}g sugars.")

        # 2. Cross-check allergen conflicts
        if allergens:
            for offer in retailer_offers:
                # If retailer claims nut-free but allergens contains peanut or tree nuts
                has_nuts = any("nut" in c.lower() or "peanut" in c.lower() or "almond" in c.lower() for c in allergens.contains)
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
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        food_preferences: str = ""
    ) -> Tuple[str, List[str]]:
        """
        Assesses product against user's specific health conditions and allergies.
        Integrates with the new deterministic ClinicalRuleEngine.
        Returns:
            (Verdict: 'SAFE' | 'PARTIALLY SAFE' | 'UNSAFE' | 'NOT VERIFIED', List[Reasons])
        """
        user_allergies = user_allergies or []
        overall_status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=product,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies,
            food_preferences=food_preferences
        )

        # Store assessments directly on the product model
        product.clinical_assessments = assessments

        # Map ClinicalStatus enum to backward-compatible string verdict
        if overall_status == ClinicalStatus.AVOID:
            legacy_verdict = "UNSAFE"
        elif overall_status == ClinicalStatus.CAUTION:
            legacy_verdict = "PARTIALLY SAFE"
        elif overall_status == ClinicalStatus.UNKNOWN:
            legacy_verdict = "NOT VERIFIED"
        else:
            legacy_verdict = "SAFE"

        return legacy_verdict, reasons
