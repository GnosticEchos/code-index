"""
Unit tests for MCP Search Tool.

Tests the search tool functionality including parameter validation,
search execution, and result formatting.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from src.code_index.config import Config
from src.code_index.mcp_server.tools.search_tool import (
    _create_code_snippet,
    _format_search_results,
    create_search_tool_description,
    search,
)
from src.code_index.models import SearchMatch, SearchResult
from src.code_index.services.shared.command_context import SearchDependencies


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
                query=None,  # type: ignore  # None query
                workspace=temp_workspace
            )
    
    @pytest.mark.asyncio
    async def test_search_tool_invalid_workspace_type(self, mock_context):
        """Test search tool with invalid workspace type."""
        with pytest.raises(ValueError, match="workspace must be a string"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=123  # type: ignore[arg-type]  # Invalid type
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
    async def test_search_tool_configuration_error(self, mock_context, temp_workspace, command_context_mock):
        """Test search tool with configuration loading error."""
        command_context_mock.load_search_dependencies.side_effect = ValueError(
            "Configuration error: invalid file"
        )

        with pytest.raises(ValueError, match="Configuration error"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_search_tool_service_error(self, mock_context, temp_workspace, command_context_mock):
        """Test search tool handling of service errors from SearchService."""
        config = Config()
        config.search_min_score = 0.4
        config.search_max_results = 50

        failing_result = SearchResult(
            query="test query",
            matches=[],
            total_found=0,
            execution_time_seconds=0.1,
            search_method="text",
            config_summary={},
            errors=["Ollama service validation failed"],
            warnings=[],
        )

        search_service = MagicMock()
        search_service.search_code.return_value = failing_result

        collection_manager = MagicMock()
        collection_manager.list_collections.return_value = [
            {"workspace_path": temp_workspace, "name": "test-collection"}
        ]

        deps = SearchDependencies(
            config=config,
            search_service=search_service,
            collection_manager=collection_manager,
        )
        command_context_mock.load_search_dependencies.side_effect = None
        command_context_mock.load_search_dependencies.return_value = deps

        # Search should raise exception when there are service errors
        with pytest.raises(Exception, match="Search failed: Search execution reported errors: Ollama service validation failed"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_search_tool_search_failure(self, mock_context, temp_workspace, command_context_mock):
        """Test search tool when SearchService raises an exception."""
        config = Config()

        search_service = MagicMock()
        search_service.search_code.side_effect = Exception("Search service failed")

        collection_manager = MagicMock()
        collection_manager.list_collections.return_value = [
            {"workspace_path": temp_workspace, "name": "test-collection"}
        ]

        deps = SearchDependencies(
            config=config,
            search_service=search_service,
            collection_manager=collection_manager,
        )
        command_context_mock.load_search_dependencies.side_effect = None
        command_context_mock.load_search_dependencies.return_value = deps

        # Search should raise exception when search service fails
        with pytest.raises(Exception, match="Search failed: Search service failed"):
            await search(
                ctx=mock_context,
                query="test query",
                workspace=temp_workspace
            )

    @pytest.mark.asyncio
    async def test_search_tool_successful_search(self, mock_context, temp_workspace, command_context_mock):
        """Test successful search execution."""
        config = Config()
        config.search_snippet_preview_chars = 120

        matches = [
            SearchMatch(
                file_path="main.py",
                start_line=1,
                end_line=3,
                code_chunk="def main():\n    print('Hello, World!')\n",
                match_type="function",
                score=0.85,
                adjusted_score=0.9,
                metadata={},
            ),
            SearchMatch(
                file_path="utils.py",
                start_line=5,
                end_line=6,
                code_chunk="def helper():\n    return True\n",
                match_type="function",
                score=0.75,
                adjusted_score=0.8,
                metadata={},
            ),
        ]

        successful_result = SearchResult(
            query="test query",
            matches=matches,
            total_found=2,
            execution_time_seconds=0.05,
            search_method="text",
            config_summary={},
            errors=[],
            warnings=[],
        )

        search_service = MagicMock()
        search_service.search_code.return_value = successful_result

        collection_manager = MagicMock()
        collection_manager.list_collections.return_value = [
            {"workspace_path": temp_workspace, "name": "test-collection"}
        ]

        deps = SearchDependencies(
            config=config,
            search_service=search_service,
            collection_manager=collection_manager,
        )
        command_context_mock.load_search_dependencies.side_effect = None
        command_context_mock.load_search_dependencies.return_value = deps

        result = await search(
            ctx=mock_context,
            query="test query",
            workspace=temp_workspace,
            min_score=0.5,
            max_results=10,
        )

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["result_count"] == 2
        first_result = result["results"][0]
        assert first_result["filePath"] == "main.py"
        assert first_result["startLine"] == 1
        assert first_result["endLine"] == 3
        assert first_result["type"] == "function"
        assert first_result["score"] == 0.85
        assert first_result["adjustedScore"] == 0.9
        assert "def main()" in first_result["snippet"]

    @pytest.mark.asyncio
    async def test_search_tool_not_indexed(self, mock_context, temp_workspace, command_context_mock):
        """Test search tool with not indexed workspace."""
        config = Config()

        collection_manager = MagicMock()
        collection_manager.list_collections.return_value = []

        deps = SearchDependencies(
            config=config,
            search_service=MagicMock(),
            collection_manager=collection_manager,
        )
        command_context_mock.load_search_dependencies.side_effect = None
        command_context_mock.load_search_dependencies.return_value = deps

        result = await search(
            ctx=mock_context,
            query="test query",
            workspace=temp_workspace
        )

        assert isinstance(result, dict)
        assert result["status"] == "not_indexed"
        assert result["results"] == []
        assert "not indexed" in result["message"]
        assert result["workspace"] == temp_workspace

    @pytest.mark.asyncio
    async def test_search_tool_empty_results(self, mock_context, temp_workspace, command_context_mock):
        """Test search tool returning no matches."""
        config = Config()
        config.search_min_score = 0.4

        empty_result = SearchResult(
            query="nonexistent query",
            matches=[],
            total_found=0,
            execution_time_seconds=0.02,
            search_method="text",
            config_summary={},
            errors=[],
            warnings=[],
        )

        search_service = MagicMock()
        search_service.search_code.return_value = empty_result

        collection_manager = MagicMock()
        collection_manager.list_collections.return_value = [
            {"workspace_path": temp_workspace, "name": "test-collection"}
        ]

        deps = SearchDependencies(
            config=config,
            search_service=search_service,
            collection_manager=collection_manager,
        )
        command_context_mock.load_search_dependencies.side_effect = None
        command_context_mock.load_search_dependencies.return_value = deps

        result = await search(
            ctx=mock_context,
            query="nonexistent query",
            workspace=temp_workspace
        )

        assert isinstance(result, dict)
        assert result["status"] == "no_results"
        assert result["results"] == []
        assert "no results matched the query" in result["message"]
        assert result["query"] == "nonexistent query"


class TestSearchToolHelpers:
    """Test cases for search tool helper functions."""
    
    def test_format_search_results_empty(self):
        """Test formatting empty search results."""
        result = _format_search_results([], 100)

        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_format_search_results_with_data(self):
        """Test formatting search results with data."""
        matches = [
            SearchMatch(
                file_path="main.py",
                start_line=1,
                end_line=3,
                code_chunk="def main():\n    print('Hello, World!')\n    return 0",
                match_type="function",
                score=0.85,
                adjusted_score=0.9,
                metadata={},
            ),
            SearchMatch(
                file_path="utils.py",
                start_line=5,
                end_line=7,
                code_chunk="def helper():\n    return True",
                match_type="function",
                score=0.75,
                adjusted_score=0.8,
                metadata={},
            ),
        ]

        result = _format_search_results(matches, 100)
        
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
    
    def test_format_search_results_missing_data(self):
        """Test formatting search results with missing match attributes."""
        class IncompleteMatch:
            def __init__(self, score: float):
                self.score = score

        matches = [IncompleteMatch(0.85), IncompleteMatch(0.75)]

        result = _format_search_results(matches, 80)

        assert len(result) == 2
        assert result[0]["score"] == 0.85
        assert result[0]["adjustedScore"] == 0.85
        assert result[0]["filePath"] == ""
    
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
        assert "Search Optimization Tips:" in description
        assert "Common Error Solutions:" in description
        assert "Returns:" in description
        
        # Check for specific parameters
        assert "query" in description
        assert "workspace" in description
        assert "min_score" in description
        assert "max_results" in description
        
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