"""
Path resolution service.
"""
import os
from typing import Optional


class PathResolver:
    """Resolves and normalizes file paths."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getcwd()
    
    def resolve(self, path: str) -> str:
        """Resolve path relative to base."""
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self.base_path, path))
    
    def get_relative(self, path: str) -> str:
        """Get path relative to base."""
        try:
            return os.path.relpath(path, self.base_path)
        except ValueError:
            return path
    
    def get_extension(self, path: str) -> str:
        """Get file extension."""
        return os.path.splitext(path)[1].lower()
    
    def get_language_from_path(self, path: str) -> Optional[str]:
        """Get language from file path."""
        ext = self.get_extension(path)
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.rs': 'rust', '.go': 'go', '.java': 'java', '.cpp': 'cpp',
            '.c': 'c', '.h': 'c', '.hpp': 'cpp', '.cs': 'csharp'
        }
        return lang_map.get(ext)