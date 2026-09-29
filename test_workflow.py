import os
from dotenv import load_dotenv
from schemas import ProductSafetyRequest
from agent import run_agent_workflow, scrape_product_url

load_dotenv()

def test_url_scraping():
    print("\n--- 1. Testing Web Scraping Functionality ---")
    test_url = "https://world.openfoodfacts.org/product/737628064502/rice-noodles-ka-me"
    result = scrape_product_url(test_url)
    print(f"Scrape Success: {result['success']}")
    print(f"Scraped Title: {result['title']}")
    print(f"Content length: {len(result['content'])} characters")
    assert result["success"] is True or len(result["content"]) > 0
    print("Scraping test passed!")

def test_langgraph_workflow_with_text():
    print("\n--- 2. Testing LangGraph Workflow with Text & Hidden Allergen Detection ---")
    # Patient with Type 2 Diabetes and Dairy Allergy
    # Ingredient text includes hidden dairy (casein, whey) and high glycemic sugars
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
    print("\nWorkflow Execution Output:")
    print(f"Verdict: {result.get('verdict')}")
    print(f"Report Length: {len(result.get('final_output', ''))}")
    assert result.get("verdict") in ["UNSAFE", "PARTIALLY SAFE", "SAFE"]
    assert "whey" in result.get("final_output", "").lower() or "casein" in result.get("final_output", "").lower()
    print("LangGraph workflow test passed!")

def test_blocked_or_missing_ingredients_url():
    print("\n--- 3. Testing Missing Ingredient / Blocked URL Guardrail ---")
    # Amazon URLs trigger bot protection or lack plain ingredient text
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
    print("Workflow Execution Output for blocked/empty URL:")
    print(f"Verdict: {result.get('verdict')}")
    print(f"Has Ingredients: {result.get('has_ingredients')}")
    print(f"Scrape Reason: {result.get('scrape_reason')}")
    
    assert result.get("verdict") == "UNABLE TO ASSESS"
    assert result.get("has_ingredients") is False
    assert "Paste Ingredients List" in result.get("final_output", "")
    assert "Upload Product Label Photo" in result.get("final_output", "")
    print("Missing ingredient URL fallback guardrail test passed successfully!")

if __name__ == "__main__":
    try:
        test_url_scraping()
        test_langgraph_workflow_with_text()
        test_blocked_or_missing_ingredients_url()
        print("\nAll integration tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
