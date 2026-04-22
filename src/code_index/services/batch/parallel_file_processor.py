"""
Parallel file processing services for improved indexing throughput.

This module provides concurrent file processing using ThreadPoolExecutor,
with thread-safe error handling, progress reporting, and result aggregation.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import List, Callable, Any, Optional, Dict, Tuple
from enum import Enum
import logging
import time


logger = logging.getLogger("code_index.parallel_processor")


class ProcessingOrder(Enum):
    """Order in which results should be returned."""
    ORDERED = "ordered"      # Results in same order as input
    UNORDERED = "unordered"  # Results as they complete (faster)


class ParallelProcessingError(Exception):
    """Exception raised when parallel processing fails."""
    pass


class ErrorContext:
    """Context information for a processing error."""
    
    def __init__(
        self,
        file_path: Optional[str] = None,
        batch_index: Optional[int] = None,
        error: Optional[Exception] = None
    ):
        self.file_path = file_path
        self.batch_index = batch_index
        self.error = error
        self.timestamp = time.time()


class ErrorHandler:
    """Handles errors during parallel processing."""
    
    def __init__(
        self,
        continue_on_error: bool = True,
        max_errors: Optional[int] = None
    ):
        self.continue_on_error = continue_on_error
        self.max_errors = max_errors
        self.errors: List[ErrorContext] = []
        self._error_count = 0
        self._lock = Lock()
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Handle an error during processing.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            True if processing should continue, False otherwise
        """
        with self._lock:
            self._error_count += 1
            error_context = ErrorContext(
                file_path=context.get("file") if context else None,
                batch_index=context.get("batch_index") if context else None,
                error=error
            )
            self.errors.append(error_context)
            
            file_path = context.get("file") if context else "unknown"
            logger.warning(f"Failed to process {file_path}: {error}")
            
            if self.max_errors and self._error_count >= self.max_errors:
                logger.error(f"Max errors ({self.max_errors}) reached, stopping processing")
                return False
            
            return self.continue_on_error
    
    def get_errors(self) -> List[ErrorContext]:
        """Get all captured errors."""
        with self._lock:
            return self.errors.copy()
    
    def get_error_count(self) -> int:
        """Get total error count."""
        with self._lock:
            return self._error_count
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        with self._lock:
            return self._error_count > 0
    
    def clear(self) -> None:
        """Clear all errors."""
        with self._lock:
            self.errors.clear()
            self._error_count = 0


class ProcessingResult:
    """Result of processing a single file."""
    
    def __init__(
        self,
        file_path: str,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        processing_time: float = 0.0
    ):
        self.file_path = file_path
        self.success = success
        self.data = data
        self.error = error
        self.processing_time = processing_time


