import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import requests

from schemas import RetailerOffer, SourceConfidence

logger = logging.getLogger(__name__)

class BaseRetailer(ABC):
    """
    Abstract Base Class for Retailer Intelligence Sources.
    Modular, respecting rate limits, robots.txt, terms, and graceful fallback.
    Never attempts CAPTCHA bypass or unauthorized crawling.
    """
    def __init__(self, name: str, enabled: bool = True, timeout: int = 6):
        self.name = name
        self.enabled = enabled
        self.timeout = timeout
        self.headers = {
            "User-Agent": "SafeBite-Product-Intelligence/1.0 (Health & Allergen Cross-Referencing Engine; respectful bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @abstractmethod
    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        """Search the retailer catalog for live product offers."""
        pass

    @abstractmethod
    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        """Fetch retailer product offer from a direct product link."""
        pass

    def safe_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        """
        Executes a safe GET request. 
        If 403 (bot protection), 429 (rate limited), or connection issue occurs, 
        returns None gracefully without attempting bypass or violation of terms.
        """
        if not self.enabled:
            return None
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code in (403, 429, 503):
                logger.warning(f"[{self.name}] Rate limit / bot protection encountered (HTTP {resp.status_code}). Gracefully falling back.")
                return None
            if resp.status_code == 200:
                return resp
            logger.info(f"[{self.name}] Request returned HTTP {resp.status_code}")
            return None
        except Exception as e:
            logger.info(f"[{self.name}] Network error: {e}. Gracefully falling back.")
            return None

    def create_offer(
        self,
        product_name: str,
        product_url: str,
        price: Optional[float] = None,
        currency: str = "₹",
        pack_size: Optional[str] = None,
        in_stock: bool = True,
        availability_status: str = "Available",
        location: Optional[str] = None,
        confidence: SourceConfidence = SourceConfidence.MEDIUM
    ) -> RetailerOffer:
        """Helper to create a validated RetailerOffer with standard timestamp and source metadata."""
        return RetailerOffer(
            retailer=self.name,
            product_name=product_name,
            price=price,
            currency=currency,
            pack_size=pack_size,
            in_stock=in_stock,
            product_url=product_url,
            availability_status=availability_status,
            location=location,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            confidence=confidence
        )
