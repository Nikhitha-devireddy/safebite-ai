from typing import List, Optional, Dict
from schemas import RetailerOffer
from retailer_sources.base import BaseRetailer
from retailer_sources.amazon import AmazonRetailer
from retailer_sources.bigbasket import BigBasketRetailer
from retailer_sources.blinkit import BlinkitRetailer
from retailer_sources.zepto import ZeptoRetailer

# Registry of modular retailers
AVAILABLE_RETAILERS: Dict[str, BaseRetailer] = {
    "amazon": AmazonRetailer(),
    "bigbasket": BigBasketRetailer(),
    "blinkit": BlinkitRetailer(),
    "zepto": ZeptoRetailer()
}

def get_retailer(name: str) -> Optional[BaseRetailer]:
    return AVAILABLE_RETAILERS.get(name.lower())

def get_all_retailers(enabled_only: bool = True) -> List[BaseRetailer]:
    if enabled_only:
        return [r for r in AVAILABLE_RETAILERS.values() if r.enabled]
    return list(AVAILABLE_RETAILERS.values())

def search_all_retailers(query: str, location: Optional[str] = None) -> List[RetailerOffer]:
    """
    Queries all enabled retailers in parallel or sequence,
    aggregating offers with price, availability, and direct links.
    """
    aggregated_offers: List[RetailerOffer] = []
    for retailer in get_all_retailers(enabled_only=True):
        try:
            offers = retailer.search(query=query, location=location)
            aggregated_offers.extend(offers)
        except Exception as e:
            # Never crash if one retailer fails
            pass
    return aggregated_offers
