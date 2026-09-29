import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import TypedDict, Optional, Dict, Any
from schemas import ProductSafetyRequest
from langgraph.graph import StateGraph, END
from llm_service import generate_clinical_assessment

# Load environment variables
load_dotenv()

# Define Agent State
class AgentState(TypedDict):
    request: ProductSafetyRequest
    scraped_content: Optional[str]
    scrape_success: Optional[bool]
    has_ingredients: Optional[bool]
    scrape_reason: Optional[str]
    product_analysis: Optional[str]
    final_output: Optional[str]
    verdict: Optional[str]
    provider_used: Optional[str]

def scrape_product_url(url: str) -> Dict[str, Any]:
    """
    Scrapes a product URL and extracts title, meta description, and page text.
    Detects anti-bot protection and verifies whether ingredient/nutritional data exists.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title and meta description
        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Product Page"
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Remove irrelevant or noisy tags
        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe", "button"]):
            element.decompose()

        # Extract textual content
        text_content = soup.get_text(separator=" ", strip=True)

        # Consolidate scraped information
        compiled_text = f"Product Title: {page_title}\n"
        if meta_desc:
            compiled_text += f"Product Summary: {meta_desc}\n\n"
        compiled_text += f"Page Content & Ingredients:\n{text_content}"

        # Truncate to avoid context overload while preserving ingredient details
        truncated_content = compiled_text[:7000]

        # 1. Anti-bot / Captcha detection
        bot_patterns = [
            r"robot check",
            r"continue shopping",
            r"enter the characters you see",
            r"access denied",
            r"pardon our interruption",
            r"verify you are human",
            r"security check",
            r"just a moment\.\.\.",
            r"enable javascript",
            r"cloudflare"
        ]
        for bp in bot_patterns:
            if re.search(bp, text_content, re.IGNORECASE):
                return {
                    "success": False,
                    "has_ingredients": False,
                    "title": page_title,
                    "content": truncated_content,
                    "reason": "The website (e.g., Amazon, Blinkit, BigBasket) blocked automated extraction with anti-bot protection or captcha."
                }

        # 2. Ingredient & Nutrition detection
        ing_patterns = [
            r"\bingredients?\s*[:\-\b]",
            r"\bcomposition\b",
            r"\bnutrition facts\b",
            r"\bnutritional (?:information|value)\b",
            r"\bcontains\s*[:\-]",
            r"\ballergens?\s*[:\-]",
            r"\bactive ingredients?\b"
        ]
        has_ing = any(re.search(p, text_content, re.IGNORECASE) for p in ing_patterns)

        if not has_ing:
            return {
                "success": False,
                "has_ingredients": False,
                "title": page_title,
                "content": truncated_content,
                "reason": "The webpage loaded, but no ingredient list or nutritional facts were found. Ingredients may be stored in product images or rendered via JavaScript tabs."
            }

        return {
            "success": True,
            "has_ingredients": True,
            "title": page_title,
            "content": truncated_content,
            "reason": "Ingredients successfully detected on page."
        }
    except Exception as e:
        return {
            "success": False,
            "has_ingredients": False,
            "title": "Unknown Product",
            "content": f"Could not scrape URL directly ({str(e)}). Product URL: {url}",
            "reason": f"Could not reach or scrape the webpage ({str(e)})."
        }

# Node 1: Web Scraper / Input Handler Node
def scrape_url_node(state: AgentState) -> AgentState:
    """Fetches text content from a URL or passes through manual text."""
    req = state["request"]
    
    if req.input_type == "url":
        print(f"\n[Tool Execution] Scraping live webpage data from: {req.product_source}")
        scrape_result = scrape_product_url(req.product_source)
        state["scraped_content"] = scrape_result["content"]
        state["scrape_success"] = scrape_result["success"]
        state["has_ingredients"] = scrape_result.get("has_ingredients", False)
        state["scrape_reason"] = scrape_result.get("reason", "")
        if scrape_result["success"]:
            print(f"Webpage successfully scraped: {scrape_result['title']}")
        else:
            print(f"Scraping notice: {scrape_result.get('reason', scrape_result['content'])}")
    else:
        print("\n[Tool Execution] Using direct user-provided text input.")
        state["scraped_content"] = req.product_source
        state["scrape_success"] = True
        state["has_ingredients"] = True
        state["scrape_reason"] = "Direct user input provided."
        
    return state

# Node 2: Clinical Product Safety Audit
def analyze_product_node(state: AgentState) -> AgentState:
    req = state["request"]
    product_data = state["scraped_content"]

    # Short-circuit if URL scraping could not fetch ingredients
    if req.input_type == "url" and not state.get("has_ingredients", False):
        reason = state.get("scrape_reason", "Could not extract ingredient list from this URL.")
        state["verdict"] = "UNABLE TO ASSESS"
        state["provider_used"] = "URL Scraper Guardrail"
        state["product_analysis"] = (
            f"### ⚠️ Could Not Fetch Ingredients from URL\n\n"
            f"**Provided URL:** `{req.product_source}`\n\n"
            f"**Reason:** {reason}\n\n"
            f"---\n\n"
            f"### 👉 Please Select Another Option:\n"
            f"Because ingredient data could not be extracted from this link, please use one of these alternative options:\n\n"
            f"1. **📝 Paste Ingredients List**: Copy and paste the ingredient text directly from the product packaging or e-commerce listing.\n"
            f"2. **📸 Upload Product Label Photo**: Upload a photo of the product's nutrition / ingredient label for high-precision multimodal OCR."
        )
        state["final_output"] = state["product_analysis"]
        return state
    
    allergies_formatted = ", ".join(req.allergies) if req.allergies else "None specified"
    preferences_formatted = req.food_preferences if req.food_preferences else "None specified"
    
    prompt = f"""
    You are an elite clinical pharmacologist, toxicologist, and allergen-detection specialist.
    Your mission is to perform a rigorous safety assessment of a product for a user, cross-referencing their medical conditions, strict allergies, and food preferences.
    Special focus: Users often do not know hidden allergens or chemical/scientific names of allergens in ingredient lists. Uncover ALL hidden allergens and contraindications.

    USER PROFILE:
    - User Name: {req.user_name}
    - Medical History / Chronic Conditions: {req.medical_history}
    - Strict Allergies: {allergies_formatted}
    - Dietary / Food Preferences: {preferences_formatted}

    PRODUCT DATA (Scraped from URL or provided as text):
    {product_data}

    CLINICAL AUDIT INSTRUCTIONS:
    1. **Hidden Allergen & Derivative Detection**:
       - Scrutinize all ingredients for disguised or derivative forms of the user's allergies.
       - Examples: Casein/whey/ghee/lactose/sodium caseinate for dairy; malt/spelt/barley/rye/brewer's yeast/dextrin for gluten; lecithin/edamame/hydrolyzed vegetable protein for soy; albumin/lysozyme/globulin for egg; isinglass/gelatin for fish/animal products; hidden nuts, seeds, sulfites, MSG, etc.
    2. **Medical Pathophysiology Analysis**:
       - Dynamically analyze the user's chronic condition:
         * Diabetes: High-glycemic carbs, maltodextrin, high-fructose corn syrup, dextrose, added sugars.
         * Hypertension / Cardiac: High sodium, sodium benzoate, MSG, disodium phosphate.
         * Constipation / GI: Low fiber, high refined starches, astringents, heavy binding dairy, excess iron/calcium binders.
         * Celiac / IBS / GERD / Gout / Kidney: Gluten traces, high FODMAPs, purines, oxalates, phosphorus, acid triggers.
    3. **Food Preference Compliance**:
       - Verify if the product complies with preferences (e.g., Vegan, Vegetarian, Halal, Kosher, Keto). Flag hidden animal byproducts (gelatin, carmine/cochineal, bone char sugar, tallow, rennet).
    4. **Output Structure Requirements**:
       - **VERDICT LINE**: Must clearly start with one of:
         * `VERDICT: SAFE` (Zero conflicting allergens, no medical contraindications, meets preferences)
         * `VERDICT: PARTIALLY SAFE` (Caution required: 'may contain' warnings, moderate amounts of condition triggers, or borderline ingredients)
         * `VERDICT: UNSAFE` (Contains explicit or hidden allergens, severe medical contraindications, or violates food preferences)
       - Follow with structured sections:
         * **Executive Summary**: 2 sentences directly addressing the user.
         * **Hidden Allergens & Disguised Ingredients Alert**: Explicitly list any hidden allergens or clarify that none were identified.
         * **Medical Condition Interaction**: How ingredients affect their specific chronic condition.
         * **Dietary Preference Compliance**: Whether it matches their stated food preferences.
         * **Flagged vs. Safe Ingredients**: Clear bullet points explaining individual ingredients of concern.
         * **Actionable Clinical Recommendation**: Final advice (e.g., Safe to consume, strictly avoid, or consume in limited quantity).
    """
    
    print("Running clinical multi-condition evaluation...")
    analysis, provider = generate_clinical_assessment(prompt)
    
    # Determine verdict label
    verdict = "SAFE"
    if "VERDICT: UNSAFE" in analysis.upper():
        verdict = "UNSAFE"
    elif "VERDICT: PARTIALLY SAFE" in analysis.upper():
        verdict = "PARTIALLY SAFE"
    elif "VERDICT: SAFE" in analysis.upper():
        verdict = "SAFE"
        
    state["verdict"] = verdict
    state["product_analysis"] = analysis
    state["final_output"] = analysis
    state["provider_used"] = provider
        
    return state

# Build LangGraph Workflow with sequential nodes
workflow = StateGraph(AgentState)
workflow.add_node("scrape_url", scrape_url_node)
workflow.add_node("analyze_product", analyze_product_node)

# Define flow direction: START -> scrape_url -> analyze_product -> END
workflow.set_entry_point("scrape_url")
workflow.add_edge("scrape_url", "analyze_product")
workflow.add_edge("analyze_product", END)

app = workflow.compile()

def run_agent_workflow(user_request: ProductSafetyRequest) -> Dict[str, Any]:
    """Helper function to execute the full LangGraph workflow given a request."""
    initial_state = {
        "request": user_request,
        "scraped_content": None,
        "scrape_success": None,
        "has_ingredients": None,
        "scrape_reason": None,
        "product_analysis": None,
        "final_output": None,
        "verdict": None,
        "provider_used": None
    }
    final_state = app.invoke(initial_state)
    return final_state

if __name__ == "__main__":
    print("--- LangGraph Web-Enabled Clinical Safety Agent Initialized ---")
    
    # 1. Gather user profile details
    name = input("Enter user name: ").strip() or "User"
    med_history = input("Enter medical history/conditions (e.g., Constipation, Diabetes, Hypertension): ").strip()
    allergies_input = input("Enter strict allergies separated by commas (e.g., Peanuts, Dairy, Gluten): ").strip()
    preferences_input = input("Enter dietary/food preferences (e.g., Vegan, Vegetarian, Halal, None): ").strip()
    
    # 2. Input method choice
    print("\nChoose product input method:")
    print("  [1] Paste Product URL (Auto-Scrapes webpage)")
    print("  [2] Paste Ingredient List / Description Text")
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        input_type = "url"
        product_source = input("Enter the product URL: ").strip()
    else:
        input_type = "text"
        product_source = input("Paste the ingredient list or product details: ").strip()
    
    allergies_list = [a.strip() for a in allergies_input.split(",") if a.strip() and a.lower() != "none"]
    
    user_req = ProductSafetyRequest(
        user_name=name,
        medical_history=med_history,
        allergies=allergies_list,
        food_preferences=preferences_input,
        input_type=input_type,
        product_source=product_source
    )
    
    print("\nExecuting LangGraph workflow...")
    result = run_agent_workflow(user_req)
    
    print(f"\n[Engine: {result.get('provider_used')}]")
    print("\n========================================")
    print("      CLINICAL SAFETY ASSESSMENT REPORT ")
    print("========================================\n")
    print(result.get("final_output", "No output generated."))