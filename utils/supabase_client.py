import os
from functools import lru_cache
from typing import Optional
from supabase import create_client, Client

@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Get a Supabase client instance with proper typing."""
    url: Optional[str] = os.getenv("SUPABASE_URL")
    key: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError("SUPABASE_URL and a key must be set in environment variables")

    return create_client(url, key)

@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Get a Supabase client instance with admin privileges."""
    url: Optional[str] = os.getenv("SUPABASE_URL")
    service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for admin access")

    return create_client(url, service_key)
