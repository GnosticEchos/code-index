"""
Configuration query service for handling configuration queries and status queries.
"""
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ...config import Config
from ...models import FileStatus, ProcessingStats, WorkspaceStatus, ServiceHealth, SystemStatus
from ...service_validation import ValidationResult
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..command.config_loader import ConfigLoaderService
from ..shared.health_service import HealthService
from .query_service import QueryService
from ...service_validation import ServiceValidator
from ...file_processing import FileProcessingService
from ..shared.configuration_query_helpers import ConfigurationQueryHelpers


@dataclass
class QueryCache:
    """Cache for query results to improve performance."""
    file_status_cache: Dict[str, FileStatus] = field(default_factory=dict)
    processing_stats_cache: Optional[ProcessingStats] = None
    workspace_status_cache: Dict[str, WorkspaceStatus] = field(default_factory=dict)
    service_health_cache: Dict[str, ServiceHealth] = field(default_factory=dict)
    system_status_cache: Optional[SystemStatus] = None
    last_cache_update: Optional[datetime] = None

    def __post_init__(self):
        if self.file_status_cache is None:
            self.file_status_cache = {}
        if self.workspace_status_cache is None:
            self.workspace_status_cache = {}
        if self.service_health_cache is None:
            self.service_health_cache = {}

    def is_cache_valid(self, max_age_seconds: int = 30) -> bool:
        if self.last_cache_update is None:
            return False
        return (datetime.now() - self.last_cache_update).seconds < max_age_seconds

    def invalidate_cache(self) -> None:
        self.file_status_cache.clear()
        self.processing_stats_cache = None
        self.workspace_status_cache.clear()
        self.service_health_cache.clear()
        self.system_status_cache = None
        self.last_cache_update = None


