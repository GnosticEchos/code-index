"""Main MCP server implementation leveraging shared command context."""

import asyncio
import os
import sys
import logging
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastmcp import FastMCP
from ..config import Config
from ..config_service import ConfigurationService
from ..services.shared.command_context import CommandContext
from .core.error_handler import error_handler
from .core.resource_manager import resource_manager
from ..errors import ErrorResponse, ErrorCategory, ErrorSeverity


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


MCPConfigurationManager = ConfigurationService


class CodeIndexMCPServer:
    """
    Main MCP server class for code indexing functionality.
    
    This server provides MCP tools for indexing code repositories,
    searching indexed code, and managing collections.
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
        # Note: 'debug' is no longer a constructor param in FastMCP 3.x
        self._mcp = FastMCP(
            "Code Index MCP Server",
            lifespan=self._lifespan_manager
        )
        self._running = False
        
        # Set up logging - Ensure logs go to stderr to avoid protocol corruption on stdout
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            stream=sys.stderr
        )
        self.logger = logging.getLogger("src.code_index.mcp_server.server")

    @asynccontextmanager
    async def _lifespan_manager(self, server: FastMCP):
        """Lifecycle manager for background resources."""
        self.logger.info("MCP server resources initializing...")
        try:
            # Initialize resource manager and shutdown handler as expected by tests
            resource_manager.initialize()
            resource_manager.register_shutdown_handler(lambda: None) # Placeholder handler
            yield
        finally:
            self.logger.info("MCP server resources shutting down...")
            # Unified cleanup handled by _cleanup_server_resources
            await self._cleanup_server_resources()

    async def _cleanup_server_resources(self):
        """Clean up shared resources used by the server."""
        self.logger.info("Starting resource cleanup...")
        try:
            # Resource manager handles System-level cleanup
            # Tests expect this to be called once during lifespan shutdown
            await resource_manager.shutdown()
            self.logger.info("Resource cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")

    async def _validate_services(self) -> None:
        """
        Validate and register services for cleanup.
        Used by tests and initialization.
        """
        if not self.config:
            return

        # Use resource manager to track connections for cleanup
        resource_manager.register_ollama_connection(self.config.ollama_base_url)
        resource_manager.register_qdrant_connection(self.config.qdrant_url)

    async def _load_configuration(self) -> Config:
        """Load and validate system configuration."""
        try:
            config = self.config_manager.load_with_fallback(
                config_path=self.config_path_abs,
                workspace_path=self.workspace_path,
            )
            
            # Initial validation to fail fast
            validation = self.config_manager.validate_and_initialize(config)
            if not validation.valid:
                error_msg = f"Configuration validation failed: {validation.error}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            self.config = config
            # Register services for cleanup
            await self._validate_services()
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def _register_tools(self):
        """Private alias for tool registration (used by tests)."""
        self.register_tools()

    def register_tools(self):
        """Register all MCP tools."""
        from .tools.index_tool import index, set_default_config_path as set_index_config_path, create_index_tool_description
        from .tools.search_tool import search, set_default_config_path as set_search_config_path, create_search_tool_description
        from .tools.collections_tool import collections, set_default_config_path as set_collections_config_path, create_collections_tool_description
        
        # Set default config path for tools
        set_index_config_path(self.config_path_abs)
        set_search_config_path(self.config_path_abs)
        set_collections_config_path(self.config_path_abs)
        
        # Register tools with names and descriptions as expected by tests
        self._mcp.tool(name="index", description=create_index_tool_description())(index)
        self._mcp.tool(name="search", description=create_search_tool_description())(search)
        self._mcp.tool(name="collections", description=create_collections_tool_description())(collections)
        
    async def start(self):
        """Start the MCP server."""
        if self._running:
            return
            
        self.logger.info(f"Starting MCP server for workspace: {self.workspace_path}")
        try:
            # Load configuration first
            await self._load_configuration()
            
            # Register tools
            self._register_tools()
            
            # Start the server using run_async as expected by tests
            self._running = True
            await self._mcp.run_async(transport="stdio")
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            self._running = False
            raise

    async def shutdown(self):
        """Gracefully shut down the server."""
        if not self._running:
            return
            
        self.logger.info("Shutting down MCP server...")
        # FastMCP run() handles the event loop, we mainly need to 
        # ensure our internal state reflects the shutdown
        self._running = False
        
        # Cleanup handled by lifespan manager when run_async finishes
        # but if called manually, ensure we clean up
        await self._cleanup_server_resources()


def sync_main():
    """Synchronous entry point for the MCP binary."""
    server = CodeIndexMCPServer()
    asyncio.run(server.start())


if __name__ == "__main__":
    sync_main()
