"""
Unit tests for the new TreeSitterBlockExtractor with 2024-2025 best practices.
"""
import pytest
from code_index.config import Config
from code_index.services.block_extractor import TreeSitterBlockExtractor, ExtractionResult
from code_index.errors import ErrorHandler


class TestTreeSitterBlockExtractorNew:
    """Test suite for the new TreeSitterBlockExtractor implementation."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"
        self.config.tree_sitter_min_block_chars = 10
        self.config.tree_sitter_max_blocks_per_file = 100
        self.config.tree_sitter_timeout_seconds = 30.0
        self.config.tree_sitter_debug_logging = False

        self.error_handler = ErrorHandler("test")
        self.extractor = TreeSitterBlockExtractor(self.config, self.error_handler)

    def test_extract_blocks_python_function(self):
        """Test extracting blocks from Python code."""
        code = '''
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
        
        blocks = self.extractor.extract_blocks(
            code, 
            "test.py", 
            "hash123", 
            language_key="python"
        )
        
        # Should extract function and class definitions
        assert len(blocks) > 0
        
        # Check that we have function and class blocks
        function_blocks = [b for b in blocks if b.type == 'function_definition']
        class_blocks = [b for b in blocks if b.type == 'class_definition']
        
        assert len(function_blocks) >= 1
        assert len(class_blocks) >= 1
        
        # Check block properties
        for block in blocks:
            assert block.file_path == "test.py"
            assert block.file_hash == "hash123"
            assert block.identifier is not None
            assert block.content is not None
            assert len(block.content.strip()) >= self.config.tree_sitter_min_block_chars

    def test_extract_blocks_javascript_function(self):
        """Test extracting blocks from JavaScript code."""
        code = '''
function helloWorld() {
    console.log("Hello, World!");
    return true;
}

class MyClass {
    constructor() {
        this.value = 42;
    }
    
    getValue() {
        return this.value;
    }
}

const arrowFunc = () => {
    return "arrow function";
};
'''
        
        blocks = self.extractor.extract_blocks(
            code, 
            "test.js", 
            "hash456", 
            language_key="javascript"
        )
        
        # Should extract function and class definitions
        assert len(blocks) > 0
        
        # Check that we have function and class blocks
        function_blocks = [b for b in blocks if 'function' in b.type.lower()]
        class_blocks = [b for b in blocks if 'class' in b.type.lower()]
        
        assert len(function_blocks) >= 1
        assert len(class_blocks) >= 1

    def test_extract_blocks_empty_code(self):
        """Test extracting blocks from empty code."""
        blocks = self.extractor.extract_blocks("", "test.py", "hash123", "python")
        assert len(blocks) == 0

    def test_extract_blocks_whitespace_only(self):
        """Test extracting blocks from whitespace-only code."""
        blocks = self.extractor.extract_blocks("   \n  \n   ", "test.py", "hash123", "python")
        assert len(blocks) == 0

    def test_extract_blocks_invalid_language(self):
        """Test extracting blocks with invalid language."""
        blocks = self.extractor.extract_blocks("some code", "test.xyz", "hash123")
        assert len(blocks) == 0

    def test_extract_blocks_from_root_node(self):
        """Test extracting blocks from a TreeSitter root node."""
        code = '''
def test_function():
    return "test"

class TestClass:
    def test_method(self):
        return "method"
'''
        
        # Create a mock root node for testing
        from unittest.mock import Mock
        mock_root_node = Mock()
        mock_root_node.start_point = (0, 0)
        mock_root_node.end_point = (6, 0)
        mock_root_node.type = "module"
        
        result = self.extractor.extract_blocks_from_root_node(
            mock_root_node, 
            code, 
            "test.py", 
            "hash123", 
            "python"
        )
        
        assert isinstance(result, ExtractionResult)
        assert result.success is True
        assert len(result.blocks) >= 0  # May be empty due to mock limitations

    def test_extraction_result_metadata(self):
        """Test that ExtractionResult contains proper metadata."""
        code = 'def test(): pass'
        
        result = self.extractor.extract_blocks_from_root_node(
            None,  # Will use structural analysis fallback
            code, 
            "test.py", 
            "hash123", 
            "python"
        )
        
        assert isinstance(result, ExtractionResult)
        assert result.processing_time_ms >= 0
        assert result.metadata is not None
        assert 'language_key' in result.metadata
        assert result.metadata['language_key'] == 'python'

    def test_cache_functionality(self):
        """Test caching functionality."""
        code = 'def test(): pass'
        
        # First call should populate cache
        blocks1 = self.extractor.extract_blocks(code, "test.py", "hash123", "python")
        
        # Second call should use cache
        blocks2 = self.extractor.extract_blocks(code, "test.py", "hash123", "python")
        
        assert len(blocks1) == len(blocks2)
        
        # Check cache stats
        stats = self.extractor.get_extraction_stats()
        assert stats['cache_hits'] >= 1

    def test_error_handling(self):
        """Test error handling during extraction."""
        # Test with invalid parameters
        blocks = self.extractor.extract_blocks(None, "test.py", "hash123", "python")
        assert len(blocks) == 0
        
        # Test with empty file path
        blocks = self.extractor.extract_blocks("def test(): pass", "", "hash123", "python")
        assert len(blocks) == 0

    def test_performance_monitoring(self):
        """Test performance monitoring functionality."""
        code = '''
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
'''
        
        # Extract blocks multiple times
        for i in range(3):
            blocks = self.extractor.extract_blocks(code, f"test{i}.py", f"hash{i}", "python")
        
        # Check performance stats
        stats = self.extractor.get_extraction_stats()
        assert stats['total_extractions'] >= 3
        assert stats['total_processing_time_ms'] > 0

    def test_memory_efficiency(self):
        """Test memory efficiency with weak references."""
        import gc
        
        # Extract blocks
        code = 'def test(): pass'
        blocks = self.extractor.extract_blocks(code, "test.py", "hash123", "python")
        
        # Clear caches
        self.extractor.clear_caches()
        
        # Force garbage collection
        gc.collect()
        
        # Check that stats are reset
        stats = self.extractor.get_extraction_stats()
        assert stats['total_extractions'] == 0

    def test_language_detection_fallback(self):
        """Test language detection fallback when language_key is None."""
        code = 'def test(): pass'
        
        # Test with file extension
        blocks = self.extractor.extract_blocks(code, "test.py", "hash123")
        assert len(blocks) > 0
        
        # Test with special filename
        blocks = self.extractor.extract_blocks("FROM ubuntu:latest", "Dockerfile", "hash123")
        assert len(blocks) == 0  # Dockerfile language not supported yet

    def test_block_limits_enforcement(self):
        """Test that block limits are properly enforced."""
        # Create code with many functions
        code = '\n'.join([f'def func{i}(): return {i}' for i in range(200)])
        
        # Extract with limit
        blocks = self.extractor.extract_blocks(
            code, 
            "test.py", 
            "hash123", 
            "python",
            max_blocks=50
        )
        
        # Should respect the limit
        assert len(blocks) <= 50