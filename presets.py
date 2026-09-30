"""
SafeBite AI - Configurable Quick Preset Profiles Engine
Data-driven health presets translating clinically into structured nutritional filters.
Audited presets: High Protein, Low Sugar, Diabetes Friendly, Heart Conscious,
Gluten Free, Dairy Free, Peanut Free, Low Sodium, Vegetarian, Vegan, Budget Friendly.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class PresetFilterCriteria(BaseModel):
    max_total_sugar_g: Optional[float] = None
    max_added_sugar_g: Optional[float] = None
    min_protein_g: Optional[float] = None
    max_sodium_mg: Optional[float] = None
    max_price: Optional[float] = None
    excluded_allergens: List[str] = Field(default_factory=list)
    dietary_tags: List[str] = Field(default_factory=list)
    clinical_constraints: List[str] = Field(default_factory=list)

class HealthPreset(BaseModel):
    id: str
    name: str
    icon: str
    tagline: str
    user_name: str
    medical_history: str
    allergies: List[str]
    food_preferences: str
    location: Dict[str, str]
    filters: PresetFilterCriteria
    sample_queries: List[str]

# Data-driven registry of all 11 core presets
HEALTH_PRESETS: Dict[str, HealthPreset] = {
    "diabetes_friendly": HealthPreset(
        id="diabetes_friendly",
        name="Diabetes Friendly",
        icon="🩸",
        tagline="Zero Added Sugar & Low Glycemic Impact",
        user_name="Alex",
        medical_history="Type 2 Diabetes (Strict No Added Sugar / Low Glycemic)",
        allergies=[],
        food_preferences="Clean Label, Whole Foods",
        location={"country": "India", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "address": "12 Indiranagar 100ft Rd"},
        filters=PresetFilterCriteria(
            max_total_sugar_g=10.0,
            max_added_sugar_g=0.0,
            clinical_constraints=["Zero high-fructose corn syrup", "Zero maltodextrin", "Portion-controlled carbs"]
        ),
        sample_queries=["diabetic friendly snacks without added sugar", "low glycemic cookies", "unsweetened almond milk"]
    ),
    "high_protein": HealthPreset(
        id="high_protein",
        name="High Protein",
        icon="💪",
        tagline="Active Muscle Recovery & High Satiety (>= 15g Protein)",
        user_name="Marcus",
        medical_history="Athletic Nutrition / High Protein Demand",
        allergies=[],
        food_preferences="High Protein, Low Added Sugar",
        location={"country": "India", "city": "Mumbai", "state": "Maharashtra", "pincode": "400001", "address": "Bandra West"},
        filters=PresetFilterCriteria(
            min_protein_g=15.0,
            max_added_sugar_g=5.0,
            clinical_constraints=["High biological value protein", "Low trans fat"]
        ),
        sample_queries=["high protein bars under ₹400", "whey protein isolate", "clean protein snacks"]
    ),
    "low_sugar": HealthPreset(
        id="low_sugar",
        name="Low Sugar",
        icon="🍃",
        tagline="Strict Low Total Sugar (<= 5g per serving)",
        user_name="Priya",
        medical_history="Metabolic Health (Low Fructose / Low Sugar)",
        allergies=[],
        food_preferences="Clean Label, No Artificial Sweeteners",
        location={"country": "India", "city": "New Delhi", "state": "Delhi", "pincode": "110001", "address": "Connaught Place"},
        filters=PresetFilterCriteria(
            max_total_sugar_g=5.0,
            max_added_sugar_g=0.0,
            clinical_constraints=["No aspartame", "No sucralose", "Natural sweetening only"]
        ),
        sample_queries=["low sugar dark chocolate under ₹300", "sugar free peanut butter", "low sugar granola"]
    ),
    "heart_conscious": HealthPreset(
        id="heart_conscious",
        name="Heart Conscious",
        icon="❤️",
        tagline="Cardiovascular & Low Sodium Defense",
        user_name="David",
        medical_history="Hypertension, Heart Disease (Strict Low Sodium)",
        allergies=[],
        food_preferences="Low Sodium, Mediterranean Diet",
        location={"country": "United States", "city": "New York", "state": "NY", "pincode": "10001", "address": "452 Broadway"},
        filters=PresetFilterCriteria(
            max_sodium_mg=140.0,
            clinical_constraints=["Low sodium <= 140mg", "Zero trans fat", "Zero MSG"]
        ),
        sample_queries=["low sodium snacks", "unsalted mixed nuts", "heart healthy breakfast cereal"]
    ),
    "gluten_free": HealthPreset(
        id="gluten_free",
        name="Gluten Free",
        icon="🌾",
        tagline="Certified Celiac Safe (Zero Wheat, Barley, Rye)",
        user_name="Sarah",
        medical_history="Celiac Disease (Severe Gluten Enteropathy)",
        allergies=["Gluten", "Wheat", "Barley", "Rye"],
        food_preferences="Certified Gluten-Free",
        location={"country": "United States", "city": "Austin", "state": "TX", "pincode": "78701", "address": "Congress Ave"},
        filters=PresetFilterCriteria(
            excluded_allergens=["gluten", "wheat", "barley", "rye"],
            dietary_tags=["Gluten-Free"],
            clinical_constraints=["Certified Gluten-Free facility", "Zero cross-contamination"]
        ),
        sample_queries=["gluten free pasta", "celiac safe cookies", "almond flour bread"]
    ),
    "dairy_free": HealthPreset(
        id="dairy_free",
        name="Dairy Free",
        icon="🥛",
        tagline="Zero Casein, Whey, Lactose or Milk Solids",
        user_name="Liam",
        medical_history="Severe Milk Protein Allergy & Lactose Intolerance",
        allergies=["Dairy", "Milk", "Casein", "Whey", "Lactose"],
        food_preferences="Dairy-Free, Plant-Based",
        location={"country": "United Kingdom", "city": "London", "state": "Greater London", "pincode": "EC1A 1BB", "address": "10 Baker St"},
        filters=PresetFilterCriteria(
            excluded_allergens=["dairy", "milk", "casein", "whey", "lactose"],
            dietary_tags=["Dairy-Free"],
            clinical_constraints=["Zero dairy butter", "Zero milk powder", "Plant-based alternatives"]
        ),
        sample_queries=["dairy free chocolate ice cream", "oat milk barista", "plant based protein bar"]
    ),
    "peanut_free": HealthPreset(
        id="peanut_free",
        name="Peanut Free",
        icon="🥜",
        tagline="Strict Peanut & Groundnut Elimination",
        user_name="Emma",
        medical_history="Anaphylactic Peanut Allergy",
        allergies=["Peanuts", "Groundnuts", "Peanut Oil"],
        food_preferences="Nut-Safe Facility",
        location={"country": "India", "city": "Hyderabad", "state": "Telangana", "pincode": "500081", "address": "Hitec City"},
        filters=PresetFilterCriteria(
            excluded_allergens=["peanuts", "peanut", "groundnuts", "peanut oil"],
            clinical_constraints=["Dedicated peanut-free lines", "Zero peanut flour"]
        ),
        sample_queries=["peanut free protein bars", "sunflower seed butter", "nut free school snacks"]
    ),
    "low_sodium": HealthPreset(
        id="low_sodium",
        name="Low Sodium",
        icon="🧂",
        tagline="Clinical Low Sodium Benchmarks (<= 140mg/serving)",
        user_name="Arthur",
        medical_history="Chronic Kidney Disease / Stage 1 Hypertension",
        allergies=[],
        food_preferences="No Added Salt, Dash Diet",
        location={"country": "India", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600001", "address": "Anna Salai"},
        filters=PresetFilterCriteria(
            max_sodium_mg=140.0,
            clinical_constraints=["Sodium <= 140mg per serving", "Zero sodium benzoate"]
        ),
        sample_queries=["low sodium crackers", "unsalted whole grain oats", "salt free seasonings"]
    ),
    "vegetarian": HealthPreset(
        id="vegetarian",
        name="Vegetarian",
        icon="🥕",
        tagline="100% Lacto-Vegetarian (Zero Slaughter Byproducts)",
        user_name="Ananya",
        medical_history="None specified",
        allergies=[],
        food_preferences="100% Lacto-Vegetarian",
        location={"country": "India", "city": "Pune", "state": "Maharashtra", "pincode": "411001", "address": "FC Road"},
        filters=PresetFilterCriteria(
            dietary_tags=["Vegetarian"],
            clinical_constraints=["Zero gelatin", "Zero animal rennet", "Zero carmine/cochineal"]
        ),
        sample_queries=["vegetarian gelatin free gummy snacks", "pure vegetarian cheese", "ragi cookies"]
    ),
    "vegan": HealthPreset(
        id="vegan",
        name="Vegan",
        icon="🌱",
        tagline="100% Plant-Based (Zero Animal Ingredients)",
        user_name="Zoe",
        medical_history="Plant-Based Lifestyle",
        allergies=[],
        food_preferences="100% Plant-Based Vegan",
        location={"country": "United States", "city": "San Francisco", "state": "CA", "pincode": "94102", "address": "Market St"},
        filters=PresetFilterCriteria(
            dietary_tags=["Vegan"],
            clinical_constraints=["Zero dairy", "Zero eggs", "Zero honey", "Zero gelatin", "Zero carmine"]
        ),
        sample_queries=["vegan dark chocolate bars", "plant based almond yogurt", "vegan protein powder"]
    ),
    "budget_friendly": HealthPreset(
        id="budget_friendly",
        name="Budget Friendly",
        icon="💰",
        tagline="Healthy Clean Nutrition Under ₹300 ($5)",
        user_name="Karan",
        medical_history="General Health & Clean Eating",
        allergies=[],
        food_preferences="Clean Label, Affordable Staples",
        location={"country": "India", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "address": "Koramangala"},
        filters=PresetFilterCriteria(
            max_price=300.0,
            clinical_constraints=["Clean label", "No artificial colors"]
        ),
        sample_queries=["healthy snack bars under ₹200", "organic rolled oats under ₹250", "clean peanut butter under ₹300"]
    )
}

def get_preset(preset_id: str) -> Optional[HealthPreset]:
    return HEALTH_PRESETS.get(preset_id)

def get_all_presets() -> List[HealthPreset]:
    return list(HEALTH_PRESETS.values())

def apply_preset_to_session(preset_id: str, session_state: Any) -> bool:
    """
    Applies preset to Streamlit session_state safely.
    Updates domain state keys, legacy keys, and active widget keys.
    Protects against StreamlitWidgetAlreadyInstantiatedError when widgets
    have already been instantiated during the current run.
    """
    preset = get_preset(preset_id)
    if not preset:
        return False

    allergies_joined = ", ".join(preset.allergies) if preset.allergies else ""

    # 1. Update Core Application Domain State (Always safe to mutate at any point in run)
    session_state["user_name"] = preset.user_name
    session_state["medical_history"] = preset.medical_history
    session_state["allergies_list"] = list(preset.allergies)
    session_state["food_preferences"] = preset.food_preferences
    session_state["location_dict"] = {
        "country": preset.location.get("country", "India"),
        "city": preset.location.get("city", "Bengaluru"),
        "state": preset.location.get("state", "Karnataka"),
        "pincode": preset.location.get("pincode", "560001"),
        "address": preset.location.get("address", "")
    }
    session_state["active_preset_id"] = preset.id

    # 2. Update Legacy / Compatibility Keys (Required for test suite & backwards compatibility)
    session_state["profile_name"] = preset.user_name
    session_state["profile_med"] = preset.medical_history
    session_state["profile_all"] = allergies_joined
    session_state["profile_pref"] = preset.food_preferences
    session_state["profile_country"] = preset.location.get("country", "India")
    session_state["profile_city"] = preset.location.get("city", "Bengaluru")
    session_state["profile_state"] = preset.location.get("state", "Karnataka")
    session_state["profile_pincode"] = preset.location.get("pincode", "560001")
    session_state["profile_address"] = preset.location.get("address", "")

    # Determine matched saved location profile if any
    matched_loc_id = "custom"
    matched_label = "⚙️ Custom Address"
    try:
        from location_manager import LocationManager
        for k, prof in LocationManager.SAVED_PROFILES.items():
            if prof.city.lower() == preset.location.get("city", "").lower():
                matched_loc_id = k
                matched_label = prof.label
                break
    except Exception:
        pass
    session_state["active_location_id"] = matched_loc_id

    # 3. Safe Setter for Active Streamlit Widget Keys
    def _safe_set_widget(key: str, value: Any):
        try:
            session_state[key] = value
        except Exception:
            # Catch StreamlitWidgetAlreadyInstantiatedError or other session state restrictions
            pass

    _safe_set_widget("input_user_name", preset.user_name)
    _safe_set_widget("input_medical_history", preset.medical_history)
    _safe_set_widget("input_allergies", allergies_joined)
    _safe_set_widget("input_food_preferences", preset.food_preferences)
    _safe_set_widget("input_country", preset.location.get("country", "India"))
    _safe_set_widget("input_city", preset.location.get("city", "Bengaluru"))
    _safe_set_widget("input_state", preset.location.get("state", "Karnataka"))
    _safe_set_widget("input_pincode", preset.location.get("pincode", "560001"))
    _safe_set_widget("input_address", preset.location.get("address", ""))
    _safe_set_widget("sb_location_selector", matched_label)

    # Synchronize Allergen Checkboxes & Custom Allergies widget
    common_allergens = ["Peanuts", "Tree Nuts", "Dairy", "Gluten", "Soy", "Eggs", "Shellfish", "Fish", "Sesame", "Mustard"]
    custom_allergies = []
    preset_allergies_lower = [a.lower() for a in preset.allergies]
    for alg in common_allergens:
        is_chk = any(alg.lower() in a for a in preset_allergies_lower)
        _safe_set_widget(f"chk_alg_{alg}", is_chk)

    for a in preset.allergies:
        if not any(alg.lower() in a.lower() for alg in common_allergens):
            custom_allergies.append(a)
    _safe_set_widget("input_custom_allergies", ", ".join(custom_allergies))

    # Set sample query across all search inputs
    if preset.sample_queries:
        sample_q = preset.sample_queries[0]
        session_state["intel_query_input"] = sample_q
        session_state["main_intel_query_input"] = sample_q
        _safe_set_widget("tab_search_query_input", sample_q)
        _safe_set_widget("home_search_input", sample_q)

    # Set flag for top-of-script rerun application in case widgets were already instantiated
    session_state["_pending_preset_id"] = preset.id

    return True
