#!/usr/bin/env python3
"""
Test script for Rust-specific optimizations in code indexing.
"""
import os
import sys
import json
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.chunking import TreeSitterChunkingStrategy

def test_rust_file_processing():
    """Test processing of Rust files with optimizations."""
    print("Testing Rust file processing optimizations...")
    
    # Load the Rust-optimized configuration
    config_path = "config/rust_optimized_config.json" if os.path.exists("config/rust_optimized_config.json") else "rust_optimized_config.json"
    if not os.path.exists(config_path):
        print(f"Error: Configuration file {config_path} not found")
        assert False, f"Configuration file {config_path} not found"
    
    try:
        config = Config.from_file(config_path)
        chunker = TreeSitterChunkingStrategy(config)
        
        # Test with a sample Rust file path
        test_rust_file = "/home/james/kanban_frontend/kanban_api/src/auth/db/queries.rs"
        
        # Check if file should be processed
        should_process = chunker._should_process_file_for_treesitter(test_rust_file)
        print(f"Should process {test_rust_file}: {should_process}")
        
        if should_process:
            # Get language key
            language_key = chunker._get_language_key_for_path(test_rust_file)
            print(f"Language key: {language_key}")
            
            # Test queries
            queries = chunker._get_queries_for_language(language_key)
            print(f"Rust queries available: {bool(queries)}")
            
            # Test node types
            node_types = chunker._get_node_types_for_language(language_key)
            print(f"Rust node types: {node_types}")
            
        # Rust file processing test passed
        
    except Exception as e:
        print(f"Error testing Rust optimizations: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Error testing Rust optimizations: {e}"

def test_configuration_loading():
    """Test that the Rust-optimized configuration loads correctly."""
    print("\nTesting Rust-optimized configuration...")
    
    try:
        config_path = "config/rust_optimized_config.json" if os.path.exists("config/rust_optimized_config.json") else "rust_optimized_config.json"
        config = Config.from_file(config_path)
        
        # Check Rust-specific settings
        rust_optimizations = getattr(config, "rust_specific_optimizations", {})
        print(f"Rust optimizations: {rust_optimizations}")
        
        # Check Tree-sitter settings
        print(f"Tree-sitter max file size: {getattr(config, 'tree_sitter_max_file_size_bytes', 'N/A')} bytes")
        print(f"Tree-sitter max blocks: {getattr(config, 'tree_sitter_max_blocks_per_file', 'N/A')}")
        print(f"Embed timeout: {getattr(config, 'embed_timeout_seconds', 'N/A')} seconds")
        
        # Configuration loading test passed
        
    except Exception as e:
        print(f"Error loading configuration: {e}")
        assert False, f"Error loading configuration: {e}"

def main():
    """Run all tests."""
    print("=" * 60)
    print("RUST OPTIMIZATION TESTS")
    print("=" * 60)
    
    success = True
    
    # Test configuration loading
    if not test_configuration_loading():
        success = False
    
    # Test Rust file processing
    if not test_rust_file_processing():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All Rust optimization tests passed!")
        print("\nRecommendations:")
        print("1. Use the rust_optimized_config.json for Rust codebases")
        print("2. Consider increasing embed_timeout_seconds for large Rust files")
        print("3. Monitor timeout_files.txt for files that need retry")
    else:
        print("❌ Some tests failed!")
        print("\nCheck the configuration and ensure Tree-sitter Rust support is installed:")
        print("pip install tree-sitter-rust")
    
    print("=" * 60)
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
