#!/usr/bin/env python3
"""
Test script to verify TreeSitter chunking and TUI progress bar fixes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.services.block_extractor import TreeSitterBlockExtractor
from code_index.config import Config
from code_index.models import CodeBlock
import tempfile

def test_tree_sitter_extraction():
    """Test that TreeSitter extraction actually uses TreeSitter parsing."""
    print("Testing TreeSitter extraction...")
    
    # Create a config
    config = Config()
    config.tree_sitter_debug_logging = True
    
    # Create block extractor
    extractor = TreeSitterBlockExtractor(config)
    
    # Test Python code
    python_code = '''
def hello_world():
    """A simple function."""
    print("Hello, World!")
    return True

class MyClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
    
    # Test extraction
    blocks = extractor.extract_blocks(python_code, "test.py", "test_hash", "python")
    print(f"Extracted {len(blocks)} blocks using regex-based extraction:")
    for block in blocks:
        print(f"  - {block.type}: {block.identifier} (lines {block.start_line}-{block.end_line})")
    
    # Test with a mock root node to verify TreeSitter path
    class MockNode:
        def __init__(self):
            self.language = None
    
    mock_root = MockNode()
    result = extractor.extract_blocks_from_root(mock_root, python_code, "test.py", "test_hash", "python")
    print(f"Extracted {len(result.blocks)} blocks using TreeSitter extraction:")
    for block in result.blocks:
        print(f"  - {block.type}: {block.identifier} (lines {block.start_line}-{block.end_line})")
    
    print(f"Extraction method: {result.metadata.get('extraction_method', 'unknown')}")
    
    return len(result.blocks) > 0 and result.metadata.get('extraction_method') == 'treesitter'

def test_tui_progress():
    """Test TUI progress bar functionality."""
    print("\nTesting TUI progress bars...")
    
    from code_index.ui.progress_manager import ProgressManager
    
    try:
        progress_manager = ProgressManager()
        
        # Test creating and updating tasks
        overall_task = progress_manager.create_overall_task(100)
        file_task = progress_manager.create_file_task("test.py", 50)
        
        # Test starting live display
        progress = progress_manager.start_live_display()
        print("Live display started successfully")
        
        # Test updating progress
        progress_manager.update_overall_progress(overall_task, 25, 100)
        progress_manager.update_file_progress(file_task, 10, 50)
        print("Progress updates completed successfully")
        
        # Test closing
        progress_manager.close()
        print("Progress manager closed successfully")
        
        return True
        
    except Exception as e:
        print(f"TUI progress test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running TreeSitter and TUI fixes verification...")
    
    tree_sitter_success = test_tree_sitter_extraction()
    tui_success = test_tui_progress()
    
    print(f"\nResults:")
    print(f"TreeSitter extraction: {'PASS' if tree_sitter_success else 'FAIL'}")
    print(f"TUI progress bars: {'PASS' if tui_success else 'FAIL'}")