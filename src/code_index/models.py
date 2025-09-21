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
