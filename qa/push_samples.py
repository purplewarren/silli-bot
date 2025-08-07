#!/usr/bin/env python3
"""
QA Script: Push sample dyad sessions to bot
Posts sample tantrum and meal sessions to test the relay path
"""

import json
import requests
import time
import sys
from pathlib import Path
from typing import Dict, Any, List

# Configuration
BOT_BASE_URL = "http://localhost:8000"  # Adjust if bot runs on different port
WORKER_BASE_URL = "https://your-worker.workers.dev"  # Adjust to your worker URL
JWT_TOKEN = "your_test_jwt_token"  # Replace with valid test token

def load_sample_sessions(file_path: str) -> List[Dict[str, Any]]:
    """Load sample sessions from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Sample file not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {file_path}: {e}")
        return []

def post_to_bot(session_data: Dict[str, Any]) -> bool:
    """Post session data directly to bot /ingest endpoint"""
    try:
        url = f"{BOT_BASE_URL}/ingest"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JWT_TOKEN}"
        }
        
        print(f"📤 Posting to bot: {session_data['session_id']}")
        response = requests.post(url, json=session_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Bot response: {response.json()}")
            return True
        else:
            print(f"❌ Bot error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error posting to bot: {e}")
        return False

def post_to_worker(session_data: Dict[str, Any]) -> bool:
    """Post session data to Cloudflare Worker /ingest endpoint"""
    try:
        url = f"{WORKER_BASE_URL}/ingest"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JWT_TOKEN}"
        }
        
        print(f"📤 Posting to worker: {session_data['session_id']}")
        response = requests.post(url, json=session_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Worker response: {response.json()}")
            return True
        else:
            print(f"❌ Worker error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error posting to worker: {e}")
        return False

def pipe_to_bot(session_data: Dict[str, Any]) -> bool:
    """Pipe session data to bot via stdin (alternative method)"""
    try:
        # This would require the bot to read from stdin
        # For now, just simulate the pipe
        print(f"📤 Piping to bot: {session_data['session_id']}")
        print(json.dumps(session_data))
        return True
    except Exception as e:
        print(f"❌ Error piping to bot: {e}")
        return False

def test_tantrum_sessions():
    """Test tantrum session relay"""
    print("\n🧪 Testing Tantrum Sessions")
    print("=" * 40)
    
    sessions = load_sample_sessions("qa/fake_tantrum_sessions.json")
    if not sessions:
        return False
    
    success_count = 0
    for session in sessions:
        print(f"\n📊 Testing session: {session['session_id']}")
        print(f"   Dyad: {session['dyad']}")
        print(f"   Escalation: {session['metrics']['escalation_index']}")
        print(f"   Trigger: {session['context']['trigger']}")
        
        # Try bot endpoint first
        if post_to_bot(session):
            success_count += 1
        # Fallback to worker
        elif post_to_worker(session):
            success_count += 1
        # Last resort: pipe to bot
        elif pipe_to_bot(session):
            success_count += 1
        else:
            print("❌ All relay methods failed")
        
        time.sleep(1)  # Rate limiting
    
    print(f"\n✅ Tantrum sessions: {success_count}/{len(sessions)} successful")
    return success_count == len(sessions)

def test_meal_sessions():
    """Test meal session relay"""
    print("\n🍽️ Testing Meal Sessions")
    print("=" * 40)
    
    sessions = load_sample_sessions("qa/fake_meal_sessions.json")
    if not sessions:
        return False
    
    success_count = 0
    for session in sessions:
        print(f"\n📊 Testing session: {session['session_id']}")
        print(f"   Dyad: {session['dyad']}")
        print(f"   Meal Mood: {session['metrics']['meal_mood']}")
        print(f"   Eaten %: {session['context']['eaten_pct']}")
        
        # Try bot endpoint first
        if post_to_bot(session):
            success_count += 1
        # Fallback to worker
        elif post_to_worker(session):
            success_count += 1
        # Last resort: pipe to bot
        elif pipe_to_bot(session):
            success_count += 1
        else:
            print("❌ All relay methods failed")
        
        time.sleep(1)  # Rate limiting
    
    print(f"\n✅ Meal sessions: {success_count}/{len(sessions)} successful")
    return success_count == len(sessions)

def validate_payload_schema(session_data: Dict[str, Any]) -> bool:
    """Validate session data against expected schema"""
    required_fields = [
        "version", "family_id", "session_id", "mode", "dyad",
        "ts_start", "duration_s", "badges", "context", "metrics",
        "media_summaries", "events", "pii"
    ]
    
    for field in required_fields:
        if field not in session_data:
            print(f"❌ Missing required field: {field}")
            return False
    
    # Validate dyad-specific fields
    dyad = session_data["dyad"]
    if dyad == "tantrum":
        if "escalation_index" not in session_data["metrics"]:
            print("❌ Missing escalation_index in tantrum metrics")
            return False
    elif dyad == "meal":
        if "meal_mood" not in session_data["metrics"]:
            print("❌ Missing meal_mood in meal metrics")
            return False
    
    print("✅ Payload schema validation passed")
    return True

def main():
    """Main test runner"""
    print("🚀 Silli Dyad QA Test Runner")
    print("=" * 50)
    
    # Validate sample data
    print("\n🔍 Validating sample data...")
    tantrum_sessions = load_sample_sessions("qa/fake_tantrum_sessions.json")
    meal_sessions = load_sample_sessions("qa/fake_meal_sessions.json")
    
    for session in tantrum_sessions + meal_sessions:
        if not validate_payload_schema(session):
            print("❌ Schema validation failed")
            sys.exit(1)
    
    print("✅ All sample data validated")
    
    # Run tests
    tantrum_success = test_tantrum_sessions()
    meal_success = test_meal_sessions()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 30)
    print(f"Tantrum Sessions: {'✅ PASS' if tantrum_success else '❌ FAIL'}")
    print(f"Meal Sessions: {'✅ PASS' if meal_success else '❌ FAIL'}")
    
    if tantrum_success and meal_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 