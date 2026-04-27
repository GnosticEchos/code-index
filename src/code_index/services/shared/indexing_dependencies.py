"""
Dependency injection factories for IndexingService.

This module provides:
- IndexingDependencies: Dataclass for injectable dependencies
- _create_default_dependencies(): Creates production dependencies
- _create_test_dependencies(): Creates test-friendly dependencies with mocks
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from ...config import Config
from ...config_service import ConfigurationService
from ...file_processing import FileProcessingService
from ...service_validation import ServiceValidator
from ...parser import CodeParser
from ...embedder import OllamaEmbedder
from ...vector_store import QdrantVectorStore
from ...cache import CacheManager
from ...path_utils import PathUtils
from ...scanner import DirectoryScanner
from ...chunking import (
    ChunkingStrategy,
    LineChunkingStrategy,
    TreeSitterChunkingStrategy,
)
from ...errors import ErrorHandler

if TYPE_CHECKING:
    from ..treesitter.file_processor import FileProcessor
    from ..batch.batch_manager import BatchManager
    from .indexing_orchestrator import IndexingOrchestrator


logger = logging.getLogger(__name__)


@dataclass
class IndexingDependencies:
    """
    Dependency container for IndexingService and its components.
    
    This dataclass allows for optional injection of dependencies,
    enabling both production use and easy testing with mocks.
    
    Attributes:
        error_handler: Error handling instance
        config_service: Configuration service for loading/parsing configs
        file_processing_service: Service for file processing operations
        service_validator: Service for validating dependencies
        parser: Code parser instance (lazy)
        embedder: Embedding generator instance (lazy)
        vector_store: Vector storage instance (lazy)
        cache_manager: Cache manager instance (lazy)
        path_utils: Path utilities instance (lazy)
        scanner: Directory scanner instance (lazy)
        chunking_strategy: Chunking strategy instance (lazy)
    """
    error_handler: ErrorHandler = field(default_factory=ErrorHandler)
    config_service: ConfigurationService = field(default=None)
    file_processing_service: FileProcessingService = field(default=None)
    service_validator: ServiceValidator = field(default=None)
    parser: Optional[CodeParser] = None
    embedder: Optional[OllamaEmbedder] = None
    vector_store: Optional[QdrantVectorStore] = None
    cache_manager: Optional[CacheManager] = None
    path_utils: Optional[PathUtils] = None
    scanner: Optional[DirectoryScanner] = None
    chunking_strategy: Optional[ChunkingStrategy] = None
    
    def __post_init__(self):
        """Initialize default services if not provided."""
        if self.error_handler is None:
            self.error_handler = ErrorHandler()
        if self.config_service is None:
            self.config_service = ConfigurationService(self.error_handler)
        if self.file_processing_service is None:
            self.file_processing_service = FileProcessingService(self.error_handler)
        if self.service_validator is None:
            self.service_validator = ServiceValidator(self.error_handler)
    
    def initialize_for_config(self, config: Config) -> "IndexingDependencies":
        """
        Initialize lazy dependencies based on configuration.
        
        Args:
            config: Configuration object
            
        Returns:
            Self with all dependencies initialized
        """
        if self.chunking_strategy is None:
            self.chunking_strategy = self._create_chunking_strategy(config)
        
        if self.parser is None:
            self.parser = CodeParser(config, self.chunking_strategy)
        
        if self.embedder is None:
            self.embedder = OllamaEmbedder(config)
        
        if self.vector_store is None:
            self.vector_store = QdrantVectorStore(config)
        
        if self.cache_manager is None:
            self.cache_manager = CacheManager(config.workspace_path, config)
        
        if self.path_utils is None:
            self.path_utils = PathUtils(self.error_handler, config.workspace_path)
        
        if self.scanner is None:
            self.scanner = DirectoryScanner(config)
        
        return self
    
    def _create_chunking_strategy(self, config: Config) -> ChunkingStrategy:
        """Create chunking strategy based on configuration."""
        strategy_name = getattr(config, "chunking_strategy", "lines")

        if strategy_name == "treesitter":
            return TreeSitterChunkingStrategy(config)
        elif strategy_name == "tokens":
            # Token-based chunking uses line-based approach with token-aware sizing
            return LineChunkingStrategy(config)
        else:
            return LineChunkingStrategy(config)
    
    def create_orchestrator(self) -> "IndexingOrchestrator":
        """
        Create an IndexingOrchestrator with these dependencies.
        
        Returns:
            Configured IndexingOrchestrator instance
        """
        from .indexing_orchestrator import IndexingOrchestrator
        return IndexingOrchestrator(dependencies=self)
    
    def create_file_processor(self) -> "FileProcessor":
        """
        Create a FileProcessor with these dependencies.
        
        Returns:
            Configured FileProcessor instance
        """
        from ..treesitter.file_processor import FileProcessor
        return FileProcessor(dependencies=self)
    
    def create_batch_manager(self) -> "BatchManager":
        """
        Create a BatchManager with these dependencies.
        
        Returns:
            Configured BatchManager instance
        """
        from ..batch.batch_manager import BatchManager
        return BatchManager(dependencies=self)


def _create_default_dependencies(
    error_handler: Optional[ErrorHandler] = None,
    config: Optional[Config] = None
) -> IndexingDependencies:
    """
    Create production default dependencies.
    
    Args:
        error_handler: Optional error handler (creates default if not provided)
        config: Optional configuration (initializes lazy deps if provided)
        
    Returns:
        IndexingDependencies with production-ready defaults
    """
    deps = IndexingDependencies(
        error_handler=error_handler or ErrorHandler(),
        config_service=None,
        file_processing_service=None,
        service_validator=None,
        parser=None,
        embedder=None,
        vector_store=None,
        cache_manager=None,
        path_utils=None,
        scanner=None,
        chunking_strategy=None,
    )
    
    if config is not None:
        deps.initialize_for_config(config)
    
    return deps


def _create_test_dependencies(
    error_handler: Optional[ErrorHandler] = None,
    mock_parser: Optional[object] = None,
    mock_embedder: Optional[object] = None,
    mock_vector_store: Optional[object] = None,
    mock_cache_manager: Optional[object] = None,
    mock_path_utils: Optional[object] = None,
    mock_scanner: Optional[object] = None,
) -> IndexingDependencies:
    """
    Create test-friendly dependencies with mockable components.
    
    This is useful for unit testing where you want to inject mocks
    for external dependencies like parsers, embedders, and vector stores.
    
    Args:
        error_handler: Optional error handler (creates default if not provided)
        mock_parser: Mock parser instance (optional)
        mock_embedder: Mock embedder instance (optional)
        mock_vector_store: Mock vector store instance (optional)
        mock_cache_manager: Mock cache manager instance (optional)
        mock_path_utils: Mock path utilities instance (optional)
        mock_scanner: Mock directory scanner instance (optional)
        
    Returns:
        IndexingDependencies with test-friendly defaults
    """
    deps = IndexingDependencies(
        error_handler=error_handler or ErrorHandler(),
        config_service=None,
        file_processing_service=None,
        service_validator=None,
        parser=mock_parser,
        embedder=mock_embedder,
        vector_store=mock_vector_store,
        cache_manager=mock_cache_manager,
        path_utils=mock_path_utils,
        scanner=mock_scanner,
        chunking_strategy=None,
    )
    
    return deps
