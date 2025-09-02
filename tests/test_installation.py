#!/usr/bin/env python3
"""
Test script to verify the code index tool installation.
"""
import sys
import os

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

def test_imports():
    """Test that all modules can be imported."""
    try:
        from code_index.config import Config
        from code_index.utils import get_file_hash
        from code_index.cache import CacheManager
        from code_index.scanner import DirectoryScanner
        from code_index.parser import CodeParser, CodeBlock
        from code_index.embedder import OllamaEmbedder
        from code_index.vector_store import QdrantVectorStore
        print("All modules imported successfully!")
        assert True
    except ImportError as e:
        print(f"Import error: {e}")
        assert False

def test_config():
    """Test configuration creation."""
    try:
        from code_index.config import Config
        config = Config()
        print(f"Configuration created: {config}")
        assert True
    except Exception as e:
        print(f"Configuration error: {e}")
        assert False

def main():
    """Run all tests."""
    print("Testing code index tool installation...")
    
    success = True
    success &= test_imports()
    success &= test_config()
    
    if success:
        print("\nAll tests passed! The code index tool is properly installed.")
        print("Run 'code-index --help' to see available commands.")
    else:
        print("\nSome tests failed. Please check the installation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
