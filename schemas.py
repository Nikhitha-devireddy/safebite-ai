from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# =========================================================================
# EXISTING SCHEMAS (PRESERVED FOR FULL BACKWARD COMPATIBILITY)
# =========================================================================

class UserLocation(BaseModel):
    country: str = Field(default="India", description="Country name, e.g., India, United States, United Kingdom.")
    state: str = Field(default="", description="State or province, e.g., Karnataka, California, Texas, Maharashtra.")
    city: str = Field(default="", description="Town or city, e.g., Bengaluru, Mumbai, New York, London.")
    pincode: str = Field(default="", description="Pincode or postal code, e.g., 560001, 400001, 10001.")
    address: str = Field(default="", description="Street address or locality.")

class ProductSafetyRequest(BaseModel):
    user_name: str = Field(description="The name of the user checking the product.")
    medical_history: str = Field(description="The user's medical history or chronic conditions.")
    allergies: List[str] = Field(description="Strict list of food allergies to avoid.")
    food_preferences: Optional[str] = Field(default="", description="Dietary and food preferences such as Vegan, Vegetarian, Halal, Kosher, Gluten-Free, Low-FODMAP, Keto, etc.")
    input_type: str = Field(description="Method chosen: 'url', 'text', or 'image'")
    product_source: str = Field(description="Either the URL link, the raw ingredient text, or image note provided by the user.")
    location: Optional[UserLocation] = None


# =========================================================================
# PRODUCT WEB & RETAIL INTELLIGENCE SCHEMAS
# =========================================================================

class SourceConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"

class NutritionFacts(BaseModel):
    serving_size: Optional[str] = Field(default=None, description="Serving size, e.g., '100g' or '1 bar (50g)'")
    calories: Optional[float] = Field(default=None, description="Energy in kcal")
    sugar_g: Optional[float] = Field(default=None, description="Total sugars in grams")
    carbs_g: Optional[float] = Field(default=None, description="Total carbohydrates in grams")
    protein_g: Optional[float] = Field(default=None, description="Protein content in grams")
    fat_g: Optional[float] = Field(default=None, description="Total fat in grams")
    saturated_fat_g: Optional[float] = Field(default=None, description="Saturated fat in grams")
    fiber_g: Optional[float] = Field(default=None, description="Dietary fiber in grams")
    sodium_mg: Optional[float] = Field(default=None, description="Sodium content in milligrams")
    source: str = Field(default="Not verified", description="Primary data source (e.g. Open Food Facts, Manufacturer)")
    source_url: Optional[str] = None
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    retrieved_at: Optional[str] = None

class Ingredients(BaseModel):
    raw_text: Optional[str] = Field(default=None, description="Complete ingredient declaration string")
    ingredient_list: List[str] = Field(default_factory=list, description="Parsed individual ingredient tokens")
    additives: List[str] = Field(default_factory=list, description="Preservatives, emulsifiers, artificial colors")
    is_clean_label: bool = Field(default=False, description="True if free from synthetic additives and high-fructose syrups")
    source: str = Field(default="Not verified")
    source_url: Optional[str] = None
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    retrieved_at: Optional[str] = None

class Allergens(BaseModel):
    contains: List[str] = Field(default_factory=list, description="Declared primary allergens (e.g. peanuts, dairy, gluten)")
    may_contain: List[str] = Field(default_factory=list, description="Cross-contamination / shared facility traces")
    free_from: List[str] = Field(default_factory=list, description="Verified allergen-free claims")
    source: str = Field(default="Not verified")
    source_url: Optional[str] = None
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    retrieved_at: Optional[str] = None

class RetailerOffer(BaseModel):
    retailer: str = Field(description="Retailer name, e.g. Amazon, BigBasket, Blinkit, Zepto, Official Store")
    product_name: str = Field(description="Specific title listed on this retailer platform")
    price: Optional[float] = Field(default=None, description="Current selling price in numeric format")
    currency: str = Field(default="₹", description="Currency symbol")
    pack_size: Optional[str] = Field(default=None, description="Pack size / weight (e.g., '50g', 'Pack of 6')")
    in_stock: bool = Field(default=True, description="Stock availability status")
    product_url: str = Field(description="Direct deep link or retailer search URL")
    availability_status: str = Field(default="Available", description="Human-readable availability note")
    location: Optional[str] = Field(default=None, description="City / Region target")
    retrieved_at: str = Field(description="ISO timestamp of query retrieval")
    confidence: SourceConfidence = SourceConfidence.MEDIUM

class Evidence(BaseModel):
    manufacturer_verified: bool = Field(default=False, description="Confirmed via official manufacturer / lab panel")
    open_food_facts_verified: bool = Field(default=False, description="Confirmed via Open Food Facts database")
    retailer_verified: bool = Field(default=False, description="Confirmed across live retail inventory")
    sources_consulted: List[str] = Field(default_factory=list, description="Names of all sources checked")
    source_urls: List[str] = Field(default_factory=list, description="Direct URLs consulted")
    conflicts_detected: List[str] = Field(default_factory=list, description="Visible report of any cross-source discrepancies")
    overall_confidence: SourceConfidence = Field(default=SourceConfidence.LOW, description="Aggregated confidence rating")
    last_verified: str = Field(description="Timestamp of last data audit")

class Product(BaseModel):
    id: str = Field(description="Unique deterministic ID based on barcode or normalized brand+name")
    name: str = Field(description="Canonical product title")
    brand: str = Field(description="Brand or manufacturer name")
    variant: Optional[str] = Field(default=None, description="Flavor, type, or variant specification")
    pack_size: Optional[str] = Field(default=None, description="Canonical package net weight / volume")
    barcode: Optional[str] = Field(default=None, description="GTIN/EAN-13/UPC barcode if available")
    description: Optional[str] = None
    nutrition: Optional[NutritionFacts] = None
    ingredients: Optional[Ingredients] = None
    allergens: Optional[Allergens] = None
    retailer_offers: List[RetailerOffer] = Field(default_factory=list)
    evidence: Evidence
    health_safety_verdict: Optional[str] = Field(default="NOT VERIFIED", description="SAFE, UNSAFE, PARTIALLY SAFE, or NOT VERIFIED")
    health_safety_reasons: List[str] = Field(default_factory=list)