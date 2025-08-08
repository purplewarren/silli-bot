"""
Test audio analysis functionality
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Add bot module to path
sys.path.append(str(Path(__file__).parent.parent))

from bot.analysis_audio import extract_features
from bot.scoring import wind_down_scorer


def create_test_wav():
    """Create a tiny WAV fixture for testing."""
    # Create a simple test audio (1 second of 440Hz sine wave)
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = 0.1 * np.sin(2 * np.pi * frequency * t)  # Low amplitude sine wave
    
    # Save as WAV
    test_wav_path = Path("tests/test_audio.wav")
    test_wav_path.parent.mkdir(exist_ok=True)
    
    sf.write(test_wav_path, audio, sample_rate)
    return test_wav_path


def test_extract_features():
    """Test feature extraction from WAV file."""
    print("Testing feature extraction...")
    
    # Create test WAV
    wav_path = create_test_wav()
    
    try:
        # Extract features
        features = extract_features(wav_path)
        
        # Check that all required fields are present
        required_fields = [
            'level_dbfs', 'centroid_norm', 'rolloff_norm', 
            'flux_norm', 'vad_fraction', 'stationarity'
        ]
        
        for field in required_fields:
            assert hasattr(features, field), f"Missing field: {field}"
            value = getattr(features, field)
            assert isinstance(value, (int, float)), f"Field {field} is not numeric: {value}"
        
        print(f"✅ Features extracted successfully:")
        print(f"   level_dbfs: {features.level_dbfs}")
        print(f"   centroid_norm: {features.centroid_norm}")
        print(f"   rolloff_norm: {features.rolloff_norm}")
        print(f"   flux_norm: {features.flux_norm}")
        print(f"   vad_fraction: {features.vad_fraction}")
        print(f"   stationarity: {features.stationarity}")
        
        return features
        
    except Exception as e:
        print(f"❌ Feature extraction failed: {e}")
        raise
    finally:
        # Clean up test file
        if wav_path.exists():
            wav_path.unlink()


def test_score_and_tips(features):
    """Test scoring and tips generation."""
    print("Testing score and tips...")
    
    try:
        # Calculate score and tips
        score, badges, tips = wind_down_scorer.score_and_tips(features)
        
        # Check score range
        assert 0 <= score <= 100, f"Score out of range: {score}"
        
        # Check that we have some output
        assert isinstance(badges, list), "Badges should be a list"
        assert isinstance(tips, list), "Tips should be a list"
        assert len(tips) > 0, "Should have at least one tip"
        
        print(f"✅ Score and tips generated successfully:")
        print(f"   Score: {score}/100")
        print(f"   Badges: {badges}")
        print(f"   Tips: {tips}")
        
        return True
        
    except Exception as e:
        print(f"❌ Score and tips failed: {e}")
        raise


def main():
    """Run audio analysis tests."""
    print("🎵 Running audio analysis tests...\n")
    
    try:
        # Test feature extraction
        features = test_extract_features()
        
        print()
        
        # Test scoring and tips
        test_score_and_tips(features)
        
        print("\n✅ All audio analysis tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Audio analysis tests failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 