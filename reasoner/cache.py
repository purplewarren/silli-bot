#!/usr/bin/env python3
"""
In-memory cache for reasoner responses
Provides LRU eviction and TTL-based expiration
"""

import json
import hashlib
import time
import os
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict

class ReasonerCache:
    """In-memory cache for reasoner responses with LRU eviction and TTL"""
    
    def __init__(self):
        # Get configuration from environment
        self.ttl_seconds = int(os.getenv('REASONER_CACHE_TTL_S', 300))  # 5 minutes default
        self.max_size = int(os.getenv('REASONER_CACHE_MAX', 256))  # 256 entries default
        
        # Cache storage: OrderedDict for LRU behavior
        self._cache: OrderedDict[str, Tuple[Dict[str, Any], float]] = OrderedDict()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def _generate_cache_key(self, dyad: str, features: Dict[str, Any], 
                           context: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        """
        Generate cache key from request parameters
        
        Args:
            dyad: The dyad type
            features: Audio/video features
            context: User-provided context
            metrics: Computed metrics
            
        Returns:
            SHA256 hash of the request parameters
        """
        # Create a normalized request dict
        request_data = {
            'dyad': dyad,
            'features': features,
            'context': context,
            'metrics': metrics
        }
        
        # Convert to JSON with sorted keys for consistent hashing
        json_str = json.dumps(request_data, sort_keys=True, separators=(',', ':'))
        
        # Generate SHA256 hash
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def get(self, dyad: str, features: Dict[str, Any], 
            context: Dict[str, Any], metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired
        
        Args:
            dyad: The dyad type
            features: Audio/video features
            context: User-provided context
            metrics: Computed metrics
            
        Returns:
            Cached response if valid, None otherwise
        """
        cache_key = self._generate_cache_key(dyad, features, context, metrics)
        current_time = time.time()
        
        if cache_key in self._cache:
            cached_response, timestamp = self._cache[cache_key]
            
            # Check if entry is expired
            if current_time - timestamp > self.ttl_seconds:
                # Remove expired entry
                del self._cache[cache_key]
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            self.hits += 1
            return cached_response
        
        self.misses += 1
        return None
    
    def set(self, dyad: str, features: Dict[str, Any], 
            context: Dict[str, Any], metrics: Dict[str, Any], 
            response: Dict[str, Any]) -> None:
        """
        Cache a response
        
        Args:
            dyad: The dyad type
            features: Audio/video features
            context: User-provided context
            metrics: Computed metrics
            response: The response to cache
        """
        # If cache is disabled, don't store anything
        if not self.is_enabled():
            return
        
        cache_key = self._generate_cache_key(dyad, features, context, metrics)
        current_time = time.time()
        
        # Remove expired entries first
        self._cleanup_expired(current_time)
        
        # If key already exists, update it
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            self._cache[cache_key] = (response, current_time)
            return
        
        # Check if we need to evict due to size limit
        if len(self._cache) >= self.max_size:
            # Remove least recently used item
            self._cache.popitem(last=False)
            self.evictions += 1
        
        # Add new entry
        self._cache[cache_key] = (response, current_time)
    
    def _cleanup_expired(self, current_time: float) -> None:
        """
        Remove expired entries from cache
        
        Args:
            current_time: Current timestamp
        """
        expired_keys = []
        
        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cached entries"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
        }
    
    def is_enabled(self) -> bool:
        """
        Check if cache is enabled
        
        Returns:
            True if cache is enabled (max_size > 0 and ttl_seconds > 0)
        """
        return self.max_size > 0 and self.ttl_seconds > 0 