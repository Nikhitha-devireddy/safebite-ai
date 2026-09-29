import re
import json
import logging
from typing import Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup
import requests

from schemas import NutritionFacts, Ingredients, Allergens, RetailerOffer, SourceConfidence
from nutrition_extractor import NutritionExtractor
from product_normalizer import ProductNormalizer

logger = logging.getLogger(__name__)

class ProductWebChecker:
    """
    Direct URL and Web Intelligence Inspector.
    Scrapes product URLs respectfully, parsing OpenGraph, JSON-LD schema.org/Product,
    and HTML nutrition/ingredient panels.
    Falls back gracefully when bot protection or empty text is encountered.
    """

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "SafeBite-Web-Intelligence/1.0 (+https://github.com/Nikhitha-devireddy/safebite-ai)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def inspect_url(self, url: str) -> Dict[str, Any]:
        """
        Audits a web URL for product specifications, nutrition, ingredients, and pricing.
        Returns a dictionary with success, product metadata, nutrition, ingredients, allergens, and raw offer.
        """
        clean_url = url.strip()
        result = {
            "success": False,
            "url": clean_url,
            "title": "",
            "brand": "",
            "variant": None,
            "pack_size": None,
            "price": None,
            "currency": "₹",
            "nutrition": None,
            "ingredients": None,
            "allergens": None,
            "raw_text": "",
            "source_type": "Web Source",
            "error_reason": None
        }

        try:
            resp = requests.get(clean_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code in (403, 429, 503):
                result["error_reason"] = f"Site protected or rate-limited (HTTP {resp.status_code}). Respecting access controls without bypassing."
                return result

            if resp.status_code != 200:
                result["error_reason"] = f"HTTP {resp.status_code} encountered."
                return result

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 1. Extract Title
            title = ""
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            elif soup.title:
                title = soup.title.get_text(strip=True)
            result["title"] = title

            # 2. Extract JSON-LD (schema.org/Product)
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") in ("Product", "IndividualProduct"):
                            if "name" in item and not result["title"]:
                                result["title"] = item["name"]
                            if "brand" in item:
                                b_val = item["brand"]
                                result["brand"] = b_val.get("name") if isinstance(b_val, dict) else str(b_val)
                            if "offers" in item:
                                offers = item["offers"]
                                if isinstance(offers, list) and offers:
                                    offers = offers[0]
                                if isinstance(offers, dict) and "price" in offers:
                                    try:
                                        result["price"] = float(offers["price"])
                                    except (ValueError, TypeError):
                                        pass
                            break
                except Exception:
                    pass

            # 3. Brand Fallback
            if not result["brand"]:
                og_site_name = soup.find("meta", property="og:site_name")
                if og_site_name and og_site_name.get("content"):
                    result["brand"] = og_site_name["content"].strip()
                else:
                    # Extract from domain or title
                    result["brand"] = ProductNormalizer.normalize_brand(title.split("-")[0].split("|")[0])

            # 4. Pack size and Variant
            result["pack_size"] = ProductNormalizer.extract_pack_size(title)
            result["variant"] = ProductNormalizer.extract_variant(title)

            # 5. Extract Text for Nutrition and Ingredients
            # Remove scripts, styles, navs
            for elem in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                elem.extract()
            page_text = soup.get_text(separator="\n", strip=True)
            result["raw_text"] = page_text[:8000]

            nutrition, ingredients, allergens = NutritionExtractor.extract_from_text(
                page_text,
                source_name=f"Web URL ({result['brand'] or 'Direct Site'})",
                source_url=clean_url
            )
            result["nutrition"] = nutrition
            result["ingredients"] = ingredients
            result["allergens"] = allergens
            result["success"] = True

        except requests.Timeout:
            result["error_reason"] = "Connection timed out while fetching product URL."
        except Exception as e:
            result["error_reason"] = f"Failed to parse product URL: {str(e)}"

        return result
