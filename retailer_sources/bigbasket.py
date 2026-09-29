import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup

from schemas import RetailerOffer, SourceConfidence
from retailer_sources.base import BaseRetailer

class BigBasketRetailer(BaseRetailer):
    """
    BigBasket Supermarket Grocery Intelligence Source (India).
    Handles Bengaluru and Indian metro delivery availability.
    """
    def __init__(self, enabled: bool = True):
        super().__init__(name="BigBasket", enabled=enabled)
        self.base_url = "https://www.bigbasket.com"

    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        if not self.enabled:
            return []

        offers: List[RetailerOffer] = []
        encoded = urllib.parse.quote(query)
        search_url = f"{self.base_url}/ps/?q={encoded}"
        direct_link = f"https://duckduckgo.com/?q={urllib.parse.quote(f'!ducky site:bigbasket.com {query}')}"

        resp = self.safe_get(search_url)
        if resp and resp.text and "Just a moment..." not in resp.text:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Look for product cards / JSON script tags in BigBasket HTML
                script_tag = soup.find("script", id="__NEXT_DATA__")
                if script_tag and script_tag.string:
                    import json
                    data = json.loads(script_tag.string)
                    # Traverse products in Next.js state if present
                    prods = data.get("props", {}).get("pageProps", {}).get("productSearch", {}).get("products", [])
                    for p in prods[:4]:
                        p_name = p.get("desc") or p.get("p_desc") or query
                        p_price = p.get("sp") or p.get("pricing", {}).get("discount", {}).get("prim_price", {}).get("sp")
                        p_weight = p.get("w") or p.get("pack_desc")
                        p_slug = p.get("slug")
                        p_url = f"{self.base_url}/pd/{p.get('id')}/{p_slug}" if p_slug else search_url
                        
                        offers.append(
                            self.create_offer(
                                product_name=p_name,
                                product_url=p_url,
                                price=float(p_price) if p_price else None,
                                pack_size=p_weight,
                                in_stock=not p.get("out_of_stock", False),
                                availability_status=f"Available for Delivery in {location or 'Bengaluru'}",
                                location=location,
                                confidence=SourceConfidence.HIGH if p_price else SourceConfidence.MEDIUM
                            )
                        )
            except Exception:
                pass

        if not offers:
            # Respectful fallback offer
            offers.append(
                self.create_offer(
                    product_name=f"{query} (BigBasket Grocery)",
                    product_url=direct_link,
                    price=None,
                    pack_size=None,
                    in_stock=True,
                    availability_status=f"Available on BigBasket Supermarket ({location or 'Bengaluru / Metro Hub'})",
                    location=location,
                    confidence=SourceConfidence.MEDIUM
                )
            )

        return offers

    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        if "bigbasket" not in url.lower():
            return None
        return self.create_offer(
            product_name="BigBasket Product",
            product_url=url,
            price=None,
            in_stock=True,
            availability_status="Available on BigBasket",
            confidence=SourceConfidence.MEDIUM
        )
