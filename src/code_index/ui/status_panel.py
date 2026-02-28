"""
Status panel for TUI operations.
"""
from typing import Optional
import logging
import time

from rich.panel import Panel
from rich.console import Console
from rich.text import Text

logger = logging.getLogger(__name__)


class StatusPanel:
    """Display status information in TUI operations."""
    
    def __init__(self, console: Console, refresh_interval: float = 0.1):
        """Initialize status panel."""
        try:
            self.console = console
            self.enabled = True
            self.refresh_interval = refresh_interval
            self.last_update_time = 0
            self.last_operation = ""
            self.last_language_info = ""
            self.last_error_info = ""
        except Exception as e:
            logger.warning(f"Failed to initialize StatusPanel: {e}")
            self.console = None
            self.enabled = False
            self.refresh_interval = refresh_interval
            self.last_update_time = 0
            self.last_operation = ""
            self.last_language_info = ""
            self.last_error_info = ""
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass
    
    def create_panel(self, current_operation: str, language_info: str = "", error_info: str = "") -> Optional[Panel]:
        """Create status panel."""
        if not self.enabled or not self.console:
            return None
        
        # Throttle updates and avoid unnecessary redraws
        current_time = time.time()
        if (current_time - self.last_update_time < self.refresh_interval) and \
           (current_operation == self.last_operation) and \
           (language_info == self.last_language_info) and \
           (error_info == self.last_error_info):
            return None
            
        self.last_update_time = current_time
        self.last_operation = current_operation
        self.last_language_info = language_info
        self.last_error_info = error_info
        
        try:
            status_text = Text()
            status_text.append(f"🔄 Current: {current_operation}", style="blue")
            
            if language_info:
                status_text.append(f" | 🔍 {language_info}", style="blue")
            
            if error_info:
                status_text.append(f" | ❌ {error_info}", style="red")
            
            return Panel(status_text, title="Status", border_style="blue")
        except Exception as e:
            logger.warning(f"Failed to create status panel: {e}")
            return None
    
    def update_operation(self, current_operation: str) -> Optional[Panel]:
        """Update current operation."""
        return self.create_panel(current_operation)
    
    def show_error(self, error_message: str) -> Optional[Panel]:
        """Show error message with proper formatting."""
        if not self.enabled or not self.console:
            logger.error(f"Error: {error_message}")
            return None
        try:
            error_text = Text()
            error_text.append("❌ Error: ", style="red")
            error_text.append(error_message, style="red")
            return Panel(error_text, title="Error", border_style="red")
        except Exception as e:
            logger.warning(f"Failed to show error panel: {e}")
            logger.error(f"Error: {error_message}")
            return None
    
    def show_warning(self, warning_message: str) -> Optional[Panel]:
        """Show warning message with proper formatting."""
        if not self.enabled or not self.console:
            logger.warning(f"Warning: {warning_message}")
            return None
        try:
            warning_text = Text()
            warning_text.append("⚠️  Warning: ", style="yellow")
            warning_text.append(warning_message, style="yellow")
            return Panel(warning_text, title="Warning", border_style="yellow")
        except Exception as e:
            logger.warning(f"Failed to show warning panel: {e}")
            logger.warning(f"Warning: {warning_message}")
            return None
    
    def show_success(self, message: str) -> Optional[Panel]:
        """Show success message with proper formatting."""
        if not self.enabled or not self.console:
            logger.info(f"Success: {message}")
            return None
        try:
            success_text = Text()
            success_text.append(f"✅ Success: {message}", style="green")
            return Panel(success_text, title="Success", border_style="green")
        except Exception as e:
            logger.warning(f"Failed to show success panel: {e}")
            logger.info(f"Success: {message}")
            return None
