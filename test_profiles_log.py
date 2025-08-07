#!/usr/bin/env python3
"""
Test for Family Profiles JSONL logging
"""

import json
from bot.profiles import ProfilesStore, FamilyProfile
from datetime import datetime


def test_profiles_log():
    """Test the JSONL logging functionality."""
    print("🧪 Testing Family Profiles JSONL Logging")
    print("=" * 50)
    
    # Create store
    store = ProfilesStore()
    
    # Test 1: Create a profile manually
    print("\n1. Creating profile manually...")
    profile = FamilyProfile(
        family_id="fam_999",
        creator_chat_id=999,
        members=[999],
        parent_name="Test Parent",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Test 2: Append to log
    print("\n2. Appending events to JSONL log...")
    events = [
        {
            'type': 'UPSERT_PROFILE',
            'payload': profile.dict()
        },
        {
            'type': 'SET_FIELDS',
            'family_id': 'fam_999',
            'payload': {'parent_name': 'Updated Parent'}
        },
        {
            'type': 'ADD_MEMBER',
            'family_id': 'fam_999',
            'chat_id': 888
        }
    ]
    
    for event in events:
        store._append_log(event)
        print(f"✅ Appended: {event['type']}")
    
    # Test 3: Check if log file was created
    print("\n3. Checking JSONL log file...")
    if store.profiles_log_path.exists():
        print(f"✅ Log file created: {store.profiles_log_path}")
        with open(store.profiles_log_path, 'r') as f:
            lines = f.readlines()
            print(f"   Lines in log: {len(lines)}")
            for i, line in enumerate(lines):
                event = json.loads(line)
                print(f"   Line {i+1}: {event['type']} at {event['ts']}")
    else:
        print("❌ Log file not created")
    
    print("\n🎉 JSONL logging test completed!")


if __name__ == "__main__":
    test_profiles_log() 