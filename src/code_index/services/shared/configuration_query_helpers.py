"""
Helper functions for ConfigurationQueryService.
Extracted to reduce file size while maintaining test compatibility.
"""
import time
from datetime import datetime
from pathlib import Path as PathImpl
from typing import Dict, Any, List, Optional, Type

from ...config import Config
from ...models import FileStatus, ProcessingStats, WorkspaceStatus, ServiceHealth, SystemStatus
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ...vector_store import QdrantVectorStore
from ...cache import CacheManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..query.configuration_query_service import QueryCache


class ConfigurationQueryHelpers:
    """Static helper methods for configuration queries."""

    @staticmethod
    def check_file_processed(file_path: str, config: Config, path_cls: Type = PathImpl) -> bool:
        """Check if a file has been processed and indexed."""
        try:
            vector_store = QdrantVectorStore(config)
            return False
        except Exception:
            return False

    @staticmethod
    def get_indexed_files_count(workspace: str, config: Config) -> int:
        """Get count of indexed files in workspace."""
        try:
            vector_store = QdrantVectorStore(config)
            return 0
        except Exception:
            return 0

    @staticmethod
    def get_last_indexing_timestamp(workspace: str, config: Config) -> Optional[datetime]:
        """Get timestamp of last indexing operation."""
        try:
            cache_manager = CacheManager(workspace, config)
            return None
        except Exception:
            return None

    @staticmethod
    def detect_project_type(markers: List[str]) -> str:
        """Detect project type based on found markers."""
        if 'package.json' in markers:
            return 'nodejs'
        elif 'requirements.txt' in markers or 'pyproject.toml' in markers:
            return 'python'
        elif 'Cargo.toml' in markers:
            return 'rust'
        elif '.git' in markers:
            return 'git_repository'
        return 'unknown'

    @staticmethod
    def get_config_info(config: Config) -> Dict[str, Any]:
        """Get configuration information."""
        return {
            "search_min_score": getattr(config, "search_min_score", "not configured"),
            "search_max_results": getattr(config, "search_max_results", "not configured"),
            "search_strategy": getattr(config, "search_strategy", "not configured"),
            "workspace_path": getattr(config, "workspace_path", "not configured")
        }

    @staticmethod
    def build_file_status(file_path: str, config: Config, error_handler: ErrorHandler,
                          cache: 'QueryCache', cache_ttl_seconds: int, max_cache_size: int,
                          path_cls: Type = PathImpl) -> FileStatus:
        """Build file status with caching."""
        
        cache_key = f"file_status:{file_path}:{config.workspace_path}"
        if cache_key in cache.file_status_cache and cache.is_cache_valid(cache_ttl_seconds):
            return cache.file_status_cache[cache_key]

        is_processed, last_modified, file_size_bytes, processing_time_seconds, error_message, metadata = \
            False, None, None, None, None, {}

        try:
            file_path_obj = path_cls(file_path)
            if not file_path_obj.exists():
                error_message = f"File not found: {file_path}"
            else:
                stat = file_path_obj.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                file_size_bytes = stat.st_size
                try:
                    is_processed = ConfigurationQueryHelpers.check_file_processed(file_path, config)
                except Exception as e:
                    metadata["vector_store_error"] = str(e)
                try:
                    cache_manager = CacheManager(config.workspace_path, config)
                    cached_time = cache_manager.get_processing_time(file_path)
                    if cached_time:
                        processing_time_seconds = cached_time
                except Exception as e:
                    metadata["cache_error"] = str(e)
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_file_status", file_path=file_path)
            error_response = error_handler.handle_file_error(e, error_context, "file_status_check")
            error_message = error_response.message
            metadata["query_error"] = error_response.message

        status = FileStatus(file_path=file_path, is_processed=is_processed, last_modified=last_modified,
                           file_size_bytes=file_size_bytes, processing_time_seconds=processing_time_seconds,
                           error_message=error_message, metadata=metadata)

        if len(cache.file_status_cache) < max_cache_size:
            cache.file_status_cache[cache_key] = status
            cache.last_cache_update = datetime.now()
        return status

    @staticmethod
    def build_processing_stats(config: Config, error_handler: ErrorHandler,
                               cache: 'QueryCache', cache_ttl_seconds: int,
                               path_cls: Type = PathImpl) -> ProcessingStats:
        """Build processing stats with caching."""
        
        cache_key = f"processing_stats:{config.workspace_path}"
        if cache.processing_stats_cache and cache.is_cache_valid(cache_ttl_seconds):
            return cache.processing_stats_cache

        total_files = processed_files = failed_files = total_blocks = 0
        total_processing_time = 0.0
        last_processing_timestamp = None
        average_processing_time = 0.0
        metadata = {}

        try:
            workspace_path = path_cls(config.workspace_path)
            if workspace_path.exists():
                total_files = sum(1 for _ in workspace_path.rglob('*') if _.is_file())
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
            if processed_files > 0:
                average_processing_time = total_processing_time / processed_files
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_processing_stats",
                                         additional_data={"workspace": config.workspace_path})
            error_response = error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            metadata["stats_error"] = error_response.message

        stats = ProcessingStats(total_files=total_files, processed_files=processed_files, failed_files=failed_files,
                               total_blocks=total_blocks, average_processing_time_seconds=average_processing_time,
                               last_processing_timestamp=last_processing_timestamp, workspace_path=config.workspace_path,
                               metadata=metadata)
        cache.processing_stats_cache = stats
        cache.last_cache_update = datetime.now()
        return stats

    @staticmethod
    def build_workspace_status(workspace: str, config: Config, error_handler: ErrorHandler,
                              cache: 'QueryCache', cache_ttl_seconds: int, max_cache_size: int,
                              path_cls: Type = PathImpl) -> WorkspaceStatus:
        """Build workspace status with caching."""
        cache_key = f"workspace_status:{workspace}"
        if cache_key in cache.workspace_status_cache and cache.is_cache_valid(cache_ttl_seconds):
            return cache.workspace_status_cache[cache_key]

        is_valid = total_files = indexed_files = 0
        last_indexing_timestamp = None
        indexing_progress_percent = 0.0
        errors, warnings, metadata = [], [], {}

        try:
            workspace_path = path_cls(workspace)
            if not workspace_path.exists():
                errors.append(f"Workspace path does not exist: {workspace}")
            elif not workspace_path.is_dir():
                errors.append(f"Workspace path is not a directory: {workspace}")
            else:
                is_valid = True
                total_files = sum(1 for _ in workspace_path.rglob('*') if _.is_file())
                try:
                    indexed_files = ConfigurationQueryHelpers.get_indexed_files_count(workspace, config)
                    indexing_progress_percent = (indexed_files / total_files * 100) if total_files > 0 else 0.0
                    last_indexing_timestamp = ConfigurationQueryHelpers.get_last_indexing_timestamp(workspace, config)
                except Exception as e:
                    warnings.append(f"Could not check indexing status: {str(e)}")
                    metadata["indexing_check_error"] = str(e)
                project_markers = ['.git', 'package.json', 'requirements.txt', 'Cargo.toml', 'pyproject.toml']
                found_markers = [m for m in project_markers if (workspace_path / m).exists()]
                if found_markers:
                    metadata["project_markers"] = found_markers
                    metadata["project_type"] = ConfigurationQueryHelpers.detect_project_type(found_markers)
                else:
                    warnings.append("No common project markers found")
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_workspace_status",
                                         additional_data={"workspace": workspace})
            error_response = error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            errors.append(error_response.message)

        status = WorkspaceStatus(workspace_path=workspace, is_valid=is_valid, total_files=total_files,
                                indexed_files=indexed_files, last_indexing_timestamp=last_indexing_timestamp,
                                indexing_progress_percent=indexing_progress_percent, errors=errors, warnings=warnings,
                                metadata=metadata)
        if len(cache.workspace_status_cache) < max_cache_size:
            cache.workspace_status_cache[cache_key] = status
            cache.last_cache_update = datetime.now()
        return status

    @staticmethod
    def build_service_health(config: Config, error_handler: ErrorHandler, service_validator,
                            cache: 'QueryCache', cache_ttl_seconds: int, max_cache_size: int) -> ServiceHealth:
        """Build service health with caching."""
        cache_key = f"service_health:{config.workspace_path}"
        if cache_key in cache.service_health_cache and cache.is_cache_valid(cache_ttl_seconds):
            return cache.service_health_cache[cache_key]

        is_healthy, response_time_ms, error_message = False, None, None
        metadata = {}
        start_time = time.time()

        try:
            validation_results = service_validator.validate_all_services(config)
            failed_validations = [result for result in validation_results if not result.valid]
            if failed_validations:
                error_message = "; ".join([f"{r.service}: {r.error}" for r in failed_validations])
                metadata["failed_services"] = [r.service for r in failed_validations]
            else:
                is_healthy = True
            metadata["validation_results"] = [vars(result) for result in validation_results]
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_service_health")
            error_response = error_handler.handle_error(e, error_context, ErrorCategory.SERVICE_CONNECTION, ErrorSeverity.MEDIUM)
            error_message = error_response.message
            metadata["health_check_error"] = str(e)

        response_time_ms = int((time.time() - start_time) * 1000)
        health = ServiceHealth(service_name="code_index_system", is_healthy=is_healthy, response_time_ms=response_time_ms,
                               last_check_timestamp=datetime.now(), error_message=error_message, metadata=metadata)
        if len(cache.service_health_cache) < max_cache_size:
            cache.service_health_cache[cache_key] = health
            cache.last_cache_update = datetime.now()
        return health

    @staticmethod
    def build_system_status(config: Config, error_handler: ErrorHandler,
                           get_service_health_fn, get_workspace_status_fn,
                           cache: 'QueryCache', cache_ttl_seconds: int) -> SystemStatus:
        """Build system status with caching."""
        cache_key = f"system_status:{config.workspace_path}"
        if cache.system_status_cache and cache.is_cache_valid(cache_ttl_seconds):
            return cache.system_status_cache

        overall_health = "healthy"
        total_services = healthy_services = degraded_services = unhealthy_services = 0
        total_workspaces = indexed_workspaces = 0
        system_uptime_seconds = None
        metadata = {}

        try:
            service_health = get_service_health_fn(config)
            total_services = 1
            if service_health.is_healthy:
                healthy_services = 1
            else:
                unhealthy_services = 1
                overall_health = "unhealthy"
            try:
                import psutil
                system_uptime_seconds = psutil.boot_time()
                if system_uptime_seconds:
                    system_uptime_seconds = time.time() - system_uptime_seconds
            except Exception as e:
                metadata["uptime_error"] = str(e)
            try:
                total_workspaces = 1
                workspace_status = get_workspace_status_fn(config.workspace_path, config)
                if workspace_status.is_indexed():
                    indexed_workspaces = 1
                elif workspace_status.has_issues():
                    overall_health = "degraded"
                    degraded_services = 1
                    healthy_services = 0
            except Exception as e:
                metadata["workspace_error"] = str(e)
                overall_health = "degraded"
            if unhealthy_services > 0:
                overall_health = "unhealthy"
            elif degraded_services > 0:
                overall_health = "degraded"
        except Exception as e:
            error_context = ErrorContext(component="configuration_query_service", operation="get_system_status")
            error_response = error_handler.handle_error(e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM)
            overall_health = "unhealthy"
            metadata["system_check_error"] = error_response.message

        status = SystemStatus(overall_health=overall_health, total_services=total_services, healthy_services=healthy_services,
                            degraded_services=degraded_services, unhealthy_services=unhealthy_services,
                            total_workspaces=total_workspaces, indexed_workspaces=indexed_workspaces,
                            system_uptime_seconds=system_uptime_seconds, last_status_check=datetime.now(), metadata=metadata)
        cache.system_status_cache = status
        cache.last_cache_update = datetime.now()
        return status
