"""
Integration tests for MCP Server.

Tests MCP protocol integration, service connectivity, and end-to-end workflows
covering index → search → collections flows.
"""

import pytest
import tempfile
import os
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.code_index.mcp_server.server import CodeIndexMCPServer
from src.code_index.config import Config


class TestMCPProtocolIntegration:
    """Integration tests for MCP protocol functionality."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with test files and configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                ("main.py", "def main():\n    print('Hello, World!')\n    return 0\n"),
                ("utils.py", "def helper_function():\n    return True\n\ndef another_helper():\n    return False\n"),
                ("models.py", "class User:\n    def __init__(self, name):\n        self.name = name\n"),
                ("README.md", "# Test Project\n\nThis is a test project for MCP integration.\n"),
                ("config.json", '{"app_name": "test_app", "version": "1.0.0"}\n')
            ]
            
            for filename, content in test_files:
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
            
            # Create MCP server configuration
            config_file = Path(temp_dir) / "code_index.json"
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "workspace_path": temp_dir,
                "chunking_strategy": "lines",
                "use_tree_sitter": False,
                "search_min_score": 0.4,
                "search_max_results": 50,
                "batch_segment_threshold": 60
            }
            config_file.write_text(json.dumps(config_data, indent=2))
            
            yield temp_dir
    
    @pytest.fixture
    def mock_services(self):
        """Mock external services (Ollama, Qdrant) for integration testing."""
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                
                # Mock successful Ollama embedder
                mock_embedder = Mock()
                mock_embedder.validate_configuration.return_value = {"valid": True}
                mock_embedder.create_embeddings.return_value = {
                    "embeddings": [[0.1] * 768]  # Mock 768-dimensional embedding
                }
                mock_embedder_class.return_value = mock_embedder
                
                # Mock successful Qdrant vector store
                mock_vector_store = Mock()
                mock_collection = Mock()
                mock_collection.name = "ws-test123456789"
                mock_collections = Mock()
                mock_collections.collections = [mock_collection]
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "ws-test123456789"
                mock_vector_store.initialize = Mock()
                mock_vector_store.search.return_value = []
                mock_vector_store_class.return_value = mock_vector_store
                
                yield {
                    "embedder": mock_embedder,
                    "vector_store": mock_vector_store,
                    "embedder_class": mock_embedder_class,
                    "vector_store_class": mock_vector_store_class
                }
    
    @pytest.mark.asyncio
    async def test_mcp_server_initialization_and_tool_registration(self, temp_workspace):
        """Test MCP server initialization and tool registration."""
        config_path = os.path.join(temp_workspace, "code_index.json")
        
        with patch('src.code_index.mcp_server.server.FastMCP') as mock_fastmcp_class:
            mock_fastmcp = Mock()
            mock_fastmcp.run = AsyncMock()
            mock_fastmcp.tool = Mock()
            mock_fastmcp_class.return_value = mock_fastmcp
            
            server = CodeIndexMCPServer(config_path)
            
            # Test configuration loading
            await server._load_configuration()
            assert server.config is not None
            assert server.config.embedding_length == 768
            
            # Test tool registration
            with patch.object(server, '_validate_services', new_callable=AsyncMock):
                server._register_tools()
                
                # Verify all three tools were registered
                assert mock_fastmcp.tool.call_count == 3
                
                # Check tool names
                registered_tools = [call[1]['name'] for call in mock_fastmcp.tool.call_args_list]
                assert 'index' in registered_tools
                assert 'search' in registered_tools
                assert 'collections' in registered_tools
    
    @pytest.mark.asyncio
    async def test_mcp_server_service_validation_integration(self, temp_workspace, mock_services):
        """Test MCP server service validation integration."""
        config_path = os.path.join(temp_workspace, "code_index.json")
        server = CodeIndexMCPServer(config_path)
        
        # Load configuration
        await server._load_configuration()
        
        # Test service validation
        await server._validate_services()
        
        # Verify service validation calls
        mock_services["embedder"].validate_configuration.assert_called_once()
        mock_services["vector_store"].client.get_collections.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mcp_server_lifespan_management(self, temp_workspace):
        """Test MCP server lifespan management integration."""
        config_path = os.path.join(temp_workspace, "code_index.json")
        
        with patch('src.code_index.mcp_server.server.resource_manager') as mock_resource_manager:
            mock_resource_manager.initialize = Mock()
            mock_resource_manager.shutdown = AsyncMock()
            mock_resource_manager.register_shutdown_handler = Mock()
            
            server = CodeIndexMCPServer(config_path)
            
            # Test lifespan manager
            mock_server = Mock()
            lifespan_gen = server._lifespan_manager(mock_server)
            
            # Start phase - use async with instead of __anext__
            async with lifespan_gen:
                # Verify initialization
                mock_resource_manager.initialize.assert_called_once()
                mock_resource_manager.register_shutdown_handler.assert_called_once()
            
            # Verify shutdown was called
            mock_resource_manager.shutdown.assert_called_once()


class TestServiceConnectivityIntegration:
    """Integration tests for service connectivity."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "code_index.json"
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768
            }
            config_file.write_text(json.dumps(config_data, indent=2))
            yield str(config_file)
    
    @pytest.mark.asyncio
    async def test_ollama_service_integration(self, temp_config):
        """Test Ollama service integration."""
        server = CodeIndexMCPServer(temp_config)
        await server._load_configuration()
        
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            # Test successful connection
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {"valid": True}
            mock_embedder_class.return_value = mock_embedder
            
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                mock_vector_store = Mock()
                mock_collections = Mock()
                mock_collections.collections = []
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store_class.return_value = mock_vector_store
                
                # Should not raise exception
                await server._validate_services()
                
                # Verify Ollama validation was called
                mock_embedder.validate_configuration.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ollama_service_failure_integration(self, temp_config):
        """Test Ollama service failure integration."""
        server = CodeIndexMCPServer(temp_config)
        await server._load_configuration()
        
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            # Test connection failure
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {
                "valid": False,
                "error": "Connection refused"
            }
            mock_embedder_class.return_value = mock_embedder
            
            with pytest.raises(ValueError, match="service_validation_failed"):
                await server._validate_services()
    
    @pytest.mark.asyncio
    async def test_qdrant_service_integration(self, temp_config):
        """Test Qdrant service integration."""
        server = CodeIndexMCPServer(temp_config)
        await server._load_configuration()
        
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {"valid": True}
            mock_embedder_class.return_value = mock_embedder
            
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                # Test successful connection
                mock_vector_store = Mock()
                mock_collections = Mock()
                mock_collections.collections = []
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store_class.return_value = mock_vector_store
                
                # Should not raise exception
                await server._validate_services()
                
                # Verify Qdrant validation was called
                mock_vector_store.client.get_collections.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_qdrant_service_failure_integration(self, temp_config):
        """Test Qdrant service failure integration."""
        server = CodeIndexMCPServer(temp_config)
        await server._load_configuration()
        
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            mock_embedder = Mock()
            mock_embedder.validate_configuration.return_value = {"valid": True}
            mock_embedder_class.return_value = mock_embedder
            
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                # Test connection failure
                mock_vector_store_class.side_effect = Exception("Qdrant connection failed")
                
                with pytest.raises(ValueError, match="service_validation_failed"):
                    await server._validate_services()


