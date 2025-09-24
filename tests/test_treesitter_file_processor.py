"""
Unit tests for TreeSitterFileProcessor service.
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.services.file_processor import TreeSitterFileProcessor
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

    def test_validate_file_test_file_filtered(self):
        """Test that test files are filtered out when configured."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as f:
            f.write('def test_something():\n    assert True\n')
            temp_file = f.name

        try:
            result = self.processor.validate_file(temp_file)
            assert result is False  # Should be filtered out
        finally:
            os.unlink(temp_file)

    def test_validate_file_example_file_filtered(self):
        """Test that example files are filtered out when configured."""
        # Create a temporary example file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_example.py', delete=False) as f:
            f.write('def example_function():\n    return "example"\n')
            temp_file = f.name

        try:
            result = self.processor.validate_file(temp_file)
            assert result is False  # Should be filtered out
        finally:
            os.unlink(temp_file)

    def test_validate_file_custom_pattern_filtered(self):
        """Test that files matching custom patterns are filtered."""
        # Create a temporary file with custom pattern
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f:
            f.write('temporary content\n')
            temp_file = f.name

        try:
            result = self.processor.validate_file(temp_file)
            assert result is False  # Should be filtered out
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

    def test_apply_language_optimizations_python(self):
        """Test language-specific optimizations for Python."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
class MyClass:
    def __init__(self):
        self.value = 42

    def method(self):
        return self.value
''')
            temp_file = f.name

        try:
            optimizations = self.processor.apply_language_optimizations(temp_file)
            assert 'language' in optimizations
            assert optimizations['language'] == 'python'
            assert 'max_file_size' in optimizations
            assert 'max_blocks' in optimizations
        finally:
            os.unlink(temp_file)

    def test_apply_language_optimizations_javascript(self):
        """Test language-specific optimizations for JavaScript."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write('function hello() { console.log("Hello"); }')
            temp_file = f.name

        try:
            optimizations = self.processor.apply_language_optimizations(temp_file)
            assert 'language' in optimizations
            assert optimizations['language'] == 'javascript'
        finally:
            os.unlink(temp_file)

    def test_apply_language_optimizations_unsupported_language(self):
        """Test optimizations for unsupported language."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write('unknown file content')
            temp_file = f.name

        try:
            optimizations = self.processor.apply_language_optimizations(temp_file)
            assert optimizations is None
        finally:
            os.unlink(temp_file)

    def test_filter_by_criteria_size_limit(self):
        """Test filtering by file size criteria."""
        # Create a large file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Write content larger than typical limits - actually create 1MB of content
            content = 'def function():\n    return "' + 'x' * 1000000 + '"\n'
            f.write(content)
            temp_file = f.name

        try:
            # Mock a very small size limit
            original_limit = getattr(self.config, 'tree_sitter_max_file_size_bytes', None)
            self.config.tree_sitter_max_file_size_bytes = 100  # Very small limit

            result = self.processor.filter_by_criteria(temp_file, {'size': len(content.encode())})
            assert result is False  # Should be filtered due to size
        finally:
            # Restore original limit
            if original_limit is not None:
                self.config.tree_sitter_max_file_size_bytes = original_limit
            os.unlink(temp_file)

    def test_filter_by_criteria_valid_file(self):
        """Test filtering of valid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def valid_function():\n    return "valid"\n')
            temp_file = f.name

        try:
            result = self.processor.filter_by_criteria(temp_file, {'size': 50})
            assert result is True  # Should pass all criteria
        finally:
            os.unlink(temp_file)

    def test_get_file_language_python(self):
        """Test language detection for Python files."""
        language = self.processor._get_file_language('test.py')
        assert language == 'python'

    def test_get_file_language_typescript(self):
        """Test language detection for TypeScript files."""
        language = self.processor._get_file_language('test.ts')
        assert language == 'typescript'

    def test_get_file_language_unsupported(self):
        """Test language detection for unsupported files."""
        language = self.processor._get_file_language('test.xyz')
        assert language is None

    def test_is_test_file_detection(self):
        """Test test file detection logic."""
        test_files = [
            'test_example.py',
            'example_test.py',
            'test_example_test.py',
            'tests/test_file.py',
            'test.py'
        ]

        non_test_files = [
            'example.py',
            'main.py',
            'utils.py',
            'config.py'
        ]

        for test_file in test_files:
            assert self.processor._is_test_file(test_file) is True

        for non_test_file in non_test_files:
            assert self.processor._is_test_file(non_test_file) is False

    def test_is_example_file_detection(self):
        """Test example file detection logic."""
        example_files = [
            'example.py',
            'sample.py',
            'demo.py',
            'examples/example.py'
        ]

        non_example_files = [
            'main.py',
            'utils.py',
            'test.py',
            'config.py'
        ]

        for example_file in example_files:
            assert self.processor._is_example_file(example_file) is True

        for non_example_file in non_example_files:
            assert self.processor._is_example_file(non_example_file) is False

    def test_matches_skip_pattern(self):
        """Test pattern matching for skip patterns."""
        # Test cases: (pattern, file, expected_result)
        test_cases = [
            ('*.tmp', 'file.tmp', True),
            ('*.tmp', 'data.tmp', True),
            ('*.tmp', 'file.py', False),
            ('*.tmp', 'data.txt', False),
            
            ('*.log', 'data.log', True),
            ('*.log', 'error.log', True),
            ('*.log', 'data.txt', False),
            ('*.log', 'file.py', False),
            
            ('temp_*', 'temp_file.py', True),
            ('temp_*', 'temp_data.js', True),
            ('temp_*', 'file.py', False),
            ('temp_*', 'main.py', False),
        ]

        for pattern, file_path, expected in test_cases:
            result = self.processor._matches_skip_pattern(file_path, pattern)
            assert result is expected, f"Pattern '{pattern}' should {'match' if expected else 'not match'} '{file_path}', got {result}"

    def test_error_handling_invalid_file(self):
        """Test error handling for invalid files."""
        with patch.object(self.error_handler, 'handle_error') as mock_handle:
            result = self.processor.validate_file('/invalid/path/file.py')
            assert result is False
            mock_handle.assert_called_once()

    def test_error_handling_file_access_error(self):
        """Test error handling for file access errors."""
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write('def test_function():\n    return True\n')  # Add content to avoid empty file filter
                    temp_file = f.name

                try:
                    # Make file unreadable
                    os.chmod(temp_file, 0o000)

                    result = self.processor.validate_file(temp_file)
                    assert result is False
                    mock_handle.assert_called_once()
                finally:
                    os.chmod(temp_file, 0o644)  # Restore permissions
                    os.unlink(temp_file)

    def test_configuration_integration(self):
        """Test integration with configuration service."""
        # Test that configuration changes are reflected
        original_skip_test = self.config.tree_sitter_skip_test_files
        original_skip_examples = self.config.tree_sitter_skip_examples

        try:
            # Disable filtering
            self.config.tree_sitter_skip_test_files = False
            self.config.tree_sitter_skip_examples = False

            with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as f:
                f.write('def test_function():\n    return True\n')
                temp_file = f.name

            try:
                result = self.processor.validate_file(temp_file)
                assert result is True  # Should pass when filtering disabled
            finally:
                os.unlink(temp_file)

        finally:
            # Restore original settings
            self.config.tree_sitter_skip_test_files = original_skip_test
            self.config.tree_sitter_skip_examples = original_skip_examples


if __name__ == "__main__":
    pytest.main([__file__, "-v"])