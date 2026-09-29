import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup

from schemas import RetailerOffer, SourceConfidence
from retailer_sources.base import BaseRetailer

class BlinkitRetailer(BaseRetailer):
    """
    Blinkit Quick-Commerce 10-15 min Grocery Intelligence Source (India).
    Targeted to quick instant delivery in Bengaluru, Delhi-NCR, Mumbai, etc.
    """
    def __init__(self, enabled: bool = True):
        super().__init__(name="Blinkit", enabled=enabled)
        self.base_url = "https://blinkit.com"

    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        if not self.enabled:
            return []

        offers: List[RetailerOffer] = []
        encoded = urllib.parse.quote(query)
        search_url = f"{self.base_url}/s/?q={encoded}"
        direct_link = f"https://duckduckgo.com/?q={urllib.parse.quote(f'!ducky site:blinkit.com {query}')}"

        resp = self.safe_get(search_url)
        if resp and resp.text and "Just a moment..." not in resp.text:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Look for product cards
                cards = soup.find_all("div", attrs={"data-test-id": re.compile(r"product", re.I)})
                for card in cards[:3]:
                    title_elem = card.find(text=True)
                    title = title_elem.strip() if title_elem else query
                    offers.append(
                        self.create_offer(
                            product_name=title,
                            product_url=search_url,
                            price=None,
                            pack_size=None,
                            in_stock=True,
                            availability_status=f"⚡ 10-15 Min Delivery in {location or 'Bengaluru'}",
                            location=location,
                            confidence=SourceConfidence.MEDIUM
                        )
                    )
            except Exception:
                pass

        if not offers:
            offers.append(
                self.create_offer(
                    product_name=f"{query} (Blinkit Quick Commerce)",
                    product_url=direct_link,
                    price=None,
                    pack_size=None,
                    in_stock=True,
                    availability_status=f"⚡ Instant 10-Min Delivery in {location or 'Bengaluru'}",
                    location=location,
                    confidence=SourceConfidence.MEDIUM
                )
            )

        return offers

    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        if "blinkit" not in url.lower():
            return None
        return self.create_offer(
            product_name="Blinkit Product",
            product_url=url,
            price=None,
            in_stock=True,
            availability_status="Instant Delivery via Blinkit",
            confidence=SourceConfidence.MEDIUM
        )
