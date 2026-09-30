"""
SafeBite AI - Unified Product Intelligence & Multi-Source Engine
Coordinates:
- 🥗 Open Food Facts (Public Collaborative Database with caching)
- 🛒 Multi-Retailer Live Offers (Amazon, BigBasket, Blinkit, Zepto, Instamart, Flipkart, JioMart)
- 🌐 Direct URL Inspector with JSON-LD & HTML tables
- 🔢 Barcode & GTIN Lookup
- 🎯 Identity Matching (Prevents merging conflicting variants)
- 🛡️ Deterministic Clinical Safety Assessment
"""

import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from schemas import (
    Product, NutritionFacts, Ingredients, Allergens,
    RetailerOffer, Evidence, SourceConfidence, ProductIdentityConfidence
)
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer
from product_identity import ProductIdentityMatcher
from evidence_engine import EvidenceEngine
from product_web_checker import ProductWebChecker
from retailer_sources import search_all_retailers
from source_manager import SourceManager
from config import Config

class ProductSources:
    """
    Unified Product Web & Retail Intelligence Engine.
    Aggregates authoritative databases and live retail platforms in parallel.
    """

    OFF_BARCODE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or Config.OFF_API_TIMEOUT
        self.headers = {
            "User-Agent": Config.USER_AGENT,
            "Accept": "application/json"
        }
        self.web_checker = ProductWebChecker(timeout=self.timeout)
        self.source_manager = SourceManager()

    def route_and_fetch(
        self,
        raw_input: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        food_preferences: str = ""
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
        if clean_in.startswith("http://") or clean_in.startswith("https://") or any(clean_in.lower().startswith(d) for d in ["www.", "world.openfoodfacts.org", "amazon.", "bigbasket.", "blinkit.", "zepto."]):
            return self.fetch_by_url(
                url=clean_in,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location,
                food_preferences=food_preferences
            )

        # 2. Barcode Route (8-14 digits, allowing spaces and hyphens)
        digits_only = re.sub(r"[\s\-]", "", clean_in)
        if digits_only.isdigit() and len(digits_only) in (8, 12, 13, 14):
            prod = self.fetch_by_barcode(
                barcode=digits_only,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location,
                food_preferences=food_preferences
            )
            if prod:
                return prod

        # 3. Product Name / Query Route
        return self.fetch_by_query(
            query=clean_in,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies,
            location=location,
            food_preferences=food_preferences
        )

    def fetch_by_barcode(
        self,
        barcode: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        food_preferences: str = ""
    ) -> Optional[Product]:
        """Fetches product by barcode from Open Food Facts and cross-checks retailers."""
        user_allergies = user_allergies or []
        barcode_clean = re.sub(r"\D", "", barcode.strip())
        if not barcode_clean:
            return None
        cache_key = f"barcode:{barcode_clean}"
        cached_prod = self.source_manager.get_cached(cache_key, ttl_seconds=Config.CACHE_OFF_TTL)
        if cached_prod:
            # Re-evaluate clinical safety with current user profile
            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=cached_prod,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            cached_prod.health_safety_verdict = verdict
            cached_prod.health_safety_reasons = reasons
            return cached_prod

        req_url = self.OFF_BARCODE_URL.format(barcode=barcode)
        start_time = time.time()
        
        try:
            resp = requests.get(req_url, headers=self.headers, timeout=self.timeout)
            dur = round((time.time() - start_time) * 1000, 1)
            self.source_manager.record_telemetry("Open Food Facts (Barcode)", dur, resp.status_code == 200, resp.status_code)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1 and "product" in data:
                    p_data = data["product"]
                    prod = self._build_product_from_off(
                        p_data=p_data,
                        barcode=barcode,
                        user_medical_history=user_medical_history,
                        user_allergies=user_allergies,
                        location=location,
                        food_preferences=food_preferences
                    )
                    self.source_manager.set_cached(cache_key, prod)
                    return prod
        except Exception as e:
            dur = round((time.time() - start_time) * 1000, 1)
            self.source_manager.record_telemetry("Open Food Facts (Barcode)", dur, False, None)

        return None

    def fetch_by_query(
        self,
        query: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        food_preferences: str = ""
    ) -> Optional[Product]:
        """
        Discovers product via Open Food Facts search + Retailer Intelligence concurrently.
        Uses ThreadPoolExecutor to run independent operations simultaneously in 2-3 seconds.
        """
        user_allergies = user_allergies or []
        cache_key = f"query:{query.lower().strip()}:{location}"
        cached = self.source_manager.get_cached(cache_key, ttl_seconds=Config.CACHE_QUERY_TTL)
        if cached:
            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=cached,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            cached.health_safety_verdict = verdict
            cached.health_safety_reasons = reasons
            return cached

        off_product = None
        retailer_offers: List[RetailerOffer] = []

        # Worker 1: Open Food Facts Search
        def _fetch_off() -> Optional[Dict[str, Any]]:
            start_t = time.time()
            try:
                params = {
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": 3
                }
                resp = requests.get(self.OFF_SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
                dur = round((time.time() - start_t) * 1000, 1)
                self.source_manager.record_telemetry("Open Food Facts (Search)", dur, resp.status_code == 200, resp.status_code)
                if resp.status_code == 200:
                    s_data = resp.json()
                    products = s_data.get("products", [])
                    if products:
                        return products[0]
            except Exception:
                dur = round((time.time() - start_t) * 1000, 1)
                self.source_manager.record_telemetry("Open Food Facts (Search)", dur, False, None)
            return None

        # Worker 2: Retailers Search
        def _fetch_retailers() -> List[RetailerOffer]:
            return search_all_retailers(query=query, location=location)

        # Execute parallel retrieval
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_off = executor.submit(_fetch_off)
            fut_ret = executor.submit(_fetch_retailers)
            
            try:
                off_product = fut_off.result(timeout=Config.OFF_API_TIMEOUT + 1.0)
            except Exception:
                off_product = None

            try:
                retailer_offers = fut_ret.result(timeout=Config.RETAILER_TIMEOUT + 1.0)
            except Exception:
                retailer_offers = []

        if off_product:
            prod = self._build_product_from_off(
                p_data=off_product,
                barcode=off_product.get("code"),
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location,
                existing_offers=retailer_offers,
                food_preferences=food_preferences
            )
            self.source_manager.set_cached(cache_key, prod)
            return prod

        # If Open Food Facts lacked data, build from Retailer listings with strict UNVERIFIED label
        if retailer_offers:
            first_offer = retailer_offers[0]
            raw_title = first_offer.product_name
            brand = ProductNormalizer.normalize_brand(raw_title.split("-")[0])
            variant = ProductNormalizer.extract_variant(raw_title)
            pack_size = ProductNormalizer.extract_pack_size(raw_title) or first_offer.pack_size
            prod_id = ProductNormalizer.generate_product_id(brand, query, variant, pack_size)

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
                identity_confidence=ProductIdentityConfidence.HIGH
            )

            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=product,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            product.health_safety_verdict = verdict
            product.health_safety_reasons = reasons

            self.source_manager.set_cached(cache_key, product)
            return product

        return None

    def fetch_by_url(
        self,
        url: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        food_preferences: str = ""
    ) -> Optional[Product]:
        user_allergies = user_allergies or []
        clean_url = url.strip()
        if clean_url and not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        # If Open Food Facts URL, route directly to verified barcode lookup
        off_barcode_match = re.search(r"openfoodfacts\.org/product/(\d+)", clean_url)
        if off_barcode_match:
            barcode = off_barcode_match.group(1)
            off_prod = self.fetch_by_barcode(
                barcode=barcode,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                location=location,
                food_preferences=food_preferences
            )
            if off_prod:
                return off_prod

        web_res = self.web_checker.inspect_url(clean_url)
        if not web_res.get("success"):
            return None

        title = web_res.get("title") or "Verified Product"
        brand = web_res.get("brand") or "Manufacturer"
        variant = web_res.get("variant")
        pack_size = web_res.get("pack_size")
        barcode = web_res.get("barcode")
        prod_id = ProductNormalizer.generate_product_id(brand, title, variant, pack_size, barcode)

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
            product_url=clean_url,
            availability_status="Available on Website",
            location=location,
            retrieved_at=now_str,
            confidence=SourceConfidence.HIGH if web_res.get("price") else SourceConfidence.MEDIUM
        )

        # Cross-search other retailers for this product title
        other_offers = search_all_retailers(query=f"{brand} {title}".strip()[:40], location=location)
        
        # Verify identity before attaching external offers
        verified_offers = [offer]
        for ext_off in other_offers:
            if ext_off.retailer == "Direct Web / Official Store":
                continue
            id_conf, _ = ProductIdentityMatcher.evaluate_match(
                target_name=title,
                candidate_name=ext_off.product_name,
                target_brand=brand,
                target_pack=pack_size
            )
            if ProductIdentityMatcher.can_merge_clinical_evidence(id_conf):
                verified_offers.append(ext_off)

        sources_consulted = ["Direct Web Inspection"] + [o.retailer for o in verified_offers if o.retailer != "Direct Web / Official Store"]
        source_urls = [clean_url] + [o.product_url for o in verified_offers]

        evidence, _ = EvidenceEngine.cross_validate(
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=verified_offers,
            sources_consulted=sources_consulted,
            source_urls=source_urls
        )

        product = Product(
            id=prod_id,
            name=title,
            brand=brand,
            variant=variant,
            pack_size=pack_size,
            barcode=barcode,
            description=web_res.get("raw_text", "")[:300],
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=verified_offers,
            evidence=evidence,
            identity_confidence=ProductIdentityConfidence.HIGH
        )

        verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
            product=product,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies,
            food_preferences=food_preferences
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
        existing_offers: Optional[List[RetailerOffer]] = None,
        food_preferences: str = ""
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
        raw_offers = existing_offers if existing_offers is not None else search_all_retailers(query=f"{brand} {name}".strip()[:40], location=location)

        # Filter out retailer offers that are conflicting variants
        verified_offers: List[RetailerOffer] = []
        for off in raw_offers:
            id_conf, _ = ProductIdentityMatcher.evaluate_match(
                target_name=name,
                candidate_name=off.product_name,
                target_brand=brand,
                target_pack=pack_size
            )
            if ProductIdentityMatcher.can_merge_clinical_evidence(id_conf):
                verified_offers.append(off)

        sources_consulted = ["Open Food Facts Database"] + [o.retailer for o in verified_offers]
        source_urls = [f"https://world.openfoodfacts.org/product/{code}"] if code else []
        source_urls.extend([o.product_url for o in verified_offers])

        evidence, _ = EvidenceEngine.cross_validate(
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=verified_offers,
            sources_consulted=sources_consulted,
            source_urls=source_urls
        )

        # Extract image URL if available
        image_url = p_data.get("image_front_url") or p_data.get("image_url")

        product = Product(
            id=prod_id,
            name=name,
            brand=brand,
            variant=variant,
            pack_size=pack_size,
            barcode=code,
            description=p_data.get("generic_name") or f"{brand} {name}",
            image_url=image_url,
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            retailer_offers=verified_offers,
            evidence=evidence,
            identity_confidence=ProductIdentityConfidence.EXACT if code else ProductIdentityConfidence.HIGH
        )

        verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
            product=product,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies,
            food_preferences=food_preferences
        )
        product.health_safety_verdict = verdict
        product.health_safety_reasons = reasons

        return product
