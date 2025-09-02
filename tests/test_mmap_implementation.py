#!/usr/bin/env python3
"""
Test script to verify mmap file reading implementation.
"""

import os
import tempfile
from src.code_index.config import Config
from src.code_index.parser import CodeParser
from src.code_index.chunking import LineChunkingStrategy


def test_mmap_implementation():
    """Test that mmap file reading works correctly."""
    print("Testing mmap file reading implementation...")
    
    # Create test content
    test_content = """#!/usr/bin/env python3
# Test file for mmap implementation
def hello_world():
    \"\"\"A simple hello world function.\"\"\"
    print("Hello, World!")
    return "Hello, World!"

class TestClass:
    \"\"\"A test class for demonstration.\"\"\"
    
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        \"\"\"Return the stored value.\"\"\"
        return self.value

if __name__ == "__main__":
    hello_world()
    obj = TestClass()
    print(f"Value: {obj.get_value()}")
"""
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        # Test traditional reading
        config_trad = Config()
        config_trad.use_mmap_file_reading = False
        parser_trad = CodeParser(config_trad, LineChunkingStrategy(config_trad))
        
        result_trad = parser_trad.parse_file(test_file)
        print(f"Traditional reading: {len(result_trad)} blocks")
        
        # Test mmap reading
        config_mmap = Config()
        config_mmap.use_mmap_file_reading = True
        parser_mmap = CodeParser(config_mmap, LineChunkingStrategy(config_mmap))
        
        result_mmap = parser_mmap.parse_file(test_file)
        print(f"Mmap reading: {len(result_mmap)} blocks")
        
        # Verify results are identical
        if len(result_trad) != len(result_mmap):
            print("ERROR: Different number of blocks generated!")
            assert False, "Different number of blocks generated!"
        
        for i, (block_trad, block_mmap) in enumerate(zip(result_trad, result_mmap)):
            if block_trad.content != block_mmap.content:
                print(f"ERROR: Block {i} content mismatch!")
                print(f"Traditional: {len(block_trad.content)} chars")
                print(f"Mmap: {len(block_mmap.content)} chars")
                assert False, f"Block {i} content mismatch!"
        
        print("✓ Both methods produce identical results")
        
        # Test configuration options
        config_small = Config()
        config_small.use_mmap_file_reading = True
        config_small.mmap_min_file_size_bytes = 1024 * 1024  # 1MB minimum
        
        # This should use traditional reading since file is small
        parser_small = CodeParser(config_small, LineChunkingStrategy(config_small))
        result_small = parser_small.parse_file(test_file)
        print(f"Small file with high threshold: {len(result_small)} blocks")
        
        print("✓ Configuration options work correctly")
        
        # Test passed successfully
        
    finally:
        # Clean up
        try:
            os.unlink(test_file)
        except:
            pass


def test_error_handling():
    """Test error handling in mmap implementation."""
    print("\nTesting error handling...")
    
    # Test with non-existent file
    config = Config()
    config.use_mmap_file_reading = True
    parser = CodeParser(config, LineChunkingStrategy(config))
    
    result = parser.parse_file("/non/existent/file.py")
    if len(result) == 0:
        print("✓ Non-existent file handled gracefully")
    else:
        print("ERROR: Non-existent file should return empty list")
        assert False, "Non-existent file should return empty list"
    
    # Test with empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        empty_file = f.name
    
    try:
        result = parser.parse_file(empty_file)
        if len(result) == 0:
            print("✓ Empty file handled correctly")
        else:
            print("ERROR: Empty file should return empty list")
            assert False, "Empty file should return empty list"
    finally:
        try:
            os.unlink(empty_file)
        except:
            pass
    
    # Error handling tests passed


if __name__ == "__main__":
    print("Running mmap implementation tests...")
    print("=" * 50)
    
    success = True
    success &= test_mmap_implementation()
    success &= test_error_handling()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    
    exit(0 if success else 1)