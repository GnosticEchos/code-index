"""
Services for CQRS pattern implementation and Tree-sitter operations.

This package contains command and query services that separate
business logic from presentation layer concerns, plus specialized
Tree-sitter services for file processing, resource management,
block extraction, query execution, configuration management,
batch processing, and parallel file processing.

Organization:
- core/: Main service entry points
- query/: CQRS read operations
- command/: CQRS write operations
- treesitter/: Tree-sitter specialized services
- batch/: Batch processing and parallel execution
- embedding/: Embedding and caching services
- shared/: Common utilities and helpers
"""

# Core service imports
from .core.search_service import SearchService
from .core.indexing_service import IndexingService
from .core.configuration_service import ConfigurationService, QueryCache

# Query services (CQRS read operations)
from .query.configuration_query_service import ConfigurationQueryService
from .query.query_executor import TreeSitterQueryExecutor
from .query.query_embedding_cache import QueryEmbeddingCache

# Command services (CQRS write operations)
from .command.configuration_command_service import ConfigurationCommandService
from .command.config_overrides import build_index_overrides, build_search_overrides

# Shared utilities
from .shared.health_service import HealthService
from .shared.workspace_service import WorkspaceService
from .shared.command_context import CommandContext, IndexDependencies, SearchDependencies, CollectionDependencies

# Batch processing services
from .batch.batch_processor import TreeSitterBatchProcessor, BatchProcessingResult
from .batch.batch_manager import BatchManager
from .batch.batch_utils import BatchProgressTracker

# Parallel file processing
from .batch.parallel_file_processor import (
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
from .shared.indexing_dependencies import (
    IndexingDependencies,
    _create_default_dependencies,
    _create_test_dependencies,
)

# Embedding services
from .embedding.streaming_embedder import StreamingEmbedder, BatchResult
from .embedding.embedding_cache import EmbeddingCache

# Tree-sitter specialized services
from .treesitter.file_processor import FileProcessor
from .treesitter.treesitter_file_processor import TreeSitterFileProcessor
from .treesitter.resource_manager import TreeSitterResourceManager
from .treesitter.block_extractor import TreeSitterBlockExtractor, ExtractionResult
from .treesitter.tree_sitter_coordinator import TreeSitterChunkCoordinator
from .command.config_manager import TreeSitterConfigurationManager

__all__ = [
    # Core services
    'SearchService',
    'IndexingService',
    'ConfigurationService',
    'QueryCache',
    
    # Query services (CQRS)
    'ConfigurationQueryService',
    'TreeSitterQueryExecutor',
    'QueryEmbeddingCache',
    
    # Command services (CQRS)
    'ConfigurationCommandService',
    'build_index_overrides',
    'build_search_overrides',
    
    # Shared utilities
    'HealthService',
    'WorkspaceService',
    'CommandContext',
    'IndexDependencies',
    'SearchDependencies',
    'CollectionDependencies',
    
    # Tree-sitter services
    'TreeSitterFileProcessor',
    'FileProcessor',
    'TreeSitterResourceManager',
    'TreeSitterBlockExtractor',
    'ExtractionResult',
    'TreeSitterChunkCoordinator',
    'TreeSitterConfigurationManager',
    
    # Batch processing
    'TreeSitterBatchProcessor',
    'BatchProcessingResult',
    'BatchManager',
    'BatchProgressTracker',
    
    # Parallel processing
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
    
    # Embedding
    'StreamingEmbedder',
    'BatchResult',
    'EmbeddingCache',
]

# Backward compatibility - map old submodule imports to new locations
_SUBMODULE_MAP = {
    'search_service': '.core.search_service',
    'indexing_service': '.core.indexing_service', 
    'configuration_service': '.core.configuration_service',
    'configuration_query_service': '.query.configuration_query_service',
    'query_executor': '.query.query_executor',
    'query_embedding_cache': '.query.query_embedding_cache',
    'configuration_command_service': '.command.configuration_command_service',
    'config_overrides': '.command.config_overrides',
    'config_manager': '.command.config_manager',
    'health_service': '.shared.health_service',
    'workspace_service': '.shared.workspace_service',
    'command_context': '.shared.command_context',
    'indexing_dependencies': '.shared.indexing_dependencies',
    'indexing_orchestrator': '.shared.indexing_orchestrator',
    'batch_processor': '.batch.batch_processor',
    'batch_manager': '.batch.batch_manager',
    'batch_utils': '.batch.batch_utils',
    'parallel_file_processor': '.batch.parallel_file_processor',
    'file_processor': '.treesitter.file_processor',
    'resource_manager': '.treesitter.resource_manager',
    'block_extractor': '.treesitter.block_extractor',
    'tree_sitter_coordinator': '.treesitter.tree_sitter_coordinator',
    'streaming_embedder': '.embedding.streaming_embedder',
    'embedding_cache': '.embedding.embedding_cache',
    'config_loader': '.command.config_loader',
    'dimension_validator': '.embedding.dimension_validator',
}

def __getattr__(name):
    if name in _SUBMODULE_MAP:
        import importlib
        return importlib.import_module(_SUBMODULE_MAP[name], __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")