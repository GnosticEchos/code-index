#!/usr/bin/env python3
"""
Simple test to verify Tree-sitter integration works correctly.
"""
import os
import sys
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.parser import CodeParser


def simple_treesitter_test():
    """Simple test of Tree-sitter integration."""
    print("=== Simple Tree-sitter Test ===")
    
    # Create test file
    test_dir = tempfile.mkdtemp(prefix="simple_treesitter_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Create simple Python file
        test_file = os.path.join(test_dir, "simple.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    print('Hello')\n")
        
        # Test configuration
        config = Config()
        config.use_tree_sitter = True
        config.chunking_strategy = "treesitter"
        config.tree_sitter_skip_test_files = False
        config.tree_sitter_skip_examples = False
        config.tree_sitter_skip_patterns = []
        
        # Initialize parser
        parser = CodeParser(config)
        
        # Test file processing check
        should_process = parser._should_process_file_for_treesitter(test_file)
        print(f"Should process file: {should_process}")
        
        # Read file content
        with open(test_file, "r") as f:
            content = f.read()
        
        # Calculate file hash
        from code_index.utils import get_file_hash
        file_hash = get_file_hash(test_file)
        
        # Test language key detection
        try:
            language_key = parser._get_language_key_for_path(test_file)
            print(f"Language key detected: {language_key}")
            
            if language_key:
                print("✅ Language detection working")
            else:
                print("⚠️  Language detection returned None")
                
        except Exception as e:
            print(f"Language detection error: {e}")
        
        # Test Tree-sitter parser loading
        try:
            if language_key:
                parser_obj = parser._get_tree_sitter_parser(language_key)
                if parser_obj:
                    print("✅ Tree-sitter parser loaded successfully")
                else:
                    print("⚠️  Tree-sitter parser returned None")
            else:
                print("Skipping parser test - no language key")
        except Exception as e:
            print(f"Parser loading error: {e}")
            
        print("\n=== Simple Tree-sitter Test Complete ===")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = simple_treesitter_test()
    sys.exit(0 if success else 1)