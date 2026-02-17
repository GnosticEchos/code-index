"""Query embedding cache wrapper with cache management and statistics."""

from typing import Optional, List, Dict, Any
from ..embedding.embedding_cache import EmbeddingCache


class QueryEmbeddingCache:
    """Wrapper around EmbeddingCache for query embeddings with additional management features."""

    def __init__(
        self,
        max_size: int = 256,
        ttl_seconds: Optional[float] = None,
        cache: Optional[EmbeddingCache] = None
    ):
        """Initialize the query embedding cache wrapper.

        Args:
            max_size: Maximum number of entries in the cache (default: 256)
            ttl_seconds: Optional time-to-live in seconds for cache entries.
            cache: Optional pre-configured EmbeddingCache instance.
        """
        self._cache = cache if cache is not None else EmbeddingCache(
            max_size=max_size,
            ttl_seconds=ttl_seconds
        )
        self._default_max_size = max_size
        self._default_ttl_seconds = ttl_seconds

    def get_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached embedding for a query.

        Args:
            query: The query string to look up.

        Returns:
            The cached embedding vector or None if not found.
        """
        return self._cache.get(query)

    def set_embedding(self, query: str, embedding: List[float]) -> None:
        """Store embedding for a query.

        Args:
            query: The query string.
            embedding: The embedding vector to cache.
        """
        self._cache.set(query, embedding)

    def get_or_create(self, query: str, embed_func) -> List[float]:
        """Get cached embedding or create and cache a new one.

        Args:
            query: The query string.
            embed_func: Function to call if embedding is not cached.

        Returns:
            The embedding vector (cached or newly created).
        """
        embedding = self._cache.get(query)
        if embedding is None:
            embedding = embed_func(query)
            self._cache.set(query, embedding)
        return embedding

    def clear(self) -> None:
        """Clear all cached embeddings and reset statistics."""
        self._cache.clear()

    def reset(self) -> None:
        """Reset the cache with initial configuration."""
        self._cache.clear()
        # Re-initialize with default settings
        self._cache = EmbeddingCache(
            max_size=self._default_max_size,
            ttl_seconds=self._default_ttl_seconds
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics including hits, misses, size, and configuration.
        """
        stats = self._cache.get_stats()
        stats['max_size'] = self._cache.max_size
        stats['ttl_seconds'] = self._cache.ttl_seconds
        stats['hit_rate'] = self._calculate_hit_rate()
        return stats

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage.

        Returns:
            Hit rate as a float between 0 and 100, or 0 if no accesses.
        """
        stats = self._cache.get_stats()
        total = stats['hits'] + stats['misses']
        if total == 0:
            return 0.0
        return round((stats['hits'] / total) * 100, 2)

    def reconfigure(self, max_size: Optional[int] = None, ttl_seconds: Optional[float] = None) -> None:
        """Reconfigure the cache with new settings.

        Args:
            max_size: New maximum cache size (uses current if not provided).
            ttl_seconds: New TTL in seconds (uses current if not provided).
        """
        if max_size is not None:
            self._default_max_size = max_size
        if ttl_seconds is not None:
            self._default_ttl_seconds = ttl_seconds

        # Create new cache with updated settings
        self._cache = EmbeddingCache(
            max_size=self._default_max_size,
            ttl_seconds=self._default_ttl_seconds
        )

    @property
    def cache(self) -> EmbeddingCache:
        """Access the underlying EmbeddingCache instance."""
        return self._cache

    @property
    def max_size(self) -> int:
        """Get the maximum cache size."""
        return self._cache.max_size

    @property
    def ttl_seconds(self) -> Optional[float]:
        """Get the TTL in seconds, or None if disabled."""
        return self._cache.ttl_seconds