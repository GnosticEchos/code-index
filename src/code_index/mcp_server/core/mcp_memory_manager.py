"""
Memory management utilities for large indexing operations in MCP Server.

This module provides memory pooling and memory usage tracking functionality.
"""

import logging
from typing import Dict, Any, List, Callable

from ...constants import MEMORY_POOL_MAX_SIZE


class MemoryManager:
    """
    Memory management utilities for large indexing operations.
    """
    
    def __init__(self, resource_manager: Any):
        """
        Initialize memory manager.
        
        Args:
            resource_manager: Resource manager instance
        """
        self.resource_manager = resource_manager
        self.logger = logging.getLogger(__name__)
        self._memory_pools: Dict[str, List[Any]] = {}
    
    def create_memory_pool(self, pool_name: str, max_size: int = MEMORY_POOL_MAX_SIZE) -> None:
        """
        Create a memory pool for reusing objects.
        
        Args:
            pool_name: Name of the memory pool
            max_size: Maximum number of objects in the pool
        """
        self._memory_pools[pool_name] = []
        
        def cleanup_pool():
            if pool_name in self._memory_pools:
                del self._memory_pools[pool_name]
                self.logger.debug(f"Cleaned up memory pool: {pool_name}")
        
        self.resource_manager.register_resource(
            resource_id=f"memory_pool_{pool_name}",
            resource_type="memory_pool",
            cleanup_func=cleanup_pool,
            metadata={"pool_name": pool_name, "max_size": max_size}
        )
    
    def get_from_pool(self, pool_name: str, factory_func: Callable[[], Any]) -> Any:
        """
        Get an object from the memory pool or create a new one.
        
        Args:
            pool_name: Name of the memory pool
            factory_func: Function to create new objects
            
        Returns:
            Object from pool or newly created object
        """
        if pool_name not in self._memory_pools:
            self.create_memory_pool(pool_name)
        
        pool = self._memory_pools[pool_name]
        
        if pool:
            return pool.pop()
        else:
            return factory_func()
    
    def return_to_pool(self, pool_name: str, obj: Any, max_size: int = MEMORY_POOL_MAX_SIZE) -> None:
        """
        Return an object to the memory pool.
        
        Args:
            pool_name: Name of the memory pool
            obj: Object to return to pool
            max_size: Maximum pool size
        """
        if pool_name not in self._memory_pools:
            return
        
        pool = self._memory_pools[pool_name]
        
        if len(pool) < max_size:
            # Reset object state if possible
            if hasattr(obj, 'clear'):
                obj.clear()
            elif hasattr(obj, 'reset'):
                obj.reset()
            
            pool.append(obj)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        stats = {
            "memory_pools": {
                name: len(pool) for name, pool in self._memory_pools.items()
            }
        }
        
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            stats.update({
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            })
        except ImportError:
            pass
        except Exception as e:
            self.logger.debug(f"Error getting memory stats: {e}")
        
        return stats


def create_memory_manager(resource_manager: Any) -> MemoryManager:
    """
    Factory function to create a MemoryManager.
    
    Args:
        resource_manager: Resource manager instance
        
    Returns:
        MemoryManager instance
    """
    return MemoryManager(resource_manager)