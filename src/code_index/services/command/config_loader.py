"""
Configuration loader service for loading configuration files.

This service handles configuration loading from various sources.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ...config import Config
from ...service_validation import ValidationResult
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..shared.health_service import HealthService
from ..shared.workspace_service import WorkspaceService


class ConfigLoaderService:
    """Enhanced configuration loader service for loading configuration from multiple sources with validation and service integration."""

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize enhanced configuration loader service."""
        self.error_handler = error_handler or ErrorHandler()
        self.config_cache: Dict[str, Config] = {}
        self.validation_cache: Dict[str, List[ValidationResult]] = {}
        self.health_service = HealthService(error_handler)
        self.workspace_service = WorkspaceService(error_handler)

    def load_with_fallback(
        self,
        config_path: str = "code_index.json",
        workspace_path: str = ".",
        overrides: Optional[Dict[str, Any]] = None,
        validate_services: bool = True
    ) -> Config:
        """Enhanced configuration loading with fallback to defaults and multiple sources."""
        cache_key = f"{config_path}:{workspace_path}:{hash(str(overrides) if overrides else '{}')}"
        # Check cache first
        if cache_key in self.config_cache:
            return self.config_cache[cache_key]

        try:
            # Start with default configuration
            config = Config()
            initial_path = Path(workspace_path).resolve().parent if Path(workspace_path).is_relative_to('.') else Path(workspace_path).resolve()
            config.workspace_path = str(initial_path)

            # Load configuration from file if it exists
            if Path(config_path).exists():
                config = Config.from_file(config_path)
                config.workspace_path = str(initial_path)
            else:
                # Apply default values
                defaults = self.load_default_config()
                for key, value in defaults.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # Apply environment variable overrides
            config = self._apply_environment_overrides(config)

            # Apply workspace-specific configuration (skip if explicit non-default config)
            config = self._apply_workspace_config(config, workspace_path, explicit_config_path=config_path)

            # Apply workspace validation using WorkspaceService
            workspace_validation = self.workspace_service.validate_workspace(workspace_path, config)
            if not workspace_validation.valid:
                raise ValueError(f"Workspace validation failed: {workspace_validation.error}")

            # Apply CLI overrides if provided
            if overrides:
                config = self._apply_cli_overrides(config, overrides)

            # Validate configuration values
            validation_errors = self._validate_config_values(config)
            if validation_errors:
                raise ValueError(f"Configuration validation failed: {', '.join(validation_errors)}")

            # Validate services if requested
            if validate_services:
                health_validation = self._validate_services(config)
                if not health_validation.valid:
                    raise ValueError(f"Service validation failed: {health_validation.error}")

            # Cache the configuration
            self.config_cache[cache_key] = config
            return config

        except Exception as e:
            error_context = ErrorContext(
                component="config_loader_service",
                operation="load_with_fallback",
                additional_data={
                    "config_path": config_path,
                    "workspace_path": workspace_path
                }
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.CRITICAL
            )
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
                    pass

            # Feature flags
            if os.getenv("CODE_INDEX_USE_TREE_SITTER"):
                config.use_tree_sitter = os.getenv("CODE_INDEX_USE_TREE_SITTER").lower() in ("true", "1", "yes")

            return config
        except Exception:
            return config

    def _apply_workspace_config(self, config: Config, workspace_path: str, explicit_config_path: Optional[str] = None) -> Config:
        """Apply workspace-specific configuration overrides.
        
        Args:
            config: The current configuration
            workspace_path: Path to the workspace
            explicit_config_path: If provided, skip loading workspace configs that match this path
                                  (user explicitly specified a config file)
        """
        try:
            # If user explicitly specified a config file, don't override with workspace configs
            # This respects the user's choice when they use --config option
            if explicit_config_path:
                explicit_path = Path(explicit_config_path).resolve()
                # Check if the explicit config is in the workspace directory
                workspace_path_obj = Path(workspace_path).resolve()
                # Only skip if the explicit config is NOT the default workspace config
                default_workspace_config = workspace_path_obj / "code_index.json"
                if explicit_path != default_workspace_config.resolve():
                    # User specified a non-default config, skip workspace overrides
                    return config
            
            # Look for workspace-specific config files
            workspace_config_paths = [
                Path(workspace_path) / ".code_index.json",
                Path(workspace_path) / ".code_index.yaml",
                Path(workspace_path) / ".code_index.yml",
                Path(workspace_path) / "config" / "config.json",
            ]

            for config_path in workspace_config_paths:
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        if config_path.suffix in ('.yaml', '.yml'):
                            import yaml
                            workspace_config = yaml.safe_load(f)
                        else:
                            workspace_config = json.load(f)
                        
                        # Apply configuration with precedence rules
                        if isinstance(workspace_config, dict):
                            config.update_from_dict(workspace_config)
                        break

            return config
        except Exception:
            return config

    def _apply_cli_overrides(self, config: Config, overrides: Dict[str, Any]) -> Config:
        """Apply CLI-specific configuration overrides."""
        try:
            # Create a copy of the config to avoid modifying the original
            new_config = Config()
            new_config.update_from_dict(config.to_dict())

            # Apply overrides
            for key, value in overrides.items():
                if hasattr(new_config, key):
                    setattr(new_config, key, value)

            # Validate the configuration with overrides
            validation_result = self.validate_and_initialize(new_config)
            if not validation_result.valid:
                raise ValueError(f"Configuration with CLI overrides is invalid: {validation_result.error}")

            return new_config
        except Exception as e:
            error_context = ErrorContext(
                component="config_loader_service",
                operation="apply_cli_overrides",
                additional_data={"overrides": list(overrides.keys()) if overrides else []}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            raise ValueError(f"CLI override application failed: {error_response.message}")

    def validate_and_initialize(self, config: Config, validate_services: bool = True) -> ValidationResult:
        """Enhanced validation with service validation and initialization."""
        try:
            # Validate configuration values
            validation_errors = self._validate_config_values(config)
            if validation_errors:
                return ValidationResult(
                    service="configuration",
                    valid=False,
                    error=f"Configuration validation failed: {', '.join(validation_errors)}"
                )

            # Validate services if requested
            if validate_services:
                health_validation = self._validate_services(config)
                if not health_validation.valid:
                    return ValidationResult(
                        service="configuration",
                        valid=False,
                        error=f"Service validation failed: {health_validation.error}",
                        details={"validation_results": [vars(result) for result in health_validation.details.get('validation_results', [])]}
                    )
            else:
                # Create mock successful validation results for testing
                health_validation = ValidationResult(
                    service="configuration",
                    valid=True,
                    details={"test_mode": True}
                )

            return ValidationResult(
                service="configuration",
                valid=True,
                details={"validation_results": [vars(result) for result in health_validation.details.get('validation_results', [])]}
            )

        except Exception as e:
            error_context = ErrorContext(
                component="config_loader_service",
                operation="validate_and_initialize"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="configuration",
                valid=False,
                error=error_response.message
            )

    def _validate_config_values(self, config: Config) -> List[str]:
        """Validate individual configuration values."""
        errors = []

        # Validate embedding length
        if getattr(config, "embedding_length") is None or getattr(config, "embedding_length") <= 0:
            errors.append("embedding_length must be a positive integer")

        # Validate chunking strategy
        valid_strategies = ["lines", "tokens", "treesitter"]
        if getattr(config, "chunking_strategy") not in valid_strategies:
            errors.append(f"chunking_strategy must be one of {valid_strategies}")

        # Validate search parameters
        if getattr(config, "search_min_score") < 0 or getattr(config, "search_min_score") > 1:
            errors.append("search_min_score must be between 0 and 1")

        if getattr(config, "search_max_results") <= 0:
            errors.append("search_max_results must be positive")

        # Validate timeout values
        if getattr(config, "embed_timeout_seconds") <= 0:
            errors.append("embed_timeout_seconds must be positive")

        # Validate file size limits
        if getattr(config, "max_file_size_bytes") <= 0:
            errors.append("max_file_size_bytes must be positive")

        # Validate Tree-sitter compatibility
        if getattr(config, "chunking_strategy") == "treesitter" and not getattr(config, "use_tree_sitter"):
            errors.append("chunking_strategy='treesitter' requires use_tree_sitter=true")

        return errors

    def _validate_services(self, config: Config) -> ValidationResult:
        """Validate service connectivity and functionality."""
        try:
            from ..service_validation import ServiceValidator
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

            return ValidationResult(
                service="configuration",
                valid=True,
                details={"validation_results": [vars(result) for result in validation_results]}
            )
        except Exception as e:
            error_context = ErrorContext(
                component="config_loader_service",
                operation="_validate_services"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="configuration",
                valid=False,
                error=error_response.message
            )
        finally:
            # Record response time handled by service validator
            pass

    def clear_cache(self) -> None:
        """Clear configuration and validation caches."""
        self.config_cache.clear()
        self.validation_cache.clear()

    def get_config_summary(self, config: Config) -> Dict[str, Any]:
        """Get a summary of configuration values for debugging."""
        return {
            "workspace_path": getattr(config, "workspace_path"),
            "ollama_base_url": getattr(config, "ollama_base_url"),
            "ollama_model": getattr(config, "ollama_model"),
            "qdrant_url": getattr(config, "qdrant_url"),
            "embedding_length": getattr(config, "embedding_length"),
            "chunking_strategy": getattr(config, "chunking_strategy"),
            "use_tree_sitter": getattr(config, "use_tree_sitter"),
            "embed_timeout_seconds": getattr(config, "embed_timeout_seconds"),
            "search_min_score": getattr(config, "search_min_score"),
            "search_max_results": getattr(config, "search_max_results"),
            "search_strategy": getattr(config, "search_strategy"),
        }

    def load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "ollama_model": "llama3.2:3b",
            "ollama_base_url": "https://localhost:11434",
            "qdrant_url": "https://localhost:6334",
            "qdrant_api_key": "",
            "workspace_path": ".",
            "search_min_score": 0.4,
            "search_max_results": 50,
            "search_strategy": "text",
            "tree_sitter_max_file_size_bytes": 10000000,
            "tree_sitter_max_blocks_per_file": 1000,
            "tree_sitter_max_functions_per_file": 50,
            "tree_sitter_max_classes_per_file": 10,
            "batch_segment_threshold": 10,
            "use_tree_sitter": False,
            "chunking_strategy": "lines"
        }
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep merge nested dictionaries."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to configuration."""
        defaults = self.load_default_config()
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        return config