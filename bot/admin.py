"""
Admin utilities for Silli ME Bot
"""
import os
from typing import Set

def get_admin_ids() -> Set[int]:
    """Get set of admin user IDs from environment variable."""
    admin_ids_str = os.getenv("ADMIN_IDS", "").strip()
    if not admin_ids_str:
        return set()
    
    admin_ids = set()
    for id_str in admin_ids_str.split(","):
        id_str = id_str.strip()
        if id_str.isdigit():
            admin_ids.add(int(id_str))
    
    return admin_ids

def is_admin(user_id: int) -> bool:
    """Check if user ID is in the admin list."""
    return user_id in get_admin_ids()