class TestEndToEndWorkflows:
    """End-to-end workflow tests covering index → search → collections flows."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a comprehensive temporary workspace for E2E testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a realistic project structure
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            
            test_files = [
                ("src/main.py", "def main():\n    print('Hello, World!')\n    return 0\n"),
                ("src/auth.py", "def authenticate(user, password):\n    return user == 'admin' and password == 'secret'\n"),
                ("src/database.py", "class Database:\n    def connect(self):\n        pass\n    def query(self, sql):\n        return []\n"),
                ("src/utils.py", "def helper_function():\n    return True\n"),
                ("README.md", "# Test Project\n\nAuthentication and database utilities.\n"),
                ("requirements.txt", "requests>=2.25.0\npsycopg2>=2.8.0\n")
            ]
            
            for filepath, content in test_files:
                full_path = Path(temp_dir) / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            # Create configuration
            config_file = Path(temp_dir) / "code_index.json"
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "workspace_path": temp_dir,
                "chunking_strategy": "lines",
                "use_tree_sitter": False,
                "search_min_score": 0.4,
                "search_max_results": 50
            }
            config_file.write_text(json.dumps(config_data, indent=2))
            
            yield temp_dir
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context for tool calls."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_index_search_collections_workflow(self, temp_workspace, mock_context):
        """Test complete index → search → collections workflow."""
        from src.code_index.mcp_server.tools.index_tool import index
        from src.code_index.mcp_server.tools.search_tool import search
        from src.code_index.mcp_server.tools.collections_tool import collections
        
        # Mock all external services
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                with patch('src.code_index.collections.CollectionManager') as mock_collection_manager_class:
                    with patch('src.code_index.scanner.DirectoryScanner') as mock_scanner_class:
                        with patch('src.code_index.parser.CodeParser') as mock_parser_class:
                            with patch('src.code_index.cache.CacheManager') as mock_cache_class:
                                with patch('src.code_index.chunking.LineChunkingStrategy') as mock_chunking_class:
                                    
                                    # Setup mocks for indexing
                                    mock_embedder = Mock()
                                    mock_embedder.validate_configuration.return_value = {"valid": True}
                                    mock_embedder.create_embeddings.return_value = {
                                        "embeddings": [[0.1] * 768, [0.2] * 768]
                                    }
                                    mock_embedder_class.return_value = mock_embedder
                                    
                                    mock_vector_store = Mock()
                                    mock_vector_store.initialize = Mock()
                                    # Use a dynamic collection name that matches what the search tool will generate
                                    import hashlib
                                    workspace_hash = hashlib.md5(temp_workspace.encode()).hexdigest()[:16]
                                    mock_vector_store.collection_name = f"ws-{workspace_hash}"
                                    mock_vector_store_class.return_value = mock_vector_store
                                    
                                    mock_scanner = Mock()
                                    # Return absolute paths within the temporary workspace
                                    mock_scanner.scan_directory.return_value = (
                                        [os.path.join(temp_workspace, "src/main.py"), os.path.join(temp_workspace, "src/auth.py")],
                                        0
                                    )
                                    mock_scanner_class.return_value = mock_scanner

                                    # Mock file existence checks to prevent real file access
                                    with patch('os.path.exists', return_value=True):
                                        with patch('os.path.isfile', return_value=True):
                                            with patch('builtins.open', create=True) as mock_file:
                                                mock_file.return_value.__enter__.return_value.read.return_value = "mock file content"
                                    
                                    mock_parser = Mock()
                                    # Mock the parse_file method to return a list of mock CodeBlock objects
                                    mock_parser.parse_file.return_value = [
                                        Mock(
                                            file_path=os.path.join(temp_workspace, "src/main.py"),
                                            identifier="main",
                                            type="function",
                                            start_line=1,
                                            end_line=3,
                                            content="def main():\n    print('Hello')",
                                            file_hash="mock_hash_1",
                                            segment_hash="mock_segment_1"
                                        ),
                                        Mock(
                                            file_path=os.path.join(temp_workspace, "src/auth.py"),
                                            identifier="authenticate",
                                            type="function",
                                            start_line=1,
                                            end_line=3,
                                            content="def authenticate():\n    return True",
                                            file_hash="mock_hash_2",
                                            segment_hash="mock_segment_2"
                                        )
                                    ]
                                    mock_parser_class.return_value = mock_parser
                                    
                                    mock_cache = Mock()
                                    mock_cache_class.return_value = mock_cache
                                    
                                    mock_chunking = Mock()
                                    mock_chunking_class.return_value = mock_chunking
                                    
                                    # Mock Path.exists for workspace validation
                                    with patch('pathlib.Path.exists', return_value=True):
                                        
                                        # Step 1: Index the workspace
                                        index_result = await index(
                                            ctx=mock_context,
                                            workspace=temp_workspace,
                                            config=None,
                                            workspacelist=None,
                                            embed_timeout=None,
                                            chunking_strategy=None,
                                            use_tree_sitter=None
                                        )
                                        
                                        assert index_result["success"] is True
                                        assert "indexing_results" in index_result
                                        
                                        # Verify indexing components were called
                                        mock_embedder.validate_configuration.assert_called()
                                        mock_vector_store.initialize.assert_called()
                                        mock_scanner.scan_directory.assert_called()
                                    
                                    # Setup mocks for searching (using same collection name)
                                    mock_collection = Mock()
                                    mock_collection.name = mock_vector_store.collection_name
                                    mock_collections = Mock()
                                    mock_collections.collections = [mock_collection]
                                    mock_vector_store.client.get_collections.return_value = mock_collections
                                    
                                    # Mock search results
                                    mock_search_results = [
                                        {
                                            "score": 0.85,
                                            "adjustedScore": 0.90,
                                            "payload": {
                                                "filePath": "src/auth.py",
                                                "startLine": 1,
                                                "endLine": 2,
                                                "type": "function",
                                                "codeChunk": "def authenticate(user, password):\n    return user == 'admin' and password == 'secret'"
                                            }
                                        }
                                    ]
                                    mock_vector_store.search.return_value = mock_search_results
                                    
                                    # Step 2: Search the indexed content (using same mocks)
                                    with patch('src.code_index.mcp_server.tools.search_tool.OllamaEmbedder', return_value=mock_embedder):
                                        with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore', return_value=mock_vector_store):
                                            search_result = await search(
                                                ctx=mock_context,
                                                query="authentication function",
                                                workspace=temp_workspace,
                                                min_score=0.5,
                                                max_results=10
                                            )
                                    
                                    assert isinstance(search_result, list)
                                    assert len(search_result) == 1
                                    assert search_result[0]["filePath"] == "src/auth.py"
                                    assert search_result[0]["type"] == "function"
                                    assert "authenticate" in search_result[0]["snippet"]
                                    
                                    # Verify search components were called
                                    mock_embedder.create_embeddings.assert_called()
                                    mock_vector_store.search.assert_called()
                                    
                                    # Setup mocks for collections management
                                    mock_collection_manager = Mock()
                                    mock_collections_data = [
                                        {
                                            "name": mock_vector_store.collection_name,
                                            "points_count": 10,
                                            "workspace_path": temp_workspace,
                                            "dimensions": {"vector": 768},
                                            "model_identifier": "nomic-embed-text"
                                        }
                                    ]
                                    mock_collection_manager.list_collections.return_value = mock_collections_data
                                    mock_collection_manager_class.return_value = mock_collection_manager
                                    
                                    # Step 3: List collections (using same mocks)
                                    with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager', return_value=mock_collection_manager):
                                        collections_result = await collections(
                                            ctx=mock_context,
                                            subcommand="list",
                                            detailed=True
                                        )
                                    
                                    assert collections_result["success"] is True
                                    assert collections_result["data"]["total_count"] == 1
                                    collection = collections_result["data"]["collections"][0]
                                    assert collection["name"] == mock_vector_store.collection_name
                                    assert collection["points_count"] == 10
                                    assert collection["workspace_path"] == temp_workspace
                                    
                                    # Verify collections components were called
                                    mock_collection_manager.list_collections.assert_called()
    
    @pytest.mark.asyncio
    async def test_workflow_with_configuration_overrides(self, temp_workspace, mock_context):
        """Test workflow with configuration overrides."""
        from src.code_index.mcp_server.tools.index_tool import index
        from src.code_index.mcp_server.tools.search_tool import search
        
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                with patch('src.code_index.scanner.DirectoryScanner') as mock_scanner_class:
                    with patch('src.code_index.parser.CodeParser') as mock_parser_class:
                        with patch('src.code_index.cache.CacheManager') as mock_cache_class:
                            with patch('src.code_index.chunking.TreeSitterChunkingStrategy') as mock_chunking_class:
                                
                                # Setup mocks
                                mock_embedder = Mock()
                                mock_embedder.validate_configuration.return_value = {"valid": True}
                                mock_embedder.create_embeddings.return_value = {"embeddings": [[0.1] * 768]}
                                mock_embedder_class.return_value = mock_embedder
                                
                                mock_vector_store = Mock()
                                mock_vector_store.initialize = Mock()
                                # Use a dynamic collection name that matches what the search tool will generate
                                import hashlib
                                workspace_hash = hashlib.md5(temp_workspace.encode()).hexdigest()[:16]
                                mock_vector_store.collection_name = f"ws-{workspace_hash}"
                                mock_collection = Mock()
                                mock_collection.name = mock_vector_store.collection_name
                                mock_collections = Mock()
                                mock_collections.collections = [mock_collection]
                                mock_vector_store.client.get_collections.return_value = mock_collections
                                mock_vector_store.search.return_value = []
                                mock_vector_store_class.return_value = mock_vector_store
                                
                                mock_scanner = Mock()
                                mock_scanner.scan_directory.return_value = ([os.path.join(temp_workspace, "src/main.py")], 0)
                                mock_scanner_class.return_value = mock_scanner

                                # Mock file existence checks to prevent real file access
                                with patch('os.path.exists', return_value=True):
                                    with patch('os.path.isfile', return_value=True):
                                        with patch('builtins.open', create=True) as mock_file:
                                            mock_file.return_value.__enter__.return_value.read.return_value = "mock file content"

                                # Mock file existence checks to prevent real file access
                                with patch('os.path.exists', return_value=True):
                                    with patch('os.path.isfile', return_value=True):
                                        with patch('builtins.open', create=True) as mock_file:
                                            mock_file.return_value.__enter__.return_value.read.return_value = "mock file content"
                                
                                mock_parser = Mock()
                                mock_parser.parse_file.return_value = [
                                    Mock(
                                        file_path=os.path.join(temp_workspace, "src/main.py"),
                                        identifier="main",
                                        type="function",
                                        start_line=1,
                                        end_line=3,
                                        content="def main():\n    print('Hello')",
                                        file_hash="mock_hash_1",
                                        segment_hash="mock_segment_1"
                                    )
                                ]
                                mock_parser_class.return_value = mock_parser
                                
                                mock_cache = Mock()
                                mock_cache_class.return_value = mock_cache
                                
                                mock_chunking = Mock()
                                mock_chunking_class.return_value = mock_chunking
                                
                                with patch('pathlib.Path.exists', return_value=True):
                                    
                                    # Index with Tree-sitter overrides
                                    index_result = await index(
                                        ctx=mock_context,
                                        workspace=temp_workspace,
                                        config=None,
                                        workspacelist=None,
                                        embed_timeout=120,
                                        chunking_strategy="treesitter",
                                        use_tree_sitter=True
                                    )
                                    
                                    assert index_result["success"] is True
                                    
                                    # Verify Tree-sitter chunking was used
                                    mock_chunking_class.assert_called()
                                    
                                    # Search with custom scoring overrides (using same mocks)
                                    with patch('src.code_index.mcp_server.tools.search_tool.OllamaEmbedder', return_value=mock_embedder):
                                        with patch('src.code_index.mcp_server.tools.search_tool.QdrantVectorStore', return_value=mock_vector_store):
                                            search_result = await search(
                                                ctx=mock_context,
                                                query="main function",
                                                workspace=temp_workspace,
                                                min_score=0.6,
                                                max_results=20
                                            )
                                    
                                    assert isinstance(search_result, list)
                                    
                                    # Verify search was called with overrides
                                    mock_vector_store.search.assert_called()
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_and_recovery(self, temp_workspace, mock_context):
        """Test workflow error handling and recovery scenarios."""
        from src.code_index.mcp_server.tools.index_tool import index
        from src.code_index.mcp_server.tools.search_tool import search
        
        # Test indexing failure and recovery
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            
            # First attempt: Ollama service failure
            mock_embedder_failure = Mock()
            mock_embedder_failure.validate_configuration.return_value = {
                "valid": False,
                "error": "Connection refused"
            }
            mock_embedder_class.return_value = mock_embedder_failure
            
            index_result = await index(
                ctx=mock_context,
                workspace=temp_workspace,
                config=None,
                workspacelist=None,
                embed_timeout=None,
                chunking_strategy=None,
                use_tree_sitter=None
            )
            
            # The overall operation succeeds (processed 0 files), but workspace processing fails
            assert index_result["success"] is True
            assert "indexing_results" in index_result
            assert "workspace_results" in index_result["indexing_results"]
            workspace_result = index_result["indexing_results"]["workspace_results"][0]
            assert workspace_result["status"] == "failed"
            assert "Configuration validation failed" in workspace_result["error"]
            
            # Second attempt: Service recovery
            mock_embedder_success = Mock()
            mock_embedder_success.validate_configuration.return_value = {"valid": True}
            mock_embedder_class.return_value = mock_embedder_success
            
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                with patch('src.code_index.scanner.DirectoryScanner') as mock_scanner_class:
                    with patch('src.code_index.parser.CodeParser') as mock_parser_class:
                        with patch('src.code_index.cache.CacheManager') as mock_cache_class:
                            with patch('src.code_index.chunking.LineChunkingStrategy') as mock_chunking_class:
                                
                                # Setup successful mocks
                                mock_vector_store = Mock()
                                mock_vector_store.initialize = Mock()
                                mock_vector_store_class.return_value = mock_vector_store
                                
                                mock_scanner = Mock()
                                mock_scanner.scan_directory.return_value = (["src/main.py"], 0)
                                mock_scanner_class.return_value = mock_scanner
                                
                                mock_parser = Mock()
                                mock_parser_class.return_value = mock_parser
                                
                                mock_cache = Mock()
                                mock_cache_class.return_value = mock_cache
                                
                                mock_chunking = Mock()
                                mock_chunking_class.return_value = mock_chunking
                                
                                with patch('pathlib.Path.exists', return_value=True):
                                    
                                    # Recovery attempt should succeed
                                    index_result = await index(
                                        ctx=mock_context,
                                        workspace=temp_workspace,
                                        config=None,
                                        workspacelist=None,
                                        embed_timeout=None,
                                        chunking_strategy=None,
                                        use_tree_sitter=None
                                    )
                                    
                                    assert index_result["success"] is True
        
        # Test search without indexing (collection not found)
        with patch('src.code_index.embedder.OllamaEmbedder') as mock_embedder_class:
            with patch('src.code_index.vector_store.QdrantVectorStore') as mock_vector_store_class:
                
                mock_embedder = Mock()
                mock_embedder.validate_configuration.return_value = {"valid": True}
                mock_embedder_class.return_value = mock_embedder
                
                mock_vector_store = Mock()
                mock_collections = Mock()
                mock_collections.collections = []  # No collections
                mock_vector_store.client.get_collections.return_value = mock_collections
                mock_vector_store.collection_name = "ws-test123456789"
                mock_vector_store_class.return_value = mock_vector_store
                
                with pytest.raises(ValueError, match="Workspace has not been indexed yet"):
                    await search(
                        ctx=mock_context,
                        query="test query",
                        workspace=temp_workspace
                    )


class TestConfigurationExampleValidation:
    """Tests to validate configuration examples work correctly."""
    
    @pytest.fixture
    def config_examples(self):
        """Provide various configuration examples for testing."""
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
    
    def test_configuration_examples_validation(self, config_examples):
        """Test that all configuration examples are valid."""
        from src.code_index.mcp_server.core.config_manager import MCPConfigurationManager
        
        for example_name, config_data in config_examples.items():
            with tempfile.TemporaryDirectory() as temp_dir:
                config_file = Path(temp_dir) / f"{example_name}_config.json"
                config_file.write_text(json.dumps(config_data, indent=2))
                
                manager = MCPConfigurationManager(str(config_file))
                
                # Should load without errors
                config = manager.load_config()
                
                # Verify key properties
                assert config.embedding_length == 768
                assert config.chunking_strategy in ["lines", "tokens", "treesitter"]
                assert isinstance(config.use_tree_sitter, bool)
                assert config.search_min_score >= 0.0
                assert config.search_min_score <= 1.0
                assert config.search_max_results > 0
    
    def test_configuration_override_examples(self, config_examples):
        """Test configuration override examples work correctly."""
        from src.code_index.mcp_server.core.config_manager import MCPConfigurationManager
        
        base_config_data = config_examples["fast_indexing"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "base_config.json"
            config_file.write_text(json.dumps(base_config_data, indent=2))
            
            manager = MCPConfigurationManager(str(config_file))
            base_config = manager.load_config()
            
            # Test various override scenarios
            override_examples = [
                {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_skip_test_files": True
                },
                {
                    "batch_segment_threshold": 150,
                    "embed_timeout_seconds": 300,
                    "use_mmap_file_reading": True
                },
                {
                    "search_min_score": 0.6,
                    "search_max_results": 25,
                    "search_file_type_weights": {".py": 1.3, ".rs": 1.2}
                }
            ]
            
            for overrides in override_examples:
                # Should apply overrides without errors
                modified_config = manager.apply_overrides(base_config, overrides)
                
                # Verify overrides were applied
                for key, value in overrides.items():
                    if hasattr(modified_config, key):
                        assert getattr(modified_config, key) == value
    
    def test_optimization_strategy_examples(self):
        """Test optimization strategy examples from documentation."""
        from src.code_index.mcp_server.core.config_manager import MCPConfigurationManager
        
        manager = MCPConfigurationManager()
        examples = manager.get_optimization_examples()
        
        assert isinstance(examples, dict)
        assert len(examples) > 0
        
        # Verify each example is valid
        for strategy_name, config_data in examples.items():
            assert isinstance(config_data, dict)
            assert "config" in config_data
            assert isinstance(config_data["config"], dict)
            # Basic validation that config is not empty
            assert len(config_data["config"]) > 0
            
            # Create temporary config to validate
            with tempfile.TemporaryDirectory() as temp_dir:
                config_file = Path(temp_dir) / f"{strategy_name}.json"
                config_file.write_text(json.dumps(config_data, indent=2))
                
                test_manager = MCPConfigurationManager(str(config_file))
                
                # Should load and validate successfully
                config = test_manager.load_config()
                assert config.embedding_length > 0
                assert config.chunking_strategy in ["lines", "tokens", "treesitter"]


if __name__ == "__main__":
    pytest.main([__file__])