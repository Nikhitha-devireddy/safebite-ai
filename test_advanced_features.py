"""
SafeBite AI - Advanced 10/10 Technical Features Test Suite
Tests:
- Continuous Glucose Monitor (CGM) Blood Sugar Curve Predictor
- NOVA Food Processing Classification (Groups 1 to 4)
- 6-Axis Clinical Nutritional Radar Matrix
- Smart Safe Swap Recommender Engine with delta percentage comparisons
"""

import unittest
from schemas import NutritionFacts, Ingredients, Allergens
from cgm_simulator import (
    CgmGlucosePredictor,
    NovaProcessingScorer,
    ClinicalRadarMatrix,
    SmartSafeSwapEngine
)


class TestAdvancedFeatures(unittest.TestCase):

    def test_cgm_glucose_simulation_high_sugar(self):
        """High glycemic food must trigger Dangerous Spike with rapid velocity."""
        high_sugar_nut = NutritionFacts(
            calories=350.0,
            carbs_g=65.0,
            sugar_g=45.0,
            fiber_g=1.0,
            protein_g=2.0,
            fat_g=3.0
        )
        sim = CgmGlucosePredictor.simulate_glucose_curve(high_sugar_nut, is_diabetic=True)
        self.assertTrue(sim["available"])
        self.assertGreater(sim["peak_glucose"], 140.0)
        self.assertEqual(sim["risk_level"], "DANGEROUS_SPIKE")
        self.assertGreater(sim["glycemic_load"], 20.0)
        self.assertEqual(len(sim["curve"]), 11)
        self.assertIn("<svg", sim["svg_chart"])

    def test_cgm_glucose_simulation_low_gi_buffered(self):
        """High protein, high fiber, low net-carb food must produce a stable glycemic curve."""
        clean_nut = NutritionFacts(
            calories=220.0,
            carbs_g=14.0,
            sugar_g=1.5,
            fiber_g=8.0,
            protein_g=18.0,
            fat_g=12.0
        )
        sim = CgmGlucosePredictor.simulate_glucose_curve(clean_nut, is_diabetic=False)
        self.assertTrue(sim["available"])
        self.assertEqual(sim["risk_level"], "STABLE_GLYCEMIC")
        self.assertLess(sim["delta_peak"], 30.0)
        self.assertEqual(sim["net_carbs_g"], 6.0)

    def test_nova_processing_classification(self):
        """NOVA Classification must differentiate whole foods from ultra-processed formulations (UPF)."""
        # NOVA 4: Ultra-processed formulation with emulsifiers and artificial sweeteners
        upf_ing = "Sugar, Fractionated Palm Oil, Maltodextrin, Polysorbate 80, Sucralose, E471, Artificial Vanilla Flavor"
        res_upf = NovaProcessingScorer.evaluate_nova("Frosted Cream Cookies", upf_ing, additives_count=4)
        self.assertEqual(res_upf["nova_group"], 4)
        self.assertIn("NOVA 4", res_upf["nova_badge"])
        self.assertLess(res_upf["clean_label_score"], 60)
        self.assertGreater(len(res_upf["upf_markers_found"]), 0)

        # NOVA 1: Whole grain oats / single ingredient
        clean_ing = "100% Organic Rolled Oats"
        res_clean = NovaProcessingScorer.evaluate_nova("Rolled Oats", clean_ing, additives_count=0)
        self.assertEqual(res_clean["nova_group"], 1)
        self.assertIn("NOVA 1", res_clean["nova_badge"])
        self.assertGreaterEqual(res_clean["clean_label_score"], 95)

    def test_clinical_radar_matrix(self):
        """6-Axis Clinical Radar Matrix computes normalized scores across all health dimensions."""
        nut = NutritionFacts(
            calories=180.0,
            protein_g=14.0,
            carbs_g=12.0,
            sugar_g=2.0,
            fiber_g=7.0,
            fat_g=5.0,
            saturated_fat_g=1.0,
            sodium_mg=85.0
        )
        ing = Ingredients(
            raw_text="Organic Sprouted Quinoa, Pea Protein, Flaxseed, Sea Salt",
            additives=[],
            is_clean_label=True
        )
        scores = ClinicalRadarMatrix.compute_radar_scores(nut, ing, None)
        self.assertEqual(len(scores), 6)
        expected_axes = [
            "Glycemic Stability", "Cardiovascular Safety", "Gut Microbiome",
            "Protein Purity", "Clean Label", "Satiety Index"
        ]
        for axis in expected_axes:
            self.assertIn(axis, scores)
            self.assertGreaterEqual(scores[axis], 0.0)
            self.assertLessEqual(scores[axis], 100.0)

        # Clean food should achieve high Clean Label and Glycemic scores
        self.assertGreater(scores["Clean Label"], 80.0)
        self.assertGreater(scores["Glycemic Stability"], 75.0)

    def test_smart_safe_swap_engine(self):
        """Smart Safe Swap Engine provides 1:1 clean replacements with delta reductions."""
        swaps = SmartSafeSwapEngine.get_smart_swaps("Cadbury Dairy Milk Chocolate", "Confectionery")
        self.assertGreater(len(swaps), 0)
        swap = swaps[0]
        self.assertIn("swap_name", swap)
        self.assertIn("delta_sugar", swap)
        self.assertIn("clean_perks", swap)
        self.assertIn("-", swap["delta_sugar"])  # Must show reduction


if __name__ == "__main__":
    unittest.main()
