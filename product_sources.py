import re
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import requests

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    RetailerOffer, Evidence, SourceConfidence
)
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer
from evidence_engine import EvidenceEngine
from product_web_checker import ProductWebChecker
from retailer_sources import search_all_retailers

class ProductSources:
    """
    Unified Product Web & Retail Intelligence Engine.
    Aggregates:
    - 🥗 Open Food Facts (Public API)
    - 🛒 Amazon India & Global
    - 🛍️ BigBasket Supermarket (India)
    - ⚡ Blinkit 10-Min Quick Commerce (India)
    - ⚡ Zepto Instant Grocery (India)
    - 🌐 General Web / Direct URL Checker
    - 🔢 Barcode Lookup & Product Name Search
    """

    OFF_BARCODE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

    def __init__(self, timeout: int = 7):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "SafeBite-Product-Intelligence/1.0 (https://github.com/Nikhitha-devireddy/safebite-ai; karthik@example.com)",
            "Accept": "application/json"
        }
        self.web_checker = ProductWebChecker(timeout=timeout)

    def route_and_fetch(
        self,
        raw_input: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru"
    ) -> Optional[Product]:
        """
        Main Input Router:
        Detects whether input is a URL, Barcode, or Product Search Query,
        then queries discovery sources, matches identity, extracts nutrition,
        cross-validates evidence, and evaluates clinical safety.
        """
        clean_in = raw_input.strip()
        user_allergies = user_allergies or []

        # 1. URL Route
        if clean_in.startswith("http://") or clean_in.startswith("https://"):
            return self.fetch_by_url(
                url=clean_in,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location
            )

        # 2. Barcode Route (8-14 digits)
        digits_only = re.sub(r"\D", "", clean_in)
        if len(digits_only) in (8, 12, 13, 14) and len(digits_only) == len(clean_in):
            prod = self.fetch_by_barcode(
                barcode=digits_only,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location
            )
            if prod:
                return prod

        # 3. Product Name / Query Route
        return self.fetch_by_query(
            query=clean_in,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies,
            location=location
        )

    def fetch_by_barcode(
        self,
        barcode: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru"
    ) -> Optional[Product]:
        """Fetches product by barcode from Open Food Facts and cross-checks retailers."""
        user_allergies = user_allergies or []
        req_url = self.OFF_BARCODE_URL.format(barcode=barcode)
        
        try:
            resp = requests.get(req_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1 and "product" in data:
                    p_data = data["product"]
                    return self._build_product_from_off(
                        p_data=p_data,
                        barcode=barcode,
                        user_medical_history=user_medical_history,
                        user_allergies=user_allergies,
                        location=location
                    )
        except Exception:
            pass

        return None

    def fetch_by_query(
        self,
        query: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru"
    ) -> Optional[Product]:
        """
        Discovers product via Open Food Facts search + Retailer Intelligence.
        """
        user_allergies = user_allergies or []
        
        # 1. Search Open Food Facts for authoritative nutrition and ingredients
        off_product = None
        try:
            params = {
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 3
            }
            resp = requests.get(self.OFF_SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                s_data = resp.json()
                products = s_data.get("products", [])
                if products:
                    off_product = products[0]
        except Exception:
            pass

        # 2. Search Retailers (Amazon, BigBasket, Blinkit, Zepto) for live offers
        retailer_offers = search_all_retailers(query=query, location=location)

        if off_product:
            return self._build_product_from_off(
                p_data=off_product,
                barcode=off_product.get("code"),
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location,
                existing_offers=retailer_offers
            )

        # If Open Food Facts lacked data, build from Retailer and Web intelligence
        if retailer_offers:
            first_offer = retailer_offers[0]
            raw_title = first_offer.product_name
            brand = ProductNormalizer.normalize_brand(raw_title.split("-")[0])
            variant = ProductNormalizer.extract_variant(raw_title)
            pack_size = ProductNormalizer.extract_pack_size(raw_title) or first_offer.pack_size
            prod_id = ProductNormalizer.generate_product_id(brand, query, variant, pack_size)

            # Nutrition and Ingredients remain strictly None / UNVERIFIED if not verified from packaging
            now_str = datetime.now(timezone.utc).isoformat()
            nutrition = NutritionFacts(
                source="Retailer Listings (Awaiting Lab Panel)",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str
            )
            ingredients = Ingredients(
                source="Retailer Listings",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str
            )
            allergens = Allergens(
                source="Retailer Listings",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str
            )

            sources_consulted = [o.retailer for o in retailer_offers]
            source_urls = [o.product_url for o in retailer_offers]
            evidence, _ = EvidenceEngine.cross_validate(
                nutrition=nutrition,
                ingredients=ingredients,
                allergens=allergens,
                retailer_offers=retailer_offers,
                sources_consulted=sources_consulted,
                source_urls=source_urls
            )

            product = Product(
                id=prod_id,
                name=query.title(),
                brand=brand,
                variant=variant,
                pack_size=pack_size,
                description=f"Catalog item discovered across {', '.join(sources_consulted)}.",
                nutrition=nutrition,
                ingredients=ingredients,
                allergens=allergens,
                retailer_offers=retailer_offers,
                evidence=evidence,
                health_safety_verdict="NOT VERIFIED",
                health_safety_reasons=[
                    "⚠️ Nutrition facts and full ingredients list could not be verified from official manufacturer or Open Food Facts.",
                    "Available on live retail platforms (see Retailer Availability section below)."
                ]
            )
            return product

        return None

    def fetch_by_url(
        self,
        url: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru"
    ) -> Optional[Product]:
        user_allergies = user_allergies or []

        # If Open Food Facts URL, route directly to verified barcode lookup
        off_barcode_match = re.search(r"openfoodfacts\.org/product/(\d+)", url)
        if off_barcode_match:
            barcode = off_barcode_match.group(1)
            off_prod = self.fetch_by_barcode(
                barcode=barcode,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location
            )
            if off_prod:
                return off_prod

        web_res = self.web_checker.inspect_url(url)
        
        if not web_res.get("success"):
            # Failed to fetch or blocked
            return None

        title = web_res.get("title") or "Verified Product"
        brand = web_res.get("brand") or "Manufacturer"
        variant = web_res.get("variant")
        pack_size = web_res.get("pack_size")
        prod_id = ProductNormalizer.generate_product_id(brand, title, variant, pack_size)

        nutrition = web_res.get("nutrition")
        ingredients = web_res.get("ingredients")
        allergens = web_res.get("allergens")

        # Create offer for this URL
        now_str = datetime.now(timezone.utc).isoformat()
        offer = RetailerOffer(
            retailer="Direct Web / Official Store",
            product_name=title,
            price=web_res.get("price"),
            currency=web_res.get("currency", "₹"),
            pack_size=pack_size,
            in_stock=True,
            product_url=url,
            availability_status="Available on Website",
            location=location,
            retrieved_at=now_str,
            confidence=SourceConfidence.HIGH if web_res.get("price") else SourceConfidence.MEDIUM
        )

        # Cross-search other retailers for this product title
        other_offers = search_all_retailers(query=f"{brand} {title}".strip()[:40], location=location)
        all_offers = [offer] + [o for o in other_offers if o.retailer != "Direct Web / Official Store"]

        sources_consulted = ["Direct Web Inspection"] + [o.retailer for o in all_offers if o.retailer != "Direct Web / Official Store"]
        source_urls = [url] + [o.product_url for o in all_offers]

        evidence, _ = EvidenceEngine.cross_validate(
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=all_offers,
            sources_consulted=sources_consulted,
            source_urls=source_urls
        )

        product = Product(
            id=prod_id,
            name=title,
            brand=brand,
            variant=variant,
            pack_size=pack_size,
            description=web_res.get("raw_text", "")[:300],
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=all_offers,
            evidence=evidence
        )

        verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
            product=product,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies
        )
        product.health_safety_verdict = verdict
        product.health_safety_reasons = reasons

        return product

    def _build_product_from_off(
        self,
        p_data: Dict[str, Any],
        barcode: Optional[str] = None,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        existing_offers: Optional[List[RetailerOffer]] = None
    ) -> Product:
        """Constructs canonical Product model from Open Food Facts data."""
        user_allergies = user_allergies or []
        name = p_data.get("product_name") or p_data.get("product_name_en") or "Nutrition Product"
        raw_brand = p_data.get("brands") or ""
        brand = ProductNormalizer.normalize_brand(raw_brand) if raw_brand else "Brand"
        
        variant = ProductNormalizer.extract_variant(name)
        pack_size = p_data.get("quantity") or ProductNormalizer.extract_pack_size(name)
        code = barcode or p_data.get("code")
        prod_id = ProductNormalizer.generate_product_id(brand, name, variant, pack_size, code)

        nutrition, ingredients, allergens = NutritionExtractor.extract_from_open_food_facts(
            p_data,
            url=f"https://world.openfoodfacts.org/product/{code}" if code else None
        )

        # Discover live retailer offers if not already supplied
        if existing_offers is None:
            retailer_offers = search_all_retailers(query=f"{brand} {name}".strip()[:40], location=location)
        else:
            retailer_offers = existing_offers

        sources_consulted = ["Open Food Facts Database"] + [o.retailer for o in retailer_offers]
        source_urls = [f"https://world.openfoodfacts.org/product/{code}"] if code else []
        source_urls.extend([o.product_url for o in retailer_offers])

        evidence, _ = EvidenceEngine.cross_validate(
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=retailer_offers,
            sources_consulted=sources_consulted,
            source_urls=source_urls
        )

        product = Product(
            id=prod_id,
            name=name,
            brand=brand,
            variant=variant,
            pack_size=pack_size,
            barcode=code,
            description=p_data.get("generic_name") or f"{brand} {name}",
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=retailer_offers,
            evidence=evidence
        )

        verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
            product=product,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies
        )
        product.health_safety_verdict = verdict
        product.health_safety_reasons = reasons

        return product
