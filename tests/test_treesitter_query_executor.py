"""
Unit tests for TreeSitterQueryExecutor service.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index import TreeSitterError
from code_index.services.query_executor import TreeSitterQueryExecutor
from code_index.chunking import TreeSitterError
from code_index.errors import ErrorHandler


class TestTreeSitterQueryExecutor:
    """Test suite for TreeSitterQueryExecutor."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"

        self.error_handler = ErrorHandler("test")
        self.query_executor = TreeSitterQueryExecutor(self.config, self.error_handler)

    def test_initialization(self):
        """Test query executor initialization."""
        assert self.query_executor.config is self.config
        assert self.query_executor.error_handler is self.error_handler
        assert hasattr(self.query_executor, 'query_cache')

    def test_execute_with_fallbacks_success_captures(self):
        """Test successful query execution with captures API."""
        python_code = '''
def hello_world():
    print("Hello, World!")
    return True
'''

        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query with captures API
        mock_query = Mock()
        mock_captures = {
            'function': [
                {
                    'function.name': Mock(start_point=(1, 0), end_point=(1, 13)),
                    'function.body': Mock(start_point=(1, 18), end_point=(3, 1))
                }
            ]
        }
        mock_query.captures.return_value = mock_captures

        result = self.query_executor.execute_with_fallbacks(
            python_code, query_text, mock_parser, 'python'
        )

        assert result is not None
        assert 'function' in result
        assert len(result['function']) == 1
        mock_query.captures.assert_called_once()

    def test_execute_with_fallbacks_success_matches(self):
        """Test successful query execution with matches API."""
        python_code = '''
def hello_world():
    print("Hello, World!")
    return True
'''

        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query with matches API (no captures)
        mock_query = Mock()
        mock_query.captures = False
        from unittest.mock import Mock as _MockForMatches
        mock_matches = [
            {
                'pattern': 0,
                'captures': {
                    'function.name': _MockForMatches(start_point=(1, 0), end_point=(1, 13)),
                    'function.body': _MockForMatches(start_point=(1, 18), end_point=(3, 1))
                }
            }
        ]
        # Provide a callable matches() returning the prepared structure
        mock_query.matches = _MockForMatches(return_value=mock_matches)

        result = self.query_executor.execute_with_fallbacks(
            python_code, query_text, mock_parser, 'python'
        )

        assert result is not None
        assert 'function' in result
        assert len(result['function']) == 1
        mock_query.matches.assert_called_once()

    def test_execute_with_fallbacks_success_cursor(self):
        """Test successful query execution with cursor API."""
        python_code = '''
def hello_world():
    print("Hello, World!")
    return True
'''

        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query with cursor API
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = False

        with patch('tree_sitter.QueryCursor') as mock_cursor_class:
            mock_cursor = Mock()
            mock_cursor_class.return_value = mock_cursor

            mock_matches = [
                {
                    'pattern': 0,
                    'captures': {
                        'function.name': Mock(start_point=(1, 0), end_point=(1, 13)),
                        'function.body': Mock(start_point=(1, 18), end_point=(3, 1))
                    }
                }
            ]
            mock_cursor.matches.return_value = mock_matches

            result = self.query_executor.execute_with_fallbacks(
                python_code, query_text, mock_parser, 'python'
            )

            assert result is not None
            assert 'function' in result
            assert len(result['function']) == 1
            # QueryCursor is called multiple times due to fallback patterns
            assert mock_cursor_class.call_count >= 1

    def test_execute_with_fallbacks_fallback_to_matches(self):
        """Test fallback from captures to matches API."""
        python_code = '''
def hello_world():
    print("Hello, World!")
    return True
'''

        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query that fails on captures but succeeds on matches
        mock_query = Mock()
        mock_query.captures.side_effect = Exception("Captures API failed")
        from unittest.mock import Mock as _MockForMatches
        mock_matches = [
            {
                'pattern': 0,
                'captures': {
                    'function.name': _MockForMatches(start_point=(1, 0), end_point=(1, 13)),
                    'function.body': _MockForMatches(start_point=(1, 18), end_point=(3, 1))
                }
            }
        ]
        # Provide a callable matches() returning the prepared structure
        mock_query.matches = _MockForMatches(return_value=mock_matches)

        result = self.query_executor.execute_with_fallbacks(
            python_code, query_text, mock_parser, 'python'
        )

        assert result is not None
        assert 'function' in result
        mock_query.captures.assert_called_once()
        mock_query.matches.assert_called_once()

    def test_execute_with_fallbacks_fallback_to_cursor(self):
        """Test fallback from matches to cursor API."""
        python_code = '''
def hello_world():
    print("Hello, World!")
    return True
'''

        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query that fails on both captures and matches
        mock_query = Mock()
        mock_query.captures.side_effect = Exception("Captures API failed")
        mock_query.matches.side_effect = Exception("Matches API failed")

        with patch('tree_sitter.QueryCursor') as mock_cursor_class:
            mock_cursor = Mock()
            mock_cursor_class.return_value = mock_cursor

            mock_matches = [
                {
                    'pattern': 0,
                    'captures': {
                        'function.name': Mock(start_point=(1, 0), end_point=(1, 13)),
                        'function.body': Mock(start_point=(1, 18), end_point=(3, 1))
                    }
                }
            ]
            mock_cursor.matches.return_value = mock_matches

            result = self.query_executor.execute_with_fallbacks(
                python_code, query_text, mock_parser, 'python'
            )

            assert result is not None
            assert 'function' in result
            # QueryCursor is called multiple times due to fallback patterns
            assert mock_cursor_class.call_count >= 1

    def test_execute_with_fallbacks_all_apis_fail(self):
        """Test behavior when all query APIs fail."""
        python_code = '''
def hello_world():
    print("Hello, World!")
    return True
'''

        query_text = '''
        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query that fails on all APIs
        mock_query = Mock()
        mock_query.captures.side_effect = Exception("Captures API failed")
        mock_query.matches.side_effect = Exception("Matches API failed")

        with patch('tree_sitter.QueryCursor', side_effect=Exception("Cursor API failed")):
            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                result = self.query_executor.execute_with_fallbacks(
                    python_code, query_text, mock_parser, 'python'
                )

                assert result is None
                mock_handle.assert_called_once()

    def test_execute_with_fallbacks_empty_code(self):
        """Test query execution with empty code."""
        result = self.query_executor.execute_with_fallbacks(
            '', 'test_query', Mock(), 'python'
        )
        assert result is None

    def test_execute_with_fallbacks_whitespace_only(self):
        """Test query execution with whitespace-only code."""
        result = self.query_executor.execute_with_fallbacks(
            '   \n\t  \n  ', 'test_query', Mock(), 'python'
        )
        assert result is None

    def test_normalize_capture_results_valid(self):
        """Test normalization of valid capture results."""
        mock_captures = {
            'function': [
                {
                    'function.name': Mock(start_point=(1, 0), end_point=(1, 13)),
                    'function.body': Mock(start_point=(1, 18), end_point=(3, 1))
                }
            ],
            'class': [
                {
                    'class.name': Mock(start_point=(5, 0), end_point=(5, 8)),
                    'class.body': Mock(start_point=(5, 13), end_point=(7, 1))
                }
            ]
        }

        normalized = self.query_executor._normalize_capture_results(mock_captures)

        assert len(normalized) == 2
        assert normalized[0]['type'] == 'function'
        assert normalized[1]['type'] == 'class'

    def test_normalize_capture_results_empty(self):
        """Test normalization of empty capture results."""
        normalized = self.query_executor._normalize_capture_results({})
        assert len(normalized) == 0

    def test_normalize_capture_results_none(self):
        """Test normalization of None capture results."""
        normalized = self.query_executor._normalize_capture_results(None)
        assert len(normalized) == 0

    def test_normalize_capture_results_malformed(self):
        """Test normalization of malformed capture results."""
        # Missing required keys
        malformed_captures = {
            'function': [
                {
                    'function.name': Mock(start_point=(1, 0), end_point=(1, 13))
                    # Missing function.body
                }
            ]
        }

        normalized = self.query_executor._normalize_capture_results(malformed_captures)
        assert len(normalized) == 0  # Should filter out malformed entries

    def test_validate_query_api_captures(self):
        """Test query API validation for captures method."""
        mock_query = Mock()
        mock_query.captures = True

        assert self.query_executor._validate_query_api(mock_query) is True

    def test_validate_query_api_matches(self):
        """Test query API validation for matches method."""
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = True

        assert self.query_executor._validate_query_api(mock_query) is True

    def test_validate_query_api_cursor(self):
        """Test query API validation for cursor method."""
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = False

        with patch('tree_sitter.QueryCursor') as mock_cursor:
            assert self.query_executor._validate_query_api(mock_query) is True

    def test_validate_query_api_invalid(self):
        """Test query API validation for invalid query."""
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = False

        with patch('tree_sitter.QueryCursor', side_effect=ImportError):
            assert self.query_executor._validate_query_api(mock_query) is False

    def test_query_caching(self):
        """Test query result caching."""
        python_code = 'def test(): pass'
        query_text = 'test_query'

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query
        mock_query = Mock()
        mock_captures = {'function': []}
        mock_query.captures.return_value = mock_captures

        with patch.object(self.query_executor, '_compile_query', return_value=mock_query):
            # First execution
            result1 = self.query_executor.execute_with_fallbacks(
                python_code, query_text, mock_parser, 'python'
            )

            # Second execution (should use cache)
            result2 = self.query_executor.execute_with_fallbacks(
                python_code, query_text, mock_parser, 'python'
            )

            assert result1 is result2  # Should return same cached result

    def test_query_cache_invalidation(self):
        """Test query cache invalidation."""
        # Set cache entry
        self.query_executor._set_cached_result('python', 'query1', {'result': 'cached'})

        # Invalidate cache
        self.query_executor._invalidate_cache('python')

        # Check that cache is cleared
        assert self.query_executor._get_cached_result('python', 'query1') is None

    def test_query_cache_different_languages(self):
        """Test that cache is isolated by language."""
        python_code = 'def test(): pass'
        js_code = 'function test() {}'

        # Mock parsers and trees
        mock_parser_py = Mock()
        mock_tree_py = Mock()
        mock_parser_py.parse.return_value = mock_tree_py
        mock_tree_py.root_node = Mock()

        mock_parser_js = Mock()
        mock_tree_js = Mock()
        mock_parser_js.parse.return_value = mock_tree_js
        mock_tree_js.root_node = Mock()

        # Mock queries
        mock_query_py = Mock()
        mock_query_py.captures.return_value = {'function': []}

        mock_query_js = Mock()
        mock_query_js.captures.return_value = {'function': []}

        with patch.object(self.query_executor, '_compile_query') as mock_compile:
            mock_compile.side_effect = [mock_query_py, mock_query_js]

            # Execute for Python
            result_py = self.query_executor.execute_with_fallbacks(
                python_code, 'test_query', mock_parser_py, 'python'
            )

            # Execute for JavaScript
            result_js = self.query_executor.execute_with_fallbacks(
                js_code, 'test_query', mock_parser_js, 'javascript'
            )

            # Should have different results (different languages)
            assert result_py is not result_js
            assert mock_compile.call_count == 2  # Should compile separately

    def test_error_handling_syntax_error_in_query(self):
        """Test error handling for syntax errors in queries."""
        python_code = 'def test(): pass'

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        with patch.object(self.query_executor, '_compile_query', side_effect=Exception("Syntax error in query")):
            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                result = self.query_executor.execute_with_fallbacks(
                    python_code, 'invalid_query', mock_parser, 'python'
                )

                assert result is None
                mock_handle.assert_called_once()

    def test_performance_with_complex_query(self):
        """Test performance with complex query patterns."""
        # Create a complex Python file
        complex_code = '''
