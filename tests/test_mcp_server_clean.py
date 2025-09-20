"""
Unit tests for MCP Server core functionality.

Tests the main MCP server class, configuration loading, service validation,
and tool registration.
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from src.code_index.mcp_server.server import CodeIndexMCPServer
from src.code_index.config import Config


class TestCodeIndexMCPServer:
    """Test cases for the main MCP server class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "chunking_strategy": "lines",
                "use_tree_sitter": False,
                "search_min_score": 0.4,
                "search_max_results": 50
            }
            json.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def mock_fastmcp(self):
        """Mock FastMCP for testing."""
        with patch('src.code_index.mcp_server.server.FastMCP') as mock:
            mock_instance = Mock()
            mock_instance.run_async = AsyncMock()
            mock_instance.run = AsyncMock()
            mock_instance.tool = Mock()
            mock_instance.tool.return_value = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_config_manager(self):
        """Mock configuration manager."""
        with patch('src.code_index.mcp_server.server.MCPConfigurationManager') as mock:
            mock_instance = Mock()
            mock_config = Config()
            mock_config.embedding_length = 768
            mock_instance.load_config.return_value = mock_config
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_resource_manager(self):
        """Mock resource manager."""
        with patch('src.code_index.mcp_server.server.resource_manager') as mock:
            mock.initialize = Mock()
            mock.shutdown = AsyncMock()
            mock.register_shutdown_handler = Mock()
            mock.register_ollama_connection = Mock()
            mock.register_qdrant_connection = Mock()
            yield mock

    def test_server_initialization(self, temp_config_file):
        """Test server initialization with configuration file."""
        server = CodeIndexMCPServer(temp_config_file)
        
        assert server.config_path == temp_config_file
        assert server.config is None  # Not loaded until start()
        assert server._running is False
        assert server.config_manager is not None

    def test_server_initialization_default_config(self):
        """Test server initialization with default configuration."""
        server = CodeIndexMCPServer()
        
        assert server.config_path == "code_index.json"
        assert server.config is None
        assert server._running is False

    @pytest.mark.asyncio
    async def test_load_configuration_success(self, temp_config_file, mock_config_manager):
        """Test successful configuration loading."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config_manager = mock_config_manager
        
        await server._load_configuration()
        
        assert server.config is not None
        mock_config_manager.load_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_configuration_failure(self, temp_config_file, mock_config_manager):
        """Test configuration loading failure."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config_manager = mock_config_manager
        
        # Mock configuration loading failure
        mock_config_manager.load_config.side_effect = ValueError("Invalid configuration")
        
        with pytest.raises(ValueError, match="Invalid configuration"):
            await server._load_configuration()

    @pytest.mark.asyncio
    async def test_validate_services_success(self, temp_config_file, mock_resource_manager):
        """Test successful service validation."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config = Config()
        server.config.embedding_length = 768
        
        # Mock successful Ollama validation
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {"valid": True}
            mock_embedder_class.return_value = mock_embedder
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_qdrant_class:
                mock_qdrant = Mock()
                mock_collections = Mock()
                mock_collections.collections = []
                mock_qdrant.client.get_collections.return_value = mock_collections
                mock_qdrant_class.return_value = mock_qdrant
                
                await server._validate_services()
                
                # Verify service registration
                mock_resource_manager.register_ollama_connection.assert_called_once()
                mock_resource_manager.register_qdrant_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_services_ollama_failure(self, temp_config_file):
        """Test service validation with Ollama failure."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config = Config()
        server.config.embedding_length = 768
        
        # Mock Ollama validation failure
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {
                "valid": False,
                "error": "Connection failed"
            }
            mock_embedder_class.return_value = mock_embedder
            with pytest.raises(ValueError) as exc_info:
                await server._validate_services()
            assert "service_validation_failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_services_qdrant_failure(self, temp_config_file):
        """Test service validation with Qdrant failure."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config = Config()
        server.config.embedding_length = 768
        
        # Mock successful Ollama validation
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {"valid": True}
            mock_embedder_class.return_value = mock_embedder
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_qdrant_class:
                mock_qdrant_class.side_effect = Exception("Qdrant connection failed")
                
                with pytest.raises(ValueError) as exc_info:
                    await server._validate_services()
                assert "service_validation_failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_tools(self, temp_config_file, mock_fastmcp):
        """Test tool registration functionality."""
        server = CodeIndexMCPServer(temp_config_file)
        server._mcp = mock_fastmcp
        
        # Register tools
        server._register_tools()
        
        # Verify all three tools were registered
        assert mock_fastmcp.tool.call_count == 3
        
        # Check tool names
        registered_tools = [call[1]['name'] for call in mock_fastmcp.tool.call_args_list]
        assert 'index' in registered_tools
        assert 'search' in registered_tools
        assert 'collections' in registered_tools

    @pytest.mark.asyncio
    async def test_lifespan_manager(self, temp_config_file, mock_resource_manager):
        """Test lifespan manager functionality."""
        server = CodeIndexMCPServer(temp_config_file)
        
        # Mock server object
        mock_server = Mock()
        
        # Test lifespan manager
        lifespan_gen = server._lifespan_manager(mock_server)
        
        # Start phase - use async with instead of __anext__
        async with lifespan_gen:
            # Verify initialization
            mock_resource_manager.initialize.assert_called_once()
            mock_resource_manager.register_shutdown_handler.assert_called_once()
        
        # Verify shutdown was called
        mock_resource_manager.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_success(self, temp_config_file, mock_fastmcp, mock_config_manager, mock_resource_manager):
        """Test successful server start."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config_manager = mock_config_manager
        
        # Mock service validation
        with patch.object(server, '_validate_services', new_callable=AsyncMock):
            with patch.object(server, '_register_tools'):
                await server.start()
                
                assert server._running is True
                mock_fastmcp.run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    async def test_start_configuration_failure(self, temp_config_file, mock_config_manager):
        """Test server start with configuration failure."""
        server = CodeIndexMCPServer(temp_config_file)
        server.config_manager = mock_config_manager
        
        # Mock configuration loading failure
        mock_config_manager.load_config.side_effect = ValueError("Config error")
        
        with pytest.raises(ValueError, match="Config error"):
            await server.start()
        
        assert server._running is False

    @pytest.mark.asyncio
    async def test_shutdown(self, temp_config_file):
        """Test server shutdown."""
        server = CodeIndexMCPServer(temp_config_file)
        server._running = True
        
        await server.shutdown()
        
        assert server._running is False

    def test_cleanup_server_resources(self, temp_config_file):
        """Test server resource cleanup."""
        server = CodeIndexMCPServer(temp_config_file)
        
        # Should not raise any exceptions
        server._cleanup_server_resources()


class TestServerIntegration:
    """Integration tests for server components."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def hello():\n    return 'world'\n")
            
            config_file = Path(temp_dir) / "code_index.json"
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "workspace_path": temp_dir
            }
            config_file.write_text(json.dumps(config_data, indent=2))
            
            yield temp_dir

    @pytest.mark.asyncio
    async def test_server_with_real_config(self, temp_workspace):
        """Test server initialization with real configuration file."""
        config_path = os.path.join(temp_workspace, "code_index.json")
        server = CodeIndexMCPServer(config_path)
        
        # Test configuration loading
        await server._load_configuration()
        
        assert server.config is not None
        assert server.config.embedding_length == 768
        assert server.config.workspace_path == temp_workspace

    def test_server_error_handling(self, temp_workspace):
        """Test server error handling with invalid configuration."""
        # Create invalid config
        config_path = os.path.join(temp_workspace, "invalid_config.json")
        with open(config_path, 'w') as f:
            f.write("invalid json content")
        
        server = CodeIndexMCPServer(config_path)
        
        # Should handle invalid JSON gracefully
        with pytest.raises(ValueError):
            asyncio.run(server._load_configuration())


if __name__ == "__main__":
    pytest.main([__file__])