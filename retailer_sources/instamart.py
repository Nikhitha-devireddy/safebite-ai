"""
SafeBite AI - Swiggy Instamart Retailer Adapter
Quick commerce intelligence for grocery and health snacks in supported urban locations.
Handles bot detection and access restrictions gracefully.
"""

import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup

from schemas import RetailerOffer, SourceConfidence
from retailer_sources.base import BaseRetailer

class InstamartRetailer(BaseRetailer):
    """
    Swiggy Instamart 10-15 Min Grocery Intelligence Source.
    """
    def __init__(self, enabled: bool = True):
        super().__init__(name="Swiggy Instamart", enabled=enabled)
        self.base_url = "https://www.swiggy.com/instamart"

    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        if not self.enabled:
            return []

        offers: List[RetailerOffer] = []
        encoded_query = urllib.parse.quote(query)
        search_url = f"{self.base_url}/search?custom_back=true&query={encoded_query}"
        direct_link = f"https://www.swiggy.com/instamart/search?query={encoded_query}"

        resp = self.safe_get(search_url)
        if resp and resp.text:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Look for product cards
                cards = soup.find_all("div", attrs={"data-testid": re.compile(r"item|product", re.I)})
                for card in cards[:3]:
                    name_elem = card.find(["h2", "h3", "div"], string=re.compile(query.split()[0], re.I))
                    title = name_elem.get_text(strip=True) if name_elem else query
                    
                    price_elem = card.find(string=re.compile(r"₹\s*\d+"))
                    price = None
                    if price_elem:
                        p_match = re.search(r"₹\s*(\d+(?:\.\d+)?)", price_elem)
                        if p_match:
                            price = float(p_match.group(1))

                    offers.append(self.create_offer(
                        product_name=title,
                        product_url=direct_link,
                        price=price,
                        currency="₹",
                        availability_status=f"Instant Delivery in {location or 'Metro Area'}",
                        location=location,
                        confidence=SourceConfidence.MEDIUM if price else SourceConfidence.LOW
                    ))
            except Exception:
                pass

        # If direct scraping was blocked or empty, return direct search deep-link offer
        if not offers:
            offers.append(self.create_offer(
                product_name=f"{query.title()} (Live Instamart Catalog)",
                product_url=direct_link,
                price=None,
                currency="₹",
                availability_status=f"Check Instamart app for {location or 'your location'}",
                location=location,
                confidence=SourceConfidence.LOW
            ))

        return offers

    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        if "swiggy.com/instamart" not in url:
            return None
        return self.create_offer(
            product_name="Instamart Product",
            product_url=url,
            availability_status="Available on Instamart",
            confidence=SourceConfidence.MEDIUM
        )
