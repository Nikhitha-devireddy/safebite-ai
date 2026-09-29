"""
SafeBite AI - Retailer Base Adapter & Retrieval Architecture
Provides standard error handling for 200, 301/302, 403, 404, 408, 429, 500+,
timeouts, SSL errors, and connection failures.
Never bypasses CAPTCHA, bot protection, or website terms.
Emits structured RetrievalResult for full observability.
"""

import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
import requests

from schemas import RetailerOffer, SourceConfidence, RetrievalResult
from config import Config

logger = logging.getLogger(__name__)

class BaseRetailer(ABC):
    """
    Abstract Base Class for Retailer Intelligence Sources.
    Modular, respecting rate limits, robots.txt, terms, and graceful fallback.
    Never attempts CAPTCHA bypass or unauthorized crawling.
    """
    def __init__(self, name: str, enabled: bool = True, timeout: Optional[int] = None):
        self.name = name
        self.enabled = enabled
        self.timeout = timeout or Config.RETAILER_TIMEOUT
        self.headers = {
            "User-Agent": Config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.last_result: Optional[RetrievalResult] = None

    @abstractmethod
    def search(self, query: str, location: Optional[str] = None) -> List[RetailerOffer]:
        """Search the retailer catalog for live product offers."""
        pass

    @abstractmethod
    def get_offer_by_url(self, url: str) -> Optional[RetailerOffer]:
        """Fetch retailer product offer from a direct product link."""
        pass

    def safe_fetch_with_result(self, url: str, params: Optional[Dict[str, Any]] = None) -> Tuple[Optional[requests.Response], RetrievalResult]:
        """
        Executes an audited HTTP GET request.
        Safely classifies status codes:
        - 200: Success
        - 301/302: Redirect
        - 403: Bot protection / access restricted (graceful fallback)
        - 429: Rate limited
        - 404: Not found
        - 500+: Server error
        - Timeout / Connection Failure
        """
        start_time = time.time()
        now_str = datetime.now(timezone.utc).isoformat()

        if not self.enabled:
            res = RetrievalResult(
                success=False,
                source=self.name,
                url=url,
                error_type="DISABLED",
                error_message=f"{self.name} retailer source is currently disabled in configuration.",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str,
                duration_ms=0.0
            )
            self.last_result = res
            return None, res

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            duration_ms = round((time.time() - start_time) * 1000, 1)

            if resp.status_code == 200:
                res = RetrievalResult(
                    success=True,
                    status_code=200,
                    source=self.name,
                    url=url,
                    confidence=SourceConfidence.HIGH,
                    retrieved_at=now_str,
                    duration_ms=duration_ms
                )
                self.last_result = res
                return resp, res

            elif resp.status_code == 403:
                logger.warning(f"[{self.name}] Access restricted / bot protection (HTTP 403). Gracefully falling back.")
                res = RetrievalResult(
                    success=False,
                    status_code=403,
                    source=self.name,
                    url=url,
                    error_type="BLOCKED_403",
                    error_message=f"This source ({self.name}) blocked automated access. SafeBite will try another verified source.",
                    confidence=SourceConfidence.UNVERIFIED,
                    retrieved_at=now_str,
                    duration_ms=duration_ms
                )
                self.last_result = res
                return None, res

            elif resp.status_code == 429:
                logger.warning(f"[{self.name}] Rate limit encountered (HTTP 429).")
                res = RetrievalResult(
                    success=False,
                    status_code=429,
                    source=self.name,
                    url=url,
                    error_type="RATE_LIMITED_429",
                    error_message=f"{self.name} is rate-limited. Falling back to alternative data sources.",
                    confidence=SourceConfidence.UNVERIFIED,
                    retrieved_at=now_str,
                    duration_ms=duration_ms
                )
                self.last_result = res
                return None, res

            elif resp.status_code == 404:
                res = RetrievalResult(
                    success=False,
                    status_code=404,
                    source=self.name,
                    url=url,
                    error_type="NOT_FOUND_404",
                    error_message=f"Product page not found on {self.name} (HTTP 404).",
                    confidence=SourceConfidence.UNVERIFIED,
                    retrieved_at=now_str,
                    duration_ms=duration_ms
                )
                self.last_result = res
                return None, res

            elif resp.status_code >= 500:
                res = RetrievalResult(
                    success=False,
                    status_code=resp.status_code,
                    source=self.name,
                    url=url,
                    error_type="SERVER_ERROR_5XX",
                    error_message=f"{self.name} server temporarily unavailable (HTTP {resp.status_code}).",
                    confidence=SourceConfidence.UNVERIFIED,
                    retrieved_at=now_str,
                    duration_ms=duration_ms
                )
                self.last_result = res
                return None, res

            else:
                res = RetrievalResult(
                    success=False,
                    status_code=resp.status_code,
                    source=self.name,
                    url=url,
                    error_type="HTTP_ERROR",
                    error_message=f"{self.name} returned HTTP {resp.status_code}.",
                    confidence=SourceConfidence.UNVERIFIED,
                    retrieved_at=now_str,
                    duration_ms=duration_ms
                )
                self.last_result = res
                return None, res

        except requests.exceptions.Timeout:
            duration_ms = round((time.time() - start_time) * 1000, 1)
            logger.info(f"[{self.name}] Request timed out after {self.timeout}s.")
            res = RetrievalResult(
                success=False,
                source=self.name,
                url=url,
                error_type="TIMEOUT",
                error_message=f"{self.name} connection timed out ({self.timeout}s). Gracefully bypassed.",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str,
                duration_ms=duration_ms
            )
            self.last_result = res
            return None, res

        except requests.exceptions.ConnectionError:
            duration_ms = round((time.time() - start_time) * 1000, 1)
            res = RetrievalResult(
                success=False,
                source=self.name,
                url=url,
                error_type="CONNECTION_ERROR",
                error_message=f"Could not connect to {self.name}. Network route unreachable.",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str,
                duration_ms=duration_ms
            )
            self.last_result = res
            return None, res

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 1)
            res = RetrievalResult(
                success=False,
                source=self.name,
                url=url,
                error_type="UNKNOWN_ERROR",
                error_message=f"Temporary issue accessing {self.name}: {str(e)}",
                confidence=SourceConfidence.UNVERIFIED,
                retrieved_at=now_str,
                duration_ms=duration_ms
            )
            self.last_result = res
            return None, res

    def safe_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        """
        Executes a safe GET request. 
        Returns Response if 200, None on any error or bot challenge.
        Maintains backward compatibility for existing retailers.
        """
        resp, _ = self.safe_fetch_with_result(url, params)
        return resp

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
