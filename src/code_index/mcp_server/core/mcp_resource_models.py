"""
Resource management models and dataclasses for MCP Server.

This module contains the data classes used by the resource management system.
"""

from typing import Dict, Any, Callable
from dataclasses import dataclass, field


@dataclass
class ResourceInfo:
    """Information about a managed resource."""
    resource_id: str
    resource_type: str
    created_at: float
    cleanup_func: Callable[[], None]
    metadata: Dict[str, Any] = field(default_factory=dict)