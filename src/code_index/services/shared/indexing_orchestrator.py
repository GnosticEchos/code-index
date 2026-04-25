"""
Indexing orchestrator for coordinating indexing workflows.

Central coordinator that manages the indexing process by delegating
to FileProcessor and BatchManager while maintaining clean separation of concerns.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from ...config import Config
from ...config_service import ConfigurationService
from ...service_validation import ServiceValidator
from ...parser import CodeParser
from ...embedder import OllamaEmbedder
from ...vector_store import QdrantVectorStore
from ...cache import CacheManager
from ...path_utils import PathUtils
from ...models import IndexingResult, ValidationResult
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..treesitter.file_processor import FileProcessor
from ..batch.batch_manager import BatchManager
from ..core.search_service import SearchService
from ..shared.indexing_dependencies import IndexingDependencies


logger = logging.getLogger("code_index.orchestrator")


class IndexingOrchestrator:
    """
    Orchestrates the indexing workflow.
    
    Responsibilities:
    - Coordinate the indexing workflow
    - Delegate to FileProcessor and BatchManager
    - Handle lifecycle management
    - Create final results
    
    Supports dependency injection via IndexingDependencies for testing.
    """
    
    def __init__(
        self,
        error_handler: Optional[ErrorHandler] = None,
        dependencies: Optional[IndexingDependencies] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            error_handler: Optional error handler (used if dependencies not provided)
            dependencies: Optional IndexingDependencies instance for DI
        """
        if dependencies is not None:
            self._dependencies = dependencies
            self.error_handler = dependencies.error_handler
            self.config_service = dependencies.config_service
            self.service_validator = dependencies.service_validator
        else:
            self._dependencies = None
            self.error_handler = error_handler or ErrorHandler()
            self.config_service = ConfigurationService(self.error_handler)
            self.service_validator = ServiceValidator(self.error_handler)
        
        self.logger = logging.getLogger(__name__)
        self.processing_logger = logging.getLogger("code_index.processing")
    
    @property
    def dependencies(self) -> Optional[IndexingDependencies]:
        """Get dependencies instance."""
        return self._dependencies
    
    def initialize_components(self, config: Config):
        """
        Initialize all required components for indexing.
        
        Args:
            config: Configuration object
            
        Returns:
            Tuple of (parser, embedder, vector_store, cache_manager, path_utils)
        """
        if self._dependencies is not None and self._dependencies.chunking_strategy is not None:
            chunking_strategy = self._dependencies.chunking_strategy
        else:
            # Determine chunking strategy
            strategy_name = getattr(config, "chunking_strategy", "lines")
            if strategy_name == "treesitter":
                from ...chunking import TreeSitterChunkingStrategy
                chunking_strategy = TreeSitterChunkingStrategy(config)
            else:
                from ...chunking import LineChunkingStrategy
                chunking_strategy = LineChunkingStrategy(config)
        
        # Use dependencies or create new instances
        if self._dependencies is not None:
            parser = self._dependencies.parser
            embedder = self._dependencies.embedder
            vector_store = self._dependencies.vector_store
            cache_manager = self._dependencies.cache_manager
            path_utils = self._dependencies.path_utils
        else:
            parser = None
            embedder = None
            vector_store = None
            cache_manager = None
            path_utils = None
        
        # Initialize components if not provided
        if parser is None:
            parser = CodeParser(config, chunking_strategy)
        if embedder is None:
            embedder = OllamaEmbedder(config)
        if vector_store is None:
            vector_store = QdrantVectorStore(config)
        if cache_manager is None:
            cache_manager = CacheManager(config.workspace_path, config)
        if path_utils is None:
            path_utils = PathUtils(self.error_handler, config.workspace_path)
        
        return parser, embedder, vector_store, cache_manager, path_utils
    
    def index_workspace(
        self,
        workspace: str,
        config: Config,
        progress_callback: Optional[Callable[[str, int, int, str, int], None]] = None,
        file_processor: Optional[FileProcessor] = None,
        batch_manager: Optional[BatchManager] = None
    ) -> IndexingResult:
        """
        Execute complete workspace indexing workflow.
        
        Args:
            workspace: Path to the workspace to index
            config: Configuration object with indexing parameters
            progress_callback: Optional progress callback
            file_processor: Optional FileProcessor instance
            batch_manager: Optional BatchManager instance
            
        Returns:
            IndexingResult with detailed operation results
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        timed_out_files: List[str] = []
        
        try:
            # Validate workspace
            validation_result = self.validate_workspace(workspace, config)
            if not validation_result.valid:
                errors.extend(validation_result.errors)
                return self._create_result(
                    workspace, config, 0, 0, errors, warnings, 
                    timed_out_files, start_time
                )
            
            # Initialize components
            parser, embedder, vector_store, cache_manager, path_utils = \
                self.initialize_components(config)
            
            # Get file paths
            file_paths = self._get_file_paths(workspace, config)
            
            if not file_paths:
                warnings.append("No files found to process after filtering")
                return self._create_result(
                    workspace, config, 0, 0, errors, warnings,
                    timed_out_files, start_time
                )
            
            # Create FileProcessor if not provided
            if file_processor is None:
                file_processor = FileProcessor(
                    config, self.error_handler, parser, embedder,
                    vector_store, cache_manager, path_utils
                )
            
            # Create BatchManager if not provided
            if batch_manager is None:
                batch_manager = BatchManager(config, self.error_handler)
            
            vector_store.initialize()
            
            # Process files
            processed_count, total_blocks = self._process_files(
                file_paths, file_processor, batch_manager,
                timed_out_files, errors, warnings,
                progress_callback
            )
            
            return self._create_result(
                workspace, config, processed_count, total_blocks,
                errors, warnings, timed_out_files, start_time
            )
            
        except Exception as e:
            error_context = ErrorContext(
                component="indexing_orchestrator",
                operation="index_workspace",
                additional_data={"workspace": workspace}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.CRITICAL
            )
            errors.append(error_response.message)
            
            return self._create_result(
                workspace, config, 0, 0, errors, warnings,
                timed_out_files, start_time
            )
        
        finally:
            self._invalidate_cache(config)
    
    def validate_workspace(self, workspace: str, config: Config) -> ValidationResult:
        """
        Validate workspace before indexing.
        
        Args:
            workspace: Path to the workspace
            config: Configuration object
            
        Returns:
            ValidationResult with validation status
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        metadata: Dict[str, Any] = {}
        
        try:
            # Check if workspace exists
            if not Path(workspace).exists():
                errors.append(f"Workspace path does not exist: {workspace}")
            elif not Path(workspace).is_dir():
                errors.append(f"Workspace path is not a directory: {workspace}")
            else:
                metadata["workspace_exists"] = True
                
                # Check workspace permissions
                if not Path(workspace).is_absolute():
                    abs_workspace = str(Path(workspace).resolve())
                    metadata["absolute_path"] = abs_workspace
                else:
                    abs_workspace = workspace
                
                # Check read access
                try:
                    test_file = Path(abs_workspace) / ".git" / "config"
                    if test_file.exists():
                        test_file.read_text()
                    else:
                        list(Path(abs_workspace).iterdir())
                    metadata["read_access"] = True
                except PermissionError:
                    errors.append(f"No read access to workspace: {abs_workspace}")
                except Exception:
                    metadata["read_access"] = True
                
                # Check for project markers
                project_markers = ['.git', 'package.json', 'requirements.txt', 
                                   'Cargo.toml', 'pyproject.toml']
                found_markers = []
                for marker in project_markers:
                    if (Path(abs_workspace) / marker).exists():
                        found_markers.append(marker)
                
                if found_markers:
                    metadata["project_markers"] = found_markers
                    metadata["project_type"] = self._detect_project_type(found_markers)
                else:
                    warnings.append("No common project markers found")
                
                # Validate services
                service_results = self.service_validator.validate_all_services(config)
                failed_services = [r for r in service_results if not r.valid]
                
                if failed_services:
                    errors.extend([f"{r.service}: {r.error}" for r in failed_services])
                    metadata["service_validation"] = [r.to_dict() for r in service_results]
                else:
                    metadata["service_validation"] = [r.to_dict() for r in service_results]
            
            return ValidationResult(
                workspace_path=workspace,
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                validation_time_seconds=time.time() - start_time
            )
            
        except Exception as e:
            error_context = ErrorContext(
                component="indexing_orchestrator",
                operation="validate_workspace",
                additional_data={"workspace": workspace}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )
            errors.append(error_response.message)
            
            return ValidationResult(
                workspace_path=workspace,
                valid=False,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                validation_time_seconds=time.time() - start_time
            )
    
    def _get_file_paths(self, workspace: str, config: Config) -> List[str]:
        """Get list of file paths to process."""
        batch_manager = BatchManager(config, self.error_handler)
        return batch_manager.get_file_paths(workspace, config)
    
    def _process_files(
        self,
        file_paths: List[str],
        file_processor: FileProcessor,
        batch_manager: BatchManager,
        timed_out_files: List[str],
        errors: List[str],
        warnings: List[str],
        progress_callback: Optional[Callable] = None
    ) -> tuple[int, int]:
        """
        Process all files and return counts.
        
        Args:
            file_paths: List of file paths
            file_processor: FileProcessor instance
            batch_manager: BatchManager instance
            timed_out_files: List to track timed out files
            errors: List to collect errors
            warnings: List to collect warnings
            progress_callback: Optional progress callback
            
        Returns:
            Tuple of (processed_count, total_blocks)
        """
        processed_count = 0
        skipped_count = 0
        total_blocks = 0
        
        total_files = len(file_paths)
        
        if progress_callback and total_files:
            progress_callback("", 0, total_files, "init", 0)
        
        for file_index, file_path in enumerate(file_paths, start=1):
            completed_count = processed_count + skipped_count
            
            result = file_processor.process_single_file(
                file_path=file_path,
                config=file_processor.config,
                timed_out_files=timed_out_files,
                errors=errors,
                warnings=warnings,
                progress_callback=progress_callback,
                file_index=file_index,
                total_files=total_files,
                completed_count=completed_count
            )
            
            if result.get('success'):
                processed_count += 1
                total_blocks += result.get('blocks_processed', 0)
            elif result.get('skipped'):
                skipped_count += 1
        
        return processed_count, total_blocks
    
    def _create_result(
        self,
        workspace: str,
        config: Config,
        processed_count: int,
        total_blocks: int,
        errors: List[str],
        warnings: List[str],
        timed_out_files: List[str],
        start_time: float
    ) -> IndexingResult:
        """Create IndexingResult object."""
        return IndexingResult(
            processed_files=processed_count,
            total_blocks=total_blocks,
            errors=errors,
            warnings=warnings,
            timed_out_files=timed_out_files,
            processing_time_seconds=time.time() - start_time,
            timestamp=datetime.now(),
            workspace_path=workspace,
            config_summary=self.config_service.get_config_summary(config)
        )
    
    def _detect_project_type(self, markers: List[str]) -> str:
        """Detect project type based on found markers."""
        if 'package.json' in markers:
            return 'nodejs'
        elif 'requirements.txt' in markers or 'pyproject.toml' in markers:
            return 'python'
        elif 'Cargo.toml' in markers:
            return 'rust'
        elif '.git' in markers:
            return 'git_repository'
        else:
            return 'unknown'
    
    def _invalidate_cache(self, config: Config):
        """Invalidate search cache after indexing."""
        try:
            SearchService.invalidate_workspace_cache(config.workspace_path)
        except Exception:
            self.logger.debug("Failed to invalidate search cache", exc_info=True)