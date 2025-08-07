#!/usr/bin/env python3
"""
Unit tests for reasoner merge functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.reason_client import clamp_metric_overrides, truncate_tips

def test_clamp_metric_overrides():
    """Test metric overrides clamping"""
    print("🧪 Testing metric overrides clamping...")
    
    # Test escalation_index clamping
    overrides = {"escalation_index": 1.5}  # Should be clamped to 1.0
    clamped = clamp_metric_overrides(overrides)
    assert clamped["escalation_index"] == 1.0
    
    overrides = {"escalation_index": -0.5}  # Should be clamped to 0.0
    clamped = clamp_metric_overrides(overrides)
    assert clamped["escalation_index"] == 0.0
    
    overrides = {"escalation_index": 0.75}  # Should remain 0.75
    clamped = clamp_metric_overrides(overrides)
    assert clamped["escalation_index"] == 0.75
    
    # Test meal_mood clamping
    overrides = {"meal_mood": 150.0}  # Should be clamped to 100.0
    clamped = clamp_metric_overrides(overrides)
    assert clamped["meal_mood"] == 100.0
    
    overrides = {"meal_mood": -25.0}  # Should be clamped to 0.0
    clamped = clamp_metric_overrides(overrides)
    assert clamped["meal_mood"] == 0.0
    
    overrides = {"meal_mood": 85.5}  # Should remain 85.5
    clamped = clamp_metric_overrides(overrides)
    assert clamped["meal_mood"] == 85.5
    
    # Test multiple metrics
    overrides = {
        "escalation_index": 1.2,
        "meal_mood": 120.0
    }
    clamped = clamp_metric_overrides(overrides)
    assert clamped["escalation_index"] == 1.0
    assert clamped["meal_mood"] == 100.0
    
    # Test unknown metrics (should be ignored)
    overrides = {
        "escalation_index": 0.5,
        "unknown_metric": 999.0
    }
    clamped = clamp_metric_overrides(overrides)
    assert clamped["escalation_index"] == 0.5
    assert "unknown_metric" not in clamped
    
    print("✅ metric overrides clamping test passed")

def test_truncate_tips():
    """Test tip truncation"""
    print("\n🧪 Testing tip truncation...")
    
    # Test short tips (no truncation needed)
    tips = ["Try reducing ambient noise"]
    truncated = truncate_tips(tips, max_words=25)
    assert truncated == ["Try reducing ambient noise"]
    
    # Test long tip (truncation needed)
    long_tip = "Based on the audio analysis, I recommend trying a white noise machine and ensuring the room temperature is comfortable while also checking if there are any external sounds that might be disturbing the sleep environment"
    tips = [long_tip]
    truncated = truncate_tips(tips, max_words=25)
    assert len(truncated) == 1
    assert truncated[0].endswith("...")
    # Count words excluding ellipsis
    words = truncated[0].replace("...", "").split()
    assert len(words) == 25
    
    # Test multiple tips
    tips = [
        "Short tip",
        "This is a very long tip that should be truncated because it exceeds the maximum word limit and needs to be shortened to fit properly in the display",
        "Another short tip"
    ]
    truncated = truncate_tips(tips, max_words=10)
    assert len(truncated) == 3
    assert truncated[0] == "Short tip"
    assert truncated[1].endswith("...")
    # Count words excluding ellipsis
    words = truncated[1].replace("...", "").split()
    assert len(words) == 10
    assert truncated[2] == "Another short tip"
    
    # Test empty and invalid tips
    tips = ["", None, "Valid tip", "   "]
    truncated = truncate_tips(tips, max_words=25)
    assert truncated == ["Valid tip"]  # Only valid tips should remain
    
    # Test edge case: exactly at word limit
    exact_tip = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive"
    tips = [exact_tip]
    truncated = truncate_tips(tips, max_words=25)
    assert len(truncated) == 1
    assert len(truncated[0].split()) == 25  # Should not add ellipsis
    assert not truncated[0].endswith("...")  # Should not have ellipsis
    
    print("✅ tip truncation test passed")

def main():
    """Run all reasoner merge tests"""
    print("🚀 Reasoner Merge Test Suite")
    print("=" * 40)
    
    try:
        test_clamp_metric_overrides()
        test_truncate_tips()
        
        print("\n🎉 All reasoner merge tests passed!")
        print("\n📋 Hardening Summary:")
        print("✅ Metric overrides clamped to valid ranges")
        print("✅ Tips truncated to 25 words maximum")
        print("✅ Edge cases handled properly")
        print("✅ Invalid inputs filtered out")
        
        return 0
        
    except Exception as e:
        print(f"\n💥 Reasoner merge test failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 