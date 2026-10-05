"""
SafeBite AI - Supabase Cloud Persistence & Storage Client
Provides persistent storage for:
- User Health Profiles (allergies, medical history, presets)
- Scan History (product audits, clinical verdicts, OCR logs)
- Verified Products Cache (offline and fast repeated lookup)
- Label Scans (Supabase Storage for packaging photos)
"""

import os
import io
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("safebite.supabase")

_supabase_client = None


def get_supabase_client():
    """Returns a singleton Supabase client or None if credentials are not configured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        logger.warning("Supabase URL or Key not set in environment.")
        return None

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def is_supabase_enabled() -> bool:
    """Checks if Supabase client is properly configured and reachable."""
    client = get_supabase_client()
    return client is not None


def save_user_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    """Saves or updates a user's health parameters and preferences in Supabase."""
    client = get_supabase_client()
    if not client:
        return False

    payload = {
        "user_id": user_id,
        "user_name": profile_data.get("user_name", "User"),
        "medical_history": profile_data.get("medical_history", ""),
        "allergies": profile_data.get("allergies_list", []),
        "food_preferences": profile_data.get("food_preferences", ""),
        "diabetic_insulin_sensitivity": float(profile_data.get("diabetic_insulin_sensitivity", 1.0)),
        "cultural_flags": profile_data.get("cultural_flags", {}),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        # Upsert user profile
        client.table("user_profiles").upsert(payload).execute()
        return True
    except Exception as e:
        logger.error(f"Error saving user profile to Supabase: {e}")
        return False


def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user profile by ID."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching user profile from Supabase: {e}")
        return None


def save_scan_history(entry: Dict[str, Any]) -> bool:
    """Records an audited product scan into Supabase scan_history."""
    client = get_supabase_client()
    if not client:
        return False

    payload = {
        "user_id": entry.get("user_id", "default_user"),
        "product_id": entry.get("product_id") or str(uuid.uuid4())[:8],
        "product_name": entry.get("name", "Unknown Product"),
        "brand": entry.get("brand", ""),
        "verdict": entry.get("verdict", "UNKNOWN"),
        "confidence": entry.get("confidence", "UNVERIFIED"),
        "input_mode": entry.get("input_mode", "text"),
        "nutrition_facts": entry.get("nutrition_facts", {}),
        "ingredients": entry.get("ingredients", ""),
        "allergens": entry.get("allergens", []),
        "ocr_text": entry.get("ocr_text", ""),
        "image_url": entry.get("image_url"),
        "clinical_reasons": entry.get("clinical_reasons", []),
        "created_at": entry.get("timestamp") or datetime.now(timezone.utc).isoformat()
    }

    try:
        client.table("scan_history").insert(payload).execute()
        return True
    except Exception as e:
        logger.error(f"Error saving scan history to Supabase: {e}")
        return False


def get_scan_history(user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches recent scan history entries."""
    client = get_supabase_client()
    if not client:
        return []

    try:
        query = client.table("scan_history").select("*").order("created_at", desc=True).limit(limit)
        if user_id:
            query = query.eq("user_id", user_id)
        res = query.execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error fetching scan history from Supabase: {e}")
        return []


def cache_verified_product(product_data: Dict[str, Any]) -> bool:
    """Caches an authoritative lab product profile into verified_products_cache."""
    client = get_supabase_client()
    if not client:
        return False

    payload = {
        "id": product_data.get("id") or str(uuid.uuid4()),
        "barcode": product_data.get("barcode", ""),
        "name": product_data.get("name", "Unknown"),
        "brand": product_data.get("brand", ""),
        "category": product_data.get("category", ""),
        "nutrition_facts": product_data.get("nutrition_facts", {}),
        "ingredients": product_data.get("ingredients", ""),
        "allergens": product_data.get("allergens", []),
        "nova_group": product_data.get("nova_group", 0),
        "last_verified_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        client.table("verified_products_cache").upsert(payload).execute()
        return True
    except Exception as e:
        logger.error(f"Error caching product in Supabase: {e}")
        return False


def get_cached_product(barcode_or_id: str) -> Optional[Dict[str, Any]]:
    """Searches cache by barcode or ID."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        res = client.table("verified_products_cache").select("*").or_(
            f"barcode.eq.{barcode_or_id},id.eq.{barcode_or_id}"
        ).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"Error querying product cache from Supabase: {e}")
        return None


def upload_label_scan(image_bytes: bytes, filename: Optional[str] = None, content_type: str = "image/jpeg") -> Optional[str]:
    """Uploads packaging image to Supabase Storage 'label-scans' bucket and returns its public URL."""
    client = get_supabase_client()
    if not client:
        return None

    if not filename:
        ext = "jpg" if "jpeg" in content_type else "png"
        filename = f"scans/{uuid.uuid4().hex}.{ext}"

    try:
        # Upload file to label-scans bucket
        client.storage.from_("label-scans").upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        # Retrieve public URL
        public_url = client.storage.from_("label-scans").get_public_url(filename)
        return public_url
    except Exception as e:
        logger.error(f"Error uploading image to Supabase Storage: {e}")
        return None


def test_supabase_connection() -> Dict[str, Any]:
    """Tests the connection to Supabase and reports status."""
    client = get_supabase_client()
    if not client:
        return {"connected": False, "error": "Client could not be initialized"}

    status = {
        "connected": True,
        "url": os.environ.get("SUPABASE_URL"),
        "tables": {}
    }

    for table in ["user_profiles", "scan_history", "verified_products_cache"]:
        try:
            res = client.table(table).select("*").limit(1).execute()
            status["tables"][table] = "accessible"
        except Exception as e:
            status["tables"][table] = f"error: {str(e)[:100]}"

    return status
