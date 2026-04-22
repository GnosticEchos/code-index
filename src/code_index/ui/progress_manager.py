"""
Progress manager for TUI progress bars and status display.
"""
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn, TaskProgressColumn
from rich.console import Console
from rich.live import Live
from typing import Optional, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)


class ProgressManager:
    """Manage progress bars and status display for TUI operations."""
    
    def __init__(self, console: Optional[Console] = None, refresh_interval: float = 0.1):
        """Initialize progress manager."""
        # Validate refresh_interval to prevent ZeroDivisionError
        if refresh_interval <= 0:
            logger.warning(f"Invalid refresh_interval {refresh_interval}, using default 0.1")
            refresh_interval = 0.1
        
        try:
            self.console = console or Console()
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                expand=True
            )
            self.live_display = None
            self.current_status = "Initializing..."
            self.overall_task_id = None
            self.enabled = True
            self.refresh_interval = refresh_interval
            self.last_update_time = 0
            self.last_overall_completed = -1
            self.last_file_completed = {}
        except Exception as e:
            logger.warning(f"Failed to initialize ProgressManager: {e}")
            self.console = None
            self.progress = None
            self.live_display = None
            self.current_status = "Initializing..."
            self.overall_task_id = None
            self.enabled = False
            self.refresh_interval = refresh_interval
            self.last_update_time = 0
            self.last_overall_completed = -1
            self.last_file_completed = {}
    
    def __enter__(self):
        """Enter context manager - start live display."""
        if self.enabled and self.progress and self.console:
            try:
                # Reduced refresh rate to match throttling interval
                self.live_display = Live(self.progress, console=self.console, refresh_per_second=1 / self.refresh_interval)
                self.live_display.__enter__()
            except Exception as e:
                logger.warning(f"Failed to start live display: {e}")
                self.enabled = False
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - clean up resources."""
        self.close()
    
    def create_overall_task(self, total_files: int) -> Optional[int]:
        """Create overall progress task."""
        if not self.enabled or not self.progress:
            return None
        try:
            self.overall_task_id = self.progress.add_task(f"📁 Processing Files | {self.current_status}", total=total_files)
            return self.overall_task_id
        except Exception as e:
            logger.warning(f"Failed to create overall task: {e}")
            return None
    
    def create_file_task(self, filename: str, total_blocks: int) -> Optional[int]:
        """Create file processing task."""
        if not self.enabled or not self.progress:
            return None
        try:
            task_id = self.progress.add_task(f"🔄 {filename}", total=total_blocks)
            self.last_file_completed[task_id] = -1
            return task_id
        except Exception as e:
            logger.warning(f"Failed to create file task for {filename}: {e}")
            return None
    
    def start_live_display(self):
        """Start live display for progress bars (backward compatibility)."""
        if not self.enabled or not self.progress or not self.console:
            return None
        try:
            self.live_display = Live(self.progress, console=self.console, refresh_per_second=1 / self.refresh_interval)
            self.live_display.__enter__()
            return self.progress
        except Exception as e:
            logger.warning(f"Failed to start live display: {e}")
            self.enabled = False
            return None
    
    def update_status(self, current_operation: str):
        """Update status panel text."""
        self.current_status = current_operation
        if not self.enabled or not self.progress or self.overall_task_id is None:
            return
        try:
            # Update the overall task description to include status
            current_desc = self.progress.tasks[self.overall_task_id].description
            if "|" in current_desc:
                current_desc = current_desc.split("|", 1)[0]
            self.progress.update(self.overall_task_id, description=f"{current_desc.strip()} | {self.current_status}")
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
    
    def update_overall_progress(
        self,
        overall_task_id: int,
        completed_files: int,
        total_files: int,
        current_file: Optional[str] = None,
    ) -> None:
        """Update overall progress, optionally changing the displayed description."""
        if not self.enabled or not self.progress:
            return
        
        # Throttle updates and avoid unnecessary redraws
        current_time = time.time()
        if (current_time - self.last_update_time < self.refresh_interval) and (completed_files == self.last_overall_completed):
            return
        
        self.last_update_time = current_time
        self.last_overall_completed = completed_files
        
        try:
            update_kwargs: Dict[str, Any] = {"completed": completed_files}
            if current_file:
                update_kwargs["description"] = f"📄 {current_file} | {self.current_status}"
            self.progress.update(overall_task_id, **update_kwargs)
        except Exception as e:
            logger.warning(f"Failed to update overall progress: {e}")
    
    def update_file_progress(self, file_task_id: int, completed_blocks: int, total_blocks: int):
        """Update file progress."""
        if not self.enabled or not self.progress:
            return
        
        # Throttle updates and avoid unnecessary redraws
        current_time = time.time()
        if (current_time - self.last_update_time < self.refresh_interval) and (file_task_id in self.last_file_completed and completed_blocks == self.last_file_completed[file_task_id]):
            return
        
        self.last_update_time = current_time
        self.last_file_completed[file_task_id] = completed_blocks
        
        try:
            self.progress.update(file_task_id, completed=completed_blocks)
        except Exception as e:
            logger.warning(f"Failed to update file progress: {e}")
    
    def get_status_text(self, current_file: str, speed: float, eta: float, total_blocks: int, processed_blocks: int, language_info: str = ""):
        """Get status text for TUI display."""
        return f"⚡ Speed: {speed:.1f} files/sec | ⏱️  ETA: {eta:.1f}s | 📊 Blocks: {processed_blocks}/{total_blocks}"
    
    def close(self):
        """Close progress manager."""
        if self.live_display:
            try:
                self.live_display.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Failed to close live display: {e}")
            finally:
                self.live_display = None
        if self.progress:
            try:
                self.progress.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Failed to close progress: {e}")
            finally:
                self.progress = None
