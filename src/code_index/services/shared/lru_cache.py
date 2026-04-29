"""
LRU Cache with optional TTL for search results.
"""
import copy
import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Tuple


class SearchLRUCache:
    """Thread-safe LRU cache with optional TTL expiry for search results."""

    def __init__(self, *, max_entries: int, ttl_seconds: Optional[int]) -> None:
        self._store: "OrderedDict[Tuple[Any, ...], Tuple[Any, float]]" = OrderedDict()
        self._lock = threading.Lock()
        self._max_entries = max(1, max_entries)
        self._ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None

    def configure(self, *, max_entries: int, ttl_seconds: Optional[int]) -> None:
        with self._lock:
            self._max_entries = max(1, max_entries)
            self._ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
            self._prune_if_needed()

    def get(self, key: Tuple[Any, ...]) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            result, timestamp = self._store[key]
            if self._ttl_seconds is not None and (time.time() - timestamp) > self._ttl_seconds:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key, last=True)
            return copy.deepcopy(result)

    def set(self, key: Tuple[Any, ...], value: Any) -> None:
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
