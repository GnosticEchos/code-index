"""
Status panel for TUI operations.
"""
from typing import Optional

from rich.panel import Panel
from rich.console import Console

class StatusPanel:
    """Display status information in TUI operations."""
    
    def __init__(self, console: Console):
        """Initialize status panel."""
        self.console = console
    
    def create_panel(self, current_operation: str, language_info: str = "", error_info: str = "") -> Panel:
        """Create status panel."""
        status_text = f"🔄 Current: {current_operation}"
        
        if language_info:
            status_text += f" | 🔍 {language_info}"
        
        if error_info:
            status_text += f" | ❌ {error_info}"
        
        return Panel(status_text, title="Status", border_style="blue")
    
    def update_operation(self, current_operation: str):
        """Update current operation."""
        return self.create_panel(current_operation)
    
    def show_error(self, error_message: str):
        """Show error message."""
        return self.create_panel("Error", error_info=error_message)
    
    def show_success(self, message: str):
        """Show success message."""
        return self.create_panel("Success", language_info=message)
