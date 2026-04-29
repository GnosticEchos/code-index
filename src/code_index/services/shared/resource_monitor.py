"""
Resource monitoring service for Tree-sitter resources.
"""
import time
from typing import Dict, Any

from ...constants import MEMORY_THRESHOLD_DEFAULT, MEMORY_THRESHOLD_HIGH, MEMORY_CHECK_INTERVAL_SECONDS


class ResourceMonitor:
    """Monitors Tree-sitter resource usage and memory."""
    
    def __init__(self, memory_cleanup_threshold: float = MEMORY_THRESHOLD_DEFAULT, debug_enabled: bool = False):
        self.memory_cleanup_threshold = memory_cleanup_threshold
        self.debug_enabled = debug_enabled
        self._last_memory_check = time.time()
        self._memory_check_interval = MEMORY_CHECK_INTERVAL_SECONDS
        self.performance_metrics = {
            'total_resources_created': 0,
            'total_resources_released': 0,
            'total_cleanup_operations': 0,
            'total_memory_freed_bytes': 0,
            'average_resource_lifetime_seconds': 0,
            'memory_optimization_efficiency': 0,
            'resource_reuse_rate': 0
        }
    
    def check_memory_and_cleanup(self, enable_aggressive_cleanup: bool = True, resource_manager=None):
        """Check memory usage and perform cleanup if needed."""
        try:
            current_time = time.time()
            if current_time - self._last_memory_check < self._memory_check_interval:
                return
            
            self._last_memory_check = current_time
            
            memory_info = self.get_memory_usage()
            memory_percent = memory_info.get("percent", 0)
            
            if memory_percent > self.memory_cleanup_threshold:
                if hasattr(resource_manager, '_perform_aggressive_cleanup'):
                    resource_manager._perform_aggressive_cleanup()
                
                import gc
                gc.collect()
                
                new_memory_info = self.get_memory_usage()
                new_memory_percent = new_memory_info.get("percent", 0)
                if memory_percent > 0:
                    efficiency = ((memory_percent - new_memory_percent) / memory_percent) * 100
                    self.performance_metrics['memory_optimization_efficiency'] = max(0, efficiency)
        except (ImportError, AttributeError, TypeError):
            pass
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get comprehensive memory usage information."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            available_memory_percent = 100.0 - memory_percent
            
            recommendations = []
            if memory_percent > self.memory_cleanup_threshold:
                recommendations.append("Consider running cleanup operation")
            if memory_percent > MEMORY_THRESHOLD_HIGH:
                recommendations.append("High memory usage - immediate cleanup recommended")
            if available_memory_percent < 20:
                recommendations.append("Low available memory - consider reducing batch sizes")
            
            return {
                "rss_bytes": memory_info.rss,
                "vms_bytes": memory_info.vms,
                "percent": memory_percent,
                "available_percent": available_memory_percent,
                "recommendations": recommendations
            }
        except (ImportError, AttributeError, TypeError):
            return {
                "rss_bytes": 1000000,
                "vms_bytes": 2000000,
                "percent": 5.0,
                "available_percent": 95.0,
                "recommendations": []
            }
    
    def get_memory_usage_bytes(self) -> int:
        """Get memory usage as RSS bytes (for backward compatibility)."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except (ImportError, AttributeError, TypeError):
            return 0
    
    @property
    def last_memory_check(self) -> float:
        return self._last_memory_check

    def get_resource_info(self, resources: Dict, processed_languages: set) -> Dict[str, Any]:
        """Get information about managed resources."""
        try:
            current_time = time.time()
            resource_types = {}
            total_resources = len(resources) if resources else 0
            total_size = 0
            
            if resources:
                for resource_key, resource_info in resources.items():
                    resource_type = resource_info.resource_type if hasattr(resource_info, 'resource_type') else 'unknown'
                    resource_types[resource_type] = resource_types.get(resource_type, 0) + 1
                    total_size += getattr(resource_info, 'size_bytes', 0)
            
            if resources:
                ages = [current_time - info.created_at for info in resources.values() if hasattr(info, 'created_at')]
                avg_age = sum(ages) / len(ages) if ages else 0
                max_age = max(ages) if ages else 0
                min_age = min(ages) if ages else 0
            else:
                avg_age = max_age = min_age = 0
            
            return {
                "total_resources": total_resources,
                "resource_types": resource_types,
                "total_size_bytes": total_size,
                "average_resource_age_seconds": avg_age,
                "oldest_resource_age_seconds": max_age,
                "newest_resource_age_seconds": min_age,
                "processed_languages": len(processed_languages) if processed_languages else 0,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def calculate_memory_efficiency(self) -> float:
        """Calculate memory optimization efficiency."""
        try:
            if self.performance_metrics['total_memory_freed_bytes'] > 0:
                efficiency = min(100.0, (self.performance_metrics['total_memory_freed_bytes'] / (1024 * 1024)) * 10)
                return efficiency
            return 0.0
        except (KeyError, TypeError, ValueError):
            return 0.0