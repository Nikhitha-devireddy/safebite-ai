import os
import sys
import unittest
from dotenv import load_dotenv

# Ensure Windows terminal can print unicode characters
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from recommendations import recommend_safe_products, process_automated_order
from schemas import UserLocation, ProductSafetyRequest

load_dotenv()

class TestRecommendations(unittest.TestCase):

    def test_recommendation_and_order_flow(self):
        """Testing safe product recommendations and order processing in India."""
        loc_india = {
            "country": "India",
            "state": "Karnataka",
            "city": "Bengaluru",
            "pincode": "560001",
            "address": "12 Indiranagar 100ft Rd"
        }

        products = recommend_safe_products(
            user_name="Alex",
            medical_history="Type 2 Diabetes",
            allergies=["Dairy"],
            food_preferences="Vegan",
            craving_query="Ice cream",
            location=loc_india
        )

        self.assertGreater(len(products), 0, "Should generate at least one product")

        sample_product = products[0]
        required_keys = [
            "name", "brand", "category", "natural_highlight", "key_ingredients",
            "medical_suitability", "allergen_guarantee", "estimated_price",
            "primary_order_link", "primary_retailer_name",
            "secondary_order_link", "secondary_retailer_name"
        ]
        for key in required_keys:
            self.assertIn(key, sample_product, f"Missing key '{key}' in recommended product")

        order = process_automated_order(
            product=sample_product,
            user_name="Alex",
            location=loc_india,
            quantity=2
        )

        self.assertIsNotNone(order.get("order_id"))
        self.assertEqual(order.get("status"), "Order Dispatched & In Transit")
        self.assertIn("delivery_eta", order)
        self.assertIn("total_price", order)

        order_keys = [
            "order_id", "product_name", "brand", "quantity", "unit_price",
            "total_price", "recipient_name", "delivery_location", "delivery_eta",
            "direct_checkout_url", "secondary_checkout_url", "quick_commerce_url",
            "primary_retailer", "secondary_retailer", "quick_commerce_retailer"
        ]
        for ok in order_keys:
            self.assertIn(ok, order, f"Missing key '{ok}' in order result")

        self.assertIn("full_formatted_address", order["delivery_location"])

    def test_us_location_recommendations(self):
        """Testing US location retailer routing and direct product pages."""
        loc_us = {
            "country": "United States",
            "state": "NY",
            "city": "New York",
            "pincode": "10001",
            "address": "452 Broadway"
        }
        products = recommend_safe_products(
            user_name="Sarah",
            medical_history="Celiac Disease",
            allergies=["Gluten"],
            food_preferences="Vegetarian",
            craving_query="Cookies",
            location=loc_us
        )
        self.assertGreater(len(products), 0)
        p = products[0]
        self.assertIn("Amazon", p["primary_retailer_name"])
        self.assertIn("secondary_retailer_name", p)

if __name__ == "__main__":
    unittest.main()
