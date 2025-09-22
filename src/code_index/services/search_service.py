"""
SearchService for CQRS pattern implementation.

This service handles code search operations, separating business logic
from CLI concerns and providing a clean interface for search operations.
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..config import Config
from ..config_service import ConfigurationService
from ..service_validation import ServiceValidator, ValidationResult
from ..embedder import OllamaEmbedder
from ..vector_store import QdrantVectorStore
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..models import SearchResult, SearchMatch


class SearchService:
    """
    Service for handling code search operations.

    This service encapsulates the business logic for searching code,
    separating command operations from query operations and CLI concerns.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the SearchService with required dependencies."""
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = ConfigurationService(self.error_handler)
        self.service_validator = ServiceValidator(self.error_handler)

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

            # Initialize components
            embedder, vector_store = self._initialize_search_components(config)

            # Convert query to embedding
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
                            "search_query": query
                        }
                    )
                    matches.append(match)
                except Exception as e:
                    warnings.append(f"Failed to process search result: {str(e)}")
                    continue

            return SearchResult(
                query=query,
                matches=matches,
                total_found=len(matches),
                execution_time_seconds=time.time() - start_time,
                search_method="text",
                config_summary=self.config_service.get_config_summary(config),
                errors=errors,
                warnings=warnings
            )

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
            combined_warnings = warnings if warnings else None

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
        """Initialize search components (embedder and vector store)."""
        embedder = OllamaEmbedder(config)
        vector_store = QdrantVectorStore(config)
        return embedder, vector_store