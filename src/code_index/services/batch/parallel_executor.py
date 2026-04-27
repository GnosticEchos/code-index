"""
Parallel executor module for parallel file processing.

This module handles parallel execution of file processing tasks.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import List, Callable, Any, Optional, Dict
import logging
import time


logger = logging.getLogger("code_index.parallel_executor")


class ParallelExecutor:
    """
    Executes tasks in parallel using ThreadPoolExecutor.
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        batch_size: int = 10,
        ordered: bool = False
    ):
        self._max_workers = max_workers
        self._batch_size = batch_size
        self._ordered = ordered
        self._results: List = []
        self._lock = Lock()
        self._processed_count = 0
    
    def execute_parallel(
        self,
        files: List[str],
        process_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List:
        """Execute tasks in parallel."""
        if not files:
            return []
        
        self._results = [None] * len(files)
        self._processed_count = 0
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            if self._ordered:
                self._process_ordered(executor, files, process_func, progress_callback)
            else:
                self._process_unordered(executor, files, process_func, progress_callback)
        
        return self._results
    
    def _process_ordered(
        self,
        executor: ThreadPoolExecutor,
        files: List[str],
        process_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Process files in order."""
        futures = []
        for file_path in files:
            future = executor.submit(self._wrap_process, process_func, file_path)
            futures.append(future)
        
        for i, future in enumerate(futures):
            try:
                result = future.result()
                self._results[i] = result
            except Exception as e:
                self._results[i] = self._create_error_result(files[i], str(e))
            
            self._update_progress(len(files), progress_callback)
    
    def _process_unordered(
        self,
        executor: ThreadPoolExecutor,
        files: List[str],
        process_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Process files as they complete."""
        futures = {
            executor.submit(self._wrap_process, process_func, file_path): i
            for i, file_path in enumerate(files)
        }
        
        for future in as_completed(futures):
            i = futures[future]
            try:
                result = future.result()
                with self._lock:
                    self._results[i] = result
            except Exception as e:
                with self._lock:
                    self._results[i] = self._create_error_result(files[i], str(e))
            
            self._update_progress(len(files), progress_callback)
    
    def _wrap_process(self, process_func: Callable, file_path: str) -> Any:
        """Wrap processing function with timing."""
        start_time = time.time()
        try:
            result_data = process_func(file_path)
            return self._create_result(file_path, True, result_data, time.time() - start_time)
        except Exception as e:
            return self._create_result(file_path, False, None, time.time() - start_time, str(e))
    
    def _create_result(
        self,
        file_path: str,
        success: bool,
        data: Any,
        processing_time: float,
        error: Optional[str] = None
    ) -> Dict:
        """Create a result dictionary."""
        return {
            "file_path": file_path,
            "success": success,
            "data": data,
            "error": error,
            "processing_time": processing_time
        }
    
    def _create_error_result(self, file_path: str, error: str) -> Dict:
        """Create an error result."""
        return self._create_result(file_path, False, None, 0.0, error)
    
    def _update_progress(self, total: int, callback: Optional[Callable]) -> None:
        """Update progress tracking."""
        with self._lock:
            self._processed_count += 1
            current = self._processed_count
        
        if callback:
            callback(current, total)
    
    def execute_batch(
        self,
        files: List[str],
        process_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List:
        """Execute files in batches."""
        if not files:
            return []
        
        batches = [
            files[i:i + self._batch_size]
            for i in range(0, len(files), self._batch_size)
        ]
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._wrap_batch, process_func, batch): i
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                except Exception as e:
                    for file_path in batches[future.result()]:
                        results.append(self._create_error_result(file_path, str(e)))
                
                if progress_callback:
                    progress_callback(len(results), len(files))
        
        return results
    
    def _wrap_batch(self, process_func: Callable, batch: List[str]) -> List:
        """Wrap batch processing function."""
        try:
            results = process_func(batch)
            return results
        except Exception:
            return [self._create_error_result(f, "Batch processing failed") for f in batch]


def create_parallel_executor(max_workers: int = 4, batch_size: int = 10, ordered: bool = False) -> ParallelExecutor:
    """Factory function to create a ParallelExecutor."""
    return ParallelExecutor(max_workers, batch_size, ordered)
