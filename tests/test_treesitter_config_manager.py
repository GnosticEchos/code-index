"""
Unit tests for TreeSitterConfigurationManager service.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index import TreeSitterError
from code_index.services.config_manager import TreeSitterConfigurationManager
from code_index.chunking import TreeSitterError
from code_index.errors import ErrorHandler


class TestTreeSitterConfigurationManager:
    """Test suite for TreeSitterConfigurationManager."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"

        self.error_handler = ErrorHandler("test")
        self.config_manager = TreeSitterConfigurationManager(self.config, self.error_handler)

    def test_initialization(self):
        """Test configuration manager initialization."""
        assert self.config_manager.config is self.config
        assert self.config_manager.error_handler is self.error_handler
        assert hasattr(self.config_manager, 'query_cache')
        assert hasattr(self.config_manager, 'language_configs')

    def test_get_query_for_language_python(self):
        """Test query retrieval for Python."""
        query = self.config_manager.get_query_for_language('python')
        assert query is not None
        assert 'function_definition' in query
        assert 'class_definition' in query

    def test_get_query_for_language_javascript(self):
        """Test query retrieval for JavaScript."""
        query = self.config_manager.get_query_for_language('javascript')
        assert query is not None
        assert 'function_declaration' in query or 'function' in query

    def test_get_query_for_language_typescript(self):
        """Test query retrieval for TypeScript."""
        query = self.config_manager.get_query_for_language('typescript')
        assert query is not None
        assert 'interface_declaration' in query or 'type_alias_declaration' in query

    def test_get_query_for_language_unsupported(self):
        """Test query retrieval for unsupported language."""
        query = self.config_manager.get_query_for_language('unsupported_language')
        assert query is None

    def test_get_query_for_language_empty_string(self):
        """Test query retrieval for empty language string."""
        query = self.config_manager.get_query_for_language('')
        assert query is None

    def test_get_query_for_language_none(self):
        """Test query retrieval for None language."""
        query = self.config_manager.get_query_for_language(None)
        assert query is None

    def test_get_language_config_python(self):
        """Test language configuration retrieval for Python."""
        config = self.config_manager.get_language_config('python')
        assert config is not None
        assert 'extensions' in config
        assert '.py' in config['extensions']
        assert 'max_file_size' in config
        assert 'max_blocks' in config

    def test_get_language_config_javascript(self):
        """Test language configuration retrieval for JavaScript."""
        config = self.config_manager.get_language_config('javascript')
        assert config is not None
        assert 'extensions' in config
        assert '.js' in config['extensions']

    def test_get_language_config_unsupported(self):
        """Test language configuration retrieval for unsupported language."""
        config = self.config_manager.get_language_config('unsupported_language')
        assert config is None

    def test_apply_optimizations_python(self):
        """Test optimization application for Python."""
        optimizations = self.config_manager.apply_optimizations('python')
        assert optimizations is not None
        assert 'language' in optimizations
        assert optimizations['language'] == 'python'
        assert 'max_file_size' in optimizations
        assert 'max_blocks' in optimizations

    def test_apply_optimizations_javascript(self):
        """Test optimization application for JavaScript."""
        optimizations = self.config_manager.apply_optimizations('javascript')
        assert optimizations is not None
        assert 'language' in optimizations
        assert optimizations['language'] == 'javascript'

    def test_apply_optimizations_unsupported(self):
        """Test optimization application for unsupported language."""
        optimizations = self.config_manager.apply_optimizations('unsupported_language')
        assert optimizations is None

    def test_validate_configuration_valid(self):
        """Test configuration validation for valid setup."""
        is_valid = self.config_manager.validate_configuration()
        assert is_valid is True

    def test_validate_configuration_invalid_config(self):
        """Test configuration validation for invalid setup."""
        # Break the configuration
        original_config = self.config_manager.config
        self.config_manager.config = None

        try:
            is_valid = self.config_manager.validate_configuration()
            assert is_valid is False
        finally:
            self.config_manager.config = original_config

    def test_get_cached_query_hit(self):
        """Test cached query retrieval on cache hit."""
        language = 'python'
        query_text = 'test_query'

        # Set up cache
        mock_query = Mock()
        self.config_manager._set_cached_query(language, query_text, mock_query)

        # Retrieve from cache
        cached_query = self.config_manager._get_cached_query(language, query_text)
        assert cached_query is mock_query

    def test_get_cached_query_miss(self):
        """Test cached query retrieval on cache miss."""
        cached_query = self.config_manager._get_cached_query('python', 'nonexistent_query')
        assert cached_query is None

    def test_get_cached_query_different_languages(self):
        """Test that cache is isolated by language."""
        # Set up cache for Python
        mock_query_py = Mock()
        self.config_manager._set_cached_query('python', 'test_query', mock_query_py)

        # Try to get for JavaScript
        cached_query_js = self.config_manager._get_cached_query('javascript', 'test_query')
        assert cached_query_js is None

        # Verify Python cache is still intact
        cached_query_py = self.config_manager._get_cached_query('python', 'test_query')
        assert cached_query_py is mock_query_py

    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # Set up cache
        mock_query = Mock()
        self.config_manager._set_cached_query('python', 'test_query', mock_query)

        # Verify it's cached
        assert self.config_manager._get_cached_query('python', 'test_query') is mock_query

        # Invalidate cache
        self.config_manager._invalidate_cache('python')

        # Verify it's gone
        assert self.config_manager._get_cached_query('python', 'test_query') is None

    def test_invalidate_all_caches(self):
        """Test invalidation of all caches."""
        # Set up caches for multiple languages
        mock_query_py = Mock()
        mock_query_js = Mock()

        self.config_manager._set_cached_query('python', 'test_query', mock_query_py)
        self.config_manager._set_cached_query('javascript', 'test_query', mock_query_js)

        # Verify they're cached
        assert self.config_manager._get_cached_query('python', 'test_query') is mock_query_py
        assert self.config_manager._get_cached_query('javascript', 'test_query') is mock_query_js

        # Invalidate all caches
        self.config_manager._invalidate_all_caches()

        # Verify they're all gone
        assert self.config_manager._get_cached_query('python', 'test_query') is None
        assert self.config_manager._get_cached_query('javascript', 'test_query') is None

    def test_query_compilation_success(self):
        """Test successful query compilation."""
        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        compiled_query = self.config_manager._compile_query('python', query_text)
        assert compiled_query is not None
        assert hasattr(compiled_query, 'captures') or hasattr(compiled_query, 'matches')

    def test_query_compilation_failure(self):
        """Test query compilation failure."""
        invalid_query_text = '''
        (invalid_syntax
            missing_closing_paren
        '''

        with patch.object(self.error_handler, 'handle_error') as mock_handle:
            compiled_query = self.config_manager._compile_query('python', invalid_query_text)
            assert compiled_query is None
            mock_handle.assert_called_once()

    def test_query_compilation_with_captures_api(self):
        """Test query compilation using captures API."""
        query_text = '''
        (function_definition
            name: (identifier) @function.name) @function
        '''

        with patch('tree_sitter.Query') as mock_query_class:
            mock_query_instance = Mock()
            mock_query_instance.captures = True
            mock_query_class.return_value = mock_query_instance

            compiled_query = self.config_manager._compile_query('python', query_text)
            assert compiled_query is mock_query_instance
            mock_query_class.assert_called_once()

    def test_query_compilation_with_matches_api(self):
        """Test query compilation using matches API."""
        query_text = '''
        (function_definition
            name: (identifier) @function.name) @function
        '''

        with patch('tree_sitter.Query') as mock_query_class:
            mock_query_instance = Mock()
            mock_query_instance.captures = False
            mock_query_instance.matches = True
            mock_query_class.return_value = mock_query_instance

            compiled_query = self.config_manager._compile_query('python', query_text)
            assert compiled_query is mock_query_instance

    def test_query_compilation_with_cursor_api(self):
        """Test query compilation using cursor API."""
        query_text = '''
        (function_definition
            name: (identifier) @function.name) @function
        '''

        with patch('tree_sitter.Query') as mock_query_class:
            mock_query_instance = Mock()
            mock_query_instance.captures = False
            mock_query_instance.matches = False
            mock_query_class.return_value = mock_query_instance

            with patch('tree_sitter.QueryCursor') as mock_cursor:
                compiled_query = self.config_manager._compile_query('python', query_text)
                assert compiled_query is mock_query_instance

    def test_query_compilation_fallback_behavior(self):
        """Test query compilation fallback behavior."""
        query_text = '''
        (function_definition
            name: (identifier) @function.name) @function
        '''

        # Mock Query to fail on first two attempts, succeed on third
        call_count = 0
        def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("API not available")
            mock_query = Mock()
            mock_query.captures = True
            return mock_query

        with patch('tree_sitter.Query', side_effect=mock_query_side_effect):
            compiled_query = self.config_manager._compile_query('python', query_text)
            assert compiled_query is not None
            assert call_count == 3  # Should try all three APIs

    def test_get_node_types_for_language_python(self):
        """Test node types retrieval for Python."""
        node_types = self.config_manager._get_node_types_for_language('python')
        assert node_types is not None
        assert 'function_definition' in node_types
        assert 'class_definition' in node_types

    def test_get_node_types_for_language_javascript(self):
        """Test node types retrieval for JavaScript."""
        node_types = self.config_manager._get_node_types_for_language('javascript')
        assert node_types is not None
        assert 'function_declaration' in node_types or 'function' in node_types

    def test_get_node_types_for_language_unsupported(self):
        """Test node types retrieval for unsupported language."""
        node_types = self.config_manager._get_node_types_for_language('unsupported_language')
        assert node_types is None

    def test_get_language_from_extension_py(self):
        """Test language detection from .py extension."""
        language = self.config_manager._get_language_from_extension('.py')
        assert language == 'python'

    def test_get_language_from_extension_js(self):
        """Test language detection from .js extension."""
        language = self.config_manager._get_language_from_extension('.js')
        assert language == 'javascript'

    def test_get_language_from_extension_unsupported(self):
        """Test language detection from unsupported extension."""
        language = self.config_manager._get_language_from_extension('.xyz')
        assert language is None

    def test_get_language_from_extension_case_insensitive(self):
        """Test case-insensitive language detection."""
        language = self.config_manager._get_language_from_extension('.PY')
        assert language == 'python'

    def test_get_language_from_extension_no_dot(self):
        """Test language detection from extension without dot."""
        language = self.config_manager._get_language_from_extension('py')
        assert language == 'python'

    def test_error_handling_invalid_language_config(self):
        """Test error handling for invalid language configuration."""
        with patch.object(self.config_manager, '_get_language_config', side_effect=Exception("Config error")):
            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                query = self.config_manager.get_query_for_language('python')
                assert query is None
                mock_handle.assert_called_once()

    def test_error_handling_query_compilation_error(self):
        """Test error handling for query compilation errors."""
        with patch('tree_sitter.Query', side_effect=Exception("Compilation failed")):
            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                query = self.config_manager._compile_query('python', 'invalid_query')
                assert query is None
                mock_handle.assert_called_once()

    def test_performance_with_large_query_cache(self):
        """Test performance with large query cache."""
        # Create many cache entries
        for i in range(100):
            mock_query = Mock()
            self.config_manager._set_cached_query('python', f'query_{i}', mock_query)

        # Verify all are cached
        for i in range(100):
            cached = self.config_manager._get_cached_query('python', f'query_{i}')
            assert cached is not None

        # Clear cache
        self.config_manager._invalidate_cache('python')

        # Verify all are cleared
        for i in range(100):
            cached = self.config_manager._get_cached_query('python', f'query_{i}')
            assert cached is None

    def test_memory_efficiency_with_query_caching(self):
        """Test memory efficiency with query caching."""
        # Create queries for multiple languages
        languages = ['python', 'javascript', 'typescript', 'rust', 'go']
        queries_per_language = 10

        for lang in languages:
            for i in range(queries_per_language):
                mock_query = Mock()
                self.config_manager._set_cached_query(lang, f'query_{i}', mock_query)

        # Verify isolation between languages
        for lang in languages:
            for other_lang in languages:
                if lang != other_lang:
                    # Other language should not have this query
                    cached = self.config_manager._get_cached_query(other_lang, f'query_from_{lang}')
                    assert cached is None

        # Verify all queries are cached for their respective languages
        for lang in languages:
            for i in range(queries_per_language):
                cached = self.config_manager._get_cached_query(lang, f'query_{i}')
                assert cached is not None

    def test_configuration_override_behavior(self):
        """Test configuration override behavior."""
        # Test that configuration changes are reflected
        original_max_blocks = self.config_manager.get_language_config('python')['max_blocks']

        # Modify configuration
        self.config_manager.language_configs['python']['max_blocks'] = 999

        # Verify change is reflected
        updated_config = self.config_manager.get_language_config('python')
        assert updated_config['max_blocks'] == 999

        # Restore original
        self.config_manager.language_configs['python']['max_blocks'] = original_max_blocks

    def test_debug_logging_integration(self):
        """Test debug logging integration."""
        with patch.object(self.error_handler, 'handle_error') as mock_handle:
            # Trigger an error condition
            query = self.config_manager.get_query_for_language('nonexistent_language')

            # Should not raise exception but should log error
            assert query is None
            mock_handle.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])