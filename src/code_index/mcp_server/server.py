"""
Main MCP Server Implementation

This module contains the main MCP server class and entry point
for the code index MCP server.
"""

import asyncio
import sys
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from ..config import Config
from .core.config_manager import MCPConfigurationManager
from .core.error_handler import error_handler
from .core.resource_manager import resource_manager


class CodeIndexMCPServer:
    """
    Main MCP server class for code indexing functionality.
    
    This server provides MCP tools for indexing code repositories,
    performing semantic searches, and managing collections.
    """
    
    def __init__(self, config_path: str = "code_index.json"):
        """
        Initialize the MCP server.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config: Optional[Config] = None
        self.config_manager = MCPConfigurationManager(config_path)
        
        # Create FastMCP server with custom lifespan for resource management integration
        self._mcp = FastMCP(
            "Code Index MCP Server",
            lifespan=self._lifespan_manager
        )
        self._running = False
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stderr)]
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self) -> None:
        """Start the MCP server."""
        try:
            self.logger.info("Starting Code Index MCP Server...")
            
            # Load configuration
            await self._load_configuration()
            
            # Validate services
            await self._validate_services()
            
            # Register tools
            self._register_tools()
            
            # Start the MCP server with stdio transport
            # FastMCP's lifespan manager will handle resource initialization
            self._running = True
            self.logger.info("MCP Server started successfully")
            
            # Run the server using run_async for proper async context handling
            await self._mcp.run_async(transport="stdio")
            
        except Exception as e:
            error_response = error_handler.handle_unknown_error(e, {"component": "server_startup"})
            self.logger.error(f"Failed to start MCP server: {error_response['message']}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the MCP server and cleanup resources."""
        if self._running:
            self.logger.info("Shutting down MCP server...")
            self._running = False
            
            # FastMCP's lifespan manager will handle resource cleanup
            self.logger.info("MCP server shutdown complete")
    
    @asynccontextmanager
    async def _lifespan_manager(self, server):
        """
        Custom lifespan manager that integrates with our resource management.

        This works with FastMCP's lifespan system to provide proper startup/shutdown
        coordination between FastMCP's resource management and our system-level
        resource management.
        """
        try:
            # Startup phase
            self.logger.info("Initializing system resources...")
            
            # Initialize our resource manager
            resource_manager.initialize()
            
            # Register cleanup handlers
            resource_manager.register_shutdown_handler(self._cleanup_server_resources)
            
            self.logger.info("System resources initialized")
            
            # Yield control to FastMCP
            yield
            
        finally:
            # Shutdown phase
            self.logger.info("Cleaning up system resources...")
            
            # Shutdown our resource manager
            await resource_manager.shutdown()
            
            self.logger.info("System resources cleaned up")
    
    def _cleanup_server_resources(self) -> None:
        """Cleanup server-specific resources."""
        try:
            # Cleanup any server-specific resources here
            self.logger.debug("Cleaning up server resources")
        except Exception as e:
            self.logger.error(f"Error cleaning up server resources: {e}")
    
    async def _load_configuration(self) -> None:
        """Load and validate configuration."""
        try:
            self.config = self.config_manager.load_config()
            self.logger.info("Configuration loaded and validated successfully")
        except ValueError as e:
            error_response = error_handler.handle_configuration_error(e, {"config_file": self.config_path})
            self.logger.error(f"Configuration validation failed: {error_response['message']}")
            raise
        except Exception as e:
            error_response = error_handler.handle_configuration_error(e, {"config_file": self.config_path})
            self.logger.error(f"Failed to load configuration: {error_response['message']}")
            raise
    
    def _register_tools(self) -> None:
        """Register MCP tools with the server."""
        from .tools.index_tool import index, create_index_tool_description
        from .tools.search_tool import search, create_search_tool_description
        from .tools.collections_tool import collections, create_collections_tool_description
        
        # Register index tool
        self._mcp.tool(
            name="index",
            description=create_index_tool_description()
        )(index)
        
        # Register search tool
        self._mcp.tool(
            name="search",
            description=create_search_tool_description()
        )(search)
        
        # Register collections tool
        self._mcp.tool(
            name="collections",
            description=create_collections_tool_description()
        )(collections)
        
        self.logger.info("Registered index, search, and collections tools with MCP server")
    
    async def _validate_services(self) -> None:
        """Validate connectivity to required services (Ollama, Qdrant)."""
        if not self.config:
            raise ValueError("Configuration must be loaded before validating services")
        
        validation_errors = []
        
        # Validate Ollama service
        try:
            from ..embedder import OllamaEmbedder
            embedder = OllamaEmbedder(self.config)
            
            # Register Ollama connection for cleanup
            resource_manager.register_ollama_connection(embedder)
            
            ollama_result = embedder.validate_configuration()
            
            if not ollama_result.get("valid", False):
                # Use error handler for structured error response
                context = {
                    "base_url": self.config.ollama_base_url,
                    "model": self.config.ollama_model
                }
                error_response = error_handler.handle_service_connection_error(
                    "Ollama", 
                    Exception(ollama_result.get("error", "Unknown error")), 
                    context
                )
                validation_errors.append(error_response)
            else:
                self.logger.info("Ollama service validation successful")
                
        except Exception as e:
            context = {
                "base_url": self.config.ollama_base_url,
                "model": self.config.ollama_model
            }
            error_response = error_handler.handle_service_connection_error("Ollama", e, context)
            validation_errors.append(error_response)
        
        # Validate Qdrant service
        try:
            from ..vector_store import QdrantVectorStore
            vector_store = QdrantVectorStore(self.config)
            
            # Register Qdrant connection for cleanup
            resource_manager.register_qdrant_connection(vector_store)
            
            # Test connection by getting collections
            collections = vector_store.client.get_collections()
            self.logger.info(f"Qdrant service validation successful - found {len(collections.collections)} collections")
            
        except Exception as e:
            context = {
                "qdrant_url": self.config.qdrant_url,
                "api_key": self.config.qdrant_api_key
            }
            error_response = error_handler.handle_service_connection_error("Qdrant", e, context)
            validation_errors.append(error_response)
        
        # Raise error if any service validation failed
        if validation_errors:
            # Combine all validation errors into a single structured response
            combined_error = {
                "error": True,
                "error_type": "service_validation_failed",
                "message": "One or more services failed validation",
                "validation_errors": validation_errors,
                "actionable_guidance": [
                    "Check that all required services are running",
                    "Verify service URLs and authentication in configuration",
                    "Review individual service errors for specific guidance"
                ]
            }
            
            self.logger.error(f"Service validation failed: {combined_error['message']}")
            raise ValueError(str(combined_error))


async def main() -> None:
    """Main entry point for the MCP server."""
    server = CodeIndexMCPServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        print("Shutting down MCP server...", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await server.shutdown()
def sync_main() -> None:
    """Synchronous entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())