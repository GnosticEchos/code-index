"""
IndexingService for CQRS pattern implementation.

This service acts as a facade for indexing operations, delegating to
specialized services: IndexingOrchestrator, FileProcessor, and BatchManager.

This refactoring extracts:
- Orchestration logic -> IndexingOrchestrator
- Individual file processing -> FileProcessor
- Batch operations -> BatchManager
"""

import time
import logging
from typing import List, Optional, Callable

from ...config import Config
from ...config_service import ConfigurationService
from ...file_processing import FileProcessingService
from ...service_validation import ServiceValidator
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ...models import IndexingResult, ProcessingResult, ValidationResult
from ..shared.indexing_orchestrator import IndexingOrchestrator
from ..treesitter.file_processor import FileProcessor
from ..batch.batch_manager import BatchManager
from ..shared.indexing_dependencies import IndexingDependencies, _create_default_dependencies


class IndexingService:
    """
    Service for handling workspace indexing operations.
    
    This service acts as a facade, delegating to specialized services:
    - IndexingOrchestrator: Coordinates the indexing workflow
    - FileProcessor: Handles individual file processing
    - BatchManager: Manages batch operations
    
    Public API maintained for backward compatibility.
    
    Supports dependency injection via IndexingDependencies for testing.
    """
    
    def __init__(
        self,
        error_handler: Optional[ErrorHandler] = None,
        dependencies: Optional[IndexingDependencies] = None
    ):
        """
        Initialize the IndexingService with required dependencies.
        
        Args:
            error_handler: Optional error handler (used if dependencies not provided)
            dependencies: Optional IndexingDependencies instance for DI
        """
        if dependencies is not None:
            self._dependencies = dependencies
            self.error_handler = dependencies.error_handler
            self.config_service = dependencies.config_service
            self.file_processor_service = dependencies.file_processing_service
            self.service_validator = dependencies.service_validator
        else:
            self._dependencies = None
            self.error_handler = error_handler or ErrorHandler()
            self.config_service = ConfigurationService(self.error_handler)
            self.file_processor_service = FileProcessingService(self.error_handler)
            self.service_validator = ServiceValidator(self.error_handler)
        
        self.logger = logging.getLogger(__name__)
        self.processing_logger = logging.getLogger("code_index.processing")
        
        # Specialized services (lazy initialization)
        self._orchestrator: Optional[IndexingOrchestrator] = None
        self._file_processor: Optional[FileProcessor] = None
        self._batch_manager: Optional[BatchManager] = None
    
    @property
    def dependencies(self) -> IndexingDependencies:
        """Get or create dependencies instance."""
        if self._dependencies is None:
            self._dependencies = _create_default_dependencies(self.error_handler)
        return self._dependencies
    
    @dependencies.setter
    def dependencies(self, value: IndexingDependencies):
        """Set dependencies instance and reset lazy services."""
        self._dependencies = value
        self.error_handler = value.error_handler
        self.config_service = value.config_service
        self.file_processor_service = value.file_processing_service
        self.service_validator = value.service_validator
        # Reset lazy services to use new dependencies
        self._orchestrator = None
        self._file_processor = None
        self._batch_manager = None
    
    @property
    def orchestrator(self) -> IndexingOrchestrator:
        """Get or create IndexingOrchestrator instance."""
        if self._orchestrator is None:
            if self._dependencies is not None:
                self._orchestrator = self.dependencies.create_orchestrator()
            else:
                self._orchestrator = IndexingOrchestrator(error_handler=self.error_handler)
        return self._orchestrator
    
    @property
    def file_processor(self) -> FileProcessor:
        """Get or create FileProcessor instance."""
        if self._file_processor is None:
            if self._dependencies is not None:
                self._file_processor = self.dependencies.create_file_processor()
            else:
                self._file_processor = FileProcessor(
                    Config() if not hasattr(self, '_config') else self._config,
                    self.error_handler
                )
        return self._file_processor
    
    @property
    def batch_manager(self) -> BatchManager:
        """Get or create BatchManager instance."""
        if self._batch_manager is None:
            if self._dependencies is not None:
                self._batch_manager = self.dependencies.create_batch_manager()
            else:
                self._batch_manager = BatchManager(
                    Config() if not hasattr(self, '_config') else self._config,
                    self.error_handler
                )
        return self._batch_manager
    
    def index_workspace(
        self,
        workspace: str,
        config: Config,
        progress_callback: Optional[Callable[[str, int, int, str, int], None]] = None,
    ) -> IndexingResult:
        """
        Execute indexing command for a workspace.
        
        Delegates to IndexingOrchestrator.index_workspace().
        
        Args:
            workspace: Path to the workspace to index
            config: Configuration object with indexing parameters
            progress_callback: Optional progress callback
            
        Returns:
            IndexingResult with detailed operation results
        """
        # Store config for lazy service initialization
        self._config = config
        
        return self.orchestrator.index_workspace(
            workspace=workspace,
            config=config,
            progress_callback=progress_callback
        )
    
    def process_files(self, files: List[str], config: Config) -> List[ProcessingResult]:
        """
        Process a list of files for indexing.
        
        Delegates to FileProcessor for individual file processing.
        
        Args:
            files: List of file paths to process
            config: Configuration object with processing parameters
            
        Returns:
            List of ProcessingResult objects for each file
        """
        results: List[ProcessingResult] = []
        
        try:
            # Initialize components
            parser, embedder, vector_store, cache_manager, path_utils = \
                self.orchestrator.initialize_components(config)
            
            # Create FileProcessor with components
            processor = FileProcessor(
                config, self.error_handler, parser, embedder,
                vector_store, cache_manager, path_utils
            )
            
            for file_path in files:
                start_time = time.time()
                
                result = processor.process_single_file(
                    file_path=file_path,
                    config=config
                )
                
                processing_time = time.time() - start_time
                
                results.append(ProcessingResult(
                    file_path=file_path,
                    success=result.get('success', False),
                    blocks_processed=result.get('blocks_processed', 0),
                    processing_time_seconds=processing_time,
                    error=result.get('error')
                ))
        
        except Exception as e:
            error_context = ErrorContext(
                component="indexing_service",
                operation="process_files"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.HIGH
            )
            
            # Mark remaining files as failed
            for file_path in files[len(results):]:
                results.append(ProcessingResult(
                    file_path=file_path,
                    success=False,
                    blocks_processed=0,
                    error=error_response.message
                ))
        
        return results
    
    def validate_workspace(self, workspace: str, config: Config) -> ValidationResult:
        """
        Validate workspace before indexing.
        
        Delegates to IndexingOrchestrator.validate_workspace().
        
        Args:
            workspace: Path to the workspace to validate
            config: Configuration object with validation parameters
            
        Returns:
            ValidationResult with validation status and details
        """
        return self.orchestrator.validate_workspace(workspace, config)