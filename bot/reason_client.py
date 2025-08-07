#!/usr/bin/env python3
"""
Lightweight HTTP client for Silli Reasoner
Provides async interface for bot to call local reasoning engine
"""

import aiohttp
import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

class ReasonerUnavailable(Exception):
    """Raised when the reasoner is unavailable or returns an error"""
    pass

@dataclass
class ReasonerConfig:
    """Configuration for reasoner client"""
    base_url: str
    enabled: bool = False
    timeout_s: int = 8
    model_hint: str = "gpt-oss-20b"
    temperature: float = 0.2

def clamp_metric_overrides(overrides: Dict[str, float]) -> Dict[str, float]:
    """
    Clamp metric overrides to valid ranges
    
    Args:
        overrides: Dictionary of metric overrides from reasoner
        
    Returns:
        Clamped overrides with values in valid ranges
    """
    clamped = {}
    
    if "escalation_index" in overrides:
        value = float(overrides["escalation_index"])
        clamped["escalation_index"] = max(0.0, min(1.0, value))
    
    if "meal_mood" in overrides:
        value = float(overrides["meal_mood"])
        clamped["meal_mood"] = max(0.0, min(100.0, value))
    
    return clamped

def truncate_tips(tips: List[str], max_words: int = 25) -> List[str]:
    """
    Truncate tips to maximum word count
    
    Args:
        tips: List of tips from reasoner
        max_words: Maximum words per tip
        
    Returns:
        List of truncated tips
    """
    truncated = []
    
    for tip in tips:
        if not tip or not isinstance(tip, str):
            continue
        
        # Skip whitespace-only strings
        if not tip.strip():
            continue
            
        words = tip.split()
        if len(words) <= max_words:
            truncated.append(tip)
        else:
            # Truncate to max_words and add ellipsis
            truncated_tip = " ".join(words[:max_words]) + "..."
            truncated.append(truncated_tip)
    
    return truncated

class ReasonClient:
    """Lightweight HTTP client for Silli Reasoner"""
    
    def __init__(self, base_url: str, timeout_s: int = 8):
        """
        Initialize reasoner client
        
        Args:
            base_url: Base URL of reasoner service (e.g., http://localhost:5001)
            timeout_s: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout_s = timeout_s
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout_s)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def health_check(self) -> bool:
        """
        Check if reasoner is healthy and available
        
        Returns:
            True if reasoner is healthy, False otherwise
        """
        try:
            if not self.session:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as session:
                    async with session.get(f"{self.base_url}/health") as response:
                        return response.status == 200
            else:
                async with self.session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send inference request to reasoner
        
        Args:
            payload: Request payload with dyad, features, context, metrics, history
            
        Returns:
            Response from reasoner with tips, rationale, etc.
            
        Raises:
            ReasonerUnavailable: If reasoner is unavailable or returns error
        """
        if not self.session:
            raise ReasonerUnavailable("Client session not initialized. Use async context manager.")
        
        try:
            url = f"{self.base_url}/v1/reason"
            headers = {"Content-Type": "application/json"}
            
            async with self.session.post(
                url, 
                json=payload, 
                headers=headers
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise ReasonerUnavailable(
                        f"Reasoner returned {response.status}: {error_text}"
                    )
                
                return await response.json()
                
        except asyncio.TimeoutError:
            raise ReasonerUnavailable(f"Request timed out after {self.timeout_s}s")
        except aiohttp.ClientError as e:
            raise ReasonerUnavailable(f"Network error: {e}")
        except json.JSONDecodeError as e:
            raise ReasonerUnavailable(f"Invalid JSON response: {e}")
        except Exception as e:
            raise ReasonerUnavailable(f"Unexpected error: {e}")
    
    async def get_models(self) -> Dict[str, Any]:
        """
        Get available models from reasoner
        
        Returns:
            Models information from reasoner
            
        Raises:
            ReasonerUnavailable: If reasoner is unavailable
        """
        if not self.session:
            raise ReasonerUnavailable("Client session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status != 200:
                    raise ReasonerUnavailable(f"Failed to get models: {response.status}")
                return await response.json()
        except Exception as e:
            raise ReasonerUnavailable(f"Failed to get models: {e}")

def create_reasoner_config() -> ReasonerConfig:
    """Create reasoner configuration from environment variables"""
    return ReasonerConfig(
        base_url=os.getenv('REASONER_BASE_URL', 'http://localhost:5001'),
        enabled=bool(os.getenv('REASONER_ENABLED', '0').lower() in ('1', 'true', 'yes', 'on')),
        timeout_s=int(os.getenv('REASONER_TIMEOUT', '8')),
        model_hint=os.getenv('REASONER_MODEL_HINT', 'gpt-oss-20b'),
        temperature=float(os.getenv('REASONER_TEMP', '0.2'))
    )

async def get_reasoning_insights(
    dyad: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
    metrics: Dict[str, Any],
    history: list,
    config: ReasonerConfig
) -> Optional[Dict[str, Any]]:
    """
    Get AI reasoning insights for a dyad session
    
    Args:
        dyad: Dyad type (night, tantrum, meal)
        features: Computed features from media
        context: User-provided context
        metrics: Computed metrics
        history: Recent session history
        config: Reasoner configuration
        
    Returns:
        Reasoning response with tips and rationale, or None if disabled/unavailable
    """
    if not config.enabled:
        return None
    
    try:
        async with ReasonClient(config.base_url, config.timeout_s) as client:
            # Check health first
            if not await client.health_check():
                return None
            
            # Prepare payload
            payload = {
                "dyad": dyad,
                "features": features,
                "context": context,
                "metrics": metrics,
                "history": history
            }
            
            # Get reasoning
            response = await client.infer(payload)
            return response
            
    except ReasonerUnavailable:
        # Log error but don't fail the main flow
        return None
    except Exception as e:
        # Unexpected errors should be logged but not fail the flow
        return None

# Convenience function for sync contexts
def get_reasoning_insights_sync(
    dyad: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
    metrics: Dict[str, Any],
    history: list,
    config: ReasonerConfig
) -> Optional[Dict[str, Any]]:
    """
    Synchronous wrapper for get_reasoning_insights
    """
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            get_reasoning_insights(dyad, features, context, metrics, history, config)
        )
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(
            get_reasoning_insights(dyad, features, context, metrics, history, config)
        ) 