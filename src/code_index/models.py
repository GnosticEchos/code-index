"""
Data models for the code index tool.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


class CodeBlock:
    """Represents a code block extracted from a file."""

    def __init__(self, file_path: str, identifier: str, type: str, start_line: int,
                  end_line: int, content: str, file_hash: str, segment_hash: str):
        self.file_path = file_path
        self.identifier = identifier
        self.type = type
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.file_hash = file_hash
        self.segment_hash = segment_hash


@dataclass
class IndexingResult:
    """Structured result for workspace indexing operations."""

    processed_files: int
    total_blocks: int
    errors: List[str]
    warnings: List[str]
    timed_out_files: List[str]
    processing_time_seconds: float
    timestamp: datetime
    workspace_path: str
    config_summary: Dict[str, Any]

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def is_successful(self) -> bool:
        """Check if indexing completed successfully."""
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """Check if there were any warnings during indexing."""
        return len(self.warnings) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the indexing result."""
        return {
            "processed_files": self.processed_files,
            "total_blocks": self.total_blocks,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "timed_out_files": len(self.timed_out_files),
            "processing_time_seconds": self.processing_time_seconds,
            "successful": self.is_successful(),
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ProcessingResult:
    """Result for file processing operations."""

    file_path: str
    success: bool
    blocks_processed: int
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.metadata is None:
            self.metadata = {}

    def is_successful(self) -> bool:
        """Check if file processing was successful."""
        return self.success

    def has_error(self) -> bool:
        """Check if there was an error during processing."""
        return self.error is not None


@dataclass
class ValidationResult:
    """Result for workspace validation operations."""

    workspace_path: str
    valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    validation_time_seconds: float

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    def is_valid(self) -> bool:
        """Check if workspace validation passed."""
        return self.valid

    def has_issues(self) -> bool:
        """Check if there are any errors or warnings."""
        return len(self.errors) > 0 or len(self.warnings) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the validation result."""
        return {
            "workspace_path": self.workspace_path,
            "valid": self.valid,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "validation_time_seconds": self.validation_time_seconds
        }


@dataclass
class SearchMatch:
    """Individual search match result."""

    file_path: str
    start_line: int
    end_line: int
    code_chunk: str
    match_type: str  # "function", "class", "method", "variable", "comment", "text"
    score: float
    adjusted_score: float
    metadata: Dict[str, Any]

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    def get_context_lines(self, before: int = 2, after: int = 2) -> List[str]:
        """Get context lines around the match."""
        # For now, return the code_chunk as-is since we don't have full file context
        # In a real implementation, this would read the file to get full context
        lines = self.code_chunk.split('\n')
        return lines

    def to_dict(self) -> Dict[str, Any]:
        """Convert search match to dictionary."""
        return {
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "code_chunk": self.code_chunk,
            "match_type": self.match_type,
            "score": self.score,
            "adjusted_score": self.adjusted_score,
            "metadata": self.metadata
        }


@dataclass
class SearchResult:
    """Structured result for search operations."""

    query: str
    matches: List[SearchMatch]
    total_found: int
    execution_time_seconds: float
    search_method: str  # "text", "similarity", "embedding"
    config_summary: Dict[str, Any]
    errors: List[str]
    warnings: List[str]

    def __post_init__(self):
        """Initialize lists if not provided."""
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def is_successful(self) -> bool:
        """Check if search completed successfully."""
        return len(self.errors) == 0

    def has_matches(self) -> bool:
        """Check if search found any matches."""
        return len(self.matches) > 0

    def get_top_matches(self, limit: int = 10) -> List[SearchMatch]:
        """Get top matches sorted by adjusted score."""
        return sorted(self.matches, key=lambda x: x.adjusted_score, reverse=True)[:limit]

    def get_matches_by_file(self) -> Dict[str, List[SearchMatch]]:
        """Group matches by file path."""
        grouped = {}
        for match in self.matches:
            if match.file_path not in grouped:
                grouped[match.file_path] = []
            grouped[match.file_path].append(match)
        return grouped

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the search result."""
        return {
            "query": self.query,
            "total_found": self.total_found,
            "matches_returned": len(self.matches),
            "execution_time_seconds": self.execution_time_seconds,
            "search_method": self.search_method,
            "successful": self.is_successful(),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "top_score": max((m.adjusted_score for m in self.matches), default=0.0),
            "avg_score": sum(m.adjusted_score for m in self.matches) / len(self.matches) if self.matches else 0.0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "query": self.query,
            "matches": [match.to_dict() for match in self.matches],
            "total_found": self.total_found,
            "execution_time_seconds": self.execution_time_seconds,
            "search_method": self.search_method,
            "config_summary": self.config_summary,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.get_summary()
        }


@dataclass
class FileStatus:
    """Result for file processing status queries."""

    file_path: str
    is_processed: bool
    last_modified: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.metadata is None:
            self.metadata = {}

    def is_successful(self) -> bool:
        """Check if file processing was successful."""
        return self.is_processed and self.error_message is None

    def has_error(self) -> bool:
        """Check if there was an error during processing."""
        return self.error_message is not None

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the file status."""
        return {
            "file_path": self.file_path,
            "is_processed": self.is_processed,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "file_size_bytes": self.file_size_bytes,
            "processing_time_seconds": self.processing_time_seconds,
            "successful": self.is_successful(),
            "has_error": self.has_error()
        }


@dataclass
class ProcessingStats:
    """Result for processing statistics queries."""

    total_files: int
    processed_files: int
    failed_files: int
    total_blocks: int
    average_processing_time_seconds: float
    last_processing_timestamp: Optional[datetime] = None
    workspace_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.metadata is None:
            self.metadata = {}

    def get_success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100.0

    def get_failure_rate(self) -> float:
        """Get the failure rate as a percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.failed_files / self.total_files) * 100.0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the processing statistics."""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "total_blocks": self.total_blocks,
            "average_processing_time_seconds": self.average_processing_time_seconds,
            "success_rate_percent": self.get_success_rate(),
            "failure_rate_percent": self.get_failure_rate(),
            "last_processing_timestamp": self.last_processing_timestamp.isoformat() if self.last_processing_timestamp else None,
            "workspace_path": self.workspace_path
        }


@dataclass
class WorkspaceStatus:
    """Result for workspace status queries."""

    workspace_path: str
    is_valid: bool
    total_files: int
    indexed_files: int
    last_indexing_timestamp: Optional[datetime] = None
    indexing_progress_percent: float = 0.0
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

    def is_indexed(self) -> bool:
        """Check if workspace has been indexed."""
        return self.indexed_files > 0

    def has_issues(self) -> bool:
        """Check if there are any errors or warnings."""
        return len(self.errors) > 0 or len(self.warnings) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the workspace status."""
        return {
            "workspace_path": self.workspace_path,
            "is_valid": self.is_valid,
            "total_files": self.total_files,
            "indexed_files": self.indexed_files,
            "indexing_progress_percent": self.indexing_progress_percent,
            "last_indexing_timestamp": self.last_indexing_timestamp.isoformat() if self.last_indexing_timestamp else None,
            "is_indexed": self.is_indexed(),
            "has_issues": self.has_issues(),
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }


