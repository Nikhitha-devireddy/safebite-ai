import os
import unittest
from dotenv import load_dotenv
from schemas import ProductSafetyRequest
from agent import run_agent_workflow, scrape_product_url

load_dotenv()

class TestWorkflow(unittest.TestCase):

    def test_url_scraping(self):
        """Testing Web Scraping Functionality."""
        test_url = "https://world.openfoodfacts.org/product/737628064502/rice-noodles-ka-me"
        result = scrape_product_url(test_url)
        self.assertTrue(result["success"] is True or len(result["content"]) > 0)

    def test_langgraph_workflow_with_text(self):
        """Testing LangGraph Workflow with Text & Hidden Allergen Detection."""
        sample_ingredients = """
        Ingredients: Enriched wheat flour, high fructose corn syrup, maltodextrin, 
        whey protein concentrate, sodium caseinate, partially hydrogenated soybean oil, 
        natural vanilla flavor, salt.
        """
        
        req = ProductSafetyRequest(
            user_name="Sarah",
            medical_history="Type 2 Diabetes",
            allergies=["Dairy", "Milk Protein"],
            food_preferences="Vegetarian",
            input_type="text",
            product_source=sample_ingredients
        )
        
        result = run_agent_workflow(req)
        self.assertIn(result.get("verdict"), ["UNSAFE", "PARTIALLY SAFE", "SAFE"])
        out_text = result.get("final_output", "").lower()
        self.assertTrue("whey" in out_text or "casein" in out_text or "dairy" in out_text)

    def test_blocked_or_missing_ingredients_url(self):
        """Testing Missing Ingredient / Blocked URL Guardrail."""
        blocked_url = "https://www.amazon.in/dp/B07T5Z2Q1W"
        
        req = ProductSafetyRequest(
            user_name="John",
            medical_history="Hypertension",
            allergies=["Peanuts"],
            food_preferences="None",
            input_type="url",
            product_source=blocked_url
        )
        
        result = run_agent_workflow(req)
        self.assertEqual(result.get("verdict"), "UNABLE TO ASSESS")
        self.assertFalse(result.get("has_ingredients"))
        self.assertIn("Paste Ingredients List", result.get("final_output", ""))
        self.assertIn("Upload Product Label Photo", result.get("final_output", ""))

if __name__ == "__main__":
    unittest.main()
