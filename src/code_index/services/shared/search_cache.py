"""
Search cache module for caching search results.

This module provides LRU caching functionality for search results
with TTL support.
"""

import copy
import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Tuple, Dict
from ...models import SearchResult


class SearchLRUCache:
    """
    LRU Cache for search results with TTL support.
    
    Thread-safe implementation with configurable max entries and TTL.
    """
    
    def __init__(self, *, max_entries: int, ttl_seconds: Optional[int] = None) -> None:
        self._store: "OrderedDict[Tuple[Any, ...], Tuple[SearchResult, float]]" = OrderedDict()
        self._lock = threading.Lock()
        self._max_entries = max(1, max_entries)
        self._ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None

    def configure(self, *, max_entries: int, ttl_seconds: Optional[int]) -> None:
        with self._lock:
            self._max_entries = max(1, max_entries)
            self._ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
            self._prune_if_needed()

    def get(self, key: Tuple[Any, ...]) -> Optional[SearchResult]:
        with self._lock:
            if key not in self._store:
                return None

            result, timestamp = self._store[key]
            if self._ttl_seconds is not None and (time.time() - timestamp) > self._ttl_seconds:
                self._store.pop(key, None)
                return None

            self._store.move_to_end(key, last=True)
            return copy.deepcopy(result)

    def set(self, key: Tuple[Any, ...], value: SearchResult) -> None:
        with self._lock:
            self._store[key] = (copy.deepcopy(value), time.time())
            self._store.move_to_end(key, last=True)
            self._prune_if_needed()

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def _prune_if_needed(self) -> None:
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)


class SearchCacheRegistry:
    """
    Registry for managing search caches per workspace.
    """
    
    _caches: Dict[str, SearchLRUCache] = {}
    _registry_lock = threading.Lock()
    
    @classmethod
    def get_or_create_cache(
        cls, 
        workspace: str, 
        max_entries: int, 
        ttl_seconds: Optional[float] = None
    ) -> SearchLRUCache:
        """Get or create a cache for the given workspace."""
        with cls._registry_lock:
            if workspace not in cls._caches:
                cls._caches[workspace] = SearchLRUCache(
                    max_entries=max_entries,
                    ttl_seconds=int(ttl_seconds) if ttl_seconds else None
                )
            return cls._caches[workspace]
    
    @classmethod
    def invalidate_workspace_cache(cls, workspace_path: str) -> None:
        """Invalidate cache for a specific workspace."""
        with cls._registry_lock:
            cls._caches.pop(workspace_path, None)
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all caches."""
        with cls._registry_lock:
            cls._caches.clear()