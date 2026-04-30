"""
File filtering service.
"""
import os
from typing import List, Optional

class FileFilter:
    """Filters files based on patterns and rules."""
    
    def __init__(self, skip_patterns: Optional[List[str]] = None, skip_test_files: bool = True):
        self.skip_patterns = skip_patterns or []
        self.skip_test_files = skip_test_files
    
    def should_process(self, file_path: str) -> bool:
        """Check if file should be processed."""
        basename = os.path.basename(file_path)
        
        # Skip test files
        if self.skip_test_files and ('test_' in basename or '_test.' in basename or basename.startswith('test.')):
            return False
        
        # Skip patterns
        for pattern in self.skip_patterns:
            if pattern in file_path:
                return False
        
        return True
    
    def filter_files(self, files: List[str]) -> List[str]:
        """Filter list of files."""
        return [f for f in files if self.should_process(f)]