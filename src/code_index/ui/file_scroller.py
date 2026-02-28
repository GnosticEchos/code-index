"""File scroller for TUI file processing display."""
from typing import List, Dict

class FileScroller:
    """Display files being processed in TUI operations."""

    def __init__(self, max_files: int = 5):
        """Initialize file scroller."""
        self.max_files = max_files
        self.files: List[Dict[str, str]] = []
        self.file_map: Dict[str, Dict[str, str]] = {}  # O(1) lookups

    def add_file(self, file_path: str, file_size: str = "Unknown"):
        """Add a file to the scroller."""
        # If file already exists, update size and return
        if file_path in self.file_map:
            self.file_map[file_path]["size"] = file_size
            # Update in files list too
            for file in self.files:
                if file["path"] == file_path:
                    file["size"] = file_size
            return

        # Remove oldest file if we have too many files
        if len(self.files) >= self.max_files:
            oldest_file = self.files.pop(0)
            del self.file_map[oldest_file["path"]]

        # Add new file
        file_entry = {
            "path": file_path,
            "size": file_size,
            "status": "pending",
            "message": ""
        }
        self.files.append(file_entry)
        self.file_map[file_path] = file_entry

    def ensure_file(self, file_path: str, file_size: str = "Unknown"):
        """Ensure a file entry exists, adding it if necessary."""
        if file_path not in self.file_map:
            self.add_file(file_path, file_size)
    
    def update_status(self, file_path: str, status: str, message: str = ""):
        """Update file status."""
        if file_path in self.file_map:
            self.file_map[file_path]["status"] = status
            if message:
                self.file_map[file_path]["message"] = message
    
    def get_display_text(self) -> str:
        """Get display text for TUI display."""
        if not self.files:
            return "No files being processed"
        
        display_lines = []
        for file in self.files:
            status = file.get("status", "pending")
            if status == "success":
                status_symbol = "✅"
            elif status == "processing":
                status_symbol = "🔄"
            elif status == "error":
                status_symbol = "❌"
            elif status == "skipped":
                status_symbol = "⏭️"
            else:
                status_symbol = "⏳"

            message = file.get("message", "")
            line = f"{status_symbol} {file['path']} ({file['size']})"
            if message:
                line += f" - {message}"
            display_lines.append(line)
        
        return "\n".join(display_lines)
    
    def clear(self):
        """Clear all files."""
        self.files = []
        self.file_map.clear()
