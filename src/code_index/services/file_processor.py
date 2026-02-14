"""
File processing services for Tree-sitter operations and indexing.

This module contains:
- TreeSitterFileProcessor: For Tree-sitter specific file filtering and validation
- FileProcessor: For indexing-specific individual file processing
"""

import os
import hashlib
import uuid
import logging
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import time
from threading import Lock


from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..parser import CodeParser
from ..embedder import OllamaEmbedder
from ..vector_store import QdrantVectorStore
from ..cache import CacheManager
from ..path_utils import PathUtils
from ..models import ProcessingResult
from .indexing_dependencies import IndexingDependencies
from .streaming_embedder import StreamingEmbedder, BatchResult


logger = logging.getLogger("code_index.file_processor")


class TreeSitterFileProcessor:
    """
    Service for processing and validating files for Tree-sitter operations.

    Handles:
    - File filtering based on configuration
    - Language-specific optimizations
    - File size validation
    - Path-based filtering
    """

    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """Initialize the TreeSitterFileProcessor."""
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        self._logger = logger
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)
        
        # Add scalability configuration
        self.enable_chunked_processing = getattr(config, "enable_chunked_processing", True)
        self.large_file_threshold = getattr(config, "large_file_threshold_bytes", 256 * 1024)
        self.streaming_threshold = getattr(config, "streaming_threshold_bytes", 1024 * 1024)
        self.default_chunk_size = getattr(config, "default_chunk_size_bytes", 64 * 1024)
        self.memory_threshold_mb = getattr(config, "memory_optimization_threshold_mb", 100)
        self.enable_progressive_indexing = getattr(config, "enable_progressive_indexing", True)

        # Read monitoring configuration settings
        monitoring_config = getattr(config, "monitoring", {})
        self.enable_performance_tracking = monitoring_config.get("enable_performance_tracking", False)
        self.log_mmap_metrics = monitoring_config.get("log_mmap_metrics", False)
        self.log_resource_usage = monitoring_config.get("log_resource_usage", False)
        self.log_per_file_metrics = monitoring_config.get("log_per_file_metrics", False)
        self.log_memory_usage = monitoring_config.get("log_memory_usage", False)
        self.log_mmap_statistics = monitoring_config.get("log_mmap_statistics", False)
        self.log_cache_performance = monitoring_config.get("log_cache_performance", False)
        self.log_cache_efficiency = monitoring_config.get("log_cache_efficiency", False)
        self.enable_detailed_logging = monitoring_config.get("enable_detailed_logging", False)
        self.performance_report_interval = monitoring_config.get("performance_report_interval", 30)
        self.log_file_processing_times = monitoring_config.get("log_file_processing_times", False)
        self.track_cross_platform_compatibility = monitoring_config.get("track_cross_platform_compatibility", False)

    def validate_file(self, file_path: str) -> bool:
        """Validate if a file should be processed by Tree-sitter."""
        try:
            if not os.path.exists(file_path):
                return False
            if not os.path.isfile(file_path):
                return False
            if not self._validate_file_size(file_path):
                return False
            if not self._should_process_file_for_treesitter(file_path):
                return False
            return True
        except Exception:
            return False

    def _validate_file_size(self, file_path: str) -> bool:
        """Validate file size against Tree-sitter limits."""
        try:
            max_size = getattr(self.config, "tree_sitter_max_file_size_bytes", 512 * 1024)
            file_size = os.path.getsize(file_path)
            return file_size <= max_size
        except (OSError, IOError):
            return False

    def _should_process_file_for_treesitter(self, file_path: str) -> bool:
        """Apply smart filtering like ignore patterns."""
        try:
            # Check for generated directories
            generated_dirs = ['target/', 'build/', 'dist/', 'node_modules/', '__pycache__/']
            if any(gen_dir in file_path for gen_dir in generated_dirs):
                return False

            # Skip empty files
            if os.path.getsize(file_path) == 0:
                return False

            # Check for binary files
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\0' in chunk:
                    return False

            return True
        except Exception:
            return False

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive information about a file."""
        info = {
            "path": file_path,
            "exists": False,
            "is_file": False,
            "size_bytes": 0,
            "extension": "",
            "is_valid": False,
            "should_process": False,
            "language_key": None,
            "optimizations": {}
        }

        try:
            path_obj = Path(file_path)
            if path_obj.exists() and path_obj.is_file():
                info["exists"] = True
                info["is_file"] = True
                info["size_bytes"] = path_obj.stat().st_size
                info["extension"] = path_obj.suffix.lower()
                info["is_valid"] = self.validate_file(file_path)
                info["should_process"] = info["is_valid"]
        except Exception:
            pass

        return info

    def _get_file_language(self, file_path: str) -> Optional[str]:
        """Get language key for a file."""
        try:
            from ..language_detection import LanguageDetector
            language_detector = LanguageDetector(self.config, self.error_handler)
            return language_detector.detect_language(file_path)
        except Exception:
            return None

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except (OSError, IOError):
            return 0


class FileProcessor:
    """
    Handles individual file processing for indexing operations.
    
    Responsibilities:
    - File hash computation for change detection
    - Individual file parsing into blocks
    - Embedding generation per file
    - Path sanitization and validation
    - Vector point preparation for storage
    - Parallel file processing for improved throughput
    
    Supports dependency injection via IndexingDependencies for testing.
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        error_handler: Optional[ErrorHandler] = None,
        parser: Optional[CodeParser] = None,
        embedder: Optional[OllamaEmbedder] = None,
        vector_store: Optional[QdrantVectorStore] = None,
        cache_manager: Optional[CacheManager] = None,
        path_utils: Optional[PathUtils] = None,
        dependencies: Optional[IndexingDependencies] = None,
        parallel_workers: int = 1
    ):
        """
        Initialize the file processor with dependencies.
        
        Args:
            config: Configuration object (optional if dependencies provided)
            error_handler: Error handler instance
            parser: Code parser instance
            embedder: Embedding generator instance
            vector_store: Vector storage instance
            cache_manager: Cache manager instance
            path_utils: Path utilities instance
            dependencies: IndexingDependencies instance for DI
            parallel_workers: Number of parallel workers (1 = sequential)
        """
        if dependencies is not None:
            self._dependencies = dependencies
            self.config = config or Config()
            self.error_handler = dependencies.error_handler
            self.parser = dependencies.parser
            self.embedder = dependencies.embedder
            self.vector_store = dependencies.vector_store
            self.cache_manager = dependencies.cache_manager
            self.path_utils = dependencies.path_utils
        else:
            self._dependencies = None
            self.config = config or Config()
            self.error_handler = error_handler or ErrorHandler()
            self.parser = parser
            self.embedder = embedder
            self.vector_store = vector_store
            self.cache_manager = cache_manager
            self.path_utils = path_utils
        
        self.logger = logging.getLogger(__name__)
        self.processing_logger = logging.getLogger("code_index.processing")
        
        # Initialize parallel processor if workers > 1
        self._parallel_processor = None
        self._parallel_workers = parallel_workers
        if parallel_workers > 1:
            from .parallel_file_processor import ParallelFileProcessor
            self._parallel_processor = ParallelFileProcessor(
                max_workers=parallel_workers,
                error_handler=None,  # Use internal error handling
                continue_on_error=True
            )
    
    def get_file_hash(self, file_path: str) -> str:
        """Compute hash of file content for change detection."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to compute hash for {file_path}: {e}")
            return ""
    
    def process_single_file(
        self,
        file_path: str,
        config: Optional[Config] = None,
        timed_out_files: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None,
        file_index: int = 0,
        total_files: int = 1,
        completed_count: int = 0
    ) -> Dict[str, Any]:
        """
        Process a single file: parse, embed, and store.
        
        Args:
            file_path: Path to the file
            config: Configuration object
            timed_out_files: List to track timed out files
            errors: List to collect errors
            warnings: List to collect warnings
            progress_callback: Optional progress callback
            file_index: Current file index
            total_files: Total files to process
            completed_count: Number of completed files
            
        Returns:
            Dictionary with processing result
        """
        result = {
            'success': False,
            'file_path': file_path,
            'blocks_processed': 0,
            'error': None
        }
        
        timed_out_files = timed_out_files or []
        errors = errors or []
        warnings = warnings or []
        cfg = config or self.config
        
        try:
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "start", 0)
            
            rel_path = self._get_relative_path(file_path, cfg.workspace_path)
            
            # Check if file has changed
            current_hash = self.get_file_hash(file_path)
            cached_hash = self.cache_manager.get_hash(file_path) if self.cache_manager else None
            
            if current_hash == cached_hash:
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                result['skipped'] = True
                return result
            
            # Parse file into blocks
            blocks = self.parser.parse_file(file_path) if self.parser else []
            
            if not blocks:
                if self.cache_manager:
                    self.cache_manager.update_hash(file_path, current_hash)
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                result['skipped'] = True
                result['reason'] = 'no_blocks'
                return result
            
            # Generate embeddings
            texts = [block.content for block in blocks if block.content.strip()]
            
            if not texts:
                if self.cache_manager:
                    self.cache_manager.update_hash(file_path, current_hash)
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                result['skipped'] = True
                result['reason'] = 'no_text_content'
                return result
            
            # Create embeddings in batches
            batch_size = getattr(cfg, "batch_segment_threshold", 10)
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                try:
                    embedding_response = self.embedder.create_embeddings(batch_texts)
                    all_embeddings.extend(embedding_response["embeddings"])
                except Exception as e:
                    error_context = ErrorContext(
                        component="file_processor",
                        operation="embed_batch",
                        file_path=rel_path
                    )
                    error_response = self.error_handler.handle_network_error(
                        e, error_context, "Ollama"
                    )
                    warnings.append(f"Embedding failed for {rel_path}: {error_response.message}")
                    break
            
            if len(all_embeddings) < len(texts) and len(all_embeddings) == 0:
                result['error'] = 'No embeddings generated'
                return result
            
            # Prepare points for vector store
            points = self._prepare_vector_points(
                file_path, blocks, all_embeddings, rel_path
            )
            
            # Store in vector database
            try:
                self.vector_store.delete_points_by_file_path(rel_path)
            except Exception:
                pass
            
            try:
                self.vector_store.upsert_points(points)
            except Exception as e:
                error_context = ErrorContext(
                    component="file_processor",
                    operation="upsert_points",
                    file_path=rel_path
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.DATABASE, ErrorSeverity.MEDIUM
                )
                errors.append(f"Failed to store vectors for {rel_path}: {error_response.message}")
                return result
            
            # Update cache
            if self.cache_manager:
                self.cache_manager.update_hash(file_path, current_hash)
            
            result['success'] = True
            result['blocks_processed'] = len(blocks)
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "success", len(blocks))
            
        except Exception as e:
            error_context = ErrorContext(
                component="file_processor",
                operation="process_file",
                file_path=file_path
            )
            error_response = self.error_handler.handle_file_error(
                e, error_context, "file_processing"
            )
            errors.append(f"Failed to process {file_path}: {error_response.message}")
            result['error'] = error_response.message
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "error", 0)
        
        return result
    
    def process_files_parallel(
        self,
        files: List[str],
        config: Optional[Config] = None,
        use_parallel: bool = True,
        progress_callback: Optional[Callable[[str, int, int, str, int], None]] = None,
        error_collector: Optional[List[str]] = None,
        warning_collector: Optional[List[str]] = None,
        timed_out_collector: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files with optional parallel execution.
        
        Args:
            files: List of file paths to process
            config: Configuration object
            use_parallel: Enable parallel processing (default: True)
            progress_callback: Optional progress callback(file, completed, total, status, blocks)
            error_collector: List to collect errors
            warning_collector: List to collect warnings
            timed_out_collector: List to collect timed out files
            
        Returns:
            List of processing results
            
        Example:
            >>> processor = FileProcessor(config, parallel_workers=4)
            >>> results = processor.process_files_parallel(
            ...     file_list, 
            ...     use_parallel=True,
            ...     progress_callback=on_progress
            ... )
        """
        if not files:
            return []
        
        errors = error_collector or []
        warnings = warning_collector or []
        timed_out_files = timed_out_collector or []
        cfg = config or self.config
        
        # Use parallel processing if enabled and available
        if use_parallel and self._parallel_processor and self._parallel_workers > 1:
            return self._process_files_parallel_impl(
                files, cfg, progress_callback, errors, warnings, timed_out_files
            )
        
        # Sequential fallback
        return self._process_files_sequential(
            files, cfg, progress_callback, errors, warnings, timed_out_files
        )
    
    def _process_files_parallel_impl(
        self,
        files: List[str],
        config: Config,
        progress_callback: Optional[Callable],
        errors: List[str],
        warnings: List[str],
        timed_out_files: List[str]
    ) -> List[Dict[str, Any]]:
        """Internal implementation of parallel file processing."""
        from .parallel_file_processor import ParallelProgressTracker
        
        # Create thread-local storage for error/warning collection
        thread_locals: Dict[int, Dict[str, List[str]]] = {}
        lock = Lock()
        completed_count = 0
        
        def process_wrapper(file_path: str) -> Dict[str, Any]:
            """Wrapper for thread-safe processing."""
            # Create thread-local error/warning collectors
            import threading
            thread_id = threading.get_ident()
            
            with lock:
                if thread_id not in thread_locals:
                    thread_locals[thread_id] = {
                        'errors': [],
                        'warnings': [],
                        'timed_out': []
                    }
            
            local_errors = thread_locals[thread_id]['errors']
            local_warnings = thread_locals[thread_id]['warnings']
            local_timed_out = thread_locals[thread_id]['timed_out']
            
            # Process the file
            result = self.process_single_file(
                file_path=file_path,
                config=config,
                timed_out_files=local_timed_out,
                errors=local_errors,
                warnings=local_warnings,
                progress_callback=None,  # We'll handle progress separately
                total_files=len(files),
                completed_count=0
            )
            
            return result
        
        def parallel_progress(current: int, total: int) -> None:
            """Progress callback for parallel processing."""
            nonlocal completed_count
            completed_count = current
            if progress_callback and current <= len(files):
                file_path = files[current - 1] if current > 0 else ""
                progress_callback(file_path, current, total, "processing", 0)
        
        # Process files in parallel
        parallel_results = self._parallel_processor.process_files(
            files=files,
            process_func=process_wrapper,
            progress_callback=parallel_progress
        )
        
        # Merge thread-local errors/warnings into main collectors
        for thread_data in thread_locals.values():
            errors.extend(thread_data['errors'])
            warnings.extend(thread_data['warnings'])
            timed_out_files.extend(thread_data['timed_out'])
        
        # Convert ProcessingResult objects to dictionaries
        results = []
        for i, parallel_result in enumerate(parallel_results):
            if parallel_result is None:
                # Failed to get any result
                results.append({
                    'success': False,
                    'file_path': files[i],
                    'blocks_processed': 0,
                    'error': 'Processing failed with no result'
                })
            elif hasattr(parallel_result, 'data') and parallel_result.data:
                # Use the result data directly
                results.append(parallel_result.data)
            else:
                # Create result from ProcessingResult
                results.append({
                    'success': parallel_result.success,
                    'file_path': parallel_result.file_path,
                    'blocks_processed': 0,
                    'error': parallel_result.error
                })
        
        return results
    
    def _process_files_sequential(
        self,
        files: List[str],
        config: Config,
        progress_callback: Optional[Callable],
        errors: List[str],
        warnings: List[str],
        timed_out_files: List[str]
    ) -> List[Dict[str, Any]]:
        """Sequential file processing fallback."""
        results = []
        
        for i, file_path in enumerate(files):
            result = self.process_single_file(
                file_path=file_path,
                config=config,
                timed_out_files=timed_out_files,
                errors=errors,
                warnings=warnings,
                progress_callback=progress_callback,
                file_index=i,
                total_files=len(files),
                completed_count=i
            )
            results.append(result)
        
        return results
    
    def _get_relative_path(self, file_path: str, workspace_path: str) -> str:
        """Get workspace-relative path or normalized path."""
        if self.path_utils:
            return self.path_utils.get_workspace_relative_path(file_path) or \
                   self.path_utils.normalize_path(file_path)
        
        try:
            file_p = Path(file_path)
            workspace_p = Path(workspace_path)
            if file_p.is_absolute() and workspace_p.is_absolute():
                rel_path = file_p.relative_to(workspace_p)
                return str(rel_path)
        except (ValueError, TypeError):
            pass
        
        return str(Path(file_path).name)
    
    def _prepare_vector_points(
        self,
        file_path: str,
        blocks: List,
        embeddings: List[List[float]],
        rel_path: str
    ) -> List[Dict[str, Any]]:
        """Prepare vector points for storage."""
        points = []
        
        for i, block in enumerate(blocks):
            if i >= len(embeddings):
                break
            
            point_id = str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{file_path}:{block.start_line}:{block.end_line}:{getattr(block, 'split_index', '')}"
            ))
            
            payload = {
                "filePath": rel_path,
                "codeChunk": block.content,
                "startLine": block.start_line,
                "endLine": block.end_line,
                "type": block.type,
                "embedding_model": getattr(self.embedder, 'model_identifier', 'unknown')
            }
            
            # Add split metadata if this block is part of a split
            if hasattr(block, 'split_index') and block.split_index is not None:
                payload["splitIndex"] = block.split_index
                payload["splitTotal"] = block.split_total
                payload["parentBlockId"] = block.parent_block_id
            
            point = {
                "id": point_id,
                "vector": embeddings[i],
                "payload": payload
            }
            points.append(point)
        
        return points
    
    def create_processing_result(
        self,
        file_path: str,
        success: bool,
        blocks_processed: int,
        processing_time: float,
        error: Optional[str] = None
    ) -> ProcessingResult:
        """Create a ProcessingResult object."""
        return ProcessingResult(
            file_path=file_path,
            success=success,
            blocks_processed=blocks_processed,
            processing_time_seconds=processing_time,
            error=error
        )
    
    def get_streaming_embedder(
        self,
        batch_size: Optional[int] = None,
        parallel_batches: int = 1,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> StreamingEmbedder:
        """
        Get a streaming embedder instance for memory-efficient processing.
        
        Args:
            batch_size: Override batch size (default from config)
            parallel_batches: Number of parallel batch processing threads
            progress_callback: Optional progress callback
            
        Returns:
            StreamingEmbedder instance
        """
        if batch_size is None:
            batch_size = getattr(self.config, "batch_segment_threshold", 32)
        return StreamingEmbedder(
            embedder=self.embedder,
            batch_size=batch_size,
            parallel_batches=parallel_batches,
            progress_callback=progress_callback,
            error_handler=self.error_handler
        )
    
    def process_single_file_streaming(
        self,
        file_path: str,
        config: Optional[Config] = None,
        timed_out_files: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None,
        file_index: int = 0,
        total_files: int = 1,
        completed_count: int = 0,
        batch_size: Optional[int] = None,
        on_batch: Optional[Callable[[BatchResult], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a single file using streaming embeddings for memory efficiency.
        
        This method processes embeddings in batches and yields results as they
        are computed, rather than accumulating all embeddings in memory.
        
        Args:
            file_path: Path to the file
            config: Configuration object
            timed_out_files: List to track timed out files
            errors: List to collect errors
            warnings: List to collect warnings
            progress_callback: Optional progress callback
            file_index: Current file index
            total_files: Total files to process
            completed_count: Number of completed files
            batch_size: Override batch size for streaming
            on_batch: Optional callback for each batch result
            
        Returns:
            Dictionary with processing result
        """
        result = {
            'success': False,
            'file_path': file_path,
            'blocks_processed': 0,
            'error': None
        }
        
        timed_out_files = timed_out_files or []
        errors = errors or []
        warnings = warnings or []
        cfg = config or self.config
        
        try:
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "start", 0)
            
            rel_path = self._get_relative_path(file_path, cfg.workspace_path)
            
            # Check if file has changed
            current_hash = self.get_file_hash(file_path)
            cached_hash = self.cache_manager.get_hash(file_path) if self.cache_manager else None
            
            if current_hash == cached_hash:
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                result['skipped'] = True
                return result
            
            # Parse file into blocks
            blocks = self.parser.parse_file(file_path) if self.parser else []
            
            if not blocks:
                if self.cache_manager:
                    self.cache_manager.update_hash(file_path, current_hash)
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                result['skipped'] = True
                result['reason'] = 'no_blocks'
                return result
            
            # Generate embeddings using streaming
            texts = [block.content for block in blocks if block.content.strip()]
            
            if not texts:
                if self.cache_manager:
                    self.cache_manager.update_hash(file_path, current_hash)
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                result['skipped'] = True
                result['reason'] = 'no_text_content'
                return result
            
            # Get streaming embedder
            streaming_embedder = self.get_streaming_embedder(
                batch_size=batch_size,
                progress_callback=None  # We handle progress separately
            )
            
            # Process embeddings in streaming fashion
            all_embeddings = []
            batch_index = 0
            total_batches = (len(texts) + streaming_embedder.batch_size - 1) // streaming_embedder.batch_size
            
            for embedding_batch in streaming_embedder.embed_stream(texts):
                all_embeddings.extend(embedding_batch)
            
                # Call batch callback if provided
                if on_batch:
                    batch_start = batch_index * streaming_embedder.batch_size
                    batch_end = min(batch_start + streaming_embedder.batch_size, len(texts))
                    batch_texts = texts[batch_start:batch_end]
                    batch_result = BatchResult(
                        chunks=batch_texts,
                        embeddings=embedding_batch,
                        batch_index=batch_index,
                        total_batches=total_batches
                    )
                    on_batch(batch_result)
            
                batch_index += 1
            
            if len(all_embeddings) < len(texts) and len(all_embeddings) == 0:
                result['error'] = 'No embeddings generated'
                return result
            
            # Prepare points for vector store
            points = self._prepare_vector_points(
                file_path, blocks, all_embeddings, rel_path
            )
            
            # Store in vector database
            try:
                self.vector_store.delete_points_by_file_path(rel_path)
            except Exception:
                pass
            
            try:
                self.vector_store.upsert_points(points)
            except Exception as e:
                error_context = ErrorContext(
                    component="file_processor",
                    operation="upsert_points",
                    file_path=rel_path
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.DATABASE, ErrorSeverity.MEDIUM
                )
                errors.append(f"Failed to store vectors for {rel_path}: {error_response.message}")
                return result
            
            # Update cache
            if self.cache_manager:
                self.cache_manager.update_hash(file_path, current_hash)
            
            result['success'] = True
            result['blocks_processed'] = len(blocks)
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "success", len(blocks))
            
        except Exception as e:
            error_context = ErrorContext(
                component="file_processor",
                operation="process_file_streaming",
                file_path=file_path
            )
            error_response = self.error_handler.handle_file_error(
                e, error_context, "file_processing"
            )
            errors.append(f"Failed to process {file_path}: {error_response.message}")
            result['error'] = error_response.message
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "error", 0)