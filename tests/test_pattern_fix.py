import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.smart_ignore_manager import SmartIgnoreManager

def test_pattern_fix():
    """Test pattern matching fix."""
    print("=== Testing Pattern Matching Fix ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    
    # Initialize smart ignore manager
    ignore_manager = SmartIgnoreManager(config.workspace_path, config)
    
    # Test the specific pattern that should match .egg-info files
    pattern = "*.egg-info/"
    print(f"Testing pattern: {pattern}")
    
    # Test various file paths that should be ignored
    test_paths = [
        "src/code_index/code_index.egg-info/top_level.txt",
        "src/code_index/code_index.egg-info/SOURCES.txt",
        "src/code_index/code_index.egg-info/dependency_links.txt",
        "src/code_index/code_index.egg-info/PKG-INFO",
        "src/code_index/code_index.egg-info/requires.txt"
    ]
    
    for rel_path in test_paths:
        # Test the current matching logic
        matches_current = ignore_manager._matches_pattern(rel_path, pattern)
        
        # Test improved matching logic
        matches_improved = _improved_matches_pattern(rel_path, pattern)
        
        print(f"{rel_path}:")
        print(f"  Current: {matches_current}")
        print(f"  Improved: {matches_improved}")
        print()

def _improved_matches_pattern(file_path: str, pattern: str) -> bool:
    """Improved pattern matching that handles directory patterns better."""
    import fnmatch
    
    # Handle directory patterns ending with /
    if pattern.endswith('/'):
        dir_pattern = pattern[:-1]  # Remove trailing slash
        
        # Check if any parent directory matches the pattern
        path_parts = file_path.split(os.sep)
        for i in range(len(path_parts)):
            # Reconstruct directory path up to this level
            dir_path = os.sep.join(path_parts[:i+1])
            if fnmatch.fnmatch(dir_path, dir_pattern):
                return True
            if fnmatch.fnmatch(path_parts[i], dir_pattern):
                return True
                
        return False
    
    # Handle wildcard patterns
    if '*' in pattern or '?' in pattern:
        try:
            return fnmatch.fnmatch(file_path, pattern)
        except:
            pass
    
    # Handle exact matches
    if file_path == pattern:
        return True
    
    # Handle extensions
    if pattern.startswith('*.'):
        _, ext = os.path.splitext(file_path)
        if ext == pattern[1:]:
            return True
    
    return False

if __name__ == "__main__":
    test_pattern_fix()