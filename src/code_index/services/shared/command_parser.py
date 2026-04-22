"""
Command parser module for parsing configuration commands.

This module handles parsing and validating configuration commands.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    """Parsed command result."""
    command_type: str
    params: Dict[str, Any]
    valid: bool
    errors: List[str]


class CommandParser:
    """
    Parses and validates configuration commands.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def parse_save_config_command(self, config: Any, file_path: str, format: str = "json") -> ParsedCommand:
        """Parse save config command."""
        errors = []
        
        if not file_path:
            errors.append("file_path is required")
        
        if format not in ["json", "yaml"]:
            errors.append("format must be json or yaml")
        
        return ParsedCommand(
            command_type="save_config",
            params={"file_path": file_path, "format": format},
            valid=len(errors) == 0,
            errors=errors
        )
    
    def parse_update_config_command(self, config: Any, updates: Dict[str, Any]) -> ParsedCommand:
        """Parse update config command."""
        errors = []
        
        if not updates:
            errors.append("updates cannot be empty")
        
        return ParsedCommand(
            command_type="update_config",
            params={"updates": updates},
            valid=len(errors) == 0,
            errors=errors
        )
    
    def parse_apply_overrides_command(self, config: Any, overrides: Dict[str, Any]) -> ParsedCommand:
        """Parse apply overrides command."""
        errors = []
        
        if not overrides:
            errors.append("overrides cannot be empty")
        
        return ParsedCommand(
            command_type="apply_overrides",
            params={"overrides": overrides},
            valid=len(errors) == 0,
            errors=errors
        )
    
    def parse_create_workspace_command(self, workspace_path: str, base_config_path: Optional[str], overrides: Optional[Dict[str, Any]]) -> ParsedCommand:
        """Parse create workspace command."""
        errors = []
        
        if not workspace_path:
            errors.append("workspace_path is required")
        
        return ParsedCommand(
            command_type="create_workspace_config",
            params={
                "workspace_path": workspace_path,
                "base_config_path": base_config_path,
                "overrides": overrides or {}
            },
            valid=len(errors) == 0,
            errors=errors
        )
    
    def parse_export_command(self, config: Any, file_path: str, format: str = "json", include_metadata: bool = True) -> ParsedCommand:
        """Parse export command."""
        errors = []
        
        if not file_path:
            errors.append("file_path is required")
        
        return ParsedCommand(
            command_type="export_config",
            params={
                "file_path": file_path,
                "format": format,
                "include_metadata": include_metadata
            },
            valid=len(errors) == 0,
            errors=errors
        )


def create_command_parser(logger=None) -> CommandParser:
    """Factory function to create a CommandParser."""
    return CommandParser(logger)
