"""
Storage module for Silli Bot - JSONL append and CSV roll-up
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger
from .models import EventRecord, SessionRecord


class Storage:
    """Storage manager for events and sessions."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.events_file = data_dir / "events.jsonl"
        self.sessions_file = data_dir / "sessions.csv"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize sessions CSV if it doesn't exist
        if not self.sessions_file.exists():
            self._init_sessions_csv()
    
    def _init_sessions_csv(self):
        """Initialize sessions CSV with headers."""
        headers = [
            "family_id", "session_id", "date", "phase", "start_ts", "end_ts",
            "time_to_calm_min", "adoption_rate", "helpfulness_1to7", "privacy_1to7", "notes"
        ]
        
        with open(self.sessions_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        logger.info(f"Initialized sessions CSV: {self.sessions_file}")
    
    def append_event(self, event: EventRecord) -> None:
        """Append event to JSONL file with safe writing."""
        try:
            # Convert to dict and handle datetime serialization
            event_dict = event.model_dump()
            event_dict['ts'] = event_dict['ts'].isoformat()
            
            # Append to JSONL file
            with open(self.events_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_dict) + '\n')
                f.flush()  # Ensure immediate write
            
            logger.info(f"Appended event: {event.event} for family {event.family_id}")
            
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            raise
    
    def rollup_session(self, session_record: SessionRecord) -> None:
        """Roll up session data to CSV (stub implementation)."""
        try:
            # Convert to dict for CSV writing
            session_dict = session_record.model_dump()
            
            # Handle datetime serialization
            if session_dict.get('start_ts'):
                session_dict['start_ts'] = session_dict['start_ts'].isoformat()
            if session_dict.get('end_ts'):
                session_dict['end_ts'] = session_dict['end_ts'].isoformat()
            
            # Append to CSV
            with open(self.sessions_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=session_dict.keys())
                writer.writerow(session_dict)
            
            logger.info(f"Rolled up session: {session_record.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to rollup session: {e}")
            raise
    
    def get_events_file_path(self) -> Path:
        """Get path to events JSONL file."""
        return self.events_file
    
    def get_sessions_file_path(self) -> Path:
        """Get path to sessions CSV file."""
        return self.sessions_file
    
    def get_events_count(self) -> int:
        """Get count of events in JSONL file."""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except FileNotFoundError:
            return 0
    
    def get_events(self, family_id: str) -> list[EventRecord]:
        """Get all events for a specific family."""
        events = []
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        event_dict = json.loads(line)
                        # Convert ISO string back to datetime
                        if 'ts' in event_dict:
                            event_dict['ts'] = datetime.fromisoformat(event_dict['ts'])
                        event = EventRecord(**event_dict)
                        if event.family_id == family_id:
                            events.append(event)
        except FileNotFoundError:
            logger.info(f"No events file found for family {family_id}")
        except Exception as e:
            logger.error(f"Error reading events for family {family_id}: {e}")
        
        return events 