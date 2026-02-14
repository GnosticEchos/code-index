"""
Batch manager for processing files in optimized batches.

Handles file batching, memory management, and chunking strategy selection.
Extracted from IndexingService for better testability and maintainability.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Iterator
from pathlib import Path

from ..config import Config
from ..scanner import DirectoryScanner
from ..chunking import (
    ChunkingStrategy,
    LineChunkingStrategy,
    TokenChunkingStrategy,
    TreeSitterChunkingStrategy,
)
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from .indexing_dependencies import IndexingDependencies
from .streaming_embedder import StreamingEmbedder, BatchResult


logger = logging.getLogger("code_index.batch_manager")


class BatchManager:
    """
    Manages batch operations for indexing.
    
    Responsibilities:
    - Batch creation and management
    - Chunking strategy selection
    - Memory-efficient batch processing
    - File list management
    - Parallel processing coordination
    
    Supports dependency injection via IndexingDependencies for testing.
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        error_handler: Optional[ErrorHandler] = None,
        scanner: Optional[DirectoryScanner] = None,
        dependencies: Optional[IndexingDependencies] = None,
        parallel_workers: int = 1
    ):
        """
        Initialize the batch manager.
        
        Args:
            config: Configuration object (optional if dependencies provided)
            error_handler: Error handler instance
            scanner: Directory scanner instance
            dependencies: IndexingDependencies instance for DI
            parallel_workers: Number of parallel workers (1 = sequential)
        """
        if dependencies is not None:
            self._dependencies = dependencies
            self.config = config or Config()
            self.error_handler = dependencies.error_handler
            self.scanner = dependencies.scanner
        else:
            self._dependencies = None
            self.config = config or Config()
            self.error_handler = error_handler or ErrorHandler()
            self.scanner = scanner
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize parallel processor if workers > 1
        self._parallel_processor = None
        self._parallel_workers = parallel_workers
        
        # Check config for parallel workers setting
        if hasattr(self.config, 'performance') and self.config.performance:
            config_workers = getattr(self.config.performance, 'parallel_workers', 1)
            if config_workers > 1:
                self._parallel_workers = config_workers
        
        if self._parallel_workers > 1:
            from .parallel_file_processor import ParallelFileProcessor
            self._parallel_processor = ParallelFileProcessor(
                max_workers=self._parallel_workers,
                batch_size=getattr(self.config, 'batch_size', 10),
                error_handler=None,
                continue_on_error=True
            )
            logger.info(f"BatchManager initialized with {self._parallel_workers} parallel workers")
    
    def get_chunking_strategy(self) -> ChunkingStrategy:
        """
        Get the appropriate chunking strategy based on configuration.
        
        Returns:
            Configured chunking strategy instance
        """
        strategy_name = getattr(self.config, "chunking_strategy", "lines")
        
        if strategy_name == "treesitter":
            return TreeSitterChunkingStrategy(self.config)
        elif strategy_name == "tokens":
            return TokenChunkingStrategy(self.config)
        else:
            return LineChunkingStrategy(self.config)
    
    def get_file_paths(self, workspace: str, config: Config) -> List[str]:
        """
        Get list of file paths to process.
        
        Args:
            workspace: Workspace path
            config: Configuration object
            
        Returns:
            List of file paths to index
        """
        if self.scanner is None:
            self.scanner = DirectoryScanner(config)
        
        scanned_paths, skipped_count = self.scanner.scan_directory()
        return scanned_paths
    
    def create_batches(
        self,
        file_paths: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[str]]:
        """
        Create batches from file list for memory-efficient processing.
        
        Args:
            file_paths: List of file paths
            batch_size: Override batch size (default from config)
            
        Returns:
            List of file batches
        """
        if not file_paths:
            return []
        
        batch_size = batch_size or getattr(self.config, "batch_size", 10)
        batches = []
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    def process_files(
        self,
        files: List[str],
        process_func: Callable[[str], Any],
        use_parallel: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        ordered_results: bool = False
    ) -> List[Any]:
        """
        Process files with optional parallel execution.
        
        Args:
            files: List of file paths to process
            process_func: Function to process each file
            use_parallel: Enable parallel processing (default: False)
            progress_callback: Called with (processed, total) on progress
            ordered_results: Return results in input order (default: False)
            
        Returns:
            List of processing results
            
        Example:
            >>> batch_manager = BatchManager(config, parallel_workers=4)
            >>> def process_file(path):
            ...     return parse_and_embed(path)
            >>> results = batch_manager.process_files(
            ...     files, 
            ...     process_file, 
            ...     use_parallel=True
            ... )
        """
        if not files:
            return []
        
        # Use parallel processing if enabled and available
        if use_parallel and self._parallel_processor and self._parallel_workers > 1:
            return self._process_files_parallel(
                files, process_func, progress_callback, ordered_results
            )
        
        # Sequential processing
        return self._process_files_sequential(
            files, process_func, progress_callback
        )
    
    def _process_files_parallel(
        self,
        files: List[str],
        process_func: Callable[[str], Any],
        progress_callback: Optional[Callable[[int, int], None]],
        ordered_results: bool
    ) -> List[Any]:
        """Process files in parallel using ThreadPoolExecutor."""
        from .parallel_file_processor import ProcessingOrder
        
        # Configure ordered/unordered processing
        original_ordered = getattr(self._parallel_processor, '_ordered', False)
        self._parallel_processor._ordered = ordered_results
        
        try:
            results = self._parallel_processor.process_files(
                files=files,
                process_func=process_func,
                progress_callback=progress_callback
            )
            
            # Extract data from ProcessingResult objects
            return [r.data if r and hasattr(r, 'data') else r for r in results]
        
        finally:
            # Restore original setting
            self._parallel_processor._ordered = original_ordered
    
    def _process_files_sequential(
        self,
        files: List[str],
        process_func: Callable[[str], Any],
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> List[Any]:
        """Process files sequentially."""
        results = []
        
        for i, file_path in enumerate(files):
            try:
                result = process_func(file_path)
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to process {file_path}: {e}")
                results.append(None)
            
            if progress_callback:
                progress_callback(i + 1, len(files))
        
        return results
    
    def process_batches_parallel(
        self,
        batches: List[List[str]],
        process_func: Callable[[List[str]], List[Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """
        Process batches in parallel.
        
        Args:
            batches: List of file batches to process
            process_func: Function to process each batch
            progress_callback: Called with (processed, total) on progress
            
        Returns:
            List of combined results from all batches
        """
        if not batches:
            return []
        
        # Use parallel processor if available
        if self._parallel_processor and self._parallel_workers > 1:
            # Flatten files for parallel processing
            all_files = []
            batch_indices = []
            for batch in batches:
                batch_indices.append((len(all_files), len(all_files) + len(batch)))
                all_files.extend(batch)
            
            # Process all files in parallel
            def single_file_wrapper(file_path: str) -> Any:
                # Find which batch this file belongs to
                for batch in batches:
                    if file_path in batch:
                        return process_func([file_path])[0] if process_func([file_path]) else None
                return None
            
            results = self._parallel_processor.process_files(
                files=all_files,
                process_func=single_file_wrapper,
                progress_callback=progress_callback
            )
            
            return [r.data if r and hasattr(r, 'data') else r for r in results]
        
        # Sequential batch processing
        all_results = []
        for i, batch in enumerate(batches):
            try:
                batch_results = process_func(batch)
                if batch_results:
                    all_results.extend(batch_results)
            except Exception as e:
                self.logger.warning(f"Failed to process batch {i}: {e}")
            
            if progress_callback:
                progress_callback(i + 1, len(batches))
        
        return all_results
    
    def get_optimal_batch_size(self, file_paths: List[str]) -> int:
        """
        Determine optimal batch size based on file sizes.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Optimal batch size
        """
        if not file_paths:
            return 10
        
        try:
            # Calculate total size
            total_size = sum(Path(f).stat().st_size for f in file_paths if Path(f).exists())
            avg_size = total_size / len(file_paths)
            
            # Target batch memory usage (e.g., 10MB per batch)
            target_batch_mb = 10
            target_batch_bytes = target_batch_mb * 1024 * 1024
            
            optimal_size = max(1, int(target_batch_bytes / avg_size)) if avg_size > 0 else 10
            max_size = getattr(self.config, "max_batch_size", 50)
            
            return min(optimal_size, max_size)
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate optimal batch size: {e}")
            return getattr(self.config, "batch_size", 10)
    
    def estimate_memory_usage(self, file_paths: List[str]) -> int:
        """
        Estimate memory usage for processing files.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Estimated memory usage in bytes
        """
        total_size = 0
        
        for file_path in file_paths:
            try:
                if Path(file_path).exists():
                    # Estimate: file size + processing overhead (3x for parsing/embedding)
                    total_size += Path(file_path).stat().st_size * 3
            except Exception:
                pass
        
        return total_size
    
    def sort_by_size(
        self,
        file_paths: List[str],
        descending: bool = True
    ) -> List[str]:
        """
        Sort file paths by size for optimal processing order.
        
        Args:
            file_paths: List of file paths
            descending: Sort largest first (default True)
            
        Returns:
            Sorted list of file paths
        """
        try:
            return sorted(
                file_paths,
                key=lambda f: Path(f).stat().st_size if Path(f).exists() else 0,
                reverse=descending
            )
        except Exception as e:
            self.logger.warning(f"Failed to sort files by size: {e}")
            return file_paths
    
    def filter_changed_files(
        self,
        file_paths: List[str],
        cache_manager: Any,
        get_hash_func: Callable[[str], str]
    ) -> List[str]:
        """
        Filter out files that haven't changed since last indexing.
        
        Args:
            file_paths: List of file paths
            cache_manager: Cache manager instance
            get_hash_func: Function to compute file hash
            
        Returns:
            List of changed file paths
        """
        changed_files = []
        
        for file_path in file_paths:
            current_hash = get_hash_func(file_path)
            cached_hash = cache_manager.get_hash(file_path) if cache_manager else None
            
            if current_hash != cached_hash:
                changed_files.append(file_path)
        
        return changed_files
    
    def get_batch_stats(self, batches: List[List[str]]) -> Dict[str, Any]:
        """
        Get statistics about created batches.
        
        Args:
            batches: List of file batches
            
        Returns:
            Dictionary with batch statistics
        """
        total_files = sum(len(batch) for batch in batches)
        total_size = 0
        
        for batch in batches:
            for file_path in batch:
                try:
                    if Path(file_path).exists():
                        total_size += Path(file_path).stat().st_size
                except Exception:
                    pass
        
        return {
            'total_batches': len(batches),
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'average_batch_size': total_files / len(batches) if batches else 0,
            'largest_batch': max(len(batch) for batch in batches) if batches else 0,
            'smallest_batch': min(len(batch) for batch in batches) if batches else 0
        }
    
    def get_streaming_embedder(
        self,
        embedder: Any,
        batch_size: Optional[int] = None,
        parallel_batches: int = 1,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> StreamingEmbedder:
        """
        Get a streaming embedder instance for memory-efficient processing.
        
        Args:
            embedder: The underlying embedder instance (e.g., OllamaEmbedder)
            batch_size: Override batch size (default from config)
            parallel_batches: Number of parallel batch processing threads
            progress_callback: Optional progress callback
            
        Returns:
            StreamingEmbedder instance
        """
        if batch_size is None:
            batch_size = getattr(self.config, "batch_segment_threshold", 32)
        return StreamingEmbedder(
            embedder=embedder,
            batch_size=batch_size,
            parallel_batches=parallel_batches,
            progress_callback=progress_callback,
            error_handler=self.error_handler
        )
    
    def process_files_streaming(
        self,
        files: List[str],
        chunking_strategy: ChunkingStrategy,
        streaming_embedder: StreamingEmbedder,
        on_batch: Optional[Callable[[BatchResult], None]] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Iterator[BatchResult]:
        """
        Process files using streaming embeddings for memory efficiency.
        
        This method processes files and yields batch results as they are
        computed, rather than accumulating all results in memory.
        
        Args:
            files: List of file paths to process
            chunking_strategy: Chunking strategy to use
            streaming_embedder: Streaming embedder instance
            on_batch: Optional callback for each batch result
            progress_callback: Optional progress callback
            
        Yields:
            BatchResult for each processed batch
            
        Example:
            >>> batch_manager = BatchManager(config)
            >>> embedder = StreamingEmbedder(ollama_embedder)
            >>> for batch_result in batch_manager.process_files_streaming(
            ...     files, chunking_strategy, embedder
            ... ):
            ...     # Process batch result immediately
            ...     store_embeddings(batch_result.embeddings)
        """
        total_files = len(files)
        if total_files == 0:
            if progress_callback:
                progress_callback(100.0)
            return
        
        batch_index = 0
        total_batches = (total_files + streaming_embedder.batch_size - 1) // streaming_embedder.batch_size
        
        for i in range(0, total_files, streaming_embedder.batch_size):
            batch_files = files[i:i + streaming_embedder.batch_size]
            
            # Collect all chunks from batch files
            all_chunks = []
            for file_path in batch_files:
                try:
                    chunks = chunking_strategy.chunk(file_path)
                    all_chunks.extend(chunks)
                except Exception as e:
                    self.logger.warning(f"Failed to chunk {file_path}: {e}")
                    continue
            
            if not all_chunks:
                continue
            
            # Extract text from chunks
            texts = [chunk.content if hasattr(chunk, 'content') else str(chunk) for chunk in all_chunks]
            
            # Generate embeddings using streaming
            embeddings = []
            for embedding_batch in streaming_embedder.embed_stream(texts):
                embeddings.extend(embedding_batch)
            
            # Create batch result
            batch_result = BatchResult(
                chunks=texts,
                embeddings=embeddings,
                batch_index=batch_index,
                total_batches=total_batches
            )
            
            # Call batch callback if provided
            if on_batch:
                on_batch(batch_result)
            
            # Report progress
            if progress_callback:
                progress = min(100.0, (i + len(batch_files)) / total_files * 100.0)
                progress_callback(progress)
            
            yield batch_result
            batch_index += 1
        
        # Report completion
        if progress_callback:
            progress_callback(100.0)
    
    def estimate_embedding_memory(
        self,
        num_texts: int,
        embedding_dim: int = 768
    ) -> Dict[str, Any]:
        """
        Estimate memory usage for embedding operations.
        
        Args:
            num_texts: Number of texts to embed
            embedding_dim: Dimension of each embedding vector
            
        Returns:
            Dictionary with memory usage estimates
        """
        # Each float is 8 bytes (double precision)
        bytes_per_embedding = embedding_dim * 8
        total_bytes = num_texts * bytes_per_embedding
        
        # Add overhead for Python objects (rough estimate)
        overhead = num_texts * 100  # ~100 bytes per embedding object
        
        total_with_overhead = total_bytes + overhead
        
        return {
            'num_texts': num_texts,
            'embedding_dim': embedding_dim,
            'bytes_per_embedding': bytes_per_embedding,
            'total_bytes': total_bytes,
            'overhead_bytes': overhead,
            'total_with_overhead_bytes': total_with_overhead,
            'total_mb': total_with_overhead / (1024 * 1024)
        }
    
    def get_optimal_streaming_batch_size(
        self,
        num_texts: int,
        embedding_dim: int = 768,
        target_memory_mb: int = 50
    ) -> int:
        """
        Calculate optimal batch size for streaming based on memory constraints.
        
        Args:
            num_texts: Total number of texts to embed
            embedding_dim: Dimension of each embedding vector
            target_memory_mb: Target memory usage per batch in MB
            
        Returns:
            Optimal batch size
        """
        if num_texts == 0:
            return getattr(self.config, "batch_segment_threshold", 32)
        memory_estimate = self.estimate_embedding_memory(1, embedding_dim)
        target_bytes = target_memory_mb * 1024 * 1024
        
        # Calculate optimal batch size
        optimal_size = max(1, int(target_bytes / memory_estimate['total_with_overhead_bytes']))
        
        # Respect configured batch size as upper bound
        max_batch_size = getattr(self.config, "batch_segment_threshold", 32)
        return min(optimal_size, max_batch_size)