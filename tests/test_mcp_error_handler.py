"""
Unit tests for MCP Error Handler.

Tests error handling functionality including structured error responses,
actionable guidance generation, and error categorization.
"""

import pytest
from unittest.mock import Mock, patch

from src.code_index.mcp_server.core.error_handler import error_handler


class TestErrorHandler:
    """Test cases for the error handler functionality."""
    
    def test_handle_configuration_error_basic(self):
        """Test basic configuration error handling."""
        error = ValueError("embedding_length is required")
        context = {"config_file": "code_index.json"}
        
        result = error_handler.handle_configuration_error(error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "configuration_error"
        assert "embedding_length is required" in result["message"]
        assert result["context"]["config_file"] == "code_index.json"
        assert len(result["actionable_guidance"]) > 0
    
    def test_handle_configuration_error_missing_embedding_length(self):
        """Test configuration error for missing embedding_length."""
        error = ValueError("embedding_length must be set in configuration")
        context = {"config_file": "code_index.json"}
        
        result = error_handler.handle_configuration_error(error, context)
        
        assert result["error_type"] == "configuration_error"
        assert "embedding_length" in result["message"]
        
        # Should provide specific guidance for embedding_length
        guidance = result["actionable_guidance"]
        assert any("embedding_length" in g for g in guidance)
        assert any("nomic-embed-text" in g for g in guidance)
    
    def test_handle_configuration_error_invalid_chunking_strategy(self):
        """Test configuration error for invalid chunking strategy."""
        error = ValueError("chunking_strategy must be one of ['lines', 'tokens', 'treesitter']")
        context = {"config_file": "code_index.json", "current_value": "invalid"}
        
        result = error_handler.handle_configuration_error(error, context)
        
        assert result["error_type"] == "configuration_error"
        assert "chunking_strategy" in result["message"]
        
        # Should provide guidance about valid strategies
        guidance = result["actionable_guidance"]
        assert any("chunking_strategy" in g for g in guidance)
        assert any("lines" in g or "tokens" in g or "treesitter" in g for g in guidance)
    
    def test_handle_service_connection_error_ollama(self):
        """Test service connection error for Ollama."""
        error = Exception("Connection refused")
        context = {
            "base_url": "http://localhost:11434",
            "model": "nomic-embed-text:latest"
        }
        
        result = error_handler.handle_service_connection_error("Ollama", error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "service_connection_error"
        assert result["service"] == "Ollama"
        assert "Connection refused" in result["message"]
        assert result["context"]["base_url"] == "http://localhost:11434"
        
        # Should provide Ollama-specific guidance
        guidance = result["actionable_guidance"]
        assert any("Ollama" in g for g in guidance)
        assert any("running" in g.lower() for g in guidance)
    
    def test_handle_service_connection_error_qdrant(self):
        """Test service connection error for Qdrant."""
        error = Exception("Connection timeout")
        context = {
            "qdrant_url": "http://localhost:6333",
            "api_key": "test_key"
        }
        
        result = error_handler.handle_service_connection_error("Qdrant", error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "service_connection_error"
        assert result["service"] == "Qdrant"
        assert "Connection timeout" in result["message"]
        
        # Should provide Qdrant-specific guidance
        guidance = result["actionable_guidance"]
        assert any("Qdrant" in g for g in guidance)
        assert any("6333" in g or "port" in g.lower() for g in guidance)
    
    def test_handle_operation_error_indexing(self):
        """Test operation error during indexing."""
        error = Exception("File processing failed")
        context = {
            "operation": "indexing",
            "workspace": "/test/workspace",
            "file": "problematic_file.py"
        }
        
        result = error_handler.handle_operation_error(error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "operation_error"
        assert "File processing failed" in result["message"]
        assert result["context"]["operation"] == "indexing"
        assert result["context"]["workspace"] == "/test/workspace"
        
        # Should provide operation-specific guidance
        guidance = result["actionable_guidance"]
        assert any("indexing" in g.lower() for g in guidance)
    
    def test_handle_operation_error_search(self):
        """Test operation error during search."""
        error = Exception("Vector search failed")
        context = {
            "operation": "search",
            "query": "test query",
            "collection": "test_collection"
        }
        
        result = error_handler.handle_operation_error(error, context)
        
        assert result["error_type"] == "operation_error"
        assert "Vector search failed" in result["message"]
        assert result["context"]["operation"] == "search"
        
        # Should provide search-specific guidance
        guidance = result["actionable_guidance"]
        assert any("search" in g.lower() for g in guidance)
    
    def test_handle_validation_error_parameter(self):
        """Test validation error for parameters."""
        error = ValueError("min_score must be between 0 and 1")
        context = {
            "parameter": "min_score",
            "value": 1.5,
            "valid_range": "0.0-1.0"
        }
        
        result = error_handler.handle_validation_error(error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "min_score must be between 0 and 1" in result["message"]
        assert result["context"]["parameter"] == "min_score"
        
        # Should provide parameter-specific guidance
        guidance = result["actionable_guidance"]
        assert any("min_score" in g for g in guidance)
        assert any("0" in g and "1" in g for g in guidance)
    
    def test_handle_validation_error_workspace(self):
        """Test validation error for workspace."""
        error = ValueError("Workspace path does not exist")
        context = {
            "parameter": "workspace",
            "value": "/nonexistent/path"
        }
        
        result = error_handler.handle_validation_error(error, context)
        
        assert result["error_type"] == "validation_error"
        assert "Workspace path does not exist" in result["message"]
        
        # Should provide workspace-specific guidance
        guidance = result["actionable_guidance"]
        assert any("workspace" in g.lower() for g in guidance)
        assert any("path" in g.lower() for g in guidance)
    
    def test_handle_safety_error_destructive_operation(self):
        """Test safety error for destructive operations."""
        error = Exception("Operation requires confirmation")
        context = {
            "operation": "delete",
            "target": "all collections",
            "confirmation_required": True
        }
        
        result = error_handler.handle_safety_error(error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "safety_error"
        assert "Operation requires confirmation" in result["message"]
        assert result["context"]["operation"] == "delete"
        
        # Should provide safety-specific guidance
        guidance = result["actionable_guidance"]
        assert any("confirmation" in g.lower() for g in guidance)
        assert any("yes=true" in g for g in guidance)
    
    def test_handle_safety_error_resource_exhaustion(self):
        """Test safety error for resource exhaustion."""
        error = Exception("Memory limit exceeded")
        context = {
            "operation": "indexing",
            "memory_usage": "8GB",
            "limit": "4GB"
        }
        
        result = error_handler.handle_safety_error(error, context)
        
        assert result["error_type"] == "safety_error"
        assert "Memory limit exceeded" in result["message"]
        
        # Should provide resource management guidance
        guidance = result["actionable_guidance"]
        assert any("memory" in g.lower() for g in guidance)
    
    def test_handle_unknown_error(self):
        """Test handling of unknown/unexpected errors."""
        error = RuntimeError("Unexpected system error")
        context = {"component": "mcp_server"}
        
        result = error_handler.handle_unknown_error(error, context)
        
        assert result["error"] is True
        assert result["error_type"] == "unknown_error"
        assert "Unexpected system error" in result["message"]
        assert result["context"]["component"] == "mcp_server"
        
        # Should provide general guidance
        guidance = result["actionable_guidance"]
        assert len(guidance) > 0
        assert any("support" in g.lower() or "documentation" in g.lower() for g in guidance)
    
    def test_generate_actionable_guidance_configuration(self):
        """Test actionable guidance generation for configuration errors."""
        error_type = "configuration_error"
        message = "embedding_length must be set"
        context = {"config_file": "code_index.json"}
        
        guidance = error_handler._generate_actionable_guidance(error_type, message, context)
        
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        assert any("embedding_length" in g for g in guidance)
        assert any("code_index.json" in g for g in guidance)
    
    def test_generate_actionable_guidance_service_connection(self):
        """Test actionable guidance generation for service connection errors."""
        error_type = "service_connection_error"
        message = "Ollama connection failed"
        context = {"service": "Ollama", "base_url": "http://localhost:11434"}
        
        guidance = error_handler._generate_actionable_guidance(error_type, message, context)
        
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        assert any("Ollama" in g for g in guidance)
        assert any("11434" in g for g in guidance)
    
    def test_generate_actionable_guidance_operation_error(self):
        """Test actionable guidance generation for operation errors."""
        error_type = "operation_error"
        message = "Indexing failed"
        context = {"operation": "indexing", "workspace": "/test"}
        
        guidance = error_handler._generate_actionable_guidance(error_type, message, context)
        
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        assert any("indexing" in g.lower() for g in guidance)
    
    def test_generate_actionable_guidance_validation_error(self):
        """Test actionable guidance generation for validation errors."""
        error_type = "validation_error"
        message = "Invalid parameter value"
        context = {"parameter": "min_score", "value": 1.5}
        
        guidance = error_handler._generate_actionable_guidance(error_type, message, context)
        
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        assert any("min_score" in g for g in guidance)
    
    def test_generate_actionable_guidance_safety_error(self):
        """Test actionable guidance generation for safety errors."""
        error_type = "safety_error"
        message = "Confirmation required"
        context = {"operation": "delete"}
        
        guidance = error_handler._generate_actionable_guidance(error_type, message, context)
        
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        assert any("confirmation" in g.lower() for g in guidance)
    
    def test_generate_actionable_guidance_unknown_error(self):
        """Test actionable guidance generation for unknown errors."""
        error_type = "unknown_error"
        message = "Unexpected error"
        context = {}
        
        guidance = error_handler._generate_actionable_guidance(error_type, message, context)
        
        assert isinstance(guidance, list)
        assert len(guidance) > 0
        # Should provide general guidance
        assert any("documentation" in g.lower() or "support" in g.lower() for g in guidance)
    
    def test_categorize_error_configuration(self):
        """Test error categorization for configuration errors."""
        error = ValueError("embedding_length is required")
        
        category = error_handler._categorize_error(error, {})
        
        assert category == "configuration_error"
    
    def test_categorize_error_validation(self):
        """Test error categorization for validation errors."""
        error = ValueError("min_score must be between 0 and 1")
        
        category = error_handler._categorize_error(error, {"parameter": "min_score"})
        
        assert category == "validation_error"
    
    def test_categorize_error_operation(self):
        """Test error categorization for operation errors."""
        error = Exception("File processing failed")
        
        category = error_handler._categorize_error(error, {"operation": "indexing"})
        
        assert category == "operation_error"
    
    def test_categorize_error_safety(self):
        """Test error categorization for safety errors."""
        error = Exception("Confirmation required")
        
        category = error_handler._categorize_error(error, {"confirmation_required": True})
        
        assert category == "safety_error"
    
    def test_categorize_error_unknown(self):
        """Test error categorization for unknown errors."""
        error = RuntimeError("Unexpected error")
        
        category = error_handler._categorize_error(error, {})
        
        assert category == "unknown_error"
    
    def test_format_error_response_complete(self):
        """Test complete error response formatting."""
        error_type = "configuration_error"
        message = "embedding_length is required"
        context = {"config_file": "code_index.json"}
        guidance = ["Set embedding_length in configuration", "Use 768 for nomic-embed-text"]
        
        response = error_handler._format_error_response(error_type, message, context, guidance)
        
        assert response["error"] is True
        assert response["error_type"] == "configuration_error"
        assert response["message"] == "embedding_length is required"
        assert response["context"] == context
        assert response["actionable_guidance"] == guidance
        assert "timestamp" in response
    
    def test_format_error_response_minimal(self):
        """Test minimal error response formatting."""
        error_type = "unknown_error"
        message = "Something went wrong"
        
        response = error_handler._format_error_response(error_type, message, {}, [])
        
        assert response["error"] is True
        assert response["error_type"] == "unknown_error"
        assert response["message"] == "Something went wrong"
        assert response["context"] == {}
        assert response["actionable_guidance"] == []
        assert "timestamp" in response
    
    def test_error_handler_integration_configuration(self):
        """Test complete error handling workflow for configuration error."""
        error = ValueError("embedding_length must be set in configuration")
        context = {"config_file": "code_index.json"}
        
        result = error_handler.handle_configuration_error(error, context)
        
        # Verify complete response structure
        assert "error" in result
        assert "error_type" in result
        assert "message" in result
        assert "context" in result
        assert "actionable_guidance" in result
        assert "timestamp" in result
        
        # Verify content quality
        assert result["error"] is True
        assert result["error_type"] == "configuration_error"
        assert len(result["actionable_guidance"]) > 0
        assert all(isinstance(g, str) for g in result["actionable_guidance"])
    
    def test_error_handler_integration_service_connection(self):
        """Test complete error handling workflow for service connection error."""
        error = Exception("Connection refused")
        context = {"base_url": "http://localhost:11434", "model": "nomic-embed-text"}
        
        result = error_handler.handle_service_connection_error("Ollama", error, context)
        
        # Verify complete response structure
        assert all(key in result for key in ["error", "error_type", "message", "context", "actionable_guidance", "timestamp"])
        
        # Verify service-specific content
        assert result["service"] == "Ollama"
        assert "Ollama" in str(result["actionable_guidance"])
    
    def test_error_handler_thread_safety(self):
        """Test error handler thread safety with concurrent calls."""
        import threading
        import time
        
        results = []
        
        def handle_error(i):
            error = ValueError(f"Test error {i}")
            context = {"test_id": i}
            result = error_handler.handle_configuration_error(error, context)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=handle_error, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all results are correct and unique
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result["error"] is True
            assert result["error_type"] == "configuration_error"
            assert f"Test error {i}" in result["message"]
            assert result["context"]["test_id"] == i


if __name__ == "__main__":
    pytest.main([__file__])