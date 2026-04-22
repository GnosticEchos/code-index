"""
Resource Management and Cleanup System for MCP Server

This module provides comprehensive resource management including memory management,
connection cleanup, and graceful shutdown handling for the MCP server.

Uses extracted modules:
- mcp_resource_models: ResourceInfo dataclass
- mcp_memory_manager: MemoryManager class
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Set, Callable
from contextlib import asynccontextmanager

from ...constants import (
    MEMORY_THRESHOLD_MCP, CLEANUP_INTERVAL_MCP, SHUTDOWN_WAIT_TIMEOUT
)

# Import from extracted modules
from .mcp_resource_models import ResourceInfo
from .mcp_memory_manager import create_memory_manager
from .mcp_resource_utils import (
    cleanup_old_resources_by_type,
    check_memory_and_collect,
    cleanup_service_connections,
    setup_signal_handlers
)


class ResourceManager:
    """
    System-level resource management for the MCP server.
    
    This complements FastMCP's built-in resource management (which handles MCP resources
    like tools, prompts, and resources) by providing system-level resource management:
    
    FastMCP handles:
    - MCP resource lifecycle (tools, prompts, resources)
    - Component enable/disable functionality
    - Lifespan context management for startup/shutdown
    
    This ResourceManager handles:
    - System resource cleanup (connections, memory, files)
    - Integration with CLI tool's existing resource patterns
    - Graceful shutdown coordination beyond FastMCP's lifespan
    - Memory pressure monitoring and cleanup
    
    Works alongside existing CLI patterns:
    - Cache management (cache.py)
    - Timeout file tracking (cli.py)  
    - Tree-sitter resource cleanup (chunking.py)
    """
    
    def __init__(self):
        """Initialize the resource manager."""
        self.logger = logging.getLogger(__name__)
        self._resources: Dict[str, ResourceInfo] = {}
        self._cleanup_callbacks: List[Callable[[], None]] = []
        self._shutdown_event = asyncio.Event()
        self._shutdown_handlers: List[Callable[[], None]] = []
        self._active_operations: Set[str] = set()
        self._operation_lock = threading.Lock()
        self._memory_threshold_mb = MEMORY_THRESHOLD_MCP  # 1GB default memory threshold
        self._cleanup_interval = CLEANUP_INTERVAL_MCP  # 5 minutes cleanup interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # Track service connections (MCP-specific)
        self._ollama_connections: Set[Any] = set()
        self._qdrant_connections: Set[Any] = set()
        
        # Track Tree-sitter chunking strategies for cleanup
        self._tree_sitter_strategies: Set[Any] = set()
        
        # Track timeout files across operations (complements CLI timeout logging)
        self._timeout_files: Set[str] = set()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def initialize(self) -> None:
        """Initialize the resource manager and start background tasks."""
        if self._initialized:
            return
        
        self.logger.info("Initializing resource manager...")
        
        # Start periodic cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        self._initialized = True
        self.logger.info("Resource manager initialized successfully")
    
    async def shutdown(self) -> None:
        """Shutdown the resource manager and cleanup all resources."""
        if not self._initialized:
            return
        
        self.logger.info("Shutting down resource manager...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active operations to complete (with timeout)
        await self._wait_for_operations_completion(timeout=SHUTDOWN_WAIT_TIMEOUT)
        
        # Run shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                handler()
            except Exception as e:
                self.logger.error(f"Error in shutdown handler: {e}")
        
        # Cleanup all managed resources
        await self._cleanup_all_resources()
        
        # Cleanup service connections
        self._cleanup_service_connections()
        
        self._initialized = False
        self.logger.info("Resource manager shutdown complete")
    
    def register_resource(self, resource_id: str, resource_type: str, 
                         cleanup_func: Callable[[], None], 
                         metadata: Dict[str, Any] = None) -> None:
        """
        Register a resource for management and cleanup.
        
        Args:
            resource_id: Unique identifier for the resource
            resource_type: Type of resource (connection, file, memory, etc.)
            cleanup_func: Function to call when cleaning up the resource
            metadata: Additional metadata about the resource
        """
        metadata = metadata or {}
        
        resource_info = ResourceInfo(
            resource_id=resource_id,
            resource_type=resource_type,
            created_at=time.time(),
            cleanup_func=cleanup_func,
            metadata=metadata
        )
        
        self._resources[resource_id] = resource_info
        self.logger.debug(f"Registered resource: {resource_id} ({resource_type})")
    
    def unregister_resource(self, resource_id: str) -> bool:
        """
        Unregister a resource from management.
        
        Args:
            resource_id: Unique identifier for the resource
            
        Returns:
            True if resource was found and removed, False otherwise
        """
        if resource_id in self._resources:
            del self._resources[resource_id]
            self.logger.debug(f"Unregistered resource: {resource_id}")
            return True
        return False
    
    def cleanup_resource(self, resource_id: str) -> bool:
        """
        Cleanup a specific resource.
        
        Args:
            resource_id: Unique identifier for the resource
            
        Returns:
            True if resource was found and cleaned up, False otherwise
        """
        if resource_id not in self._resources:
            return False
        
        resource_info = self._resources[resource_id]
        try:
            resource_info.cleanup_func()
            self.logger.debug(f"Cleaned up resource: {resource_id}")
        except Exception as e:
            self.logger.error(f"Error cleaning up resource {resource_id}: {e}")
        finally:
            del self._resources[resource_id]
        
        return True
    
    def register_shutdown_handler(self, handler: Callable[[], None]) -> None:
        """
        Register a handler to be called during shutdown.
        
        Args:
            handler: Function to call during shutdown
        """
        self._shutdown_handlers.append(handler)
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for periodic cleanup.
        
        Args:
            callback: Function to call during periodic cleanup
        """
        self._cleanup_callbacks.append(callback)
    
    @asynccontextmanager
    async def operation_context(self, operation_id: str):
        """
        Context manager for tracking active operations.
        
        Args:
            operation_id: Unique identifier for the operation
        """
        with self._operation_lock:
            self._active_operations.add(operation_id)
        
        self.logger.debug(f"Started operation: {operation_id}")
        
        try:
            yield
        finally:
            with self._operation_lock:
                self._active_operations.discard(operation_id)
            self.logger.debug(f"Completed operation: {operation_id}")
    
    def register_ollama_connection(self, connection: Any) -> None:
        """
        Register an Ollama connection for cleanup.
        
        Args:
            connection: Ollama connection object
        """
        self._ollama_connections.add(connection)
        self.logger.debug("Registered Ollama connection")
    
    def register_qdrant_connection(self, connection: Any) -> None:
        """
        Register a Qdrant connection for cleanup.
        
        Args:
            connection: Qdrant connection object
        """
        self._qdrant_connections.add(connection)
        self.logger.debug("Registered Qdrant connection")
    
    def register_tree_sitter_strategy(self, strategy: Any) -> None:
        """
        Register a Tree-sitter chunking strategy for resource cleanup.
        
        This complements the existing cleanup_resources() method in TreeSitterChunkingStrategy.
        
        Args:
            strategy: TreeSitterChunkingStrategy instance
        """
        self._tree_sitter_strategies.add(strategy)
        self.logger.debug("Registered Tree-sitter chunking strategy")
    
    def add_timeout_file(self, file_path: str) -> None:
        """
        Track a file that timed out during processing.
        
        This complements the CLI tool's timeout file logging system.
        
        Args:
            file_path: Path to the file that timed out
        """
        self._timeout_files.add(file_path)
        self.logger.debug(f"Added timeout file: {file_path}")
    
    def get_timeout_files(self) -> Set[str]:
        """
        Get all files that have timed out during processing.
        
        Returns:
            Set of file paths that timed out
        """
        return self._timeout_files.copy()
    
    def clear_timeout_files(self) -> None:
        """Clear the timeout files tracking."""
        self._timeout_files.clear()
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get statistics about managed resources.
        
        Returns:
            Dictionary with resource statistics
        """
        resource_types = {}
        for resource in self._resources.values():
            resource_type = resource.resource_type
            if resource_type not in resource_types:
                resource_types[resource_type] = 0
            resource_types[resource_type] += 1
        
        return {
            "total_resources": len(self._resources),
            "resource_types": resource_types,
            "active_operations": len(self._active_operations),
            "ollama_connections": len(self._ollama_connections),
            "qdrant_connections": len(self._qdrant_connections),
            "tree_sitter_strategies": len(self._tree_sitter_strategies),
            "timeout_files": len(self._timeout_files),
            "memory_threshold_mb": self._memory_threshold_mb,
            "cleanup_interval": self._cleanup_interval
        }
    
    def set_memory_threshold(self, threshold_mb: int) -> None:
        """
        Set the memory threshold for cleanup triggers.
        
        Args:
            threshold_mb: Memory threshold in megabytes
        """
        self._memory_threshold_mb = threshold_mb
        self.logger.info(f"Set memory threshold to {threshold_mb}MB")
    
    def force_cleanup(self) -> None:
        """Force immediate cleanup of all eligible resources."""
        self.logger.info("Forcing immediate resource cleanup")
        
        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in cleanup callback: {e}")
        
        # Cleanup old resources
        self._cleanup_old_resources()
        
        # Check memory usage and cleanup if needed
        self._check_memory_usage()
        
        # Trigger Tree-sitter resource cleanup if memory pressure is high
        self._cleanup_tree_sitter_resources()
    
    def _cleanup_tree_sitter_resources(self) -> None:
        """
        Cleanup Tree-sitter resources when under memory pressure.
        
        This complements the existing cleanup_resources() method in TreeSitterChunkingStrategy
        by providing a centralized way to trigger cleanup across all active strategies.
        """
        if not self._tree_sitter_strategies:
            return
        
        self.logger.debug("Cleaning up Tree-sitter resources due to memory pressure")
        
        for strategy in list(self._tree_sitter_strategies):
            try:
                if hasattr(strategy, 'cleanup_resources'):
                    strategy.cleanup_resources()
            except Exception as e:
                self.logger.debug(f"Error cleaning up Tree-sitter strategy: {e}")
    
    def integrate_with_cli_cache_cleanup(self, config: Any) -> int:
        """
        Integrate with the CLI tool's cache cleanup system.
        
        This method provides a bridge to the existing cache.py cleanup functions,
        allowing the MCP server to trigger cache cleanup when needed.
        
        Args:
            config: Configuration object for cache directory resolution
            
        Returns:
            Number of cache files removed
        """
        try:
            # Import here to avoid circular dependencies
            from ...cache import clear_all_caches
            
            removed = clear_all_caches(config)
            self.logger.info(f"CLI cache cleanup removed {removed} files")
            return removed
            
        except Exception as e:
            self.logger.error(f"Error during CLI cache cleanup: {e}")
            return 0
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task that runs in the background."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                if self._shutdown_event.is_set():
                    break
                
                self.logger.debug("Running periodic cleanup")
                self.force_cleanup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    def _cleanup_old_resources(self) -> None:
        """Cleanup resources that are older than a certain threshold."""
        resources_to_cleanup = cleanup_old_resources_by_type(self._resources)
        for resource_id in resources_to_cleanup:
            self.cleanup_resource(resource_id)
    
    def _check_memory_usage(self) -> None:
        """Check memory usage and trigger cleanup if threshold is exceeded."""
        check_memory_and_collect(
            self._memory_threshold_mb,
            self._resources,
            self.cleanup_resource
        )
    
    async def _wait_for_operations_completion(self, timeout: float = 30.0) -> None:
        """
        Wait for active operations to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        
        while self._active_operations and (time.time() - start_time) < timeout:
            self.logger.info(f"Waiting for {len(self._active_operations)} active operations to complete...")
            await asyncio.sleep(1.0)
        
        if self._active_operations:
            self.logger.warning(f"Shutdown timeout reached with {len(self._active_operations)} operations still active")
    
    async def _cleanup_all_resources(self) -> None:
        """Cleanup all managed resources."""
        resource_ids = list(self._resources.keys())
        
        for resource_id in resource_ids:
            try:
                self.cleanup_resource(resource_id)
            except Exception as e:
                self.logger.error(f"Error cleaning up resource {resource_id}: {e}")
        
        self.logger.info(f"Cleaned up {len(resource_ids)} resources")
    
    def _cleanup_service_connections(self) -> None:
        """Cleanup service connections and Tree-sitter resources."""
        cleanup_service_connections(self._ollama_connections, "Ollama", ['close', 'session'])
        cleanup_service_connections(self._qdrant_connections, "Qdrant", ['close', 'client'])
        
        # Cleanup Tree-sitter strategies
        for strategy in list(self._tree_sitter_strategies):
            try:
                if hasattr(strategy, 'cleanup_resources'):
                    strategy.cleanup_resources()
            except Exception as e:
                self.logger.debug(f"Error cleaning up Tree-sitter strategy: {e}")
        
        self._tree_sitter_strategies.clear()
        self.logger.debug("Service connections and Tree-sitter resources cleaned up")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            
            # Create a new event loop if we're not in one
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Schedule shutdown
            if loop.is_running():
                loop.create_task(self.shutdown())
            else:
                loop.run_until_complete(self.shutdown())
        
        setup_signal_handlers(signal_handler)


# Global resource manager instance
resource_manager = ResourceManager()
memory_manager = create_memory_manager(resource_manager)