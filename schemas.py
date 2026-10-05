"""
SafeBite AI - Core Data Schemas
Structured, typed Pydantic models for product intelligence, clinical safety evaluation,
nutrition facts, allergens, retailer offers, and source provenance.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# =========================================================================
# ENUMS & CONSTANTS
# =========================================================================

class SourceConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"

class ClinicalStatus(str, Enum):
    CLEAR = "CLEAR"         # Verified safe, compliant with medical profile
    CAUTION = "CAUTION"     # Traces, borderline nutrient thresholds, or mild caution
    AVOID = "AVOID"         # Strictly contraindicated or allergen trigger
    UNKNOWN = "UNKNOWN"     # Missing or unverified data (never defaults to CLEAR)

class ProductIdentityConfidence(str, Enum):
    EXACT = "EXACT"         # Barcode or exact brand + name + variant + pack size match
    HIGH = "HIGH"           # High-confidence variant and brand match
    POSSIBLE = "POSSIBLE"   # Brand matched, but flavor/pack size not fully confirmed
    UNVERIFIED = "UNVERIFIED"

# =========================================================================
# USER PROFILE & LOCATION SCHEMAS (PRESERVED FOR FULL BACKWARD COMPATIBILITY)
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
# RETRIEVAL & OBSERVABILITY RESULT SCHEMA
# =========================================================================

class RetrievalResult(BaseModel):
    success: bool = Field(default=False, description="True if retrieval succeeded with valid data")
    status_code: Optional[int] = Field(default=None, description="HTTP response status code")
    source: str = Field(description="Name of the data source or retailer")
    url: str = Field(default="", description="Target URL consulted")
    data: Any = Field(default=None, description="Extracted payload or response body")
    error_type: Optional[str] = Field(default=None, description="Error category, e.g. 403_BLOCKED, 429_RATE_LIMIT, TIMEOUT")
    error_message: str = Field(default="", description="Human-readable status or error explanation")
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    retrieved_at: str = Field(default="", description="ISO timestamp of query execution")
    duration_ms: float = Field(default=0.0, description="Execution latency in milliseconds")

# =========================================================================
# CLINICAL ASSESSMENT SCHEMA
# =========================================================================

class ClinicalAssessment(BaseModel):
    condition: str = Field(description="Target medical condition or allergen category evaluated")
    status: ClinicalStatus = Field(description="CLEAR, CAUTION, AVOID, or UNKNOWN")
    reason: str = Field(description="Human-readable clinical rationale")
    evidence: str = Field(description="Specific ingredient or numerical nutrition value backing the conclusion")
    matched_factors: List[str] = Field(default_factory=list, description="Specific ingredients or tokens that triggered this rule")
    confidence: SourceConfidence = Field(default=SourceConfidence.UNVERIFIED)
    source: str = Field(default="SafeBite Clinical Engine")
    condition_overview: Optional[str] = Field(default=None, description="Medical background of the condition and why dietary limits apply")
    offending_ingredients: List[Dict[str, str]] = Field(default_factory=list, description="List of offending ingredients with specific issues and physiological rationales")
    clinical_action: Optional[str] = Field(default=None, description="Actionable recommendation or replacement strategy")

# =========================================================================
# PRODUCT WEB & RETAIL INTELLIGENCE SCHEMAS
# =========================================================================

class NutritionFacts(BaseModel):
    serving_size: Optional[str] = Field(default=None, description="Serving size, e.g., '100g' or '1 bar (50g)'")
    calories: Optional[float] = Field(default=None, description="Energy in kcal")
    sugar_g: Optional[float] = Field(default=None, description="Total sugars in grams (backward-compatible field)")
    total_sugars: Optional[float] = Field(default=None, description="Total sugars in grams")
    added_sugars: Optional[float] = Field(default=None, description="Added sugars in grams")
    carbs_g: Optional[float] = Field(default=None, description="Total carbohydrates in grams (backward-compatible field)")
    carbohydrates: Optional[float] = Field(default=None, description="Total carbohydrates in grams")
    protein_g: Optional[float] = Field(default=None, description="Protein content in grams (backward-compatible field)")
    protein: Optional[float] = Field(default=None, description="Protein content in grams")
    fat_g: Optional[float] = Field(default=None, description="Total fat in grams (backward-compatible field)")
    total_fat: Optional[float] = Field(default=None, description="Total fat in grams")
    saturated_fat_g: Optional[float] = Field(default=None, description="Saturated fat in grams")
    trans_fat_g: Optional[float] = Field(default=None, description="Trans fat in grams")
    fiber_g: Optional[float] = Field(default=None, description="Dietary fiber in grams")
    sodium_mg: Optional[float] = Field(default=None, description="Sodium content in milligrams")
    cholesterol_mg: Optional[float] = Field(default=None, description="Cholesterol in milligrams")
    micronutrients: Dict[str, Any] = Field(default_factory=dict, description="Vitamins, minerals, potassium, calcium if reported")
    source: str = Field(default="Not verified", description="Primary data source (e.g. Open Food Facts, Manufacturer)")
    source_url: Optional[str] = None
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    retrieved_at: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        """Synchronize alias fields for complete backward and forward compatibility."""
        if self.sugar_g is not None and self.total_sugars is None:
            self.total_sugars = self.sugar_g
        elif self.total_sugars is not None and self.sugar_g is None:
            self.sugar_g = self.total_sugars

        if self.carbs_g is not None and self.carbohydrates is None:
            self.carbohydrates = self.carbs_g
        elif self.carbohydrates is not None and self.carbs_g is None:
            self.carbs_g = self.carbohydrates

        if self.protein_g is not None and self.protein is None:
            self.protein = self.protein_g
        elif self.protein is not None and self.protein_g is None:
            self.protein_g = self.protein

        if self.fat_g is not None and self.total_fat is None:
            self.total_fat = self.fat_g
        elif self.total_fat is not None and self.fat_g is None:
            self.fat_g = self.total_fat

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
    cross_contact_warnings: List[str] = Field(default_factory=list, description="Explicit cross-contact declarations")
    source: str = Field(default="Not verified")
    source_url: Optional[str] = None
    confidence: SourceConfidence = SourceConfidence.UNVERIFIED
    retrieved_at: Optional[str] = None

class RetailerOffer(BaseModel):
    retailer: str = Field(description="Retailer name, e.g. Amazon, BigBasket, Blinkit, Zepto, Flipkart, Instamart, JioMart")
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
    category: Optional[str] = Field(default="General Grocery", description="Product category")
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, description="Product image URL if available")
    nutrition: Optional[NutritionFacts] = None
    ingredients: Optional[Ingredients] = None
    allergens: Optional[Allergens] = None
    dietary_tags: List[str] = Field(default_factory=list, description="Vegan, Vegetarian, Gluten-Free, Diabetic-Friendly, etc.")
    retailer_offers: List[RetailerOffer] = Field(default_factory=list)
    evidence: Evidence = Field(
        default_factory=lambda: Evidence(
            manufacturer_verified=False,
            open_food_facts_verified=False,
            retailer_verified=False,
            sources_consulted=[],
            source_urls=[],
            conflicts_detected=[],
            overall_confidence=SourceConfidence.LOW,
            last_verified="Not verified"
        ),
        description="Source provenance, cross-validation, and confidence tracking"
    )
    health_safety_verdict: Optional[str] = Field(default="NOT VERIFIED", description="SAFE, UNSAFE, PARTIALLY SAFE, or NOT VERIFIED")
    health_safety_reasons: List[str] = Field(default_factory=list)
    clinical_assessments: List[ClinicalAssessment] = Field(default_factory=list, description="Condition-specific clinical evaluation list")
    identity_confidence: ProductIdentityConfidence = Field(default=ProductIdentityConfidence.UNVERIFIED, description="Confidence in variant matching")
    recommended_portion: Optional[Dict[str, Any]] = Field(default=None, description="Clinical portion limit and serving guidance based on medical history")