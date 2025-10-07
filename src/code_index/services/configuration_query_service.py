"""
Configuration query service for handling configuration queries and status queries.
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..config import Config
from ..models import ValidationResult
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..services.config_loader import ConfigLoaderService
from ..services.health_service import HealthService
from ..services.query_service import QueryService

class ConfigurationQueryService:
    """Service for handling configuration queries and status queries."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize configuration query service."""
        self.error_handler = error_handler or ErrorHandler()
        self.config_loader = ConfigLoaderService(error_handler)
        self.health_service = HealthService(error_handler)
        self.query_service = QueryService(error_handler)
    
    def get_status(self, config: Config, include_health: bool = True, include_workspace: bool = True) -> Dict[str, Any]:
        """Get comprehensive system status information."""
        start_time = time.time()
        try:
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": 0,
                "config_info": self._get_config_info(config),
                "workspace_info": {},
                "health_info": [],
                "config_validation": [],
                "config_with_health": False
            }
            
            # Add health information if requested
            if include_health:
                health_results = self.health_service.check_health(config)
                metadata["health_info"] = health_results
                metadata["config_with_health"] = True
            
            # Add workspace info if requested
            if include_workspace:
                from ..services.workspace_service import WorkspaceService
                workspace_service = WorkspaceService(self.error_handler)
                metadata["workspace_info"] = workspace_service.get_workspace_info(config.workspace_path)
            
            # Validate configuration
            config_loader = ConfigLoaderService(self.error_handler)
            validation_result = config_loader.validate_and_initialize(config, validate_services=include_health)
            metadata["config_validation"] = {
                "valid": validation_result.valid,
                "error": validation_result.error,
                "response_time_ms": validation_result.response_time_ms
            }
            
            metadata["response_time_ms"] = int((time.time() - start_time) * 1000)
            return metadata
        except Exception as e:
            error_context = ErrorContext(
                component="configuration_query_service",
                operation="get_status"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )
            return {
                "error": error_response.message,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "timestamp": datetime.now().isoformat(),
                "config_with_health": False,
                "workspace_path": getattr(config, "workspace_path", "not configured"),
                "search_min_score": getattr(config, "search_min_score", "not configured"),
                "search_max_results": getattr(config, "search_max_results", "not configured"),
                "search_strategy": getattr(config, "search_strategy", "not configured")
            }
    
    def validate_config(self, config: Optional[Config] = None, config_path: str = "code_index.json", workspace_path: str = ".") -> ValidationResult:
        """Validate configuration with comprehensive validation."""
        start_time = time.time()
        try:
            if config is None:
                config_loader = ConfigLoaderService(self.error_handler)
                config = config_loader.load_with_fallback(config_path, workspace_path)
            
            # Validate configuration values
            config_loader = ConfigLoaderService(self.error_handler)
            validation_result = config_loader.validate_and_initialize(config)
            
            return ValidationResult(
                service="configuration_query_service",
                valid=validation_result.valid,
                error=validation_result.error,
                details={
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "config_path": getattr(config, "workspace_path", "not configured"),
                    "config_with_health": getattr(config, "config_with_health", False),
                    "config_info": self._get_config_info(config),
                }
            )
        except Exception as e:
            error_context = ErrorContext(
                component="configuration_query_service",
                operation="validate_config"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="configuration_query_service",
                valid=False,
                error=error_response.message,
                details={},
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check configuration and service connectivity"]
            )
    
    def search_with_config(self, query: str, config: Optional[Config] = None, config_path: str = "code_index.json", workspace_path: str = ".") -> Dict[str, Any]:
        """Execute search with configuration validation."""
        try:
            if config is None:
                config_loader = ConfigLoaderService(self.error_handler)
                config = config_loader.load_with_fallback(config_path, workspace_path)
            
            # Validate configuration
            validation_result = self.validate_config(config)
            if not validation_result.valid:
                return {
                    "error": validation_result.error,
                    "results": [],
                    "total_found": 0
                }
            
            # Execute search using QueryService
            query_service = QueryService(self.error_handler)
            search_result = query_service.search_code(query, config)
            
            return {
                "results": search_result.matches,
                "total_found": search_result.total_found,
                "search_strategy": getattr(config, "search_strategy", "similarity"),
                "search_min_score": getattr(config, "search_min_score", 0.4),
                "search_max_results": getattr(config, "search_max_results", 50),
                "workspace_path": getattr(config, "workspace_path", "not configured")
            }
        except Exception as e:
            error_context = ErrorContext(
                component="configuration_query_service",
                operation="search_with_config"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
            )
            return {
                "error": error_response.message,
                "results": [],
                "total_found": 0
            }
    
    def _get_config_info(self, config: Config) -> Dict[str, Any]:
        """Get configuration information."""
        return {
            "search_min_score": getattr(config, "search_min_score", "not configured"),
            "search_max_results": getattr(config, "search_max_results", "not configured"),
            "search_strategy": getattr(config, "search_strategy", "not configured"),
            "workspace_path": getattr(config, "workspace_path", "not configured")
        }