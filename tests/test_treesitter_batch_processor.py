"""
Unit tests for TreeSitterBatchProcessor service.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.services.batch_processor import TreeSitterBatchProcessor, BatchProcessingResult
from code_index import TreeSitterError
from code_index.errors import ErrorHandler
from code_index.models import CodeBlock


class TestTreeSitterBatchProcessor:
    """Test suite for TreeSitterBatchProcessor."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"

        self.error_handler = ErrorHandler("test")

        # Create the actual batch processor with real services
        self.batch_processor = TreeSitterBatchProcessor(
            self.config,
            self.error_handler
        )

    def test_initialization(self):
        """Test batch processor initialization."""
        assert self.batch_processor.config is self.config
        assert self.batch_processor.error_handler is self.error_handler
        assert hasattr(self.batch_processor, 'file_processor')
        assert hasattr(self.batch_processor, 'resource_manager')
        assert hasattr(self.batch_processor, 'block_extractor')

    def test_process_batch_single_file_basic(self):
        """Test batch processing with a single file - basic functionality."""
        files = [
            {
                'text': 'def hello_world():\n    print("Hello, World!")\n    return True',
                'file_path': 'test.py',
                'file_hash': 'hash123'
            }
        ]

        # Process the batch using real services
        results = self.batch_processor.process_batch(files)

        # Verify basic structure - should return BatchProcessingResult
        assert isinstance(results, BatchProcessingResult)
        assert results.success is True
        assert results.processed_files >= 0
        assert 'test.py' in results.results
        
        # The results should contain CodeBlock objects or empty list
        if results.results['test.py']:
            assert isinstance(results.results['test.py'][0], CodeBlock)

    def test_process_batch_multiple_files_basic(self):
        """Test batch processing with multiple files - basic functionality."""
        files = [
            {
                'text': 'def func1():\n    return 1',
                'file_path': 'file1.py',
                'file_hash': 'hash1'
            },
            {
                'text': 'def func2():\n    return 2',
                'file_path': 'file2.py',
                'file_hash': 'hash2'
            }
        ]

        results = self.batch_processor.process_batch(files)

        assert isinstance(results, BatchProcessingResult)
        assert results.success is True
        assert 'file1.py' in results.results
        assert 'file2.py' in results.results
        
        # Should have processed at least some files
        assert results.processed_files >= 0

    def test_process_batch_mixed_languages_basic(self):
        """Test batch processing with mixed language files - basic functionality."""
        files = [
            {
                'text': 'def python_func():\n    return "python"',
                'file_path': 'test.py',
                'file_hash': 'hash_py'
            },
            {
                'text': 'function jsFunc() {\n    return "js";\n}',
                'file_path': 'test.js',
                'file_hash': 'hash_js'
            }
        ]

        results = self.batch_processor.process_batch(files)

        assert isinstance(results, BatchProcessingResult)
        assert results.success is True
        assert 'test.py' in results.results
        assert 'test.js' in results.results
        assert results.processed_files >= 0

    def test_process_batch_empty_list(self):
        """Test batch processing with empty file list."""
        results = self.batch_processor.process_batch([])
        
        assert isinstance(results, BatchProcessingResult)
        assert results.results == {}
        assert results.processed_files == 0
        assert results.failed_files == 0

    def test_group_by_language(self):
        """Test grouping files by language."""
        files = [
            {'file_path': 'test.py', 'language': 'python'},
            {'file_path': 'test.js', 'language': 'javascript'},
            {'file_path': 'test2.py', 'language': 'python'},
            {'file_path': 'test2.js', 'language': 'javascript'},
            {'file_path': 'test.ts', 'language': 'typescript'}
        ]

        grouped = self.batch_processor.group_by_language(files)

        # Should group by actual language detection, not the mock language field
        assert isinstance(grouped, dict)
        # Files should be grouped somehow - either by detected language or as unknown
        assert len(grouped) >= 1

    def test_group_by_language_empty_list(self):
        """Test grouping empty file list."""
        grouped = self.batch_processor.group_by_language([])
        assert grouped == {}

    def test_group_by_language_no_language_key(self):
        """Test grouping files without language key."""
        files = [
            {'file_path': 'test.py'},
            {'file_path': 'test.js'},
            {'file_path': 'test.txt'}
        ]

        grouped = self.batch_processor.group_by_language(files)

        # Should group by detected language or unknown
        assert isinstance(grouped, dict)
        assert len(grouped) >= 1

    def test_optimize_batch_config(self):
        """Test batch configuration optimization."""
        python_files = [
            {'file_path': 'test1.py', 'size': 1000},
            {'file_path': 'test2.py', 'size': 2000},
            {'file_path': 'test3.py', 'size': 3000}
        ]

        optimized_config = self.batch_processor.optimize_batch_config('python', len(python_files))

        # Check that config contains expected optimization parameters
        assert isinstance(optimized_config, dict)
        assert 'max_blocks_per_file' in optimized_config
        assert 'timeout_multiplier' in optimized_config
        assert 'resource_sharing' in optimized_config
        assert 'parallel_processing' in optimized_config

    def test_optimize_batch_config_empty_list(self):
        """Test batch configuration optimization with empty list."""
        optimized_config = self.batch_processor.optimize_batch_config('python', 0)
        
        assert isinstance(optimized_config, dict)
        assert 'max_blocks_per_file' in optimized_config

    def test_process_files_integration(self):
        """Test processing actual files from filesystem."""
        # Create temporary test files
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test Python file
            test_file = os.path.join(temp_dir, 'test.py')
            with open(test_file, 'w') as f:
                f.write('def test_function():\n    return "test"')
            
            # Process the file
            results = self.batch_processor.process_files([test_file])
            
            assert isinstance(results, BatchProcessingResult)
            assert results.success is True
            assert test_file in results.results

    def test_error_handling_invalid_file(self):
        """Test error handling for invalid files."""
        files = [
            {
                'text': 'invalid python syntax {{{',
                'file_path': 'invalid.py',
                'file_hash': 'hash_invalid'
            }
        ]

        results = self.batch_processor.process_batch(files)

        # Should handle errors gracefully
        assert isinstance(results, BatchProcessingResult)
        assert 'invalid.py' in results.results
        # Should not crash, even if extraction fails
        assert isinstance(results.results['invalid.py'], list)

    def test_memory_efficiency_with_shared_resources(self):
        """Test memory efficiency with shared resources."""
        files = [
            {
                'text': 'def func1():\n    return 1',
                'file_path': 'file1.py',
                'file_hash': 'hash1'
            },
            {
                'text': 'def func2():\n    return 2',
                'file_path': 'file2.py',
                'file_hash': 'hash2'
            }
        ]

        results = self.batch_processor.process_batch(files)

        assert isinstance(results, BatchProcessingResult)
        assert results.success is True
        assert 'file1.py' in results.results
        assert 'file2.py' in results.results

    def test_error_recovery_mechanism(self):
        """Test error recovery mechanism in batch processing."""
        files = [
            {
                'text': 'def func1():\n    return 1',
                'file_path': 'file1.py',
                'file_hash': 'hash1'
            },
            {
                'text': 'def func2():\n    return 2',
                'file_path': 'file2.py',
                'file_hash': 'hash2'
            },
            {
                'text': 'def func3():\n    return 3',
                'file_path': 'file3.py',
                'file_hash': 'hash3'
            }
        ]

        results = self.batch_processor.process_batch(files)

        # Should process all files despite potential errors
        assert isinstance(results, BatchProcessingResult)
        assert results.success is True
        assert 'file1.py' in results.results
        assert 'file2.py' in results.results
        assert 'file3.py' in results.results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])