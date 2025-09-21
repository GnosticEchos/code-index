"""
Configuration Service for centralized configuration management.

This module provides a centralized configuration service that consolidates
configuration loading from multiple sources with fallback mechanisms and
supports CLI overrides, workspace-specific configurations, and validation.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union, TypeVar, Type, Generic
from pathlib import Path
from dataclasses import dataclass, asdict

from .config import Config
from .service_validation import ServiceValidator, ValidationResult
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity

T = TypeVar('T')


@dataclass
class ConfigurationSource:
    """Represents a configuration source with priority and metadata."""
    name: str
    priority: int
    path: Optional[str] = None
    source_type: str = "default"  # "default", "env", "file", "cli", "workspace"


class ConfigurationService:
    """
    Centralized configuration management service.

    This service consolidates configuration loading from multiple sources:
    - Default configuration (hardcoded fallbacks)
    - Environment variables
    - Configuration files (JSON, YAML)
    - CLI arguments and options
    - Workspace-specific overrides

    The service provides fallback mechanisms and type-safe configuration access.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None, test_mode: bool = False):
        """Initialize the configuration service."""
        self.logger = logging.getLogger(__name__)
        self.error_handler = error_handler or ErrorHandler()
        self._config_cache: Dict[str, Config] = {}
        self._validation_cache: Dict[str, List[ValidationResult]] = {}
        self.test_mode = test_mode

        # Define configuration sources in priority order (highest first)
        self._sources = [
            ConfigurationSource("cli_overrides", 100, source_type="cli"),
            ConfigurationSource("workspace_config", 90, source_type="workspace"),
            ConfigurationSource("environment_variables", 80, source_type="env"),
            ConfigurationSource("config_file", 70, source_type="file"),
            ConfigurationSource("default_config", 10, source_type="default"),
        ]

    def load_with_fallback(
        self,
        config_path: str = "code_index.json",
        workspace_path: str = ".",
        overrides: Optional[Dict[str, Any]] = None
    ) -> Config:
        """
        Load configuration with fallback to defaults and multiple sources.

        Args:
            config_path: Path to configuration file
            workspace_path: Workspace directory path
            overrides: Optional configuration overrides

        Returns:
            Loaded and validated configuration

        Raises:
            ValueError: If configuration is invalid or services fail validation
        """
        cache_key = f"{config_path}:{workspace_path}:{hash(str(overrides))}"

        # Check cache first
        if cache_key in self._config_cache:
            self.logger.debug(f"Returning cached configuration for {cache_key}")
            return self._config_cache[cache_key]

        try:
            self.logger.info(f"Loading configuration with fallback for workspace: {workspace_path}")

            # Start with default configuration
            config = Config()
            config.workspace_path = workspace_path

            # Load configuration from file if it exists
            if os.path.exists(config_path):
                config = Config.from_file(config_path)
                config.workspace_path = workspace_path  # Override workspace path
                self.logger.info(f"Loaded configuration from {config_path}")
            else:
                self.logger.info(f"Configuration file {config_path} not found, using defaults")

            # Apply environment variable overrides
            config = self._apply_environment_overrides(config)

            # Apply workspace-specific configuration
            config = self._apply_workspace_config(config, workspace_path)

            # Apply CLI overrides if provided
            if overrides:
                config = self.apply_cli_overrides(config, overrides)

            # Validate configuration
            validation_result = self.validate_and_initialize(config)
            if not validation_result.valid:
                raise ValueError(f"Configuration validation failed: {validation_result.error}")

            # Cache the configuration
            self._config_cache[cache_key] = config
            self.logger.info("Configuration loaded successfully with fallback")

            return config

        except Exception as e:
            error_context = ErrorContext(
                component="config_service",
                operation="load_with_fallback",
                additional_data={
                    "config_path": config_path,
                    "workspace_path": workspace_path
                }
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.CRITICAL
            )
            self.logger.error(f"Failed to load configuration: {error_response.message}")
            raise ValueError(f"Configuration loading failed: {error_response.message}")

    def _apply_environment_overrides(self, config: Config) -> Config:
        """Apply environment variable overrides to configuration."""
        try:
            # Core service endpoints
            if os.getenv("OLLAMA_BASE_URL"):
                config.ollama_base_url = os.getenv("OLLAMA_BASE_URL")
            if os.getenv("OLLAMA_MODEL"):
                config.ollama_model = os.getenv("OLLAMA_MODEL")
            if os.getenv("QDRANT_URL"):
                config.qdrant_url = os.getenv("QDRANT_URL")
            if os.getenv("QDRANT_API_KEY"):
                config.qdrant_api_key = os.getenv("QDRANT_API_KEY")
            if os.getenv("WORKSPACE_PATH"):
                config.workspace_path = os.getenv("WORKSPACE_PATH")

            # Performance settings
            if os.getenv("CODE_INDEX_EMBED_TIMEOUT"):
                try:
                    config.embed_timeout_seconds = int(os.getenv("CODE_INDEX_EMBED_TIMEOUT"))
                except ValueError:
                    self.logger.warning("Invalid CODE_INDEX_EMBED_TIMEOUT value, ignoring")

            # Feature flags
            if os.getenv("CODE_INDEX_USE_TREE_SITTER"):
                config.use_tree_sitter = os.getenv("CODE_INDEX_USE_TREE_SITTER").lower() in ("true", "1", "yes")

            self.logger.debug("Applied environment variable overrides")
            return config

        except Exception as e:
            self.logger.warning(f"Error applying environment overrides: {e}")
            return config

    def _apply_workspace_config(self, config: Config, workspace_path: str) -> Config:
        """Apply workspace-specific configuration overrides."""
        try:
            # Look for workspace-specific config files
            workspace_config_files = [
                os.path.join(workspace_path, ".code_index.json"),
                os.path.join(workspace_path, ".code_index.yaml"),
                os.path.join(workspace_path, ".code_index.yml"),
                os.path.join(workspace_path, "code_index.json"),
            ]

            for config_file in workspace_config_files:
                if os.path.exists(config_file):
                    self.logger.info(f"Loading workspace-specific config from {config_file}")
                    config = self._load_config_file(config_file, config)
                    break

            return config

        except Exception as e:
            self.logger.warning(f"Error applying workspace config: {e}")
            return config

    def _load_config_file(self, file_path: str, base_config: Config) -> Config:
        """Load configuration from a file (JSON or YAML)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            # Apply file configuration to base config
            for key, value in data.items():
                if hasattr(base_config, key):
                    setattr(base_config, key, value)

            self.logger.debug(f"Loaded configuration from {file_path}")
            return base_config

        except Exception as e:
            self.logger.warning(f"Error loading config file {file_path}: {e}")
            return base_config

    def apply_cli_overrides(self, config: Config, overrides: Dict[str, Any]) -> Config:
        """
        Apply CLI-specific configuration overrides.

        Args:
            config: Base configuration to override
            overrides: Dictionary of CLI override parameters

        Returns:
            Configuration with CLI overrides applied
        """
        try:
            self.logger.info(f"Applying CLI overrides: {list(overrides.keys())}")

            # Create a copy of the config to avoid modifying the original
            new_config = Config()
            for key, value in vars(config).items():
                setattr(new_config, key, value)

            # Apply overrides
            for key, value in overrides.items():
                if hasattr(new_config, key):
                    old_value = getattr(new_config, key)
                    setattr(new_config, key, value)
                    self.logger.debug(f"Applied CLI override: {key} = {value} (was: {old_value})")
                else:
                    self.logger.warning(f"Unknown configuration parameter: {key}")

            # Validate the configuration with overrides
            validation_result = self.validate_and_initialize(new_config)
            if not validation_result.valid:
                raise ValueError(f"Configuration with CLI overrides is invalid: {validation_result.error}")

            return new_config

        except Exception as e:
            error_context = ErrorContext(
                component="config_service",
                operation="apply_cli_overrides",
                additional_data={"overrides": list(overrides.keys()) if overrides else []}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            self.logger.error(f"Failed to apply CLI overrides: {error_response.message}")
            raise ValueError(f"CLI override application failed: {error_response.message}")

    def validate_and_initialize(self, config: Config) -> ValidationResult:
        """
        Validate configuration and initialize services.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult indicating success or failure
        """
        try:
            cache_key = str(hash(str(vars(config))))

            # Check cache first
            if cache_key in self._validation_cache:
                self.logger.debug("Returning cached validation result")
                return self._validation_cache[cache_key]

            self.logger.info("Validating configuration and initializing services")

            # Validate configuration values
            validation_errors = self._validate_config_values(config)
            if validation_errors:
                return ValidationResult(
                    service="configuration",
                    valid=False,
                    error=f"Configuration validation failed: {', '.join(validation_errors)}"
                )

            # Validate services (skip in test mode)
            if not self.test_mode:
                service_validator = ServiceValidator(self.error_handler)
                validation_results = service_validator.validate_all_services(config)

                # Check for service validation failures
                failed_validations = [result for result in validation_results if not result.valid]
                if failed_validations:
                    error_messages = [f"{result.service}: {result.error}" for result in failed_validations]
                    return ValidationResult(
                        service="configuration",
                        valid=False,
                        error=f"Service validation failed: {', '.join(error_messages)}",
                        details={"validation_results": [vars(result) for result in validation_results]}
                    )
            else:
                # In test mode, create mock successful validation results
                validation_results = [
                    ValidationResult(service="ollama", valid=True, details={"test_mode": True}),
                    ValidationResult(service="qdrant", valid=True, details={"test_mode": True})
                ]

            # Cache successful validation (store the configuration result, not the service results)
            self._validation_cache[cache_key] = ValidationResult(
                service="configuration",
                valid=True,
                details={"validation_results": [vars(result) for result in validation_results]}
            )

            self.logger.info("Configuration validation and service initialization successful")
            return ValidationResult(
                service="configuration",
                valid=True,
                details={"validation_results": [vars(result) for result in validation_results]}
            )

        except Exception as e:
            error_context = ErrorContext(
                component="config_service",
                operation="validate_and_initialize"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            self.logger.error(f"Configuration validation failed: {error_response.message}")
            return ValidationResult(
                service="configuration",
                valid=False,
                error=error_response.message
            )

    def _validate_config_values(self, config: Config) -> List[str]:
        """Validate individual configuration values."""
        errors = []

        # Validate embedding length
        if config.embedding_length is None or config.embedding_length <= 0:
            errors.append("embedding_length must be a positive integer")

        # Validate chunking strategy
        valid_strategies = ["lines", "tokens", "treesitter"]
        if config.chunking_strategy not in valid_strategies:
            errors.append(f"chunking_strategy must be one of {valid_strategies}")

        # Validate search parameters
        if config.search_min_score < 0 or config.search_min_score > 1:
            errors.append("search_min_score must be between 0 and 1")

        if config.search_max_results <= 0:
            errors.append("search_max_results must be positive")

        # Validate timeout values
        if config.embed_timeout_seconds <= 0:
            errors.append("embed_timeout_seconds must be positive")

        # Validate file size limits
        if config.max_file_size_bytes <= 0:
            errors.append("max_file_size_bytes must be positive")

        # Validate Tree-sitter compatibility
        if config.chunking_strategy == "treesitter" and not config.use_tree_sitter:
            errors.append("chunking_strategy='treesitter' requires use_tree_sitter=true")

        return errors

    def create_workspace_config(
        self,
        workspace_path: str,
        base_config_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Config:
        """
        Create workspace-specific configuration.

        Args:
            workspace_path: Path to the workspace
            base_config_path: Optional base configuration file path
            overrides: Optional configuration overrides

        Returns:
            Workspace-specific configuration
        """
        try:
            self.logger.info(f"Creating workspace-specific configuration for {workspace_path}")

            # Start with base configuration
            if base_config_path and os.path.exists(base_config_path):
                config = Config.from_file(base_config_path)
            else:
                config = Config()

            # Set workspace path
            config.workspace_path = workspace_path

            # Apply workspace-specific overrides
            config = self._apply_workspace_config(config, workspace_path)

            # Apply additional overrides
            if overrides:
                config = self.apply_cli_overrides(config, overrides)

            # Validate the configuration
            validation_result = self.validate_and_initialize(config)
            if not validation_result.valid:
                raise ValueError(f"Workspace configuration validation failed: {validation_result.error}")

            self.logger.info(f"Created workspace-specific configuration for {workspace_path}")
            return config

        except Exception as e:
            error_context = ErrorContext(
                component="config_service",
                operation="create_workspace_config",
                additional_data={"workspace_path": workspace_path}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            self.logger.error(f"Failed to create workspace config: {error_response.message}")
            raise ValueError(f"Workspace configuration creation failed: {error_response.message}")

    def get_config_value(self, config: Config, key: str, expected_type: Type[T], default: T = None) -> T:
        """
        Get configuration value with type safety.

        Args:
            config: Configuration object
            key: Configuration key to retrieve
            expected_type: Expected type of the value
            default: Default value if key not found or type mismatch

        Returns:
            Configuration value with proper type

        Raises:
            ValueError: If value type doesn't match expected type and no default provided
        """
        try:
            if not hasattr(config, key):
                if default is not None:
                    return default
                raise ValueError(f"Configuration key '{key}' not found")

            value = getattr(config, key)

            if value is None:
                if default is not None:
                    return default
                return None

            if not isinstance(value, expected_type):
                if default is not None:
                    self.logger.warning(
                        f"Configuration key '{key}' has type {type(value).__name__}, "
                        f"expected {expected_type.__name__}, using default"
                    )
                    return default
                raise ValueError(
                    f"Configuration key '{key}' has type {type(value).__name__}, "
                    f"expected {expected_type.__name__}"
                )

            return value

        except Exception as e:
            error_context = ErrorContext(
                component="config_service",
                operation="get_config_value",
                additional_data={"config_key": key}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.LOW
            )
            self.logger.error(f"Failed to get config value: {error_response.message}")
            if default is not None:
                return default
            raise ValueError(f"Configuration value retrieval failed: {error_response.message}")

    def clear_cache(self) -> None:
        """Clear configuration and validation caches."""
        self._config_cache.clear()
        self._validation_cache.clear()
        self.logger.debug("Configuration cache cleared")

    def get_configuration_sources(self) -> List[ConfigurationSource]:
        """Get list of available configuration sources."""
        return self._sources.copy()

    def get_config_summary(self, config: Config) -> Dict[str, Any]:
        """Get a summary of configuration values for debugging."""
        return {
            "workspace_path": config.workspace_path,
            "ollama_base_url": config.ollama_base_url,
            "ollama_model": config.ollama_model,
            "qdrant_url": config.qdrant_url,
            "embedding_length": config.embedding_length,
            "chunking_strategy": config.chunking_strategy,
            "use_tree_sitter": config.use_tree_sitter,
            "embed_timeout_seconds": config.embed_timeout_seconds,
            "search_min_score": config.search_min_score,
            "search_max_results": config.search_max_results,
        }