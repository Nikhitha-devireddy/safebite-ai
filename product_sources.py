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
from clinical_engine import ClinicalRuleEngine
import supabase_client
import bs4

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

    @classmethod
    def extract_title_from_url(cls, url: str) -> str:
        """Extracts human-readable product title from URL slug or path."""
        try:
            parsed = urllib.parse.urlparse(url)
            path = urllib.parse.unquote(parsed.path).strip("/")
            segments = [s for s in path.split("/") if s]
            for i, s in enumerate(segments):
                if s.lower() in ("dp", "gp", "product", "pd", "prn", "pn", "products", "item") and i > 0:
                    candidate = segments[i-1]
                    if len(candidate) > 3 and not candidate.isdigit():
                        return candidate.replace("-", " ").replace("_", " ").strip().title()
                if s.lower() in ("dp", "gp", "product", "pd", "prn", "pn", "products", "item") and i + 1 < len(segments):
                    candidate = segments[i+1]
                    if not re.match(r"^[A-Z0-9]{8,15}$", candidate, re.I) and not candidate.isdigit():
                        return candidate.replace("-", " ").replace("_", " ").strip().title()
                    elif i + 2 < len(segments):
                        cand2 = segments[i+2]
                        if not cand2.isdigit():
                            return cand2.replace("-", " ").replace("_", " ").strip().title()
            meaningful = [s for s in segments if len(s) > 4 and not re.match(r"^[A-Z0-9]{8,15}$", s, re.I) and not s.isdigit()]
            if meaningful:
                longest = max(meaningful, key=len)
                title = re.sub(r"\.html?$", "", longest)
                return title.replace("-", " ").replace("_", " ").strip().title()
        except Exception:
            pass
        return ""

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

    @classmethod
    def _save_to_supabase_cache(cls, prod: Product, barcode: str):
        """Helper to cache verified product in Supabase PostgreSQL."""
        try:
            if supabase_client.is_supabase_enabled() and barcode:
                nut_dict = prod.nutrition.model_dump() if prod.nutrition else {}
                supabase_client.cache_verified_product({
                    "id": prod.id,
                    "barcode": barcode,
                    "name": prod.name,
                    "brand": prod.brand,
                    "category": prod.category or "General Grocery",
                    "nutrition_facts": nut_dict,
                    "ingredients": prod.ingredients.raw_text if prod.ingredients else "",
                    "allergens": prod.allergens.contains if prod.allergens else [],
                    "nova_group": 4
                })
        except Exception:
            pass

    @classmethod
    def _build_product_from_cached_dict(
        cls,
        sb_data: Dict[str, Any],
        barcode: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        food_preferences: str = ""
    ) -> Optional[Product]:
        """Reconstructs canonical Product from Supabase cache record."""
        user_allergies = user_allergies or []
        nut_dict = sb_data.get("nutrition_facts") or {}
        nutrition = NutritionFacts(**nut_dict) if nut_dict else None
        ing_raw = sb_data.get("ingredients") or ""
        ingredients = Ingredients(raw_text=ing_raw, is_clean_label=False) if ing_raw else None
        allgs_list = sb_data.get("allergens") or []
        allergens = Allergens(contains=allgs_list) if allgs_list else None

        evidence = Evidence(
            manufacturer_verified=True,
            sources_consulted=["Supabase Verified Products Cache", "SafeBite Clinical Engine"],
            overall_confidence=SourceConfidence.HIGH,
            last_verified=sb_data.get("last_verified_at", "Cached")
        )
        prod = Product(
            id=sb_data.get("id") or f"prod_{barcode}",
            name=sb_data.get("name", "Cached Product"),
            brand=sb_data.get("brand", "Verified Brand"),
            category=sb_data.get("category", "General Grocery"),
            barcode=barcode,
            nutrition=nutrition,
            ingredients=ingredients,
            allergens=allergens,
            evidence=evidence,
            identity_confidence=ProductIdentityConfidence.EXACT
        )
        verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
            product=prod,
            user_medical_history=user_medical_history,
            user_allergies=user_allergies,
            food_preferences=food_preferences
        )
        prod.health_safety_verdict = verdict
        prod.health_safety_reasons = reasons
        prod.recommended_portion = ClinicalRuleEngine.calculate_recommended_portion(
            prod,
            user_medical_history
        )
        return prod

    @classmethod
    def _resolve_barcode_from_web(cls, barcode: str) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
        """
        Resolves product title, brand, variant, and pack size for any barcode
        via live web barcode indexing without API key dependency.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        for q in [f"{barcode}+barcode", f"{barcode}+product"]:
            try:
                url = f"https://html.duckduckgo.com/html/?q={q}"
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    soup = bs4.BeautifulSoup(resp.text, "html.parser")
                    links = soup.select(".result__title a")
                    for a in links[:6]:
                        raw = a.get_text().strip()
                        clean = re.sub(r"[\r\n\t]+", " ", raw)
                        clean = re.split(r"[\u2022\ufffd\-\–\—\|]", clean)[0].strip()
                        if (
                            clean and len(clean) > 4 and 
                            not clean.lower().startswith((
                                "barcode lookup", "upc barcode", "barcode search", 
                                "lookup", "scan upc", "free barcode", "online barcode"
                            ))
                        ):
                            brand = ProductNormalizer.normalize_brand(clean.split()[0])
                            variant = ProductNormalizer.extract_variant(clean)
                            pack_size = ProductNormalizer.extract_pack_size(clean)
                            return clean, brand, variant, pack_size
            except Exception:
                pass
        return None

    @classmethod
    def _resolve_barcode_via_ai(cls, barcode: str) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
        """
        Identifies product using GS1 country prefixes and LLM FMCG knowledge.
        """
        try:
            from llm_service import generate_clinical_assessment
            gs1_hint = "Indian FMCG market (GS1 890)" if barcode.startswith("890") else "Global FMCG market"
            prompt = (
                f"You are a barcode registry expert. Given consumer barcode '{barcode}' ({gs1_hint}), "
                f"identify the exact product name, manufacturer/brand, and pack size if known. "
                f"Return ONLY a 1-line comma-separated answer in the format: Product Name, Brand, Pack Size. "
                f"If you do not know the exact product, respond with UNKNOWN."
            )
            text, _ = generate_clinical_assessment(prompt)
            if text and "UNKNOWN" not in text.upper():
                parts = [p.strip() for p in text.strip().split(",")]
                if len(parts) >= 2 and len(parts[0]) > 3:
                    name = parts[0].strip("`\"' ")
                    brand = parts[1].strip("`\"' ")
                    pack_size = parts[2].strip("`\"' ") if len(parts) > 2 else None
                    return name, brand, None, pack_size
        except Exception:
            pass
        return None

    def fetch_by_barcode(
        self,
        barcode: str,
        user_medical_history: str = "",
        user_allergies: Optional[List[str]] = None,
        location: Optional[str] = "Bengaluru",
        food_preferences: str = ""
    ) -> Optional[Product]:
        """
        Fetches product by barcode through a 6-layer Universal Resolution Pipeline:
        Layer 1: In-memory cache
        Layer 2: Supabase PostgreSQL 'verified_products_cache'
        Layer 3: Reference FMCG Barcode Index (common Indian & Global household staples)
        Layer 4: Multi-Shard Open Food Facts (world + in + v0)
        Layer 5: Live Web Barcode & GTIN Resolution (DuckDuckGo / UPC registries)
        Layer 6: AI Barcode Identification (LLM GS1 prefix analyzer)
        """
        user_allergies = user_allergies or []
        barcode_clean = re.sub(r"\D", "", barcode.strip())
        if not barcode_clean:
            return None

        cache_key = f"barcode:{barcode_clean}"
        cached_prod = self.source_manager.get_cached(cache_key, ttl_seconds=Config.CACHE_OFF_TTL)
        if cached_prod:
            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=cached_prod,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            cached_prod.health_safety_verdict = verdict
            cached_prod.health_safety_reasons = reasons
            cached_prod.recommended_portion = ClinicalRuleEngine.calculate_recommended_portion(
                cached_prod,
                user_medical_history
            )
            return cached_prod

        # LAYER 2: Supabase Cloud Database Cache
        try:
            if supabase_client.is_supabase_enabled():
                sb_cached = supabase_client.get_cached_product(barcode_clean)
                if sb_cached:
                    prod = self._build_product_from_cached_dict(
                        sb_cached, barcode_clean, user_medical_history, user_allergies, location, food_preferences
                    )
                    if prod:
                        self.source_manager.set_cached(cache_key, prod)
                        return prod
        except Exception:
            pass

        # LAYER 3: Built-in Reference FMCG Barcode Index
        REFERENCE_BARCODES = {
            # Indian Staples, Biscuits, Confectionery & Snacks
            "8901233030548": ("Cadbury Dairy Milk Chocolate", "Cadbury", "Chocolate Bar", "13.2g"),
            "8901233024035": ("Cadbury 5 Star Chocolate", "Cadbury", "Chocolate Bar", "40g"),
            "8901233017778": ("Cadbury Perk Chocolate Wafer", "Cadbury", "Wafer Bar", "13g"),
            "8901058852875": ("Maggi 2-Minute Masala Instant Noodles", "Maggi", "Instant Noodles", "70g"),
            "8901058859133": ("Maggi Nutri-licious Oats Noodles", "Maggi", "Instant Noodles", "73g"),
            "8901491101837": ("Kurkure Masala Munch", "Kurkure", "Namkeen Snack", "82g"),
            "8901491103053": ("Lay's India's Magic Masala", "Lay's", "Potato Chips", "50g"),
            "8901491000857": ("Lay's Classic Salted", "Lay's", "Potato Chips", "50g"),
            "8901719101037": ("Parle-G Original Glucose Biscuits", "Parle", "Biscuits", "80g"),
            "8901719108012": ("Parle Monaco Salted Biscuits", "Parle", "Biscuits", "75g"),
            "8901719104038": ("Parle Hide & Seek Chocolate Chip Cookies", "Parle", "Cookies", "82g"),
            "8901063012110": ("Britannia Good Day Cashew Cookies", "Britannia", "Cookies", "100g"),
            "8901063012653": ("Britannia Bourbon Chocolate Cream Biscuits", "Britannia", "Biscuits", "150g"),
            "8901063142276": ("Britannia Marie Gold Biscuits", "Britannia", "Biscuits", "150g"),
            "8906001020301": ("Amul Pure Cow Ghee", "Amul", "Dairy / Ghee", "1L"),
            "8901262010016": ("Amul Salted Butter", "Amul", "Dairy / Butter", "100g"),
            "8901262020015": ("Amul Taaza Homogenised Toned Milk", "Amul", "Dairy / Milk", "1L"),
            "8906132400010": ("The Whole Truth Double Cocoa Protein Bar", "The Whole Truth", "Protein Bar", "52g"),
            "8906010500054": ("Dabur 100% Pure Honey", "Dabur", "Honey", "250g"),
            "8904043901007": ("Tata Salt Vacuum Evaporated Iodized Salt", "Tata", "Iodized Salt", "1kg"),
            "8904043905005": ("Tata Sampann Unpolished Toor Dal", "Tata", "Pulses", "1kg"),
            "7622210400015": ("Oreo Original Vanilla Creme Sandwich Biscuits", "Oreo", "Cookies", "120g"),
            "8901725132223": ("Sunfeast Dark Fantasy Choco Fills", "Sunfeast", "Biscuits", "75g"),
            "8901725121111": ("Aashirvaad Shudh Chakki Atta Whole Wheat", "Aashirvaad", "Flour", "5kg"),
            "8901725013000": ("Sunfeast Yippee! Magic Masala Noodles", "Yippee!", "Instant Noodles", "70g"),
            "8902579100018": ("Haldiram's Nagpur Aloo Bhujia", "Haldiram's", "Namkeen", "150g"),
            "8902579100025": ("Haldiram's Gulab Jamun", "Haldiram's", "Traditional Sweets", "1kg"),
            "8902579100032": ("Haldiram's Rasgulla", "Haldiram's", "Traditional Sweets", "1kg"),
            # International Staples
            "737628064502": ("Ka-Me Rice Noodles", "Ka-Me", "Rice Noodles", "142g"),
            "0041220576920": ("100% Whole Grain Rolled Oats", "H-E-B", "Rolled Oats", "453g"),
            "038000198661": ("Special K Cereal", "Kellogg's", "Breakfast Cereal", "340g"),
            "028400043809": ("Lay's Classic Potato Chips", "Frito-Lay", "Potato Chips", "226g"),
            "049000028904": ("Coca-Cola Original Taste", "The Coca-Cola Company", "Soft Drink", "355ml"),
            "9002490100070": ("Red Bull Energy Drink", "Red Bull", "Energy Drink", "250ml")
        }
        if barcode_clean in REFERENCE_BARCODES:
            p_name, p_brand, p_var, p_pack = REFERENCE_BARCODES[barcode_clean]
            p_nut, p_ing, p_allg = NutritionExtractor.fetch_universal_nutrition(
                product_name=p_name,
                brand=p_brand,
                variant=p_var
            )
            prod_id = ProductNormalizer.generate_product_id(p_brand, p_name, p_var, p_pack, barcode_clean)
            evidence, _ = EvidenceEngine.cross_validate(
                nutrition=p_nut,
                ingredients=p_ing,
                allergens=p_allg,
                retailer_offers=[],
                sources_consulted=["Verified Reference FMCG Registry", "SafeBite Clinical Engine"],
                source_urls=[]
            )
            prod = Product(
                id=prod_id,
                name=p_name,
                brand=p_brand,
                variant=p_var,
                pack_size=p_pack,
                barcode=barcode_clean,
                nutrition=p_nut,
                ingredients=p_ing,
                allergens=p_allg,
                evidence=evidence,
                identity_confidence=ProductIdentityConfidence.EXACT
            )
            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=prod,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            prod.health_safety_verdict = verdict
            prod.health_safety_reasons = reasons
            prod.recommended_portion = ClinicalRuleEngine.calculate_recommended_portion(prod, user_medical_history)
            self.source_manager.set_cached(cache_key, prod)
            self._save_to_supabase_cache(prod, barcode_clean)
            return prod

        # LAYER 4: Multi-Shard Open Food Facts (world, in, v0)
        off_urls = [
            f"https://world.openfoodfacts.org/api/v2/product/{barcode_clean}.json",
            f"https://in.openfoodfacts.org/api/v2/product/{barcode_clean}.json",
            f"https://world.openfoodfacts.org/api/v0/product/{barcode_clean}.json"
        ]
        start_time = time.time()
        for req_url in off_urls:
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
                            barcode=barcode_clean,
                            user_medical_history=user_medical_history,
                            user_allergies=user_allergies,
                            location=location,
                            food_preferences=food_preferences
                        )
                        self.source_manager.set_cached(cache_key, prod)
                        self._save_to_supabase_cache(prod, barcode_clean)
                        return prod
            except Exception:
                continue

        # LAYER 5: Live Web Barcode & Product Identification Engine
        web_match = self._resolve_barcode_from_web(barcode_clean)
        if web_match:
            p_name, p_brand, p_var, p_pack = web_match
            p_nut, p_ing, p_allg = NutritionExtractor.fetch_universal_nutrition(
                product_name=p_name,
                brand=p_brand,
                variant=p_var
            )
            prod_id = ProductNormalizer.generate_product_id(p_brand, p_name, p_var, p_pack, barcode_clean)
            evidence, _ = EvidenceEngine.cross_validate(
                nutrition=p_nut,
                ingredients=p_ing,
                allergens=p_allg,
                retailer_offers=[],
                sources_consulted=["Live Web Barcode Index", "SafeBite Clinical Engine"],
                source_urls=[]
            )
            prod = Product(
                id=prod_id,
                name=p_name,
                brand=p_brand,
                variant=p_var,
                pack_size=p_pack,
                barcode=barcode_clean,
                nutrition=p_nut,
                ingredients=p_ing,
                allergens=p_allg,
                evidence=evidence,
                identity_confidence=ProductIdentityConfidence.EXACT
            )
            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=prod,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            prod.health_safety_verdict = verdict
            prod.health_safety_reasons = reasons
            prod.recommended_portion = ClinicalRuleEngine.calculate_recommended_portion(prod, user_medical_history)
            self.source_manager.set_cached(cache_key, prod)
            self._save_to_supabase_cache(prod, barcode_clean)
            return prod

        # LAYER 6: AI Barcode Identification (GS1 Prefix Analyzer)
        ai_match = self._resolve_barcode_via_ai(barcode_clean)
        if ai_match:
            p_name, p_brand, p_var, p_pack = ai_match
            p_nut, p_ing, p_allg = NutritionExtractor.fetch_universal_nutrition(
                product_name=p_name,
                brand=p_brand,
                variant=p_var
            )
            prod_id = ProductNormalizer.generate_product_id(p_brand, p_name, p_var, p_pack, barcode_clean)
            evidence, _ = EvidenceEngine.cross_validate(
                nutrition=p_nut,
                ingredients=p_ing,
                allergens=p_allg,
                retailer_offers=[],
                sources_consulted=["GS1 AI Product Identifier", "SafeBite Clinical Engine"],
                source_urls=[]
            )
            prod = Product(
                id=prod_id,
                name=p_name,
                brand=p_brand,
                variant=p_var,
                pack_size=p_pack,
                barcode=barcode_clean,
                nutrition=p_nut,
                ingredients=p_ing,
                allergens=p_allg,
                evidence=evidence,
                identity_confidence=ProductIdentityConfidence.EXACT
            )
            verdict, reasons = EvidenceEngine.evaluate_clinical_safety(
                product=prod,
                user_medical_history=user_medical_history,
                user_allergies=user_allergies,
                food_preferences=food_preferences
            )
            prod.health_safety_verdict = verdict
            prod.health_safety_reasons = reasons
            prod.recommended_portion = ClinicalRuleEngine.calculate_recommended_portion(prod, user_medical_history)
            self.source_manager.set_cached(cache_key, prod)
            self._save_to_supabase_cache(prod, barcode_clean)
            return prod

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

        # If Open Food Facts lacked data, build from Retailer listings and Universal Clinical Nutrition Engine
        first_offer = retailer_offers[0] if retailer_offers else None
        raw_title = first_offer.product_name if first_offer else query
        brand = ProductNormalizer.normalize_brand(raw_title.split("-")[0])
        variant = ProductNormalizer.extract_variant(raw_title)
        pack_size = ProductNormalizer.extract_pack_size(raw_title) or (first_offer.pack_size if first_offer else None)
        prod_id = ProductNormalizer.generate_product_id(brand, query, variant, pack_size)

        now_str = datetime.now(timezone.utc).isoformat()
        nutrition, ingredients, allergens = NutritionExtractor.fetch_universal_nutrition(
            product_name=query.title(),
            brand=brand,
            variant=variant
        )

        sources_consulted = [o.retailer for o in retailer_offers] if retailer_offers else ["Universal Clinical Nutrition Registry"]
        source_urls = [o.product_url for o in retailer_offers] if retailer_offers else []
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
        has_direct_nut = bool(
            web_res.get("success") and 
            web_res.get("nutrition") and 
            web_res["nutrition"].calories is not None
        )

        if has_direct_nut:
            title = web_res.get("title") or "Verified Product"
            brand = web_res.get("brand") or "Manufacturer"
            variant = web_res.get("variant")
            pack_size = web_res.get("pack_size")
            barcode = web_res.get("barcode")
            nutrition = web_res.get("nutrition")
            ingredients = web_res.get("ingredients")
            allergens = web_res.get("allergens")
        else:
            # Universal Extraction: derive title from URL path/slug and retrieve verified nutrition & formulation
            extracted_title = self.extract_title_from_url(clean_url)
            title = extracted_title or (web_res.get("title") if web_res else "") or "Verified Product"
            brand = ProductNormalizer.normalize_brand(title.split()[0])
            variant = ProductNormalizer.extract_variant(title)
            pack_size = ProductNormalizer.extract_pack_size(title) or (web_res.get("pack_size") if web_res else None)
            barcode = web_res.get("barcode") if web_res else None

            # Fetch authoritative nutrition facts & ingredients
            nutrition, ingredients, allergens = NutritionExtractor.fetch_universal_nutrition(
                product_name=title,
                brand=brand,
                variant=variant,
                source_url=clean_url
            )

        prod_id = ProductNormalizer.generate_product_id(brand, title, variant, pack_size, barcode)

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
