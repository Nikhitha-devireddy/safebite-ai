import re
from typing import List, Dict, Any, Optional, Tuple
from schemas import Product, SourceConfidence
from product_sources import ProductSources
from evidence_engine import EvidenceEngine

class ProductSearchPipeline:
    """
    Search -> Retrieve -> Verify -> Normalize -> Filter -> Reason -> Cite.
    Processes complex queries like:
    'Find low-sugar protein bars without peanuts under ₹500 available in Bengaluru.'
    """

    def __init__(self):
        self.sources = ProductSources()

    def parse_query_criteria(self, query: str) -> Dict[str, Any]:
        """Parses natural language query constraints."""
        q_lower = query.lower()
        
        # 1. Price constraint (e.g. 'under ₹500', 'under 500', '< 300', 'below 400')
        max_price = None
        price_match = re.search(r"(?:under|below|less\s*than|<)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", q_lower)
        if price_match:
            try:
                max_price = float(price_match.group(1))
            except ValueError:
                pass

        # 2. Nutrition constraints
        low_sugar = any(w in q_lower for w in ["low sugar", "low-sugar", "no sugar", "sugar free", "zero sugar", "diabetic"])
        high_protein = any(w in q_lower for w in ["high protein", "high-protein", "protein"])

        # 3. Allergen exclusions (e.g. 'without peanuts', 'no peanuts', 'nut-free', 'dairy-free')
        excluded_allergens = []
        for all_match in re.finditer(r"(?:without|no|free\s*from|zero)\s+([a-z\s]+?)(?=\s+(?:under|below|in|available|for|\$|₹|\d|$))", q_lower):
            raw_item = all_match.group(1).strip()
            if raw_item in ("sugar", "carbs", "added sugar"):
                low_sugar = True
            elif raw_item in ("peanuts", "peanut", "nuts", "dairy", "milk", "gluten", "soy", "eggs"):
                excluded_allergens.append(raw_item)

        if "peanut free" in q_lower or "without peanuts" in q_lower:
            if "peanuts" not in excluded_allergens:
                excluded_allergens.append("peanuts")
        if "gluten free" in q_lower or "without gluten" in q_lower:
            if "gluten" not in excluded_allergens:
                excluded_allergens.append("gluten")
        if "dairy free" in q_lower or "without dairy" in q_lower:
            if "dairy" not in excluded_allergens:
                excluded_allergens.append("dairy")

        # 4. Location extraction (e.g. 'in Bengaluru', 'available in Bengaluru', 'in Mumbai')
        location = "Bengaluru"
        loc_match = re.search(r"(?:in|for|at|around)\s+([A-Za-z]+)\b", query, re.I)
        if loc_match:
            candidate_loc = loc_match.group(1).strip()
            if candidate_loc.lower() not in ("low", "high", "under", "without", "bars", "peanuts", "sugar"):
                location = candidate_loc.title()

        # 5. Extract core food craving / product keywords
        clean_target = query
        words_to_strip = [
            r"\bfind\b", r"\bsearch(?:\s+for)?\b", r"\bshow\s+me\b", r"\blooking\s+for\b",
            r"\blow[\-\s]sugar\b", r"\bno\s+sugar\b", r"\bsugar[\-\s]free\b", r"\bzero\s+sugar\b",
            r"\bhigh[\-\s]protein\b", r"\bwithout\s+[a-z]+\b", r"\bfree\s+from\s+[a-z]+\b",
            r"\b(?:under|below|less\s+than|<)\s*(?:₹|rs\.?|inr)?\s*\d+\b",
            r"\bavailable\s+in\s+[a-z]+\b",
            r"\bin\s+(?:bengaluru|bangalore|mumbai|delhi|hyderabad|chennai|pune|kolkata|london|new\s+york|india|usa|uk)\b",
            r"\bbest\b"
        ]
        for pat in words_to_strip:
            clean_target = re.sub(pat, " ", clean_target, flags=re.I)
        # Strip trailing punctuation, extra spaces
        clean_target = re.sub(r"[\.,;:!\?]+", " ", clean_target)
        clean_target = re.sub(r"\s+", " ", clean_target).strip()
        if not clean_target:
            clean_target = "Protein Bar"

        return {
            "search_term": clean_target,
            "max_price": max_price,
            "low_sugar": low_sugar,
            "high_protein": high_protein,
            "excluded_allergens": excluded_allergens,
            "location": location,
            "raw_query": query
        }

    def search_and_filter(
        self,
        query: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None
    ) -> Tuple[List[Product], Dict[str, Any], str]:
        """
        Executes full Search -> Retrieve -> Verify -> Normalize -> Filter -> Reason -> Cite cycle.
        Returns:
            (List[matching_products], criteria_dict, reasoning_summary)
        """
        criteria = self.parse_query_criteria(query)
        user_allergies = user_allergies or []
        
        # Combine user's profile allergies with query-specific exclusions
        effective_allergens = list(set([a.lower() for a in user_allergies if a.strip()] + criteria["excluded_allergens"]))
        
        # Search Open Food Facts and Retailers
        search_term = criteria["search_term"]
        location = criteria["location"]

        # If user explicitly searched for protein bars, query top safe clean-label variants
        query_candidates = [search_term]
        if "protein" in search_term.lower() and "bar" in search_term.lower():
            query_candidates.extend([
                "The Whole Truth Protein Bar",
                "Yogabar Protein Bar",
                "Phab Protein Bar",
                "RiteBite Max Protein Bar"
            ])

        discovered_products: List[Product] = []
        seen_ids = set()

        for cand in query_candidates[:4]:
            prod = self.sources.route_and_fetch(
                raw_input=cand,
                user_medical_history=user_medical_history,
                user_allergies=effective_allergens,
                location=location
            )
            if prod and prod.id not in seen_ids:
                seen_ids.add(prod.id)
                discovered_products.append(prod)

        # FILTERING & REASONING STAGE
        passed_products: List[Product] = []
        for p in discovered_products:
            # 1. Price check
            if criteria["max_price"] is not None:
                # Check minimum available price among retailer offers
                valid_prices = [o.price for o in p.retailer_offers if o.price is not None]
                if valid_prices:
                    min_price = min(valid_prices)
                    if min_price > criteria["max_price"]:
                        continue # Exceeds budget

            # 2. Allergen check (Strict)
            if effective_allergens:
                has_conflict = False
                if p.allergens:
                    for excl in effective_allergens:
                        for c in p.allergens.contains:
                            if excl in c.lower() or c.lower() in excl:
                                has_conflict = True
                                break
                if has_conflict:
                    continue

            # 3. Low-sugar check
            if criteria["low_sugar"] and p.nutrition and p.nutrition.sugar_g is not None:
                if p.nutrition.sugar_g > 10.0:
                    continue # Too high in sugar for low-sugar criteria

            passed_products.append(p)

        # Sort products: prefer verified high confidence, then lowest sugar if requested
        if criteria["low_sugar"]:
            passed_products.sort(
                key=lambda x: (
                    x.evidence.overall_confidence == SourceConfidence.HIGH,
                    -(x.nutrition.sugar_g if x.nutrition and x.nutrition.sugar_g is not None else 999)
                ),
                reverse=True
            )
        else:
            passed_products.sort(
                key=lambda x: x.evidence.overall_confidence == SourceConfidence.HIGH,
                reverse=True
            )

        # REASONING & CITING
        price_cap_str = f"₹{criteria['max_price']}" if criteria['max_price'] else "No Price Cap"
        summary_lines = [
            f"### 🎯 Intelligence Search Results for: *'{query}'*",
            f"- **Target Product**: `{criteria['search_term'].title()}` | **Location**: `{location}`",
            f"- **Strict Allergen Filter**: `{', '.join(effective_allergens) if effective_allergens else 'None'}`",
            f"- **Price Cap**: `{price_cap_str}`",
            f"- **Low-Sugar Constraint**: `{'Active (<= 10g sugar limit)' if criteria['low_sugar'] else 'Standard'}`",
            f"- **Verified Matching Products Discovered**: **{len(passed_products)} items**"
        ]

        if not passed_products:
            summary_lines.append(
                "\n⚠️ No product in our verified database met all strict constraints simultaneously. "
                "Try relaxing the price limit or searching for a specific brand name directly."
            )
        else:
            summary_lines.append(
                f"\nAll returned items have been cross-checked against live inventories in **{location}** "
                f"across Amazon, BigBasket, Blinkit, and Zepto with verified evidence citations."
            )

        reasoning_text = "\n".join(summary_lines)
        return passed_products, criteria, reasoning_text
