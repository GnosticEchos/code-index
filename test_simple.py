#!/usr/bin/env python3
"""
Simple test to verify TreeSitter chunking works with a Python file.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.services.block_extractor import TreeSitterBlockExtractor
from code_index.config import Config

def test_tree_sitter_python():
    """Test TreeSitter extraction with Python code."""
    print("Testing TreeSitter extraction with Python code...")
    
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
    print(f"Extracted {len(blocks)} blocks:")
    for block in blocks:
        print(f"  - {block.type}: {block.identifier} (lines {block.start_line}-{block.end_line})")
        print(f"    Content: {repr(block.content[:50])}...")
    
    return len(blocks) > 0

if __name__ == "__main__":
    print("Running TreeSitter extraction test...")
    success = test_tree_sitter_python()
    print(f"TreeSitter extraction: {'PASS' if success else 'FAIL'}")