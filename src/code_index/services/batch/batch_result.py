"""
Batch processing result model and related utilities.

This module contains the BatchProcessingResult dataclass and related
functionality for batch processing operations.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class BatchProcessingResult:
    """Result of batch processing operation."""
    results: Dict[str, List[Any]]
    success: bool
    processed_files: int
    failed_files: int
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    performance_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}


def create_error_result(
    error_message: str,
    failed_files: int,
    metadata: Optional[Dict[str, Any]] = None
) -> BatchProcessingResult:
    """Create an error result for batch processing failures."""
    return BatchProcessingResult(
        results={},
        success=False,
        processed_files=0,
        failed_files=failed_files,
        error_message=error_message,
        metadata=metadata or {"error": error_message},
        performance_metrics={"error": error_message}
    )


def create_success_result(
    results: Dict[str, List[Any]],
    processed_files: int,
    failed_files: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
    performance_metrics: Optional[Dict[str, Any]] = None
) -> BatchProcessingResult:
    """Create a success result for batch processing."""
    return BatchProcessingResult(
        results=results,
        success=True,
        processed_files=processed_files,
        failed_files=failed_files,
        metadata=metadata,
        performance_metrics=performance_metrics
    )