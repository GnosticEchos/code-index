"""
Thread-safe result collector module for aggregating parallel operation results.

This module provides thread-safe collection of results from parallel operations.
"""

import threading
from typing import List, Any, Optional, Tuple


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
        self._lock = threading.Lock()
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