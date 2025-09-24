"""
Unit tests for TreeSitterResourceManager service.
"""
import os
import sys
import time
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index import TreeSitterError
from code_index.services.resource_manager import TreeSitterResourceManager
from code_index.chunking import TreeSitterError
from code_index.errors import ErrorHandler


class TestTreeSitterResourceManager:
    """Test suite for TreeSitterResourceManager."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"

        self.error_handler = ErrorHandler("test")
        self.resource_manager = TreeSitterResourceManager(self.config, self.error_handler)

    def test_initialization(self):
        """Test resource manager initialization."""
        assert self.resource_manager.config is self.config
        assert self.resource_manager.error_handler is self.error_handler
        assert hasattr(self.resource_manager, 'parsers')
        assert hasattr(self.resource_manager, 'query_cache')
        assert hasattr(self.resource_manager, 'resource_usage')

    def test_ensure_tree_sitter_version_success(self):
        """Test successful Tree-sitter version check."""
        with patch('tree_sitter.Query') as mock_query:
            mock_query.captures = True
            mock_query.matches = True

            # Should not raise an exception
            self.resource_manager.ensure_tree_sitter_version()

    def test_ensure_tree_sitter_version_failure_no_bindings(self):
        """Test Tree-sitter version check failure due to missing bindings."""
        with patch.dict('sys.modules', {'tree_sitter': None}):
            with pytest.raises(TreeSitterError, match="Tree-sitter package not installed"):
                self.resource_manager.ensure_tree_sitter_version()

    def test_ensure_tree_sitter_version_failure_no_api(self):
        """Test Tree-sitter version check failure due to missing API."""
        with patch('tree_sitter.Query') as mock_query:
            # Remove all API methods
            del mock_query.captures
            del mock_query.matches

            with patch('tree_sitter.QueryCursor', side_effect=ImportError):
                with pytest.raises(TreeSitterError, match="Tree-sitter bindings do not expose"):
                    self.resource_manager.ensure_tree_sitter_version()

    def test_acquire_resources_parser_creation(self):
        """Test resource acquisition with parser creation."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            # Mock the language loading
            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                resources = self.resource_manager.acquire_resources('python')

                assert 'parser' in resources
                assert 'language' in resources
                assert resources['parser'] == mock_parser_instance
                assert resources['language'] == mock_language_instance

    def test_acquire_resources_parser_reuse(self):
        """Test resource acquisition with parser reuse."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            # First acquisition
            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                resources1 = self.resource_manager.acquire_resources('python')

                # Second acquisition should reuse
                resources2 = self.resource_manager.acquire_resources('python')

                # Parser should be the same instance (reused)
                assert resources1['parser'] is resources2['parser']

    def test_release_resources(self):
        """Test resource release."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                resources = self.resource_manager.acquire_resources('python')

                # Release resources
                self.resource_manager.release_resources('python', resources)

                # Parser should be deleted
                mock_parser_instance.delete.assert_called_once()

    def test_cleanup_all_resources(self):
        """Test cleanup of all resources."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                # Acquire resources for multiple languages
                resources1 = self.resource_manager.acquire_resources('python')
                resources2 = self.resource_manager.acquire_resources('javascript')

                # Cleanup all
                self.resource_manager.cleanup_all()

                # All parsers should be deleted
                assert mock_parser_instance.delete.call_count == 2

    def test_resource_timeout_handling(self):
        """Test resource timeout handling."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            # Set a very short timeout
            original_timeout = getattr(self.config, 'embed_timeout_seconds', None)
            self.config.embed_timeout_seconds = 0.001  # Very short timeout

            try:
                with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                    with patch('time.sleep'):  # Mock sleep to speed up test
                        resources = self.resource_manager.acquire_resources('python')

                        # Should still return resources even with timeout
                        assert 'parser' in resources
                        assert 'language' in resources
            finally:
                if original_timeout is not None:
                    self.config.embed_timeout_seconds = original_timeout

    def test_resource_usage_tracking(self):
        """Test resource usage tracking."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                # Initial usage should be zero
                initial_usage = self.resource_manager.get_resource_usage()
                assert initial_usage['parsers'] == 0
                assert initial_usage['languages'] == 0

                # Acquire resources
                self.resource_manager.acquire_resources('python')

                # Usage should increase
                usage = self.resource_manager.get_resource_usage()
                assert usage['parsers'] == 1
                assert usage['languages'] == 1

    def test_memory_monitoring(self):
        """Test memory usage monitoring."""
        with patch('psutil.Process') as mock_process:
            mock_proc = Mock()
            mock_process.return_value = mock_proc
            mock_proc.memory_info.return_value = Mock(rss=1000000)  # 1MB

            memory_usage = self.resource_manager.get_memory_usage()
            assert memory_usage == 1000000  # Should return RSS in bytes

    def test_memory_monitoring_disabled(self):
        """Test memory monitoring when psutil is not available."""
        with patch.dict('sys.modules', {'psutil': None}):
            # Should not raise an error
            memory_usage = self.resource_manager.get_memory_usage()
            assert memory_usage == 0  # Should return 0 when psutil not available

    def test_parser_lifecycle_management(self):
        """Test parser lifecycle management."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                # Create parser
                parser = self.resource_manager._create_parser('python')
                assert parser == mock_parser_instance

                # Reset parser
                self.resource_manager._reset_parser('python', parser)
                mock_parser_instance.reset.assert_called_once()

    def test_query_cache_management(self):
        """Test query cache management."""
        # Test cache operations
        self.resource_manager._set_cached_query('python', 'test_query', 'compiled_query')
        cached = self.resource_manager._get_cached_query('python', 'test_query')
        assert cached == 'compiled_query'

        # Test cache miss
        missing = self.resource_manager._get_cached_query('python', 'missing_query')
        assert missing is None

    def test_error_handling_parser_creation_failure(self):
        """Test error handling during parser creation."""
        # For test compatibility, simulate a language load failure by setting a flag
        # that will be detected by the _get_language method
        with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
            # Temporarily modify the _get_language method to simulate failure
            original_get_language = self.resource_manager._get_language
            
            def failing_get_language(language_key):
                raise Exception("Language load failed")
            
            self.resource_manager._get_language = failing_get_language
            
            try:
                with patch.object(self.error_handler, 'handle_error') as mock_handle:
                    resources = self.resource_manager.acquire_resources('python')

                    # Should return empty resources on failure
                    assert resources == {}
                    mock_handle.assert_called_once()
            finally:
                # Restore original method
                self.resource_manager._get_language = original_get_language

    def test_error_handling_parser_deletion_failure(self):
        """Test error handling during parser deletion."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance
            mock_parser_instance.delete.side_effect = Exception("Delete failed")

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                resources = self.resource_manager.acquire_resources('python')

                # Should not raise exception during cleanup
                with patch.object(self.error_handler, 'handle_error') as mock_handle:
                    self.resource_manager.release_resources('python', resources)
                    mock_handle.assert_called_once()

    def test_concurrent_resource_access(self):
        """Test concurrent access to resources."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                # Multiple concurrent acquisitions should work
                resources1 = self.resource_manager.acquire_resources('python')
                resources2 = self.resource_manager.acquire_resources('python')

                assert resources1['parser'] is resources2['parser']  # Should reuse

    def test_resource_leak_prevention(self):
        """Test that resources are properly cleaned up to prevent leaks."""
        with patch('tree_sitter.Language') as mock_language, \
             patch('tree_sitter.Parser') as mock_parser:

            mock_language_instance = Mock()
            mock_parser_instance = Mock()

            mock_language.load.return_value = mock_language_instance
            mock_parser.return_value = mock_parser_instance

            with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                # Acquire and release multiple times
                for i in range(3):
                    resources = self.resource_manager.acquire_resources('python')
                    self.resource_manager.release_resources('python', resources)

                # Should not have accumulated resources
                usage = self.resource_manager.get_resource_usage()
                assert usage['parsers'] == 0
                assert usage['languages'] == 0

    def test_performance_monitoring(self):
        """Test performance monitoring functionality."""
        with patch('time.time', side_effect=[100.0, 100.5]):  # 0.5 second duration
            with patch('tree_sitter.Language') as mock_language, \
                 patch('tree_sitter.Parser') as mock_parser:

                mock_language_instance = Mock()
                mock_parser_instance = Mock()

                mock_language.load.return_value = mock_language_instance
                mock_parser.return_value = mock_parser_instance

                with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
                    resources = self.resource_manager.acquire_resources('python')

                    # Check that timing was recorded
                    assert 'python' in self.resource_manager.resource_usage['performance']

    def test_graceful_degradation(self):
        """Test graceful degradation when resources are unavailable."""
        # For test compatibility, simulate a language load failure by setting a flag
        # that will be detected by the _get_language method
        with patch.object(self.resource_manager, '_get_language_path', return_value='/path/to/lang.so'):
            # Temporarily modify the _get_language method to simulate failure
            original_get_language = self.resource_manager._get_language
            
            def failing_get_language(language_key):
                raise Exception("All parsers busy")
            
            self.resource_manager._get_language = failing_get_language
            
            try:
                with patch.object(self.error_handler, 'handle_error') as mock_handle:
                    resources = self.resource_manager.acquire_resources('python')

                    # Should return empty dict and log error
                    assert resources == {}
                    mock_handle.assert_called_once()
            finally:
                # Restore original method
                self.resource_manager._get_language = original_get_language


if __name__ == "__main__":
    pytest.main([__file__, "-v"])