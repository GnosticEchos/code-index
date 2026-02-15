"""
Batch status tracker module for tracking batch processing status and metrics.

This module handles performance metrics, status tracking, and memory monitoring.
"""

import time
import logging
from typing import Dict, Any, Optional


batch_logger = logging.getLogger('code_index.batch_status_tracker')


class BatchStatusTracker:
    """
    Tracks status and metrics for batch processing operations.
    
    Handles:
    - Performance metrics tracking
    - Memory usage monitoring
    - Progress tracking
    """
    
    def __init__(self, config, log_memory_usage: bool = False):
        self.config = config
        self.log_memory_usage = log_memory_usage
        self.performance_metrics = {
            'total_batches_processed': 0,
            'total_files_processed': 0,
            'total_processing_time_ms': 0,
            'average_processing_time_per_file_ms': 0,
            'parallel_processing_efficiency': 0,
            'memory_usage_optimization': 0
        }
    
    def update_performance_metrics(
        self,
        file_count: int,
        processing_time: float,
        language_groups: int,
        parallel_enabled: bool
    ):
        """
        Update performance metrics after batch processing.
        
        Args:
            file_count: Number of files processed
            processing_time: Total processing time in milliseconds
            language_groups: Number of language groups
            parallel_enabled: Whether parallel processing was used
        """
        self.performance_metrics['total_batches_processed'] += 1
        
        if file_count > 0:
            self.performance_metrics['total_files_processed'] += file_count
            self.performance_metrics['total_processing_time_ms'] += processing_time
            
            # Calculate average processing time per file
            self.performance_metrics['average_processing_time_per_file_ms'] = (
                self.performance_metrics['total_processing_time_ms'] /
                self.performance_metrics['total_files_processed']
            )
        
        # Calculate parallel processing efficiency
        if parallel_enabled and file_count > 5:
            estimated_sequential_time = processing_time * 1.5
            if estimated_sequential_time > 0:
                efficiency = (estimated_sequential_time - processing_time) / estimated_sequential_time * 100
                self.performance_metrics['parallel_processing_efficiency'] = max(0, efficiency)
        
        batch_logger.info(
            f"Performance metrics updated: avg {self.performance_metrics['average_processing_time_per_file_ms']:.2f}ms/file, "
            f"parallel efficiency: {self.performance_metrics['parallel_processing_efficiency']:.1f}%"
        )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return dict(self.performance_metrics)
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def should_optimize_memory(self) -> bool:
        """Determine if memory optimization is needed."""
        try:
            import psutil
            process = psutil.Process()
            memory_percent = process.memory_percent()
            return memory_percent > 80.0
        except Exception:
            return False
    
    def log_memory_stats(self, start_memory: float, end_memory: float):
        """Log memory statistics."""
        if self.log_memory_usage:
            memory_delta = end_memory - start_memory
            batch_logger.info(
                f"Memory usage - Start: {start_memory:.2f} MB, "
                f"End: {end_memory:.2f} MB, Delta: {memory_delta:.2f} MB"
            )
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.performance_metrics = {
            'total_batches_processed': 0,
            'total_files_processed': 0,
            'total_processing_time_ms': 0,
            'average_processing_time_per_file_ms': 0,
            'parallel_processing_efficiency': 0,
            'memory_usage_optimization': 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all tracked metrics."""
        return {
            "performance": self.performance_metrics,
            "memory_tracking_enabled": self.log_memory_usage,
            "current_memory_mb": self.get_memory_usage_mb()
        }


def create_status_tracker(config, log_memory_usage: bool = False) -> BatchStatusTracker:
    """Factory function to create a BatchStatusTracker."""
    return BatchStatusTracker(config, log_memory_usage)
