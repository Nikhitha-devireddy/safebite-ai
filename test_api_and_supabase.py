"""
Unit tests for Headless FastAPI REST API and Supabase Client
"""

import unittest
from starlette.testclient import TestClient
from api.main import app
import supabase_client

class TestApiAndSupabase(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("clinical_engine", data["engines"])
        self.assertIn("supabase", data)

    def test_cgm_simulation_endpoint(self):
        res = self.client.post("/api/v1/cgm/simulate", json={
            "carbohydrates_g": 50.0,
            "fiber_g": 6.0,
            "added_sugars_g": 15.0,
            "baseline_glucose": 90.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("peak_glucose", data)
        self.assertIn("curve", data)
        self.assertGreater(data["peak_glucose"], 90.0)

    def test_audit_endpoint(self):
        res = self.client.post("/api/v1/audit", json={
            "product_name": "Dark Chocolate 70%",
            "brand": "PureCacao",
            "ingredients_text": "Cocoa mass, sugar, cocoa butter, emulsifier (soy lecithin), vanilla flavor.",
            "nutrition": {
                "calories": 550,
                "carbohydrates_g": 35,
                "added_sugars_g": 28,
                "fiber_g": 8,
                "protein_g": 7,
                "sodium_mg": 20
            },
            "allergies": ["Dairy"],
            "medical_history": "General Health",
            "save_to_history": False
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("verdict", data)
        self.assertIn("nova_group", data)
        self.assertIn("fssai_compliance", data)
        # Cocoa butter is NOT dairy butter (false-positive filter verification)
        self.assertNotIn("Dairy / Milk", data.get("allergens_detected", []))

    def test_swaps_endpoint(self):
        res = self.client.post("/api/v1/swaps", json={"category": "chocolate"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["swaps_count"], 0)
        self.assertIn("recommendations", data)

    def test_supabase_client_connection(self):
        status = supabase_client.test_supabase_connection()
        self.assertIsInstance(status, dict)
        self.assertTrue(status.get("connected"))

if __name__ == "__main__":
    unittest.main()
