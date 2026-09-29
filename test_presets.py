"""
SafeBite AI - Quick Presets & Multi-Location Test Suite
Verifies data integrity for all 11 core health presets,
filter parameter translation, session state binding, and location serviceability routing.
"""

import unittest
from presets import HEALTH_PRESETS, get_all_presets, get_preset, apply_preset_to_session
from location_manager import LocationManager

class TestPresetsAndLocations(unittest.TestCase):

    def test_all_11_presets_registered(self):
        """All 11 required quick presets must be registered with complete metadata."""
        expected_presets = [
            "high_protein", "low_sugar", "diabetes_friendly", "heart_conscious",
            "gluten_free", "dairy_free", "peanut_free", "low_sodium",
            "vegetarian", "vegan", "budget_friendly"
        ]
        all_presets = get_all_presets()
        self.assertEqual(len(all_presets), 11)

        for p_id in expected_presets:
            p = get_preset(p_id)
            self.assertIsNotNone(p, f"Missing preset: {p_id}")
            self.assertGreater(len(p.name), 0)
            self.assertGreater(len(p.user_name), 0)
            self.assertIsInstance(p.location, dict)
            self.assertGreater(len(p.sample_queries), 0)

    def test_preset_filter_translation(self):
        """Presets must translate into structured numerical and categorical filters."""
        # Low Sugar preset
        ls = get_preset("low_sugar")
        self.assertEqual(ls.filters.max_total_sugar_g, 5.0)
        self.assertEqual(ls.filters.max_added_sugar_g, 0.0)

        # High Protein preset
        hp = get_preset("high_protein")
        self.assertEqual(hp.filters.min_protein_g, 15.0)

        # Low Sodium preset
        l_sod = get_preset("low_sodium")
        self.assertEqual(l_sod.filters.max_sodium_mg, 140.0)

        # Celiac / Gluten-Free preset
        gf = get_preset("gluten_free")
        self.assertIn("gluten", [a.lower() for a in gf.filters.excluded_allergens])

    def test_apply_preset_to_session_state(self):
        """Applying preset must update both persistent keys and Streamlit widget keys."""
        mock_session = {}
        success = apply_preset_to_session("diabetes_friendly", mock_session)
        self.assertTrue(success)

        # Verify persistent keys
        self.assertEqual(mock_session["profile_name"], "Alex")
        self.assertIn("Diabetes", mock_session["profile_med"])
        self.assertEqual(mock_session["profile_city"], "Bengaluru")

        # Verify widget keys (ensures Streamlit UI inputs update synchronously)
        self.assertEqual(mock_session["input_user_name"], "Alex")
        self.assertIn("Diabetes", mock_session["input_medical_history"])
        self.assertEqual(mock_session["input_city"], "Bengaluru")
        self.assertIn("diabetic", mock_session["intel_query_input"].lower())

    def test_multi_location_serviceability(self):
        """LocationManager accurately determines retail serviceability without false claims."""
        # Indian Metro (Bengaluru) -> Quick commerce active
        bengaluru_res = LocationManager.get_serviceability("Blinkit", "Bengaluru", "India")
        self.assertTrue(bengaluru_res["serviceable"])
        self.assertTrue(bengaluru_res["verified"])

        # Non-metro or international city -> Quick commerce requires verification
        rural_res = LocationManager.get_serviceability("Blinkit", "Shimla", "India")
        self.assertFalse(rural_res["verified"])
        self.assertIn("verification", rural_res["note"].lower())

        # USA location -> Amazon active, Blinkit unverified
        us_amazon = LocationManager.get_serviceability("Amazon", "New York", "United States")
        self.assertTrue(us_amazon["serviceable"])
        self.assertIn("Amazon.com", us_amazon["note"])

if __name__ == "__main__":
    unittest.main()
