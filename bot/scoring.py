"""
Wind-Down scoring system for audio analysis.
Rule-based scoring with configurable weights and badge/tip mapping.
"""

import json
import os
from typing import List, Tuple, Dict, Any
from loguru import logger
from .models import FeatureSummary


class WindDownScorer:
    """Rule-based scorer for Wind-Down analysis."""
    
    def __init__(self, weights_file: str = "weights.json"):
        self.weights_file = weights_file
        self.weights = self._load_weights()
        self.tips = self._load_tips()
    
    def _load_weights(self) -> Dict[str, float]:
        """Load scoring weights from file or use defaults."""
        try:
            if os.path.exists(self.weights_file):
                with open(self.weights_file, 'r') as f:
                    weights = json.load(f)
                logger.info(f"Loaded weights from {self.weights_file}")
                return weights
            else:
                # Default weights
                weights = {
                    "w1_vad": 35.0,
                    "w2_flux": 25.0,
                    "w3_centroid": 20.0,
                    "w4_level": 20.0,
                    "w5_steady_bonus": 15.0
                }
                logger.info("Weights file not found, using defaults")
                return weights
        except Exception as e:
            logger.error(f"Error loading weights: {e}")
            return {
                "w1_vad": 35.0,
                "w2_flux": 25.0,
                "w3_centroid": 20.0,
                "w4_level": 20.0,
                "w5_steady_bonus": 15.0
            }
    
    def _load_tips(self) -> Dict[str, str]:
        """Load tips from file or use defaults."""
        try:
            tips_file = "tips.json"
            if os.path.exists(tips_file):
                with open(tips_file, 'r') as f:
                    tips = json.load(f)
                logger.info(f"Loaded tips from {tips_file}")
                return tips
            else:
                # Default tips
                tips = {
                    "quiet_minute": "Quiet minute + 4-7-8 breathing; speak softer than a whisper.",
                    "dim_lights": "Dim lights to warm (~1800K); hide bright screens.",
                    "white_noise": "Use gentle white noise; keep level below conversation loudness.",
                    "lullaby_pacing": "Lullaby pacing ~60–70 BPM; mirror child, then fade."
                }
                logger.info("Tips file not found, using defaults")
                return tips
        except Exception as e:
            logger.error(f"Error loading tips: {e}")
            return {
                "quiet_minute": "Quiet minute + 4-7-8 breathing; speak softer than a whisper.",
                "dim_lights": "Dim lights to warm (~1800K); hide bright screens.",
                "white_noise": "Use gentle white noise; keep level below conversation loudness.",
                "lullaby_pacing": "Lullaby pacing ~60–70 BPM; mirror child, then fade."
            }
    
    def calculate_score(self, features: FeatureSummary) -> int:
        """Calculate Wind-Down Score (0-100)."""
        try:
            # Normalize level_dbfs to 0-1 range
            norm_level = max(0, min(1, (features.level_dbfs + 60) / 60))
            
            # Calculate steady noise bonus
            steady_bonus = 0
            if (features.flux_norm < 0.12 and 
                -40 <= features.level_dbfs <= -25):
                steady_bonus = self.weights["steady_bonus"]
            
            # Calculate score
            score = 100
            score -= self.weights["w1_vad"] * features.vad_fraction
            score -= self.weights["w2_flux"] * features.flux_norm
            score -= self.weights["w3_centroid"] * features.centroid_norm
            score -= self.weights["w4_level"] * norm_level
            score += steady_bonus
            
            # Clamp to 0-100
            score = max(0, min(100, int(score)))
            
            logger.info(f"Calculated score: {score} (vad={features.vad_fraction:.2f}, "
                       f"flux={features.flux_norm:.2f}, centroid={features.centroid_norm:.2f}, "
                       f"level={norm_level:.2f}, bonus={steady_bonus})")
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return 50  # Default middle score
    
    def determine_badges(self, features: FeatureSummary) -> List[str]:
        """Determine badges based on audio features."""
        badges = []
        
        try:
            # Speech present
            if features.vad_fraction > 0.22:
                badges.append("Speech present")
            
            # Music/TV present
            if features.centroid_norm > 0.55 and features.flux_norm > 0.25:
                badges.append("Music/TV present")
            
            # Fluctuating
            elif features.flux_norm > 0.25:
                badges.append("Fluctuating")
            
            # Steady (default)
            else:
                badges.append("Steady")
            
            logger.info(f"Determined badges: {badges}")
            return badges
            
        except Exception as e:
            logger.error(f"Error determining badges: {e}")
            return ["Steady"]
    
    def select_tips(self, score: int, badges: List[str]) -> List[str]:
        """Select 2-3 tips based on score and badges."""
        try:
            selected_tips = []
            
            # Always include quiet minute for low scores
            if score < 60:
                selected_tips.append(self.tips["quiet_minute"])
            
            # Include dim lights for most cases
            if score < 80:
                selected_tips.append(self.tips["dim_lights"])
            
            # Include white noise for steady environments
            if "Steady" in badges and score < 70:
                selected_tips.append(self.tips["white_noise"])
            
            # Include lullaby pacing for speech present
            if "Speech present" in badges:
                selected_tips.append(self.tips["lullaby_pacing"])
            
            # Ensure we have 2-3 tips
            if len(selected_tips) < 2:
                if score < 70:
                    selected_tips.append(self.tips["white_noise"])
                else:
                    selected_tips.append(self.tips["dim_lights"])
            
            # Limit to 3 tips
            selected_tips = selected_tips[:3]
            
            logger.info(f"Selected tips: {selected_tips}")
            return selected_tips
            
        except Exception as e:
            logger.error(f"Error selecting tips: {e}")
            return [self.tips["dim_lights"], self.tips["quiet_minute"]]
    
    def score_and_tips(self, features: FeatureSummary) -> Tuple[int, List[str], List[str]]:
        """Calculate score, badges, and tips for audio features."""
        score = self.calculate_score(features)
        badges = self.determine_badges(features)
        tips = self.select_tips(score, badges)
        
        return score, badges, tips 