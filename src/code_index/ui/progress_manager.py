"""
Progress manager for TUI progress bars and status display.
"""
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn, TaskProgressColumn, MofNCompleteColumn
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from typing import Optional, Dict, Any


class ProgressManager:
    """Manage progress bars and status display for TUI operations."""
    
    def __init__(self):
        """Initialize progress manager."""
        self.console = Console()
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
    
    def create_overall_task(self, total_files: int) -> int:
        """Create overall progress task."""
        self.overall_task_id = self.progress.add_task(f"📁 Processing Files | {self.current_status}", total=total_files)
        return self.overall_task_id
    
    def create_file_task(self, filename: str, total_blocks: int) -> int:
        """Create file processing task."""
        return self.progress.add_task(f"🔄 {filename}", total=total_blocks)
    
    def start_live_display(self):
        """Start live display for progress bars using context manager pattern."""
        self.live_display = Live(self.progress, console=self.console, refresh_per_second=10)
        self.live_display.__enter__()
        return self.progress
    
    def update_status(self, current_operation: str):
        """Update status panel text."""
        self.current_status = current_operation
        if self.overall_task_id is not None:
            # Update the overall task description to include status
            current_desc = self.progress.tasks[self.overall_task_id].description
            if "|" in current_desc:
                current_desc = current_desc.split("|", 1)[0]
            self.progress.update(self.overall_task_id, description=f"{current_desc.strip()} | {self.current_status}")
    
    def update_overall_progress(
        self,
        overall_task_id: int,
        completed_files: int,
        total_files: int,
        current_file: Optional[str] = None,
    ) -> None:
        """Update overall progress, optionally changing the displayed description."""
        update_kwargs: Dict[str, Any] = {"completed": completed_files}
        if current_file:
            update_kwargs["description"] = f"📄 {current_file} | {self.current_status}"
        self.progress.update(overall_task_id, **update_kwargs)
    
    def update_file_progress(self, file_task_id: int, completed_blocks: int, total_blocks: int):
        """Update file progress."""
        self.progress.update(file_task_id, completed=completed_blocks)
    
    def get_status_text(self, current_file: str, speed: float, eta: float, total_blocks: int, processed_blocks: int, language_info: str = ""):
        """Get status text for TUI display."""
        return f"⚡ Speed: {speed:.1f} files/sec | ⏱️  ETA: {eta:.1f}s | 📊 Blocks: {processed_blocks}/{total_blocks}"
    
    def close(self):
        """Close progress manager."""
        if self.live_display:
            self.live_display.__exit__(None, None, None)
            self.live_display = None
        if self.progress:
            self.progress.__exit__(None, None, None)
