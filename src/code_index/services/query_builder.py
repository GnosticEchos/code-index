"""
Query builder module for building configuration queries.

This module handles building queries for status, validation, and search operations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from ..config import Config


class QueryBuilder:
    """
    Builds queries for configuration query operations.
    """
    
    def __init__(self, error_handler=None):
        self.error_handler = error_handler
    
    def build_status_query(self, config: Config, include_health: bool = True, include_workspace: bool = True) -> Dict[str, Any]:
        """Build a status query."""
        return {
            "include_health": include_health,
            "include_workspace": include_workspace,
            "timestamp": datetime.now().isoformat()
        }
    
    def build_config_validation_query(self, config: Optional[Config], config_path: str, workspace_path: str) -> Dict[str, Any]:
        """Build a config validation query."""
        return {
            "config_path": config_path,
            "workspace_path": workspace_path,
            "timestamp": datetime.now().isoformat()
        }
    
    def build_search_query(self, query: str, config: Optional[Config], config_path: str, workspace_path: str) -> Dict[str, Any]:
        """Build a search query."""
        return {
            "query": query,
            "config_path": config_path,
            "workspace_path": workspace_path,
            "timestamp": datetime.now().isoformat()
        }
    
    def build_file_status_query(self, file_path: str, config: Config) -> Dict[str, Any]:
        """Build a file status query."""
        return {
            "file_path": file_path,
            "workspace_path": config.workspace_path,
            "timestamp": datetime.now().isoformat()
        }
    
    def build_processing_stats_query(self, config: Config) -> Dict[str, Any]:
        """Build a processing stats query."""
        return {
            "workspace_path": config.workspace_path,
            "timestamp": datetime.now().isoformat()
        }
    
    def build_workspace_status_query(self, workspace: str, config: Config) -> Dict[str, Any]:
        """Build a workspace status query."""
        return {
            "workspace": workspace,
            "timestamp": datetime.now().isoformat()
        }


def create_query_builder(error_handler=None) -> QueryBuilder:
    """Factory function to create a QueryBuilder."""
    return QueryBuilder(error_handler)
