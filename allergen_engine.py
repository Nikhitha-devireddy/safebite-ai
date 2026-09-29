"""
SafeBite AI - Clinical Allergen Intelligence Engine
Provides comprehensive, deterministic detection of direct allergens, hidden derivatives,
precautionary allergen labeling (PAL / "may contain"), and cross-contact facility warnings.
Strictly excludes false positives (e.g., cocoa butter, peanut butter != dairy butter).
"""

import re
from enum import Enum
from typing import List, Dict, Set, Optional, Tuple
from pydantic import BaseModel, Field

from schemas import Product, Allergens, Ingredients, SourceConfidence

class AllergenDetectionType(str, Enum):
    DIRECT = "DIRECT"                   # Direct allergen declared (e.g. "peanuts", "milk")
    DERIVATIVE = "DERIVATIVE"           # Hidden chemical/processing derivative (e.g. "casein", "whey", "maltodextrin")
    TRACE_MAY_CONTAIN = "MAY_CONTAIN"   # Precautionary label (e.g. "may contain traces of...")
    CROSS_CONTACT = "CROSS_CONTACT"     # Shared equipment or facility statement

class AllergenHit(BaseModel):
    allergen_category: str = Field(description="Normalized allergen category (e.g., 'Dairy / Milk', 'Peanuts')")
    user_declared_allergy: str = Field(description="User allergy that matched this trigger")
    matched_token: str = Field(description="Exact ingredient token or phrase identified")
    detection_type: AllergenDetectionType = Field(description="DIRECT, DERIVATIVE, MAY_CONTAIN, or CROSS_CONTACT")
    evidence_snippet: str = Field(description="Contextual quote from ingredients/label")
    clinical_risk: str = Field(description="Clinical risk explanation")
    confidence: SourceConfidence = Field(default=SourceConfidence.HIGH)

