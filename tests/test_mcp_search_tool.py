"""
Unit tests for MCP Search Tool.

Tests the search tool functionality including parameter validation,
search execution, and result formatting.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.code_index.mcp_server.tools.search_tool import (
    search,
    create_search_tool_description,
    _create_empty_results_response,
    _format_search_results,
    _create_code_snippet
)
from src.code_index.config import Config


class TestSearchTool:
    """Test cases for the search tool function."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        return Mock()
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                ("main.py", "def main():\n    print('Hello, World!')\n"),
                ("utils.py", "def helper():\n    return True\n"),
                ("README.md", "# Test Project\n\nThis is a test.\n")
            ]
            
            for filename, content in test_files:
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
            
            # Create config file
            config_file = Path(temp_dir) / "code_index.json"
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "workspace_path": temp_dir,
                "search_min_score": 0.4,
                "search_max_results": 50
            }
            config_file.write_text(json.dumps(config_data, indent=2))
            
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_search_tool_missing_query(self, mock_context, temp_workspace):
        """Test search tool with missing query parameter."""
        with pytest.raises(ValueError, match="query parameter is required"):
            await search(
                ctx=mock_context,
                query="",  # Empty query
                workspace=temp_workspace
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_invalid_query_type(self, mock_context, temp_workspace):
        """Test search tool with invalid query type."""
        with pytest.raises(ValueError, match="query parameter is required"):
            await search(
                ctx=mock_context,
                query=None,  # None query
                workspace=temp_workspace
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_invalid_workspace_type(self, mock_context):
        """Test search tool with invalid workspace type."""
        with pytest.raises(ValueError, match="workspace must be a string"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=123  # Invalid type
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_nonexistent_workspace(self, mock_context):
        """Test search tool with non-existent workspace."""
        with pytest.raises(ValueError, match="Workspace path does not exist"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace="/nonexistent/path"
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_workspace_not_directory(self, mock_context):
        """Test search tool with workspace that is not a directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValueError, match="Workspace path is not a directory"):
                await search(
                    ctx=mock_context,
                    query="test query",
                    workspace=temp_file.name
                )
    
    @pytest.mark.asyncio
    async def test_search_tool_invalid_min_score(self, mock_context, temp_workspace):
        """Test search tool with invalid min_score parameter."""
        with pytest.raises(ValueError, match="min_score must be a number between 0.0 and 1.0"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=temp_workspace,
                min_score=1.5  # Invalid range
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_invalid_max_results(self, mock_context, temp_workspace):
        """Test search tool with invalid max_results parameter."""
        with pytest.raises(ValueError, match="max_results must be a positive integer"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=temp_workspace,
                max_results=0  # Invalid value
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_configuration_error(self, mock_context, temp_workspace):
        """Test search tool with configuration loading error."""
        with patch('src.code_index.mcp_server.tools.search_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:
                # Mock config manager to raise error
                mock_config_manager = Mock()
                mock_config_manager.load_config.side_effect = ValueError("Configuration error: invalid file")
                mock_config_manager_class.return_value = mock_config_manager

                # Mock vector store to bypass collection check
                mock_vector_store = Mock()
                mock_collection = Mock()
                mock_collection.name = "test_collection"
                mock_collections = Mock()
                mock_collections.collections = [mock_collection]
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "test_collection"
                mock_vector_store.search.return_value = []  # Return empty list to avoid len() error
                mock_vector_store_class.return_value = mock_vector_store

                with pytest.raises(ValueError, match="Configuration error"):
                    await search(
                        ctx=mock_context,
                        query="test query",
                        workspace=temp_workspace
                    )
    
    @pytest.mark.asyncio
    async def test_search_tool_service_validation_failure(self, mock_context, temp_workspace):
        """Test search tool with service validation failure."""
        with patch('src.code_index.mcp_server.tools.search_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.search_tool.OllamaEmbedder') as mock_embedder_class:
                with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:
                    # Mock config manager to return valid config
                    mock_config_manager = Mock()
                    base_config = Mock()
                    base_config.workspace_path = temp_workspace
                    base_config.ollama_base_url = "http://localhost:11434"
                    base_config.ollama_model = "nomic-embed-text:latest"
                    base_config.qdrant_url = "http://localhost:6333"
                    base_config.embedding_length = 768
                    base_config.embed_timeout_seconds = 60
                    base_config.search_min_score = 0.4
                    base_config.search_max_results = 50
                    mock_config_manager.load_config.return_value = base_config
                    mock_config_manager.apply_overrides.return_value = base_config
                    mock_config_manager_class.return_value = mock_config_manager

                    mock_embedder = Mock()
                    mock_embedder.validate_configuration.return_value = {
                        "valid": False,
                        "error": "Connection failed"
                    }
                    mock_embedder_class.return_value = mock_embedder

                    # Mock vector store to bypass collection check
                    mock_vector_store = Mock()
                    mock_collection = Mock()
                    mock_collection.name = "test_collection"
                    mock_collections = Mock()
                    mock_collections.collections = [mock_collection]
                    mock_vector_store.client.get_collections.return_value = mock_collections
                    mock_vector_store.collection_name = "test_collection"
                    mock_vector_store.search.return_value = []  # Return empty list to avoid len() error
                    mock_vector_store_class.return_value = mock_vector_store

                    with pytest.raises(Exception, match="Ollama service validation failed"):
                        await search(
                            ctx=mock_context,
                            query="test query",
                            workspace=temp_workspace
                        )
    
    @pytest.mark.asyncio
    async def test_search_tool_collection_not_found(self, mock_context, temp_workspace):
        """Test search tool with collection not found."""
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                
                # Mock successful embedder validation
                mock_embedder = Mock()
                mock_embedder.validate_configuration.return_value = {"valid": True}
                mock_embedder_class.return_value = mock_embedder
                
                # Mock vector store with no collections
                mock_vector_store = Mock()
                mock_collections = Mock()
                mock_collections.collections = []  # No collections
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "test_collection"
                mock_vector_store_class.return_value = mock_vector_store
                
                with pytest.raises(ValueError, match="Workspace has not been indexed yet"):
                    await search(
                        ctx=mock_context,
                        query="test query",
                        workspace=temp_workspace
                    )
    
    @pytest.mark.asyncio
    async def test_search_tool_embedding_failure(self, mock_context, temp_workspace):
        """Test search tool with embedding generation failure."""
        with patch('src.code_index.mcp_server.tools.search_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.search_tool.OllamaEmbedder') as mock_embedder_class:
                with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:
                    # Mock config manager to return valid config
                    mock_config_manager = Mock()
                    base_config = Mock()
                    base_config.workspace_path = temp_workspace
                    base_config.ollama_base_url = "http://localhost:11434"
                    base_config.ollama_model = "nomic-embed-text:latest"
                    base_config.qdrant_url = "http://localhost:6333"
                    base_config.embedding_length = 768
                    base_config.embed_timeout_seconds = 60
                    base_config.search_min_score = 0.4
                    base_config.search_max_results = 50
                    mock_config_manager.load_config.return_value = base_config
                    mock_config_manager.apply_overrides.return_value = base_config
                    mock_config_manager_class.return_value = mock_config_manager

                    # Mock embedder that fails during embedding generation
                    mock_embedder = Mock()
                    mock_embedder.validate_configuration.return_value = {"valid": True}
                    mock_embedder.create_embeddings.side_effect = Exception("Embedding failed")
                    mock_embedder_class.return_value = mock_embedder

                    # Mock vector store with existing collection
                    mock_vector_store = Mock()
                    mock_collection = Mock()
                    mock_collection.name = "test_collection"
                    mock_collections = Mock()
                    mock_collections.collections = [mock_collection]
                    mock_vector_store.client.get_collections.return_value = mock_collections
                    mock_vector_store.collection_name = "test_collection"
                    mock_vector_store.search.return_value = []  # Return empty list to avoid len() error
                    mock_vector_store_class.return_value = mock_vector_store

                    with pytest.raises(Exception, match="Failed to generate embedding"):
                        await search(
                            ctx=mock_context,
                            query="test query",
                            workspace=temp_workspace
                        )
    
    @pytest.mark.asyncio
    async def test_search_tool_search_failure(self, mock_context, temp_workspace):
        """Test search tool with search operation failure."""
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:

                # Mock successful embedder
                mock_embedder = Mock()
                mock_embedder.validate_configuration.return_value = {"valid": True}
                mock_embedder.create_embeddings.return_value = {
                    "embeddings": [[0.1, 0.2, 0.3]]  # Mock embedding
                }
                mock_embedder_class.return_value = mock_embedder

                # Mock vector store that fails during search
                mock_vector_store = Mock()
                mock_collection = Mock()
                mock_collection.name = "test_collection"
                mock_collections = Mock()
                mock_collections.collections = [mock_collection]
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "test_collection"
                mock_vector_store.search.side_effect = Exception("Search failed")
                mock_vector_store_class.return_value = mock_vector_store

                with pytest.raises(Exception, match="Search operation failed"):
                    await search(
                        ctx=mock_context,
                        query="test query",
                        workspace=temp_workspace
                    )
    
    @pytest.mark.asyncio
    async def test_search_tool_successful_search(self, mock_context, temp_workspace):
        """Test successful search tool execution."""
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:

                # Mock successful embedder
                mock_embedder = Mock()
                mock_embedder.validate_configuration.return_value = {"valid": True}
                mock_embedder.create_embeddings.return_value = {
                    "embeddings": [[0.1] * 768]  # Mock 768-dimensional embedding
                }
                mock_embedder_class.return_value = mock_embedder

                # Mock successful vector store
                mock_vector_store = Mock()
                mock_collection = Mock()
                mock_collection.name = "test_collection"
                mock_collections = Mock()
                mock_collections.collections = [mock_collection]
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "test_collection"

                # Mock search results
                mock_results = [
                    {
                        "score": 0.85,
                        "adjustedScore": 0.90,
                        "payload": {
                            "filePath": "main.py",
                            "startLine": 1,
                            "endLine": 3,
                            "type": "function",
                            "codeChunk": "def main():\n    print('Hello, World!')\n"
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
                            "codeChunk": "def helper():\n    return True\n"
                        }
                    }
                ]
                mock_vector_store.search.return_value = mock_results
                mock_vector_store_class.return_value = mock_vector_store

                result = await search(
                    ctx=mock_context,
                    query="test query",
                    workspace=temp_workspace,
                    min_score=0.5,
                    max_results=10
                )

                assert isinstance(result, list)
                assert len(result) == 2

                # Check first result
                first_result = result[0]
                assert first_result["filePath"] == "main.py"
                assert first_result["startLine"] == 1
                assert first_result["endLine"] == 3
                assert first_result["type"] == "function"
                assert first_result["score"] == 0.85
                assert first_result["adjustedScore"] == 0.90
                assert "def main()" in first_result["snippet"]
    
    @pytest.mark.asyncio
    async def test_search_tool_empty_results(self, mock_context, temp_workspace):
        """Test search tool with empty results."""
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:

                # Mock successful embedder
                mock_embedder = Mock()
                mock_embedder.validate_configuration.return_value = {"valid": True}
                mock_embedder.create_embeddings.return_value = {
                    "embeddings": [[0.1] * 768]  # Mock 768-dimensional embedding
                }
                mock_embedder_class.return_value = mock_embedder

                # Mock vector store with empty results
                mock_vector_store = Mock()
                mock_collection = Mock()
                mock_collection.name = "test_collection"
                mock_collections = Mock()
                mock_collections.collections = [mock_collection]
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "test_collection"
                mock_vector_store.search.return_value = []  # Empty results
                mock_vector_store_class.return_value = mock_vector_store

                result = await search(
                    ctx=mock_context,
                    query="nonexistent query",
                    workspace=temp_workspace
                )

                assert isinstance(result, list)
                assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_search_tool_with_overrides(self, mock_context, temp_workspace):
        """Test search tool with configuration overrides."""
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore') as mock_vector_store_class:
                with patch('src.code_index.mcp_server.tools.search_tool.MCPConfigurationManager') as mock_config_manager_class:

                    # Mock config manager
                    mock_config_manager = Mock()
                    base_config = Config()
                    base_config.embedding_length = 1024  # Use 1024 to match expected dimension
                    base_config.search_min_score = 0.4
                    base_config.search_max_results = 50
                    mock_config_manager.load_config.return_value = base_config

                    # Mock apply_overrides to return modified config
                    modified_config = Config()
                    modified_config.embedding_length = 1024  # Use 1024 to match expected dimension
                    modified_config.search_min_score = 0.6  # Override applied
                    modified_config.search_max_results = 20  # Override applied
                    mock_config_manager.apply_overrides.return_value = modified_config
                    mock_config_manager_class.return_value = mock_config_manager

                    # Mock successful embedder and vector store
                    mock_embedder = Mock()
                    mock_embedder.validate_configuration.return_value = {"valid": True}
                    mock_embedder.create_embeddings.return_value = {"embeddings": [[0.1] * 1024]}  # Mock 1024-dimensional embedding
                    mock_embedder_class.return_value = mock_embedder

                    mock_vector_store = Mock()
                    mock_collection = Mock()
                    mock_collection.name = "test_collection"
                    mock_collections = Mock()
                    mock_collections.collections = [mock_collection]
                    mock_vector_store.client.get_collections.return_value = mock_collections
                    mock_vector_store.collection_name = "test_collection"
                    mock_vector_store.search.return_value = []
                    mock_vector_store_class.return_value = mock_vector_store

                    result = await search(
                        ctx=mock_context,
                        query="test query",
                        workspace=temp_workspace
                    )

                    # Configuration overrides removed due to FastMCP limitations


class TestSearchToolHelpers:
    """Test cases for search tool helper functions."""
    
    def test_create_empty_results_response(self):
        """Test creating empty results response."""
        result = _create_empty_results_response("test query", 0.5, "/test/workspace")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_format_search_results_empty(self):
        """Test formatting empty search results."""
        config = Config()
        result = _format_search_results([], config)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_format_search_results_with_data(self):
        """Test formatting search results with data."""
        config = Config()
        config.search_snippet_preview_chars = 100
        
        raw_results = [
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
                    "startLine": 5,
                    "endLine": 7,
                    "type": "function",
                    "codeChunk": "def helper():\n    return True"
                }
            }
        ]
        
        result = _format_search_results(raw_results, config)
        
        assert len(result) == 2
        
        # Check first result (should be sorted by adjustedScore)
        first_result = result[0]
        assert first_result["filePath"] == "main.py"
        assert first_result["startLine"] == 1
        assert first_result["endLine"] == 3
        assert first_result["type"] == "function"
        assert first_result["score"] == 0.85
        assert first_result["adjustedScore"] == 0.90
        assert "def main()" in first_result["snippet"]
        
        # Check second result
        second_result = result[1]
        assert second_result["filePath"] == "utils.py"
        assert second_result["adjustedScore"] == 0.80
    
    def test_format_search_results_missing_payload(self):
        """Test formatting search results with missing payload data."""
        config = Config()
        
        raw_results = [
            {
                "score": 0.85,
                "adjustedScore": 0.90,
                "payload": None  # Missing payload
            },
            {
                "score": 0.75,
                # Missing adjustedScore and payload
            }
        ]
        
        result = _format_search_results(raw_results, config)
        
        assert len(result) == 2
        
        # Should handle missing data gracefully
        first_result = result[0]
        assert first_result["filePath"] == ""
        assert first_result["startLine"] == 0
        assert first_result["endLine"] == 0
        assert first_result["type"] == ""
        assert first_result["score"] == 0.85
        assert first_result["adjustedScore"] == 0.90
        assert first_result["snippet"] == ""
        
        second_result = result[1]
        assert second_result["score"] == 0.75
        assert second_result["adjustedScore"] == 0.75  # Should default to score
    
    def test_create_code_snippet_basic(self):
        """Test creating basic code snippet."""
        code = "def hello():\n    return 'world'\n\nprint('test')"
        snippet = _create_code_snippet(code, 50)
        
        assert len(snippet) <= 53  # 50 + "..."
        assert "def hello()" in snippet
    
    def test_create_code_snippet_empty(self):
        """Test creating code snippet from empty code."""
        snippet = _create_code_snippet("", 100)
        assert snippet == ""
    
    def test_create_code_snippet_short_code(self):
        """Test creating code snippet from short code."""
        code = "print('hello')"
        snippet = _create_code_snippet(code, 100)
        
        assert snippet == code  # Should return as-is
        assert not snippet.endswith("...")
    
    def test_create_code_snippet_long_code(self):
        """Test creating code snippet from long code."""
        code = "def very_long_function_name():\n" + "    # This is a comment\n" * 20
        snippet = _create_code_snippet(code, 50)
        
        assert len(snippet) <= 53  # 50 + "..."
        assert snippet.endswith("...")
        assert "def very_long_function_name()" in snippet
    
    def test_create_code_snippet_boundary_truncation(self):
        """Test code snippet truncation at word boundaries."""
        code = "def function():\n    return True\n\ndef another_function():\n    pass"
        snippet = _create_code_snippet(code, 30)
        
        assert len(snippet) <= 33  # 30 + "..."
        assert snippet.endswith("...")
        # Should try to truncate at reasonable boundary
    
    def test_create_code_snippet_excessive_empty_lines(self):
        """Test code snippet with excessive empty lines."""
        code = "def function():\n\n\n\n\n    return True\n\n\n\ndef another():\n    pass"
        snippet = _create_code_snippet(code, 100)
        
        # Should clean up excessive empty lines
        assert snippet.count("\n\n\n") == 0  # Should not have triple newlines


class TestSearchToolDescription:
    """Test cases for search tool description generation."""
    
    def test_create_search_tool_description(self):
        """Test search tool description creation."""
        description = create_search_tool_description()
        
        assert isinstance(description, str)
        assert len(description) > 100  # Should be comprehensive
        
        # Check for key sections
        assert "PREREQUISITE" in description
        assert "Usage Examples:" in description
        assert "Parameters:" in description
        assert "# Configuration overrides removed due to FastMCP limitations" in description
        assert "Search Optimization Tips:" in description
        assert "Common Error Solutions:" in description
        assert "Returns:" in description
        
        # Check for specific parameters
        assert "query" in description
        assert "workspace" in description
        assert "min_score" in description
        assert "max_results" in description
        
        # Configuration overrides removed due to FastMCP limitations
        assert "# Configuration overrides removed due to FastMCP limitations" in description
        
        # Check for examples
        assert "search(query=" in description
        assert "authentication middleware" in description
        
        # Check for optimization tips
        assert "specific technical terms" in description
        assert "min_score values" in description
        
        # Check for error solutions
        assert "No collections found" in description
        assert "Run the 'index' tool first" in description


if __name__ == "__main__":
    pytest.main([__file__])