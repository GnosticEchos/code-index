"""
TUI integration for rich TUI operations.
"""
from typing import Optional
import time

from code_index.config import Config
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from code_index.ui.progress_manager import ProgressManager
from code_index.ui.file_scroller import FileScroller
from code_index.ui.status_panel import StatusPanel
from rich.console import Console


class TUIInterface:
    """TUI interface for rich TUI operations."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None, console: Optional[Console] = None, refresh_interval: float = 0.1):
        """Initialize TUI interface."""
        self.error_handler = error_handler or ErrorHandler()
        self.console = console or Console()
        self.refresh_interval = refresh_interval
        self.progress_manager = ProgressManager(self.console, refresh_interval)
        self.file_scroller = FileScroller()
        self.status_panel = StatusPanel(self.console, refresh_interval)
        self.live_display = None
        self.last_update_time = 0
        self.last_status_text = ""
    
    def __enter__(self):
        """Enter context manager - initialize progress manager."""
        self.progress_manager.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - clean up resources."""
        self.close()
    
    def start_indexing(self, total_files: int):
        """Start indexing with TUI display."""
        overall_task_id = self.progress_manager.create_overall_task(total_files)
        return overall_task_id
    
    def update_indexing_progress(self, overall_task_id: int, completed_files: int, total_files: int, current_file: str, speed: float, eta: float, total_blocks: int, processed_blocks: int, language_info: str = ""):
        """Update indexing progress."""
        # Throttle updates
        current_time = time.time()
        if current_time - self.last_update_time < self.refresh_interval:
            return None
            
        status_text = self.progress_manager.get_status_text(current_file, speed, eta, total_blocks, processed_blocks, language_info)
        
        # Avoid unnecessary updates if status hasn't changed
        if status_text == self.last_status_text:
            return None
            
        self.last_update_time = current_time
        self.last_status_text = status_text
        
        self.progress_manager.update_overall_progress(overall_task_id, completed_files, total_files)
        return self.status_panel.create_panel("Indexing", language_info=status_text)
    
    def add_file_to_scroller(self, file_path: str, file_size: str = "Unknown"):
        """Add file to file scroller."""
        self.file_scroller.add_file(file_path, file_size)
    
    def update_file_status(self, file_path: str, status: str):
        """Update file status in scroller."""
        self.file_scroller.update_status(file_path, status)
    
    def show_error(self, error_message: str):
        """Show error in TUI."""
        return self.status_panel.show_error(error_message)
    
    def show_search_results(self, results: list, query: str):
        """Show search results in TUI."""
        if not results:
            return f"No results found for query: {query}"
        
        results_text = []
        for result in results:
            results_text.append(f"Rank: {result.get('rank', 0)} | Score: {result.get('score', 0.0):.3f} | File: {result.get('file_path', 'Unknown')}:{result.get('start_line', 0)}-{result.get('end_line', 0)} | Type: {result.get('type', 'unknown')}")
        
        return "\n".join(results_text)
    
    def close(self):
        """Close TUI interface."""
        self.progress_manager.close()
        if self.live_display:
            self.live_display.stop()
