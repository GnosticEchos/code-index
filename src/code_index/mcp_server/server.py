"""Main MCP server implementation leveraging shared command context."""

import asyncio
import os
import sys
import logging
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime


class _ConfigPath(str):
    """String subclass that preserves both raw and absolute config paths."""

    def __new__(cls, raw: str, absolute: str):
        obj = super().__new__(cls, raw)
        obj.raw = raw
        obj.absolute = absolute
        return obj

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.raw or other == self.absolute
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.absolute)

from fastmcp import FastMCP
from ..config import Config
from ..config_service import ConfigurationService
from ..services.command_context import CommandContext
from .core.error_handler import error_handler


class MCPErrorHandlerAdapter:
    """Adapter to make MCPErrorHandler compatible with ErrorHandler interface."""

    def __init__(self, mcp_error_handler):
        self.mcp_error_handler = mcp_error_handler

    def handle_error(self, error, context, category=None, severity=None, include_stack_trace=True):
        """Adapt MCPErrorHandler methods to ErrorHandler interface."""
        # Map ErrorCategory to MCP error handling methods
        if category and hasattr(category, 'value'):
            category_str = category.value
        else:
            category_str = "unknown"

        # Use appropriate MCP error handler method based on category
        if category_str == "configuration":
            response = self.mcp_error_handler.handle_configuration_error(error, context.additional_data if context.additional_data else {})
        elif category_str == "network":
            response = self.mcp_error_handler.handle_service_connection_error(
                context.additional_data.get("service", "unknown") if context.additional_data else "unknown",
                error,
                context.additional_data if context.additional_data else {}
            )
        else:
            response = self.mcp_error_handler.handle_unknown_error(error, context.additional_data if context.additional_data else {})

        # Convert MCP response to ErrorResponse format
        from ..errors import ErrorResponse, ErrorCategory, ErrorSeverity
        return ErrorResponse(
            error=True,
            error_type=type(error).__name__,
            category=category or ErrorCategory.UNKNOWN,
            severity=severity or ErrorSeverity.MEDIUM,
            message=response.get("message", str(error)),
            context=context,
            timestamp=datetime.now(),
            recovery_suggestions=[],
            actionable_guidance=response.get("actionable_guidance", [])
        )
from .core.resource_manager import resource_manager

MCPConfigurationManager = ConfigurationService


class CodeIndexMCPServer:
    """
    Main MCP server class for code indexing functionality.
    
    This server provides MCP tools for indexing code repositories,
    """
    
    def __init__(self, config_path: str = "code_index.json"):
        """
        Initialize the MCP server.

        Args:
            config_path: Path to the configuration file
        """
        config_path_abs = os.path.abspath(config_path)
        self.config_path = _ConfigPath(config_path, config_path_abs)
        self.config_path_abs = config_path_abs
        self.workspace_path = os.path.dirname(self.config_path_abs) or os.getcwd()
        self.config: Optional[Config] = None
        self._error_adapter = MCPErrorHandlerAdapter(error_handler)
        self.config_manager = MCPConfigurationManager(self._error_adapter)
        self.command_context = CommandContext(
            error_handler=self._error_adapter,
            config_service=self.config_manager,
        )

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
        """Load and validate configuration using centralized ConfigurationService."""
        try:
            # Load configuration with shared command context
            config = self.config_manager.load_with_fallback(
                config_path=self.config_path_abs,
                workspace_path=self.workspace_path,
            )
            self.config = config
            self.logger.info("Configuration loaded and validated successfully using ConfigurationService")
        except ValueError as e:
            error_response = error_handler.handle_configuration_error(e, {"config_file": self.config_path_abs})
            self.logger.error(f"Configuration validation failed: {error_response['message']}")
            raise
        except Exception as e:
            error_response = error_handler.handle_configuration_error(e, {"config_file": self.config_path_abs})
            self.logger.error(f"Failed to load configuration: {error_response['message']}")
            raise

    
    def _register_tools(self) -> None:
        """Register MCP tools with the server and configure shared settings."""
        from .tools.index_tool import (
            index,
            create_index_tool_description,
            set_default_config_path as set_index_tool_config_path,
        )
        from .tools.search_tool import (
            search,
            create_search_tool_description,
            set_default_config_path as set_search_tool_config_path,
        )
        from .tools.collections_tool import (
            collections,
            create_collections_tool_description,
            set_default_config_path as set_collections_tool_config_path,
        )
        import inspect

        # Share explicit config path with MCP tools so they don't infer per-workspace JSON
        set_index_tool_config_path(self.config_path_abs)
        set_search_tool_config_path(self.config_path_abs)
        set_collections_tool_config_path(self.config_path_abs)

        
        # Register tools with proper async handling to avoid coroutine warnings
        # FastMCP expects async functions to be registered directly
        
        # Register index tool (async function)
        if inspect.iscoroutinefunction(index):
            self._mcp.tool(
                name="index",
                description=create_index_tool_description()
            )(index)
        else:
            # Wrap sync function if needed (shouldn't happen, but for safety)
            async def async_index(*args, **kwargs):
                return index(*args, **kwargs)
            self._mcp.tool(
                name="index",
                description=create_index_tool_description()
            )(async_index)
        
        # Register search tool (async function)
        if inspect.iscoroutinefunction(search):
            self._mcp.tool(
                name="search",
                description=create_search_tool_description()
            )(search)
        else:
            # Wrap sync function if needed (shouldn't happen, but for safety)
            async def async_search(*args, **kwargs):
                return search(*args, **kwargs)
            self._mcp.tool(
                name="search",
                description=create_search_tool_description()
            )(async_search)
        
        # Register collections tool (async function)
        if inspect.iscoroutinefunction(collections):
            self._mcp.tool(
                name="collections",
                description=create_collections_tool_description()
            )(collections)
        else:
            # Wrap sync function if needed (shouldn't happen, but for safety)
            async def async_collections(*args, **kwargs):
                return collections(*args, **kwargs)
            self._mcp.tool(
                name="collections",
                description=create_collections_tool_description()
            )(async_collections)
        
        self.logger.info("Registered index, search, and collections tools with MCP server")
    
    async def _validate_services(self) -> None:
        """Validate connectivity to required services (Ollama, Qdrant)."""
        if not self.config:
            raise ValueError("Configuration must be loaded before validating services")

        # ConfigurationService handles validation internally, so services are already validated
        # Just register service connections for cleanup
        try:
            from ..embedder import OllamaEmbedder
            from ..vector_store import QdrantVectorStore

            embedder = OllamaEmbedder(self.config)
            vector_store = QdrantVectorStore(self.config)

            resource_manager.register_ollama_connection(embedder)
            resource_manager.register_qdrant_connection(vector_store)

        except Exception as e:
            self.logger.warning(f"Failed to register service connections for cleanup: {e}")


async def main(config_path: str = "code_index.json") -> None:
    """Main entry point for the MCP server."""
    server = CodeIndexMCPServer(config_path=config_path)
    try:
        await server.start()
    except KeyboardInterrupt:
        print("Shutting down MCP server...", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await server.shutdown()

def sync_main(config_path: str = "code_index.json") -> None:
    """Synchronous entry point for console script."""
    asyncio.run(main(config_path=config_path))


if __name__ == "__main__":
    asyncio.run(main())