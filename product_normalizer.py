import re
import hashlib
from typing import Optional, Tuple, Dict, Any

class ProductNormalizer:
    """
    Normalizes Product Names, Brands, Pack Sizes, and Variants.
    Guarantees exact variant and size matching to prevent conflating
    different formulations (e.g. Peanut Butter vs Cocoa) or pack sizes.
    """

    KNOWN_VARIANTS = [
        "double cocoa", "dark chocolate", "peanut butter", "hazelnut",
        "almond fudge", "cranberry", "blueberry", "vanilla", "cinnamon",
        "salted caramel", "cookies & cream", "coconut", "matcha", "coffee",
        "unsweetened", "sugar free", "gluten free", "vegan", "keto"
    ]

    @classmethod
    def clean_text(cls, text: str) -> str:
        if not text:
            return ""
        # Remove weird symbols, redundant spaces
        cleaned = re.sub(r"[\t\r\n]+", " ", text)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def normalize_brand(cls, raw_brand: Optional[str]) -> str:
        if not raw_brand or not raw_brand.strip():
            return "Independent Brand"
        b = cls.clean_text(raw_brand)
        # Strip trailing 'Foods', 'Pvt Ltd', 'Inc', 'LLC', etc.
        b = re.sub(r"\b(pvt\.?\s*ltd\.?|private\s*limited|inc\.?|llc|co\.?|corp\.?|foods|nutrition)\b", "", b, flags=re.I)
        b = re.sub(r"[\s,\-\.]+$", "", b).strip()
        return b.title() if b else raw_brand.strip().title()

    @classmethod
    def extract_pack_size(cls, text: str) -> Optional[str]:
        """Extracts and normalizes pack size or weight string."""
        if not text:
            return None
        # Match weight in g, kg, ml, l or count
        m = re.search(r"(\d+(?:\.\d+)?)\s*(g|kg|ml|l|grams?|litres?|pack\s*of\s*\d+|bars?|count)\b", text, re.I)
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            if unit in ("kg",):
                val = int(val * 1000)
                return f"{val}g"
            elif unit in ("l", "litres"):
                val = int(val * 1000)
                return f"{val}ml"
            elif unit in ("g", "grams"):
                return f"{int(val) if val.is_integer() else val}g"
            elif unit in ("ml",):
                return f"{int(val) if val.is_integer() else val}ml"
            else:
                return f"{int(val) if val.is_integer() else val} {unit}"
        return None

    @classmethod
    def extract_variant(cls, text: str) -> Optional[str]:
        """Identifies formulation variant or flavor."""
        if not text:
            return None
        text_lower = text.lower()
        for v in cls.KNOWN_VARIANTS:
            if re.search(r"\b" + re.escape(v) + r"\b", text_lower):
                return v.title()
        
        # Flavor in parentheses or after hyphen, e.g., 'Ka-Me - Rice Noodles' or 'Bar (Dark Chocolate)'
        parentheses_match = re.search(r"\(([^)]+)\)", text)
        if parentheses_match:
            candidate = parentheses_match.group(1).strip()
            if len(candidate) <= 30 and not any(char.isdigit() for char in candidate):
                return candidate.title()
        return None

    @classmethod
    def generate_product_id(cls, brand: str, name: str, variant: Optional[str] = None, pack_size: Optional[str] = None, barcode: Optional[str] = None) -> str:
        """Deterministic product ID hash."""
        if barcode and barcode.strip():
            return f"SB-{barcode.strip()}"
        key_str = f"{brand.lower()}|{name.lower()}|{str(variant).lower()}|{str(pack_size).lower()}".strip()
        hash_val = hashlib.sha256(key_str.encode("utf-8")).hexdigest()[:12].upper()
        return f"SB-PRD-{hash_val}"

    @classmethod
    def is_exact_match(cls, title_a: str, title_b: str) -> Tuple[bool, str]:
        """
        Validates if two product titles refer to the exact same formulation and size.
        Returns (is_match, reason).
        """
        pack_a = cls.extract_pack_size(title_a)
        pack_b = cls.extract_pack_size(title_b)
        if pack_a and pack_b and pack_a.lower() != pack_b.lower():
            return False, f"Pack size mismatch ({pack_a} vs {pack_b})"

        var_a = cls.extract_variant(title_a)
        var_b = cls.extract_variant(title_b)
        if var_a and var_b and var_a.lower() != var_b.lower():
            return False, f"Variant formulation mismatch ({var_a} vs {var_b})"

        return True, "Exact or compatible variant match"
