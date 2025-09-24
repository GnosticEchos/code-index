"""
Pytest configuration and fixtures for MCP Server tests.

Provides common fixtures and configuration for all MCP server tests.
"""

import pytest
import tempfile
import os
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test utilities
from tests.utilities.test_data_generator import TestDataGenerator
from tests.utilities.service_mocks import ServiceMocks


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        test_files = [
            ("main.py", "def main():\n    print('Hello, World!')\n    return 0\n"),
            ("utils.py", "def helper_function():\n    return True\n\ndef another_helper():\n    return False\n"),
            ("models.py", "class User:\n    def __init__(self, name):\n        self.name = name\n\n    def get_name(self):\n        return self.name\n"),
            ("README.md", "# Test Project\n\nThis is a test project for MCP integration.\n\n## Features\n\n- Authentication\n- Database utilities\n"),
            ("config.json", '{"app_name": "test_app", "version": "1.0.0", "debug": true}\n'),
            ("requirements.txt", "requests>=2.25.0\npsycopg2>=2.8.0\npytest>=6.0.0\n")
        ]
        
        for filename, content in test_files:
            file_path = Path(temp_dir) / filename
            file_path.write_text(content)
        
        yield temp_dir


@pytest.fixture
def temp_config_file(temp_workspace):
    """Create a temporary configuration file."""
    config_data = {
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "nomic-embed-text:latest",
        "qdrant_url": "http://localhost:6333",
        "embedding_length": 768,
        "workspace_path": temp_workspace,
        "chunking_strategy": "lines",
        "use_tree_sitter": False,
        "search_min_score": 0.4,
        "search_max_results": 50,
        "batch_segment_threshold": 60,
        "embed_timeout_seconds": 60
    }
    
    config_file = Path(temp_workspace) / "code_index.json"
    config_file.write_text(json.dumps(config_data, indent=2))
    
    return str(config_file)


@pytest.fixture
def mock_context():
    """Create a mock MCP context for tool calls."""
    context = Mock()
    context.elicit = Mock()
    return context


@pytest.fixture
def mock_ollama_embedder():
    """Create a mock Ollama embedder."""
    with patch('src.code_index.embedder.OllamaEmbedder') as mock_class:
        mock_embedder = Mock()
        mock_embedder.validate_configuration.return_value = {"valid": True}
        mock_embedder.create_embeddings.return_value = {
            "embeddings": [[0.1] * 768, [0.2] * 768]
        }
        mock_class.return_value = mock_embedder
        yield mock_embedder


@pytest.fixture
def mock_qdrant_vector_store():
    """Create a mock Qdrant vector store."""
    with patch('src.code_index.vector_store.QdrantVectorStore') as mock_class:
        mock_vector_store = Mock()
        mock_vector_store.initialize = Mock()
        mock_vector_store.collection_name = "ws-test123456789"
        
        # Mock collections
        mock_collection = Mock()
        mock_collection.name = "ws-test123456789"
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_vector_store.client.get_collections.return_value = mock_collections
        
        # Mock search results
        mock_vector_store.search.return_value = []
        
        mock_class.return_value = mock_vector_store
        yield mock_vector_store


