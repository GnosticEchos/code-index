"""
Progress Reporter for MCP Server

Provides progress reporting for long-running operations with MCP-compatible updates,
ETA calculations, and batch operation tracking.
"""

import time
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class ProgressUpdate:
    """Progress information for long-running operations"""
    operation_type: str
    completed_items: int
    total_items: int
    current_item: str
    elapsed_seconds: float
    eta_seconds: Optional[float]
    status_message: str
    progress_percentage: float
    items_per_second: float
    batch_info: Optional[Dict[str, Any]] = None


@dataclass
class BatchProgressInfo:
    """Information about batch processing progress"""
    current_batch: int
    total_batches: int
    batch_size: int
    items_in_current_batch: int
    batch_start_time: float
    batch_eta_seconds: Optional[float]


class ProgressReporter:
    """
    Provides progress reporting for long-running operations with MCP-compatible
    updates, ETA calculations, and batch operation tracking.
    """
    
    def __init__(
        self,
        total_items: int,
        operation_type: str = "indexing",
        update_interval: int = 10,
        min_update_interval: float = 1.0,
        progress_callback: Optional[Callable[[ProgressUpdate], Awaitable[None]]] = None
    ):
        """
        Initialize the progress reporter.
        
        Args:
            total_items: Total number of items to process
            operation_type: Type of operation (e.g., "indexing", "searching")
            update_interval: Number of items between progress updates
            min_update_interval: Minimum time between updates in seconds
            progress_callback: Optional async callback for progress updates
        """
        self.total_items = total_items
        self.operation_type = operation_type
        self.update_interval = update_interval
        self.min_update_interval = min_update_interval
        self.progress_callback = progress_callback
        
        # Progress tracking
        self.completed_items = 0
        self.current_item = ""
        self.start_time = time.time()
        self.last_update_time = 0.0
        self.last_update_count = 0
        
        # Batch tracking
        self.batch_info: Optional[BatchProgressInfo] = None
        self.batch_history: List[Dict[str, Any]] = []
        
        # ETA calculation
        self.eta_window_size = 50  # Number of recent items for ETA calculation
        self.recent_times: List[float] = []
        
        self.logger = logging.getLogger(__name__)
    
    async def update_progress(self, completed_items: int, current_item: str) -> None:
        """
        Update progress with current status.
        
        Args:
            completed_items: Number of items completed so far
            current_item: Description of current item being processed
        """
        self.completed_items = completed_items
        self.current_item = current_item
        
        current_time = time.time()
        
        # Track timing for ETA calculation
        if len(self.recent_times) >= self.eta_window_size:
            self.recent_times.pop(0)
        self.recent_times.append(current_time)
        
        # Check if we should send an update
        should_update = (
            # Regular interval updates
            (completed_items - self.last_update_count) >= self.update_interval or
            # Time-based updates
            (current_time - self.last_update_time) >= self.min_update_interval or
            # First and last items
            completed_items == 1 or completed_items == self.total_items
        )
        
        if should_update and self.progress_callback:
            await self._send_progress_update()
            self.last_update_time = current_time
            self.last_update_count = completed_items
    
    async def start_batch_operation(
        self,
        total_batches: int,
        batch_size: int,
        batch_description: str = "batch"
    ) -> None:
        """
        Start tracking a batch operation.
        
        Args:
            total_batches: Total number of batches to process
            batch_size: Number of items per batch
            batch_description: Description of what each batch contains
        """
        self.batch_info = BatchProgressInfo(
            current_batch=0,
            total_batches=total_batches,
            batch_size=batch_size,
            items_in_current_batch=0,
            batch_start_time=time.time(),
            batch_eta_seconds=None
        )
        
        self.logger.info(f"Starting batch operation: {total_batches} batches of {batch_size} {batch_description}")
        
        if self.progress_callback:
            await self._send_progress_update()
    
    async def update_batch_progress(
        self,
        batch_num: int,
        items_in_batch: int,
        batch_description: str = ""
    ) -> None:
        """
        Update progress for batch operations.
        
        Args:
            batch_num: Current batch number (1-indexed)
            items_in_batch: Number of items in current batch
            batch_description: Optional description of current batch
        """
        if not self.batch_info:
            self.logger.warning("update_batch_progress called without starting batch operation")
            return
        
        current_time = time.time()
        
        # Update batch info
        self.batch_info.current_batch = batch_num
        self.batch_info.items_in_current_batch = items_in_batch
        
        # Calculate batch ETA if we have history
        if len(self.batch_history) > 0:
            avg_batch_time = sum(b["duration"] for b in self.batch_history) / len(self.batch_history)
            remaining_batches = self.batch_info.total_batches - batch_num
            self.batch_info.batch_eta_seconds = avg_batch_time * remaining_batches
        
        # Update current item description
        if batch_description:
            self.current_item = f"Batch {batch_num}/{self.batch_info.total_batches}: {batch_description}"
        else:
            self.current_item = f"Processing batch {batch_num}/{self.batch_info.total_batches}"
        
        if self.progress_callback:
            await self._send_progress_update()
    
    async def complete_batch(self, batch_num: int, items_processed: int) -> None:
        """
        Mark a batch as complete and record timing.
        
        Args:
            batch_num: Completed batch number
            items_processed: Number of items actually processed in batch
        """
        if not self.batch_info:
            return
        
        current_time = time.time()
        batch_duration = current_time - self.batch_info.batch_start_time
        
        # Record batch history
        batch_record = {
            "batch_num": batch_num,
            "items_processed": items_processed,
            "duration": batch_duration,
            "items_per_second": items_processed / batch_duration if batch_duration > 0 else 0,
            "completed_at": current_time
        }
        self.batch_history.append(batch_record)
        
        # Update overall progress
        self.completed_items += items_processed
        
        # Reset batch start time for next batch
        self.batch_info.batch_start_time = current_time
        
        self.logger.debug(f"Completed batch {batch_num}: {items_processed} items in {batch_duration:.2f}s")
        
        if self.progress_callback:
            await self._send_progress_update()
    
    def calculate_eta(self, completed: int, elapsed_time: float) -> Optional[float]:
        """
        Calculate estimated time to completion.
        
        Args:
            completed: Number of items completed
            elapsed_time: Time elapsed since start
            
        Returns:
            Estimated seconds to completion, or None if cannot calculate
        """
        if completed <= 0 or self.total_items <= completed:
            return None
        
        # Use recent timing data if available
        if len(self.recent_times) >= 2:
            recent_duration = self.recent_times[-1] - self.recent_times[0]
            recent_items = min(len(self.recent_times), completed)
            if recent_duration > 0 and recent_items > 0:
                items_per_second = recent_items / recent_duration
                remaining_items = self.total_items - completed
                return remaining_items / items_per_second
        
        # Fallback to overall average
        if elapsed_time > 0:
            items_per_second = completed / elapsed_time
            remaining_items = self.total_items - completed
            return remaining_items / items_per_second
        
        return None
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive progress summary.
        
        Returns:
            Dictionary with detailed progress information
        """
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        progress_pct = (self.completed_items / self.total_items * 100) if self.total_items > 0 else 0
        items_per_second = self.completed_items / elapsed if elapsed > 0 else 0
        eta = self.calculate_eta(self.completed_items, elapsed)
        
        summary = {
            "operation_type": self.operation_type,
            "completed_items": self.completed_items,
            "total_items": self.total_items,
            "progress_percentage": round(progress_pct, 1),
            "elapsed_seconds": round(elapsed, 1),
            "items_per_second": round(items_per_second, 2),
            "eta_seconds": round(eta, 1) if eta else None,
            "current_item": self.current_item,
            "status": self._get_status_message()
        }
        
        # Add batch information if available
        if self.batch_info:
            batch_progress_pct = (self.batch_info.current_batch / self.batch_info.total_batches * 100) if self.batch_info.total_batches > 0 else 0
            summary["batch_info"] = {
                "current_batch": self.batch_info.current_batch,
                "total_batches": self.batch_info.total_batches,
                "batch_progress_percentage": round(batch_progress_pct, 1),
                "items_in_current_batch": self.batch_info.items_in_current_batch,
                "batch_eta_seconds": round(self.batch_info.batch_eta_seconds, 1) if self.batch_info.batch_eta_seconds else None
            }
            
            # Add batch performance history
            if self.batch_history:
                recent_batches = self.batch_history[-5:]  # Last 5 batches
                avg_batch_time = sum(b["duration"] for b in recent_batches) / len(recent_batches)
                avg_items_per_second = sum(b["items_per_second"] for b in recent_batches) / len(recent_batches)
                
                summary["batch_performance"] = {
                    "average_batch_time": round(avg_batch_time, 2),
                    "average_items_per_second": round(avg_items_per_second, 2),
                    "completed_batches": len(self.batch_history)
                }
        
        return summary
    
    async def _send_progress_update(self) -> None:
        """Send progress update through callback if available."""
        if not self.progress_callback:
            return
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        progress_pct = (self.completed_items / self.total_items * 100) if self.total_items > 0 else 0
        items_per_second = self.completed_items / elapsed if elapsed > 0 else 0
        eta = self.calculate_eta(self.completed_items, elapsed)
        
        # Create batch info if available
        batch_info_dict = None
        if self.batch_info:
            batch_info_dict = asdict(self.batch_info)
        
        update = ProgressUpdate(
            operation_type=self.operation_type,
            completed_items=self.completed_items,
            total_items=self.total_items,
            current_item=self.current_item,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            status_message=self._get_status_message(),
            progress_percentage=progress_pct,
            items_per_second=items_per_second,
            batch_info=batch_info_dict
        )
        
        try:
            await self.progress_callback(update)
        except Exception as e:
            self.logger.error(f"Error sending progress update: {e}")
    
    def _get_status_message(self) -> str:
        """Generate a human-readable status message."""
        if self.completed_items == 0:
            return f"Starting {self.operation_type}..."
        elif self.completed_items >= self.total_items:
            return f"Completed {self.operation_type}"
        else:
            progress_pct = (self.completed_items / self.total_items * 100)
            
            if self.batch_info:
                return f"Processing batch {self.batch_info.current_batch}/{self.batch_info.total_batches} ({progress_pct:.1f}% complete)"
            else:
                return f"Processing {self.completed_items}/{self.total_items} items ({progress_pct:.1f}% complete)"
    
    def format_eta(self, eta_seconds: Optional[float]) -> str:
        """
        Format ETA in human-readable format.
        
        Args:
            eta_seconds: ETA in seconds
            
        Returns:
            Formatted ETA string
        """
        if eta_seconds is None:
            return "Unknown"
        
        if eta_seconds < 60:
            return f"{int(eta_seconds)}s"
        elif eta_seconds < 3600:
            minutes = int(eta_seconds / 60)
            seconds = int(eta_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(eta_seconds / 3600)
            minutes = int((eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def format_progress_for_mcp(self) -> Dict[str, Any]:
        """
        Format progress information for MCP client consumption.
        
        Returns:
            Dictionary formatted for MCP protocol
        """
        summary = self.get_progress_summary()
        
        # Format for MCP client
        mcp_progress = {
            "type": "progress_update",
            "operation": summary["operation_type"],
            "progress": {
                "completed": summary["completed_items"],
                "total": summary["total_items"],
                "percentage": summary["progress_percentage"],
                "current": summary["current_item"]
            },
            "timing": {
                "elapsed": summary["elapsed_seconds"],
                "eta": self.format_eta(summary["eta_seconds"]),
                "rate": f"{summary['items_per_second']:.1f} items/sec"
            },
            "status": summary["status"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Add batch information if available
        if "batch_info" in summary:
            mcp_progress["batch"] = {
                "current": summary["batch_info"]["current_batch"],
                "total": summary["batch_info"]["total_batches"],
                "percentage": summary["batch_info"]["batch_progress_percentage"],
                "eta": self.format_eta(summary["batch_info"]["batch_eta_seconds"])
            }
        
        return mcp_progress