"""
TUI (Terminal User Interface) components for code-index.

Provides Rich-based progress bars, file scrollers, and status panels
for enhanced user experience during indexing operations.
"""

from .progress_manager import ProgressManager
from .file_scroller import FileScroller
from .status_panel import StatusPanel
from .tui_integration import TUIInterface

__all__ = ["ProgressManager", "FileScroller", "StatusPanel", "TUIInterface"]
