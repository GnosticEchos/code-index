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
        if refresh_interval <= 0:
            refresh_interval = 0.1
        
        try:
            self.console = console or Console()
            # One single bar for everything
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
            self.last_description = ""
        except Exception as e:
            logger.warning(f"Failed to initialize ProgressManager: {e}")
            self.enabled = False
    
    def __enter__(self):
        if self.enabled and self.progress and self.console:
            try:
                self.live_display = Live(self.progress, console=self.console, refresh_per_second=1 / self.refresh_interval)
                self.live_display.__enter__()
            except Exception:
                self.enabled = False
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_overall_task(self, total_files: int) -> Optional[int]:
        """Create or return the existing overall progress task."""
        if not self.enabled or not self.progress:
            return None
            
        # Return existing task if already created
        if self.overall_task_id is not None:
            return self.overall_task_id
            
        try:
            desc = f"📁 Processing Files | {self.current_status}"
            self.overall_task_id = self.progress.add_task(desc, total=total_files)
            self.last_description = desc
            return self.overall_task_id
        except Exception:
            return None
    
    def start_live_display(self):
        if not self.enabled or not self.progress or not self.console:
            return None
        try:
            # Singleton live display
            if self.live_display is None:
                self.live_display = Live(self.progress, console=self.console, refresh_per_second=1 / self.refresh_interval)
                self.live_display.__enter__()
            return self.progress
        except Exception:
            self.enabled = False
            return None
    
    def update_status(self, current_operation: str):
        self.current_status = current_operation
        if not self.enabled or self.overall_task_id is None:
            return
        self._update_display()
    
    def update_overall_progress(
        self,
        overall_task_id: int,
        completed_files: int,
        total_files: int,
        current_file: Optional[str] = None,
    ) -> None:
        """Update the single overall progress bar."""
        if not self.enabled or not self.progress:
            return
        
        # Ensure we are updating the correct task
        target_task_id = overall_task_id if overall_task_id is not None else self.overall_task_id
        if target_task_id is None:
            return

        # Throttling
        current_time = time.time()
        is_final = completed_files >= total_files
        
        # Build a single unified description
        if current_file and "Processing Files" not in current_file:
            new_desc = f"📄 {current_file} | {self.current_status}"
        else:
            new_desc = f"📁 Processing Files | {self.current_status}"

        progress_changed = completed_files != self.last_overall_completed
        desc_changed = new_desc != self.last_description

        # Only skip if too soon AND progress/desc hasn't changed (unless it's the final update)
        if not is_final and (current_time - self.last_update_time < self.refresh_interval):
            if not progress_changed and not desc_changed:
                return

        self.last_update_time = current_time
        self.last_overall_completed = completed_files
        self.last_description = new_desc
        
        try:
            self.progress.update(target_task_id, completed=completed_files, description=new_desc)
        except Exception:
            pass

    def _update_display(self):
        """Internal helper to refresh the current task description."""
        if self.overall_task_id is not None:
             if "📄" in self.last_description:
                 parts = self.last_description.split("|", 1)
                 new_desc = f"{parts[0].strip()} | {self.current_status}"
             else:
                 new_desc = f"📁 Processing Files | {self.current_status}"
             
             self.progress.update(self.overall_task_id, description=new_desc)
             self.last_description = new_desc

    def close(self):
        if self.live_display:
            try:
                self.live_display.__exit__(None, None, None)
            except Exception:
                pass
            finally:
                self.live_display = None
        if self.progress:
            # rich.progress.Progress doesn't have an __exit__ but its Live parent does
            self.progress = None
            
    # Legacy methods marked for removal
    def create_file_task(self, filename: str, total_blocks: int): return None
    def update_file_progress(self, file_task_id: int, completed_blocks: int, total_blocks: int): pass
    def get_status_text(self, *args, **kwargs): return ""