class ComplexClass:
    def __init__(self):
        self.value = 42

    def method1(self):
        return self.value

    def method2(self):
        return self.value * 2

    def method3(self):
        return self.value * 3

def standalone_function():
    return "standalone"

class AnotherClass:
    def another_method(self):
        return "another"
'''

        complex_query = '''
        (class_definition
            name: (identifier) @class.name
            body: (block
                (function_definition
                    name: (identifier) @method.name
                    body: (block) @method.body) @method)*) @class

        (function_definition
            name: (identifier) @function.name
            body: (block) @function.body) @function
        '''

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query
        mock_query = Mock()
        mock_captures = {
            'class': [
                {
                    'class.name': Mock(start_point=(1, 0), end_point=(1, 13)),
                    'method.name': Mock(start_point=(4, 4), end_point=(4, 11)),
                    'method.body': Mock(start_point=(4, 16), end_point=(5, 5))
                },
                {
                    'class.name': Mock(start_point=(15, 0), end_point=(15, 12)),
                    'method.name': Mock(start_point=(16, 4), end_point=(16, 18)),
                    'method.body': Mock(start_point=(16, 23), end_point=(17, 5))
                }
            ],
            'function': [
                {
                    'function.name': Mock(start_point=(12, 0), end_point=(12, 19)),
                    'function.body': Mock(start_point=(12, 24), end_point=(13, 1))
                }
            ]
        }
        mock_query.captures.return_value = mock_captures

        with patch.object(self.query_executor, '_compile_query', return_value=mock_query):
            result = self.query_executor.execute_with_fallbacks(
                complex_code, complex_query, mock_parser, 'python'
            )

            assert result is not None
            assert 'class' in result
            assert 'function' in result
            assert len(result['class']) == 2
            assert len(result['function']) == 1

    def test_memory_efficiency_with_large_results(self):
        """Test memory efficiency with large query results."""
        # Create code with many small functions
        large_code = '\n'.join([f'def func_{i}(): return {i}' for i in range(100)])

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = Mock()

        # Mock query with many results
        mock_query = Mock()
        mock_captures = {
            'function': [
                {
                    'function.name': Mock(start_point=(i*2, 0), end_point=(i*2, 8)),
                    'function.body': Mock(start_point=(i*2, 13), end_point=(i*2+1, 1))
                }
                for i in range(100)
            ]
        }
        mock_query.captures.return_value = mock_captures

        with patch.object(self.query_executor, '_compile_query', return_value=mock_query):
            result = self.query_executor.execute_with_fallbacks(
                large_code, 'test_query', mock_parser, 'python'
            )

            assert result is not None
            assert len(result['function']) == 100

    def test_graceful_degradation_on_parser_failure(self):
        """Test graceful degradation when parser fails."""
        python_code = 'def test(): pass'

        # Mock parser that fails
        mock_parser = Mock()
        mock_parser.parse.side_effect = Exception("Parser failed")

        with patch.object(self.error_handler, 'handle_error') as mock_handle:
            result = self.query_executor.execute_with_fallbacks(
                python_code, 'test_query', mock_parser, 'python'
            )

            assert result is None
            mock_handle.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])