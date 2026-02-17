"""
Command result module for CQRS command operations.

This module defines the CommandResult dataclass for consistent
command operation feedback.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of a configuration command operation."""
    success: bool
    message: str
    details: Dict[str, Any] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}