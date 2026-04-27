"""
SearchService for CQRS pattern implementation.

This service handles code search operations, separating business logic
from CLI concerns and providing a clean interface for search operations.

Uses extracted modules:
- search_strategy_selector: Strategy selection logic
- result_ranker: Result ranking and processing
"""

import copy
import time
import threading
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ...config import Config
from ...config_service import ConfigurationService
from ...service_validation import ServiceValidator, ValidationResult
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ...models import SearchResult, SearchMatch
from ..query.query_embedding_cache import QueryEmbeddingCache

# Import from extracted modules
from ..shared.search_strategy_selector import SearchStrategySelector
from ..shared.result_ranker import ResultRanker


class SearchService:
    """
    Service for handling code search operations.

    This service encapsulates the business logic for searching code,
    separating command operations from query operations and CLI concerns.
    """

    _cache_registry: Dict[str, "SearchService._LRUCache"] = {}
    _cache_registry_lock = threading.Lock()

    def __init__(self, error_handler: Optional[ErrorHandler] = None, embedding_cache: Optional[QueryEmbeddingCache] = None):
        """Initialize the SearchService with required dependencies."""
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = ConfigurationService(self.error_handler)
        self.service_validator = ServiceValidator(self.error_handler)
        self._cache: Optional[SearchService._LRUCache] = None
        self._embedding_cache = embedding_cache or QueryEmbeddingCache()
        self._config: Optional[Config] = None
    
    def _init_strategy_selector(self, config: Config) -> SearchStrategySelector:
        """Initialize strategy selector with config."""
        return SearchStrategySelector(config)
    
    def _init_result_ranker(self, config: Config) -> ResultRanker:
        """Initialize result ranker with config."""
        return ResultRanker(config)

    def search_code(self, query: str, config: Config) -> SearchResult:
        """
        Execute text-based code search.

        Args:
            query: Search query string
            config: Configuration object with search parameters

        Returns:
            SearchResult with detailed search results
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        cache_enabled = getattr(config, "search_cache_enabled", False)
        cache_key: Optional[Tuple[Any, ...]] = None
        cache: Optional[SearchService._LRUCache] = None

        try:
            # Validate search configuration
            validation_result = self.validate_search_config(config)
            if not validation_result.valid:
                if validation_result.error:
                    errors.append(f"Configuration: {validation_result.error}")
                return SearchResult(
                    query=query,
                    matches=[],
                    total_found=0,
                    execution_time_seconds=time.time() - start_time,
                    search_method="text",
                    config_summary=self.config_service.get_config_summary(config),
                    errors=errors,
                    warnings=warnings
                )

            if cache_enabled:
                cache = self._get_or_create_cache(config)
                cache_key = self._build_cache_key(query, config)
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    cached_result.execution_time_seconds = time.time() - start_time
                    return cached_result

            # Initialize components
            embedder, vector_store = self._initialize_search_components(config)

            # Convert query to embedding (with caching)
            embedding_cache_enabled = getattr(config, "embedding_cache_enabled", True)
            if embedding_cache_enabled:
                query_embedding = self._embedding_cache.get_embedding(query)
                if query_embedding is None:
                    embedding_response = embedder.create_embeddings([query])
                    if not embedding_response["embeddings"]:
                        errors.append("Failed to generate embedding for search query")
                        return SearchResult(
                            query=query,
                            matches=[],
                            total_found=0,
                            execution_time_seconds=time.time() - start_time,
                            search_method="text",
                            config_summary=self.config_service.get_config_summary(config),
                            errors=errors,
                            warnings=warnings
                        )
                    query_embedding = embedding_response["embeddings"][0]
                    self._embedding_cache.set_embedding(query, query_embedding)
            else:
                embedding_response = embedder.create_embeddings([query])
                if not embedding_response["embeddings"]:
                    errors.append("Failed to generate embedding for search query")
                    return SearchResult(
                        query=query,
                        matches=[],
                        total_found=0,
                        execution_time_seconds=time.time() - start_time,
                        search_method="text",
                        config_summary=self.config_service.get_config_summary(config),
                        errors=errors,
                        warnings=warnings
                    )
                query_embedding = embedding_response["embeddings"][0]

            # Perform vector search
            search_results = vector_store.search(
                query_vector=query_embedding,
                min_score=getattr(config, "search_min_score", 0.4),
                max_results=getattr(config, "search_max_results", 50)
            )

            # Convert search results to SearchMatch objects
            # First, group split parts by parentBlockId for reassembly
            split_groups: Dict[str, List[Dict[str, Any]]] = {}
            non_split_results: List[Dict[str, Any]] = []
            
            for result in search_results:
                payload = result["payload"]
                if "splitIndex" in payload and "parentBlockId" in payload:
                    parent_id = payload["parentBlockId"]
                    if parent_id not in split_groups:
                        split_groups[parent_id] = []
                    split_groups[parent_id].append(result)
                else:
                    non_split_results.append(result)
            
            # Reassemble split parts and convert to SearchMatch objects
            matches = []
            
            # Process non-split results
            for result in non_split_results:
                try:
                    match = SearchMatch(
                        file_path=result["payload"]["filePath"],
                        start_line=result["payload"]["startLine"],
                        end_line=result["payload"]["endLine"],
                        code_chunk=result["payload"]["codeChunk"],
                        match_type=result["payload"].get("type", "text"),
                        score=result["score"],
                        adjusted_score=result.get("adjustedScore", result["score"]),
                        metadata={
                            "embedding_model": result["payload"].get("embedding_model", ""),
                            "search_query": query
                        }
                    )
                    matches.append(match)
                except Exception as e:
                    warnings.append(f"Failed to process search result: {str(e)}")
                    continue
            
            # Process and reassemble split parts
            for parent_id, parts in split_groups.items():
                try:
                    # Sort parts by splitIndex
                    sorted_parts = sorted(parts, key=lambda p: p["payload"]["splitIndex"])
                    
                    # Verify we have all parts
                    total_expected = sorted_parts[0]["payload"]["splitTotal"]
                    if len(sorted_parts) != total_expected:
                        # Missing parts - add individual parts with warning
                        warnings.append(f"Incomplete split block {parent_id}: have {len(sorted_parts)} of {total_expected} parts")
                        for part in sorted_parts:
                            match = SearchMatch(
                                file_path=part["payload"]["filePath"],
                                start_line=part["payload"]["startLine"],
                                end_line=part["payload"]["endLine"],
                                code_chunk=part["payload"]["codeChunk"],
                                match_type=part["payload"].get("type", "text"),
                                score=part["score"],
                                adjusted_score=part.get("adjustedScore", part["score"]),
                                metadata={
                                    "embedding_model": part["payload"].get("embedding_model", ""),
                                    "search_query": query,
                                    "split_part": f"{part['payload']['splitIndex']} of {total_expected}"
                                }
                            )
                            matches.append(match)
                        continue
                    
                    # Reassemble the complete block
                    first_part = sorted_parts[0]
                    last_part = sorted_parts[-1]
                    
                    # Concatenate all code chunks
                    reassembled_code = "".join(
                        p["payload"]["codeChunk"] for p in sorted_parts
                    )
                    
                    # Use the best score from all parts
                    best_score = max(p["score"] for p in sorted_parts)
                    best_adjusted = max(p.get("adjustedScore", p["score"]) for p in sorted_parts)
                    
                    match = SearchMatch(
                        file_path=first_part["payload"]["filePath"],
                        start_line=first_part["payload"]["startLine"],
                        end_line=last_part["payload"]["endLine"],
                        code_chunk=reassembled_code,
                        match_type=first_part["payload"].get("type", "text"),
                        score=best_score,
                        adjusted_score=best_adjusted,
                        metadata={
                            "embedding_model": first_part["payload"].get("embedding_model", ""),
                            "search_query": query,
                            "reassembled_from": total_expected,
                            "parent_block_id": parent_id
                        }
                    )
                    matches.append(match)
                except Exception as e:
                    warnings.append(f"Failed to reassemble split block {parent_id}: {str(e)}")
                    continue

            result = SearchResult(
                query=query,
                matches=matches,
                total_found=len(matches),
                execution_time_seconds=time.time() - start_time,
                search_method="text",
                config_summary=self.config_service.get_config_summary(config),
                errors=errors,
                warnings=warnings
            )

            if cache_enabled and cache is not None and cache_key is not None and result.is_successful():
                cache.set(cache_key, result)

            return result

        except Exception as e:
            error_context = ErrorContext(
                component="search_service",
                operation="search_code",
                additional_data={"query": query}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.DATABASE, ErrorSeverity.HIGH
            )
            errors.append(error_response.message)

            return SearchResult(
                query=query,
                matches=[],
                total_found=0,
                execution_time_seconds=time.time() - start_time,
                search_method="text",
                config_summary=self.config_service.get_config_summary(config),
                errors=errors,
                warnings=warnings
            )

    def search_similar_files(self, file_path: str, config: Config) -> SearchResult:
        """
        Search for files similar to the given file path.

        Args:
            file_path: Path to the file to find similar files for
            config: Configuration object with search parameters

        Returns:
            SearchResult with similar file matches
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Validate search configuration
            validation_result = self.validate_search_config(config)
            if not validation_result.valid:
                if validation_result.error:
                    errors.append(f"Configuration: {validation_result.error}")
                return SearchResult(
                    query=f"similar:{file_path}",
                    matches=[],
                    total_found=0,
                    execution_time_seconds=time.time() - start_time,
                    search_method="similarity",
                    config_summary=self.config_service.get_config_summary(config),
                    errors=errors,
                    warnings=warnings
                )

            # Check if file exists
            if not Path(file_path).exists():
                errors.append(f"File not found: {file_path}")
                return SearchResult(
                    query=f"similar:{file_path}",
                    matches=[],
                    total_found=0,
                    execution_time_seconds=time.time() - start_time,
                    search_method="similarity",
                    config_summary=self.config_service.get_config_summary(config),
                    errors=errors,
                    warnings=warnings
                )

            # Initialize components
            embedder, vector_store = self._initialize_search_components(config)

            # Read file content and generate embedding
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                if not file_content.strip():
                    errors.append(f"File is empty: {file_path}")
                    return SearchResult(
                        query=f"similar:{file_path}",
                        matches=[],
                        total_found=0,
                        execution_time_seconds=time.time() - start_time,
                        search_method="similarity",
                        config_summary=self.config_service.get_config_summary(config),
                        errors=errors,
                        warnings=warnings
                    )

                # Generate embedding for file content
                embedding_response = embedder.create_embeddings([file_content])
                if not embedding_response["embeddings"]:
                    errors.append(f"Failed to generate embedding for file: {file_path}")
                    return SearchResult(
                        query=f"similar:{file_path}",
                        matches=[],
                        total_found=0,
                        execution_time_seconds=time.time() - start_time,
                        search_method="similarity",
                        config_summary=self.config_service.get_config_summary(config),
                        errors=errors,
                        warnings=warnings
                    )

                file_embedding = embedding_response["embeddings"][0]

                # Perform vector search
                search_results = vector_store.search(
                    query_vector=file_embedding,
                    min_score=getattr(config, "search_min_score", 0.4),
                    max_results=getattr(config, "search_max_results", 50)
                )

                # Convert search results to SearchMatch objects
                matches = []
                for result in search_results:
                    try:
                        # Skip the original file if it appears in results
                        if result["payload"]["filePath"] == file_path:
                            continue

                        match = SearchMatch(
                            file_path=result["payload"]["filePath"],
                            start_line=result["payload"]["startLine"],
                            end_line=result["payload"]["endLine"],
                            code_chunk=result["payload"]["codeChunk"],
                            match_type=result["payload"].get("type", "text"),
                            score=result["score"],
                            adjusted_score=result.get("adjustedScore", result["score"]),
                            metadata={
                                "embedding_model": result["payload"].get("embedding_model", ""),
                                "similarity_file": file_path
                            }
                        )
                        matches.append(match)
                    except Exception as e:
                        warnings.append(f"Failed to process similarity result: {str(e)}")
                        continue

                return SearchResult(
                    query=f"similar:{file_path}",
                    matches=matches,
                    total_found=len(matches),
                    execution_time_seconds=time.time() - start_time,
                    search_method="similarity",
                    config_summary=self.config_service.get_config_summary(config),
                    errors=errors,
                    warnings=warnings
                )

            except Exception as e:
                error_context = ErrorContext(
                    component="search_service",
                    operation="search_similar_files",
                    file_path=file_path
                )
                error_response = self.error_handler.handle_file_error(
                    e, error_context, "file_reading"
                )
                errors.append(error_response.message)

                return SearchResult(
                    query=f"similar:{file_path}",
                    matches=[],
                    total_found=0,
                    execution_time_seconds=time.time() - start_time,
                    search_method="similarity",
                    config_summary=self.config_service.get_config_summary(config),
                    errors=errors,
                    warnings=warnings
                )

        except Exception as e:
            error_context = ErrorContext(
                component="search_service",
                operation="search_similar_files",
                additional_data={"file_path": file_path}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.DATABASE, ErrorSeverity.HIGH
            )
            errors.append(error_response.message)

            return SearchResult(
                query=f"similar:{file_path}",
                matches=[],
                total_found=0,
                execution_time_seconds=time.time() - start_time,
                search_method="similarity",
                config_summary=self.config_service.get_config_summary(config),
                errors=errors,
                warnings=warnings
            )

    def search_by_embedding(self, embedding: List[float], config: Config) -> SearchResult:
        """
        Search using a pre-computed embedding vector.

        Args:
            embedding: Pre-computed embedding vector
            config: Configuration object with search parameters

        Returns:
            SearchResult with search results
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Validate search configuration
            validation_result = self.validate_search_config(config)
            if not validation_result.valid:
                if validation_result.error:
                    errors.append(f"Configuration: {validation_result.error}")
                return SearchResult(
                    query="embedding_search",
                    matches=[],
                    total_found=0,
                    execution_time_seconds=time.time() - start_time,
                    search_method="embedding",
                    config_summary=self.config_service.get_config_summary(config),
                    errors=errors,
                    warnings=warnings
                )

            # Initialize components
            _, vector_store = self._initialize_search_components(config)

            # Perform vector search
            search_results = vector_store.search(
                query_vector=embedding,
                min_score=getattr(config, "search_min_score", 0.4),
                max_results=getattr(config, "search_max_results", 50)
            )

            # Convert search results to SearchMatch objects
            matches = []
            for result in search_results:
                try:
                    match = SearchMatch(
                        file_path=result["payload"]["filePath"],
                        start_line=result["payload"]["startLine"],
                        end_line=result["payload"]["endLine"],
                        code_chunk=result["payload"]["codeChunk"],
                        match_type=result["payload"].get("type", "text"),
                        score=result["score"],
                        adjusted_score=result.get("adjustedScore", result["score"]),
                        metadata={
                            "embedding_model": result["payload"].get("embedding_model", ""),
                            "search_method": "embedding"
                        }
                    )
                    matches.append(match)
                except Exception as e:
                    warnings.append(f"Failed to process embedding search result: {str(e)}")
                    continue

            return SearchResult(
                query="embedding_search",
                matches=matches,
                total_found=len(matches),
                execution_time_seconds=time.time() - start_time,
                search_method="embedding",
                config_summary=self.config_service.get_config_summary(config),
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            error_context = ErrorContext(
                component="search_service",
                operation="search_by_embedding"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.DATABASE, ErrorSeverity.HIGH
            )
            errors.append(error_response.message)

            return SearchResult(
                query="embedding_search",
                matches=[],
                total_found=0,
                execution_time_seconds=time.time() - start_time,
                search_method="embedding",
                config_summary=self.config_service.get_config_summary(config),
                errors=errors,
                warnings=warnings
            )

    def validate_search_config(self, config: Config) -> ValidationResult:
        """
        Validate search configuration and services.

        Args:
            config: Configuration object to validate

        Returns:
            ValidationResult with validation status
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        metadata: Dict[str, Any] = {}

        try:
            # Validate configuration values
            if getattr(config, "search_min_score", 0.4) < 0 or getattr(config, "search_min_score", 0.4) > 1:
                errors.append("search_min_score must be between 0 and 1")

            if getattr(config, "search_max_results", 50) <= 0:
                errors.append("search_max_results must be positive")

            # Validate services
            service_results = self.service_validator.validate_all_services(config)
            failed_services = [result for result in service_results if not result.valid]

            if failed_services:
                errors.extend([f"{result.service}: {result.error}" for result in failed_services])
                metadata["service_validation"] = [result.to_dict() for result in service_results]
            else:
                metadata["service_validation"] = [result.to_dict() for result in service_results]

            # Check if vector store has data
            try:
                _, vector_store = self._initialize_search_components(config)
                if hasattr(vector_store, 'collection_exists'):
                    if not vector_store.collection_exists():
                        warnings.append("No indexed data found - run indexing first")
                    else:
                        metadata["collection_exists"] = True
            except Exception as e:
                warnings.append(f"Could not check collection status: {str(e)}")

            # Create a combined validation result
            combined_error = "; ".join(errors) if errors else None

            return ValidationResult(
                service="search_service",
                valid=len(errors) == 0,
                error=combined_error,
                details=metadata,
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=warnings if warnings else []
            )

        except Exception as e:
            error_context = ErrorContext(
                component="search_service",
                operation="validate_search_config"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )

            return ValidationResult(
                service="search_service",
                valid=False,
                error=error_response.message,
                details=metadata,
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check configuration and service connectivity"]
            )

    def _initialize_search_components(self, config: Config):
        """Initialize search components (delegated to strategy selector)."""
        selector = self._init_strategy_selector(config)
        return selector.initialize_components(config)

    def get_embedding_cache_stats(self) -> Dict[str, Any]:
        """Get statistics for the query embedding cache.

        Returns:
            Dictionary with cache statistics including hits, misses, size, and hit rate.
        """
        return self._embedding_cache.get_stats()

    def clear_embedding_cache(self) -> None:
        """Clear all entries from the query embedding cache."""
        self._embedding_cache.clear()

    def configure_embedding_cache(self, max_size: Optional[int] = None, ttl_seconds: Optional[float] = None) -> None:
        """Configure the embedding cache settings.

        Args:
            max_size: Maximum number of entries (uses current if not provided).
            ttl_seconds: TTL in seconds for cache entries (uses current if not provided).
        """
        self._embedding_cache.reconfigure(max_size=max_size, ttl_seconds=ttl_seconds)

    def _get_or_create_cache(self, config: Config) -> "SearchService._LRUCache":
        workspace = getattr(config, "workspace_path", "") or ""
        max_entries = max(1, int(getattr(config, "search_cache_max_entries", 128) or 128))
        ttl_seconds = getattr(config, "search_cache_ttl_seconds", None)

        with SearchService._cache_registry_lock:
            cache = SearchService._cache_registry.get(workspace)
            if cache is None:
                cache = SearchService._LRUCache(max_entries=max_entries, ttl_seconds=ttl_seconds)
                SearchService._cache_registry[workspace] = cache
            else:
                cache.configure(max_entries=max_entries, ttl_seconds=ttl_seconds)

        self._cache = cache
        return cache

    def _build_cache_key(self, query: str, config: Config) -> Tuple[Any, ...]:
        weights = tuple(sorted((config.search_file_type_weights or {}).items())) if getattr(config, "search_file_type_weights", None) else tuple()
        path_boosts = tuple(
            (entry.get("pattern"), entry.get("weight"))
            for entry in (getattr(config, "search_path_boosts", []) or [])
        )
        lang_boosts = tuple(sorted((config.search_language_boosts or {}).items())) if getattr(config, "search_language_boosts", None) else tuple()
        exclude_patterns = tuple(sorted(getattr(config, "search_exclude_patterns", []) or []))

        return (
            query,
            getattr(config, "workspace_path", ""),
            getattr(config, "search_min_score", 0.4),
            getattr(config, "search_max_results", 50),
            weights,
            path_boosts,
            lang_boosts,
            exclude_patterns,
            getattr(config, "ollama_model", ""),
            getattr(config, "qdrant_url", ""),
        )

    @staticmethod
    def invalidate_workspace_cache(workspace_path: str) -> None:
        workspace = workspace_path or ""
        with SearchService._cache_registry_lock:
            cache = SearchService._cache_registry.pop(workspace, None)
            if cache is not None:
                cache.clear()

    class _LRUCache:
        def __init__(self, *, max_entries: int, ttl_seconds: Optional[int]) -> None:
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