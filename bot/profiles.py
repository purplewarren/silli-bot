"""
Family Profiles - Append-only log + snapshot storage

Provides family profile management with:
- Pydantic models with validation
- Append-only JSONL logging
- Fast snapshot indexing
- Thread-safe operations
- Join code system
"""

import asyncio
import json
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field
from loguru import logger
import collections.abc


# ==================== PYDANTIC MODELS ====================

class Child(BaseModel):
    name: str
    age_years: float
    sex: Literal["m", "f", "na"]


class FamilyProfile(BaseModel):
    family_id: str  # "fam_<creator_chat_id>"
    creator_chat_id: int
    members: List[int]  # includes creator
    parent_name: str
    parent_age: Optional[int] = None
    timezone: str = "UTC"  # IANA tz
    children: List[Child] = []
    health_notes: str = ""
    lifestyle_tags: List[str] = []
    cloud_reasoning: bool = False  # Per-family reasoner toggle
    locale: str = "en"  # User language preference
    created_at: datetime
    updated_at: datetime
    version: int = 1
    complete: bool = False  # gates the bot


# ==================== PROFILES STORE ====================

def _jsonl_safe(obj):
    """Recursively convert datetimes to ISO strings for JSONL logging."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [_jsonl_safe(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: _jsonl_safe(v) for k, v in obj.items()}
    elif isinstance(obj, collections.abc.Mapping):
        return {k: _jsonl_safe(v) for k, v in obj.items()}
    elif hasattr(obj, 'dict'):
        return _jsonl_safe(obj.model_dump())
    else:
        return obj

class ProfilesStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.profiles_log_path = self.data_dir / "profiles.jsonl"
        self.profiles_index_path = self.data_dir / "profiles_index.json"
        self.join_codes_path = self.data_dir / "join_codes.json"
        
        self._lock = None
        self._index: Dict[str, FamilyProfile] = {}
        self._join_codes: Dict[str, Dict[str, Any]] = {}
        
        # Load existing data
        self._load_index()
        self._load_join_codes()
    
    def _get_lock(self):
        """Get or create the asyncio lock."""
        if self._lock is None:
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                # If we're not in an event loop, create a dummy lock
                class DummyLock:
                    async def __aenter__(self): pass
                    async def __aexit__(self, *args): pass
                self._lock = DummyLock()
        return self._lock
    
    def _create_minimal_profile(self, chat_id: int) -> FamilyProfile:
        """Create a minimal profile stub."""
        family_id = f"fam_{chat_id}"
        now = datetime.now()
        
        return FamilyProfile(
            family_id=family_id,
            creator_chat_id=chat_id,
            members=[chat_id],
            parent_name="",
            created_at=now,
            updated_at=now
        )
    
    def _load_index(self) -> None:
        """Load profiles index from JSON file."""
        try:
            if self.profiles_index_path.exists():
                with open(self.profiles_index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._index = {
                        family_id: FamilyProfile(**profile_data)
                        for family_id, profile_data in data.items()
                    }
                logger.info(f"Loaded {len(self._index)} profiles from index")
            else:
                logger.info("No profiles index found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading profiles index: {e}")
            self._index = {}
    
    def _save_index(self) -> None:
        """Save profiles index to JSON file."""
        try:
            data = {
                family_id: profile.model_dump()
                for family_id, profile in self._index.items()
            }
            with open(self.profiles_index_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved {len(self._index)} profiles to index")
        except Exception as e:
            logger.error(f"Error saving profiles index: {e}")
    
    def _load_join_codes(self) -> None:
        """Load join codes from JSON file."""
        try:
            if self.join_codes_path.exists():
                with open(self.join_codes_path, 'r', encoding='utf-8') as f:
                    self._join_codes = json.load(f)
                logger.info(f"Loaded {len(self._join_codes)} join codes")
            else:
                logger.info("No join codes found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading join codes: {e}")
            self._join_codes = {}
    
    def _save_join_codes(self) -> None:
        """Save join codes to JSON file."""
        try:
            with open(self.join_codes_path, 'w', encoding='utf-8') as f:
                json.dump(self._join_codes, f, indent=2, default=str)
            logger.debug(f"Saved {len(self._join_codes)} join codes")
        except Exception as e:
            logger.error(f"Error saving join codes: {e}")
    
    def _append_log(self, event: Dict[str, Any]) -> None:
        """Append event to JSONL log."""
        try:
            event['ts'] = datetime.now().isoformat()
            safe_event = _jsonl_safe(event)
            with open(self.profiles_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(safe_event) + '\n')
            logger.debug(f"Appended event: {event['type']}")
        except Exception as e:
            logger.error(f"Error appending to log: {e}")
    
    def _garbage_collect_join_codes(self) -> None:
        """Remove expired join codes."""
        now = datetime.now()
        expired = []
        for code, data in self._join_codes.items():
            expires_at = datetime.fromisoformat(data['expires_at'])
            if now > expires_at:
                expired.append(code)
        
        for code in expired:
            del self._join_codes[code]
        
        if expired:
            logger.info(f"Garbage collected {len(expired)} expired join codes")
            self._save_join_codes()
    
    async def get_profile_by_chat(self, chat_id: int) -> Optional[FamilyProfile]:
        """Get profile by chat ID (any member)."""
        async with self._get_lock():
            for profile in self._index.values():
                if chat_id in profile.members:
                    return profile
            return None
    
    def get_profile_by_chat_sync(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get profile by chat ID (sync version for i18n)."""
        for profile in self._index.values():
            if chat_id in profile.members:
                return profile.model_dump()
        return None
    
    async def get_profile(self, family_id: str) -> Optional[FamilyProfile]:
        """Get profile by family ID."""
        async with self._get_lock():
            return self._index.get(family_id)
    
    async def create_or_get(self, chat_id: int) -> FamilyProfile:
        """Create minimal profile stub or get existing."""
        async with self._get_lock():
            # Check if user is already a member of any family
            existing = await self.get_profile_by_chat(chat_id)
            if existing:
                return existing
            
            # Create new family
            family_id = f"fam_{chat_id}"
            now = datetime.now()
            
            profile = FamilyProfile(
                family_id=family_id,
                creator_chat_id=chat_id,
                members=[chat_id],
                parent_name="",
                created_at=now,
                updated_at=now
            )
            
            self._index[family_id] = profile
            self._save_index()
            
            # Log creation
            self._append_log({
                'type': 'UPSERT_PROFILE',
                'payload': profile.model_dump()
            })
            
            logger.info(f"Created new family profile: {family_id}")
            return profile
    
    async def upsert_fields(self, family_id: str, **fields) -> FamilyProfile:
        """Update profile fields."""
        async with self._get_lock():
            if family_id not in self._index:
                raise ValueError(f"Family {family_id} not found")
            
            profile = self._index[family_id]
            
            # Update fields
            for key, value in fields.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.now()
            self._index[family_id] = profile
            self._save_index()
            
            # Log update
            self._append_log({
                'type': 'SET_FIELDS',
                'family_id': family_id,
                'payload': fields
            })
            
            logger.info(f"Updated profile {family_id}: {list(fields.keys())}")
            return profile
    
    def upsert_fields_sync(self, chat_id: int, fields: Dict[str, Any]) -> bool:
        """Update profile fields (sync version for i18n)."""
        try:
            # Find family by chat_id
            family_id = None
            for fid, profile in self._index.items():
                if chat_id in profile.members:
                    family_id = fid
                    break
            
            if not family_id:
                logger.error(f"No family found for chat_id {chat_id}")
                return False
            
            profile = self._index[family_id]
            
            # Update fields
            for key, value in fields.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.now()
            self._index[family_id] = profile
            self._save_index()
            
            # Log update
            self._append_log({
                'type': 'SET_FIELDS',
                'family_id': family_id,
                'payload': fields
            })
            
            logger.info(f"Updated profile {family_id}: {list(fields.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Error in upsert_fields_sync: {e}")
            return False
    
    async def mark_complete(self, family_id: str, value: bool = True) -> FamilyProfile:
        """Mark profile as complete."""
        return await self.upsert_fields(family_id, complete=value)
    
    async def add_member(self, family_id: str, chat_id: int) -> FamilyProfile:
        """Add member to family."""
        async with self._get_lock():
            if family_id not in self._index:
                raise ValueError(f"Family {family_id} not found")
            
            profile = self._index[family_id]
            
            if chat_id not in profile.members:
                profile.members.append(chat_id)
                profile.updated_at = datetime.now()
                self._index[family_id] = profile
                self._save_index()
                
                # Log addition
                self._append_log({
                    'type': 'ADD_MEMBER',
                    'family_id': family_id,
                    'chat_id': chat_id
                })
                
                logger.info(f"Added member {chat_id} to family {family_id}")
            
            return profile
    
    async def remove_member(self, family_id: str, chat_id: int) -> FamilyProfile:
        """Remove member from family."""
        async with self._get_lock():
            if family_id not in self._index:
                raise ValueError(f"Family {family_id} not found")
            
            profile = self._index[family_id]
            
            if chat_id in profile.members:
                profile.members.remove(chat_id)
                profile.updated_at = datetime.now()
                self._index[family_id] = profile
                self._save_index()
                
                # Log removal
                self._append_log({
                    'type': 'REMOVE_MEMBER',
                    'family_id': family_id,
                    'chat_id': chat_id
                })
                
                logger.info(f"Removed member {chat_id} from family {family_id}")
            
            return profile
    
    async def find_family_id_by_member(self, chat_id: int) -> Optional[str]:
        """Find family ID by member chat ID."""
        profile = await self.get_profile_by_chat(chat_id)
        return profile.family_id if profile else None
    
    async def generate_join_code(self, family_id: str) -> str:
        """Generate secure join code for family."""
        async with self._get_lock():
            if family_id not in self._index:
                raise ValueError(f"Family {family_id} not found")
            
            # Generate 6-8 character code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            
            # Set expiration (48 hours)
            expires_at = datetime.now() + timedelta(hours=48)
            
            self._join_codes[code] = {
                'family_id': family_id,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }
            
            self._save_join_codes()
            
            logger.info(f"Generated join code {code} for family {family_id}")
            return code
    
    async def consume_join_code(self, code: str, chat_id: int) -> FamilyProfile:
        """Consume join code and add user to family."""
        async with self._get_lock():
            # Garbage collect expired codes
            self._garbage_collect_join_codes()
            
            if code not in self._join_codes:
                raise ValueError("Invalid or expired join code")
            
            code_data = self._join_codes[code]
            family_id = code_data['family_id']
            
            # Add member to family
            profile = await self.add_member(family_id, chat_id)
            
            # Remove used code
            del self._join_codes[code]
            self._save_join_codes()
            
            logger.info(f"Consumed join code {code} for chat {chat_id} -> family {family_id}")
            return profile
    
    async def list_members(self, family_id: str) -> List[int]:
        """List all members of a family."""
        profile = await self.get_profile(family_id)
        return profile.members if profile else []


# ==================== GLOBAL INSTANCE ====================

profiles = ProfilesStore() 