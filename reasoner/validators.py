#!/usr/bin/env python3
"""
Post-response validator for reasoning responses
Ensures output meets constraints and safety requirements
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validation with cleaned data"""
    tips: List[str]
    rationale: str
    metric_overrides: Optional[Dict[str, float]]
    is_valid: bool
    warnings: List[str]

def strip_emojis_except_simple(text: str) -> str:
    """
    Strip emojis except simple ones (basic emoticons)
    
    Args:
        text: Input text
        
    Returns:
        Text with complex emojis removed
    """
    # Keep simple emoticons: :) :( :D :P etc.
    simple_emoticons = r'[:;=]-?[)(DPp]'
    
    # Remove complex emojis (Unicode emoji ranges)
    # This covers most emoji ranges
    emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F]'  # Emoticons
        r'|[\U0001F300-\U0001F5FF]'  # Misc symbols & pictographs
        r'|[\U0001F680-\U0001F6FF]'  # Transport & map symbols
        r'|[\U0001F1E0-\U0001F1FF]'  # Flags
        r'|[\U00002600-\U000027BF]'  # Misc symbols
        r'|[\U0001F900-\U0001F9FF]'  # Supplemental symbols
        r'|[\U0001FA70-\U0001FAFF]'  # Symbols and pictographs extended-A
        r'|[\U0001FAB0-\U0001FABF]'  # Symbols and pictographs extended-B
        r'|[\U0001FAC0-\U0001FAFF]'  # Symbols and pictographs extended-C
        r'|[\U0001FAD0-\U0001FAFF]'  # Symbols and pictographs extended-D
        r'|[\U0001FAE0-\U0001FAFF]'  # Symbols and pictographs extended-E
        r'|[\U0001FAF0-\U0001FAFF]'  # Symbols and pictographs extended-F
    )
    
    # Remove complex emojis
    cleaned = emoji_pattern.sub('', text)
    
    # Preserve simple emoticons
    return cleaned

def remove_urls(text: str) -> str:
    """
    Remove URLs from text
    
    Args:
        text: Input text
        
    Returns:
        Text with URLs removed
    """
    # URL pattern - matches http/https URLs
    url_pattern = re.compile(
        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
        re.IGNORECASE
    )
    
    return url_pattern.sub('', text)

def check_profanity(text: str) -> bool:
    """
    Basic profanity check using blocklist
    
    Args:
        text: Text to check
        
    Returns:
        True if profanity found, False otherwise
    """
    # Basic profanity blocklist (add more as needed)
    profanity_words = {
        'fuck', 'shit', 'damn', 'bitch', 'ass', 'piss', 'cock', 'dick', 'pussy',
        'cunt', 'whore', 'slut', 'bastard', 'motherfucker', 'fucker', 'shitty',
        'fucking', 'shitting', 'damned', 'asshole', 'dumbass', 'jackass'
    }
    
    # Convert to lowercase and split into words
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Check for profanity
    for word in words:
        if word in profanity_words:
            return True
    
    return False

def clamp_metric_overrides(overrides: Dict[str, float]) -> Dict[str, float]:
    """
    Clamp metric overrides to valid ranges
    
    Args:
        overrides: Metric overrides dictionary
        
    Returns:
        Clamped metric overrides
    """
    clamped = {}
    
    for key, value in overrides.items():
        try:
            if key == 'escalation_index':
                clamped[key] = max(0.0, min(1.0, float(value)))
            elif key == 'meal_mood':
                clamped[key] = max(0.0, min(100.0, float(value)))
            else:
                # Keep other metrics as-is
                clamped[key] = value
        except (ValueError, TypeError):
            # Skip invalid values
            continue
    
    return clamped

def validate_tips(tips: List[str]) -> List[str]:
    """
    Validate and clean tips
    
    Args:
        tips: List of tips
        
    Returns:
        Cleaned and validated tips
    """
    validated_tips = []
    warnings = []
    
    for i, tip in enumerate(tips):
        if not isinstance(tip, str):
            warnings.append(f"Tip {i+1}: Not a string, skipping")
            continue
        
        # Clean the tip
        cleaned_tip = tip.strip()
        
        # Remove URLs
        cleaned_tip = remove_urls(cleaned_tip)
        
        # Strip complex emojis
        cleaned_tip = strip_emojis_except_simple(cleaned_tip)
        
        # Check for profanity
        if check_profanity(cleaned_tip):
            warnings.append(f"Tip {i+1}: Profanity detected, skipping")
            continue
        
        # Check word limit
        words = cleaned_tip.split()
        if len(words) > 25:
            # Truncate to 25 words
            cleaned_tip = ' '.join(words[:25]) + '...'
            warnings.append(f"Tip {i+1}: Truncated to 25 words")
        
        # Skip empty tips
        if not cleaned_tip.strip():
            warnings.append(f"Tip {i+1}: Empty after cleaning, skipping")
            continue
        
        validated_tips.append(cleaned_tip)
        
        # Limit to 2 tips
        if len(validated_tips) >= 2:
            break
    
    return validated_tips

def validate_rationale(rationale: str) -> str:
    """
    Validate and clean rationale
    
    Args:
        rationale: Rationale text
        
    Returns:
        Cleaned rationale
    """
    if not isinstance(rationale, str):
        return "No rationale provided"
    
    # Clean the rationale
    cleaned = rationale.strip()
    
    # Remove URLs
    cleaned = remove_urls(cleaned)
    
    # Strip complex emojis
    cleaned = strip_emojis_except_simple(cleaned)
    
    # Check for profanity
    if check_profanity(cleaned):
        return "Analysis completed"
    
    # Check character limit
    if len(cleaned) > 140:
        cleaned = cleaned[:137] + '...'
    
    return cleaned if cleaned else "Analysis completed"

def validate_reasoning(
    tips: List[str],
    rationale: str,
    metric_overrides: Optional[Dict[str, float]] = None
) -> ValidationResult:
    """
    Validate reasoning response
    
    Args:
        tips: List of tips
        rationale: Rationale text
        metric_overrides: Optional metric overrides
        
    Returns:
        ValidationResult with cleaned data
    """
    warnings = []
    
    # Validate tips
    validated_tips = validate_tips(tips)
    
    # Validate rationale
    validated_rationale = validate_rationale(rationale)
    
    # Validate metric overrides
    validated_overrides = None
    if metric_overrides:
        try:
            validated_overrides = clamp_metric_overrides(metric_overrides)
            # If no valid metrics remain, set to None
            if not validated_overrides:
                validated_overrides = None
        except (ValueError, TypeError) as e:
            warnings.append(f"Invalid metric overrides: {e}")
            validated_overrides = None
    
    # Determine if response is valid
    # A response is valid if it has at least one tip OR a meaningful rationale
    has_tips = len(validated_tips) > 0
    has_meaningful_rationale = (
        validated_rationale != "Analysis completed" and 
        validated_rationale != "No rationale provided" and
        len(validated_rationale.strip()) > 0
    )
    is_valid = has_tips or has_meaningful_rationale
    
    return ValidationResult(
        tips=validated_tips,
        rationale=validated_rationale,
        metric_overrides=validated_overrides,
        is_valid=is_valid,
        warnings=warnings
    ) 