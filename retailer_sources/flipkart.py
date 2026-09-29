"""
SafeBite AI - Flipkart Grocery & Supermart Retailer Adapter
E-commerce grocery intelligence source across India.
Handles bot challenges and redirects gracefully.
"""

import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup

from schemas import RetailerOffer, SourceConfidence
from retailer_sources.base import BaseRetailer

class FlipkartRetailer(BaseRetailer):
    """
    Flipkart Grocery & Supermart intelligence source.
    """
    def __init__(self, enabled: bool = True):
        super().__init__(name="Flipkart Grocery", enabled=enabled)
        self.base_url = "https://www.flipkart.com"

    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        if not self.enabled:
            return []

        offers: List[RetailerOffer] = []
        encoded_query = urllib.parse.quote(f"{query} grocery")
        search_url = f"{self.base_url}/search?q={encoded_query}"
        direct_link = f"{self.base_url}/search?q={encoded_query}"

        resp = self.safe_get(search_url)
        if resp and resp.text:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.find_all("div", attrs={"data-id": True})
                for item in items[:3]:
                    title_elem = item.find("a", attrs={"title": True})
                    title = title_elem["title"] if title_elem else query
                    
                    price_elem = item.find("div", string=re.compile(r"₹\d+"))
                    price = None
                    if price_elem:
                        p_match = re.search(r"₹(\d+(?:\.\d+)?)", price_elem.get_text(strip=True))
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
                product_name=f"{query.title()} on Flipkart",
                product_url=direct_link,
                price=None,
                currency="₹",
                availability_status=f"Verify Flipkart Grocery availability in {location or 'your PIN'}",
                location=location,
                confidence=SourceConfidence.LOW
            ))

        return offers

    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        if "flipkart.com" not in url:
            return None
        return self.create_offer(
            product_name="Flipkart Grocery Item",
            product_url=url,
            availability_status="Available on Flipkart",
            confidence=SourceConfidence.MEDIUM
        )