@dataclass
class ServiceHealth:
    """Result for service health queries."""

    service_name: str
    is_healthy: bool
    response_time_ms: Optional[int] = None
    last_check_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.metadata is None:
            self.metadata = {}

    def is_available(self) -> bool:
        """Check if service is available."""
        return self.is_healthy

    def has_error(self) -> bool:
        """Check if there was an error during health check."""
        return self.error_message is not None

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the service health."""
        return {
            "service_name": self.service_name,
            "is_healthy": self.is_healthy,
            "response_time_ms": self.response_time_ms,
            "last_check_timestamp": self.last_check_timestamp.isoformat() if self.last_check_timestamp else None,
            "is_available": self.is_available(),
            "has_error": self.has_error(),
            "error_message": self.error_message
        }


@dataclass
class SystemStatus:
    """Result for system status queries."""

    overall_health: str  # "healthy", "degraded", "unhealthy"
    total_services: int
    healthy_services: int
    degraded_services: int
    unhealthy_services: int
    total_workspaces: int
    indexed_workspaces: int
    system_uptime_seconds: Optional[float] = None
    last_status_check: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.metadata is None:
            self.metadata = {}

    def is_system_healthy(self) -> bool:
        """Check if overall system is healthy."""
        return self.overall_health == "healthy"

    def get_health_percentage(self) -> float:
        """Get the health percentage of services."""
        if self.total_services == 0:
            return 0.0
        return (self.healthy_services / self.total_services) * 100.0

    def get_indexing_coverage(self) -> float:
        """Get the indexing coverage percentage."""
        if self.total_workspaces == 0:
            return 0.0
        return (self.indexed_workspaces / self.total_workspaces) * 100.0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the system status."""
        return {
            "overall_health": self.overall_health,
            "total_services": self.total_services,
            "healthy_services": self.healthy_services,
            "degraded_services": self.degraded_services,
            "unhealthy_services": self.unhealthy_services,
            "total_workspaces": self.total_workspaces,
            "indexed_workspaces": self.indexed_workspaces,
            "system_uptime_seconds": self.system_uptime_seconds,
            "last_status_check": self.last_status_check.isoformat() if self.last_status_check else None,
            "is_system_healthy": self.is_system_healthy(),
            "health_percentage": self.get_health_percentage(),
            "indexing_coverage": self.get_indexing_coverage()
        }
