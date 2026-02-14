"""Embedding cache with thread safety, TTL support, and statistics tracking."""

import time
import threading
from typing import Optional, Any


class EmbeddingCache:
    """Thread-safe cache for embeddings with configurable size and optional TTL."""

    def __init__(self, max_size: int = 256, ttl_seconds: Optional[float] = None):
        """Initialize the embedding cache.

        Args:
            max_size: Maximum number of entries in the cache (default: 256)
            ttl_seconds: Optional time-to-live in seconds for cache entries.
                         If None, entries never expire.
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._lock = threading.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get an embedding from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached embedding or None if not found/expired.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            value, timestamp = self._cache[key]
            
            # Check TTL if enabled
            if self._ttl_seconds is not None:
                if time.time() - timestamp > self._ttl_seconds:
                    # Entry expired, remove it
                    del self._cache[key]
                    self._misses += 1
                    return None
            
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """Store an embedding in the cache.

        Args:
            key: The cache key.
            value: The embedding to cache.
        """
        with self._lock:
            # Evict oldest entry if cache is full
            if len(self._cache) >= self._max_size and key not in self._cache:
                # Remove the oldest entry (first item in dict)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all entries from the cache and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with 'hits', 'misses', and 'size' statistics.
        """
        with self._lock:
            return {
                'hits': self._hits,
                'misses': self._misses,
                'size': len(self._cache)
            }

    @property
    def max_size(self) -> int:
        """Get the maximum cache size."""
        return self._max_size

    @property
    def ttl_seconds(self) -> Optional[float]:
        """Get the TTL in seconds, or None if disabled."""
        return self._ttl_seconds
