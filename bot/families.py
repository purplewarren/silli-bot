# bot/families.py
import json, os, threading, secrets, string
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from .profiles import FamilyProfile, Child

class FamiliesStore:
    def __init__(self, path: str = "data/families.json"):
        self.path = Path(path)
        self.counter_path = Path("data/family_counter.json")
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({})
        if not self.counter_path.exists():
            self._write_counter({"next_id": 1})

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            # Safety check: ensure data is a dictionary
            if not isinstance(data, dict):
                logger.warning(f"Families file contains non-dict data: {type(data)}, initializing as empty dict")
                return {}
            return data
        except Exception as e:
            logger.error(f"Error reading families file: {e}")
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    
    def _read_counter(self) -> Dict[str, Any]:
        if not self.counter_path.exists():
            return {"next_id": 1}
        try:
            return json.loads(self.counter_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error reading counter file: {e}")
            return {"next_id": 1}
    
    def _write_counter(self, counter_data: Dict[str, Any]) -> None:
        self.counter_path.write_text(json.dumps(counter_data, indent=2), encoding="utf-8")
    
    def generate_next_family_id(self) -> str:
        """Generate the next sequential family ID (Family #000001, #000002, etc.)."""
        with self._lock:
            counter_data = self._read_counter()
            next_id = counter_data["next_id"]
            family_id = f"Family #{next_id:06d}"  # Format as Family #000001
            
            # Increment counter for next family
            counter_data["next_id"] = next_id + 1
            self._write_counter(counter_data)
            
            logger.info(f"Generated new family ID: {family_id}")
            return family_id
    
    def migrate_to_sequential_ids(self) -> Dict[str, str]:
        """Migrate existing families to sequential ID system. Returns mapping of old_id -> new_id."""
        with self._lock:
            data = self._read()
            counter_data = self._read_counter()
            
            # If no families exist, nothing to migrate
            if not data:
                logger.info("No families to migrate")
                return {}
            
            mapping = {}
            new_data = {}
            next_id = counter_data["next_id"]
            
            # Sort families by creation date for consistent numbering
            families_with_dates = []
            for old_id, family_data in data.items():
                created_at = family_data.get("created_at", "1970-01-01T00:00:00")
                families_with_dates.append((created_at, old_id, family_data))
            
            families_with_dates.sort(key=lambda x: x[0])  # Sort by creation date
            
            for _, old_id, family_data in families_with_dates:
                # Generate new sequential ID
                new_id = f"Family #{next_id:06d}"
                
                # Update family data with new ID
                family_data["family_id"] = new_id
                family_data["old_family_id"] = old_id  # Keep reference to old ID
                
                new_data[new_id] = family_data
                mapping[old_id] = new_id
                
                logger.info(f"Migrated {old_id} -> {new_id}")
                next_id += 1
            
            # Update counter and save new data
            counter_data["next_id"] = next_id
            self._write(new_data)
            self._write_counter(counter_data)
            
            logger.info(f"Migration complete: {len(mapping)} families migrated")
            return mapping

    def save_family(self, family_data: Dict[str, Any]) -> None:
        """Save a family profile."""
        with self._lock:
            data = self._read()
            family_id = family_data["family_id"]
            data[family_id] = family_data
            self._write(data)
            logger.info(f"Saved family {family_id}")

    def get_family(self, family_id: str) -> Optional[FamilyProfile]:
        """Get a family profile by ID."""
        with self._lock:
            data = self._read()
            if family_id not in data:
                return None
            
            family_data = data[family_id]
            try:
                # Convert the data to FamilyProfile
                return FamilyProfile(**family_data)
            except Exception as e:
                logger.error(f"Error creating FamilyProfile for {family_id}: {e}")
                return None

    def upsert_fields(self, family_id: str, **fields) -> Optional[FamilyProfile]:
        """Update specific fields of a family profile."""
        with self._lock:
            data = self._read()
            if family_id not in data:
                return None
            
            # Update the fields
            data[family_id].update(fields)
            data[family_id]["updated_at"] = datetime.now().isoformat()
            
            self._write(data)
            
            # Return updated profile
            return self.get_family(family_id)

    def add_member(self, family_id: str, chat_id: int) -> Optional[FamilyProfile]:
        """Add a member to a family."""
        with self._lock:
            data = self._read()
            if family_id not in data:
                return None
            
            if "members" not in data[family_id]:
                data[family_id]["members"] = []
            
            if chat_id not in data[family_id]["members"]:
                data[family_id]["members"].append(chat_id)
                data[family_id]["updated_at"] = datetime.now().isoformat()
                self._write(data)
            
            return self.get_family(family_id)

    def remove_member(self, family_id: str, chat_id: int) -> Optional[FamilyProfile]:
        """Remove a member from a family."""
        with self._lock:
            data = self._read()
            if family_id not in data:
                return None
            
            if "members" in data[family_id] and chat_id in data[family_id]["members"]:
                data[family_id]["members"].remove(chat_id)
                data[family_id]["updated_at"] = datetime.now().isoformat()
                self._write(data)
            
            return self.get_family(family_id)

    def list_members(self, family_id: str) -> List[int]:
        """List all members of a family."""
        with self._lock:
            data = self._read()
            if family_id not in data:
                return []
            
            return data[family_id].get("members", [])

    def generate_join_code(self, family_id: str) -> str:
        """Generate a join code for a family."""
        with self._lock:
            data = self._read()
            if family_id not in data:
                raise ValueError(f"Family {family_id} not found")
            
            # Generate a 6-character alphanumeric code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            
            # Store the join code with expiry
            if "join_codes" not in data[family_id]:
                data[family_id]["join_codes"] = {}
            
            data[family_id]["join_codes"][code] = {
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                "used": False
            }
            
            self._write(data)
            logger.info(f"Generated join code {code} for family {family_id}")
            return code

    def consume_join_code(self, code: str, chat_id: int) -> Optional[FamilyProfile]:
        """Consume a join code and add user to family."""
        with self._lock:
            data = self._read()
            
            # Find the family with this join code
            for family_id, family_data in data.items():
                if "join_codes" in family_data and code in family_data["join_codes"]:
                    join_code_data = family_data["join_codes"][code]
                    
                    # Check if code is expired
                    expires_at = datetime.fromisoformat(join_code_data["expires_at"])
                    if datetime.now() > expires_at:
                        logger.warning(f"Join code {code} expired")
                        return None
                    
                    # Check if code is already used
                    if join_code_data["used"]:
                        logger.warning(f"Join code {code} already used")
                        return None
                    
                    # Mark code as used
                    join_code_data["used"] = True
                    join_code_data["used_by"] = chat_id
                    join_code_data["used_at"] = datetime.now().isoformat()
                    
                    # Add user to family members
                    if "members" not in family_data:
                        family_data["members"] = []
                    
                    if chat_id not in family_data["members"]:
                        family_data["members"].append(chat_id)
                    
                    family_data["updated_at"] = datetime.now().isoformat()
                    
                    self._write(data)
                    logger.info(f"User {chat_id} joined family {family_id} with code {code}")
                    
                    return self.get_family(family_id)
            
            logger.warning(f"Invalid join code: {code}")
            return None

    def cleanup_expired_codes(self) -> None:
        """Clean up expired join codes."""
        with self._lock:
            data = self._read()
            now = datetime.now()
            
            for family_id, family_data in data.items():
                if "join_codes" in family_data:
                    expired_codes = []
                    for code, code_data in family_data["join_codes"].items():
                        expires_at = datetime.fromisoformat(code_data["expires_at"])
                        if now > expires_at:
                            expired_codes.append(code)
                    
                    for code in expired_codes:
                        del family_data["join_codes"][code]
                        logger.info(f"Cleaned up expired join code {code} for family {family_id}")
            
            self._write(data)

    # Legacy methods for backward compatibility
    def add(self, chat_id: int) -> None:
        """Legacy method - add a chat ID to the simple list."""
        with self._lock:
            data = self._read()
            if "legacy_chat_ids" not in data:
                data["legacy_chat_ids"] = []
            
            if int(chat_id) not in data["legacy_chat_ids"]:
                data["legacy_chat_ids"].append(int(chat_id))
                self._write(data)

    def remove(self, chat_id: int) -> None:
        """Legacy method - remove a chat ID from the simple list."""
        with self._lock:
            data = self._read()
            if "legacy_chat_ids" in data and int(chat_id) in data["legacy_chat_ids"]:
                data["legacy_chat_ids"].remove(int(chat_id))
                self._write(data)

    def list(self) -> List[int]:
        """Legacy method - list all chat IDs."""
        with self._lock:
            data = self._read()
            # Safety check: ensure data is a dictionary
            if not isinstance(data, dict):
                logger.warning(f"Families data is not a dictionary: {type(data)}")
                return []
            return data.get("legacy_chat_ids", [])


# Global instance
families = FamiliesStore() 