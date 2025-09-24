"""
Query Management Service for Tree-sitter operations.

This service handles Tree-sitter query compilation, validation, caching,
and language-specific query retrieval. It provides a clean interface for
managing queries across different programming languages.
"""

import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

from .config import Config
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity, error_handler
from .treesitter_queries import get_queries_for_language


class QueryCompilationError(Exception):
    """Exception raised when query compilation fails."""
    pass


class QueryValidationError(Exception):
    """Exception raised when query validation fails."""
    pass


@dataclass
class QueryInfo:
    """Information about a compiled query."""
    language: str
    query_text: str
    compiled_query: Any
    compilation_time: float
    last_used: float
    use_count: int
    is_valid: bool
    error_message: Optional[str] = None


class TreeSitterQueryManager:
    """
    Service for managing Tree-sitter queries across different languages.

    Provides:
    - Query compilation and caching
    - Query validation and error handling
    - Language-specific query retrieval
    - Performance monitoring and optimization
    - Resource cleanup and memory management
    """

    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """
        Initialize the TreeSitterQueryManager.

        Args:
            config: Configuration object
            error_handler: Optional error handler instance
        """
        self.config = config
        self.error_handler = error_handler or ErrorHandler()

        # Query cache with metadata
        self._query_cache: Dict[str, QueryInfo] = {}

        # Language-specific query cache
        self._language_queries: Dict[str, Optional[str]] = {}

        # Performance tracking
        self._compilation_times: Dict[str, float] = {}
        self._query_usage: Dict[str, int] = {}

        # Cache settings
        self.max_cache_size = getattr(config, "tree_sitter_query_cache_size", 100)
        self.cache_ttl_seconds = getattr(config, "tree_sitter_query_cache_ttl", 300)  # 5 minutes

        # Debug logging
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

    def get_query_for_language(self, language: str) -> Optional[str]:
        """
        Get the Tree-sitter query for a specific language.

        Args:
            language: Language key

        Returns:
            Query string if available, None otherwise
        """
        try:
            # Check cache first
            if language in self._language_queries:
                return self._language_queries[language]

            # Get query from treesitter_queries module
            query_text = get_queries_for_language(language)

            # Cache the result (including None)
            self._language_queries[language] = query_text

            return query_text

        except Exception as e:
            error_context = ErrorContext(
                component="query_manager",
                operation="get_query_for_language",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.LOW
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return None

    def compile_query(self, language: str, query_text: str) -> Optional[Any]:
        """
        Compile a Tree-sitter query for a language.

        Args:
            language: Language key
            query_text: Query text to compile

        Returns:
            Compiled query object if successful, None otherwise
        """
        try:
            cache_key = f"{language}:{hash(query_text)}"

            # Check cache first
            if cache_key in self._query_cache:
                cached_query = self._query_cache[cache_key]
                if cached_query.is_valid and self._is_cache_valid(cached_query):
                    cached_query.last_used = time.time()
                    cached_query.use_count += 1
                    return cached_query.compiled_query
                else:
                    # Remove invalid cached query
                    del self._query_cache[cache_key]

            # Compile new query
            start_time = time.time()
            compiled_query = self._compile_query_internal(language, query_text)
            compilation_time = time.time() - start_time

            # Create query info
            query_info = QueryInfo(
                language=language,
                query_text=query_text,
                compiled_query=compiled_query,
                compilation_time=compilation_time,
                last_used=time.time(),
                use_count=1,
                is_valid=compiled_query is not None
            )

            # Cache the query
            if len(self._query_cache) < self.max_cache_size:
                self._query_cache[cache_key] = query_info

            # Track compilation time
            self._compilation_times[language] = compilation_time

            return compiled_query

        except Exception as e:
            error_context = ErrorContext(
                component="query_manager",
                operation="compile_query",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return None

    def validate_query(self, language: str, query_text: str) -> bool:
        """
        Validate a Tree-sitter query without compiling it.

        Args:
            language: Language key
            query_text: Query text to validate

        Returns:
            True if query is valid, False otherwise
        """
        try:
            # Try to compile the query
            compiled_query = self.compile_query(language, query_text)

            # Check if compilation was successful
            if compiled_query is None:
                return False

            # Additional validation - check if query has captures
            try:
                capture_names = getattr(compiled_query, 'capture_names', [])
                if not capture_names:
                    if self._debug_enabled:
                        print(f"Warning: Query for {language} has no captures")
                    return False
            except Exception:
                # If we can't check captures, assume it's valid if compilation succeeded
                pass

            return True

        except Exception as e:
            error_context = ErrorContext(
                component="query_manager",
                operation="validate_query",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.VALIDATION, ErrorSeverity.LOW
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return False

    def get_compiled_query(self, language: str) -> Optional[Any]:
        """
        Get a compiled query for a language, compiling if necessary.

        Args:
            language: Language key

        Returns:
            Compiled query object if successful, None otherwise
        """
        try:
            # Get query text for language
            query_text = self.get_query_for_language(language)
            if not query_text:
                return None

            # Compile and return query
            return self.compile_query(language, query_text)

        except Exception as e:
            error_context = ErrorContext(
                component="query_manager",
                operation="get_compiled_query",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return None

    def clear_cache(self) -> None:
        """Clear all cached queries."""
        self._query_cache.clear()
        self._language_queries.clear()
        self._compilation_times.clear()
        self._query_usage.clear()

    def cleanup_old_queries(self) -> int:
        """
        Remove old/unused queries from cache.

        Returns:
            Number of queries removed
        """
        current_time = time.time()
        removed_count = 0

        # Remove queries that haven't been used recently
        expired_queries = []
        for cache_key, query_info in self._query_cache.items():
            if current_time - query_info.last_used > self.cache_ttl_seconds:
                expired_queries.append(cache_key)

        for cache_key in expired_queries:
            del self._query_cache[cache_key]
            removed_count += 1

        if self._debug_enabled and removed_count > 0:
            print(f"Cleaned up {removed_count} expired queries from cache")

        return removed_count

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about query cache status.

        Returns:
            Dictionary with cache statistics
        """
        total_compilation_time = sum(self._compilation_times.values())
        total_queries = len(self._query_cache)
        valid_queries = sum(1 for q in self._query_cache.values() if q.is_valid)

        return {
            "cache_size": total_queries,
            "valid_queries": valid_queries,
            "invalid_queries": total_queries - valid_queries,
            "language_queries_cached": len(self._language_queries),
            "total_compilation_time": total_compilation_time,
            "average_compilation_time": total_compilation_time / total_queries if total_queries > 0 else 0,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_cache_size": self.max_cache_size
        }

    def get_query_stats(self, language: str) -> Dict[str, Any]:
        """
        Get statistics for queries of a specific language.

        Args:
            language: Language key

        Returns:
            Dictionary with language-specific query statistics
        """
        language_queries = [
            q for q in self._query_cache.values() if q.language == language
        ]

        if not language_queries:
            return {
                "language": language,
                "query_count": 0,
                "total_compilation_time": 0,
                "average_compilation_time": 0,
                "total_uses": 0
            }

        total_compilation_time = sum(q.compilation_time for q in language_queries)
        total_uses = sum(q.use_count for q in language_queries)

        return {
            "language": language,
            "query_count": len(language_queries),
            "total_compilation_time": total_compilation_time,
            "average_compilation_time": total_compilation_time / len(language_queries),
            "total_uses": total_uses,
            "average_uses_per_query": total_uses / len(language_queries)
        }

    def _compile_query_internal(self, language: str, query_text: str) -> Optional[Any]:
        """
        Internal method to compile a Tree-sitter query.

        Args:
            language: Language key
            query_text: Query text to compile

        Returns:
            Compiled query object if successful, None otherwise
        """
        try:
            from tree_sitter import Query

            # Get Tree-sitter language
            language_obj = self._get_tree_sitter_language(language)
            if not language_obj:
                raise QueryCompilationError(f"Tree-sitter language not available for {language}")

            # Try modern constructor first
            try:
                query = Query(language_obj, query_text)
                if self._debug_enabled:
                    print(f"Compiled query using Query(language, text) for {language}")
                return query
            except Exception as e_primary:
                # Fallback to language.query if available (suppress deprecation warning)
                try:
                    if hasattr(language_obj, "query"):
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", DeprecationWarning)
                            query = language_obj.query(query_text)  # type: ignore[attr-defined]
                        if self._debug_enabled:
                            print(f"Compiled query using language.query(text) for {language}")
                        return query
                    else:
                        raise e_primary
                except Exception as e_fallback:
                    raise QueryCompilationError(f"Query compilation failed for {language}: {e_fallback}")

        except Exception as e:
            error_context = ErrorContext(
                component="query_manager",
                operation="_compile_query_internal",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return None

    def _get_tree_sitter_language(self, language: str):
        """
        Get Tree-sitter Language object for a language.

        Args:
            language: Language key

        Returns:
            Language object if available, None otherwise
        """
        try:
            import tree_sitter_language_pack as tsl
            return tsl.get_language(language)
        except Exception as e:
            if self._debug_enabled:
                print(f"Failed to load Tree-sitter language for {language}: {e}")
            return None

    def _is_cache_valid(self, query_info: QueryInfo) -> bool:
        """
        Check if a cached query is still valid.

        Args:
            query_info: Query information object

        Returns:
            True if cache is valid, False otherwise
        """
        current_time = time.time()
        return current_time - query_info.last_used <= self.cache_ttl_seconds

    def preload_common_queries(self) -> int:
        """
        Preload queries for commonly used languages.

        Returns:
            Number of queries preloaded
        """
        common_languages = [
            'python', 'javascript', 'typescript', 'rust', 'go', 'java', 'cpp', 'c'
        ]

        preloaded_count = 0
        for language in common_languages:
            try:
                query = self.get_compiled_query(language)
                if query:
                    preloaded_count += 1
            except Exception:
                continue

        if self._debug_enabled:
            print(f"Preloaded {preloaded_count} queries for common languages")

        return preloaded_count