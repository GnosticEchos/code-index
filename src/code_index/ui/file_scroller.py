"""
File scroller for TUI file processing display.
"""
from typing import List, Optional

class FileScroller:
    """Display files being processed in TUI operations."""
    
    def __init__(self, max_files: int = 5):
        """Initialize file scroller."""
        self.max_files = max_files
        self.files = []
    
    def add_file(self, file_path: str, file_size: str = "Unknown"):
        """Add a file to the scroller."""
        # Remove oldest file if we have too many files
        if len(self.files) >= self.max_files:
            self.files.pop(0)
        
        # Add new file
        self.files.append({
            "path": file_path,
            "size": file_size,
            "status": "pending"
        })
    
    def update_status(self, file_path: str, status: str):
        """Update file status."""
        for file in self.files:
            if file["path"] == file_path:
                file["status"] = status
    
    def get_display_text(self) -> str:
        """Get display text for TUI display."""
        if not self.files:
            return "No files being processed"
        
        display_lines = []
        for file in self.files:
            status_symbol = "✅" if file["status"] == "success" else "🔄" if file["status"] == "processing" else "⏳"
            display_lines.append(f"{status_symbol} {file['path']} ({file['size']})")
        
        return "\n".join(display_lines)
    
    def clear(self):
        """Clear all files."""
        self.files = []
