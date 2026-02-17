"""
ConfigurationService - Thin Facade for CQRS Pattern Implementation (Sprint 3.3).

This service acts as a unified facade that composes ConfigurationQueryService
and ConfigurationCommandService to provide backward compatibility while enabling
the CQRS pattern.

- Query operations are delegated to ConfigurationQueryService
- Command operations are delegated to ConfigurationCommandService

This separates read operations (queries) from write operations (commands),
improving maintainability and enabling independent scaling of query and command paths.
"""

import time
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ...config import Config
from ...config_service import ConfigurationService as ConfigService
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ...file_processing import FileProcessingService
from ...service_validation import ServiceValidator
from ...cache import CacheManager
from ...vector_store import QdrantVectorStore
from ...models import FileStatus, ProcessingStats, ServiceHealth, SystemStatus, WorkspaceStatus

from ..query.configuration_query_service import ConfigurationQueryService
from ..command.configuration_command_service import ConfigurationCommandService, CommandResult


@dataclass
class QueryCache:
    """Cache for query results to improve performance (delegated to query service)."""
    
    file_status_cache: Dict[str, FileStatus] = None
    processing_stats_cache: Optional[ProcessingStats] = None
    workspace_status_cache: Dict[str, WorkspaceStatus] = None
    service_health_cache: Dict[str, ServiceHealth] = None
    system_status_cache: Optional[SystemStatus] = None
    last_cache_update: Optional[datetime] = None

    def __post_init__(self):
        """Initialize cache dictionaries."""
        if self.file_status_cache is None:
            self.file_status_cache = {}
        if self.workspace_status_cache is None:
            self.workspace_status_cache = {}
        if self.service_health_cache is None:
            self.service_health_cache = {}

    def is_cache_valid(self, max_age_seconds: int = 30) -> bool:
        """Check if cache is still valid."""
        if self.last_cache_update is None:
            return False
        return (datetime.now() - self.last_cache_update).seconds < max_age_seconds

    def invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self.file_status_cache.clear()
        self.processing_stats_cache = None
        self.workspace_status_cache.clear()
        self.service_health_cache.clear()
        self.system_status_cache = None
        self.last_cache_update = None


class ConfigurationService:
    """
    Unified Configuration Service - Thin Facade for CQRS Pattern.
    
    This service provides a unified interface for configuration operations,
    delegating queries to ConfigurationQueryService and commands to
    ConfigurationCommandService.
    
    This approach maintains backward compatibility while enabling the CQRS
    pattern for better separation of concerns and scalability.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the ConfigurationService with required dependencies."""
        self.error_handler = error_handler or ErrorHandler()
        
        # Initialize composed services
        self.query_service = ConfigurationQueryService(self.error_handler)
        self.command_service = ConfigurationCommandService(self.error_handler)
        
        # Initialize cache (delegated to query service internally)
        self.cache = QueryCache()
        self.cache_ttl_seconds = 30
        self.max_cache_size = 1000

    # ==================== Backward Compatibility Properties ====================
    # These properties provide access to underlying services for backward compatibility
    
    @property
    def config_service(self) -> ConfigService:
        """Get the underlying config service (for backward compatibility)."""
        from ...config_service import ConfigurationService as ConfigService
        return ConfigService(self.error_handler)
    
    @property
    def file_processor(self) -> FileProcessingService:
        """Get the file processor (for backward compatibility)."""
        return FileProcessingService(self.error_handler)
    
    @property
    def service_validator(self) -> ServiceValidator:
        """Get the service validator (for backward compatibility)."""
        return ServiceValidator(self.error_handler)

    # ==================== Query Operations (Delegated to ConfigurationQueryService) ====================

    def get_file_status(self, file_path: str, config: Config) -> FileStatus:
        """
        Query file processing status.
        
        Args:
            file_path: Path to the file to check
            config: Configuration object with workspace context
        
        Returns:
            FileStatus with processing information
        """
        return self.query_service.get_file_status(file_path, config)

    def get_processing_stats(self, config: Config) -> ProcessingStats:
        """
        Query processing statistics and metrics.
        
        Args:
            config: Configuration object with workspace context
        
        Returns:
            ProcessingStats with aggregated statistics
        """
        return self.query_service.get_processing_stats(config)

    def get_workspace_status(self, workspace: str, config: Config) -> WorkspaceStatus:
        """
        Query workspace status and health.
        
        Args:
            workspace: Path to the workspace to check
            config: Configuration object with workspace context
        
        Returns:
            WorkspaceStatus with workspace information
        """
        return self.query_service.get_workspace_status(workspace, config)

    def get_service_health(self, config: Config) -> ServiceHealth:
        """
        Query service health and availability.
        
        Args:
            config: Configuration object with service endpoints
        
        Returns:
            ServiceHealth with service status information
        """
        return self.query_service.get_service_health(config)

    def get_system_status(self, config: Config) -> SystemStatus:
        """
        Query overall system status and metrics.
        
        Args:
            config: Configuration object with system context
        
        Returns:
            SystemStatus with comprehensive system information
        """
        return self.query_service.get_system_status(config)

    def clear_cache(self) -> None:
        """Clear all cached query results."""
        self.query_service.clear_cache()

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache status and performance."""
        return self.query_service.get_cache_info()

    # ==================== Command Operations (Delegated to ConfigurationCommandService) ====================

    def save_config(
        self,
        config: Config,
        file_path: str = "code_index.json",
        format: str = "json"
    ) -> CommandResult:
        """
        Save configuration to a file.
        
        Args:
            config: Configuration object to save
            file_path: Path to save the configuration file
            format: Output format (json or yaml)
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.save_config(config, file_path, format)

    def update_config(
        self,
        config: Config,
        updates: Dict[str, Any]
    ) -> CommandResult:
        """
        Update configuration with new values.
        
        Args:
            config: Base configuration to update
            updates: Dictionary of configuration updates
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.update_config(config, updates)

    def apply_cli_overrides(
        self,
        config: Config,
        overrides: Dict[str, Any]
    ) -> CommandResult:
        """
        Apply CLI-style overrides to configuration.
        
        Args:
            config: Base configuration
            overrides: Dictionary of CLI override parameters
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.apply_cli_overrides(config, overrides)

    def create_workspace_config(
        self,
        workspace_path: str,
        base_config_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Create workspace-specific configuration.
        
        Args:
            workspace_path: Path to the workspace
            base_config_path: Optional base configuration file path
            overrides: Optional configuration overrides
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.create_workspace_config(
            workspace_path, base_config_path, overrides
        )

    def clear_command_cache(self, cache_type: str = "all") -> CommandResult:
        """
        Clear command-related caches.
        
        Args:
            cache_type: Type of cache to clear (all, result, history)
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.clear_command_cache(cache_type)

    def export_config(
        self,
        config: Config,
        file_path: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> CommandResult:
        """
        Export configuration to a file with optional metadata.
        
        Args:
            config: Configuration object to export
            file_path: Path to export the configuration
            format: Output format (json or yaml)
            include_metadata: Include metadata in export
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.export_config(config, file_path, format, include_metadata)

    def reset_to_defaults(self, config: Config) -> CommandResult:
        """
        Reset configuration to default values.
        
        Args:
            config: Configuration object to reset
        
        Returns:
            CommandResult indicating success or failure
        """
        return self.command_service.reset_to_defaults(config)

    def get_command_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get command history for auditing.
        
        Args:
            limit: Maximum number of commands to return
        
        Returns:
            List of command history entries
        """
        return self.command_service.get_command_history(limit)

    def get_command_info(self) -> Dict[str, Any]:
        """Get information about the command service."""
        return self.command_service.get_command_info()