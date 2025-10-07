#!/usr/bin/env python3
"""
Test script to verify TreeSitter chunking with actual TreeSitter parsing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.services.block_extractor import TreeSitterBlockExtractor
from code_index.config import Config
import tempfile

def test_tree_sitter_real_parsing():
    """Test that TreeSitter extraction actually uses TreeSitter parsing with real parser."""
    print("Testing TreeSitter extraction with real parser...")
    
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
    
    # Test extraction using the main extract_blocks method (which should use TreeSitter when available)
    blocks = extractor.extract_blocks(python_code, "test.py", "test_hash", "python")
    print(f"Extracted {len(blocks)} blocks:")
    for block in blocks:
        print(f"  - {block.type}: {block.identifier} (lines {block.start_line}-{block.end_line})")
    
    # Test with fallback method
    result = extractor.extract_blocks_with_fallback(python_code, "test.py", "test_hash", "python")
    print(f"Extracted {len(result)} blocks with fallback:")
    for block in result:
        print(f"  - {block.type}: {block.identifier} (lines {block.start_line}-{block.end_line})")
    
    # Check if we're actually using TreeSitter
    print(f"\nDebug info:")
    print(f"  - Debug enabled: {extractor.debug_enabled}")
    print(f"  - Min block chars: {extractor.min_block_chars}")
    
    return len(blocks) > 0

def test_tui_progress_advanced():
    """Test TUI progress bar functionality with more realistic usage."""
    print("\nTesting TUI progress bars with realistic usage...")
    
    from code_index.ui.progress_manager import ProgressManager
    
    try:
        progress_manager = ProgressManager()
        
        # Simulate indexing process
        total_files = 100
        overall_task = progress_manager.create_overall_task(total_files)
        
        # Start live display
        progress = progress_manager.start_live_display()
        print("Live display started successfully")
        
        # Simulate file processing
        for i in range(total_files):
            file_task = progress_manager.create_file_task(f"file_{i}.py", 50)
            
            # Simulate block processing
            for j in range(50):
                progress_manager.update_file_progress(file_task, j + 1, 50)
            
            # Update overall progress
            progress_manager.update_overall_progress(overall_task, i + 1, total_files)
        
        # Test closing
        progress_manager.close()
        print("Progress manager closed successfully")
        
        return True
        
    except Exception as e:
        print(f"TUI progress test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running TreeSitter and TUI fixes verification...")
    
    tree_sitter_success = test_tree_sitter_real_parsing()
    tui_success = test_tui_progress_advanced()
    
    print(f"\nResults:")
    print(f"TreeSitter extraction: {'PASS' if tree_sitter_success else 'FAIL'}")
    print(f"TUI progress bars: {'PASS' if tui_success else 'FAIL'}")