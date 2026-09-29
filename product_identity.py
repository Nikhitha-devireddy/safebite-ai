"""
SafeBite AI - Product Identity & Variant Matching Engine
Guarantees that different formulations (e.g. Chocolate vs Peanut Butter, 50g vs 500g)
are NEVER conflated or merged.
Assigns deterministic confidence: EXACT, HIGH, POSSIBLE, UNVERIFIED.
Only EXACT and HIGH confidence matches can drive clinical safety conclusions.
"""

import re
from typing import Optional, Tuple, Dict, Any
from schemas import ProductIdentityConfidence
from product_normalizer import ProductNormalizer

class ProductIdentityMatcher:
    """
    Deterministic identity comparator preventing variant cross-contamination.
    """

    DISTINCT_FLAVORS = [
        {"chocolate", "cocoa", "dark chocolate", "fudge"},
        {"peanut", "peanut butter", "groundnut"},
        {"almond", "almond fudge", "badam"},
        {"berry", "blueberry", "cranberry", "strawberry", "raspberry"},
        {"vanilla", "french vanilla"},
        {"coffee", "mocha", "espresso", "cappuccino"},
        {"caramel", "salted caramel", "toffee"},
        {"coconut"},
        {"cinnamon"},
        {"cookies and cream", "cookies & cream", "oreo"},
        {"mango"},
        {"plain", "unflavored", "unsweetened", "original"}
    ]

    @classmethod
    def get_flavor_family(cls, text: str) -> Optional[str]:
        """Identifies primary flavor family to prevent merging conflicting variants."""
        text_lower = text.lower()
        for idx, family in enumerate(cls.DISTINCT_FLAVORS):
            for item in family:
                if re.search(r"\b" + re.escape(item) + r"\b", text_lower):
                    return sorted(list(family))[0] # Canonical family key
        return None

    @classmethod
    def evaluate_match(
        cls,
        target_name: str,
        candidate_name: str,
        target_brand: Optional[str] = None,
        candidate_brand: Optional[str] = None,
        target_pack: Optional[str] = None,
        candidate_pack: Optional[str] = None,
        target_barcode: Optional[str] = None,
        candidate_barcode: Optional[str] = None
    ) -> Tuple[ProductIdentityConfidence, str]:
        """
        Determines identity match confidence between a reference item and an external listing.
        Returns:
            (ProductIdentityConfidence, rationale)
        """
        # 1. Barcode comparison (Gold Standard)
        if target_barcode and candidate_barcode:
            tb = re.sub(r"\D", "", str(target_barcode))
            cb = re.sub(r"\D", "", str(candidate_barcode))
            if tb and cb:
                if tb == cb:
                    return ProductIdentityConfidence.EXACT, f"Exact barcode verification match ({tb})."
                else:
                    return ProductIdentityConfidence.UNVERIFIED, f"Barcode conflict: target '{tb}' vs candidate '{cb}'."

        # 2. Brand comparison
        norm_t_brand = ProductNormalizer.normalize_brand(target_brand or target_name.split()[0]).lower()
        norm_c_brand = ProductNormalizer.normalize_brand(candidate_brand or candidate_name.split()[0]).lower()

        # If brands are explicitly known and conflict
        if norm_t_brand and norm_c_brand and norm_t_brand != "independent brand" and norm_c_brand != "independent brand":
            if norm_t_brand not in norm_c_brand and norm_c_brand not in norm_t_brand:
                return ProductIdentityConfidence.UNVERIFIED, f"Brand mismatch: '{norm_t_brand}' vs '{norm_c_brand}'."

        # 3. Variant & Flavor Conflict Check (Critical for Clinical Safety)
        t_flavor = cls.get_flavor_family(target_name)
        c_flavor = cls.get_flavor_family(candidate_name)

        if t_flavor and c_flavor and t_flavor != c_flavor:
            return ProductIdentityConfidence.UNVERIFIED, f"Variant conflict: target flavor is '{t_flavor}', but candidate listing is '{c_flavor}'."

        # 4. Pack Size Conflict Check
        t_pack = target_pack or ProductNormalizer.extract_pack_size(target_name)
        c_pack = candidate_pack or ProductNormalizer.extract_pack_size(candidate_name)

        if t_pack and c_pack and t_pack.lower() != c_pack.lower():
            # If pack sizes conflict significantly (e.g. 50g vs 500g)
            return ProductIdentityConfidence.POSSIBLE, f"Pack size difference ({t_pack} vs {c_pack}). Composition may be compatible, but pack quantities differ."

        # 5. Core Name Token Overlap
        clean_t = re.sub(r"[^\w\s]", "", target_name.lower())
        clean_c = re.sub(r"[^\w\s]", "", candidate_name.lower())
        t_tokens = set(clean_t.split())
        c_tokens = set(clean_c.split())

        # Exclude generic filler words
        stop_words = {"the", "a", "an", "bar", "pack", "of", "and", "with", "organic", "natural", "premium", "box"}
        t_sig = t_tokens - stop_words
        c_sig = c_tokens - stop_words

        if not t_sig:
            return ProductIdentityConfidence.POSSIBLE, "Insufficient unique tokens in target name."

        intersection = t_sig.intersection(c_sig)
        overlap_ratio = len(intersection) / float(len(t_sig))

        if overlap_ratio >= 0.8:
            return ProductIdentityConfidence.HIGH, f"High semantic token overlap ({overlap_ratio:.0%}) with matching brand and flavor."
        elif overlap_ratio >= 0.4:
            return ProductIdentityConfidence.POSSIBLE, f"Moderate token overlap ({overlap_ratio:.0%}). Needs manual verification."
        else:
            return ProductIdentityConfidence.UNVERIFIED, f"Low semantic title overlap ({overlap_ratio:.0%})."

    @classmethod
    def can_merge_clinical_evidence(cls, confidence: ProductIdentityConfidence) -> bool:
        """Only EXACT and HIGH confidence matches are medically safe to combine."""
        return confidence in (ProductIdentityConfidence.EXACT, ProductIdentityConfidence.HIGH)
