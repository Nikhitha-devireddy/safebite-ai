"""
SafeBite AI - JioMart Grocery Retailer Adapter
Grocery and daily staples intelligence source across India.
Gracefully manages bot protection, redirects, and timeouts.
"""

import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup

from schemas import RetailerOffer, SourceConfidence
from retailer_sources.base import BaseRetailer

class JioMartRetailer(BaseRetailer):
    """
    JioMart Grocery & FMCG intelligence source.
    """
    def __init__(self, enabled: bool = True):
        super().__init__(name="JioMart", enabled=enabled)
        self.base_url = "https://www.jiomart.com"

    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        if not self.enabled:
            return []

        offers: List[RetailerOffer] = []
        encoded_query = urllib.parse.quote(query)
        search_url = f"{self.base_url}/search/{encoded_query}"
        direct_link = search_url

        resp = self.safe_get(search_url)
        if resp and resp.text:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.find_all("div", class_=re.compile(r"product-card|item", re.I))
                for item in items[:3]:
                    name_elem = item.find(["div", "span"], class_=re.compile(r"title|name", re.I))
                    title = name_elem.get_text(strip=True) if name_elem else query
                    
                    price_elem = item.find(string=re.compile(r"₹\s*\d+"))
                    price = None
                    if price_elem:
                        p_match = re.search(r"₹\s*(\d+(?:\.\d+)?)", price_elem)
                        if p_match:
                            price = float(p_match.group(1))

                    link_elem = item.find("a", href=True)
                    href = link_elem["href"] if link_elem else None
                    prod_url = f"{self.base_url}{href}" if href and href.startswith("/") else direct_link

                    offers.append(self.create_offer(
                        product_name=title,
                        product_url=prod_url,
                        price=price,
                        currency="₹",
                        availability_status=f"Available for delivery to {location or 'India'}",
                        location=location,
                        confidence=SourceConfidence.MEDIUM if price else SourceConfidence.LOW
                    ))
            except Exception:
                pass

        if not offers:
            offers.append(self.create_offer(
                product_name=f"{query.title()} on JioMart",
                product_url=direct_link,
                price=None,
                currency="₹",
                availability_status=f"Delivery coverage depends on pincode in {location or 'India'}",
                location=location,
                confidence=SourceConfidence.LOW
            ))

        return offers

    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        if "jiomart.com" not in url:
            return None
        return self.create_offer(
            product_name="JioMart Product",
            product_url=url,
            availability_status="Available on JioMart",
            confidence=SourceConfidence.MEDIUM
        )
