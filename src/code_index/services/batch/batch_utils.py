from typing import Callable, Dict, Any, List, Iterator, Optional
import logging

from ...constants import (
    BATCH_SIZE_LARGE, BATCH_SIZE_XLARGE,
    MEMORY_TARGET_EMBEDDING, MIN_BATCH_SIZE,
    EMBEDDING_DIMENSION_DEFAULT
)


logger = logging.getLogger("code_index.batch_utils")


class BatchProgressTracker:
    """Track progress during batch processing operations."""
    
    def __init__(
        self,
        total_items: int,
        progress_callback: Optional[Callable[[float], None]] = None,
        log_interval: int = 10
    ):
        """
        Initialize the progress tracker.
        
        Args:
            total_items: Total number of items to process
            progress_callback: Optional callback for progress updates
            log_interval: Log progress every N items
        """
        self.total_items = total_items
        self.progress_callback = progress_callback
        self.log_interval = log_interval
        self.completed_items = 0
        self.start_time = None
        self.logger = logger
    
    def start(self) -> None:
        """Start tracking progress."""
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting batch processing of {self.total_items} items")
    
    def update(self, items_completed: int = 1) -> None:
        """Update progress."""
        self.completed_items += items_completed
        
        if self.total_items > 0:
            progress = (self.completed_items / self.total_items) * 100.0
        else:
            progress = 100.0
        
        if self.progress_callback:
            self.progress_callback(progress)
        
        if self.completed_items % self.log_interval == 0 or self.completed_items == self.total_items:
            self._log_progress(progress)
    
    def _log_progress(self, progress: float) -> None:
        """Log current progress."""
        if self.start_time:
            import time
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate = self.completed_items / elapsed
                remaining = (self.total_items - self.completed_items) / rate if rate > 0 else 0
                self.logger.info(
                    f"Progress: {progress:.1f}% ({self.completed_items}/{self.total_items}) "
                    f"| Rate: {rate:.2f} items/sec | ETA: {remaining:.1f}s"
                )
            else:
                self.logger.info(f"Progress: {progress:.1f}% ({self.completed_items}/{self.total_items})")
    
    def complete(self) -> Dict[str, Any]:
        """Mark processing as complete and return statistics."""
        import time
        end_time = time.time()
        elapsed = end_time - self.start_time if self.start_time else 0
        
        stats = {
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'elapsed_seconds': elapsed,
            'items_per_second': self.completed_items / elapsed if elapsed > 0 else 0,
            'progress_percentage': 100.0 if self.total_items > 0 else 0.0
        }
        
        self.logger.info(
            f"Batch processing complete: {self.completed_items}/{self.total_items} items "
            f"in {elapsed:.2f}s ({stats['items_per_second']:.2f} items/sec)"
        )
        return stats


def calculate_optimal_batch_size(
    total_items: int,
    item_size_bytes: int,
    target_memory_mb: int = MEMORY_TARGET_EMBEDDING,
    max_batch_size: int = BATCH_SIZE_LARGE,
    min_batch_size: int = MIN_BATCH_SIZE
) -> int:
    """Calculate optimal batch size based on memory constraints."""
    if total_items == 0:
        return min_batch_size
    
    target_bytes = target_memory_mb * 1024 * 1024
    optimal_size = max(min_batch_size, int(target_bytes / item_size_bytes))
    
    return min(optimal_size, max_batch_size)


def estimate_text_memory_usage(
    texts: List[str],
    embedding_dim: int = EMBEDDING_DIMENSION_DEFAULT
) -> Dict[str, Any]:
    """Estimate memory usage for embedding a list of texts."""
    text_bytes = sum(len(text.encode('utf-8')) for text in texts)
    embedding_bytes = len(texts) * embedding_dim * 8
    overhead = len(texts) * 100
    total_bytes = text_bytes + embedding_bytes + overhead
    
    return {
        'num_texts': len(texts),
        'text_bytes': text_bytes,
        'embedding_bytes': embedding_bytes,
        'overhead_bytes': overhead,
        'total_bytes': total_bytes,
        'total_mb': total_bytes / (1024 * 1024),
        'embedding_dim': embedding_dim
    }


def create_batches_from_texts(
    texts: List[str],
    batch_size: int
) -> Iterator[List[str]]:
    """Create batches from a list of texts."""
    for i in range(0, len(texts), batch_size):
        yield texts[i:i + batch_size]


def validate_batch_size(
    batch_size: int,
    total_items: int,
    max_batch_size: int = BATCH_SIZE_XLARGE,
    min_batch_size: int = MIN_BATCH_SIZE
) -> int:
    """Validate and adjust batch size to acceptable limits."""
    if batch_size <= 0:
        return min_batch_size
    
    if batch_size > total_items:
        return total_items
    
    return max(min_batch_size, min(batch_size, max_batch_size))


def get_memory_efficient_batch_size(
    num_texts: int,
    avg_text_length: int,
    embedding_dim: int = EMBEDDING_DIMENSION_DEFAULT,
    target_memory_mb: int = MEMORY_TARGET_EMBEDDING,
    safety_factor: float = 0.8
) -> int:
    """Calculate memory-efficient batch size with safety margin."""
    if num_texts == 0:
        return 1
    
    text_bytes = avg_text_length
    embedding_bytes = embedding_dim * 8
    overhead = 100
    
    bytes_per_text = text_bytes + embedding_bytes + overhead
    target_bytes = target_memory_mb * 1024 * 1024 * safety_factor
    batch_size = int(target_bytes / bytes_per_text)
    
    return max(1, min(batch_size, num_texts))