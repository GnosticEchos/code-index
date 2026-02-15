"""
Query caching service for Tree-sitter queries.

This module provides caching functionality for query results
to improve performance.
"""

from typing import Dict, Any, Optional


class QueryCache:
    """
    Service for caching query results.
    
    Handles:
    - Query result caching
    - Cache invalidation
    - Cache retrieval
    """
    
    def __init__(self):
        """Initialize the QueryCache."""
        self._query_cache: Dict[str, Dict[str, Any]] = {}
    
    def _set_cached_result(self, language: str, query_key: str, result: Any) -> None:
        """Set a cached query result."""
        if language not in self._query_cache:
            self._query_cache[language] = {}
        self._query_cache[language][query_key] = result
    
    def _get_cached_result(self, language: str, query_key: str):
        """Get a cached query result if present."""
        bucket = self._query_cache.get(language)
        if not bucket:
            return None
        return bucket.get(query_key)
    
    @property
    def query_cache(self) -> Dict[str, Any]:
        """Get the query cache dictionary."""
        return self._query_cache
    
    def _get_query_cache(self, language: str) -> Dict[str, Any]:
        """Return the cache bucket for a specific language (test helper)."""
        return self.query_cache.get(language, {})
    
    def invalidate_cache(self, language: str, query_key: Optional[str] = None) -> None:
        """Invalidate the cache for a language or a specific query key."""
        if query_key is None:
            self._query_cache.pop(language, None)
        else:
            bucket = self._query_cache.get(language)
            if bucket and query_key in bucket:
                del bucket[query_key]
    
    def _invalidate_cache(self, language: str) -> None:
        """Invalidate cache for a specific language (legacy alias)."""
        if language in self._query_cache:
            del self._query_cache[language]
    
    def clear_all(self) -> None:
        """Clear all cached query results."""
        self._query_cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_queries = sum(len(v) for v in self._query_cache.values())
        return {
            "total_languages": len(self._query_cache),
            "total_queries": total_queries
        }
