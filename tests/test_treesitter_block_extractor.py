"""
Unit tests for TreeSitterBlockExtractor service.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index import TreeSitterError
from code_index.services.block_extractor import TreeSitterBlockExtractor
from code_index.chunking import TreeSitterError
from code_index.errors import ErrorHandler


class TestTreeSitterBlockExtractor:
    """Test suite for TreeSitterBlockExtractor."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"

        self.error_handler = ErrorHandler("test")
        self.block_extractor = TreeSitterBlockExtractor(self.config, self.error_handler)

    def test_initialization(self):
        """Test block extractor initialization."""
        assert self.block_extractor.config is self.config
        assert self.block_extractor.error_handler is self.error_handler
        assert hasattr(self.block_extractor, 'query_manager')
        assert hasattr(self.block_extractor, 'parser_manager')

    def test_extract_blocks_python_function(self):
        """Test block extraction for Python function."""
        python_code = '''
def hello_world():
    """A simple function."""
    print("Hello, World!")
    return True

class TestClass:
    def method(self):
        return "test"
'''

        # Mock the dependencies
        with patch.object(self.block_extractor, 'query_manager') as mock_query_manager, \
             patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:

            # Mock query manager
            mock_query_manager.get_query_for_language.return_value = '''
            (function_definition
                name: (identifier) @function.name
                body: (block) @function.body) @function

            (class_definition
                name: (identifier) @class.name
                body: (block) @class.body) @class
            '''

            # Mock parser manager
            mock_parser = Mock()
            mock_tree = Mock()
            mock_parser_manager.acquire_resources.return_value = {
                'parser': mock_parser,
                'language': Mock()
            }

            # Mock query execution
            mock_query = Mock()
            mock_captures = {
                'function': [
                    {
                        'function.name': Mock(start_point=(1, 0), end_point=(4, 1)),
                        'function.body': Mock(start_point=(3, 4), end_point=(4, 1))
                    }
                ],
                'class': [
                    {
                        'class.name': Mock(start_point=(6, 0), end_point=(8, 1)),
                        'class.body': Mock(start_point=(7, 4), end_point=(8, 1))
                    }
                ]
            }
            mock_query.captures.return_value = mock_captures
            mock_query_manager.get_cached_query.return_value = mock_query

            # Mock tree parsing
            mock_parser.parse.return_value = mock_tree
            mock_tree.root_node = Mock()

            blocks = self.block_extractor.extract_blocks(python_code, 'test.py', 'hash123')

            assert len(blocks) == 2
            assert blocks[0].type == 'function'
            assert blocks[0].identifier == 'hello_world'
            assert blocks[1].type == 'class'
            assert blocks[1].identifier == 'TestClass'

    def test_extract_blocks_javascript_function(self):
        """Test block extraction for JavaScript function."""
        js_code = '''
function calculateSum(a, b) {
    return a + b;
}

const arrowFunction = (x) => {
    return x * 2;
};
'''

        with patch.object(self.block_extractor, 'query_manager') as mock_query_manager, \
             patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:

            # Mock query manager
            mock_query_manager.get_query_for_language.return_value = '''
            (function_declaration
                name: (identifier) @function.name
                body: (statement_block) @function.body) @function

            (arrow_function
                parameters: (formal_parameters) @function.params
                body: (statement_block) @function.body) @function
            '''

            # Mock parser manager
            mock_parser = Mock()
            mock_tree = Mock()
            mock_parser_manager.acquire_resources.return_value = {
                'parser': mock_parser,
                'language': Mock()
            }

            # Mock query execution
            mock_query = Mock()
            mock_captures = {
                'function': [
                    {
                        'function.name': Mock(start_point=(1, 0), end_point=(3, 1)),
                        'function.body': Mock(start_point=(1, 28), end_point=(3, 1))
                    },
                    {
                        'function.params': Mock(start_point=(4, 21), end_point=(4, 26)),
                        'function.body': Mock(start_point=(4, 31), end_point=(6, 1))
                    }
                ]
            }
            mock_query.captures.return_value = mock_captures
            mock_query_manager.get_cached_query.return_value = mock_query

            # Mock tree parsing
            mock_parser.parse.return_value = mock_tree
            mock_tree.root_node = Mock()

            blocks = self.block_extractor.extract_blocks(js_code, 'test.js', 'hash456')

            assert len(blocks) == 2
            assert blocks[0].type == 'function'
            assert 'calculateSum' in blocks[0].identifier
            assert blocks[1].type == 'function'
            assert 'arrowFunction' in blocks[1].identifier

    def test_extract_blocks_with_query_fallback(self):
        """Test block extraction with query fallback."""
        python_code = '''
def simple_function():
    return "simple"
'''

        with patch.object(self.block_extractor, 'query_manager') as mock_query_manager, \
             patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:

            # Mock query manager - first return None, then return valid query
            mock_query_manager.get_query_for_language.side_effect = [None, 'fallback_query']

            # Mock parser manager
            mock_parser = Mock()
            mock_tree = Mock()
            mock_parser_manager.acquire_resources.return_value = {
                'parser': mock_parser,
                'language': Mock()
            }

            # Mock query execution
            mock_query = Mock()
            mock_captures = {
                'function': [
                    {
                        'function.name': Mock(start_point=(1, 0), end_point=(2, 1)),
                        'function.body': Mock(start_point=(1, 22), end_point=(2, 1))
                    }
                ]
            }
            mock_query.captures.return_value = mock_captures
            mock_query_manager.get_cached_query.return_value = mock_query

            # Mock tree parsing
            mock_parser.parse.return_value = mock_tree
            mock_tree.root_node = Mock()

            blocks = self.block_extractor.extract_blocks(python_code, 'test.py', 'hash789')

            assert len(blocks) == 1
            assert blocks[0].type == 'function'
            # Should have called get_query_for_language twice (original + fallback)
            assert mock_query_manager.get_query_for_language.call_count == 2

    def test_extract_blocks_empty_code(self):
        """Test block extraction with empty code."""
        blocks = self.block_extractor.extract_blocks('', 'empty.py', 'hash_empty')
        assert len(blocks) == 0

    def test_extract_blocks_whitespace_only(self):
        """Test block extraction with whitespace-only code."""
        blocks = self.block_extractor.extract_blocks('   \n\t  \n  ', 'whitespace.py', 'hash_ws')
        assert len(blocks) == 0

    def test_extract_blocks_no_parser_resources(self):
        """Test block extraction when parser resources are not available."""
        with patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:
            mock_parser_manager.acquire_resources.return_value = {}

            blocks = self.block_extractor.extract_blocks('def test(): pass', 'test.py', 'hash_no_parser')
            assert len(blocks) == 0

    def test_extract_blocks_query_execution_error(self):
        """Test block extraction with query execution error."""
        python_code = 'def test(): pass'

        with patch.object(self.block_extractor, 'query_manager') as mock_query_manager, \
             patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:

            # Mock parser manager
            mock_parser = Mock()
            mock_tree = Mock()
            mock_parser_manager.acquire_resources.return_value = {
                'parser': mock_parser,
                'language': Mock()
            }

            # Mock query execution error
            mock_query_manager.get_cached_query.side_effect = Exception("Query execution failed")

            # Mock tree parsing
            mock_parser.parse.return_value = mock_tree
            mock_tree.root_node = Mock()

            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                blocks = self.block_extractor.extract_blocks(python_code, 'test.py', 'hash_error')

                assert len(blocks) == 0
                mock_handle.assert_called_once()

    def test_create_block_from_node_function(self):
        """Test block creation from function node."""
        python_code = '''
def hello_world():
    """A simple function."""
    print("Hello, World!")
    return True
'''

        # Mock node with position information
        mock_node = Mock()
        mock_node.start_point = (1, 0)
        mock_node.end_point = (4, 1)
        mock_node.start_byte = 20
        mock_node.end_byte = 85

        block = self.block_extractor._create_block_from_node(
            mock_node, python_code, 'function', 'hello_world', 'test.py'
        )

        assert block.type == 'function'
        assert block.identifier == 'hello_world'
        assert block.file_path == 'test.py'
        assert block.start_line == 2  # 1-indexed
        assert block.end_line == 5    # 1-indexed
        assert 'def hello_world():' in block.content
        assert 'print("Hello, World!")' in block.content

    def test_create_block_from_node_class(self):
        """Test block creation from class node."""
        python_code = '''
class MyClass:
    def __init__(self):
        self.value = 42
'''

        mock_node = Mock()
        mock_node.start_point = (1, 0)
        mock_node.end_point = (3, 1)
        mock_node.start_byte = 20
        mock_node.end_byte = 65

        block = self.block_extractor._create_block_from_node(
            mock_node, python_code, 'class', 'MyClass', 'test.py'
        )

        assert block.type == 'class'
        assert block.identifier == 'MyClass'
        assert 'class MyClass:' in block.content
        assert 'def __init__(self):' in block.content

    def test_create_block_from_node_invalid_positions(self):
        """Test block creation with invalid node positions."""
        python_code = 'def test(): pass'

        mock_node = Mock()
        mock_node.start_point = (-1, -1)  # Invalid positions
        mock_node.end_point = (-1, -1)
        mock_node.start_byte = -1
        mock_node.end_byte = -1

        block = self.block_extractor._create_block_from_node(
            mock_node, python_code, 'function', 'test', 'test.py'
        )

        assert block.type == 'function'
        assert block.identifier == 'test'
        assert block.content == python_code  # Should use full content as fallback

    def test_normalize_capture_results(self):
        """Test normalization of capture results."""
        # Mock capture results
        mock_captures = {
            'function': [
                {
                    'function.name': Mock(start_point=(1, 0), end_point=(1, 10)),
                    'function.body': Mock(start_point=(1, 15), end_point=(3, 1))
                }
            ],
            'class': [
                {
                    'class.name': Mock(start_point=(5, 0), end_point=(5, 8)),
                    'class.body': Mock(start_point=(5, 13), end_point=(7, 1))
                }
            ]
        }

        normalized = self.block_extractor._normalize_capture_results(mock_captures)

        assert len(normalized) == 2
        assert normalized[0]['type'] == 'function'
        assert normalized[1]['type'] == 'class'

    def test_normalize_capture_results_empty(self):
        """Test normalization of empty capture results."""
        normalized = self.block_extractor._normalize_capture_results({})
        assert len(normalized) == 0

    def test_normalize_capture_results_none(self):
        """Test normalization of None capture results."""
        normalized = self.block_extractor._normalize_capture_results(None)
        assert len(normalized) == 0

    def test_validate_query_api_captures(self):
        """Test query API validation for captures method."""
        mock_query = Mock()
        mock_query.captures = True

        assert self.block_extractor._validate_query_api(mock_query) is True

    def test_validate_query_api_matches(self):
        """Test query API validation for matches method."""
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = True

        assert self.block_extractor._validate_query_api(mock_query) is True

    def test_validate_query_api_cursor(self):
        """Test query API validation for cursor method."""
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = False

        with patch('tree_sitter.QueryCursor') as mock_cursor:
            assert self.block_extractor._validate_query_api(mock_query) is True

    def test_validate_query_api_invalid(self):
        """Test query API validation for invalid query."""
        mock_query = Mock()
        mock_query.captures = False
        mock_query.matches = False

        with patch('tree_sitter.QueryCursor', side_effect=ImportError):
            assert self.block_extractor._validate_query_api(mock_query) is False

    def test_deduplication_logic(self):
        """Test block deduplication logic."""
        # Create duplicate blocks
        blocks = [
            Mock(type='function', identifier='test', start_line=1, end_line=5),
            Mock(type='function', identifier='test', start_line=1, end_line=5),  # Duplicate
            Mock(type='class', identifier='TestClass', start_line=10, end_line=15),
            Mock(type='function', identifier='test', start_line=1, end_line=5),  # Another duplicate
        ]

        deduplicated = self.block_extractor._deduplicate_blocks(blocks)

        # Should have only 2 unique blocks
        assert len(deduplicated) == 2
        assert deduplicated[0].type == 'function'
        assert deduplicated[1].type == 'class'

    def test_deduplication_empty_list(self):
        """Test deduplication of empty list."""
        deduplicated = self.block_extractor._deduplicate_blocks([])
        assert len(deduplicated) == 0

    def test_deduplication_no_duplicates(self):
        """Test deduplication when there are no duplicates."""
        blocks = [
            Mock(type='function', identifier='func1', start_line=1, end_line=5),
            Mock(type='function', identifier='func2', start_line=6, end_line=10),
            Mock(type='class', identifier='TestClass', start_line=15, end_line=20),
        ]

        deduplicated = self.block_extractor._deduplicate_blocks(blocks)
        assert len(deduplicated) == 3  # No change

    def test_error_handling_malformed_code(self):
        """Test error handling for malformed code."""
        malformed_code = '''
def broken_function(
    print("This is malformed"
'''

        with patch.object(self.block_extractor, 'query_manager') as mock_query_manager, \
             patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:

            # Mock parser manager
            mock_parser = Mock()
            mock_tree = Mock()
            mock_parser_manager.acquire_resources.return_value = {
                'parser': mock_parser,
                'language': Mock()
            }

            # Mock query execution
            mock_query = Mock()
            mock_query.captures.side_effect = Exception("Syntax error in code")
            mock_query_manager.get_cached_query.return_value = mock_query

            # Mock tree parsing
            mock_parser.parse.return_value = mock_tree
            mock_tree.root_node = Mock()

            with patch.object(self.error_handler, 'handle_error') as mock_handle:
                blocks = self.block_extractor.extract_blocks(malformed_code, 'malformed.py', 'hash_malformed')

                assert len(blocks) == 0
                mock_handle.assert_called_once()

    def test_performance_with_large_codebase(self):
        """Test performance with large codebase."""
        # Create a large Python file
        large_code = '\n'.join([f'def function_{i}():\n    return {i}' for i in range(100)])

        with patch.object(self.block_extractor, 'query_manager') as mock_query_manager, \
             patch.object(self.block_extractor, 'parser_manager') as mock_parser_manager:

            # Mock query manager
            mock_query_manager.get_query_for_language.return_value = '''
            (function_definition
                name: (identifier) @function.name
                body: (block) @function.body) @function
            '''

            # Mock parser manager
            mock_parser = Mock()
            mock_tree = Mock()
            mock_parser_manager.acquire_resources.return_value = {
                'parser': mock_parser,
                'language': Mock()
            }

            # Mock query execution
            mock_query = Mock()
            mock_captures = {
                'function': [
                    {
                        'function.name': Mock(start_point=(i*2, 0), end_point=(i*2+1, 1)),
                        'function.body': Mock(start_point=(i*2, 15), end_point=(i*2+1, 1))
                    }
                    for i in range(100)
                ]
            }
            mock_query.captures.return_value = mock_captures
            mock_query_manager.get_cached_query.return_value = mock_query

            # Mock tree parsing
            mock_parser.parse.return_value = mock_tree
            mock_tree.root_node = Mock()

            blocks = self.block_extractor.extract_blocks(large_code, 'large.py', 'hash_large')

            assert len(blocks) == 100
            assert all(block.type == 'function' for block in blocks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])