#!/usr/bin/env python3
"""
Smoke test script for Silli Bot
"""

import sys
from pathlib import Path
from datetime import datetime

# Add bot module to path
sys.path.append(str(Path(__file__).parent.parent))

from bot.models import EventRecord, FeatureSummary
from bot.storage import Storage
from bot.cards import create_sample_card


def test_event_append():
    """Test EventRecord append functionality."""
    print("Testing EventRecord append...")
    
    # Create storage instance
    storage = Storage()
    
    # Create sample event
    event = EventRecord(
        ts=datetime.now(),
        family_id="fam_test_001",
        session_id="fam_test_001_20250101_120000",
        phase="test",
        actor="system",
        event="smoke_test",
        labels=["test", "smoke"],
        features=FeatureSummary(
            level_dbfs=-25.0,
            centroid_norm=0.4,
            rolloff_norm=0.5,
            flux_norm=0.2,
            vad_fraction=0.3,
            stationarity=0.8
        ),
        score=75,
        suggestion_id="wind_down_v1"
    )
    
    # Append event
    storage.append_event(event)
    
    # Check if file was created
    events_file = storage.get_events_file_path()
    if events_file.exists():
        count = storage.get_events_count()
        print(f"✅ Event appended successfully. Total events: {count}")
        return True
    else:
        print("❌ Event file not created")
        return False


def test_card_rendering():
    """Test PNG card rendering."""
    print("Testing PNG card rendering...")
    
    try:
        # Create sample card
        card_path = create_sample_card()
        
        if card_path.exists():
            print(f"✅ Sample card created: {card_path}")
            return True
        else:
            print("❌ Sample card not created")
            return False
            
    except Exception as e:
        print(f"❌ Card rendering failed: {e}")
        return False


def main():
    """Run smoke tests."""
    print("🚀 Running Silli Bot smoke tests...\n")
    
    # Test event append
    event_success = test_event_append()
    
    print()
    
    # Test card rendering
    card_success = test_card_rendering()
    
    print()
    
    # Summary
    if event_success and card_success:
        print("✅ All smoke tests passed!")
        return 0
    else:
        print("❌ Some smoke tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 