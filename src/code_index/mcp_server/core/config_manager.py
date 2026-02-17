"""MCP Configuration Manager - Thin facade using extracted validation and persistence modules."""
import os
import logging
from typing import Dict, Any, Optional, List
from ...config import Config
from .config_validator import ConfigurationOverride, ConfigValidator
from .config_persistence import ConfigPersistence

logger = logging.getLogger(__name__)


class MCPConfigurationManager:
    """
    Enhanced configuration manager for MCP server with validation,
    documentation, and override capabilities.
    
    This is a thin facade that delegates to ConfigValidator and ConfigPersistence.
    """
    
    def __init__(self, config_path: str = "code_index.json"):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self._base_config: Optional[Config] = None
        # Delegate to extracted modules
        self._validator = ConfigValidator(self.logger)
        self._persistence = ConfigPersistence(self.logger)
    
    def load_config(self) -> Config:
        """
        Load configuration with environment variable support and validation.
        
        Returns:
            Loaded and validated configuration
            
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Load base configuration
            if os.path.exists(self.config_path):
                self._base_config = Config.from_file(self.config_path)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self._base_config = Config()
                self._base_config.save(self.config_path)
                self.logger.info(f"Created default configuration at {self.config_path}")
            
            # Validate critical configuration using validator
            validation_result = self._validator.validate_config(self._base_config)
            if not validation_result.valid:
                error_msg = "Configuration validation failed:\n"
                for error in validation_result.errors:
                    error_msg += f"\n• {error}"
                raise ValueError(error_msg)
            
            return self._base_config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Configuration loading failed: {e}")
    
    def apply_overrides(self, base_config: Config, overrides: Dict[str, Any]) -> Config:
        """
        Apply configuration overrides to base configuration with validation.
        
        Args:
            base_config: Base configuration to override
            overrides: Dictionary of override parameters
            
        Returns:
            New configuration with overrides applied
            
        Raises:
            ValueError: If override parameters are invalid or incompatible
        """
        # Create ConfigurationOverride instance from overrides
        override_obj = self._create_override_object(overrides)
        
        # Validate overrides using validator
        validation_errors = override_obj.validate()
        if validation_errors:
            error_msg = "Configuration override validation failed:\n" + "\n".join(f"• {error}" for error in validation_errors)
            raise ValueError(error_msg)
        
        # Create a copy of the base config
        new_config = Config()
        
        # Copy all fields from base config
        for key, value in vars(base_config).items():
            setattr(new_config, key, value)
        
        # Apply overrides
        override_fields = override_obj.get_non_none_fields()
        for key, value in override_fields.items():
            if hasattr(new_config, key):
                old_value = getattr(new_config, key)
                setattr(new_config, key, value)
                self.logger.debug(f"Applied override: {key} = {value} (was: {old_value})")
            else:
                self.logger.warning(f"Override parameter '{key}' not found in Config class")
        
        # Validate the final configuration
        validation_result = self._validator.validate_config(new_config)
        if not validation_result.valid:
            error_msg = "Configuration with overrides is invalid:\n"
            for error in validation_result.errors:
                error_msg += f"\n• {error}"
            raise ValueError(error_msg)
        
        return new_config
    
    def _create_override_object(self, overrides: Dict[str, Any]) -> ConfigurationOverride:
        """
        Create a ConfigurationOverride object from a dictionary of overrides.

        Args:
            overrides: Dictionary of override parameters

        Returns:
            ConfigurationOverride object with validated fields
        """
        # Filter overrides to only include valid ConfigurationOverride fields
        valid_fields = {field.name for field in ConfigurationOverride.__dataclass_fields__.values()}
        filtered_overrides = {
            key: value for key, value in overrides.items()
            if key in valid_fields
        }

        # Log any ignored parameters
        ignored_params = set(overrides.keys()) - valid_fields
        if ignored_params:
            self.logger.warning(f"Ignoring unknown override parameters: {ignored_params}")

        # Validate types before creating the object
        self._validate_override_types(filtered_overrides)

        try:
            return ConfigurationOverride(**filtered_overrides)
        except TypeError as e:
            raise ValueError(f"Invalid override parameters: {e}")

    def _validate_override_types(self, overrides: Dict[str, Any]) -> None:
        """
        Validate the types of override parameters.

        Args:
            overrides: Dictionary of override parameters to validate

        Raises:
            ValueError: If any parameter has an invalid type
        """
        from typing import Union
        field_types = {
            field.name: field.type for field in ConfigurationOverride.__dataclass_fields__.values()
        }

        for key, value in overrides.items():
            if key not in field_types:
                continue

            expected_type = field_types[key]

            # Handle Optional types
            if hasattr(expected_type, '__origin__') and expected_type.__origin__ is Union:
                expected_type = expected_type.__args__[0]

            if value is None:
                continue

            # Validate basic types
            if expected_type == int:
                if not isinstance(value, int):
                    raise ValueError(f"Invalid override parameters: {key} must be an integer, got {type(value).__name__}")
            elif expected_type == float:
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Invalid override parameters: {key} must be a number, got {type(value).__name__}")
            elif expected_type == str:
                if not isinstance(value, str):
                    raise ValueError(f"Invalid override parameters: {key} must be a string, got {type(value).__name__}")
            elif expected_type == bool:
                if not isinstance(value, bool):
                    raise ValueError(f"Invalid override parameters: {key} must be a boolean, got {type(value).__name__}")
            elif expected_type == list:
                if not isinstance(value, list):
                    raise ValueError(f"Invalid override parameters: {key} must be a list, got {type(value).__name__}")
            elif expected_type == dict:
                if not isinstance(value, dict):
                    raise ValueError(f"Invalid override parameters: {key} must be a dictionary, got {type(value).__name__}")
    
    def get_available_overrides(self) -> List[str]:
        """Get list of all available configuration override parameters."""
        return list(ConfigurationOverride.__dataclass_fields__.keys())
    
    def check_override_compatibility(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Check compatibility of override parameters and suggest corrections."""
        return self._validator.check_override_compatibility(overrides)
    
    def get_config_documentation(self) -> Dict[str, Any]:
        """Get comprehensive configuration documentation."""
        return self._persistence.get_config_documentation()
    
    def get_optimization_examples(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive example configurations for different use cases."""
        return self._persistence.get_optimization_examples()
    
    def generate_config_template(self, template_name: str, base_config: Optional[Config] = None) -> Dict[str, Any]:
        """Generate a complete configuration template for a specific use case."""
        return self._persistence.generate_config_template(template_name, base_config)
    
    def get_override_documentation(self) -> Dict[str, Any]:
        """Get documentation for configuration override parameters."""
        return self._persistence.get_override_documentation()
    
    def validate_overrides(self, overrides: Dict[str, Any]) -> List[str]:
        """Validate configuration override parameters."""
        return self._validator.validate_overrides(overrides)
    
    def _validate_config(self, config: Config) -> None:
        """
        Validate configuration for required fields and consistency.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        validation_result = self._validator.validate_config(config)
        if not validation_result.valid:
            error_msg = "Configuration validation failed:\n"
            for error in validation_result.errors:
                error_msg += f"\n• {error}"
            raise ValueError(error_msg)