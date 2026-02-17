"""
Unit tests for TreeSitterFileProcessor service.

Tests the public API of TreeSitterFileProcessor.
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.services import TreeSitterFileProcessor
from code_index.errors import ErrorHandler


class TestTreeSitterFileProcessor:
    """Test suite for TreeSitterFileProcessor."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"
        self.config.tree_sitter_skip_test_files = True
        self.config.tree_sitter_skip_examples = True
        self.config.tree_sitter_skip_patterns = ['*.tmp', '*.log']
        self.config.tree_sitter_max_file_size_bytes = 512 * 1024  # 512KB

        self.error_handler = ErrorHandler("test")
        self.processor = TreeSitterFileProcessor(self.config, self.error_handler)

    def test_validate_file_valid_python_file(self):
        """Test validation of a valid Python file."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def hello_world():\n    print("Hello, World!")\n')
            temp_file = f.name

        try:
            result = self.processor.validate_file(temp_file)
            assert result is True
        finally:
            os.unlink(temp_file)

    def test_validate_file_nonexistent_file(self):
        """Test validation of non-existent file."""
        result = self.processor.validate_file('/path/that/does/not/exist.py')
        assert result is False

    def test_validate_file_empty_file(self):
        """Test validation of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = f.name

        try:
            result = self.processor.validate_file(temp_file)
            assert result is False  # Empty files should be filtered
        finally:
            os.unlink(temp_file)

    def test_validate_file_binary_file(self):
        """Test validation of binary file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
            f.write(b'\x00\x01\x02\x03')  # Binary content
            temp_file = f.name

        try:
            result = self.processor.validate_file(temp_file)
            assert result is False  # Binary files should be filtered
        finally:
            os.unlink(temp_file)

    def test_validate_file_generated_directory_filtered(self):
        """Test that files in generated directories are filtered."""
        # Files in generated directories like __pycache__, node_modules should be filtered
        result = self.processor.validate_file('/some/path/__pycache__/file.py')
        assert result is False

        result = self.processor.validate_file('/some/path/node_modules/package/index.js')
        assert result is False

    def test_get_file_info_valid_file(self):
        """Test getting file info for a valid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def hello(): pass\n')
            temp_file = f.name

        try:
            info = self.processor.get_file_info(temp_file)

            assert info['path'] == temp_file
            assert info['exists'] is True
            assert info['is_file'] is True
            assert info['size_bytes'] > 0
            assert info['extension'] == '.py'
            assert info['is_valid'] is True
            assert info['should_process'] is True
        finally:
            os.unlink(temp_file)

    def test_get_file_info_nonexistent_file(self):
        """Test getting file info for non-existent file."""
        info = self.processor.get_file_info('/path/that/does/not/exist.py')

        assert info['path'] == '/path/that/does/not/exist.py'
        assert info['exists'] is False
        assert info['is_file'] is False
        assert info['is_valid'] is False
        assert info['should_process'] is False

    def test_get_file_info_directory(self):
        """Test getting file info for a directory - directories are not valid files."""
        # Create a temporary directory that persists for this test
        temp_dir = tempfile.mkdtemp()
        try:
            info = self.processor.get_file_info(temp_dir)

            # The get_file_info method only checks for file existence, not directory
            # A directory will show as exists=False because is_file() is False
            assert info['path'] == temp_dir
            assert info['is_file'] is False
            assert info['is_valid'] is False
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_file_language_python(self):
        """Test language detection for Python files."""
        language = self.processor._get_file_language('test.py')
        assert language == 'python'

    def test_get_file_language_javascript(self):
        """Test language detection for JavaScript files."""
        language = self.processor._get_file_language('test.js')
        assert language == 'javascript'

    def test_get_file_language_typescript(self):
        """Test language detection for TypeScript files."""
        language = self.processor._get_file_language('test.ts')
        assert language == 'typescript'

    def test_get_file_language_unsupported(self):
        """Test language detection for unsupported files."""
        language = self.processor._get_file_language('test.xyz')
        # Should return None for unsupported extensions
        assert language is None or language == 'unknown'

    def test_scalability_config_loaded(self):
        """Test that scalability configuration is loaded."""
        assert hasattr(self.processor, 'enable_chunked_processing')
        assert hasattr(self.processor, 'large_file_threshold')
        assert hasattr(self.processor, 'streaming_threshold')
        assert hasattr(self.processor, 'default_chunk_size')

    def test_monitoring_config_loaded(self):
        """Test that monitoring configuration is loaded."""
        assert hasattr(self.processor, 'enable_performance_tracking')
        assert hasattr(self.processor, 'log_mmap_metrics')
        assert hasattr(self.processor, 'log_resource_usage')

    def test_get_file_size(self):
        """Test getting file size."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def hello(): pass\n')
            temp_file = f.name

        try:
            size = self.processor._get_file_size(temp_file)
            assert size > 0
        finally:
            os.unlink(temp_file)

    def test_get_file_size_nonexistent(self):
        """Test getting file size for non-existent file."""
        size = self.processor._get_file_size('/path/that/does/not/exist.py')
        assert size == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])