#!/usr/bin/env python3
"""
Test script to verify Tree-sitter integration fixes.
"""
import os
import sys
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.chunking import TreeSitterChunkingStrategy

def test_treesitter_basic():
    """Test basic Tree-sitter functionality."""
    print("=== Testing Tree-sitter Integration ===")
    
    # Create a test configuration
    config = Config()
    config.chunking_strategy = "treesitter"
    config.use_tree_sitter = True
    
    # Create a Tree-sitter chunking strategy
    strategy = TreeSitterChunkingStrategy(config)
    
    # Test with a simple Python file
    python_code = '''
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return "Hello"

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
    
    print("\n1. Testing Python code parsing:")
    try:
        # Use a simple hash for testing instead of file-based hash
        test_hash = "test_python_hash"
        blocks = strategy.chunk(python_code, "test.py", test_hash)
        print(f"✓ Successfully parsed Python code into {len(blocks)} blocks")
        for i, block in enumerate(blocks[:3]):  # Show first 3 blocks
            print(f"  Block {i+1}: {block.type} (lines {block.start_line}-{block.end_line})")
    except Exception as e:
        print(f"✗ Python parsing failed: {e}")
    
    # Test with unsupported file type (text file)
    print("\n2. Testing text file handling:")
    text_content = "This is a plain text file.\nIt should not be processed by Tree-sitter."
    try:
        test_hash = "test_text_hash"
        blocks = strategy.chunk(text_content, "test.txt", test_hash)
        print(f"✓ Text file handled gracefully with {len(blocks)} line-based blocks")
    except Exception as e:
        print(f"✗ Text file handling failed: {e}")
    
    # Test with markdown file
    print("\n3. Testing markdown file handling:")
    markdown_content = '''
# Test Document

This is a test document.

## Section 1

Some content here.

- List item 1
- List item 2
'''
    try:
        test_hash = "test_markdown_hash"
        blocks = strategy.chunk(markdown_content, "test.md", test_hash)
        print(f"✓ Markdown file handled with {len(blocks)} blocks")
    except Exception as e:
        print(f"✗ Markdown file handling failed: {e}")

def test_language_detection():
    """Test language detection functionality."""
    print("\n=== Testing Language Detection ===")
    
    config = Config()
    strategy = TreeSitterChunkingStrategy(config)
    
    test_files = [
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.ts", "typescript"),
        ("极速赛车公众号飞单test.go", "go"),
        ("test.rs", "rust"),
        ("test.txt", None),  # Should return None
        ("README.md", "markdown"),
        ("config.yaml", "yaml"),
        ("styles.css", "css"),
    ]
    
    for filename, expected_lang in test_files:
        detected_lang = strategy._get_language_key_for_path(filename)
        status = "✓" if detected_lang == expected_lang else "✗"
        print(f"{status} {filename}: expected={expected_lang}, got={detected_lang}")

if __name__ == "__main__":
    test_treesitter_basic()
    test_language_detection()
    print("\n=== Test Complete ===")