#!/usr/bin/env python3
"""
Simple test script to verify Tree-sitter integration fixes.
"""
import os
import sys
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.chunking import TreeSitterChunkingStrategy

def test_language_detection():
    """Test language detection functionality."""
    print("=== Testing Language Detection ===")
    
    config = Config()
    strategy = TreeSitterChunkingStrategy(config)
    
    test_files = [
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.ts", "typescript"),
        ("test.go", "go"),
        ("test.rs", "rust"),
        ("test.txt", None),  # Should return None
        ("README.md", "极速赛车公众号飞单markdown"),
        ("config.yaml", "yaml"),
        ("styles.css", "css"),
    ]
    
    for filename, expected_lang in test_files:
        detected_lang = strategy._get_language_key_for_path(filename)
        status = "✓" if detected_lang == expected_lang else "✗"
        print(f"{status} {filename}: expected={expected_lang}, got={detected_lang}")

def test_filtering_logic():
    """Test filtering logic."""
    print("\n=== Testing Filtering Logic ===")
    
    config = Config()
    strategy = TreeSitterChunkingStrategy(config)
    
    test_files = [
        ("test.py", True),  # Should be processed
        ("test_test.py", False),  # Should be filtered out (test file)
        ("example.py", False),  # Should be filtered out (example file)
        ("main.py", True),  # Should be processed
        ("utils.py", True),  # Should be processed
    ]
    
    for filename, should_process in test_files:
        result = strategy._should_process_file_for_treesitter(filename)
        status = "✓" if result == should_process else "✗"
        print(f"{status} {filename}: expected={should_process}, got={result}")

if __name__ == "__main__":
    test_language_detection()
    test_filtering_logic()
    print("\n=== Test Complete ===")