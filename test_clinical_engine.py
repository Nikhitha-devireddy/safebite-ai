"""
SafeBite AI - Clinical Engine Test Suite
Tests deterministic condition evaluations across Diabetes, Hypertension,
Allergies, Celiac Disease, Lactose Intolerance, Vegan, Vegetarian, and UNKNOWN state integrity.
"""

import sys
import unittest

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    Evidence, SourceConfidence, ClinicalStatus
)
from clinical_engine import ClinicalRuleEngine

class TestClinicalEngine(unittest.TestCase):

    def setUp(self):
        self.evidence = Evidence(last_verified="2026-09-29T12:00:00Z", overall_confidence=SourceConfidence.HIGH)

    def test_unknown_state_when_nutrition_and_ingredients_missing(self):
        """Rule: Lack of evidence MUST return UNKNOWN. Lack of evidence is NEVER assumed SAFE."""
        mystery_product = Product(
            id="SB-MYSTERY-001",
            name="Mystery Food",
            brand="Unknown",
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=mystery_product,
            user_medical_history="Type 2 Diabetes, Hypertension",
            user_allergies=["Peanuts", "Dairy"]
        )
        self.assertEqual(status, ClinicalStatus.UNKNOWN)
        # Verify conditions return UNKNOWN
        for a in assessments:
            self.assertEqual(a.status, ClinicalStatus.UNKNOWN)

    def test_diabetes_high_sugar_triggers_avoid(self):
        """Diabetes: High total sugar (>10g) must trigger AVOID."""
        sugary_product = Product(
            id="SB-SUGAR-001",
            name="Sweet Energy Bar",
            brand="SugarCo",
            nutrition=NutritionFacts(sugar_g=18.0, carbs_g=35.0, calories=250),
            ingredients=Ingredients(raw_text="Oats, cane sugar, honey."),
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=sugary_product,
            user_medical_history="Type 2 Diabetes",
            user_allergies=[]
        )
        self.assertEqual(status, ClinicalStatus.AVOID)
        diabetes_assess = [a for a in assessments if "Diabetes" in a.condition][0]
        self.assertEqual(diabetes_assess.status, ClinicalStatus.AVOID)
        self.assertIn("18.0g", diabetes_assess.evidence)

    def test_diabetes_low_sugar_triggers_clear(self):
        """Diabetes: Low sugar (<=5g) with zero high-fructose syrups triggers CLEAR."""
        low_sugar_product = Product(
            id="SB-LOWSUG-001",
            name="Keto Almond Bar",
            brand="KetoLife",
            nutrition=NutritionFacts(sugar_g=1.5, carbs_g=8.0, calories=190),
            ingredients=Ingredients(raw_text="Almonds, chicory root fiber, monk fruit."),
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=low_sugar_product,
            user_medical_history="Type 2 Diabetes",
            user_allergies=[]
        )
        self.assertEqual(status, ClinicalStatus.CLEAR)
        diabetes_assess = [a for a in assessments if "Diabetes" in a.condition][0]
        self.assertEqual(diabetes_assess.status, ClinicalStatus.CLEAR)

    def test_hypertension_sodium_thresholds(self):
        """Hypertension: > 400mg triggers AVOID, <= 140mg triggers CLEAR."""
        salty_product = Product(
            id="SB-SALT-001",
            name="Salted Chips",
            brand="ChipCo",
            nutrition=NutritionFacts(sodium_mg=650.0, calories=200),
            ingredients=Ingredients(raw_text="Potatoes, vegetable oil, salt, monosodium glutamate."),
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=salty_product,
            user_medical_history="Hypertension",
            user_allergies=[]
        )
        self.assertEqual(status, ClinicalStatus.AVOID)

        low_salt_product = Product(
            id="SB-LOWSALT-001",
            name="Unsalted Walnuts",
            brand="NutCo",
            nutrition=NutritionFacts(sodium_mg=5.0, calories=180),
            ingredients=Ingredients(raw_text="Raw walnuts."),
            evidence=self.evidence
        )
        status2, assessments2, reasons2 = ClinicalRuleEngine.evaluate(
            product=low_salt_product,
            user_medical_history="Hypertension",
            user_allergies=[]
        )
        self.assertEqual(status2, ClinicalStatus.CLEAR)

    def test_peanut_allergy_direct_and_traces(self):
        """Peanut allergy: direct ingredient triggers AVOID, traces triggers CAUTION."""
        direct_peanut_prod = Product(
            id="SB-PEANUT-001",
            name="Crunchy Peanut Butter",
            brand="NutCo",
            ingredients=Ingredients(raw_text="Roasted peanuts, sea salt."),
            allergens=Allergens(contains=["peanuts"]),
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=direct_peanut_prod,
            user_medical_history="None",
            user_allergies=["Peanuts"]
        )
        self.assertEqual(status, ClinicalStatus.AVOID)

        trace_peanut_prod = Product(
            id="SB-PEANUT-002",
            name="Almond Flour Cookie",
            brand="BakeryCo",
            ingredients=Ingredients(raw_text="Almonds, coconut flour, maple syrup."),
            allergens=Allergens(contains=["almonds"], may_contain=["peanuts"]),
            evidence=self.evidence
        )
        status2, assessments2, reasons2 = ClinicalRuleEngine.evaluate(
            product=trace_peanut_prod,
            user_medical_history="None",
            user_allergies=["Peanuts"]
        )
        self.assertEqual(status2, ClinicalStatus.CAUTION)

    def test_dairy_allergy_hidden_derivatives(self):
        """Dairy allergy: casein, whey, sodium caseinate must trigger AVOID."""
        casein_prod = Product(
            id="SB-DAIRY-001",
            name="Protein Cookie",
            brand="FitCo",
            ingredients=Ingredients(raw_text="Oat flour, sodium caseinate, cocoa powder, stevia."),
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=casein_prod,
            user_medical_history="None",
            user_allergies=["Dairy"]
        )
        self.assertEqual(status, ClinicalStatus.AVOID)
        self.assertTrue(any("sodium caseinate" in a.evidence for a in assessments))

    def test_celiac_disease_gluten_grains(self):
        """Celiac: Wheat, barley, rye, malt trigger AVOID."""
        gluten_prod = Product(
            id="SB-GLUTEN-001",
            name="Malt Cereal",
            brand="MorningCo",
            ingredients=Ingredients(raw_text="Whole wheat, barley malt extract, sugar, salt."),
            evidence=self.evidence
        )
        status, assessments, reasons = ClinicalRuleEngine.evaluate(
            product=gluten_prod,
            user_medical_history="Celiac Disease",
            user_allergies=[]
        )
        self.assertEqual(status, ClinicalStatus.AVOID)

    def test_vegan_and_vegetarian_compliance(self):
        """Gelatin and carmine must trigger AVOID for vegetarian and vegan."""
        gelatin_prod = Product(
            id="SB-NONVEG-001",
            name="Fruit Gummies",
            brand="CandyCo",
            ingredients=Ingredients(raw_text="Glucose syrup, sugar, beef gelatin, natural colors."),
            evidence=self.evidence
        )
        status_veg, _, _ = ClinicalRuleEngine.evaluate(product=gelatin_prod, food_preferences="Vegetarian")
        self.assertEqual(status_veg, ClinicalStatus.AVOID)

        status_vegan, _, _ = ClinicalRuleEngine.evaluate(product=gelatin_prod, food_preferences="Vegan")
        self.assertEqual(status_vegan, ClinicalStatus.AVOID)

    def test_bulleted_ingredient_extraction_and_audit(self):
        """Pasted bulleted ingredient lists without 'Ingredients:' header must parse and audit properly."""
        from nutrition_extractor import NutritionExtractor
        raw_input = """• Granulated sugar: Provides the main structure and sweetness.
• Water: Used to bloom the gelatin and dissolve the sugar.
• Unflavored gelatin: Acts as the gelling agent that gives marshmallows their spongy, bouncy texture.
• Light corn syrup: Works as an invert sugar.
• Salt: Enhances and balances the overall sweetness."""
        nut, ing, allg = NutritionExtractor.extract_from_text(raw_input)
        self.assertIsNotNone(ing.raw_text)
        self.assertIn("Granulated sugar", ing.ingredient_list)
        self.assertIn("Unflavored gelatin", ing.ingredient_list)
        self.assertIn("Light Corn Syrup", ing.additives)

        prod = Product(
            id="SB-BULLET-001",
            name="Marshmallow",
            brand="Confectionery",
            nutrition=nut,
            ingredients=ing,
            allergens=allg,
            evidence=self.evidence
        )
        # Audit with no specified condition -> must generate Ingredient & Additive Screening
        status, assessments, reasons = ClinicalRuleEngine.evaluate(prod)
        self.assertEqual(status, ClinicalStatus.CLEAR)
        self.assertEqual(len(assessments), 1)
        self.assertEqual(assessments[0].condition, "Ingredient & Additive Screening")

        # Audit with Vegan -> must flag gelatin
        status_veg, assessments_veg, _ = ClinicalRuleEngine.evaluate(prod, food_preferences="Vegan")
        self.assertEqual(status_veg, ClinicalStatus.AVOID)

    def test_pure_ingredient_evaluation_without_nutrition_table(self):
        """Clinical safety must evaluate accurately from ingredients even when numerical nutrition table is absent."""
        from nutrition_extractor import NutritionExtractor
        
        # Product 1: High sugar + salt, no nutrition table
        candy_input = "Corn syrup, sugar, gelatin, salt, artificial flavor"
        nut1, ing1, allg1 = NutritionExtractor.extract_from_text(candy_input)
        candy_prod = Product(id="P1", name="Candy", brand="B", nutrition=nut1, ingredients=ing1, allergens=allg1, evidence=self.evidence)

        # Diabetic check -> must flag sugar/syrups as AVOID
        status_diab, ass_diab, _ = ClinicalRuleEngine.evaluate(candy_prod, user_medical_history="Type 2 Diabetes")
        self.assertEqual(status_diab, ClinicalStatus.AVOID)
        self.assertEqual(ass_diab[0].status, ClinicalStatus.AVOID)

        # Hypertension check -> must flag salt as CAUTION
        status_hyp, ass_hyp, _ = ClinicalRuleEngine.evaluate(candy_prod, user_medical_history="Hypertension")
        self.assertEqual(status_hyp, ClinicalStatus.CAUTION)

        # Product 2: Clean seed mix with no salt, no sugar, no nutrition table
        clean_input = "Chia seeds, flaxseeds, pumpkin seeds, raw almonds, organic cinnamon"
        nut2, ing2, allg2 = NutritionExtractor.extract_from_text(clean_input)
        clean_prod = Product(id="P2", name="Seed Mix", brand="B", nutrition=nut2, ingredients=ing2, allergens=allg2, evidence=self.evidence)

        # Diabetic check -> must evaluate as CLEAR
        status_c_diab, ass_c_diab, _ = ClinicalRuleEngine.evaluate(clean_prod, user_medical_history="Type 2 Diabetes")
        self.assertEqual(status_c_diab, ClinicalStatus.CLEAR)

        # Hypertension check -> must evaluate as CLEAR
        status_c_hyp, ass_c_hyp, _ = ClinicalRuleEngine.evaluate(clean_prod, user_medical_history="Hypertension")
        self.assertEqual(status_c_hyp, ClinicalStatus.CLEAR)

if __name__ == "__main__":
    unittest.main()


