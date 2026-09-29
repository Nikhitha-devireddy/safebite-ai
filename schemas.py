from typing import List, Optional
from pydantic import BaseModel, Field

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