import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup

from schemas import RetailerOffer, SourceConfidence
from retailer_sources.base import BaseRetailer

class ZeptoRetailer(BaseRetailer):
    """
    Zepto Quick Grocery Intelligence Source (India).
    Targeted to hyper-local 10-minute delivery in Bengaluru and metros.
    """
    def __init__(self, enabled: bool = True):
        super().__init__(name="Zepto", enabled=enabled)
        self.base_url = "https://www.zeptonow.com"

    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        if not self.enabled:
            return []

        offers: List[RetailerOffer] = []
        encoded = urllib.parse.quote(query)
        search_url = f"{self.base_url}/search?query={encoded}"
        direct_link = f"https://duckduckgo.com/?q={urllib.parse.quote(f'!ducky site:zeptonow.com {query}')}"

        resp = self.safe_get(search_url)
        if resp and resp.text and "Just a moment..." not in resp.text:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                product_cards = soup.find_all("a", href=re.compile(r"/pn/"))
                for card in product_cards[:3]:
                    href = card.get("href")
                    prod_url = f"{self.base_url}{href}" if href.startswith("/") else href
                    title = card.get_text(strip=True) or query
                    offers.append(
                        self.create_offer(
                            product_name=title,
                            product_url=prod_url,
                            price=None,
                            pack_size=None,
                            in_stock=True,
                            availability_status=f"⚡ 10-Min Delivery in {location or 'Bengaluru'}",
                            location=location,
                            confidence=SourceConfidence.MEDIUM
                        )
                    )
            except Exception:
                pass

        if not offers:
            offers.append(
                self.create_offer(
                    product_name=f"{query} (Zepto Quick Delivery)",
                    product_url=direct_link,
                    price=None,
                    pack_size=None,
                    in_stock=True,
                    availability_status=f"⚡ 10-Min Flash Delivery in {location or 'Bengaluru'}",
                    location=location,
                    confidence=SourceConfidence.MEDIUM
                )
            )

        return offers

    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        if "zepto" not in url.lower():
            return None
        return self.create_offer(
            product_name="Zepto Product",
            product_url=url,
            price=None,
            in_stock=True,
            availability_status="Instant Delivery via Zepto",
            confidence=SourceConfidence.MEDIUM
        )
