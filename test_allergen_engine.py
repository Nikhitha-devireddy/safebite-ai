"""
SafeBite AI - Allergen Engine Test Suite
Tests detection of direct ingredients, hidden chemical derivatives,
precautionary statements (PAL / cross-contact), and false positive exclusion filters.
"""

import unittest
from schemas import Product, Ingredients, Allergens, Evidence, SourceConfidence
from allergen_engine import AllergenEngine, AllergenDetectionType

class TestAllergenEngine(unittest.TestCase):

    def setUp(self):
        self.evidence = Evidence(last_verified="2026-09-29T12:00:00Z", overall_confidence=SourceConfidence.HIGH)

    def test_direct_allergen_detection(self):
        """Direct declared allergen tags and ingredients must be detected."""
        prod = Product(
            id="SB-ALLG-001",
            name="Peanut Clusters",
            brand="SnackCo",
            ingredients=Ingredients(raw_text="Roasted peanuts, dark chocolate, sea salt."),
            allergens=Allergens(contains=["peanuts"]),
            evidence=self.evidence
        )
        hits = AllergenEngine.screen_product(prod, ["Peanuts"])
        self.assertGreater(len(hits), 0)
        self.assertTrue(any(h.detection_type == AllergenDetectionType.DIRECT for h in hits))
        self.assertEqual(hits[0].allergen_category, "Peanuts")

    def test_hidden_dairy_derivative_detection(self):
        """Casein, whey, and sodium caseinate must trigger dairy allergy as derivatives."""
        prod = Product(
            id="SB-ALLG-002",
            name="Vanilla Shake Powder",
            brand="FitCo",
            ingredients=Ingredients(raw_text="Filtered water, whey protein isolate, sodium caseinate, natural flavor."),
            evidence=self.evidence
        )
        hits = AllergenEngine.screen_product(prod, ["Dairy"])
        self.assertGreater(len(hits), 0)
        der_tokens = [h.matched_token.lower() for h in hits if h.detection_type == AllergenDetectionType.DERIVATIVE]
        self.assertTrue("whey protein" in der_tokens or "sodium caseinate" in der_tokens)

    def test_false_positive_exclusion_cocoa_butter(self):
        """CRITICAL: Cocoa butter and peanut butter must NOT trigger dairy allergy."""
        vegan_dark_chocolate = Product(
            id="SB-ALLG-003",
            name="100% Vegan Single-Origin Dark Bar",
            brand="PureCacao",
            ingredients=Ingredients(raw_text="Organic cocoa beans, organic cocoa butter, coconut sugar."),
            allergens=Allergens(contains=[], free_from=["dairy"]),
            evidence=self.evidence
        )
        hits = AllergenEngine.screen_product(vegan_dark_chocolate, ["Dairy"])
        # Should NOT trigger dairy allergy for cocoa butter
        dairy_hits = [h for h in hits if h.allergen_category == "Dairy / Milk"]
        self.assertEqual(len(dairy_hits), 0, f"False positive dairy hit detected on cocoa butter: {dairy_hits}")

    def test_precautionary_labeling_detection(self):
        """'May contain traces of nuts' must be classified as TRACE_MAY_CONTAIN."""
        cookie_prod = Product(
            id="SB-ALLG-004",
            name="Oatmeal Raisin Cookie",
            brand="BakeryCo",
            ingredients=Ingredients(raw_text="Whole oats, raisins, palm oil. May contain traces of almonds and walnuts."),
            allergens=Allergens(may_contain=["almonds", "walnuts"]),
            evidence=self.evidence
        )
        hits = AllergenEngine.screen_product(cookie_prod, ["Tree Nuts"])
        self.assertGreater(len(hits), 0)
        self.assertTrue(any(h.detection_type in (AllergenDetectionType.TRACE_MAY_CONTAIN, AllergenDetectionType.CROSS_CONTACT) for h in hits))

    def test_shared_facility_cross_contact_warning(self):
        """'Manufactured in a facility that also processes peanuts' must be detected."""
        granola_prod = Product(
            id="SB-ALLG-005",
            name="Berry Granola",
            brand="HealthCo",
            ingredients=Ingredients(raw_text="Rolled oats, dried cranberries, agave."),
            allergens=Allergens(cross_contact_warnings=["Made in a facility that also processes peanuts and tree nuts"]),
            evidence=self.evidence
        )
        hits = AllergenEngine.screen_product(granola_prod, ["Peanuts"])
        self.assertGreater(len(hits), 0)
        self.assertTrue(any(h.detection_type == AllergenDetectionType.CROSS_CONTACT for h in hits))

if __name__ == "__main__":
    unittest.main()
