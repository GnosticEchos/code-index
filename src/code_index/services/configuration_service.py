"""
ConfigurationService for CQRS pattern implementation (Sprint 3.3).

This service handles query operations for status and statistics, providing
read-only access to system state, file processing status, workspace status,
service health, and overall system metrics. This is separate from the
ConfigurationService in Sprint 2.2 which handles configuration management.
"""

import time
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..config import Config
from ..config_service import ConfigurationService as ConfigService
from ..service_validation import ServiceValidator, ValidationResult
from ..file_processing import FileProcessingService
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..models import FileStatus, ProcessingStats, WorkspaceStatus, ServiceHealth, SystemStatus
from ..cache import CacheManager
from ..vector_store import QdrantVectorStore


@dataclass
class QueryCache:
    """Cache for query results to improve performance."""

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
    CQRS Query Service for configuration and status operations.

    This service provides read-only query operations for:
    - File processing status and statistics
    - Workspace status and health monitoring
    - Service health and availability
    - System-wide status and metrics

    This is separate from the Sprint 2.2 ConfigurationService which handles
    configuration management and loading.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the ConfigurationService with required dependencies."""
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = ConfigService(self.error_handler)
        self.file_processor = FileProcessingService(self.error_handler)
        self.service_validator = ServiceValidator(self.error_handler)

        # Initialize cache for performance optimization
        self.cache = QueryCache()

        # Cache settings
        self.cache_ttl_seconds = 30  # Cache for 30 seconds
        self.max_cache_size = 1000  # Maximum cache entries

    def get_file_status(self, file_path: str, config: Config) -> FileStatus:
        """
        Query file processing status.

        Args:
            file_path: Path to the file to check
            config: Configuration object with workspace context

        Returns:
            FileStatus with processing information
        """
        try:
            # Check cache first
            cache_key = f"file_status:{file_path}:{config.workspace_path}"
            if cache_key in self.cache.file_status_cache:
                cached_status = self.cache.file_status_cache[cache_key]
                if self.cache.is_cache_valid(self.cache_ttl_seconds):
                    return cached_status

            # Get file information
            file_path_obj = Path(file_path)
            is_processed = False
            last_modified = None
            file_size_bytes = None
            processing_time_seconds = None
            error_message = None
            metadata = {}

            try:
                # Check if file exists
                if not file_path_obj.exists():
                    error_message = f"File not found: {file_path}"
                else:
                    # Get file metadata
                    stat = file_path_obj.stat()
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                    file_size_bytes = stat.st_size

                    # Check if file has been processed (check vector store)
                    try:
                        vector_store = QdrantVectorStore(config)
                        # This is a simplified check - in practice, you'd query the vector store
                        # for points associated with this file
                        is_processed = self._check_file_processed(file_path, config)
                    except Exception as e:
                        metadata["vector_store_error"] = str(e)
                        is_processed = False

                    # Get processing time from cache if available
                    try:
                        cache_manager = CacheManager(config.workspace_path, config)
                        cached_time = cache_manager.get_processing_time(file_path)
                        if cached_time:
                            processing_time_seconds = cached_time
                    except Exception as e:
                        metadata["cache_error"] = str(e)

            except Exception as e:
                error_context = ErrorContext(
                    component="configuration_service",
                    operation="get_file_status",
                    file_path=file_path
                )
                error_response = self.error_handler.handle_file_error(
                    e, error_context, "file_status_check"
                )
                error_message = error_response.message

            # Create file status result
            status = FileStatus(
                file_path=file_path,
                is_processed=is_processed,
                last_modified=last_modified,
                file_size_bytes=file_size_bytes,
                processing_time_seconds=processing_time_seconds,
                error_message=error_message,
                metadata=metadata
            )

            # Cache the result
            if len(self.cache.file_status_cache) < self.max_cache_size:
                self.cache.file_status_cache[cache_key] = status
                self.cache.last_cache_update = datetime.now()

            return status

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_service",
                operation="get_file_status",
                file_path=file_path
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )

            return FileStatus(
                file_path=file_path,
                is_processed=False,
                error_message=error_response.message,
                metadata={"query_error": str(e)}
            )

    def get_processing_stats(self, config: Config) -> ProcessingStats:
        """
        Query processing statistics and metrics.

        Args:
            config: Configuration object with workspace context

        Returns:
            ProcessingStats with aggregated statistics
        """
        try:
            # Check cache first
            cache_key = f"processing_stats:{config.workspace_path}"
            if (self.cache.processing_stats_cache and
                self.cache.is_cache_valid(self.cache_ttl_seconds)):
                return self.cache.processing_stats_cache

            # Initialize counters
            total_files = 0
            processed_files = 0
            failed_files = 0
            total_blocks = 0
            total_processing_time = 0.0
            last_processing_timestamp = None
            average_processing_time = 0.0
            metadata = {}

            try:
                # Get workspace statistics
                workspace_path = Path(config.workspace_path)

                # Count total files in workspace
                if workspace_path.exists():
                    total_files = sum(1 for _ in workspace_path.rglob('*') if _.is_file())

                    # Get processing statistics from cache
                    try:
                        cache_manager = CacheManager(config.workspace_path, config)
                        cache_stats = cache_manager.get_workspace_stats()

                        processed_files = cache_stats.get("processed_files", 0)
                        failed_files = cache_stats.get("failed_files", 0)
                        total_blocks = cache_stats.get("total_blocks", 0)
                        total_processing_time = cache_stats.get("total_processing_time", 0.0)
                        last_processing_timestamp = cache_stats.get("last_processing_timestamp")

                        if last_processing_timestamp and isinstance(last_processing_timestamp, str):
                            last_processing_timestamp = datetime.fromisoformat(last_processing_timestamp)

                    except Exception as e:
                        metadata["cache_stats_error"] = str(e)

                # Calculate average processing time
                if processed_files > 0:
                    average_processing_time = total_processing_time / processed_files

            except Exception as e:
                error_context = ErrorContext(
                    component="configuration_service",
                    operation="get_processing_stats",
                    additional_data={"workspace": config.workspace_path}
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
                )
                metadata["stats_error"] = error_response.message

            # Create processing stats result
            stats = ProcessingStats(
                total_files=total_files,
                processed_files=processed_files,
                failed_files=failed_files,
                total_blocks=total_blocks,
                average_processing_time_seconds=average_processing_time,
                last_processing_timestamp=last_processing_timestamp,
                workspace_path=config.workspace_path,
                metadata=metadata
            )

            # Cache the result
            self.cache.processing_stats_cache = stats
            self.cache.last_cache_update = datetime.now()

            return stats

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_service",
                operation="get_processing_stats",
                additional_data={"workspace": config.workspace_path}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )

            return ProcessingStats(
                total_files=0,
                processed_files=0,
                failed_files=0,
                total_blocks=0,
                average_processing_time_seconds=0.0,
                error_message=error_response.message,
                workspace_path=config.workspace_path,
                metadata={"query_error": str(e)}
            )

    def get_workspace_status(self, workspace: str, config: Config) -> WorkspaceStatus:
        """
        Query workspace status and health.

        Args:
            workspace: Path to the workspace to check
            config: Configuration object with workspace context

        Returns:
            WorkspaceStatus with workspace information
        """
        try:
            # Check cache first
            cache_key = f"workspace_status:{workspace}"
            if cache_key in self.cache.workspace_status_cache:
                cached_status = self.cache.workspace_status_cache[cache_key]
                if self.cache.is_cache_valid(self.cache_ttl_seconds):
                    return cached_status

            # Initialize workspace status
            is_valid = False
            total_files = 0
            indexed_files = 0
            last_indexing_timestamp = None
            indexing_progress_percent = 0.0
            errors = []
            warnings = []
            metadata = {}

            try:
                workspace_path = Path(workspace)

                # Check workspace validity
                if not workspace_path.exists():
                    errors.append(f"Workspace path does not exist: {workspace}")
                elif not workspace_path.is_dir():
                    errors.append(f"Workspace path is not a directory: {workspace}")
                else:
                    is_valid = True

                    # Count files
                    total_files = sum(1 for _ in workspace_path.rglob('*') if _.is_file())

                    # Get indexing status from vector store
                    try:
                        vector_store = QdrantVectorStore(config)
                        # This would query the vector store for indexed files count
                        indexed_files = self._get_indexed_files_count(workspace, config)
                        indexing_progress_percent = (indexed_files / total_files * 100) if total_files > 0 else 0.0

                        # Get last indexing timestamp
                        last_indexing_timestamp = self._get_last_indexing_timestamp(workspace, config)

                    except Exception as e:
                        warnings.append(f"Could not check indexing status: {str(e)}")
                        metadata["indexing_check_error"] = str(e)

                    # Check for common project markers
                    project_markers = ['.git', 'package.json', 'requirements.txt', 'Cargo.toml', 'pyproject.toml']
                    found_markers = []
                    for marker in project_markers:
                        if (workspace_path / marker).exists():
                            found_markers.append(marker)

                    if found_markers:
                        metadata["project_markers"] = found_markers
                        metadata["project_type"] = self._detect_project_type(found_markers)
                    else:
                        warnings.append("No common project markers found")

            except Exception as e:
                error_context = ErrorContext(
                    component="configuration_service",
                    operation="get_workspace_status",
                    additional_data={"workspace": workspace}
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
                )
                errors.append(error_response.message)

            # Create workspace status result
            status = WorkspaceStatus(
                workspace_path=workspace,
                is_valid=is_valid,
                total_files=total_files,
                indexed_files=indexed_files,
                last_indexing_timestamp=last_indexing_timestamp,
                indexing_progress_percent=indexing_progress_percent,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )

            # Cache the result
            if len(self.cache.workspace_status_cache) < self.max_cache_size:
                self.cache.workspace_status_cache[cache_key] = status
                self.cache.last_cache_update = datetime.now()

            return status

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_service",
                operation="get_workspace_status",
                additional_data={"workspace": workspace}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )

            return WorkspaceStatus(
                workspace_path=workspace,
                is_valid=False,
                total_files=0,
                indexed_files=0,
                errors=[error_response.message],
                metadata={"query_error": str(e)}
            )

    def get_service_health(self, config: Config) -> ServiceHealth:
        """
        Query service health and availability.

        Args:
            config: Configuration object with service endpoints

        Returns:
            ServiceHealth with service status information
        """
        try:
            # Check cache first
            cache_key = f"service_health:{config.workspace_path}"
            if cache_key in self.cache.service_health_cache:
                cached_health = self.cache.service_health_cache[cache_key]
                if self.cache.is_cache_valid(self.cache_ttl_seconds):
                    return cached_health

            # Initialize health check
            service_name = "code_index_system"
            is_healthy = False
            response_time_ms = None
            error_message = None
            metadata = {}

            start_time = time.time()

            try:
                # Validate all services
                validation_results = self.service_validator.validate_all_services(config)

                # Check if all services are healthy
                failed_validations = [result for result in validation_results if not result.valid]

                if failed_validations:
                    error_messages = [f"{result.service}: {result.error}" for result in failed_validations]
                    error_message = "; ".join(error_messages)
                    metadata["failed_services"] = [result.service for result in failed_validations]
                else:
                    is_healthy = True

                metadata["validation_results"] = [vars(result) for result in validation_results]

            except Exception as e:
                error_context = ErrorContext(
                    component="configuration_service",
                    operation="get_service_health"
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.SERVICE_CONNECTION, ErrorSeverity.MEDIUM
                )
                error_message = error_response.message
                metadata["health_check_error"] = str(e)

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Create service health result
            health = ServiceHealth(
                service_name=service_name,
                is_healthy=is_healthy,
                response_time_ms=response_time_ms,
                last_check_timestamp=datetime.now(),
                error_message=error_message,
                metadata=metadata
            )

            # Cache the result
            if len(self.cache.service_health_cache) < self.max_cache_size:
                self.cache.service_health_cache[cache_key] = health
                self.cache.last_cache_update = datetime.now()

            return health

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_service",
                operation="get_service_health"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SERVICE_CONNECTION, ErrorSeverity.MEDIUM
            )

            return ServiceHealth(
                service_name="code_index_system",
                is_healthy=False,
                error_message=error_response.message,
                metadata={"query_error": str(e)}
            )

    def get_system_status(self, config: Config) -> SystemStatus:
        """
        Query overall system status and metrics.

        Args:
            config: Configuration object with system context

        Returns:
            SystemStatus with comprehensive system information
        """
        try:
            # Check cache first
            cache_key = f"system_status:{config.workspace_path}"
            if (self.cache.system_status_cache and
                self.cache.is_cache_valid(self.cache_ttl_seconds)):
                return self.cache.system_status_cache

            # Initialize system status
            overall_health = "healthy"
            total_services = 0
            healthy_services = 0
            degraded_services = 0
            unhealthy_services = 0
            total_workspaces = 0
            indexed_workspaces = 0
            system_uptime_seconds = None
            metadata = {}

            try:
                # Get service health
                service_health = self.get_service_health(config)
                total_services = 1
                if service_health.is_healthy:
                    healthy_services = 1
                else:
                    unhealthy_services = 1
                    overall_health = "unhealthy"

                # Get system uptime
                try:
                    system_uptime_seconds = psutil.boot_time()
                    if system_uptime_seconds:
                        system_uptime_seconds = time.time() - system_uptime_seconds
                except Exception as e:
                    metadata["uptime_error"] = str(e)

                # Get workspace information
                try:
                    # This would typically query a database or configuration
                    # For now, we'll use the current workspace
                    total_workspaces = 1
                    workspace_status = self.get_workspace_status(config.workspace_path, config)
                    if workspace_status.is_indexed():
                        indexed_workspaces = 1
                    elif workspace_status.has_issues():
                        overall_health = "degraded"
                        degraded_services = 1
                        healthy_services = 0

                except Exception as e:
                    metadata["workspace_error"] = str(e)
                    overall_health = "degraded"

                # Determine overall health
                if unhealthy_services > 0:
                    overall_health = "unhealthy"
                elif degraded_services > 0:
                    overall_health = "degraded"
                else:
                    overall_health = "healthy"

            except Exception as e:
                error_context = ErrorContext(
                    component="configuration_service",
                    operation="get_system_status"
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
                )
                overall_health = "unhealthy"
                metadata["system_check_error"] = error_response.message

            # Create system status result
            status = SystemStatus(
                overall_health=overall_health,
                total_services=total_services,
                healthy_services=healthy_services,
                degraded_services=degraded_services,
                unhealthy_services=unhealthy_services,
                total_workspaces=total_workspaces,
                indexed_workspaces=indexed_workspaces,
                system_uptime_seconds=system_uptime_seconds,
                last_status_check=datetime.now(),
                metadata=metadata
            )

            # Cache the result
            self.cache.system_status_cache = status
            self.cache.last_cache_update = datetime.now()

            return status

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_service",
                operation="get_system_status"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )

            return SystemStatus(
                overall_health="unhealthy",
                total_services=0,
                healthy_services=0,
                degraded_services=0,
                unhealthy_services=1,
                total_workspaces=0,
                indexed_workspaces=0,
                error_message=error_response.message,
                metadata={"query_error": str(e)}
            )

    def clear_cache(self) -> None:
        """Clear all cached query results."""
        self.cache.invalidate_cache()

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache status and performance."""
        return {
            "cache_enabled": True,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_cache_size": self.max_cache_size,
            "file_status_cache_size": len(self.cache.file_status_cache),
            "workspace_status_cache_size": len(self.cache.workspace_status_cache),
            "service_health_cache_size": len(self.cache.service_health_cache),
            "last_cache_update": self.cache.last_cache_update.isoformat() if self.cache.last_cache_update else None,
            "cache_valid": self.cache.is_cache_valid(self.cache_ttl_seconds)
        }

    # Helper methods for internal use

    def _check_file_processed(self, file_path: str, config: Config) -> bool:
        """Check if a file has been processed and indexed."""
        try:
            # This is a simplified implementation
            # In practice, this would query the vector store for file status
            vector_store = QdrantVectorStore(config)
            # Query for points associated with this file
            # For now, return False as a placeholder
            return False
        except Exception:
            return False

    def _get_indexed_files_count(self, workspace: str, config: Config) -> int:
        """Get count of indexed files in workspace."""
        try:
            # This is a simplified implementation
            # In practice, this would query the vector store for file counts
            vector_store = QdrantVectorStore(config)
            # Query for indexed files count
            # For now, return 0 as a placeholder
            return 0
        except Exception:
            return 0

    def _get_last_indexing_timestamp(self, workspace: str, config: Config) -> Optional[datetime]:
        """Get timestamp of last indexing operation."""
        try:
            # This is a simplified implementation
            # In practice, this would query the vector store or cache for timestamps
            cache_manager = CacheManager(workspace, config)
            # Get last indexing time from cache
            # For now, return None as a placeholder
            return None
        except Exception:
            return None

    def _detect_project_type(self, markers: List[str]) -> str:
        """Detect project type based on found markers."""
        if 'package.json' in markers:
            return 'nodejs'
        elif 'requirements.txt' in markers or 'pyproject.toml' in markers:
            return 'python'
        elif 'Cargo.toml' in markers:
            return 'rust'
        elif '.git' in markers:
            return 'git_repository'
        else:
            return 'unknown'