import os
import sys
from dotenv import load_dotenv

# Ensure Windows terminal can print unicode characters
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
from recommendations import recommend_safe_products, process_automated_order
from schemas import UserLocation, ProductSafetyRequest

load_dotenv()

def test_recommendation_and_order_flow():
    print("\n--- 1. Testing Safe Product Recommendations (India) ---")
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

    print(f"Generated {len(products)} products.")
    assert len(products) > 0, "Should generate at least one product"

    sample_product = products[0]
    print(f"Product: {sample_product.get('name')} by {sample_product.get('brand')}")
    print(f"Primary Store: {sample_product.get('primary_retailer_name')} -> {sample_product.get('primary_order_link')}")
    
    # Verify required keys for UI display
    required_keys = [
        "name", "brand", "category", "natural_highlight", "key_ingredients",
        "medical_suitability", "allergen_guarantee", "estimated_price",
        "primary_order_link", "primary_retailer_name",
        "secondary_order_link", "secondary_retailer_name"
    ]
    for key in required_keys:
        assert key in sample_product, f"Missing key '{key}' in recommended product"

    print("\n--- 2. Testing Automated Order Processing ---")
    order = process_automated_order(
        product=sample_product,
        user_name="Alex",
        location=loc_india,
        quantity=2
    )

    print(f"Order ID: {order['order_id']}")
    print(f"Status: {order['status']}")
    print(f"ETA: {order['delivery_eta']}")
    print(f"Total Price: {order['total_price']}")

    order_keys = [
        "order_id", "product_name", "brand", "quantity", "unit_price",
        "total_price", "recipient_name", "delivery_location", "delivery_eta",
        "direct_checkout_url", "secondary_checkout_url", "quick_commerce_url",
        "primary_retailer", "secondary_retailer", "quick_commerce_retailer"
    ]
    for ok in order_keys:
        assert ok in order, f"Missing key '{ok}' in order result"

    assert "full_formatted_address" in order["delivery_location"]
    print("Automated order flow verification passed successfully!")

def test_us_location_recommendations():
    print("\n--- 3. Testing US Location Retailer Routing ---")
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
    assert len(products) > 0
    p = products[0]
    assert "Amazon" in p["primary_retailer_name"]
    assert "secondary_retailer_name" in p
    print("US retailer routing verified successfully!")

if __name__ == "__main__":
    test_recommendation_and_order_flow()
    test_us_location_recommendations()
    print("\nAll recommendations and order pipeline tests completed successfully!")
