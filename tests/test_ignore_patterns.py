import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.smart_ignore_manager import SmartIgnoreManager

def test_ignore_patterns():
    """Test if ignore patterns are working correctly."""
    print("=== Testing Ignore Patterns ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    
    # Initialize smart ignore manager
    ignore_manager = SmartIgnoreManager(config.workspace_path, config)
    
    # Get all ignore patterns
    patterns = ignore_manager.get_all_ignore_patterns()
    print(f"Total ignore patterns: {len(patterns)}")
    print("First 20 patterns:")
    for i, pattern in enumerate(patterns[:20]):
        print(f"  {i+1}. {pattern}")
    
    # Test specific files that should be ignored
    test_files = [
        "src/code_index/code_index.egg-info/top_level.txt",
        "src/code_index/code_index.egg-info/SOURCES.txt", 
        "src/code_index/__pycache__/__init__.cpython-313.pyc",
        ".venv/bin/python",
        "build/lib/code_index/__init__.py"
    ]
    
    print(f"\n=== Testing File Ignore Detection ===")
    for file_path in test_files:
        # Create absolute path for testing
        abs_path = os.path.join(config.workspace_path, file_path)
        should_ignore = ignore_manager.should_ignore_file(abs_path)
        print(f"{file_path}: {'IGNORE' if should_ignore else 'INDEX'}")
        
        # Also test pattern matching manually
        rel_path = os.path.relpath(abs_path, config.workspace_path)
        for pattern in patterns:
            if ignore_manager._matches_pattern(rel_path, pattern):
                print(f"  -> Matches pattern: {pattern}")

if __name__ == "__main__":
    test_ignore_patterns()