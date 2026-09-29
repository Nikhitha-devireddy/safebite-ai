import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from schemas import NutritionFacts, Ingredients, Allergens, SourceConfidence

class NutritionExtractor:
    """
    Deterministic Nutrition, Ingredients, and Allergen Extractor.
    Rule 1: Never hallucinates or invents nutrition or ingredients.
    Rule 2: Treats missing data strictly as None ('Not verified').
    Rule 3: Parses Open Food Facts schema, schema.org/NutritionInformation, and raw OCR/HTML text.
    """

    # Common allergens for normalization
    KNOWN_ALLERGENS = [
        "peanuts", "peanut", "tree nuts", "almonds", "cashews", "walnuts", "pistachios",
        "hazelnuts", "pecans", "macadamia", "milk", "dairy", "casein", "whey", "lactose",
        "gluten", "wheat", "barley", "rye", "oats", "spelt", "soy", "soya", "soybean",
        "eggs", "egg", "fish", "shellfish", "crustaceans", "molluscs", "sesame", "mustard",
        "celery", "lupin", "sulfites", "sulphites"
    ]

    # Harmful / Ultra-processed additives for clean-label audit
    ADDITIVE_PATTERNS = [
        r"ins\s*\d{3,4}[a-z]?",
        r"e\s*\d{3,4}[a-z]?",
        r"high\s*fructose\s*corn\s*syrup",
        r"maltodextrin",
        r"hydrogenated\s*(?:vegetable\s*)?oil",
        r"artificial\s*(?:flavor|flavour|color|colour|sweetener)",
        r"aspartame|sucralose|acesulfame|saccharin",
        r"sodium\s*benzoate|potassium\s*sorbate",
        r"msg|monosodium\s*glutamate"
    ]

    @classmethod
    def extract_from_open_food_facts(cls, product_dict: Dict[str, Any], url: Optional[str] = None) -> Tuple[NutritionFacts, Ingredients, Allergens]:
        """Extracts strictly verified data from Open Food Facts API response."""
        nutriments = product_dict.get("nutriments", {})
        serving_size = product_dict.get("serving_size")

        # Calories: prefer serving, then 100g, then energy-kcal
        cal = nutriments.get("energy-kcal_serving") or nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal")
        if cal is not None:
            try:
                cal = float(cal)
            except (ValueError, TypeError):
                cal = None

        def get_val(keys: List[str]) -> Optional[float]:
            for k in keys:
                v = nutriments.get(k)
                if v is not None:
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        pass
            return None

        sugar = get_val(["sugars_serving", "sugars_100g", "sugars"])
        carbs = get_val(["carbohydrates_serving", "carbohydrates_100g", "carbohydrates"])
        protein = get_val(["proteins_serving", "proteins_100g", "proteins"])
        fat = get_val(["fat_serving", "fat_100g", "fat"])
        sat_fat = get_val(["saturated-fat_serving", "saturated-fat_100g", "saturated-fat"])
        fiber = get_val(["fiber_serving", "fiber_100g", "fiber"])
        
        # Sodium: OFF provides sodium in grams, convert to mg
        sodium_g = get_val(["sodium_serving", "sodium_100g", "sodium"])
        sodium_mg = round(sodium_g * 1000.0, 1) if sodium_g is not None else None

        now_str = datetime.now(timezone.utc).isoformat()
        has_any_nutrition = any(v is not None for v in [cal, sugar, carbs, protein, fat])

        nutrition = NutritionFacts(
            serving_size=serving_size or ("100g" if has_any_nutrition else None),
            calories=cal,
            sugar_g=sugar,
            carbs_g=carbs,
            protein_g=protein,
            fat_g=fat,
            saturated_fat_g=sat_fat,
            fiber_g=fiber,
            sodium_mg=sodium_mg,
            source="Open Food Facts (Public Collaborative Database)",
            source_url=url or f"https://world.openfoodfacts.org/product/{product_dict.get('code', '')}",
            confidence=SourceConfidence.HIGH if has_any_nutrition else SourceConfidence.UNVERIFIED,
            retrieved_at=now_str
        )

        # Ingredients parsing
        raw_ing = product_dict.get("ingredients_text") or product_dict.get("ingredients_text_en") or ""
        ing_list = []
        if raw_ing:
            # Split by comma or semicolon
            ing_list = [i.strip(" .()") for i in re.split(r"[,;]+", raw_ing) if i.strip()]
        
        # Additives detection
        additives_tags = product_dict.get("additives_tags", [])
        additives_clean = [a.replace("en:", "").upper() for a in additives_tags]
        
        # Regex search in raw text for common preservatives/syrups
        for pat in cls.ADDITIVE_PATTERNS:
            found = re.findall(pat, raw_ing, re.IGNORECASE)
            for f in found:
                if f.upper() not in additives_clean:
                    additives_clean.append(f.strip().title())

        is_clean = len(additives_clean) == 0 and bool(raw_ing)

        ingredients = Ingredients(
            raw_text=raw_ing or None,
            ingredient_list=ing_list,
            additives=additives_clean,
            is_clean_label=is_clean,
            source="Open Food Facts (Public Collaborative Database)",
            source_url=url or f"https://world.openfoodfacts.org/product/{product_dict.get('code', '')}",
            confidence=SourceConfidence.HIGH if raw_ing else SourceConfidence.UNVERIFIED,
            retrieved_at=now_str
        )

        # Allergens extraction
        allergens_tags = product_dict.get("allergens_tags", [])
        contains_list = [a.replace("en:", "").strip().lower() for a in allergens_tags if a.strip()]
        
        traces_tags = product_dict.get("traces_tags", [])
        may_contain_list = [t.replace("en:", "").strip().lower() for t in traces_tags if t.strip()]

        # Scan ingredients text if tags were empty
        if raw_ing and not contains_list:
            raw_lower = raw_ing.lower()
            for allergen in cls.KNOWN_ALLERGENS:
                if re.search(r"\b" + re.escape(allergen) + r"\b", raw_lower):
                    contains_list.append(allergen)

        allergens = Allergens(
            contains=list(set(contains_list)),
            may_contain=list(set(may_contain_list)),
            free_from=[],
            source="Open Food Facts (Public Collaborative Database)",
            source_url=url or f"https://world.openfoodfacts.org/product/{product_dict.get('code', '')}",
            confidence=SourceConfidence.HIGH if (contains_list or raw_ing) else SourceConfidence.UNVERIFIED,
            retrieved_at=now_str
        )

        return nutrition, ingredients, allergens

    @classmethod
    def extract_from_text(cls, text: str, source_name: str = "Web Document / Packaging", source_url: Optional[str] = None) -> Tuple[NutritionFacts, Ingredients, Allergens]:
        """
        Deterministically parses nutrition declarations from raw OCR, HTML tables, or product descriptions.
        Does not invent missing figures.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        if not text or not text.strip():
            return (
                NutritionFacts(source=source_name, source_url=source_url, confidence=SourceConfidence.UNVERIFIED, retrieved_at=now_str),
                Ingredients(source=source_name, source_url=source_url, confidence=SourceConfidence.UNVERIFIED, retrieved_at=now_str),
                Allergens(source=source_name, source_url=source_url, confidence=SourceConfidence.UNVERIFIED, retrieved_at=now_str)
            )

        def find_num(patterns: List[str]) -> Optional[float]:
            for p in patterns:
                m = re.search(p, text, re.IGNORECASE)
                if m:
                    try:
                        return float(m.group(1))
                    except (ValueError, TypeError):
                        pass
            return None

        cal = find_num([
            r"(?:energy|calories|cal(?:ories)?)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:kcal|cal)?\b",
            r"(\d+(?:\.\d+)?)\s*kcal\b"
        ])
        sugar = find_num([
            r"(?:total\s*sugars?|sugars?|added\s*sugars?)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g\b",
            r"sugar[^\d\n\r]*(\d+(?:\.\d+)?)\s*g\b"
        ])
        carbs = find_num([
            r"(?:total\s*carbohydrates?|carbohydrates?|carbs?)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g\b"
        ])
        protein = find_num([
            r"(?:protein|proteins)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g\b"
        ])
        fat = find_num([
            r"(?:total\s*fat|fat)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g\b"
        ])
        sat_fat = find_num([
            r"(?:saturated\s*fat|sat\s*fat)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g\b"
        ])
        fiber = find_num([
            r"(?:dietary\s*fiber|fiber|fibre)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*g\b"
        ])
        sodium = find_num([
            r"(?:sodium|salt)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mg\b"
        ])
        serving_match = re.search(r"(?:serving\s*size|per\s*serving)\s*[:=]?\s*([^\n\r,]+)", text, re.IGNORECASE)
        serving_size = serving_match.group(1).strip() if serving_match else None

        has_data = any(v is not None for v in [cal, sugar, carbs, protein, fat])

        nutrition = NutritionFacts(
            serving_size=serving_size,
            calories=cal,
            sugar_g=sugar,
            carbs_g=carbs,
            protein_g=protein,
            fat_g=fat,
            saturated_fat_g=sat_fat,
            fiber_g=fiber,
            sodium_mg=sodium,
            source=source_name,
            source_url=source_url,
            confidence=SourceConfidence.MEDIUM if has_data else SourceConfidence.UNVERIFIED,
            retrieved_at=now_str
        )

        # Extract Ingredients
        raw_ing = None
        ing_match = re.search(r"(?:ingredients?|contains?)\s*[:=]\s*([^\n\r]+(?:\n[^\n\r]+){0,3})", text, re.IGNORECASE)
        if ing_match:
            raw_ing = ing_match.group(1).strip()
        elif "ingredient" in text.lower():
            raw_ing = text.strip()

        ing_list = []
        additives = []
        if raw_ing:
            ing_list = [i.strip(" .()") for i in re.split(r"[,;]+", raw_ing) if i.strip()]
            for pat in cls.ADDITIVE_PATTERNS:
                f_list = re.findall(pat, raw_ing, re.IGNORECASE)
                for f in f_list:
                    if f.title() not in additives:
                        additives.append(f.strip().title())

        is_clean = len(additives) == 0 and bool(raw_ing)

        ingredients = Ingredients(
            raw_text=raw_ing,
            ingredient_list=ing_list,
            additives=additives,
            is_clean_label=is_clean,
            source=source_name,
            source_url=source_url,
            confidence=SourceConfidence.MEDIUM if raw_ing else SourceConfidence.UNVERIFIED,
            retrieved_at=now_str
        )

        # Extract Allergens
        contains_list = []
        may_contain_list = []
        text_lower = text.lower()

        # Check explicit contains
        contains_match = re.search(r"(?:contains|allergen(?:s)?(?:\s*declaration)?)\s*[:=]\s*([^\n\r\.]+)", text, re.IGNORECASE)
        if contains_match:
            chunk = contains_match.group(1).lower()
            for allergen in cls.KNOWN_ALLERGENS:
                if re.search(r"\b" + re.escape(allergen) + r"\b", chunk):
                    contains_list.append(allergen)
        else:
            # Search entire text for declared allergens
            for allergen in cls.KNOWN_ALLERGENS:
                if re.search(r"\b" + re.escape(allergen) + r"\b", text_lower):
                    contains_list.append(allergen)

        # Check may contain / cross contamination
        may_match = re.search(r"(?:may\s*contain|manufactured\s*in\s*a\s*facility\s*that\s*also\s*processes?)\s*[:=]?\s*([^\n\r\.]+)", text, re.IGNORECASE)
        if may_match:
            chunk = may_match.group(1).lower()
            for allergen in cls.KNOWN_ALLERGENS:
                if re.search(r"\b" + re.escape(allergen) + r"\b", chunk):
                    may_contain_list.append(allergen)

        allergens = Allergens(
            contains=list(set(contains_list)),
            may_contain=list(set(may_contain_list)),
            free_from=[],
            source=source_name,
            source_url=source_url,
            confidence=SourceConfidence.MEDIUM if (contains_list or raw_ing) else SourceConfidence.UNVERIFIED,
            retrieved_at=now_str
        )

        return nutrition, ingredients, allergens
