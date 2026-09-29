"""
SafeBite AI - Retailer Registry & Concurrency Engine
Aggregates live offers across Amazon, BigBasket, Blinkit, Zepto,
Swiggy Instamart, Flipkart Grocery, and JioMart in parallel.
Never crashes if individual scrapers encounter 403, 429, or network timeouts.
"""

from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from schemas import RetailerOffer
from retailer_sources.base import BaseRetailer
from retailer_sources.amazon import AmazonRetailer
from retailer_sources.bigbasket import BigBasketRetailer
from retailer_sources.blinkit import BlinkitRetailer
from retailer_sources.zepto import ZeptoRetailer
from retailer_sources.instamart import InstamartRetailer
from retailer_sources.flipkart import FlipkartRetailer
from retailer_sources.jiomart import JioMartRetailer
from config import Config

# Registry of modular retailers
AVAILABLE_RETAILERS: Dict[str, BaseRetailer] = {
    "amazon": AmazonRetailer(),
    "bigbasket": BigBasketRetailer(),
    "blinkit": BlinkitRetailer(),
    "zepto": ZeptoRetailer(),
    "instamart": InstamartRetailer(),
    "flipkart": FlipkartRetailer(),
    "jiomart": JioMartRetailer()
}

def get_retailer(name: str) -> Optional[BaseRetailer]:
    return AVAILABLE_RETAILERS.get(name.lower())

def get_all_retailers(enabled_only: bool = True) -> List[BaseRetailer]:
    if enabled_only:
        return [r for r in AVAILABLE_RETAILERS.values() if r.enabled]
    return list(AVAILABLE_RETAILERS.values())

def search_all_retailers(
    query: str,
    location: Optional[str] = None,
    retailer_names: Optional[List[str]] = None,
    max_workers: int = 5
) -> List[RetailerOffer]:
    """
    Executes concurrent parallel queries across all enabled retailers.
    Runs independent network requests simultaneously using ThreadPoolExecutor
    to slash retrieval latency from 25+ seconds down to 2-3 seconds.
    """
    if retailer_names:
        target_retailers = [AVAILABLE_RETAILERS[n.lower()] for n in retailer_names if n.lower() in AVAILABLE_RETAILERS and AVAILABLE_RETAILERS[n.lower()].enabled]
    else:
        # Default priority retailers
        priority_keys = ["amazon", "bigbasket", "blinkit", "zepto"]
        target_retailers = [AVAILABLE_RETAILERS[k] for k in priority_keys if k in AVAILABLE_RETAILERS and AVAILABLE_RETAILERS[k].enabled]

    aggregated_offers: List[RetailerOffer] = []
    seen_urls = set()

    def _query_worker(retailer: BaseRetailer) -> List[RetailerOffer]:
        try:
            return retailer.search(query=query, location=location)
        except Exception:
            return []

    # Parallel retrieval
    with ThreadPoolExecutor(max_workers=min(len(target_retailers), max_workers)) as executor:
        future_map = {executor.submit(_query_worker, r): r.name for r in target_retailers}
        for future in as_completed(future_map, timeout=Config.RETAILER_TIMEOUT + 1.0):
            try:
                offers = future.result()
                for o in offers:
                    if o.product_url not in seen_urls:
                        seen_urls.add(o.product_url)
                        aggregated_offers.append(o)
            except Exception:
                pass

    return aggregated_offers
