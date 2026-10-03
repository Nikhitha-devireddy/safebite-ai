"""
SafeBite AI - Indian Clinical & Regulatory Intelligence Engine Test Suite
Tests:
- FSSAI 14-digit license format validation
- FSSAI Veg / Non-Veg / Vegan / Fortified logo detection
- FSSAI HFSS (High Fat, Sugar, Salt) threshold evaluation
- Strict Jain Ahimsa dietary guardrails (Kandmool/root veg elimination)
- Navratri/Vrat sacred fasting compliance (Sendha Namak only, Kuttu/Singhara)
- Indian FMCG adulteration (Palm oil/Palmolein, Atta vs Maida masking, Hidden sugar syrups)
- Ayurvedic Viruddha Ahara (Incompatible food pairing) detection
- Shree Anna (National Millet Mission) superfood recommendation engine
"""

import unittest
from schemas import NutritionFacts
from indian_engine import (
    FssaiComplianceEngine,
    IndianDietaryGuardrail,
    IndianAdulterationDetector,
    AyurvedicEngine,
    MilletRecommendationEngine
)


class TestIndianEngine(unittest.TestCase):

    def test_fssai_license_validation(self):
        """14-digit FoSCoS license validation and state jurisdiction resolution."""
        # Valid Central License (Maharashtra - 27)
        res_valid = FssaiComplianceEngine.validate_license("Manufactured by Amul. Lic No: 10019043002767. Keep cool.")
        self.assertTrue(res_valid["valid"])
        self.assertEqual(res_valid["license_number"], "10019043002767")
        self.assertEqual(res_valid["license_type"], "FSSAI Central License")
        self.assertIn("FSSAI Lic", res_valid["formatted_badge"])

        # Invalid / missing license
        res_invalid = FssaiComplianceEngine.validate_license("Unbranded local snack with no registration.")
        self.assertFalse(res_invalid["valid"])
        self.assertIsNone(res_invalid["license_number"])

    def test_fssai_veg_nonveg_logos(self):
        """Mandatory FSSAI Category Logos: 🟢 Veg, 🟤 Non-Veg, 🌱 Vegan."""
        # Non-veg (contains gelatin)
        nv = FssaiComplianceEngine.detect_fssai_logos("Gummy Bears", "Sugar, Glucose Syrup, Beef Gelatin, Citric Acid")
        self.assertEqual(nv["logo_type"], "NON_VEG")
        self.assertIn("Non-Vegetarian", nv["badge"])

        # Lacto-Vegetarian (contains dairy/ghee)
        veg = FssaiComplianceEngine.detect_fssai_logos("Mysore Pak", "Besan, Pure Cow Ghee, Sugar")
        self.assertEqual(veg["logo_type"], "VEGETARIAN")
        self.assertIn("Vegetarian", veg["badge"])

        # Vegan (pure plant-based, no dairy/eggs/meat)
        vgn = FssaiComplianceEngine.detect_fssai_logos("Roasted Makhana", "Foxnuts, Cold-Pressed Groundnut Oil, Rock Salt")
        self.assertEqual(vgn["logo_type"], "VEGAN")
        self.assertIn("Vegan", vgn["badge"])

    def test_fssai_hfss_thresholds(self):
        """FSSAI High Fat, Sugar, Salt (HFSS) draft threshold limits."""
        # Unhealthy snack exceeding sugar and sodium
        bad_nut = NutritionFacts(
            sugar_g=22.0,      # > 10g threshold
            sodium_mg=450.0,   # > 250mg threshold
            saturated_fat_g=6.0 # > 4g threshold
        )
        res_bad = FssaiComplianceEngine.calculate_hfss(bad_nut)
        self.assertTrue(res_bad["is_hfss"])
        self.assertEqual(res_bad["level"], "CRITICAL_HFSS")
        self.assertEqual(len(res_bad["flags"]), 3)

        # Healthy clean food below thresholds
        good_nut = NutritionFacts(
            sugar_g=1.5,
            sodium_mg=90.0,
            saturated_fat_g=0.5
        )
        res_good = FssaiComplianceEngine.calculate_hfss(good_nut)
        self.assertFalse(res_good["is_hfss"])
        self.assertEqual(res_good["level"], "BALANCED")

    def test_strict_jain_compliance(self):
        """Strict Jain guardrail must eliminate root vegetables, garlic, onions, potato, honey, and yeast."""
        # Unsafe item with onion & potato
        unsafe_jain = "Potatoes, Refined Palmolein, Dehydrated Onion Powder, Garlic Powder, Salt"
        res_unsafe = IndianDietaryGuardrail.evaluate_jain(unsafe_jain)
        self.assertFalse(res_unsafe["compliant"])
        self.assertGreater(len(res_unsafe["violations"]), 0)

        # Safe Jain item
        safe_jain = "Roasted Makhana, Pure A2 Desi Cow Ghee, Sendha Namak, Roasted Jeera"
        res_safe = IndianDietaryGuardrail.evaluate_jain(safe_jain)
        self.assertTrue(res_safe["compliant"])
        self.assertEqual(len(res_safe["violations"]), 0)
        self.assertIn("Jain Certified", res_safe["badge"])

    def test_navratri_vrat_compliance(self):
        """Vrat fasting requires Sendha Namak and permitted flours (Kuttu/Singhara), blocking regular table salt & grains."""
        # Violation: Regular table salt and regular wheat
        unsafe_vrat = "Whole wheat flour, iodized table salt, cumin seeds, refined oil"
        res_unsafe = IndianDietaryGuardrail.evaluate_vrat(unsafe_vrat)
        self.assertFalse(res_unsafe["compliant"])

        # Compliant: Kuttu flour, Sendha Namak, roasted peanuts
        safe_vrat = "Buckwheat flour (Kuttu ka atta), Sendha Namak (Rock Salt), Roasted Peanuts, Cow Ghee"
        res_safe = IndianDietaryGuardrail.evaluate_vrat(safe_vrat)
        self.assertTrue(res_safe["compliant"])
        self.assertIn("Vrat", res_safe["badge"])

    def test_indian_adulteration_palm_oil_and_maida(self):
        """Detects Palm Oil / Palmolein and Atta-to-Maida masking."""
        # Product claiming Atta on front but using Maida and Palm Oil
        audit = IndianAdulterationDetector.audit_adulterants(
            product_name="Healthy Atta Biscuits",
            ingredients_text="Refined Wheat Flour (Maida), Refined Palmolein Oil, Invert Sugar Syrup, INS 211, Salt"
        )
        self.assertTrue(audit["has_palm_oil"])
        self.assertIsNotNone(audit["atta_masking"])
        self.assertGreater(len(audit["hidden_sugars"]), 0)
        self.assertGreater(len(audit["class_2_preservatives"]), 0)
        self.assertLess(audit["purity_score"], 50)

    def test_ayurvedic_viruddha_ahara(self):
        """Identifies incompatible food combinations (Viruddha Ahara)."""
        # Milk + Citrus Orange
        conflicts = AyurvedicEngine.evaluate_viruddha_ahara("Pasteurized Cow Milk, Orange Citrus Juice Extract, Sugar")
        self.assertGreater(len(conflicts), 0)
        self.assertIn("Milk + Sour/Citrus", conflicts[0]["name"])

    def test_shree_anna_millet_swaps(self):
        """Returns authentic Indian millet superfoods for high-carb items."""
        swaps = MilletRecommendationEngine.get_swaps_for_query("wheat cookies")
        self.assertGreater(len(swaps), 0)
        millet_names = [s["name"] for s in swaps]
        self.assertTrue(any("Ragi" in name for name in millet_names))


if __name__ == "__main__":
    unittest.main()
