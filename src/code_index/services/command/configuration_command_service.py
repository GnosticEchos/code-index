"""
Configuration command service for handling configuration write operations.

This service provides write operations for configuration management including:
- Saving configuration to files
- Updating configuration values
- Applying CLI overrides
- Creating workspace-specific configurations
- Managing configuration cache

This follows the CQRS pattern where command operations are separated from query operations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar
from dataclasses import dataclass

from ...config import Config
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ...service_validation import ServiceValidator


T = TypeVar('T')


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


class ConfigurationCommandService:
    """
    CQRS Command Service for configuration write operations.

    This service handles all write operations for configuration management:
    - Save configuration to file (JSON/YAML)
    - Update configuration values
    - Apply CLI overrides
    - Create workspace-specific configurations
    - Manage configuration cache

    All operations return CommandResult for consistent feedback.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the configuration command service."""
        self.logger = logging.getLogger(__name__)
        self.error_handler = error_handler or ErrorHandler()
        self.service_validator = ServiceValidator(self.error_handler)

        # Command history for auditing
        self._command_history: List[Dict[str, Any]] = []

        # Cache for command results
        self._result_cache: Dict[str, CommandResult] = {}

    def save_config(
        self,
        config: Config,
        file_path: str = "code_index.json",
        format: str = "json"
    ) -> CommandResult:
        """
        Save configuration to a file.

        Args:
            config: Configuration object to save
            file_path: Path to save the configuration file
            format: Output format (json or yaml)

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info(f"Saving configuration to {file_path}")

            # Validate before saving
            config_service = self._get_config_service()
            validation_result = config_service.validate_and_initialize(config)
            if not validation_result.valid:
                return CommandResult(
                    success=False,
                    message="Configuration validation failed",
                    error=validation_result.error,
                    details={"validation_error": validation_result.error}
                )

            # Convert config to dictionary
            config_dict = config.to_dict()

            # Ensure the directory exists
            output_path = Path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file based on format
            if format.lower() == "yaml":
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)

            # Record command in history
            self._record_command("save_config", {
                "file_path": file_path,
                "format": format,
                "config_keys": list(config_dict.keys())
            })

            self.logger.info(f"Configuration saved successfully to {file_path}")

            return CommandResult(
                success=True,
                message=f"Configuration saved to {file_path}",
                details={
                    "file_path": file_path,
                    "format": format,
                    "workspace_path": config.workspace_path
                }
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="save_config",
                additional_data={"file_path": file_path}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.HIGH
            )
            self.logger.error(f"Failed to save configuration: {error_response.message}")

            return CommandResult(
                success=False,
                message="Failed to save configuration",
                error=error_response.message,
                details={"file_path": file_path}
            )

    def update_config(
        self,
        config: Config,
        updates: Dict[str, Any]
    ) -> CommandResult:
        """
        Update configuration with new values.

        Args:
            config: Base configuration to update
            updates: Dictionary of configuration updates

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info(f"Updating configuration with {len(updates)} changes")

            # Create a copy to avoid modifying the original
            updated_config = Config()
            updated_config.update_from_dict(config.to_dict())

            # Track what was updated
            updated_keys = []
            rejected_keys = []

            # Apply updates using validated override mechanism
            config_service = self._get_config_service()
            for key, value in updates.items():
                result = config_service._apply_validated_override(
                    updated_config,
                    key,
                    value,
                    source="command"
                )
                if result:
                    updated_keys.append(key)
                else:
                    rejected_keys.append(key)
                    self.logger.warning(f"Update rejected for key: {key}")

            if not updated_keys:
                return CommandResult(
                    success=False,
                    message="No valid configuration updates provided",
                    error="All updates were rejected",
                    details={"rejected_keys": rejected_keys}
                )

            # Validate the updated configuration
            validation_result = config_service.validate_and_initialize(updated_config)
            if not validation_result.valid:
                return CommandResult(
                    success=False,
                    message="Updated configuration validation failed",
                    error=validation_result.error,
                    details={
                        "updated_keys": updated_keys,
                        "rejected_keys": rejected_keys,
                        "validation_error": validation_result.error
                    }
                )

            # Record command in history
            self._record_command("update_config", {
                "updated_keys": updated_keys,
                "rejected_keys": rejected_keys
            })

            self.logger.info(f"Configuration updated successfully: {updated_keys}")

            return CommandResult(
                success=True,
                message=f"Configuration updated: {', '.join(updated_keys)}",
                details={
                    "updated_keys": updated_keys,
                    "rejected_keys": rejected_keys,
                    "workspace_path": updated_config.workspace_path
                }
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="update_config",
                additional_data={"update_keys": list(updates.keys())}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            self.logger.error(f"Failed to update configuration: {error_response.message}")

            return CommandResult(
                success=False,
                message="Failed to update configuration",
                error=error_response.message,
                details={"update_attempted": list(updates.keys())}
            )

    def apply_cli_overrides(
        self,
        config: Config,
        overrides: Dict[str, Any]
    ) -> CommandResult:
        """
        Apply CLI-style overrides to configuration.

        Args:
            config: Base configuration
            overrides: Dictionary of CLI override parameters

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info(f"Applying CLI overrides: {list(overrides.keys())}")

            config_service = self._get_config_service()
            updated_config = config_service.apply_cli_overrides(config, overrides)

            # Record command in history
            self._record_command("apply_cli_overrides", {
                "override_keys": list(overrides.keys())
            })

            self.logger.info("CLI overrides applied successfully")

            return CommandResult(
                success=True,
                message="CLI overrides applied successfully",
                details={
                    "applied_overrides": list(overrides.keys()),
                    "workspace_path": updated_config.workspace_path
                }
            )

        except ValueError as e:
            return CommandResult(
                success=False,
                message="CLI override application failed",
                error=str(e),
                details={"override_keys": list(overrides.keys())}
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="apply_cli_overrides",
                additional_data={"override_keys": list(overrides.keys())}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )

            return CommandResult(
                success=False,
                message="CLI override application failed",
                error=error_response.message,
                details={"override_keys": list(overrides.keys())}
            )

    def create_workspace_config(
        self,
        workspace_path: str,
        base_config_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Create workspace-specific configuration.

        Args:
            workspace_path: Path to the workspace
            base_config_path: Optional base configuration file path
            overrides: Optional configuration overrides

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info(f"Creating workspace-specific configuration for {workspace_path}")

            config_service = self._get_config_service()
            config = config_service.create_workspace_config(
                workspace_path=workspace_path,
                base_config_path=base_config_path,
                overrides=overrides
            )

            # Record command in history
            self._record_command("create_workspace_config", {
                "workspace_path": workspace_path,
                "base_config_path": base_config_path,
                "override_keys": list(overrides.keys()) if overrides else []
            })

            self.logger.info(f"Workspace configuration created for {workspace_path}")

            return CommandResult(
                success=True,
                message=f"Workspace configuration created for {workspace_path}",
                details={
                    "workspace_path": workspace_path,
                    "config": config.to_dict()
                }
            )

        except ValueError as e:
            return CommandResult(
                success=False,
                message="Workspace configuration creation failed",
                error=str(e),
                details={"workspace_path": workspace_path}
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="create_workspace_config",
                additional_data={"workspace_path": workspace_path}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )

            return CommandResult(
                success=False,
                message="Workspace configuration creation failed",
                error=error_response.message,
                details={"workspace_path": workspace_path}
            )

    def clear_command_cache(self, cache_type: str = "all") -> CommandResult:
        """
        Clear command-related caches.

        Args:
            cache_type: Type of cache to clear (all, result, history)

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info(f"Clearing command cache: {cache_type}")

            if cache_type == "all" or cache_type == "result":
                self._result_cache.clear()

            if cache_type == "all" or cache_type == "history":
                self._command_history.clear()

            # Record command in history
            self._record_command("clear_cache", {"cache_type": cache_type})

            self.logger.info(f"Command cache cleared: {cache_type}")

            return CommandResult(
                success=True,
                message=f"Command cache cleared: {cache_type}",
                details={"cache_type": cache_type}
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="clear_command_cache",
                additional_data={"cache_type": cache_type}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.LOW
            )

            return CommandResult(
                success=False,
                message="Failed to clear command cache",
                error=error_response.message,
                details={"cache_type": cache_type}
            )

    def export_config(
        self,
        config: Config,
        file_path: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> CommandResult:
        """
        Export configuration to a file with optional metadata.

        Args:
            config: Configuration object to export
            file_path: Path to export the configuration
            format: Output format (json or yaml)
            include_metadata: Include metadata in export

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info(f"Exporting configuration to {file_path}")

            # Build export data
            export_data = config.to_dict()

            if include_metadata:
                export_data["_metadata"] = {
                    "exported_at": datetime.now().isoformat(),
                    "exported_from": config.workspace_path,
                    "format": format
                }

            # Ensure the directory exists
            output_path = Path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file based on format
            if format.lower() == "yaml":
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(export_data, f, default_flow_style=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)

            # Record command in history
            self._record_command("export_config", {
                "file_path": file_path,
                "format": format,
                "include_metadata": include_metadata
            })

            self.logger.info(f"Configuration exported to {file_path}")

            return CommandResult(
                success=True,
                message=f"Configuration exported to {file_path}",
                details={
                    "file_path": file_path,
                    "format": format,
                    "include_metadata": include_metadata
                }
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="export_config",
                additional_data={"file_path": file_path}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )
            self.logger.error(f"Failed to export configuration: {error_response.message}")

            return CommandResult(
                success=False,
                message="Failed to export configuration",
                error=error_response.message,
                details={"file_path": file_path}
            )

    def reset_to_defaults(self, config: Config) -> CommandResult:
        """
        Reset configuration to default values.

        Args:
            config: Configuration object to reset

        Returns:
            CommandResult indicating success or failure
        """
        try:
            self.logger.info("Resetting configuration to defaults")

            # Create a new config with defaults
            reset_config = Config()
            reset_config.workspace_path = config.workspace_path

            # Record command in history
            self._record_command("reset_to_defaults", {})

            self.logger.info("Configuration reset to defaults")

            return CommandResult(
                success=True,
                message="Configuration reset to defaults",
                details={
                    "reset_config": reset_config.to_dict()
                }
            )

        except Exception as e:
            error_context = ErrorContext(
                component="configuration_command_service",
                operation="reset_to_defaults"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.LOW
            )

            return CommandResult(
                success=False,
                message="Failed to reset configuration",
                error=error_response.message
            )

    def get_command_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get command history for auditing.

        Args:
            limit: Maximum number of commands to return

        Returns:
            List of command history entries
        """
        return self._command_history[-limit:]

    def get_command_info(self) -> Dict[str, Any]:
        """Get information about the command service."""
        return {
            "service": "ConfigurationCommandService",
            "command_count": len(self._command_history),
            "cache_size": len(self._result_cache),
            "last_command": self._command_history[-1] if self._command_history else None
        }

    # Private helper methods

    def _get_config_service(self):
        """Get the configuration service instance."""
        from ..config_service import ConfigurationService
        return ConfigurationService(self.error_handler)

    def _record_command(self, command_name: str, details: Dict[str, Any]) -> None:
        """Record a command in the history."""
        self._command_history.append({
            "command": command_name,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })