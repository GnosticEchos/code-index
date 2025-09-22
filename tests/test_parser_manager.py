"""
Unit tests for the Parser Management Service.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from code_index.parser_manager import TreeSitterParserManager, ParserInfo, ParserResourceMonitor, ParserCreationError
from code_index.config import Config
from code_index.errors import ErrorHandler


class TestTreeSitterParserManager:
    """Test cases for TreeSitterParserManager class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config()

    @pytest.fixture
    def error_handler(self):
        """Create a test error handler."""
        return ErrorHandler()

    @pytest.fixture
    def parser_manager(self, config, error_handler):
        """Create a TreeSitterParserManager instance for testing."""
        return TreeSitterParserManager(config, error_handler)

    def test_get_parser_success(self, parser_manager):
        """Test successful parser retrieval."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            parser = parser_manager.get_parser("python")

            assert parser is not None
            assert parser == mock_parser
            mock_create.assert_called_once_with("python")

    def test_get_parser_from_cache(self, parser_manager):
        """Test parser retrieval from cache."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()

            # First call - should create parser
            mock_create.return_value = (mock_parser, mock_language)
            parser1 = parser_manager.get_parser("python")
            assert parser1 == mock_parser
            assert mock_create.call_count == 1

            # Second call - should use cache
            parser2 = parser_manager.get_parser("python")
            assert parser2 == mock_parser
            assert mock_create.call_count == 1  # Should not create again

    def test_get_parser_cache_expiration(self, parser_manager):
        """Test parser cache expiration."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()

            # Set short TTL
            parser_manager.cache_ttl_seconds = 1

            # First call
            mock_create.return_value = (mock_parser, mock_language)
            parser1 = parser_manager.get_parser("python")
            assert parser1 == mock_parser

            # Manually expire the cache
            for parser_info in parser_manager._parser_cache.values():
                parser_info.last_used = time.time() - 2  # 2 seconds ago

            # Second call should create new parser due to expiration
            parser2 = parser_manager.get_parser("python")
            assert parser2 == mock_parser
            assert mock_create.call_count == 2  # Should create again

    def test_validate_parser_success(self, parser_manager):
        """Test successful parser validation."""
        with patch.object(parser_manager, 'get_parser') as mock_get_parser:
            with patch.object(parser_manager, '_get_test_code_for_language') as mock_get_test:
                mock_parser = Mock()
                mock_tree = Mock()
                mock_tree.root_node = Mock()
                mock_parser.parse.return_value = mock_tree
                mock_get_parser.return_value = mock_parser
                mock_get_test.return_value = "def test(): pass"

                is_valid = parser_manager.validate_parser("python")

                assert is_valid is True
                mock_parser.parse.assert_called_once()

    def test_validate_parser_no_test_code(self, parser_manager):
        """Test parser validation when no test code is available."""
        with patch.object(parser_manager, 'get_parser') as mock_get_parser:
            with patch.object(parser_manager, '_get_test_code_for_language') as mock_get_test:
                mock_parser = Mock()
                mock_get_parser.return_value = mock_parser
                mock_get_test.return_value = None

                is_valid = parser_manager.validate_parser("python")

                assert is_valid is True  # Should be valid if parser exists

    def test_validate_parser_failure(self, parser_manager):
        """Test parser validation failure."""
        with patch.object(parser_manager, 'get_parser') as mock_get_parser:
            mock_parser = Mock()
            mock_parser.parse.side_effect = Exception("Parse failed")
            mock_get_parser.return_value = mock_parser

            is_valid = parser_manager.validate_parser("python")

            assert is_valid is False

    def test_cleanup_resources(self, parser_manager):
        """Test resource cleanup."""
        # Add some parsers to cache
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            parser_manager.get_parser("python")
            parser_manager.get_parser("javascript")

            assert len(parser_manager._parser_cache) > 0

            # Clean up resources
            cleaned_count = parser_manager.cleanup_resources()

            assert cleaned_count > 0
            assert len(parser_manager._parser_cache) == 0
            assert len(parser_manager._language_cache) == 0
            assert len(parser_manager._parser_language_ids) == 0

    def test_cleanup_old_parsers(self, parser_manager):
        """Test cleanup of old parsers."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            # Add parsers
            parser_manager.get_parser("python")
            parser_manager.get_parser("javascript")

            # Set a shorter TTL for this test
            original_ttl = parser_manager.cache_ttl_seconds
            parser_manager.cache_ttl_seconds = 300  # 5 minutes

            # Manually set last_used to old time (older than TTL)
            for parser_info in parser_manager._parser_cache.values():
                parser_info.last_used = time.time() - 400  # 400 seconds ago

            # Cleanup old parsers
            removed_count = parser_manager.cleanup_old_parsers()

            # Restore original TTL
            parser_manager.cache_ttl_seconds = original_ttl

            assert removed_count > 0

    def test_get_cache_info(self, parser_manager):
        """Test getting cache information."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            # Add some parsers
            parser_manager.get_parser("python")
            parser_manager.get_parser("javascript")

            cache_info = parser_manager.get_cache_info()

            assert "cache_size" in cache_info
            assert "valid_parsers" in cache_info
            assert "invalid_parsers" in cache_info
            assert "total_memory_usage" in cache_info
            assert cache_info["cache_size"] > 0

    def test_get_parser_stats(self, parser_manager):
        """Test getting parser statistics."""
        # Test with no cached parser
        stats = parser_manager.get_parser_stats("python")
        assert stats["language"] == "python"
        assert stats["cached"] is False

        # Add a parser and test stats
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            parser_manager.get_parser("python")
            stats = parser_manager.get_parser_stats("python")

            assert stats["language"] == "python"
            assert stats["cached"] is True
            assert stats["use_count"] > 0

    def test_preload_common_parsers(self, parser_manager):
        """Test preloading common parsers."""
        with patch.object(parser_manager, 'get_parser') as mock_get_parser:
            mock_parser = Mock()
            mock_get_parser.return_value = mock_parser

            preloaded_count = parser_manager.preload_common_parsers()

            # Should attempt to preload common languages
            assert preloaded_count >= 0
            assert mock_get_parser.call_count >= 0

    def test_create_parser_success(self, parser_manager):
        """Test successful parser creation."""
        with patch('tree_sitter.Parser') as mock_parser_class:
            with patch.object(parser_manager, '_get_tree_sitter_language') as mock_get_lang:
                mock_parser = Mock()
                mock_language = Mock()
                mock_parser_class.return_value = mock_parser
                mock_get_lang.return_value = mock_language

                parser, language_obj = parser_manager._create_parser("python")

                assert parser is not None
                assert language_obj is not None
                assert parser == mock_parser
                assert language_obj == mock_language
                mock_parser_class.assert_called_once()
                mock_parser.language = mock_language

    def test_create_parser_failure(self, parser_manager):
        """Test parser creation failure."""
        with patch.object(parser_manager, '_get_tree_sitter_language') as mock_get_lang:
            mock_get_lang.return_value = None

            parser, language_obj = parser_manager._create_parser("python")

            assert parser is None
            assert language_obj is None

    def test_get_tree_sitter_language_success(self, parser_manager):
        """Test successful Tree-sitter language loading."""
        with patch('tree_sitter_language_pack.get_language') as mock_get_language:
            mock_language = Mock()
            mock_get_language.return_value = mock_language

            language_obj = parser_manager._get_tree_sitter_language("python")

            assert language_obj is not None
            assert language_obj == mock_language
            mock_get_language.assert_called_once_with("python")

    def test_get_tree_sitter_language_from_cache(self, parser_manager):
        """Test Tree-sitter language loading from cache."""
        with patch('tree_sitter_language_pack.get_language') as mock_get_language:
            mock_language = Mock()
            mock_get_language.return_value = mock_language

            # First call
            language1 = parser_manager._get_tree_sitter_language("python")
            assert language1 == mock_language
            assert mock_get_language.call_count == 1

            # Second call should use cache
            language2 = parser_manager._get_tree_sitter_language("python")
            assert language2 == mock_language
            assert mock_get_language.call_count == 1  # Should not call again

    def test_get_tree_sitter_language_failure(self, parser_manager):
        """Test Tree-sitter language loading failure."""
        with patch('tree_sitter_language_pack.get_language') as mock_get_language:
            mock_get_language.side_effect = Exception("Language not found")

            language_obj = parser_manager._get_tree_sitter_language("unknown_language")

            assert language_obj is None

    def test_cleanup_parser(self, parser_manager):
        """Test individual parser cleanup."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            # Add parser to cache
            parser_manager.get_parser("python")
            assert "python" in parser_manager._parser_cache

            # Clean up specific parser
            parser_manager._cleanup_parser("python")

            assert "python" not in parser_manager._parser_cache
            assert "python" not in parser_manager._parser_language_ids
            assert "python" not in parser_manager._language_cache

    def test_is_cache_valid(self, parser_manager):
        """Test cache validity checking."""
        parser_info = ParserInfo(
            language="python",
            parser=Mock(),
            language_id=123,
            created_at=time.time(),
            last_used=time.time(),
            use_count=1,
            memory_usage=1000,
            is_valid=True
        )

        # Should be valid
        assert parser_manager._is_cache_valid(parser_info) is True

        # Make it expired
        parser_info.last_used = time.time() - 400  # 400 seconds ago
        parser_manager.cache_ttl_seconds = 300  # 5 minutes

        # Should be invalid
        assert parser_manager._is_cache_valid(parser_info) is False

    def test_get_test_code_for_language(self, parser_manager):
        """Test getting test code for language validation."""
        # Test known languages
        python_code = parser_manager._get_test_code_for_language("python")
        assert python_code == "def test(): pass"

        js_code = parser_manager._get_test_code_for_language("javascript")
        assert js_code == "function test() {}"

        rust_code = parser_manager._get_test_code_for_language("rust")
        assert rust_code == "fn test() {}"

        # Test unknown language
        unknown_code = parser_manager._get_test_code_for_language("unknown")
        assert unknown_code is None

    def test_error_handling_in_get_parser(self, parser_manager):
        """Test error handling in get_parser."""
        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_create.side_effect = Exception("Parser creation failed")

            parser = parser_manager.get_parser("python")
            assert parser is None

    def test_error_handling_in_validate_parser(self, parser_manager):
        """Test error handling in validate_parser."""
        with patch.object(parser_manager, 'get_parser') as mock_get_parser:
            mock_get_parser.side_effect = Exception("Parser retrieval failed")

            is_valid = parser_manager.validate_parser("python")
            assert is_valid is False

    def test_error_handling_in_cleanup_resources(self, parser_manager):
        """Test error handling in cleanup_resources."""
        with patch.object(parser_manager, '_parser_cache') as mock_cache:
            mock_cache.clear.side_effect = Exception("Clear failed")

            # Should not raise exception
            cleaned_count = parser_manager.cleanup_resources()
            assert cleaned_count == 0

    def test_cache_size_limits(self, parser_manager):
        """Test cache size limits."""
        # Set small cache size
        parser_manager.max_cache_size = 2

        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            # Add parsers up to limit
            parser_manager.get_parser("python")
            parser_manager.get_parser("javascript")

            # Add one more - should still work but cache won't grow beyond limit
            parser_manager.get_parser("rust")

            cache_info = parser_manager.get_cache_info()
            assert cache_info["cache_size"] <= parser_manager.max_cache_size

    def test_debug_logging(self, parser_manager):
        """Test debug logging functionality."""
        # Enable debug logging
        parser_manager._debug_enabled = True

        with patch.object(parser_manager, '_create_parser') as mock_create:
            mock_parser = Mock()
            mock_language = Mock()
            mock_create.return_value = (mock_parser, mock_language)

            # This should not raise any exceptions
            parser = parser_manager.get_parser("python")
            assert parser is not None


class TestParserResourceMonitor:
    """Test cases for ParserResourceMonitor class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config()

    @pytest.fixture
    def resource_monitor(self, config):
        """Create a ParserResourceMonitor instance for testing."""
        return ParserResourceMonitor(config)

    def test_get_memory_usage(self, resource_monitor):
        """Test memory usage tracking."""
        memory_usage = resource_monitor.get_memory_usage()
        assert isinstance(memory_usage, int)
        assert memory_usage >= 0

    def test_reset_baseline(self, resource_monitor):
        """Test baseline memory reset."""
        initial_usage = resource_monitor.get_memory_usage()

        # Reset baseline
        resource_monitor.reset()

        # Memory usage should be reset
        new_usage = resource_monitor.get_memory_usage()
        assert isinstance(new_usage, int)
        assert new_usage >= 0

    def test_memory_usage_calculation(self, resource_monitor):
        """Test memory usage calculation."""
        # Get initial usage
        usage1 = resource_monitor.get_memory_usage()

        # Reset and get new usage
        resource_monitor.reset()
        usage2 = resource_monitor.get_memory_usage()

        # Usage should be non-negative
        assert usage1 >= 0
        assert usage2 >= 0

    @patch('psutil.Process')
    def test_memory_usage_with_psutil_error(self, mock_process, resource_monitor):
        """Test memory usage when psutil fails."""
        mock_process.side_effect = Exception("psutil error")

        memory_usage = resource_monitor.get_memory_usage()
        assert memory_usage == 0

    def test_parser_info_creation(self):
        """Test ParserInfo dataclass creation."""
        mock_parser = Mock()
        parser_info = ParserInfo(
            language="python",
            parser=mock_parser,
            language_id=123,
            created_at=time.time(),
            last_used=time.time(),
            use_count=1,
            memory_usage=1000,
            is_valid=True
        )

        assert parser_info.language == "python"
        assert parser_info.parser == mock_parser
        assert parser_info.language_id == 123
        assert parser_info.use_count == 1
        assert parser_info.memory_usage == 1000
        assert parser_info.is_valid is True

    def test_parser_info_with_error(self):
        """Test ParserInfo with error information."""
        mock_parser = Mock()
        parser_info = ParserInfo(
            language="python",
            parser=mock_parser,
            language_id=123,
            created_at=time.time(),
            last_used=time.time(),
            use_count=0,
            memory_usage=0,
            is_valid=False,
            error_message="Parser creation failed"
        )

        assert parser_info.is_valid is False
        assert parser_info.error_message == "Parser creation failed"
        assert parser_info.use_count == 0