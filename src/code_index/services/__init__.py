"""
Services for CQRS pattern implementation and Tree-sitter operations.

This package contains command and query services that separate
business logic from presentation layer concerns, plus specialized
Tree-sitter services for file processing, resource management,
block extraction, query execution, configuration management,
batch processing, and parallel file processing.
"""

from .indexing_service import IndexingService
from .search_service import SearchService
from .configuration_service import ConfigurationService
from .configuration_query_service import ConfigurationQueryService
from .configuration_command_service import ConfigurationCommandService
from .health_service import HealthService
from .workspace_service import WorkspaceService
from .command_context import CommandContext
from .config_overrides import build_index_overrides, build_search_overrides

# Tree-sitter specialized services
from .file_processor import TreeSitterFileProcessor, FileProcessor
from .resource_manager import TreeSitterResourceManager
from .block_extractor import TreeSitterBlockExtractor
from .query_executor import TreeSitterQueryExecutor
from .config_manager import TreeSitterConfigurationManager
from .batch_processor import TreeSitterBatchProcessor

# Indexing decomposition services
from .indexing_orchestrator import IndexingOrchestrator
from .batch_manager import BatchManager

# Streaming embeddings
from .streaming_embedder import StreamingEmbedder, BatchResult
from .batch_utils import BatchProgressTracker

# Parallel file processing
from .parallel_file_processor import (
    ParallelFileProcessor,
    ProcessingOrder,
    ProcessingResult,
    ErrorHandler,
    ErrorContext,
    ParallelProcessingError,
    ThreadSafeResultCollector,
    ParallelProgressTracker,
)

# Dependency injection
from .indexing_dependencies import (
    IndexingDependencies,
    _create_default_dependencies,
    _create_test_dependencies,
)

# Query embedding cache
from .embedding_cache import EmbeddingCache
from .query_embedding_cache import QueryEmbeddingCache

__all__ = [
    # Core indexing services
    'IndexingService',
    'SearchService',
    'ConfigurationService',
    'ConfigurationQueryService',
    'ConfigurationCommandService',
    'HealthService',
    'WorkspaceService',
    'CommandContext',
    'build_index_overrides',
    'build_search_overrides',
    
    # Tree-sitter specialized services
    'TreeSitterFileProcessor',
    'TreeSitterResourceManager',
    'TreeSitterBlockExtractor',
    'TreeSitterQueryExecutor',
    'TreeSitterConfigurationManager',
    'TreeSitterBatchProcessor',
    
    # Indexing decomposition services
    'IndexingOrchestrator',
    'FileProcessor',
    'BatchManager',
    
    # Streaming embeddings
    'StreamingEmbedder',
    'BatchResult',
    'BatchProgressTracker',
    
    # Parallel file processing
    'ParallelFileProcessor',
    'ProcessingOrder',
    'ProcessingResult',
    'ErrorHandler',
    'ErrorContext',
    'ParallelProcessingError',
    'ThreadSafeResultCollector',
    'ParallelProgressTracker',
    
    # Dependency injection
    'IndexingDependencies',
    '_create_default_dependencies',
    '_create_test_dependencies',
    
    # Query embedding cache
    'EmbeddingCache',
    'QueryEmbeddingCache',
]