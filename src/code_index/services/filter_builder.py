"""
Filter builder module for building filters in configuration queries.

This module handles building filters for file status, workspace status, and other queries.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


class FilterBuilder:
    """
    Builds filters for configuration query operations.
    """
    
    def __init__(self):
        pass
    
    def build_file_processed_filter(self, file_path: str, config: Any) -> Dict[str, Any]:
        """Build a filter for checking if a file is processed."""
        return {
            "file_path": file_path,
            "workspace": config.workspace_path
        }
    
    def build_workspace_validity_filter(self, workspace: str) -> Dict[str, Any]:
        """Build a filter for workspace validity."""
        workspace_path = Path(workspace)
        is_valid = workspace_path.exists() and workspace_path.is_dir()
        return {
            "workspace": workspace,
            "is_valid": is_valid,
            "exists": workspace_path.exists(),
            "is_dir": workspace_path.is_dir() if workspace_path.exists() else False
        }
    
    def build_project_type_filter(self, markers: List[str]) -> str:
        """Build a filter for project type detection."""
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
    
    def build_service_health_filter(self, validation_results: List[Any]) -> Dict[str, Any]:
        """Build a filter for service health."""
        failed_validations = [result for result in validation_results if not result.valid]
        return {
            "is_healthy": len(failed_validations) == 0,
            "failed_count": len(failed_validations),
            "total_count": len(validation_results)
        }
    
    def build_cache_validity_filter(self, last_update: Optional[datetime], max_age_seconds: int = 30) -> bool:
        """Build a filter for cache validity."""
        if last_update is None:
            return False
        return (datetime.now() - last_update).total_seconds() < max_age_seconds


def create_filter_builder() -> FilterBuilder:
    """Factory function to create a FilterBuilder."""
    return FilterBuilder()
