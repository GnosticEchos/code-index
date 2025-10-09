"""Shared command/query orchestration context for CLI and MCP front-ends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from ..config import Config
from ..config_service import ConfigurationService
from ..errors import ErrorHandler
from ..logging_utils import LoggingConfigurator
from ..collections import CollectionManager
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
    ):
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = config_service or ConfigurationService(self.error_handler)

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

        indexing_service = IndexingService(self.error_handler)
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

        search_service = SearchService(self.error_handler)
        collection_manager = CollectionManager(config)
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

        collection_manager = CollectionManager(config)
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
