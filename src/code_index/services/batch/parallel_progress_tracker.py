"""
Parallel progress tracker module for tracking progress in concurrent operations.

This module provides a thread-safe progress tracker for parallel operations.
"""

import threading
import time
from typing import Optional, Callable, Tuple


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
        self._lock = threading.Lock()
        self._last_report_time = 0.0
        self._start_time = time.time()
    
    def increment(self, count: int = 1) -> None:
        """
        Increment the completed count.
        
        Args:
            count: Number of items completed (default: 1)
        """
        should_report = False
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