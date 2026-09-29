import sys
import unittest

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens, RetailerOffer,
    Evidence, SourceConfidence
)
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer
from evidence_engine import EvidenceEngine
from retailer_sources.amazon import AmazonRetailer
from retailer_sources.bigbasket import BigBasketRetailer
from retailer_sources.blinkit import BlinkitRetailer
from retailer_sources.zepto import ZeptoRetailer
from product_sources import ProductSources
from product_search import ProductSearchPipeline

class TestProductIntelligenceEngine(unittest.TestCase):

    def test_nutrition_extractor_open_food_facts(self):
        """Verify strict deterministic extraction from Open Food Facts schema."""
        sample_off = {
            "code": "890600102030",
            "product_name": "Organic Almond Butter",
            "brands": "The Whole Truth Foods",
            "ingredients_text": "Dry roasted almonds, sea salt.",
            "allergens_tags": ["en:almonds", "en:nuts"],
            "traces_tags": ["en:peanuts"],
            "nutriments": {
                "energy-kcal_100g": 590,
                "sugars_100g": 3.8,
                "carbohydrates_100g": 18.0,
                "proteins_100g": 22.0,
                "fat_100g": 52.0,
                "saturated-fat_100g": 4.5,
                "fiber_100g": 10.5,
                "sodium_100g": 0.12 # 0.12g = 120mg
            }
        }
        nut, ing, allg = NutritionExtractor.extract_from_open_food_facts(sample_off)
        
        self.assertEqual(nut.calories, 590.0)
        self.assertEqual(nut.sugar_g, 3.8)
        self.assertEqual(nut.protein_g, 22.0)
        self.assertEqual(nut.sodium_mg, 120.0)
        self.assertEqual(nut.confidence, SourceConfidence.HIGH)

        self.assertIn("almonds", allg.contains)
        self.assertIn("peanuts", allg.may_contain)
        self.assertTrue(ing.is_clean_label)
        self.assertEqual(len(ing.additives), 0)

    def test_rule_1_never_invent_nutrition(self):
        """Rule 1 & 7: Missing nutrition fields MUST remain None and marked UNVERIFIED."""
        sample_missing = {
            "code": "123456",
            "product_name": "Mystery Snack",
            "nutriments": {} # Empty nutriments
        }
        nut, ing, allg = NutritionExtractor.extract_from_open_food_facts(sample_missing)
        self.assertIsNone(nut.calories)
        self.assertIsNone(nut.sugar_g)
        self.assertIsNone(nut.protein_g)
        self.assertEqual(nut.confidence, SourceConfidence.UNVERIFIED)

    def test_product_normalizer(self):
        """Tests exact variant and pack size matching."""
        brand = ProductNormalizer.normalize_brand("The Whole Truth Foods Pvt Ltd")
        self.assertEqual(brand, "The Whole Truth")

        pack = ProductNormalizer.extract_pack_size("The Whole Truth Double Cocoa Bar 52g")
        self.assertEqual(pack, "52g")

        variant = ProductNormalizer.extract_variant("The Whole Truth Protein Bar - Double Cocoa (Pack of 6)")
        self.assertEqual(variant, "Double Cocoa")

        # Test mismatch detection
        is_match, reason = ProductNormalizer.is_exact_match(
            "The Whole Truth Double Cocoa Bar 52g",
            "The Whole Truth Double Cocoa Bar 500g"
        )
        self.assertFalse(is_match)
        self.assertIn("Pack size mismatch", reason)

        is_match2, reason2 = ProductNormalizer.is_exact_match(
            "The Whole Truth Protein Bar - Peanut Butter 52g",
            "The Whole Truth Protein Bar - Double Cocoa 52g"
        )
        self.assertFalse(is_match2)
        self.assertIn("Variant formulation mismatch", reason2)

    def test_retailer_sources_graceful_fallbacks(self):
        """Rule 8 & 9: Respect rate limits and provide robust fallback offers without crashing."""
        for RetailerClass, expected_name in [
            (AmazonRetailer, "Amazon"),
            (BigBasketRetailer, "BigBasket"),
            (BlinkitRetailer, "Blinkit"),
            (ZeptoRetailer, "Zepto")
        ]:
            retailer = RetailerClass(enabled=True)
            offers = retailer.search(query="Dark Chocolate 85%", location="Bengaluru")
            self.assertIsInstance(offers, list)
            self.assertGreaterEqual(len(offers), 1)
            offer = offers[0]
            self.assertEqual(offer.retailer, expected_name)
            self.assertTrue(offer.product_url.startswith("http"))
            self.assertTrue("Bengaluru" in (offer.availability_status or "") or (offer.location and "Bengaluru" in offer.location))

    def test_evidence_engine_conflict_detection(self):
        """Rule 6: Visible detection of cross-source conflicts."""
        nutrition = NutritionFacts(sugar_g=12.5, source="Verified Lab Panel")
        offers = [
            RetailerOffer(
                retailer="Amazon",
                product_name="Brand Super Snack Zero Sugar Bar",
                product_url="https://amazon.in/dp/example",
                in_stock=True,
                retrieved_at="2026-09-29T10:00:00Z"
            )
        ]
        evidence, conf = EvidenceEngine.cross_validate(
            nutrition=nutrition,
            ingredients=None,
            allergens=None,
            retailer_offers=offers,
            sources_consulted=["Lab Panel", "Amazon"],
            source_urls=["https://amazon.in/dp/example"]
        )
        self.assertGreater(len(evidence.conflicts_detected), 0)
        self.assertIn("Sugar Discrepancy", evidence.conflicts_detected[0])
        self.assertEqual(conf, SourceConfidence.LOW)

    def test_evidence_engine_clinical_safety_evaluations(self):
        """SafeBite Health & Allergen screening with strict allergen trigger and diabetes rules."""
        sample_prod = Product(
            id="SB-TEST-001",
            name="Peanut Butter Crunch Bar",
            brand="Energy Brands",
            nutrition=NutritionFacts(calories=220, sugar_g=14.0, protein_g=10.0, sodium_mg=90.0, source="OFF"),
            ingredients=Ingredients(raw_text="Peanuts, whey protein, honey, salt.", is_clean_label=True),
            allergens=Allergens(contains=["peanuts", "milk"], free_from=[]),
            evidence=Evidence(last_verified="2026-09-29T10:00:00Z")
        )

        # 1. User allergic to Peanuts -> MUST BE UNSAFE
        verdict1, reasons1 = EvidenceEngine.evaluate_clinical_safety(
            product=sample_prod,
            user_medical_history="None",
            user_allergies=["Peanuts"]
        )
        self.assertEqual(verdict1, "UNSAFE")
        self.assertTrue(any("STRICT ALLERGEN TRIGGER" in r for r in reasons1))

        # 2. User with Type 2 Diabetes -> High sugar (14g) MUST trigger risk
        verdict2, reasons2 = EvidenceEngine.evaluate_clinical_safety(
            product=sample_prod,
            user_medical_history="Type 2 Diabetes",
            user_allergies=[]
        )
        self.assertEqual(verdict2, "UNSAFE")
        self.assertTrue(any("HIGH GLYCEMIC RISK" in r for r in reasons2))

        # 3. Clean product with low sugar and safe profile
        safe_prod = Product(
            id="SB-TEST-002",
            name="Organic 100% Cocoa Dark Bar",
            brand="Pascati",
            nutrition=NutritionFacts(calories=180, sugar_g=2.0, protein_g=4.0, sodium_mg=10.0, source="OFF"),
            ingredients=Ingredients(raw_text="Organic cocoa beans, organic cocoa butter.", is_clean_label=True),
            allergens=Allergens(contains=[], free_from=["dairy", "gluten", "peanuts"]),
            evidence=Evidence(last_verified="2026-09-29T10:00:00Z")
        )
        verdict3, reasons3 = EvidenceEngine.evaluate_clinical_safety(
            product=safe_prod,
            user_medical_history="Type 2 Diabetes",
            user_allergies=["Peanuts", "Dairy"]
        )
        self.assertEqual(verdict3, "SAFE")
        self.assertTrue(any("Clinically cleared" in r for r in reasons3))

    def test_query_criteria_parser(self):
        """Tests parsing complex natural language queries into structured search criteria."""
        pipeline = ProductSearchPipeline()
        query = "Find low-sugar protein bars without peanuts under ₹500 available in Bengaluru."
        criteria = pipeline.parse_query_criteria(query)
        
        self.assertEqual(criteria["search_term"], "protein bars")
        self.assertEqual(criteria["max_price"], 500.0)
        self.assertTrue(criteria["low_sugar"])
        self.assertIn("peanuts", criteria["excluded_allergens"])
        self.assertEqual(criteria["location"], "Bengaluru")

if __name__ == "__main__":
    unittest.main()