class AllergenEngine:
    """
    Standardized, research-grade food allergy screening engine.
    """

    # Comprehensive Taxonomy with explicit derivatives and false-positive guards
    ALLERGEN_TAXONOMY: Dict[str, Dict[str, Any]] = {
        "dairy": {
            "canonical_name": "Dairy / Milk",
            "aliases": ["milk", "dairy", "cow's milk", "lactose", "casein", "whey", "milk protein"],
            "direct_tokens": [
                "milk", "cow milk", "skim milk", "whole milk", "condensed milk",
                "milk powder", "milk solids", "curd", "yogurt", "yoghurt", "paneer",
                "cheese", "cream", "sour cream", "ghee", "clarified butter", "dairy butter"
            ],
            "derivative_tokens": [
                "casein", "sodium caseinate", "calcium caseinate", "potassium caseinate",
                "whey", "whey protein", "whey powder", "whey isolate", "demineralized whey",
                "lactose", "lactalbumin", "lactoglobulin", "hydrolyzed whey", "butterfat",
                "anhydrous milk fat", "milkfat", "buttermilk", "reconstituted milk"
            ],
            # Exclude plant-based butters and non-dairy foods matching "butter" or "milk"
            "false_positive_regex": [
                r"\b(?:cocoa|cacao|peanut|almond|cashew|shea|apple|mango|coconut|soy|sunflower)\s+butter\b",
                r"\b(?:almond|soy|oat|coconut|rice|cashew|hemp|flax|pea)\s+milk\b",
                r"\bbutternut\s+squash\b",
                r"\bbutterfly\s+pea\b"
            ]
        },
        "peanut": {
            "canonical_name": "Peanuts",
            "aliases": ["peanut", "peanuts", "groundnut", "groundnuts", "monkey nut", "arachis"],
            "direct_tokens": [
                "peanut", "peanuts", "groundnut", "groundnuts", "monkey nut", "earthnut"
            ],
            "derivative_tokens": [
                "peanut butter", "peanut paste", "peanut flour", "peanut meal",
                "arachis oil", "peanut protein", "defatted peanut flour", "cold-pressed peanut oil"
            ],
            "false_positive_regex": []
        },
        "tree_nut": {
            "canonical_name": "Tree Nuts",
            "aliases": ["tree nut", "tree nuts", "nuts", "almond", "walnut", "cashew", "pistachio", "hazelnut", "pecan", "macadamia", "brazil nut"],
            "direct_tokens": [
                "almond", "almonds", "walnut", "walnuts", "cashew", "cashews", "kaju",
                "pistachio", "pistachios", "pista", "hazelnut", "hazelnuts", "pecan", "pecans",
                "macadamia", "macadamias", "brazil nut", "brazil nuts", "pine nut", "pine nuts",
                "chestnut", "chestnuts", "praline", "marzipan", "gianduja"
            ],
            "derivative_tokens": [
                "almond flour", "almond meal", "almond butter", "cashew butter",
                "hazelnut paste", "walnut oil", "pistachio paste", "praline paste"
            ],
            "false_positive_regex": [
                r"\bwater\s+chestnut\b",   # Water chestnut is a tuber, not a tree nut
                r"\bnutmeg\b",             # Nutmeg is a seed, not a tree nut
                r"\bbutternut\b"
            ]
        },
        "gluten": {
            "canonical_name": "Gluten / Wheat",
            "aliases": ["gluten", "wheat", "celiac", "barley", "rye", "spelt", "semolina", "atta", "maida"],
            "direct_tokens": [
                "wheat", "barley", "rye", "spelt", "kamut", "triticale", "semolina",
                "durum", "farina", "atta", "maida", "suji", "sooji", "graham flour",
                "emmer", "einkorn", "vital wheat gluten"
            ],
            "derivative_tokens": [
                "malt", "malt extract", "barley malt", "malt flavoring", "malt syrup",
                "maltodextrin", "wheat starch", "hydrolyzed wheat protein", "brewer's yeast",
                "wheat germ", "wheat bran", "modified wheat starch"
            ],
            "false_positive_regex": [
                r"\bbuckwheat\b",          # Buckwheat is naturally gluten-free
                r"\bcorn\s*maltodextrin\b",
                r"\btapioca\s*maltodextrin\b",
                r"\brice\s*maltodextrin\b"
            ]
        },
        "soy": {
            "canonical_name": "Soy / Soybean",
            "aliases": ["soy", "soya", "soybean", "soybeans", "edamame"],
            "direct_tokens": [
                "soy", "soya", "soybean", "soybeans", "edamame", "tofu", "tempeh", "miso", "natto"
            ],
            "derivative_tokens": [
                "soy lecithin", "soya lecithin", "soy protein", "soy protein isolate",
                "hydrolyzed soy protein", "textured vegetable protein", "tvp", "soy sauce",
                "tamari", "soy flour", "soybean oil"
            ],
            "false_positive_regex": []
        },
        "egg": {
            "canonical_name": "Eggs",
            "aliases": ["egg", "eggs", "albumin", "egg white", "egg yolk"],
            "direct_tokens": [
                "egg", "eggs", "whole egg", "egg white", "egg yolk", "egg powder", "mayonnaise"
            ],
            "derivative_tokens": [
                "albumin", "albumen", "ovalbumin", "lysozyme", "ovomucoid", "ovotransferrin",
                "livetin", "vitellin", "meringue", "globulin"
            ],
            "false_positive_regex": [
                r"\beggplant\b"            # Eggplant is a nightshade vegetable, not poultry egg
            ]
        },
        "fish": {
            "canonical_name": "Fish",
            "aliases": ["fish", "finfish", "cod", "salmon", "tuna", "anchovy"],
            "direct_tokens": [
                "fish", "salmon", "tuna", "cod", "anchovy", "anchovies", "mackerel",
                "sardine", "sardines", "trout", "tilapia", "haddock", "halibut", "snapper"
            ],
            "derivative_tokens": [
                "fish oil", "fish sauce", "isinglass", "fish gelatin", "caesar dressing", "worcestershire sauce"
            ],
            "false_positive_regex": [
                r"\bfish\s*shaped\b"
            ]
        },
        "shellfish": {
            "canonical_name": "Shellfish & Crustaceans",
            "aliases": ["shellfish", "crustacean", "crustaceans", "shrimp", "prawn", "crab", "lobster", "mollusc"],
            "direct_tokens": [
                "shrimp", "shrimps", "prawn", "prawns", "crab", "crabs", "lobster", "lobsters",
                "crayfish", "clam", "clams", "mussel", "mussels", "oyster", "oysters", "scallop",
                "scallops", "squid", "calamari", "octopus"
            ],
            "derivative_tokens": [
                "glucosamine", "chitin", "chitosan", "krill oil", "shrimp paste", "oyster sauce"
            ],
            "false_positive_regex": []
        },
        "sesame": {
            "canonical_name": "Sesame",
            "aliases": ["sesame", "tahini", "til", "gingelly"],
            "direct_tokens": [
                "sesame", "sesame seed", "sesame seeds", "tahini", "til", "gingelly", "sesamum"
            ],
            "derivative_tokens": [
                "sesame oil", "toasted sesame oil", "sesame flour", "sesame paste"
            ],
            "false_positive_regex": []
        },
        "mustard": {
            "canonical_name": "Mustard",
            "aliases": ["mustard", "sarson", "rai"],
            "direct_tokens": [
                "mustard", "mustard seed", "mustard seeds", "sarson", "rai"
            ],
            "derivative_tokens": [
                "mustard oil", "mustard powder", "prepared mustard", "mustard greens"
            ],
            "false_positive_regex": []
        },
        "sulfites": {
            "canonical_name": "Sulfites / Sulphites",
            "aliases": ["sulfite", "sulfites", "sulphite", "sulphites", "sulfur dioxide"],
            "direct_tokens": [
                "sulfite", "sulfites", "sulphite", "sulphites", "sulfur dioxide", "sulphur dioxide"
            ],
            "derivative_tokens": [
                "sodium metabisulfite", "potassium metabisulfite", "sodium bisulfite",
                "potassium bisulfite", "sodium sulfite"
            ],
            "false_positive_regex": []
        }
    }

    # Precautionary allergen patterns
    PAL_PATTERNS = [
        (r"\bmay\s+contain\s+traces?\s+of\s+([^\.\n;]+)", AllergenDetectionType.TRACE_MAY_CONTAIN),
        (r"\bmay\s+contain\s+([^\.\n;]+)", AllergenDetectionType.TRACE_MAY_CONTAIN),
        (r"\bmade\s+in\s+a\s+facility\s+that\s+(?:also\s+)?(?:processes|handles)\s+([^\.\n;]+)", AllergenDetectionType.CROSS_CONTACT),
        (r"\bprocessed\s+(?:on|in)\s+shared\s+equipment\s+with\s+([^\.\n;]+)", AllergenDetectionType.CROSS_CONTACT),
        (r"\bmanufactured\s+on\s+equipment\s+that\s+(?:also\s+)?processes\s+([^\.\n;]+)", AllergenDetectionType.CROSS_CONTACT)
    ]

    @classmethod
    def match_user_allergy_category(cls, user_allergy: str) -> Optional[str]:
        """Resolves user string e.g. 'Dairy (Whey, Casein)' or 'Peanuts' to internal category key."""
        ua_clean = user_allergy.lower().strip()
        for cat_key, cat_data in cls.ALLERGEN_TAXONOMY.items():
            if cat_key in ua_clean or cat_data["canonical_name"].lower() in ua_clean:
                return cat_key
            for alias in cat_data["aliases"]:
                if alias in ua_clean or ua_clean in alias:
                    return cat_key
        return None

    @classmethod
    def screen_product(
        cls,
        product: Product,
        user_allergies: List[str]
    ) -> List[AllergenHit]:
        """
        Comprehensive product allergen screen.
        Audits:
        1. Declared allergens (Allergens.contains)
        2. Precautionary labeling (Allergens.may_contain, cross_contact_warnings)
        3. Ingredients raw text + token list (direct & derivatives)
        4. Product title & variant
        """
        hits: List[AllergenHit] = []
        if not user_allergies:
            return hits

        cleaned_user_allergens = [a.strip() for a in user_allergies if a.strip() and a.lower() != "none"]
        if not cleaned_user_allergens:
            return hits

        # Consolidate product text fields
        raw_ing_text = (product.ingredients.raw_text or "") if product.ingredients else ""
        ing_tokens = (product.ingredients.ingredient_list or []) if product.ingredients else []
        declared_contains = (product.allergens.contains or []) if product.allergens else []
        declared_may_contain = (product.allergens.may_contain or []) if product.allergens else []
        declared_cross = (product.allergens.cross_contact_warnings or []) if product.allergens else []
        title_variant_text = f"{product.brand} {product.name} {product.variant or ''}".lower()

        # Extract precautionary text from raw ingredient string
        pal_snippets: List[Tuple[str, AllergenDetectionType]] = []
        for pat, det_type in cls.PAL_PATTERNS:
            for m in re.finditer(pat, raw_ing_text, re.IGNORECASE):
                pal_snippets.append((m.group(0), det_type))

        for user_all in cleaned_user_allergens:
            cat_key = cls.match_user_allergy_category(user_all)
            cat_data = cls.ALLERGEN_TAXONOMY.get(cat_key) if cat_key else None

            # 1. SCREEN DECLARED ALLERGENS (contains)
            for item in declared_contains:
                item_lower = item.lower().strip()
                is_match = False
                if cat_data:
                    is_match = any(alias in item_lower for alias in cat_data["aliases"]) or (cat_key in item_lower)
                else:
                    is_match = user_all.lower() in item_lower or item_lower in user_all.lower()

                if is_match:
                    hits.append(AllergenHit(
                        allergen_category=cat_data["canonical_name"] if cat_data else user_all.title(),
                        user_declared_allergy=user_all,
                        matched_token=item,
                        detection_type=AllergenDetectionType.DIRECT,
                        evidence_snippet=f"Declared in product allergen statement: '{item}'",
                        clinical_risk=f"Strict Contraindication: Product explicitly declares presence of {item}."
                    ))

            # 2. SCREEN PRECAUTIONARY ALLERGENS (may contain & cross-contact)
            for item in declared_may_contain:
                item_lower = item.lower().strip()
                is_match = False
                if cat_data:
                    is_match = any(alias in item_lower for alias in cat_data["aliases"]) or (cat_key in item_lower)
                else:
                    is_match = user_all.lower() in item_lower

                if is_match:
                    hits.append(AllergenHit(
                        allergen_category=cat_data["canonical_name"] if cat_data else user_all.title(),
                        user_declared_allergy=user_all,
                        matched_token=item,
                        detection_type=AllergenDetectionType.TRACE_MAY_CONTAIN,
                        evidence_snippet=f"Precautionary statement: 'May contain {item}'",
                        clinical_risk=f"Cross-Contact Risk: Manufacturer warns product may contain traces of {item}."
                    ))

            for stmt in declared_cross:
                stmt_lower = stmt.lower()
                is_match = False
                if cat_data:
                    is_match = any(alias in stmt_lower for alias in cat_data["aliases"])
                else:
                    is_match = user_all.lower() in stmt_lower

                if is_match:
                    hits.append(AllergenHit(
                        allergen_category=cat_data["canonical_name"] if cat_data else user_all.title(),
                        user_declared_allergy=user_all,
                        matched_token=user_all,
                        detection_type=AllergenDetectionType.CROSS_CONTACT,
                        evidence_snippet=stmt,
                        clinical_risk=f"Facility Cross-Contact Warning: {stmt}"
                    ))

            # 3. SCREEN RAW INGREDIENTS & TOKENS (DIRECT & DERIVATIVES)
            if raw_ing_text:
                filtered_text = raw_ing_text
                # Remove false positive phrases before testing (e.g. cocoa butter)
                if cat_data:
                    for fp_pat in cat_data.get("false_positive_regex", []):
                        filtered_text = re.sub(fp_pat, " ", filtered_text, flags=re.IGNORECASE)

                # Check direct tokens
                tokens_to_test = cat_data["direct_tokens"] if cat_data else [user_all.lower()]
                for tok in tokens_to_test:
                    # Match whole word
                    pat = r"\b" + re.escape(tok) + r"\b"
                    match = re.search(pat, filtered_text, re.IGNORECASE)
                    if match:
                        snippet = cls._extract_snippet(filtered_text, match.start(), match.end())
                        # Check if this snippet was actually inside a "may contain" statement
                        is_inside_pal = any(tok in ps[0].lower() for ps in pal_snippets)
                        det_type = AllergenDetectionType.TRACE_MAY_CONTAIN if is_inside_pal else AllergenDetectionType.DIRECT

                        # Avoid duplicate hits
                        if not any(h.matched_token.lower() == tok.lower() and h.detection_type == det_type for h in hits):
                            hits.append(AllergenHit(
                                allergen_category=cat_data["canonical_name"] if cat_data else user_all.title(),
                                user_declared_allergy=user_all,
                                matched_token=tok,
                                detection_type=det_type,
                                evidence_snippet=snippet,
                                clinical_risk="Direct Ingredient Trigger" if det_type == AllergenDetectionType.DIRECT else "Precautionary Ingredient Mention"
                            ))

                # Check hidden derivative tokens
                if cat_data:
                    for der in cat_data["derivative_tokens"]:
                        pat = r"\b" + re.escape(der) + r"\b"
                        match = re.search(pat, filtered_text, re.IGNORECASE)
                        if match:
                            snippet = cls._extract_snippet(filtered_text, match.start(), match.end())
                            if not any(h.matched_token.lower() == der.lower() for h in hits):
                                hits.append(AllergenHit(
                                    allergen_category=cat_data["canonical_name"],
                                    user_declared_allergy=user_all,
                                    matched_token=der,
                                    detection_type=AllergenDetectionType.DERIVATIVE,
                                    evidence_snippet=snippet,
                                    clinical_risk=f"Hidden Derivative Alert: '{der}' is a biochemical derivative of {cat_data['canonical_name']}."
                                ))

            # 4. SCREEN PRODUCT TITLE & VARIANT
            if cat_data:
                for tok in cat_data["direct_tokens"]:
                    if len(tok) >= 4 and re.search(r"\b" + re.escape(tok) + r"\b", title_variant_text):
                        if not any(h.matched_token.lower() == tok.lower() for h in hits):
                            hits.append(AllergenHit(
                                allergen_category=cat_data["canonical_name"],
                                user_declared_allergy=user_all,
                                matched_token=tok,
                                detection_type=AllergenDetectionType.DIRECT,
                                evidence_snippet=f"Found in product title/variant: '{product.name} {product.variant or ''}'",
                                clinical_risk=f"Direct Allergen in Product Title: Explicit {tok} formulation."
                            ))

        return hits

    @staticmethod
    def _extract_snippet(text: str, start: int, end: int, window: int = 40) -> str:
        s = max(0, start - window)
        e = min(len(text), end + window)
        snippet = text[s:e].strip()
        if s > 0:
            snippet = "..." + snippet
        if e < len(text):
            snippet = snippet + "..."
        return snippet
