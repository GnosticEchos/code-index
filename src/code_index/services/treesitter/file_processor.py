"""
File processing services for Tree-sitter operations and indexing.
This module contains:
- TreeSitterFileProcessor: For Tree-sitter specific file filtering and validation
- FileProcessor: For indexing-specific individual file processing
"""
import logging
from typing import Optional, Dict, Any, List, Callable
from threading import Lock
from ...config import Config
from ...errors import ErrorHandler, ErrorContext
from ...parser import CodeParser
from ...embedder import OllamaEmbedder
from ...vector_store import QdrantVectorStore
from ...cache import CacheManager
from ...path_utils import PathUtils
from ...models import ProcessingResult
from ..shared.indexing_dependencies import IndexingDependencies
from ..embedding.streaming_embedder import StreamingEmbedder, BatchResult
from ..shared import file_processing_helpers as helpers
logger = logging.getLogger("code_index.file_processor")
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
        return helpers.compute_file_hash(file_path, self.logger)
    
    def process_single_file(self, file_path: str, config: Optional[Config] = None, timed_out_files: Optional[List[str]] = None,
                           errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None,
                           progress_callback: Optional[Callable] = None, file_index: int = 0, total_files: int = 1,
                           completed_count: int = 0) -> Dict[str, Any]:
        result = helpers.init_result(file_path)
        timed_out_files, errors, warnings = timed_out_files or [], errors or [], warnings or []
        cfg = config or self.config
        
        try:
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "start", 0)
            
            rel_path = self._get_relative_path(file_path, cfg.workspace_path)
            current_hash = self.get_file_hash(file_path)
            
            if helpers.check_file_changed(file_path, self.cache_manager, current_hash):
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                return helpers.handle_skip(file_path, current_hash, self.cache_manager, progress_callback, completed_count, total_files)
            
            blocks = helpers.get_file_blocks(self.parser, file_path)
            if not blocks:
                return helpers.handle_skip(file_path, current_hash, self.cache_manager, progress_callback, completed_count, total_files, 'no_blocks')
            
            texts = helpers.extract_texts_from_blocks(blocks)
            if not texts:
                return helpers.handle_skip(file_path, current_hash, self.cache_manager, progress_callback, completed_count, total_files, 'no_text_content')
            
            batch_size = getattr(cfg, "batch_segment_threshold", 10)
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                try:
                    embedding_response = self.embedder.create_embeddings(batch_texts)
                    all_embeddings.extend(embedding_response["embeddings"])
                except Exception as e:
                    error_context = ErrorContext(component="file_processor", operation="embed_batch", file_path=rel_path)
                    error_response = self.error_handler.handle_network_error(e, error_context, "Ollama")
                    warnings.append(f"Embedding failed for {rel_path}: {error_response.message}")
                    break
            
            if len(all_embeddings) < len(texts) and len(all_embeddings) == 0:
                result['error'] = 'No embeddings generated'
                return result
            
            points = self._prepare_vector_points(file_path, blocks, all_embeddings, rel_path)
            
            if not helpers.store_vectors(self.vector_store, rel_path, points, errors, self.error_handler, rel_path):
                return result
            
            helpers.update_cache(self.cache_manager, file_path, current_hash)
            result['success'] = True
            result['blocks_processed'] = len(blocks)
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "success", len(blocks))
            
        except Exception as e:
            error_context = ErrorContext(component="file_processor", operation="process_file", file_path=file_path)
            error_response = self.error_handler.handle_file_error(e, error_context, "file_processing")
            errors.append(f"Failed to process {file_path}: {error_response.message}")
            result['error'] = error_response.message
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "error", 0)
        
        return result
    
    def process_files_parallel(self, files: List[str], config: Optional[Config] = None, use_parallel: bool = True,
                              progress_callback: Optional[Callable] = None, error_collector: Optional[List[str]] = None,
                              warning_collector: Optional[List[str]] = None, timed_out_collector: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if not files:
            return []
        errors, warnings, timed_out_files = error_collector or [], warning_collector or [], timed_out_collector or []
        cfg = config or self.config
        if use_parallel and self._parallel_processor and self._parallel_workers > 1:
            return self._process_files_parallel_impl(files, cfg, progress_callback, errors, warnings, timed_out_files)
        return self._process_files_sequential(files, cfg, progress_callback, errors, warnings, timed_out_files)
    
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
        return helpers.get_relative_path(file_path, workspace_path, self.path_utils)
    
    def _prepare_vector_points(self, file_path: str, blocks: List, embeddings: List[List[float]], rel_path: str) -> List[Dict[str, Any]]:
        """Prepare vector points for storage."""
        return helpers.prepare_vector_points(file_path, blocks, embeddings, rel_path, self.embedder)
    
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
    
    def process_single_file_streaming(self, file_path: str, config: Optional[Config] = None, timed_out_files: Optional[List[str]] = None,
                                      errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None,
                                      progress_callback: Optional[Callable] = None, file_index: int = 0, total_files: int = 1,
                                      completed_count: int = 0, batch_size: Optional[int] = None,
                                      on_batch: Optional[Callable[[BatchResult], None]] = None) -> Dict[str, Any]:
        result = helpers.init_result(file_path)
        timed_out_files, errors, warnings = timed_out_files or [], errors or [], warnings or []
        cfg = config or self.config
        
        try:
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "start", 0)
            
            rel_path = self._get_relative_path(file_path, cfg.workspace_path)
            current_hash = self.get_file_hash(file_path)
            
            if helpers.check_file_changed(file_path, self.cache_manager, current_hash):
                if progress_callback:
                    progress_callback(file_path, completed_count, total_files, "skipped", 0)
                return helpers.handle_skip(file_path, current_hash, self.cache_manager, progress_callback, completed_count, total_files)
            
            blocks = helpers.get_file_blocks(self.parser, file_path)
            if not blocks:
                return helpers.handle_skip(file_path, current_hash, self.cache_manager, progress_callback, completed_count, total_files, 'no_blocks')
            
            texts = helpers.extract_texts_from_blocks(blocks)
            if not texts:
                return helpers.handle_skip(file_path, current_hash, self.cache_manager, progress_callback, completed_count, total_files, 'no_text_content')
            
            streaming_embedder = self.get_streaming_embedder(batch_size=batch_size, progress_callback=None)
            all_embeddings, batch_index = [], 0
            total_batches = (len(texts) + streaming_embedder.batch_size - 1) // streaming_embedder.batch_size
            
            for embedding_batch in streaming_embedder.embed_stream(texts):
                all_embeddings.extend(embedding_batch)
                if on_batch:
                    batch_start = batch_index * streaming_embedder.batch_size
                    batch_end = min(batch_start + streaming_embedder.batch_size, len(texts))
                    batch_result = BatchResult(chunks=texts[batch_start:batch_end], embeddings=embedding_batch,
                                             batch_index=batch_index, total_batches=total_batches)
                    on_batch(batch_result)
                batch_index += 1
            
            if len(all_embeddings) < len(texts) and len(all_embeddings) == 0:
                result['error'] = 'No embeddings generated'
                return result
            
            points = self._prepare_vector_points(file_path, blocks, all_embeddings, rel_path)
            
            if not helpers.store_vectors(self.vector_store, rel_path, points, errors, self.error_handler, rel_path):
                return result
            
            helpers.update_cache(self.cache_manager, file_path, current_hash)
            result['success'] = True
            result['blocks_processed'] = len(blocks)
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "success", len(blocks))
            
        except Exception as e:
            error_context = ErrorContext(component="file_processor", operation="process_file_streaming", file_path=file_path)
            error_response = self.error_handler.handle_file_error(e, error_context, "file_processing")
            errors.append(f"Failed to process {file_path}: {error_response.message}")
            result['error'] = error_response.message
            
            if progress_callback:
                progress_callback(file_path, completed_count, total_files, "error", 0)
        
        return result