class ParallelFileProcessor:
    """
    Process files concurrently using ThreadPoolExecutor.
    
    Features:
    - Configurable number of workers (default: 4)
    - Thread-safe error handling
    - Progress reporting for concurrent operations
    - Batch size control per worker
    - Result aggregation (ordered or unordered)
    - Graceful error recovery
    
    Note: Best suited for I/O-bound operations like file reading and embedding
    due to Python's GIL. CPU-bound operations may not see significant benefits.
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        batch_size: int = 10,
        ordered: bool = False,
        error_handler: Optional[ErrorHandler] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        continue_on_error: bool = True,
        max_errors: Optional[int] = None
    ):
        """
        Initialize the parallel file processor.
        
        Args:
            max_workers: Number of worker threads (default: 4)
            batch_size: Number of files per batch (default: 10)
            ordered: Return results in input order (default: False)
            error_handler: Custom error handler (optional)
            progress_callback: Called with (processed, total) on progress
            continue_on_error: Continue processing after errors (default: True)
            max_errors: Maximum errors before stopping (default: None)
        """
        self._max_workers = max_workers
        self._batch_size = batch_size
        self._ordered = ordered
        self._error_handler = error_handler or ErrorHandler(
            continue_on_error=continue_on_error,
            max_errors=max_errors
        )
        self._progress_callback = progress_callback
        self._results: List[Optional[ProcessingResult]] = []
        self._lock = Lock()
        self._processed_count = 0
        
        logger.debug(
            f"Initialized ParallelFileProcessor with {max_workers} workers, "
            f"batch_size={batch_size}, ordered={ordered}"
        )
    
    def process_files(
        self,
        files: List[str],
        process_func: Callable[[str], Any],
        **kwargs
    ) -> List[ProcessingResult]:
        """
        Process files in parallel.
        
        Args:
            files: List of file paths to process
            process_func: Function to process each file
            **kwargs: Additional arguments passed to process_func
            
        Returns:
            List of ProcessingResult objects (may include failures)
            
        Example:
            >>> processor = ParallelFileProcessor(max_workers=4)
            >>> def process_file(path):
            ...     with open(path) as f:
            ...         return f.read()
            >>> results = processor.process_files(file_list, process_file)
        """
        if not files:
            return []
        
        # Initialize results list with None placeholders
        self._results = [None] * len(files)
        self._processed_count = 0
        self._error_handler.clear()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            if self._ordered:
                self._process_ordered(executor, files, process_func, **kwargs)
            else:
                self._process_unordered(executor, files, process_func, **kwargs)
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in self._results if r and r.success)
        logger.info(
            f"Processed {len(files)} files in {elapsed:.2f}s "
            f"({success_count} succeeded, {len(files) - success_count} failed)"
        )
        
        return self._results
    
    def _process_ordered(
        self,
        executor: ThreadPoolExecutor,
        files: List[str],
        process_func: Callable[[str], Any],
        **kwargs
    ) -> None:
        """Process files and maintain order of results."""
        # Submit all tasks and store futures in order
        futures = []
        for file_path in files:
            future = executor.submit(self._wrap_process, process_func, file_path, **kwargs)
            futures.append(future)
        
        # Process results in order
        for i, future in enumerate(futures):
            try:
                result = future.result()
                self._results[i] = result
            except Exception as e:
                self._handle_error(e, {"file": files[i], "index": i})
                self._results[i] = ProcessingResult(
                    file_path=files[i],
                    success=False,
                    error=str(e)
                )
            
            self._update_progress(len(files))
    
    def _process_unordered(
        self,
        executor: ThreadPoolExecutor,
        files: List[str],
        process_func: Callable[[str], Any],
        **kwargs
    ) -> None:
        """Process files and return results as they complete."""
        # Submit all tasks with their indices
        futures = {
            executor.submit(self._wrap_process, process_func, file_path, **kwargs): i
            for i, file_path in enumerate(files)
        }
        
        # Process results as they complete
        for future in as_completed(futures):
            i = futures[future]
            try:
                result = future.result()
                with self._lock:
                    self._results[i] = result
            except Exception as e:
                self._handle_error(e, {"file": files[i], "index": i})
                with self._lock:
                    self._results[i] = ProcessingResult(
                        file_path=files[i],
                        success=False,
                        error=str(e)
                    )
            
            self._update_progress(len(files))
    
    def _wrap_process(
        self,
        process_func: Callable[[str], Any],
        file_path: str,
        **kwargs
    ) -> ProcessingResult:
        """Wrap processing function with timing and error handling."""
        start_time = time.time()
        try:
            result_data = process_func(file_path, **kwargs)
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                file_path=file_path,
                success=True,
                data=result_data,
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = time.time() - start_time
            logger.warning(f"Processing failed for {file_path}: {e}")
            
            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def _handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Handle an error during processing."""
        should_continue = self._error_handler.handle_error(error, context)
        if not should_continue:
            raise ParallelProcessingError(
                f"Processing stopped due to error: {error}"
            )
    
    def _update_progress(self, total: int) -> None:
        """Update progress tracking."""
        with self._lock:
            self._processed_count += 1
            current = self._processed_count
        
        if self._progress_callback:
            self._progress_callback(current, total)
    
    def process_file_batch(
        self,
        files: List[str],
        process_func: Callable[[List[str]], List[Any]],
        **kwargs
    ) -> List[ProcessingResult]:
        """
        Process files in parallel batches.
        
        Similar to process_files but processes files in batches rather than
        individually. Useful when batch processing is more efficient.
        
        Args:
            files: List of file paths to process
            process_func: Function to process a batch of files
            **kwargs: Additional arguments passed to process_func
            
        Returns:
            List of ProcessingResult objects
        """
        if not files:
            return []
        
        # Create batches
        batches = [
            files[i:i + self._batch_size]
            for i in range(0, len(files), self._batch_size)
        ]
        
        self._error_handler.clear()
        all_results: List[ProcessingResult] = []
        self._processed_count = 0
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit batch processing tasks
            futures = {
                executor.submit(self._wrap_batch_process, process_func, batch, **kwargs): i
                for i, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                batch_index = futures[future]
                batch = batches[batch_index]
                
                try:
                    batch_results = future.result()
                    if isinstance(batch_results, list):
                        all_results.extend(batch_results)
                    else:
                        # Wrap single result
                        all_results.append(batch_results)
                except Exception as e:
                    self._handle_error(e, {"batch_index": batch_index})
                    # Create failure results for all files in batch
                    for file_path in batch:
                        all_results.append(ProcessingResult(
                            file_path=file_path,
                            success=False,
                            error=str(e)
                        ))
                
                self._update_progress(len(batches))
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in all_results if r.success)
        logger.info(
            f"Processed {len(batches)} batches in {elapsed:.2f}s "
            f"({success_count} succeeded, {len(all_results) - success_count} failed)"
        )
        
        return all_results
    
    def _wrap_batch_process(
        self,
        process_func: Callable[[List[str]], List[Any]],
        batch: List[str],
        **kwargs
    ) -> List[ProcessingResult]:
        """Wrap batch processing function with timing."""
        start_time = time.time()
        results = process_func(batch, **kwargs)
        processing_time = time.time() - start_time
        
        # Ensure results are ProcessingResult objects
        if not isinstance(results, list):
            results = [results]
        
        # Wrap non-ProcessingResult items
        wrapped_results = []
        for i, result in enumerate(results):
            if isinstance(result, ProcessingResult):
                wrapped_results.append(result)
            else:
                file_path = batch[i] if i < len(batch) else "unknown"
                wrapped_results.append(ProcessingResult(
                    file_path=file_path,
                    success=True,
                    data=result,
                    processing_time=processing_time / len(results)
                ))
        
        return wrapped_results
    
    def process_with_fallback(
        self,
        files: List[str],
        process_func: Callable[[str], Any],
        fallback_func: Optional[Callable[[str], Any]] = None,
        **kwargs
    ) -> List[ProcessingResult]:
        """
        Process files in parallel with sequential fallback on failure.
        
        Args:
            files: List of file paths to process
            process_func: Primary processing function
            fallback_func: Fallback function if parallel processing fails
            **kwargs: Additional arguments passed to processing functions
            
        Returns:
            List of ProcessingResult objects
        """
        try:
            return self.process_files(files, process_func, **kwargs)
        except ParallelProcessingError as e:
            logger.warning(f"Parallel processing failed: {e}, falling back to sequential")
            
            if fallback_func is None:
                fallback_func = process_func
            
            # Sequential fallback
            results = []
            for file_path in files:
                start_time = time.time()
                try:
                    data = fallback_func(file_path, **kwargs)
                    results.append(ProcessingResult(
                        file_path=file_path,
                        success=True,
                        data=data,
                        processing_time=time.time() - start_time
                    ))
                except Exception as fallback_error:
                    results.append(ProcessingResult(
                        file_path=file_path,
                        success=False,
                        error=str(fallback_error),
                        processing_time=time.time() - start_time
                    ))
            
            return results


