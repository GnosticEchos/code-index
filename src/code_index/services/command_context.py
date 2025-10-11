"""Shared command/query orchestration context for CLI and MCP front-ends."""

from __future__ import annotations

import logging
import copy
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any

logger = logging.getLogger(__name__)

from ..config import Config
from ..config_service import ConfigurationService
from ..errors import ErrorHandler
from ..logging_utils import LoggingConfigurator
from ..collections import CollectionManager
from ..embedder import OllamaEmbedder
from ..vector_store import QdrantVectorStore
from .indexing_service import IndexingService
from .search_service import SearchService


@dataclass
class IndexDependencies:
    config: Config
    indexing_service: IndexingService


@dataclass
class SearchDependencies:
    config: Config
    search_service: SearchService
    collection_manager: CollectionManager


@dataclass
class CollectionDependencies:
    config: Config
    collection_manager: CollectionManager


class CommandContext:
    """Centralized dependency factory for command/query operations."""

    def __init__(
        self,
        error_handler: Optional[ErrorHandler] = None,
        config_service: Optional[ConfigurationService] = None,
        *,
        indexing_service_factory: Optional[Callable[[ErrorHandler], IndexingService]] = None,
        search_service_factory: Optional[Callable[[ErrorHandler], SearchService]] = None,
        collection_manager_factory: Optional[Callable[[Config], CollectionManager]] = None,
        embedder_factory: Optional[Callable[[Config], OllamaEmbedder]] = None,
        vector_store_factory: Optional[Callable[[Config], QdrantVectorStore]] = None,
    ):
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = config_service or ConfigurationService(self.error_handler)
        self._indexing_service_factory = indexing_service_factory or (lambda handler: IndexingService(handler))
        self._search_service_factory = search_service_factory or (lambda handler: SearchService(handler))
        self._collection_manager_factory = collection_manager_factory or (lambda cfg: CollectionManager(cfg))
        self._embedder_factory = embedder_factory or (lambda cfg: OllamaEmbedder(cfg))
        self._vector_store_factory = vector_store_factory or (lambda cfg: QdrantVectorStore(cfg))

    def load_index_dependencies(
        self,
        workspace_path: str,
        config_path: str,
        overrides: Optional[Dict[str, object]] = None,
        logging_overrides: Optional[Dict[str, int]] = None,
    ) -> IndexDependencies:
        config = self.config_service.load_with_fallback(
            config_path=config_path,
            workspace_path=workspace_path,
            overrides=overrides,
        )

        self._apply_logging_configuration(config, logging_overrides)

        config = self._apply_operation_overrides(config, overrides)
        indexing_service = self._indexing_service_factory(self.error_handler)
        self._initialize_vector_store(config)
        return IndexDependencies(config=config, indexing_service=indexing_service)

    def load_search_dependencies(
        self,
        workspace_path: str,
        config_path: str,
        overrides: Optional[Dict[str, object]] = None,
        logging_overrides: Optional[Dict[str, int]] = None,
    ) -> SearchDependencies:
        config = self.config_service.load_with_fallback(
            config_path=config_path,
            workspace_path=workspace_path,
            overrides=overrides,
        )

        self._apply_logging_configuration(config, logging_overrides)

        config = self._apply_operation_overrides(config, overrides)
        search_service = self._search_service_factory(self.error_handler)
        collection_manager = self._collection_manager_factory(config)
        self._initialize_vector_store(config)
        return SearchDependencies(
            config=config,
            search_service=search_service,
            collection_manager=collection_manager,
        )

    def load_collection_dependencies(
        self,
        workspace_path: str,
        config_path: str,
        overrides: Optional[Dict[str, object]] = None,
        logging_overrides: Optional[Dict[str, int]] = None,
    ) -> CollectionDependencies:
        config = self.config_service.load_with_fallback(
            config_path=config_path,
            workspace_path=workspace_path,
            overrides=overrides,
        )

        self._apply_logging_configuration(config, logging_overrides)

        config = self._apply_operation_overrides(config, overrides)
        collection_manager = self._collection_manager_factory(config)
        self._initialize_vector_store(config)
        return CollectionDependencies(config=config, collection_manager=collection_manager)

    def _apply_logging_configuration(
        self,
        config: Config,
        logging_overrides: Optional[Dict[str, int]] = None,
    ) -> None:
        LoggingConfigurator.ensure_context_filter()
        LoggingConfigurator.ensure_processing_logger()

        component_levels = dict(getattr(config, "logging_component_levels", {}) or {})
        if logging_overrides:
            component_levels.update(logging_overrides)
        config.logging_component_levels = component_levels
        LoggingConfigurator.apply_component_levels(component_levels)

    def _apply_operation_overrides(self, config: Config, overrides: Optional[Dict[str, object]]) -> Config:
        """Re-apply overrides onto loaded config without reloading from disk."""
        if not overrides:
            return config
        updated = copy.deepcopy(config)
        for key, value in overrides.items():
            if hasattr(updated, key):
                setattr(updated, key, value)
        return updated

    def _initialize_vector_store(self, config: Config) -> None:
        """Ensure vector store is ready; validate embedder configuration."""
        embedder = self._embedder_factory(config)
        try:
            validation = embedder.validate_configuration()
            if isinstance(validation, dict) and not validation.get("valid", True):
                logger.warning(
                    "Embedder configuration validation reported issues: %s",
                    validation.get("error", "unknown error"),
                )
        except Exception as validation_error:
            logger.warning("Embedder validation failed: %s", validation_error)

        try:
            vector_store = self._vector_store_factory(config)
            vector_store.initialize()
        except Exception as initialization_error:
            logger.debug(
                "Vector store initialization failed: %s",
                initialization_error,
            )
