"""
Unit tests for the new TreeSitterBlockExtractor with 2024-2025 best practices.
"""
from code_index.config import Config
from code_index.services import TreeSitterBlockExtractor  # noqa: F401
from code_index.errors import ErrorHandler


class TestTreeSitterBlockExtractorNew:
    """Test suite for the new TreeSitterBlockExtractor implementation."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"
        self.config.tree_sitter_min_block_chars = 5 # Reduced to support short names
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
        
        # Check that we have function and class blocks (Unified Schema types)
        function_blocks = [b for b in blocks if b.type == 'function']
        class_blocks = [b for b in blocks if b.type == 'class']
        
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
        
        # Check that we have function and class blocks (Unified Schema types)
        function_blocks = [b for b in blocks if b.type == 'function']
        class_blocks = [b for b in blocks if b.type == 'class']
        
        assert len(function_blocks) >= 1
        assert len(class_blocks) >= 1

    def test_extract_blocks_empty_code(self):
        """Test extracting blocks from empty code."""
        blocks = self.extractor.extract_blocks("", "test.py", "hash")
        assert len(blocks) == 0

    def test_extract_blocks_whitespace_only(self):
        """Test extracting blocks from whitespace-only code."""
        blocks = self.extractor.extract_blocks("   \n  \t ", "test.py", "hash")
        assert len(blocks) == 0

    def test_extract_blocks_invalid_language(self):
        """Test extracting blocks with an invalid language key."""
        code = "def test(): pass"
        blocks = self.extractor.extract_blocks(code, "test.txt", "hash", language_key="xyz")
        # Should return empty list for invalid languages in this context
        assert len(blocks) == 0

    def test_extract_blocks_from_root_node(self):
        """Test extraction from an existing root node."""
        import tree_sitter_language_pack
        lang = tree_sitter_language_pack.get_language('python')
        from tree_sitter import Parser
        parser = Parser(lang)
        
        code = "def test(): pass"
        tree = parser.parse(bytes(code, 'utf8'))
        
        res = self.extractor.extract_blocks_from_root_node(
            tree.root_node, code, "test.py", "hash", "python"
        )
        
        assert res.success is True
        assert len(res.blocks) >= 1
        assert res.blocks[0].type == 'function'

    def test_extraction_result_metadata(self):
        """Test that extraction result contains expected metadata."""
        code = "def test(): pass"
        res = self.extractor.extract_blocks_from_root_node(
             None, code, "test.py", "hash", "python"
        )
        
        if res.success:
             assert 'language_key' in res.metadata
             assert 'extraction_method' in res.metadata
             assert 'blocks_found' in res.metadata

    def test_cache_functionality(self):
        """Test that extractor uses internal cache."""
        code = "def test(): pass"
        file_path = "test.py"
        file_hash = "hash123"
        
        self.extractor.clear_caches()
        blocks1 = self.extractor.extract_blocks(code, file_path, file_hash, "python")
        blocks2 = self.extractor.extract_blocks(code, file_path, file_hash, "python")
        
        assert blocks1 == blocks2
        stats = self.extractor.get_extraction_stats()
        assert stats['cache_hits'] >= 1

    def test_error_handling(self):
        """Test extractor error handling."""
        # Graceful handling of invalid inputs
        # type: ignore[arg-type]
        assert self.extractor.extract_blocks(None, None, None) == []
        
        # In this implementation, if root_node is None, we fallback to basic chunking 
        # but that only happens if text is provided.
        res = self.extractor.extract_blocks_from_root_node(None, "code", "test.py", "hash", "python")
        assert res.success is True
        assert len(res.blocks) >= 1

    def test_performance_monitoring(self):
        """Test that extraction performance is monitored."""
        code = "def test(): pass"
        self.extractor.extract_blocks(code, "test.py", "hash", "python")
        
        stats = self.extractor.get_extraction_stats()
        assert stats['total_extractions'] >= 1
        assert stats['total_processing_time_ms'] > 0

    def test_memory_efficiency(self):
        """Test memory efficiency of block extraction."""
        self.extractor.clear_caches()
        
        code = "def test(): pass"
        for i in range(10):
            self.extractor.extract_blocks(code, f"test{i}.py", f"hash{i}", "python")
            
        stats = self.extractor.get_extraction_stats()
        assert stats['total_extractions'] == 10

    def test_language_detection_fallback(self):
        """Test fallback when language detection fails."""
        blocks = self.extractor.extract_blocks("some random text", "Dockerfile", "hash")
        assert len(blocks) == 0

    def test_block_limits_enforcement(self):
        """Test that max_blocks is enforced."""
        code = "\n".join([f"def func{i}(): pass" for i in range(50)])
        
        max_blocks = 5
        blocks = self.extractor.extract_blocks(code, "test.py", "hash", "python", max_blocks=max_blocks)
        
        assert len(blocks) <= max_blocks
