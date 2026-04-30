"""
Resource cleanup service for Tree-sitter resources.
"""
import time
import gc
from typing import Dict, Any


class ResourceCleanup:
    """Cleans up Tree-sitter resources."""
    
    def __init__(self, max_resource_age: int = 1800, debug_enabled: bool = False):
        self.max_resource_age = max_resource_age
        self.debug_enabled = debug_enabled
        self._last_cleanup = time.time()
        self._resources: Dict[str, Any] = {}
        self._resource_refs: Dict[str, Any] = {}
        self._parsers: Dict[str, Any] = {}
    
    def cleanup_all(self) -> Dict[str, int]:
        """Clean up all resources."""
        try:
            stats = {
                "parsers_cleaned": 0,
                "queries_cleaned": 0,
                "languages_cleared": 0,
                "resources_removed": 0
            }
            
            # Clean up parsers
            if hasattr(self, '_parsers'):
                for language_key, parser in list(self._parsers.items()):
                    if hasattr(parser, 'delete'):
                        parser.delete()
                        stats["parsers_cleaned"] += 1
                    elif hasattr(parser, 'reset'):
                        parser.reset()
                        stats["parsers_cleaned"] += 1
                self._parsers.clear()
            
            # Clean up old resources
            stats["resources_removed"] = self._cleanup_old_resources()
            
            # Clear languages
            if hasattr(self, '_processed_languages'):
                stats["languages_cleared"] = len(self._processed_languages)
                self._processed_languages.clear()
            else:
                self._processed_languages = set()  # type: ignore[attr-defined]
            
            # Force garbage collection
            gc.collect()
            
            return stats
        except Exception as e:
            return {"error": str(e)}  # type: ignore[return-value]
    
    def _cleanup_old_resources(self) -> int:
        """Clean up old resources based on age."""
        current_time = time.time()
        removed_count = 0
        
        expired_resources = []
        for resource_key, resource_info in self._resources.items():
            if current_time - resource_info.last_used > self.max_resource_age:
                expired_resources.append(resource_key)
        
        for resource_key in expired_resources:
            if resource_key in self._resources:
                del self._resources[resource_key]
            if resource_key in self._resource_refs:
                del self._resource_refs[resource_key]
            removed_count += 1
        
        self._last_cleanup = current_time
        return removed_count
    
    def perform_aggressive_cleanup(self):
        """Perform aggressive cleanup when memory is high."""
        try:
            original_max_age = self.max_resource_age
            self.max_resource_age = min(self.max_resource_age, 300)
            removed_count = self._cleanup_old_resources()
            self.max_resource_age = original_max_age
            return removed_count
        except (AttributeError, TypeError, ValueError):
            return 0
    
    def update_usage(self, resource_key: str, resource_type: str):
        """Update resource usage statistics."""
        current_time = time.time()
        if not hasattr(self, '_resources'):
            self._resources = {}
        
        if resource_key not in self._resources:
            from .resource_allocator import ResourceInfo
            self._resources[resource_key] = ResourceInfo(
                resource_type=resource_type,
                created_at=current_time,
                last_used=current_time,
                use_count=1
            )
        else:
            self._resources[resource_key].last_used = current_time
            self._resources[resource_key].use_count += 1
    
    @property
    def last_cleanup(self) -> float:
        return self._last_cleanup