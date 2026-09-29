"""
SafeBite AI - Centralized Configuration System
Maintains application constants, timeouts, clinical thresholds, and source reliability policies.
"""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ---------------------------------------------------------
    # Application Metadata
    # ---------------------------------------------------------
    APP_NAME = "SafeBite AI"
    APP_VERSION = "2.0.0-production"
    APP_TAGLINE = "Evidence before you eat."
    
    # ---------------------------------------------------------
    # Network & Retrieval Timeouts (Bounded for Speed)
    # ---------------------------------------------------------
    HTTP_CONNECT_TIMEOUT = 3.0    # Seconds
    HTTP_READ_TIMEOUT = 5.0       # Seconds
    RETAILER_TIMEOUT = 4.0        # Seconds per retailer query
    OFF_API_TIMEOUT = 5.0         # Seconds for Open Food Facts
    MAX_RETRIES = 1               # Bounded retries to avoid latency spikes
    MAX_CONCURRENT_WORKERS = 6    # Parallel scraping threads
    
    # ---------------------------------------------------------
    # Cache Configuration (TTL in Seconds)
    # ---------------------------------------------------------
    CACHE_ENABLED = True
    CACHE_QUERY_TTL = 3600        # 1 Hour
    CACHE_URL_TTL = 7200          # 2 Hours
    CACHE_OFF_TTL = 86400         # 24 Hours (authoritative data rarely changes rapidly)
    CACHE_MAX_ENTRIES = 500
    
    # ---------------------------------------------------------
    # LLM Service Settings
    # ---------------------------------------------------------
    LLM_TIMEOUT = 12.0            # Max wait time for LLM call
    FAST_FAILOVER_ON_429 = True   # Failover immediately from Gemini to Groq on rate limit
    
    # Prioritized Gemini models
    GEMINI_MODELS = [
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3.6-flash"
    ]
    
    GROQ_MODELS = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile"
    ]
    
    # ---------------------------------------------------------
    # Deterministic Clinical Safety Thresholds
    # ---------------------------------------------------------
    # Diabetes / Glycemic thresholds
    DIABETES_MAX_TOTAL_SUGAR_G = 10.0   # > 10g triggers AVOID
    DIABETES_CAUTION_SUGAR_G = 5.0      # > 5g triggers CAUTION
    DIABETES_MAX_ADDED_SUGAR_G = 0.0    # Strict 0g added sugar preference
    
    # Hypertension / Sodium thresholds (per serving, mg)
    HYPERTENSION_LOW_SODIUM_MG = 140.0  # <= 140mg is low sodium (CLEAR)
    HYPERTENSION_MAX_SODIUM_MG = 400.0  # > 400mg triggers AVOID
    
    # High Protein thresholds (per serving, g)
    HIGH_PROTEIN_MIN_G = 10.0           # >= 10g qualifies as high protein
    HIGH_PROTEIN_PREMIUM_G = 15.0       # >= 15g top tier
    
    # Low Sugar threshold (per serving, g)
    LOW_SUGAR_MAX_G = 5.0               # <= 5g total sugar
    
    # Fiber thresholds (per serving, g)
    HIGH_FIBER_MIN_G = 5.0              # >= 5g qualifies as high fiber
    
    # ---------------------------------------------------------
    # Default & Saved Locations
    # ---------------------------------------------------------
    DEFAULT_LOCATION = {
        "label": "Bengaluru (Default Metro)",
        "country": "India",
        "state": "Karnataka",
        "city": "Bengaluru",
        "pincode": "560001",
        "address": "MG Road"
    }
    
    SAVED_LOCATION_PRESETS = [
        {
            "id": "bengaluru",
            "name": "Bengaluru, Karnataka (India)",
            "country": "India",
            "state": "Karnataka",
            "city": "Bengaluru",
            "pincode": "560001",
            "address": "Indiranagar 100ft Rd"
        },
        {
            "id": "mumbai",
            "name": "Mumbai, Maharashtra (India)",
            "country": "India",
            "state": "Maharashtra",
            "city": "Mumbai",
            "pincode": "400001",
            "address": "Bandra West"
        },
        {
            "id": "delhi",
            "name": "Delhi NCR (India)",
            "country": "India",
            "state": "Delhi",
            "city": "New Delhi",
            "pincode": "110001",
            "address": "Connaught Place"
        },
        {
            "id": "hyderabad",
            "name": "Hyderabad, Telangana (India)",
            "country": "India",
            "state": "Telangana",
            "city": "Hyderabad",
            "pincode": "500081",
            "address": "Hitec City"
        },
        {
            "id": "newyork",
            "name": "New York, NY (USA)",
            "country": "United States",
            "state": "NY",
            "city": "New York",
            "pincode": "10001",
            "address": "452 Broadway"
        },
        {
            "id": "london",
            "name": "London, England (UK)",
            "country": "United Kingdom",
            "state": "Greater London",
            "city": "London",
            "pincode": "EC1A 1BB",
            "address": "10 Baker Street"
        }
    ]

    # ---------------------------------------------------------
    # User-Agent Policy (Respectful and Professional)
    # ---------------------------------------------------------
    USER_AGENT = (
        "SafeBite-Food-Safety-Intelligence/2.0 "
        "(Clinical Food Safety Verification Engine; respectful bot; +https://safebite.ai)"
    )