class ConfigurationQueryService:
    """Service for handling configuration queries and status queries."""

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        self.error_handler = error_handler or ErrorHandler()
        self.config_loader = ConfigLoaderService(self.error_handler)
        self.health_service = HealthService(self.error_handler)
        self.query_service = QueryService(self.error_handler)
        self.service_validator = ServiceValidator(self.error_handler)
        self.file_processor = FileProcessingService(self.error_handler)
        self.cache = QueryCache()
        self.cache_ttl_seconds = 30
        self.max_cache_size = 1000
        self._helpers = ConfigurationQueryHelpers()

    def get_status(self, config: Config, include_health: bool = True, include_workspace: bool = True) -> Dict[str, Any]:
        start_time = time.time()
        try:
            metadata = {"timestamp": datetime.now().isoformat(), "response_time_ms": 0,
                       "config_info": self._helpers.get_config_info(config), "workspace_info": {},
                       "health_info": [], "config_validation": [], "config_with_health": False}
            if include_health:
                health_results = self.health_service.check_health(config)
                metadata["health_info"] = health_results
                metadata["config_with_health"] = True
            if include_workspace:
                from ..shared.workspace_service import WorkspaceService
                workspace_service = WorkspaceService(self.error_handler)
                metadata["workspace_info"] = workspace_service.get_workspace_info(config.workspace_path)
            validation_result = self.config_loader.validate_and_initialize(config, validate_services=include_health)
            metadata["config_validation"] = {"valid": validation_result.valid, "error": validation_result.error,
                                              "response_time_ms": validation_result.response_time_ms}
            metadata["response_time_ms"] = int((time.time() - start_time) * 1000)
            return metadata
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_status")
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
            return {"error": error_response.message, "response_time_ms": int((time.time() - start_time) * 1000),
                    "timestamp": datetime.now().isoformat(), "config_with_health": False,
                    "workspace_path": getattr(config, "workspace_path", "not configured"),
                    "search_min_score": getattr(config, "search_min_score", "not configured"),
                    "search_max_results": getattr(config, "search_max_results", "not configured"),
                    "search_strategy": getattr(config, "search_strategy", "not configured")}

    def validate_config(self, config: Optional[Config] = None, config_path: str = "code_index.json",
                       workspace_path: str = ".") -> ValidationResult:
        start_time = time.time()
        try:
            if config is None:
                config = self.config_loader.load_with_fallback(config_path, workspace_path)
            validation_result = self.config_loader.validate_and_initialize(config)
            return ValidationResult(service="configuration_query_service", valid=validation_result.valid,
                                   error=validation_result.error,
                                   details={"response_time_ms": int((time.time() - start_time) * 1000),
                                           "config_path": getattr(config, "workspace_path", "not configured"),
                                           "config_with_health": getattr(config, "config_with_health", False),
                                           "config_info": self._helpers.get_config_info(config)})
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="validate_config")
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM)
            return ValidationResult(service="configuration_query_service", valid=False, error=error_response.message,
                                   details={}, response_time_ms=int((time.time() - start_time) * 1000),
                                   actionable_guidance=["Check configuration and service connectivity"])

    def search_with_config(self, query: str, config: Optional[Config] = None, config_path: str = "code_index.json",
                          workspace_path: str = ".") -> Dict[str, Any]:
        try:
            if config is None:
                config = self.config_loader.load_with_fallback(config_path, workspace_path)
            validation_result = self.validate_config(config)
            if not validation_result.valid:
                return {"error": validation_result.error, "results": [], "total_found": 0}
            search_result = self.query_service.search_code(query, config)
            return {"results": search_result.matches, "total_found": search_result.total_found,
                   "search_strategy": getattr(config, "search_strategy", "similarity"),
                   "search_min_score": getattr(config, "search_min_score", 0.4),
                   "search_max_results": getattr(config, "search_max_results", 50),
                   "workspace_path": getattr(config, "workspace_path", "not configured")}
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="search_with_config")
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM)
            return {"error": error_response.message, "results": [], "total_found": 0}

    def get_file_status(self, file_path: str, config: Config) -> FileStatus:
        try:
            return self._helpers.build_file_status(file_path, config, self.error_handler, self.cache,
                                                   self.cache_ttl_seconds, self.max_cache_size, Path)
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_file_status", file_path=file_path)
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            return FileStatus(file_path=file_path, is_processed=False, error_message=error_response.message,
                            metadata={"query_error": str(e)})

    def get_processing_stats(self, config: Config) -> ProcessingStats:
        try:
            return self._helpers.build_processing_stats(config, self.error_handler, self.cache, self.cache_ttl_seconds, Path)
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_processing_stats",
                                         additional_data={"workspace": config.workspace_path})
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            return ProcessingStats(total_files=0, processed_files=0, failed_files=0, total_blocks=0,
                                 average_processing_time_seconds=0.0, error_message=error_response.message,
                                 workspace_path=config.workspace_path, metadata={"query_error": str(e)})

    def get_workspace_status(self, workspace: str, config: Config) -> WorkspaceStatus:
        try:
            return self._helpers.build_workspace_status(workspace, config, self.error_handler, self.cache,
                                                         self.cache_ttl_seconds, self.max_cache_size, Path)
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_workspace_status",
                                         additional_data={"workspace": workspace})
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            return WorkspaceStatus(workspace_path=workspace, is_valid=False, total_files=0, indexed_files=0,
                                 errors=[error_response.message], metadata={"query_error": str(e)})

    def get_service_health(self, config: Config) -> ServiceHealth:
        try:
            return self._helpers.build_service_health(config, self.error_handler, self.service_validator, self.cache,
                                                       self.cache_ttl_seconds, self.max_cache_size)
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_service_health")
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.SERVICE_CONNECTION, ErrorSeverity.MEDIUM)
            return ServiceHealth(service_name="code_index_system", is_healthy=False, error_message=error_response.message,
                               metadata={"query_error": str(e)})

    def get_system_status(self, config: Config) -> SystemStatus:
        try:
            return self._helpers.build_system_status(config, self.error_handler, self.get_service_health,
                                                       self.get_workspace_status, self.cache, self.cache_ttl_seconds)
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_system_status")
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
            return SystemStatus(overall_health="unhealthy", total_services=0, healthy_services=0, degraded_services=0,
                               unhealthy_services=1, total_workspaces=0, indexed_workspaces=0,
                               error_message=error_response.message, metadata={"query_error": str(e)})

    def clear_cache(self) -> None:
        self.cache.invalidate_cache()

    def get_cache_info(self) -> Dict[str, Any]:
        return {"cache_enabled": True, "cache_ttl_seconds": self.cache_ttl_seconds, "max_cache_size": self.max_cache_size,
               "file_status_cache_size": len(self.cache.file_status_cache),
               "workspace_status_cache_size": len(self.cache.workspace_status_cache),
               "service_health_cache_size": len(self.cache.service_health_cache),
               "last_cache_update": self.cache.last_cache_update.isoformat() if self.cache.last_cache_update else None,
               "cache_valid": self.cache.is_cache_valid(self.cache_ttl_seconds)}