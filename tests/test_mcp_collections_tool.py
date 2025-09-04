"""
Unit tests for MCP Collections Tool.

Tests the collections tool functionality including parameter validation,
safety confirmations, and collection management operations.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.code_index.mcp_server.tools.collections_tool import (
    collections,
    create_collections_tool_description,
    _handle_list_collections,
    _handle_collection_info,
    _handle_delete_collection,
    _handle_prune_collections,
    _handle_clear_all_collections,
    _request_confirmation,
    _resolve_canonical_id_for_delete
)
from src.code_index.config import Config
from src.code_index.collections import CollectionManager


class TestCollectionsTool:
    """Test cases for the collections tool function."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        return Mock()
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config file
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
    async def test_collections_tool_missing_subcommand(self, mock_context):
        """Test collections tool with missing subcommand parameter."""
        with pytest.raises(ValueError, match="subcommand parameter is required"):
            await collections(
                ctx=mock_context,
                subcommand="",  # Empty subcommand
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_invalid_subcommand_type(self, mock_context):
        """Test collections tool with invalid subcommand type."""
        with pytest.raises(ValueError, match="subcommand parameter is required"):
            await collections(
                ctx=mock_context,
                subcommand=None,  # None subcommand
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_invalid_subcommand(self, mock_context):
        """Test collections tool with invalid subcommand."""
        with pytest.raises(ValueError, match="Invalid subcommand"):
            await collections(
                ctx=mock_context,
                subcommand="invalid_command"
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_info_missing_collection_name(self, mock_context):
        """Test collections tool info subcommand without collection name."""
        with pytest.raises(ValueError, match="collection_name parameter is required"):
            await collections(
                ctx=mock_context,
                subcommand="info",
                collection_name=None
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_delete_missing_collection_name(self, mock_context):
        """Test collections tool delete subcommand without collection name."""
        with pytest.raises(ValueError, match="collection_name parameter is required"):
            await collections(
                ctx=mock_context,
                subcommand="delete",
                collection_name=""
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_prune_invalid_days(self, mock_context):
        """Test collections tool prune subcommand with invalid days."""
        with pytest.raises(ValueError, match="older_than_days must be a positive integer"):
            await collections(
                ctx=mock_context,
                subcommand="prune",
                older_than_days=-5
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_invalid_boolean_parameters(self, mock_context):
        """Test collections tool with invalid boolean parameters."""
        with pytest.raises(ValueError, match="yes parameter must be a boolean"):
            await collections(
                ctx=mock_context,
                subcommand="list",
                yes="not_a_boolean"
            )
        
        with pytest.raises(ValueError, match="detailed parameter must be a boolean"):
            await collections(
                ctx=mock_context,
                subcommand="list",
                detailed="not_a_boolean"
            )
    
    @pytest.mark.asyncio
    async def test_collections_tool_configuration_error(self, mock_context):
        """Test collections tool with configuration loading error."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            mock_config_manager = Mock()
            mock_config_manager.load_config.side_effect = ValueError("Config error")
            mock_config_manager_class.return_value = mock_config_manager
            
            with pytest.raises(ValueError, match="Configuration error"):
                await collections(
                    ctx=mock_context,
                    subcommand="list"
                )
    
    @pytest.mark.asyncio
    async def test_collections_tool_collection_manager_failure(self, mock_context):
        """Test collections tool with collection manager initialization failure."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                
                # Mock successful config loading
                mock_config_manager = Mock()
                mock_config_manager.load_config.return_value = Config()
                mock_config_manager_class.return_value = mock_config_manager
                
                # Mock collection manager failure
                mock_collection_manager_class.side_effect = Exception("Manager init failed")
                
                with pytest.raises(Exception, match="Failed to initialize collection manager"):
                    await collections(
                        ctx=mock_context,
                        subcommand="list"
                    )
    
    @pytest.mark.asyncio
    async def test_collections_tool_list_success(self, mock_context):
        """Test successful collections list operation."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                
                # Mock successful config loading
                mock_config_manager = Mock()
                mock_config_manager.load_config.return_value = Config()
                mock_config_manager_class.return_value = mock_config_manager
                
                # Mock collection manager with collections
                mock_collection_manager = Mock()
                mock_collections_data = [
                    {
                        "name": "ws-abc123def456",
                        "points_count": 100,
                        "workspace_path": "/test/workspace1",
                        "dimensions": {"vector": 768},
                        "model_identifier": "nomic-embed-text"
                    },
                    {
                        "name": "ws-def456ghi789",
                        "points_count": 50,
                        "workspace_path": "/test/workspace2",
                        "dimensions": {"vector": 768},
                        "model_identifier": "nomic-embed-text"
                    }
                ]
                mock_collection_manager.list_collections.return_value = mock_collections_data
                mock_collection_manager_class.return_value = mock_collection_manager
                
                result = await collections(
                    ctx=mock_context,
                    subcommand="list"
                )
                
                assert result["success"] is True
                assert "data" in result
                assert result["data"]["total_count"] == 2
                assert len(result["data"]["collections"]) == 2
                
                # Check first collection
                first_collection = result["data"]["collections"][0]
                assert first_collection["name"] == "ws-abc123def456"
                assert first_collection["points_count"] == 100
                assert first_collection["workspace_path"] == "/test/workspace1"
    
    @pytest.mark.asyncio
    async def test_collections_tool_list_empty(self, mock_context):
        """Test collections list with no collections."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                
                # Mock successful config loading
                mock_config_manager = Mock()
                mock_config_manager.load_config.return_value = Config()
                mock_config_manager_class.return_value = mock_config_manager
                
                # Mock collection manager with no collections
                mock_collection_manager = Mock()
                mock_collection_manager.list_collections.return_value = []
                mock_collection_manager_class.return_value = mock_collection_manager
                
                result = await collections(
                    ctx=mock_context,
                    subcommand="list"
                )
                
                assert result["success"] is True
                assert result["data"]["total_count"] == 0
                assert len(result["data"]["collections"]) == 0
                assert "No collections found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_collections_tool_info_success(self, mock_context):
        """Test successful collections info operation."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                
                # Mock successful config loading
                mock_config_manager = Mock()
                mock_config_manager.load_config.return_value = Config()
                mock_config_manager_class.return_value = mock_config_manager
                
                # Mock collection manager with collection info
                mock_collection_manager = Mock()
                mock_collection_info = {
                    "name": "ws-abc123def456",
                    "status": "green",
                    "points_count": 100,
                    "vectors_count": 100,
                    "workspace_path": "/test/workspace",
                    "dimensions": {"vector": 768},
                    "model_identifier": "nomic-embed-text",
                    "config": "test_config"
                }
                mock_collection_manager.get_collection_info.return_value = mock_collection_info
                mock_collection_manager_class.return_value = mock_collection_manager
                
                result = await collections(
                    ctx=mock_context,
                    subcommand="info",
                    collection_name="ws-abc123def456"
                )
                
                assert result["success"] is True
                assert "data" in result
                collection_data = result["data"]["collection"]
                assert collection_data["name"] == "ws-abc123def456"
                assert collection_data["points_count"] == 100
                assert collection_data["workspace_path"] == "/test/workspace"
    
    @pytest.mark.asyncio
    async def test_collections_tool_info_not_found(self, mock_context):
        """Test collections info with collection not found."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                
                # Mock successful config loading
                mock_config_manager = Mock()
                mock_config_manager.load_config.return_value = Config()
                mock_config_manager_class.return_value = mock_config_manager
                
                # Mock collection manager with not found error
                mock_collection_manager = Mock()
                mock_collection_manager.get_collection_info.side_effect = Exception("Collection not found")
                mock_collection_manager_class.return_value = mock_collection_manager
                
                with pytest.raises(ValueError, match="Collection .* not found"):
                    await collections(
                        ctx=mock_context,
                        subcommand="info",
                        collection_name="nonexistent"
                    )
    
    @pytest.mark.asyncio
    async def test_collections_tool_delete_with_confirmation_bypass(self, mock_context):
        """Test collections delete with confirmation bypass."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                with patch('src.code_index.cache.delete_collection_cache') as mock_delete_cache:
                    
                    # Mock successful config loading
                    mock_config_manager = Mock()
                    config = Config()
                    mock_config_manager.load_config.return_value = config
                    mock_config_manager_class.return_value = mock_config_manager
                    
                    # Mock collection manager
                    mock_collection_manager = Mock()
                    mock_collection_info = {
                        "name": "ws-abc123def456",
                        "points_count": 100,
                        "workspace_path": "/test/workspace"
                    }
                    mock_collection_manager.get_collection_info.return_value = mock_collection_info
                    mock_collection_manager.delete_collection.return_value = True
                    mock_collection_manager_class.return_value = mock_collection_manager
                    
                    # Mock cache deletion
                    mock_delete_cache.return_value = 5
                    
                    result = await collections(
                        ctx=mock_context,
                        subcommand="delete",
                        collection_name="ws-abc123def456",
                        yes=True  # Bypass confirmation
                    )
                    
                    assert result["success"] is True
                    assert result["data"]["collection_name"] == "ws-abc123def456"
                    assert result["data"]["points_deleted"] == 100
                    assert result["data"]["cache_files_removed"] == 5
                    
                    # Verify deletion was called
                    mock_collection_manager.delete_collection.assert_called_once_with("ws-abc123def456")
    
    @pytest.mark.asyncio
    async def test_collections_tool_delete_with_confirmation_denied(self, mock_context):
        """Test collections delete with confirmation denied."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                with patch('src.code_index.mcp_server.tools.collections_tool._request_confirmation') as mock_request_confirmation:
                    
                    # Mock successful config loading
                    mock_config_manager = Mock()
                    mock_config_manager.load_config.return_value = Config()
                    mock_config_manager_class.return_value = mock_config_manager
                    
                    # Mock collection manager
                    mock_collection_manager = Mock()
                    mock_collection_info = {
                        "name": "ws-abc123def456",
                        "points_count": 100,
                        "workspace_path": "/test/workspace"
                    }
                    mock_collection_manager.get_collection_info.return_value = mock_collection_info
                    mock_collection_manager_class.return_value = mock_collection_manager
                    
                    # Mock confirmation denial
                    mock_request_confirmation.return_value = {
                        "confirmed": False,
                        "reason": "User declined"
                    }
                    
                    result = await collections(
                        ctx=mock_context,
                        subcommand="delete",
                        collection_name="ws-abc123def456",
                        yes=False  # Require confirmation
                    )
                    
                    assert result["success"] is False
                    assert "cancelled by user" in result["message"]
                    assert result["data"]["cancelled"] is True
                    
                    # Verify deletion was NOT called
                    mock_collection_manager.delete_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_collections_tool_clear_all_success(self, mock_context):
        """Test successful clear-all operation."""
        with patch('src.code_index.mcp_server.tools.collections_tool.MCPConfigurationManager') as mock_config_manager_class:
            with patch('src.code_index.mcp_server.tools.collections_tool.CollectionManager') as mock_collection_manager_class:
                with patch('src.code_index.cache.clear_all_caches') as mock_clear_caches:
                    
                    # Mock successful config loading
                    mock_config_manager = Mock()
                    config = Config()
                    mock_config_manager.load_config.return_value = config
                    mock_config_manager_class.return_value = mock_config_manager
                    
                    # Mock collection manager
                    mock_collection_manager = Mock()
                    mock_collections_list = [
                        {"name": "ws-abc123def456", "points_count": 100},
                        {"name": "ws-def456ghi789", "points_count": 50}
                    ]
                    mock_collection_manager.list_collections.return_value = mock_collections_list
                    mock_collection_manager.delete_collection.return_value = True
                    mock_collection_manager_class.return_value = mock_collection_manager
                    
                    # Mock cache clearing
                    mock_clear_caches.return_value = 10
                    
                    result = await collections(
                        ctx=mock_context,
                        subcommand="clear-all",
                        yes=True  # Bypass confirmation
                    )
                    
                    assert result["success"] is True
                    assert result["data"]["total_collections"] == 2
                    assert result["data"]["success_count"] == 2
                    assert result["data"]["failure_count"] == 0
                    assert result["data"]["cache_files_removed"] == 10
                    
                    # Verify all collections were deleted
                    assert mock_collection_manager.delete_collection.call_count == 2


class TestCollectionsToolHelpers:
    """Test cases for collections tool helper functions."""
    
    @pytest.fixture
    def mock_collection_manager(self):
        """Create a mock collection manager."""
        return Mock(spec=CollectionManager)
    
    @pytest.mark.asyncio
    async def test_handle_list_collections_success(self, mock_collection_manager):
        """Test successful list collections handling."""
        mock_collections_data = [
            {
                "name": "ws-abc123def456",
                "points_count": 100,
                "workspace_path": "/test/workspace1",
                "dimensions": {"vector": 768},
                "model_identifier": "nomic-embed-text"
            }
        ]
        mock_collection_manager.list_collections.return_value = mock_collections_data
        
        result = await _handle_list_collections(mock_collection_manager, detailed=False)
        
        assert result["success"] is True
        assert result["data"]["total_count"] == 1
        assert len(result["data"]["collections"]) == 1
        assert result["data"]["detailed"] is False
    
    @pytest.mark.asyncio
    async def test_handle_list_collections_detailed(self, mock_collection_manager):
        """Test list collections with detailed information."""
        mock_collections_data = [
            {
                "name": "ws-abc123def456",
                "points_count": 100,
                "workspace_path": "/test/workspace1",
                "dimensions": {"vector": 768},
                "model_identifier": "nomic-embed-text",
                "vectors_count": 100,
                "status": "green"
            }
        ]
        mock_collection_manager.list_collections.return_value = mock_collections_data
        
        result = await _handle_list_collections(mock_collection_manager, detailed=True)
        
        assert result["success"] is True
        assert result["data"]["detailed"] is True
        
        collection = result["data"]["collections"][0]
        assert "vectors_count" in collection
        assert "status" in collection
    
    @pytest.mark.asyncio
    async def test_handle_list_collections_empty(self, mock_collection_manager):
        """Test list collections with no collections."""
        mock_collection_manager.list_collections.return_value = []
        
        result = await _handle_list_collections(mock_collection_manager, detailed=False)
        
        assert result["success"] is True
        assert result["data"]["total_count"] == 0
        assert "No collections found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_collection_info_success(self, mock_collection_manager):
        """Test successful collection info handling."""
        mock_collection_info = {
            "name": "ws-abc123def456",
            "status": "green",
            "points_count": 100,
            "workspace_path": "/test/workspace"
        }
        mock_collection_manager.get_collection_info.return_value = mock_collection_info
        
        result = await _handle_collection_info(mock_collection_manager, "ws-abc123def456")
        
        assert result["success"] is True
        assert result["data"]["collection"]["name"] == "ws-abc123def456"
        assert result["data"]["collection"]["points_count"] == 100
    
    @pytest.mark.asyncio
    async def test_handle_collection_info_not_found(self, mock_collection_manager):
        """Test collection info with not found error."""
        mock_collection_manager.get_collection_info.side_effect = Exception("Collection not found")
        
        with pytest.raises(ValueError, match="Collection .* not found"):
            await _handle_collection_info(mock_collection_manager, "nonexistent")
    
    @pytest.mark.asyncio
    async def test_handle_delete_collection_success(self, mock_collection_manager):
        """Test successful collection deletion."""
        mock_context = Mock()
        config = Config()
        
        mock_collection_info = {
            "name": "ws-abc123def456",
            "points_count": 100,
            "workspace_path": "/test/workspace"
        }
        mock_collection_manager.get_collection_info.return_value = mock_collection_info
        mock_collection_manager.delete_collection.return_value = True
        
        with patch('src.code_index.cache.delete_collection_cache', return_value=5):
            result = await _handle_delete_collection(
                mock_context, mock_collection_manager, "ws-abc123def456", True, config
            )
        
        assert result["success"] is True
        assert result["data"]["collection_name"] == "ws-abc123def456"
        assert result["data"]["cache_files_removed"] == 5
    
    @pytest.mark.asyncio
    async def test_handle_prune_collections_success(self, mock_collection_manager):
        """Test successful collections pruning."""
        mock_context = Mock()
        
        mock_collection_manager.prune_old_collections.return_value = []  # No collections pruned
        
        result = await _handle_prune_collections(mock_context, mock_collection_manager, 30, True)
        
        assert result["success"] is True
        assert result["data"]["total_pruned"] == 0
        assert "No collections found older than" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_clear_all_collections_success(self, mock_collection_manager):
        """Test successful clear-all collections."""
        mock_context = Mock()
        config = Config()
        
        mock_collections_list = [
            {"name": "ws-abc123def456", "points_count": 100},
            {"name": "ws-def456ghi789", "points_count": 50}
        ]
        mock_collection_manager.list_collections.return_value = mock_collections_list
        mock_collection_manager.delete_collection.return_value = True
        
        with patch('src.code_index.cache.clear_all_caches', return_value=10):
            result = await _handle_clear_all_collections(mock_context, mock_collection_manager, True, config)
        
        assert result["success"] is True
        assert result["data"]["success_count"] == 2
        assert result["data"]["failure_count"] == 0
        assert result["data"]["cache_files_removed"] == 10
    
    @pytest.mark.asyncio
    async def test_request_confirmation_accepted(self):
        """Test confirmation request with acceptance."""
        mock_context = Mock()
        
        # Mock AcceptedElicitation
        from fastmcp import AcceptedElicitation
        mock_elicit_result = AcceptedElicitation(value="yes")
        mock_context.elicit = AsyncMock(return_value=mock_elicit_result)
        
        result = await _request_confirmation(mock_context, "Delete?", "This will delete everything.")
        
        assert result["confirmed"] is True
        assert "confirmed" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_request_confirmation_declined_response(self):
        """Test confirmation request with declined response."""
        mock_context = Mock()
        
        # Mock AcceptedElicitation with "no"
        from fastmcp import AcceptedElicitation
        mock_elicit_result = AcceptedElicitation(value="no")
        mock_context.elicit = AsyncMock(return_value=mock_elicit_result)
        
        result = await _request_confirmation(mock_context, "Delete?", "This will delete everything.")
        
        assert result["confirmed"] is False
        assert "declined" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_request_confirmation_declined_elicitation(self):
        """Test confirmation request with declined elicitation."""
        mock_context = Mock()
        
        # Mock DeclinedElicitation
        from fastmcp import DeclinedElicitation
        mock_elicit_result = DeclinedElicitation()
        mock_context.elicit = AsyncMock(return_value=mock_elicit_result)
        
        result = await _request_confirmation(mock_context, "Delete?", "This will delete everything.")
        
        assert result["confirmed"] is False
        assert "declined to provide confirmation" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_request_confirmation_cancelled(self):
        """Test confirmation request with cancellation."""
        mock_context = Mock()
        
        # Mock CancelledElicitation
        from fastmcp import CancelledElicitation
        mock_elicit_result = CancelledElicitation()
        mock_context.elicit = AsyncMock(return_value=mock_elicit_result)
        
        result = await _request_confirmation(mock_context, "Delete?", "This will delete everything.")
        
        assert result["confirmed"] is False
        assert "cancelled" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_request_confirmation_error(self):
        """Test confirmation request with error."""
        mock_context = Mock()
        mock_context.elicit = AsyncMock(side_effect=Exception("Elicit failed"))
        
        result = await _request_confirmation(mock_context, "Delete?", "This will delete everything.")
        
        assert result["confirmed"] is False
        assert "failed" in result["reason"]
    
    def test_resolve_canonical_id_for_delete_from_name(self):
        """Test resolving canonical ID from collection name."""
        mock_collection_manager = Mock()
        
        # Test with valid ws- pattern
        result = _resolve_canonical_id_for_delete(mock_collection_manager, "ws-abc123def456789")
        assert result == "abc123def456789"
        
        # Test with invalid pattern
        result = _resolve_canonical_id_for_delete(mock_collection_manager, "invalid-name")
        assert result is None
    
    def test_resolve_canonical_id_for_delete_from_payload(self):
        """Test resolving canonical ID from collection payload."""
        mock_collection_manager = Mock()
        
        # Mock scroll response with payload containing collection_id
        mock_point = Mock()
        mock_point.payload = {"collection_id": "abc123def456789"}
        mock_scroll_result = ([mock_point], None)
        mock_collection_manager.client.scroll.return_value = mock_scroll_result
        
        result = _resolve_canonical_id_for_delete(mock_collection_manager, "some-collection")
        assert result == "abc123def456789"
    
    def test_resolve_canonical_id_for_delete_scroll_error(self):
        """Test resolving canonical ID with scroll error."""
        mock_collection_manager = Mock()
        mock_collection_manager.client.scroll.side_effect = Exception("Scroll failed")
        
        # Should fall back to name-based resolution
        result = _resolve_canonical_id_for_delete(mock_collection_manager, "ws-abc123def456789")
        assert result == "abc123def456789"


class TestCollectionsToolDescription:
    """Test cases for collections tool description generation."""
    
    def test_create_collections_tool_description(self):
        """Test collections tool description creation."""
        description = create_collections_tool_description()
        
        assert isinstance(description, str)
        assert len(description) > 100  # Should be comprehensive
        
        # Check for key sections
        assert "SAFETY WARNING" in description
        assert "Usage Examples:" in description
        assert "Subcommands:" in description
        assert "Parameters:" in description
        assert "Safety Measures:" in description
        assert "Collection Information:" in description
        assert "Common Error Solutions:" in description
        assert "Returns:" in description
        
        # Check for subcommands
        assert "list:" in description
        assert "info:" in description
        assert "delete:" in description
        assert "prune:" in description
        assert "clear-all:" in description
        
        # Check for parameters
        assert "subcommand" in description
        assert "collection_name" in description
        assert "older_than_days" in description
        assert "yes" in description
        assert "detailed" in description
        
        # Check for safety measures
        assert "destructive operations" in description
        assert "confirmation" in description
        assert "yes=true" in description
        
        # Check for examples
        assert "collections(subcommand=" in description
        assert '"list"' in description
        assert '"delete"' in description


if __name__ == "__main__":
    pytest.main([__file__])