class ThreadSafeResultCollector:
    """
    Thread-safe collector for aggregating results from parallel operations.
    
    Provides ordered and unordered collection modes with proper synchronization.
    """
    
    def __init__(self, ordered: bool = False):
        """
        Initialize the collector.
        
        Args:
            ordered: Maintain insertion order (default: False)
        """
        self._ordered = ordered
        self._results: List[Tuple[int, Any]] = []
        self._lock = Lock()
        self._counter = 0
    
    def add(self, item: Any, index: Optional[int] = None) -> None:
        """
        Add an item to the collector.
        
        Args:
            item: Item to add
            index: Optional index for ordering
        """
        with self._lock:
            if index is None:
                index = self._counter
            self._counter += 1
            self._results.append((index, item))
    
    def extend(self, items: List[Any], start_index: Optional[int] = None) -> None:
        """
        Add multiple items to the collector.
        
        Args:
            items: Items to add
            start_index: Starting index for ordering
        """
        with self._lock:
            if start_index is None:
                start_index = self._counter
            for i, item in enumerate(items):
                self._results.append((start_index + i, item))
            self._counter += len(items)
    
    def get_results(self) -> List[Any]:
        """
        Get all collected results.
        
        Returns:
            List of results (ordered if ordered=True)
        """
        with self._lock:
            if self._ordered:
                # Sort by index
                sorted_results = sorted(self._results, key=lambda x: x[0])
                return [item for _, item in sorted_results]
            else:
                return [item for _, item in self._results]
    
    def get_count(self) -> int:
        """Get the number of collected results."""
        with self._lock:
            return len(self._results)
    
    def clear(self) -> None:
        """Clear all collected results."""
        with self._lock:
            self._results.clear()
            self._counter = 0


class ParallelProgressTracker:
    """
    Thread-safe progress tracker for parallel operations.
    
    Tracks progress across multiple workers and reports overall progress.
    """
    
    def __init__(
        self,
        total: int,
        callback: Optional[Callable[[int, int, float], None]] = None,
        report_interval: float = 0.1
    ):
        """
        Initialize the progress tracker.
        
        Args:
            total: Total number of items to process
            callback: Called with (completed, total, percentage)
            report_interval: Minimum seconds between callbacks
        """
        self._total = total
        self._callback = callback
        self._report_interval = report_interval
        self._completed = 0
        self._lock = Lock()
        self._last_report_time = 0.0
        self._start_time = time.time()
    
    def increment(self, count: int = 1) -> None:
        """
        Increment the completed count.
        
        Args:
            count: Number of items completed (default: 1)
        """
        with self._lock:
            self._completed += count
            completed = self._completed
            should_report = (
                time.time() - self._last_report_time >= self._report_interval
            )
            if should_report:
                self._last_report_time = time.time()
        
        if should_report and self._callback:
            percentage = (completed / self._total * 100) if self._total > 0 else 0
            self._callback(completed, self._total, percentage)
    
    def get_progress(self) -> Tuple[int, int, float]:
        """
        Get current progress.
        
        Returns:
            Tuple of (completed, total, percentage)
        """
        with self._lock:
            completed = self._completed
        percentage = (completed / self._total * 100) if self._total > 0 else 0
        return completed, self._total, percentage
    
    def is_complete(self) -> bool:
        """Check if processing is complete."""
        with self._lock:
            return self._completed >= self._total
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since tracking started."""
        return time.time() - self._start_time
