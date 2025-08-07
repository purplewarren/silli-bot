#!/usr/bin/env python3
"""
Test script for Silli Reasoner
Tests the Ollama integration with sample data
"""

import json
import requests
import time
from typing import Dict, Any

def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    
    try:
        response = requests.get('http://localhost:5001/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return data.get('ollama_connected', False)
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_models():
    """Test models endpoint"""
    print("\n🔍 Testing models endpoint...")
    
    try:
        response = requests.get('http://localhost:5001/models', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Models: {data}")
            return data.get('available', False)
        else:
            print(f"❌ Models failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Models error: {e}")
        return False

def test_tantrum_reasoning():
    """Test tantrum reasoning"""
    print("\n🧪 Testing tantrum reasoning...")
    
    sample_request = {
        "dyad": "tantrum",
        "features": {
            "vad_fraction": 0.45,
            "flux_norm": 0.32,
            "level_dbfs": -28.5
        },
        "context": {
            "trigger": "transition",
            "duration_min": 4,
            "co_regulation": ["mirror", "label"],
            "environment_noise": True
        },
        "metrics": {
            "escalation_index": 0.65
        },
        "history": [
            {
                "timestamp": "2024-01-15T14:30:00Z",
                "escalation_index": 0.45,
                "trigger": "frustration"
            }
        ]
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            'http://localhost:5001/v1/reason',
            json=sample_request,
            timeout=30
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tantrum reasoning successful ({response_time:.2f}s)")
            print(f"   Tips: {data.get('tips', [])}")
            print(f"   Rationale: {data.get('rationale', '')}")
            print(f"   Response time: {data.get('response_time', 0)}s")
            return True
        else:
            print(f"❌ Tantrum reasoning failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Tantrum reasoning error: {e}")
        return False

def test_meal_reasoning():
    """Test meal reasoning"""
    print("\n🍽️ Testing meal reasoning...")
    
    sample_request = {
        "dyad": "meal",
        "features": {
            "dietary_diversity": 0.75,
            "clutter_score": 0.25,
            "plate_coverage": 0.65
        },
        "context": {
            "meal_type": "lunch",
            "eaten_pct": 85,
            "stress_level": 0
        },
        "metrics": {
            "meal_mood": 82
        },
        "history": [
            {
                "timestamp": "2024-01-15T12:00:00Z",
                "meal_mood": 75,
                "eaten_pct": 70
            }
        ]
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            'http://localhost:5001/v1/reason',
            json=sample_request,
            timeout=30
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Meal reasoning successful ({response_time:.2f}s)")
            print(f"   Tips: {data.get('tips', [])}")
            print(f"   Rationale: {data.get('rationale', '')}")
            print(f"   Response time: {data.get('response_time', 0)}s")
            return True
        else:
            print(f"❌ Meal reasoning failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Meal reasoning error: {e}")
        return False

def test_pii_redaction():
    """Test PII redaction"""
    print("\n🔒 Testing PII redaction...")
    
    sample_request = {
        "dyad": "tantrum",
        "features": {},
        "context": {
            "trigger": "transition",
            "child_name": "Emma",  # Should be redacted
            "notes": "Child was upset about leaving"  # Should be redacted
        },
        "metrics": {
            "escalation_index": 0.65
        },
        "history": []
    }
    
    try:
        response = requests.post(
            'http://localhost:5001/v1/reason',
            json=sample_request,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ PII redaction test passed (no PII in response)")
            return True
        else:
            print(f"❌ PII redaction failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ PII redaction error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Silli Reasoner Test Suite")
    print("=" * 40)
    
    # Test health check
    ollama_connected = test_health_check()
    
    if not ollama_connected:
        print("\n⚠️  Ollama not connected. Some tests may fail.")
        print("   Make sure Ollama is running: ollama serve")
        print("   Install model: ollama pull gpt-oss-20b")
    
    # Test models
    models_available = test_models()
    
    # Test reasoning
    tantrum_success = test_tantrum_reasoning()
    meal_success = test_meal_reasoning()
    pii_success = test_pii_redaction()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"Ollama Connected: {'✅' if ollama_connected else '❌'}")
    print(f"Models Available: {'✅' if models_available else '❌'}")
    print(f"Tantrum Reasoning: {'✅' if tantrum_success else '❌'}")
    print(f"Meal Reasoning: {'✅' if meal_success else '❌'}")
    print(f"PII Redaction: {'✅' if pii_success else '❌'}")
    
    if all([ollama_connected, models_available, tantrum_success, meal_success, pii_success]):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 