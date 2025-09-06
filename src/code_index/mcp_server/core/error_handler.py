"""
Structured Error Handling System for MCP Server
"""

import logging
from datetime import datetime
from typing import Dict, Any, List


class MCPErrorHandler:
    """Centralized error handling system for the MCP server."""
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = logging.getLogger(__name__)
    
    def handle_configuration_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle configuration-related errors."""
        context = context or {}
        message = str(error)
        guidance = self._generate_actionable_guidance("configuration_error", message, context)

        return self._format_error_response("configuration_error", message, context, guidance)
    
    def handle_service_connection_error(self, service: str, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle service connection errors."""
        context = context or {}
        context["service"] = service
        message = f"{service} service connection failed: {error}"
        guidance = self._generate_actionable_guidance("service_connection_error", message, context)

        response = self._format_error_response("service_connection_error", message, context, guidance)
        response["service"] = service  # Add service field that's specific to this error type
        return response
    
    def handle_operation_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle operation-specific errors."""
        context = context or {}
        message = f"Operation failed: {error}"
        guidance = self._generate_actionable_guidance("operation_error", message, context)

        return self._format_error_response("operation_error", message, context, guidance)
    
    def handle_validation_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle parameter validation errors."""
        context = context or {}
        message = f"Parameter validation failed: {error}"
        guidance = self._generate_actionable_guidance("validation_error", message, context)

        return self._format_error_response("validation_error", message, context, guidance)
    
    def handle_safety_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle safety-related errors."""
        context = context or {}
        message = f"Safety check failed: {error}"
        guidance = self._generate_actionable_guidance("safety_error", message, context)

        return self._format_error_response("safety_error", message, context, guidance)
    
    def handle_resource_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle resource-related errors."""
        context = context or {}
        return {
            "error": True,
            "error_type": "resource_error",
            "message": f"Resource error: {error}",
            "context": context,
            "actionable_guidance": [
                "Check system resources (CPU, memory, disk)",
                "Monitor system performance during operations",
                "Consider reducing operation complexity"
            ]
        }
    
    def handle_unknown_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle unknown or unexpected errors."""
        context = context or {}
        self.logger.error(f"Unknown error occurred: {error}", exc_info=True)

        message = f"An unexpected error occurred: {error}"
        guidance = self._generate_actionable_guidance("unknown_error", message, context)

        return self._format_error_response("unknown_error", message, context, guidance)

    def _generate_actionable_guidance(self, error_type: str, message: str, context: Dict[str, Any] = None) -> List[str]:
        """
        Generate actionable guidance based on error type and context.

        Args:
            error_type: Type of error (configuration_error, service_connection_error, etc.)
            message: Error message
            context: Additional context information

        Returns:
            List of actionable guidance strings
        """
        context = context or {}
        guidance = []

        if error_type == "configuration_error":
            guidance.extend([
                "Check the configuration file exists and is readable",
                "Verify JSON syntax is valid",
                "Ensure all required fields are present"
            ])
            if "embedding_length" in message.lower():
                guidance.extend([
                    "Set embedding_length in code_index.json to match your model",
                    "For nomic-embed-text, use 768",
                    "For Qwen3-Embedding-0.6B:F16, use 1024"
                ])
            if "chunking_strategy" in message.lower():
                guidance.extend([
                    "chunking_strategy must be one of: 'lines', 'tokens', 'treesitter'",
                    "Use 'lines' for simple line-based chunking (fastest)",
                    "Use 'tokens' for token-based chunking (balanced)",
                    "Use 'treesitter' for semantic chunking (most accurate)"
                ])

        elif error_type == "service_connection_error":
            service = context.get("service", "service")
            guidance.extend([
                f"Ensure {service} service is running and accessible",
                "Check service configuration",
                "Verify network connectivity"
            ])
            if service.lower() == "ollama":
                base_url = context.get("base_url", "")
                if "11434" in base_url:
                    guidance.append("Verify Ollama is running on port 11434")
                guidance.extend([
                    "Verify Ollama is installed: ollama --version",
                    "Start Ollama service: ollama serve",
                    "Check model is available: ollama list"
                ])
            elif service.lower() == "qdrant":
                guidance.extend([
                    "Verify Qdrant is running on the expected port (default: 6333)",
                    "Check Qdrant configuration and API key",
                    "Ensure Qdrant collections exist"
                ])

        elif error_type == "operation_error":
            operation = context.get("operation", "").lower()
            guidance.extend([
                "Check the operation parameters are valid",
                "Verify all prerequisites are met",
                "Check system resources and connectivity"
            ])

            # Add operation-specific guidance
            if operation == "indexing":
                guidance.extend([
                    f"Indexing operation failed - check the following:",
                    "Ensure the workspace path exists and is accessible",
                    "Check that required services (Ollama, Qdrant) are running",
                    "Verify configuration file has all required fields"
                ])
            elif operation == "search":
                guidance.extend([
                    f"Search operation failed - check the following:",
                    "Ensure the workspace has been indexed first",
                    "Check that the collection exists in the vector store",
                    "Verify search parameters are within valid ranges"
                ])

        elif error_type == "validation_error":
            parameter = context.get("parameter", "")
            guidance.extend([
                "Check that all required parameters are provided",
                "Verify parameter types match the expected format",
                "Ensure parameter values are within valid ranges"
            ])

            # Add parameter-specific guidance
            if parameter == "min_score":
                guidance.extend([
                    "min_score must be a float between 0.0 and 1.0",
                    "Typical values: 0.1 for lenient matching, 0.8 for strict matching"
                ])
            elif parameter == "workspace":
                guidance.extend([
                    "Workspace path must exist and be a directory",
                    "Use absolute paths or paths relative to current directory",
                    "Check file permissions for read access"
                ])
            elif parameter:
                guidance.append(f"Check the {parameter} parameter value and format")

        elif error_type == "safety_error":
            guidance.extend([
                "This operation requires explicit confirmation",
                "Use yes=true parameter to bypass confirmation prompts",
                "Consider the consequences before proceeding"
            ])

            # Add resource-specific guidance for memory issues
            if "memory" in message.lower() or context.get("memory_usage"):
                guidance.extend([
                    "Reduce batch size or chunk size in configuration",
                    "Increase system memory or use a machine with more RAM",
                    "Process files individually instead of in batches",
                    "Consider using memory-mapped files for large datasets"
                ])

        elif error_type == "unknown_error":
            guidance.extend([
                "Check the logs for more detailed error information",
                "Verify all system requirements are met",
                "Try restarting the MCP server",
                "Check the documentation for known issues",
                "Contact support if the problem persists"
            ])

        return guidance

    def _categorize_error(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """
        Categorize an error based on its type and context.

        Args:
            error: The exception that occurred
            context: Additional context information

        Returns:
            Error category string
        """
        context = context or {}

        # Check error message patterns
        error_msg = str(error).lower()

        if "embedding_length" in error_msg or "chunking_strategy" in error_msg:
            return "configuration_error"

        if "connection" in error_msg or "timeout" in error_msg or "service" in error_msg:
            return "service_connection_error"

        if "min_score" in error_msg or "max_results" in error_msg or "parameter" in error_msg:
            return "validation_error"

        if "confirmation" in error_msg or "destructive" in error_msg:
            return "safety_error"

        # Check context clues
        if context.get("operation"):
            return "operation_error"

        if context.get("config_file"):
            return "configuration_error"

        if context.get("parameter"):
            return "validation_error"

        # Default to unknown
        return "unknown_error"

    def _format_error_response(self, error_type: str, message: str, context: Dict[str, Any] = None, guidance: List[str] = None) -> Dict[str, Any]:
        """
        Format a standardized error response.

        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
            guidance: List of actionable guidance

        Returns:
            Formatted error response dictionary
        """
        context = context or {}
        guidance = guidance or []

        return {
            "error": True,
            "error_type": error_type,
            "message": message,
            "context": context,
            "actionable_guidance": guidance,
            "timestamp": datetime.now().isoformat()
        }


# Create a global instance for easy importing
error_handler = MCPErrorHandler()