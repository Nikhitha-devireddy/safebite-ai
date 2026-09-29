"""
SafeBite AI - Unified Source Concurrency, Caching & Telemetry Manager
Coordinates parallel data retrieval across Open Food Facts, official brand websites,
and grocery retailers (Amazon, BigBasket, Blinkit, Zepto, Instamart, Flipkart, JioMart).
Enforces bounded timeouts and in-memory TTL caching to keep searches under 3-5 seconds.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from schemas import Product, RetailerOffer, SourceConfidence, RetrievalResult
from config import Config

class SourceTelemetry:
    """Tracks latency and reliability of external sources for System Health diagnostics."""
    def __init__(self):
        self.lock = threading.Lock()
        self.stats: Dict[str, Dict[str, Any]] = {}

    def record_request(self, source_name: str, duration_ms: float, success: bool, status_code: Optional[int] = None):
        with self.lock:
            if source_name not in self.stats:
                self.stats[source_name] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "blocked_403": 0,
                    "rate_limited_429": 0,
                    "total_duration_ms": 0.0,
                    "avg_duration_ms": 0.0,
                    "last_status": status_code,
                    "last_retrieved": datetime.now(timezone.utc).isoformat()
                }
            s = self.stats[source_name]
            s["total_requests"] += 1
            if success:
                s["successful_requests"] += 1
            else:
                s["failed_requests"] += 1
                if status_code == 403:
                    s["blocked_403"] += 1
                elif status_code == 429:
                    s["rate_limited_429"] += 1

            s["total_duration_ms"] += duration_ms
            s["avg_duration_ms"] = round(s["total_duration_ms"] / s["total_requests"], 1)
            s["last_status"] = status_code
            s["last_retrieved"] = datetime.now(timezone.utc).isoformat()

    def get_summary(self) -> Dict[str, Any]:
        with self.lock:
            return {k: dict(v) for k, v in self.stats.items()}

class SourceManager:
    """
    Singleton concurrency and caching manager.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SourceManager, cls).__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_lock = threading.Lock()
        self.telemetry = SourceTelemetry()
        self.executor = ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_WORKERS, thread_name_prefix="SafeBiteSourceWorker")

    def get_cached(self, key: str, ttl_seconds: int = 3600) -> Optional[Any]:
        """Retrieves item from cache if not expired."""
        with self.cache_lock:
            if key in self.cache:
                timestamp, data = self.cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return data
                else:
                    del self.cache[key]
        return None

    def set_cached(self, key: str, data: Any):
        """Stores item in in-memory cache with current timestamp."""
        with self.cache_lock:
            if len(self.cache) > Config.CACHE_MAX_ENTRIES:
                # Evict oldest entry
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
                del self.cache[oldest_key]
            self.cache[key] = (time.time(), data)

    def record_telemetry(self, source_name: str, duration_ms: float, success: bool, status_code: Optional[int] = None):
        self.telemetry.record_request(source_name, duration_ms, success, status_code)

    def get_telemetry_summary(self) -> Dict[str, Any]:
        return self.telemetry.get_summary()

    def clear_cache(self):
        with self.cache_lock:
            self.cache.clear()
