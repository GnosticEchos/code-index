"""
Utility functions for resource management in MCP Server.

This module contains helper functions for resource cleanup and management.
"""

import logging
import time
from typing import List, Set, Any, Dict, Optional

from ...constants import OLD_RESOURCE_THRESHOLD


logger = logging.getLogger(__name__)


def cleanup_old_resources_by_type(
    resources: Dict[str, Any],
    resource_types_to_cleanup: Optional[List[str]] = None
) -> List[str]:
    """
    Cleanup resources that are older than a certain threshold.
    
    Args:
        resources: Dictionary of resource_id to ResourceInfo
        resource_types_to_cleanup: List of resource types to cleanup automatically
        
    Returns:
        List of resource IDs that were cleaned up
    """
    if resource_types_to_cleanup is None:
        resource_types_to_cleanup = ["temp_file", "cache", "connection_pool"]
    
    current_time = time.time()
    old_threshold = OLD_RESOURCE_THRESHOLD
    
    resources_to_cleanup = []
    for resource_id, resource_info in resources.items():
        if current_time - resource_info.created_at > old_threshold:
            if resource_info.resource_type in resource_types_to_cleanup:
                resources_to_cleanup.append(resource_id)
    
    return resources_to_cleanup


def check_memory_and_collect(
    memory_threshold_mb: float,
    resources: Dict[str, Any],
    cleanup_resource_func: callable
) -> int:
    """
    Check memory usage and trigger cleanup if threshold is exceeded.
    
    Args:
        memory_threshold_mb: Memory threshold in MB
        resources: Dictionary of resource_id to ResourceInfo
        cleanup_resource_func: Function to cleanup a resource
        
    Returns:
        Number of resources cleaned up
    """
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > memory_threshold_mb:
            logger.warning(f"Memory usage ({memory_mb:.1f}MB) exceeds threshold ({memory_threshold_mb}MB)")
            
            # Trigger garbage collection
            import gc
            gc.collect()
            
            # Cleanup cache-type resources
            cache_resources = [
                resource_id for resource_id, resource_info in resources.items()
                if resource_info.resource_type in ["cache", "temp_file"]
            ]
            
            for resource_id in cache_resources:
                cleanup_resource_func(resource_id)
            
            logger.info(f"Cleaned up {len(cache_resources)} cache resources due to memory pressure")
            return len(cache_resources)
    
    except ImportError:
        # psutil not available, skip memory monitoring
        pass
    except Exception as e:
        logger.error(f"Error checking memory usage: {e}")
    
    return 0


def cleanup_service_connections(
    connections_set: Set[Any],
    connection_type: str,
    close_methods: List[str] = None
) -> None:
    """
    Cleanup service connections.
    
    Args:
        connections_set: Set of connection objects
        connection_type: Name of connection type for logging
        close_methods: List of methods to try for closing
    """
    if close_methods is None:
        close_methods = ['close']
    
    for connection in list(connections_set):
        try:
            for method in close_methods:
                if hasattr(connection, method):
                    getattr(connection, method)()
                    break
        except Exception as e:
            logger.debug(f"Error cleaning up {connection_type} connection: {e}")
    
    connections_set.clear()


def setup_signal_handlers(signal_handler: callable) -> None:
    """
    Setup signal handlers for graceful shutdown.
    
    Args:
        signal_handler: Handler function for signals
    """
    import signal
    
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, signal_handler)