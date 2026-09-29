"""
SafeBite AI - Product URL Inspector & Web Intelligence
Scrapes and parses product landing pages respectfully.
Extraction priority:
1. JSON-LD structured product schema (schema.org/Product, schema.org/NutritionInformation)
2. Semantic HTML nutrition tables and ingredient containers
3. Open Graph and meta property tags
4. Visible text extraction with regex fallbacks
Never crashes on bot protections (HTTP 403/429) or malformed HTML.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup
import requests

from schemas import NutritionFacts, Ingredients, Allergens, RetailerOffer, SourceConfidence, RetrievalResult
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer
from config import Config

logger = logging.getLogger(__name__)

class ProductWebChecker:
    """
    Direct URL and Web Intelligence Inspector.
    Scrapes product URLs respectfully, extracting structured metadata,
    nutrition tables, ingredient declarations, and barcodes.
    """

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or Config.HTTP_READ_TIMEOUT
        self.headers = {
            "User-Agent": Config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def inspect_url(self, url: str) -> Dict[str, Any]:
        """
        Audits a web URL for product specifications, nutrition, ingredients, and pricing.
        Returns a dictionary with product metadata, nutrition, ingredients, allergens, and raw offer.
        """
        clean_url = url.strip()
        now_str = datetime.now(timezone.utc).isoformat()

        result = {
            "success": False,
            "url": clean_url,
            "title": "",
            "brand": "",
            "variant": None,
            "pack_size": None,
            "barcode": None,
            "price": None,
            "currency": "₹",
            "nutrition": None,
            "ingredients": None,
            "allergens": None,
            "raw_text": "",
            "source_type": "Official Product Page",
            "error_reason": None,
            "retrieval_result": None
        }

        try:
            resp = requests.get(clean_url, headers=self.headers, timeout=self.timeout)
            
            if resp.status_code == 403:
                result["error_reason"] = "This website blocked automated access (HTTP 403 bot protection)."
                result["retrieval_result"] = RetrievalResult(
                    success=False, status_code=403, source="Direct Web", url=clean_url,
                    error_type="BLOCKED_403", error_message="Source blocked automated access."
                )
                return result

            if resp.status_code == 429:
                result["error_reason"] = "This website is rate-limited (HTTP 429)."
                result["retrieval_result"] = RetrievalResult(
                    success=False, status_code=429, source="Direct Web", url=clean_url,
                    error_type="RATE_LIMITED_429", error_message="Source rate-limited."
                )
                return result

            if resp.status_code != 200:
                result["error_reason"] = f"HTTP {resp.status_code} encountered."
                result["retrieval_result"] = RetrievalResult(
                    success=False, status_code=resp.status_code, source="Direct Web", url=clean_url,
                    error_type="HTTP_ERROR", error_message=f"HTTP {resp.status_code}"
                )
                return result

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 1. PRIORITY 1: JSON-LD (schema.org/Product)
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            # Handle @graph wrapper
                            sub_items = item.get("@graph", [item]) if "@graph" in item else [item]
                            for sub in sub_items:
                                if sub.get("@type") in ("Product", "IndividualProduct"):
                                    if "name" in sub and not result["title"]:
                                        result["title"] = sub["name"]
                                    if "brand" in sub and not result["brand"]:
                                        b_val = sub["brand"]
                                        result["brand"] = b_val.get("name") if isinstance(b_val, dict) else str(b_val)
                                    if "gtin13" in sub or "gtin8" in sub or "barcode" in sub:
                                        result["barcode"] = sub.get("gtin13") or sub.get("gtin8") or sub.get("barcode")
                                    if "offers" in sub:
                                        offers = sub["offers"]
                                        if isinstance(offers, list) and offers:
                                            offers = offers[0]
                                        if isinstance(offers, dict) and "price" in offers:
                                            try:
                                                result["price"] = float(offers["price"])
                                                result["currency"] = offers.get("priceCurrency", "₹")
                                            except (ValueError, TypeError):
                                                pass
                                    # Check for embedded nutrition
                                    if "nutrition" in sub and isinstance(sub["nutrition"], dict):
                                        n_data = sub["nutrition"]
                                        cal = None
                                        if "calories" in n_data:
                                            m = re.search(r"(\d+(?:\.\d+)?)", str(n_data["calories"]))
                                            cal = float(m.group(1)) if m else None
                                        
                                        def parse_g(field_val: Any) -> Optional[float]:
                                            if field_val:
                                                m = re.search(r"(\d+(?:\.\d+)?)", str(field_val))
                                                return float(m.group(1)) if m else None
                                            return None

                                        result["nutrition"] = NutritionFacts(
                                            serving_size=n_data.get("servingSize"),
                                            calories=cal,
                                            sugar_g=parse_g(n_data.get("sugarContent")),
                                            carbs_g=parse_g(n_data.get("carbohydrateContent")),
                                            protein_g=parse_g(n_data.get("proteinContent")),
                                            fat_g=parse_g(n_data.get("fatContent")),
                                            saturated_fat_g=parse_g(n_data.get("saturatedFatContent")),
                                            fiber_g=parse_g(n_data.get("fiberContent")),
                                            sodium_mg=parse_g(n_data.get("sodiumContent")),
                                            source="JSON-LD Schema.org Panel",
                                            source_url=clean_url,
                                            confidence=SourceConfidence.HIGH,
                                            retrieved_at=now_str
                                        )
                                    break
                except Exception:
                    pass

            # 2. PRIORITY 2: Open Graph & Meta Tags
            if not result["title"]:
                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    result["title"] = og_title["content"].strip()
                elif soup.title:
                    result["title"] = soup.title.get_text(strip=True)

            # Clean Page Text for parsing
            for el in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"]):
                el.decompose()

            raw_text = soup.get_text(separator=" ", strip=True)
            result["raw_text"] = raw_text[:5000]

            # 3. PRIORITY 3: Semantic HTML Extractors for Ingredients & Nutrition
            # Extract ingredients section specifically
            ing_text = ""
            ing_containers = soup.find_all(attrs={"class": re.compile(r"ingredient|composition", re.I)})
            if ing_containers:
                ing_text = " ".join([c.get_text(strip=True) for c in ing_containers])
            elif "ingredients" in raw_text.lower():
                m = re.search(r"ingredients?\s*[:\-]\s*([^\.\n\r]{10,400})", raw_text, re.I)
                if m:
                    ing_text = m.group(1).strip()

            # Parse nutrition & ingredients via deterministic extractor
            text_nut, text_ing, text_allg = NutritionExtractor.extract_from_text(
                raw_text,
                source_name=f"Official Web Page ({clean_url[:40]}...)",
                source_url=clean_url
            )

            if not result["nutrition"]:
                result["nutrition"] = text_nut

            if ing_text and not text_ing.raw_text:
                result["ingredients"] = Ingredients(
                    raw_text=ing_text,
                    ingredient_list=[i.strip() for i in re.split(r"[,;]+", ing_text) if i.strip()],
                    source="Product Web Page",
                    source_url=clean_url,
                    confidence=SourceConfidence.MEDIUM,
                    retrieved_at=now_str
                )
            else:
                result["ingredients"] = text_ing

            result["allergens"] = text_allg

            # Extract variant & pack size
            result["variant"] = ProductNormalizer.extract_variant(result["title"])
            result["pack_size"] = ProductNormalizer.extract_pack_size(result["title"])
            if not result["brand"] and result["title"]:
                result["brand"] = ProductNormalizer.normalize_brand(result["title"].split()[0])

            result["success"] = bool(result["title"])
            result["retrieval_result"] = RetrievalResult(
                success=True,
                status_code=200,
                source="Direct Web",
                url=clean_url,
                confidence=SourceConfidence.HIGH if result["nutrition"] and result["nutrition"].calories else SourceConfidence.MEDIUM,
                retrieved_at=now_str
            )
            return result

        except Exception as e:
            logger.info(f"Failed to inspect URL {clean_url}: {e}")
            result["error_reason"] = f"Failed to retrieve webpage: {str(e)}"
            result["retrieval_result"] = RetrievalResult(
                success=False,
                source="Direct Web",
                url=clean_url,
                error_type="EXCEPTION",
                error_message=str(e),
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str
            )
            return result
