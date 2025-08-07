#!/usr/bin/env python3
"""
Test script for reasoner client
Tests the integration between bot and reasoner
"""

import asyncio
import os
from dotenv import load_dotenv
from .reason_client import ReasonClient, create_reasoner_config, get_reasoning_insights

# Load environment variables
load_dotenv()

async def test_reasoner_client():
    """Test the reasoner client functionality"""
    print("🧪 Testing Reasoner Client")
    print("=" * 40)
    
    # Create config
    config = create_reasoner_config()
    print(f"Config: enabled={config.enabled}, base_url={config.base_url}")
    
    if not config.enabled:
        print("❌ Reasoner is disabled in config")
        return False
    
    # Test health check
    print("\n🔍 Testing health check...")
    try:
        async with ReasonClient(config.base_url, config.timeout_s) as client:
            health = await client.health_check()
            print(f"Health check: {'✅' if health else '❌'}")
            
            if not health:
                print("❌ Reasoner is not healthy")
                return False
            
            # Test inference
            print("\n🧠 Testing inference...")
            test_payload = {
                "dyad": "tantrum",
                "features": {
                    "vad_fraction": 0.45,
                    "flux_norm": 0.32
                },
                "context": {
                    "trigger": "transition",
                    "duration_min": 4
                },
                "metrics": {
                    "escalation_index": 0.65
                },
                "history": []
            }
            
            response = await client.infer(test_payload)
            print(f"✅ Inference successful")
            print(f"   Tips: {response.get('tips', [])}")
            print(f"   Rationale: {response.get('rationale', '')}")
            print(f"   Response time: {response.get('response_time', 0)}s")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_convenience_function():
    """Test the convenience function"""
    print("\n🧪 Testing convenience function...")
    
    config = create_reasoner_config()
    
    if not config.enabled:
        print("❌ Reasoner is disabled")
        return False
    
    try:
        response = await get_reasoning_insights(
            dyad="meal",
            features={
                "dietary_diversity": 0.75,
                "clutter_score": 0.25
            },
            context={
                "meal_type": "lunch",
                "eaten_pct": 85
            },
            metrics={
                "meal_mood": 82
            },
            history=[],
            config=config
        )
        
        if response:
            print(f"✅ Convenience function successful")
            print(f"   Tips: {response.get('tips', [])}")
            return True
        else:
            print("❌ Convenience function returned None")
            return False
            
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Reasoner Client Test Suite")
    print("=" * 50)
    
    # Test basic client
    client_success = await test_reasoner_client()
    
    # Test convenience function
    convenience_success = await test_convenience_function()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"Client Test: {'✅ PASS' if client_success else '❌ FAIL'}")
    print(f"Convenience Test: {'✅ PASS' if convenience_success else '❌ FAIL'}")
    
    if client_success and convenience_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main())) 