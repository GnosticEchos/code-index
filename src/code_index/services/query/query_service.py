"""
Query service for handling query operations.

This service handles query operations and status queries.
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from ...config import Config
from ...service_validation import ValidationResult
from ...errors import ErrorHandler, ErrorCategory, ErrorSeverity, ErrorContext


class QueryService:
    """Service for handling query operations."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize query service."""
        self.error_handler = error_handler or ErrorHandler()
    
    def get_status(self, config: Config) -> Dict[str, Any]:
        """Get system status information."""
        start_time = time.time()
        try:
            metadata = {
                "system_info": self._get_system_info(),
                "workspace_info": {},
                "config_info": self._get_config_info(config),
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
            
            # Add workspace info if workspace is configured
            if getattr(config, "workspace_path"):
                from ..shared.workspace_service import WorkspaceService
                workspace_service = WorkspaceService(self.error_handler)
                metadata["workspace_info"] = workspace_service.get_workspace_info(getattr(config, "workspace_path"))
            
            return metadata
        except Exception as e:
            error_context = ErrorContext(
                component="query_service",
                operation="get_status"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )
            return {
                "error": error_response.message,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "timestamp": datetime.now().isoformat(),
                "workspace_path": getattr(config, "workspace_path", "not configured"),
                "search_min_score": getattr(config, "search_min_score", "not configured"),
                "search_max_results": getattr(config, "search_max_results", "not configured"),
                "search_strategy": getattr(config, "search_strategy", "not configured")
            }
    
    def validate_query_config(self, config: Config) -> ValidationResult:
        """Validate query configuration."""
        start_time = time.time()
        errors: List[str] = []
        metadata: Dict[str, Any] = {}
        
        try:
            # Validate query configuration
            if not getattr(config, "search_min_score"):
                errors.append("No minimum score configured")
            elif getattr(config, "search_min_score") < 0 or getattr(config, "search_min_score") > 1:
                errors.append("search_min_score must be between 0 and 1")
            elif getattr(config, "search_max_results") <= 0:
                errors.append("Max results must be positive")
            elif getattr(config, "search_strategy") not in ["text", "similarity", "embedding"]:
                errors.append("Invalid search strategy")
            
            combined_error = "; ".join(errors) if errors else None
            return ValidationResult(
                service="query_service",
                valid=len(errors) == 0,
                error=combined_error,
                details=metadata,
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check query configuration"]
            )
        except Exception as e:
            error_context = ErrorContext(
                component="query_service",
                operation="validate_query_config"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="query_service",
                valid=False,
                error=error_response.message,
                details={},
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check query configuration"]
            )
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        import platform
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "system": platform.system(),
            "processor": platform.processor(),
            "memory": "Unknown",
            "disk_usage": "Unknown"
        }
    
    def _get_config_info(self, config: Config) -> Dict[str, Any]:
        """Get configuration information."""
        return {
            "search_min_score": getattr(config, "search_min_score", "not configured"),
            "search_max_results": getattr(config, "search_max_results", "not configured"),
            "search_strategy": getattr(config, "search_strategy", "not configured"),
            "workspace_path": getattr(config, "workspace_path", "not configured")
        }
    
    def _get_memory_info(self) -> Optional[str]:
        """Get memory information."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return f"{memory.percent:.1f}% used"
        except Exception:
            return None