@pytest.fixture
def mock_collection_manager():
    """Create a mock collection manager."""
    with patch('src.code_index.collections.CollectionManager') as mock_class:
        mock_manager = Mock()
        mock_manager.list_collections.return_value = []
        mock_manager.get_collection_info.return_value = {
            "name": "ws-test123456789",
            "points_count": 100,
            "workspace_path": "/test/workspace",
            "dimensions": {"vector": 768},
            "model_identifier": "nomic-embed-text"
        }
        mock_manager.delete_collection.return_value = True
        mock_manager.prune_old_collections.return_value = []
        mock_class.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def mock_indexing_components():
    """Create mock components for indexing operations."""
    mocks = {}
    
    # Mock scanner
    with patch('src.code_index.scanner.DirectoryScanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_directory.return_value = (["main.py", "utils.py"], 0)
        mock_scanner_class.return_value = mock_scanner
        mocks['scanner'] = mock_scanner
        
        # Mock parser
        with patch('src.code_index.parser.CodeParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            mocks['parser'] = mock_parser
            
            # Mock cache manager
            with patch('src.code_index.cache.CacheManager') as mock_cache_class:
                mock_cache = Mock()
                mock_cache_class.return_value = mock_cache
                mocks['cache'] = mock_cache
                
                # Mock chunking strategies
                with patch('src.code_index.chunking.LineChunkingStrategy') as mock_line_chunking:
                    with patch('src.code_index.chunking.TokenChunkingStrategy') as mock_token_chunking:
                        with patch('src.code_index.chunking.TreeSitterChunkingStrategy') as mock_tree_chunking:
                            mocks['line_chunking'] = mock_line_chunking.return_value
                            mocks['token_chunking'] = mock_token_chunking.return_value
                            mocks['tree_chunking'] = mock_tree_chunking.return_value
                            
                            yield mocks


@pytest.fixture
def mock_all_services(mock_ollama_embedder, mock_qdrant_vector_store, mock_collection_manager, mock_indexing_components):
    """Combine all service mocks for comprehensive testing."""
    return {
        "embedder": mock_ollama_embedder,
        "vector_store": mock_qdrant_vector_store,
        "collection_manager": mock_collection_manager,
        **mock_indexing_components
    }


@pytest.fixture
def sample_search_results():
    """Provide sample search results for testing."""
    return [
        {
            "score": 0.85,
            "adjustedScore": 0.90,
            "payload": {
                "filePath": "main.py",
                "startLine": 1,
                "endLine": 3,
                "type": "function",
                "codeChunk": "def main():\n    print('Hello, World!')\n    return 0"
            }
        },
        {
            "score": 0.75,
            "adjustedScore": 0.80,
            "payload": {
                "filePath": "utils.py",
                "startLine": 1,
                "endLine": 2,
                "type": "function",
                "codeChunk": "def helper_function():\n    return True"
            }
        },
        {
            "score": 0.65,
            "adjustedScore": 0.70,
            "payload": {
                "filePath": "models.py",
                "startLine": 1,
                "endLine": 3,
                "type": "class",
                "codeChunk": "class User:\n    def __init__(self, name):\n        self.name = name"
            }
        }
    ]


@pytest.fixture
def sample_collections_data():
    """Provide sample collections data for testing."""
    return [
        {
            "name": "ws-abc123def456",
            "points_count": 150,
            "workspace_path": "/test/workspace1",
            "dimensions": {"vector": 768},
            "model_identifier": "nomic-embed-text",
            "vectors_count": 150,
            "status": "green"
        },
        {
            "name": "ws-def456ghi789",
            "points_count": 75,
            "workspace_path": "/test/workspace2",
            "dimensions": {"vector": 768},
            "model_identifier": "nomic-embed-text",
            "vectors_count": 75,
            "status": "green"
        }
    ]


@pytest.fixture(autouse=True)
def mock_path_exists():
    """Mock Path.exists to return True for workspace validation."""
    with patch('pathlib.Path.exists', return_value=True):
        yield


@pytest.fixture
def configuration_examples():
    """Provide configuration examples for testing."""
    return {
        "fast_indexing": {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "nomic-embed-text:latest",
            "qdrant_url": "http://localhost:6333",
            "embedding_length": 768,
            "chunking_strategy": "lines",
            "use_tree_sitter": False,
            "batch_segment_threshold": 100,
            "embed_timeout_seconds": 60,
            "search_min_score": 0.3,
            "search_max_results": 100
        },
        "semantic_accuracy": {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "nomic-embed-text:latest",
            "qdrant_url": "http://localhost:6333",
            "embedding_length": 768,
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True,
            "tree_sitter_skip_test_files": True,
            "tree_sitter_skip_examples": True,
            "batch_segment_threshold": 30,
            "embed_timeout_seconds": 120,
            "search_min_score": 0.5,
            "search_max_results": 50
        },
        "large_repository": {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "nomic-embed-text:latest",
            "qdrant_url": "http://localhost:6333",
            "embedding_length": 768,
            "chunking_strategy": "tokens",
            "use_tree_sitter": False,
            "use_mmap_file_reading": True,
            "max_file_size_bytes": 2097152,
            "batch_segment_threshold": 30,
            "embed_timeout_seconds": 180,
            "search_min_score": 0.4,
            "search_max_results": 75
        }
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file names."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to tests that might be slow
        if any(keyword in item.name.lower() for keyword in ["workflow", "end_to_end", "complete"]):
            item.add_marker(pytest.mark.slow)


# Custom assertions
def assert_mcp_error_response(response: Dict[str, Any], error_type: str = None):
    """Assert that a response is a valid MCP error response."""
    assert isinstance(response, dict)
    assert response.get("error") is True
    assert "error_type" in response
    assert "message" in response
    assert "actionable_guidance" in response
    
    if error_type:
        assert response["error_type"] == error_type


def assert_mcp_success_response(response: Dict[str, Any], expected_keys: List[str] = None):
    """Assert that a response is a valid MCP success response."""
    assert isinstance(response, dict)
    assert response.get("success") is True
    assert "message" in response
    
    if expected_keys:
        for key in expected_keys:
            assert key in response


def assert_search_results_format(results: List[Dict[str, Any]]):
    """Assert that search results have the correct format."""
    assert isinstance(results, list)
    
    for result in results:
        assert isinstance(result, dict)
        required_keys = ["filePath", "startLine", "endLine", "type", "score", "adjustedScore", "snippet"]
        for key in required_keys:
            assert key in result
        
        assert isinstance(result["startLine"], int)
        assert isinstance(result["endLine"], int)
        assert isinstance(result["score"], (int, float))
        assert isinstance(result["adjustedScore"], (int, float))
        assert 0.0 <= result["score"] <= 1.0
        assert 0.0 <= result["adjustedScore"] <= 1.0


# Tree-sitter specific fixtures

@pytest.fixture
def tree_sitter_config():
    """Provide a test configuration with Tree-sitter enabled."""
    return TestDataGenerator.create_config()


@pytest.fixture
def tree_sitter_error_handler():
    """Provide a test error handler for Tree-sitter."""
    return TestDataGenerator.create_error_handler()


@pytest.fixture
def tree_sitter_file_data():
    """Provide test data for Tree-sitter file processing."""
    return TestDataGenerator.create_python_file_data()


@pytest.fixture
def tree_sitter_service_mocks():
    """Provide all Tree-sitter service mocks."""
    return ServiceMocks.create_tree_sitter_mocks()


@pytest.fixture
def tree_sitter_patched_services():
    """Provide patched Tree-sitter services context."""
    with ServiceMocks.patch_all_services() as mocks:
        yield mocks


@pytest.fixture
def tree_sitter_patched_imports():
    """Provide patched Tree-sitter imports context."""
    with ServiceMocks.patch_tree_sitter_imports() as mocks:
        yield mocks


# Make custom assertions available globally
pytest.assert_mcp_error_response = assert_mcp_error_response
pytest.assert_mcp_success_response = assert_mcp_success_response
pytest.assert_search_results_format = assert_search_results_format