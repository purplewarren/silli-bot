#!/usr/bin/env python3
"""
Reasoner Smoke Test

This script tests the complete reasoner flow by:
1. Testing reasoner API directly
2. Testing bot's reasoner integration logic
3. Verifying that tips are generated correctly
4. Capturing latency metrics
"""

import json
import time
import asyncio
import aiohttp
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add bot directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class ReasonerSmokeTest:
    """Smoke test for reasoner integration"""
    
    def __init__(self):
        self.reasoner_url = "http://localhost:5001"
        self.family_id = "fam_smoke_test"
        self.test_results = []
        
    async def test_reasoner_directly(self, dyad: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test reasoner API directly
        
        Args:
            dyad: The dyad type (tantrum, meal, night)
            session_data: Session data to test
            
        Returns:
            Test result dictionary
        """
        try:
            # Prepare reasoner request
            req = {
                "dyad": dyad,
                "features": session_data.get("features_summary", {}),
                "context": session_data.get("context", {}),
                "metrics": session_data.get("metrics", {}),
                "history": []
            }
            
            # Call reasoner API
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.post(f"{self.reasoner_url}/v1/reason", json=req) as response:
                    end_time = time.time()
                    latency_ms = int((end_time - start_time) * 1000)
                    
                    if response.status == 200:
                        result = await response.json()
                        tips = result.get("tips", [])
                        rationale = result.get("rationale", "")
                        cache_status = result.get("cache_status", "MISS")
                        
                        print(f"✅ Reasoner API call successful")
                        print(f"📊 Latency: {latency_ms}ms")
                        print(f"🏷️ Cache: {cache_status}")
                        print(f"💡 Tips: {tips}")
                        print(f"🧠 Rationale: {rationale}")
                        
                        return {
                            "success": True,
                            "latency_ms": latency_ms,
                            "tips": tips,
                            "rationale": rationale,
                            "cache_status": cache_status
                        }
                    else:
                        error_text = await response.text()
                        print(f"❌ Reasoner API call failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
                        
        except Exception as e:
            print(f"❌ Error calling reasoner API: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_logs_for_reasoner_usage(self, timeout_seconds: int = 30) -> Optional[int]:
        """
        Check logs for reasoner usage and capture latency
        
        Args:
            timeout_seconds: How long to wait for logs
            
        Returns:
            Latency in milliseconds if found, None otherwise
        """
        try:
            # Look for reasoner usage in recent logs
            log_pattern = "reasoner_call"
            latency_pattern = "latency_ms="
            
            # Check bot logs (assuming they're in logs/silli_bot.log)
            log_file = Path("logs/silli_bot.log")
            if log_file.exists():
                # Read last few lines of log file
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Check last 50 lines for reasoner usage
                    for line in reversed(lines[-50:]):
                        if log_pattern in line:
                            print(f"✅ Found reasoner usage in logs: {line.strip()}")
                            # Extract latency if present
                            if latency_pattern in line:
                                try:
                                    latency_start = line.find(latency_pattern) + len(latency_pattern)
                                    latency_end = line.find(" ", latency_start)
                                    if latency_end == -1:
                                        latency_end = len(line)
                                    latency_ms = int(line[latency_start:latency_end])
                                    print(f"📊 Reasoner latency: {latency_ms}ms")
                                    return latency_ms
                                except (ValueError, IndexError):
                                    pass
                            return 0  # Found usage but no latency info
            
            print("⚠️  No reasoner usage found in logs")
            return None
            
        except Exception as e:
            print(f"❌ Error checking logs: {e}")
            return None

    async def run_smoke_test(self) -> bool:
        """
        Run the complete smoke test
        
        Returns:
            True if all tests pass, False otherwise
        """
        print("🚀 Starting Reasoner Smoke Test")
        print("=" * 50)
        
        # Load test data
        try:
            with open("qa/fake_tantrum_sessions.json", 'r') as f:
                tantrum_sessions = json.load(f)
            
            with open("qa/fake_meal_sessions.json", 'r') as f:
                meal_sessions = json.load(f)
                
        except Exception as e:
            print(f"❌ Error loading test data: {e}")
            return False
        
        # Test 1: Tantrum session
        print("\n🧪 Test 1: Tantrum Session")
        print("-" * 30)
        
        tantrum_session = tantrum_sessions[0].copy()
        tantrum_session["family_id"] = self.family_id
        tantrum_session["session_id"] = f"smoke_tantrum_{int(time.time())}"
        
        result = await self.test_reasoner_directly("tantrum", tantrum_session)
        
        self.test_results.append({
            "test": "tantrum",
            "success": result["success"],
            "latency_ms": result.get("latency_ms"),
            "tips_found": len(result.get("tips", [])) > 0 if result["success"] else False
        })
        
        # Test 2: Meal session
        print("\n🧪 Test 2: Meal Session")
        print("-" * 30)
        
        meal_session = meal_sessions[0].copy()
        meal_session["family_id"] = self.family_id
        meal_session["session_id"] = f"smoke_meal_{int(time.time())}"
        
        result = await self.test_reasoner_directly("meal", meal_session)
        
        self.test_results.append({
            "test": "meal",
            "success": result["success"],
            "latency_ms": result.get("latency_ms"),
            "tips_found": len(result.get("tips", [])) > 0 if result["success"] else False
        })
        
        # Print summary
        print("\n📊 Test Summary")
        print("=" * 50)
        
        all_passed = True
        for result in self.test_results:
            status = "✅ PASS" if result["success"] and result["tips_found"] else "❌ FAIL"
            latency_str = f"{result['latency_ms']}ms" if result['latency_ms'] is not None else "N/A"
            print(f"{result['test'].title()}: {status} (latency: {latency_str})")
            
            if not (result["success"] and result["tips_found"]):
                all_passed = False
        
        print(f"\n🎯 Overall Result: {'✅ PASS' if all_passed else '❌ FAIL'}")
        return all_passed

async def main():
    """Main entry point"""
    smoke_test = ReasonerSmokeTest()
    
    try:
        success = await smoke_test.run_smoke_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 