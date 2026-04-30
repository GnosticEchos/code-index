"""
Command executor module for executing configuration commands.

This module handles executing configuration commands like save, update, export, etc.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of a configuration command operation."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


class CommandExecutor:
    """
    Executes configuration commands.
    """
    
    def __init__(self, error_handler=None, logger=None):
        self.error_handler = error_handler
        self.logger = logger or logging.getLogger(__name__)
    
    def execute_save_config(self, config: Any, file_path: str, format: str = "json") -> CommandResult:
        """Execute save config command."""
        try:
            config_dict = config.to_dict()
            output_path = Path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "yaml":
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)
            
            return CommandResult(
                success=True,
                message=f"Configuration saved to {file_path}",
                details={"file_path": file_path, "format": format}
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message="Failed to save configuration",
                error=str(e)
            )
    
    def execute_update_config(self, config: Any, updates: Dict[str, Any]) -> CommandResult:
        """Execute update config command."""
        try:
            from ...config import Config
            updated_config = Config()
            updated_config.update_from_dict(config.to_dict())
            
            # Track what was updated
            updated_keys = []
            rejected_keys = []
            
            for key, value in updates.items():
                if hasattr(updated_config, key):
                    setattr(updated_config, key, value)
                    updated_keys.append(key)
                else:
                    rejected_keys.append(key)
            
            return CommandResult(
                success=True,
                message=f"Configuration updated: {', '.join(updated_keys)}",
                details={
                    "updated_keys": updated_keys,
                    "rejected_keys": rejected_keys
                }
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message="Failed to update configuration",
                error=str(e)
            )
    
    def execute_export_config(self, config: Any, file_path: str, format: str = "json", include_metadata: bool = True) -> CommandResult:
        """Execute export config command."""
        try:
            export_data = config.to_dict()
            
            if include_metadata:
                export_data["_metadata"] = {
                    "exported_at": datetime.now().isoformat(),
                    "exported_from": config.workspace_path,
                    "format": format
                }
            
            output_path = Path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "yaml":
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(export_data, f, default_flow_style=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
            
            return CommandResult(
                success=True,
                message=f"Configuration exported to {file_path}",
                details={"file_path": file_path, "format": format}
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message="Failed to export configuration",
                error=str(e)
            )
    
    def execute_reset_to_defaults(self, config: Any) -> CommandResult:
        """Execute reset to defaults command."""
        try:
            from ...config import Config
            reset_config = Config()
            reset_config.workspace_path = config.workspace_path
            
            return CommandResult(
                success=True,
                message="Configuration reset to defaults",
                details={"reset_config": reset_config.to_dict()}
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message="Failed to reset configuration",
                error=str(e)
            )


def create_command_executor(error_handler=None, logger=None) -> CommandExecutor:
    """Factory function to create a CommandExecutor."""
    return CommandExecutor(error_handler, logger)
