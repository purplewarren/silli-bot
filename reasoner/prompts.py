#!/usr/bin/env python3
"""
Dyad-specific prompt templates for Silli's reasoning engine
"""

from typing import Literal, Dict, Any, List

def get_prompt(dyad: Literal["night", "tantrum", "meal"]) -> Dict[str, Any]:
    """
    Get dyad-specific prompt template
    
    Args:
        dyad: The dyad type (night, tantrum, meal)
        
    Returns:
        Prompt template with system message, constraints, and few-shot examples
    """
    
    base_system = (
        "You are Silli's reasoning engine. Be calm, brief, practical. "
        "No medical or diagnostic advice. No judgments. Parent-friendly wording."
    )
    
    base_constraints = {
        "tip_words_max": 25,
        "tips_max": 2,
        "tone": "calm, non-anthropomorphic",
        "forbidden": ["medical diagnosis", "threats", "shaming"]
    }
    
    few_shot_examples = {
        "tantrum": [
            {
                "features": {"vad_fraction": 0.7, "flux_norm": 0.6},
                "context": {"trigger": "transition"},
                "out": {
                    "tips": [
                        "Lower your voice and narrate one feeling.",
                        "Offer a small choice (shirt A/B)."
                    ],
                    "rationale": "Likely frustration around change."
                }
            }
        ],
        "meal": [
            {
                "features": {},
                "context": {"eaten_pct": 30, "stress_level": 3},
                "out": {
                    "tips": [
                        "Shrink portions; praise any tasting.",
                        "Keep table uncluttered for one meal."
                    ],
                    "rationale": "Refusal with visual overload."
                }
            }
        ],
        "night": [
            {
                "features": {"vad_fraction": 0.2},
                "context": {},
                "out": {
                    "tips": [
                        "Dim lights and pause screens 20 min.",
                        "Lower room sound—close door slightly."
                    ],
                    "rationale": "Low arousal; environmental tweak helps."
                }
            }
        ]
    }
    
    return {
        "system": base_system,
        "constraints": base_constraints,
        "few_shot": few_shot_examples[dyad]
    } 