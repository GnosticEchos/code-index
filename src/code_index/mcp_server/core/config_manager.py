"""
MCP Configuration Manager

Enhanced configuration management for the MCP server with validation,
documentation, and override support.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict

from ...config import Config


@dataclass
class ConfigurationOverride:
    """
    Represents configuration parameters that can be overridden per operation.
    
    This class defines all configuration parameters that can be overridden
    on a per-operation basis through MCP tool calls, with validation and
    compatibility checking.
    """
    # Core settings
    embedding_length: Optional[int] = None
    chunking_strategy: Optional[str] = None
    use_tree_sitter: Optional[bool] = None
    
    # Performance settings
    batch_segment_threshold: Optional[int] = None
    embed_timeout_seconds: Optional[int] = None
    max_file_size_bytes: Optional[int] = None
    use_mmap_file_reading: Optional[bool] = None
    mmap_min_file_size_bytes: Optional[int] = None
    
    # Chunking settings
    token_chunk_size: Optional[int] = None
    token_chunk_overlap: Optional[int] = None
    
    # Tree-sitter settings
    tree_sitter_languages: Optional[List[str]] = None
    tree_sitter_max_file_size_bytes: Optional[int] = None
    tree_sitter_min_block_chars: Optional[int] = None
    tree_sitter_max_blocks_per_file: Optional[int] = None
    tree_sitter_max_functions_per_file: Optional[int] = None
    tree_sitter_max_classes_per_file: Optional[int] = None
    tree_sitter_max_impl_blocks_per_file: Optional[int] = None
    tree_sitter_skip_test_files: Optional[bool] = None
    tree_sitter_skip_examples: Optional[bool] = None
    tree_sitter_debug_logging: Optional[bool] = None
    
    # Search settings
    search_min_score: Optional[float] = None
    search_max_results: Optional[int] = None
    search_file_type_weights: Optional[Dict[str, float]] = None
    search_path_boosts: Optional[List[Dict[str, Any]]] = None
    search_language_boosts: Optional[Dict[str, float]] = None
    search_exclude_patterns: Optional[List[str]] = None
    search_snippet_preview_chars: Optional[int] = None
    
    # File handling settings
    extensions: Optional[List[str]] = None
    auto_extensions: Optional[bool] = None
    skip_dot_files: Optional[bool] = None
    auto_ignore_detection: Optional[bool] = None
    
    def validate(self) -> List[str]:
        """
        Validate override parameters for type correctness and compatibility.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate chunking strategy
        if self.chunking_strategy is not None:
            valid_strategies = ["lines", "tokens", "treesitter"]
            if self.chunking_strategy not in valid_strategies:
                errors.append(f"chunking_strategy must be one of {valid_strategies}")
        
        # Validate numeric ranges
        if self.search_min_score is not None:
            if not isinstance(self.search_min_score, (int, float)) or self.search_min_score < 0 or self.search_min_score > 1:
                errors.append("search_min_score must be a number between 0 and 1")
        
        if self.search_max_results is not None:
            if not isinstance(self.search_max_results, int) or self.search_max_results <= 0:
                errors.append("search_max_results must be a positive integer")
        
        if self.batch_segment_threshold is not None:
            if not isinstance(self.batch_segment_threshold, int) or self.batch_segment_threshold <= 0:
                errors.append("batch_segment_threshold must be a positive integer")
        
        if self.embed_timeout_seconds is not None:
            if not isinstance(self.embed_timeout_seconds, int) or self.embed_timeout_seconds <= 0:
                errors.append("embed_timeout_seconds must be a positive integer")
        
        if self.max_file_size_bytes is not None:
            if not isinstance(self.max_file_size_bytes, int) or self.max_file_size_bytes <= 0:
                errors.append("max_file_size_bytes must be a positive integer")
        
        if self.embedding_length is not None:
            if not isinstance(self.embedding_length, int) or self.embedding_length <= 0:
                errors.append("embedding_length must be a positive integer")
        
        # Validate compatibility rules
        if (self.chunking_strategy == "treesitter" and self.use_tree_sitter is False):
            errors.append("chunking_strategy='treesitter' requires use_tree_sitter=true")
        
        # Check Tree-sitter parameter dependencies
        tree_sitter_fields = [
            'tree_sitter_languages', 'tree_sitter_max_file_size_bytes',
            'tree_sitter_min_block_chars', 'tree_sitter_max_blocks_per_file',
            'tree_sitter_max_functions_per_file', 'tree_sitter_max_classes_per_file',
            'tree_sitter_max_impl_blocks_per_file', 'tree_sitter_skip_test_files',
            'tree_sitter_skip_examples', 'tree_sitter_debug_logging'
        ]
        
        active_tree_sitter_params = [
            field for field in tree_sitter_fields 
            if getattr(self, field, None) is not None
        ]
        
        if active_tree_sitter_params and self.use_tree_sitter is False:
            errors.append(f"Tree-sitter parameters {active_tree_sitter_params} require use_tree_sitter=true")
        
        # Validate token chunking dependencies
        if (self.token_chunk_size is not None or self.token_chunk_overlap is not None):
            if self.chunking_strategy is not None and self.chunking_strategy != "tokens":
                errors.append("token_chunk_* parameters require chunking_strategy='tokens'")
        
        # Validate memory mapping dependencies
        if self.mmap_min_file_size_bytes is not None and self.use_mmap_file_reading is False:
            errors.append("mmap_min_file_size_bytes requires use_mmap_file_reading=true")
        
        return errors
    
    def get_non_none_fields(self) -> Dict[str, Any]:
        """
        Get dictionary of non-None override fields.
        
        Returns:
            Dictionary containing only fields with non-None values
        """
        return {
            field: value for field, value in asdict(self).items() 
            if value is not None
        }


class MCPConfigurationManager:
    """
    Enhanced configuration manager for MCP server with validation,
    documentation, and override capabilities.
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
            
            # Validate critical configuration
            self._validate_config(self._base_config)
            
            return self._base_config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Configuration loading failed: {e}")
    
    def _validate_config(self, config: Config) -> None:
        """
        Validate configuration for required fields and consistency.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        # Check required fields
        if config.embedding_length is None:
            errors.append({
                "field": "embedding_length",
                "message": "embedding_length must be set in configuration",
                "suggested_values": [768, 1024, 3584],
                "guidance": [
                    "Set embedding_length in code_index.json to match your model",
                    "For nomic-embed-text, use 768",
                    "For Qwen3-Embedding-0.6B:F16, use 1024"
                ]
            })
        
        # Validate chunking strategy
        valid_strategies = ["lines", "tokens", "treesitter"]
        if config.chunking_strategy not in valid_strategies:
            errors.append({
                "field": "chunking_strategy",
                "message": f"chunking_strategy must be one of {valid_strategies}",
                "current_value": config.chunking_strategy,
                "guidance": [
                    "Use 'lines' for simple line-based chunking (fastest)",
                    "Use 'tokens' for token-based chunking (balanced)",
                    "Use 'treesitter' for semantic chunking (most accurate)"
                ]
            })
        
        # Validate numeric ranges
        if config.search_min_score < 0 or config.search_min_score > 1:
            errors.append({
                "field": "search_min_score",
                "message": "search_min_score must be between 0 and 1",
                "current_value": config.search_min_score
            })
        
        if config.search_max_results <= 0:
            errors.append({
                "field": "search_max_results",
                "message": "search_max_results must be positive",
                "current_value": config.search_max_results
            })
        
        if errors:
            raise ValueError(self._format_validation_errors(errors))
    
    def _format_validation_errors(self, errors: List[Dict[str, Any]]) -> str:
        """Format validation errors into actionable error message."""
        message = "Configuration validation failed:\n"
        for error in errors:
            message += f"\n• {error['message']}"
            if "current_value" in error:
                message += f" (current: {error['current_value']})"
            if "suggested_values" in error:
                message += f"\n  Suggested values: {error['suggested_values']}"
            if "guidance" in error:
                for guidance in error["guidance"]:
                    message += f"\n  - {guidance}"
        return message
    
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
        
        # Validate overrides
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
        try:
            self._validate_config(new_config)
        except ValueError as e:
            raise ValueError(f"Configuration with overrides is invalid: {e}")
        
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
        field_types = {
            field.name: field.type for field in ConfigurationOverride.__dataclass_fields__.values()
        }

        for key, value in overrides.items():
            if key not in field_types:
                continue

            expected_type = field_types[key]

            # Handle Optional types
            if hasattr(expected_type, '__origin__') and expected_type.__origin__ is Union:
                # For Optional[T], check against T
                expected_type = expected_type.__args__[0]

            # Skip None values for optional fields
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
        """
        Get list of all available configuration override parameters.
        
        Returns:
            List of parameter names that can be overridden
        """
        return list(ConfigurationOverride.__dataclass_fields__.keys())
    
    def check_override_compatibility(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check compatibility of override parameters and suggest corrections.
        
        Args:
            overrides: Dictionary of override parameters to check
            
        Returns:
            Dictionary containing compatibility analysis and suggestions
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            override_obj = self._create_override_object(overrides)
            validation_errors = override_obj.validate()
            
            if validation_errors:
                result["valid"] = False
                result["errors"] = validation_errors
            
            # Check for common compatibility issues and provide suggestions
            if override_obj.chunking_strategy == "treesitter" and override_obj.use_tree_sitter is None:
                result["suggestions"].append("Consider setting use_tree_sitter=true for treesitter chunking strategy")
            
            if override_obj.use_tree_sitter is True and override_obj.chunking_strategy == "lines":
                result["warnings"].append("Tree-sitter enabled but using line-based chunking - consider 'treesitter' strategy for better semantic understanding")
            
            if override_obj.batch_segment_threshold is not None and override_obj.batch_segment_threshold > 100:
                result["warnings"].append("Large batch_segment_threshold may cause memory issues - monitor system resources")
            
            if override_obj.embed_timeout_seconds is not None and override_obj.embed_timeout_seconds < 30:
                result["warnings"].append("Short embed_timeout_seconds may cause timeouts on slower systems")
            
        except ValueError as e:
            result["valid"] = False
            result["errors"].append(str(e))
        
        return result
    
    def get_config_documentation(self) -> Dict[str, Any]:
        """
        Get comprehensive configuration documentation with parameter descriptions and examples.
        
        Returns:
            Dictionary containing complete configuration documentation organized by categories
        """
        return {
            "categories": self._get_configuration_categories(),
            "examples": self.get_optimization_examples(),
            "optimization_strategies": self._get_optimization_strategies(),
            "parameter_compatibility": self._get_parameter_compatibility_matrix(),
            "troubleshooting": self._get_troubleshooting_guide()
        }
    
    def _get_configuration_categories(self) -> Dict[str, Any]:
        """Get detailed configuration categories with comprehensive parameter documentation."""
        return {
            "core": {
                "description": "Core service endpoints and workspace configuration",
                "priority": "required",
                "parameters": {
                    "ollama_base_url": {
                        "type": "string",
                        "default": "http://localhost:11434",
                        "description": "Base URL for Ollama API service",
                        "env_var": "OLLAMA_BASE_URL",
                        "validation": "Must be a valid HTTP/HTTPS URL",
                        "examples": [
                            "http://localhost:11434",
                            "https://ollama.example.com:443"
                        ]
                    },
                    "ollama_model": {
                        "type": "string", 
                        "default": "nomic-embed-text:latest",
                        "description": "Ollama model for generating embeddings",
                        "env_var": "OLLAMA_MODEL",
                        "validation": "Model must be available in Ollama",
                        "examples": [
                            "nomic-embed-text:latest",
                            "mxbai-embed-large:latest",
                            "snowflake-arctic-embed:latest"
                        ]
                    },
                    "qdrant_url": {
                        "type": "string",
                        "default": "http://localhost:6333",
                        "description": "Qdrant vector database connection URL",
                        "env_var": "QDRANT_URL",
                        "validation": "Must be accessible Qdrant instance",
                        "examples": [
                            "http://localhost:6333",
                            "https://qdrant.example.com:6333"
                        ]
                    },
                    "qdrant_api_key": {
                        "type": "string",
                        "default": None,
                        "description": "API key for Qdrant authentication (if required)",
                        "env_var": "QDRANT_API_KEY",
                        "validation": "Required for cloud Qdrant instances",
                        "security": "Store in environment variable, not config file"
                    },
                    "workspace_path": {
                        "type": "string",
                        "default": ".",
                        "description": "Default workspace path for indexing operations",
                        "env_var": "WORKSPACE_PATH",
                        "validation": "Must be accessible directory path"
                    },
                    "embedding_length": {
                        "type": "integer",
                        "required": True,
                        "description": "Vector dimension for embeddings (must match model output)",
                        "validation": "Must match the embedding model's output dimension",
                        "model_mappings": {
                            "nomic-embed-text": 768,
                            "mxbai-embed-large": 1024,
                            "snowflake-arctic-embed": 1024,
                            "Qwen3-Embedding-0.6B:F16": 1024,
                            "text-embedding-3-large": 3584
                        },
                        "impact": "Critical - incorrect value will cause vector store failures"
                    }
                }
            },
            "performance": {
                "description": "Performance tuning and resource management settings",
                "priority": "optimization",
                "parameters": {
                    "batch_segment_threshold": {
                        "type": "integer",
                        "default": 60,
                        "description": "Number of code segments to batch together for embedding",
                        "range": "10-200",
                        "impact": "Higher values = better throughput, more memory usage",
                        "recommendations": {
                            "small_projects": 30,
                            "medium_projects": 60,
                            "large_projects": 100
                        }
                    },
                    "embed_timeout_seconds": {
                        "type": "integer",
                        "default": 60,
                        "description": "Timeout for individual embedding operations",
                        "env_var": "CODE_INDEX_EMBED_TIMEOUT",
                        "range": "10-300",
                        "impact": "Prevents hanging on problematic files",
                        "recommendations": {
                            "local_ollama": 60,
                            "remote_ollama": 120,
                            "slow_hardware": 180
                        }
                    },
                    "max_file_size_bytes": {
                        "type": "integer",
                        "default": 1048576,
                        "description": "Maximum file size to process (bytes)",
                        "range": "1KB-10MB",
                        "impact": "Larger files take more memory and processing time",
                        "recommendations": {
                            "memory_constrained": 512000,
                            "balanced": 1048576,
                            "high_memory": 5242880
                        }
                    },
                    "use_mmap_file_reading": {
                        "type": "boolean",
                        "default": False,
                        "description": "Use memory-mapped file reading for large files",
                        "impact": "Reduces memory usage for large files, may be slower",
                        "when_to_use": "Large repositories with many big files"
                    },
                    "mmap_min_file_size_bytes": {
                        "type": "integer",
                        "default": 65536,
                        "description": "Minimum file size to use memory mapping (64KB)",
                        "dependency": "Requires use_mmap_file_reading=true"
                    }
                }
            },
            "chunking": {
                "description": "Text chunking strategy and semantic analysis configuration",
                "priority": "core",
                "parameters": {
                    "chunking_strategy": {
                        "type": "string",
                        "default": "lines",
                        "options": ["lines", "tokens", "treesitter"],
                        "description": "Strategy for splitting code into searchable chunks",
                        "trade_offs": {
                            "lines": "Fastest, simple line-based splitting",
                            "tokens": "Balanced, respects token boundaries",
                            "treesitter": "Slowest, semantic code structure awareness"
                        },
                        "recommendations": {
                            "quick_indexing": "lines",
                            "balanced_accuracy": "tokens", 
                            "maximum_accuracy": "treesitter"
                        }
                    },
                    "token_chunk_size": {
                        "type": "integer",
                        "default": 1000,
                        "description": "Target size for token-based chunks",
                        "dependency": "Used when chunking_strategy='tokens'",
                        "range": "100-2000"
                    },
                    "token_chunk_overlap": {
                        "type": "integer",
                        "default": 200,
                        "description": "Overlap between adjacent token chunks",
                        "dependency": "Used when chunking_strategy='tokens'",
                        "range": "0-500"
                    },
                    "use_tree_sitter": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable semantic code structure analysis",
                        "impact": "Significantly slower but more accurate semantic chunking",
                        "languages_supported": ["rust", "typescript", "javascript", "python", "go", "java", "cpp"]
                    },
                    "tree_sitter_languages": {
                        "type": "array",
                        "default": None,
                        "description": "Specific languages to enable Tree-sitter for (null = auto-detect)",
                        "dependency": "Requires use_tree_sitter=true"
                    },
                    "tree_sitter_max_file_size_bytes": {
                        "type": "integer",
                        "default": 524288,
                        "description": "Maximum file size for Tree-sitter processing (512KB)",
                        "rationale": "Large files are often generated/minified and not semantically valuable"
                    },
                    "tree_sitter_max_blocks_per_file": {
                        "type": "integer",
                        "default": 100,
                        "description": "Maximum code blocks to extract per file",
                        "impact": "Prevents excessive chunking of large files"
                    },
                    "tree_sitter_skip_test_files": {
                        "type": "boolean",
                        "default": True,
                        "description": "Skip test files for Tree-sitter processing",
                        "rationale": "Test files often have different structure and lower search priority"
                    },
                    "tree_sitter_skip_examples": {
                        "type": "boolean",
                        "default": True,
                        "description": "Skip example/demo files for Tree-sitter processing"
                    }
                }
            },
            "search": {
                "description": "Search ranking, filtering, and result formatting configuration",
                "priority": "optimization",
                "parameters": {
                    "search_min_score": {
                        "type": "float",
                        "default": 0.4,
                        "description": "Minimum similarity score threshold for search results",
                        "range": "0.0-1.0",
                        "recommendations": {
                            "broad_search": 0.2,
                            "balanced": 0.4,
                            "precise_search": 0.6
                        }
                    },
                    "search_max_results": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum number of search results to return",
                        "range": "1-500",
                        "impact": "Higher values may slow down result processing"
                    },
                    "search_file_type_weights": {
                        "type": "object",
                        "default": {".vue": 1.30, ".ts": 1.25, ".rs": 1.20},
                        "description": "Boost scores for specific file extensions",
                        "format": "Extension to multiplier mapping"
                    },
                    "search_path_boosts": {
                        "type": "array",
                        "default": [{"pattern": "src/", "weight": 1.25}],
                        "description": "Boost scores for files matching path patterns",
                        "format": "Array of {pattern, weight} objects"
                    },
                    "search_language_boosts": {
                        "type": "object",
                        "default": {"vue": 1.20, "typescript": 1.15},
                        "description": "Boost scores for specific programming languages"
                    },
                    "search_snippet_preview_chars": {
                        "type": "integer",
                        "default": 160,
                        "description": "Number of characters to include in result snippets",
                        "range": "50-500"
                    }
                }
            },
            "advanced": {
                "description": "Advanced features and debugging configuration",
                "priority": "optional",
                "parameters": {
                    "extensions": {
                        "type": "array",
                        "default": [".rs", ".ts", ".vue", ".js", ".py"],
                        "description": "File extensions to index (comprehensive list available)",
                        "impact": "Controls which files are processed during indexing"
                    },
                    "auto_extensions": {
                        "type": "boolean",
                        "default": False,
                        "description": "Automatically detect additional file extensions using Pygments"
                    },
                    "skip_dot_files": {
                        "type": "boolean",
                        "default": True,
                        "description": "Skip hidden files and directories (starting with .)"
                    },
                    "auto_ignore_detection": {
                        "type": "boolean",
                        "default": True,
                        "description": "Automatically apply .gitignore and similar ignore patterns"
                    },
                    "timeout_log_path": {
                        "type": "string",
                        "default": "timeout_files.txt",
                        "description": "File to log embedding timeouts for retry processing"
                    },
                    "tree_sitter_debug_logging": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable detailed Tree-sitter processing logs",
                        "warning": "Generates verbose output, use only for debugging"
                    }
                }
            }
        }
    
    def _get_optimization_strategies(self) -> Dict[str, Any]:
        """Get detailed optimization strategies with trade-off explanations."""
        return {
            "speed_optimized": {
                "name": "Speed Optimized",
                "description": "Fastest indexing with minimal accuracy trade-offs",
                "use_cases": ["Large codebases", "Quick prototyping", "CI/CD pipelines"],
                "trade_offs": {
                    "pros": ["Fastest indexing", "Low memory usage", "Simple configuration"],
                    "cons": ["Less semantic accuracy", "May miss code relationships", "Basic chunking"]
                },
                "config_changes": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 100,
                    "embed_timeout_seconds": 30,
                    "max_file_size_bytes": 512000
                },
                "expected_performance": "2-5x faster than semantic chunking"
            },
            "accuracy_optimized": {
                "name": "Accuracy Optimized", 
                "description": "Maximum semantic accuracy with Tree-sitter analysis",
                "use_cases": ["Code analysis", "Documentation generation", "Semantic search"],
                "trade_offs": {
                    "pros": ["Best semantic understanding", "Accurate code structure", "Context-aware chunking"],
                    "cons": ["Slower indexing", "Higher memory usage", "Complex configuration"]
                },
                "config_changes": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_max_blocks_per_file": 150,
                    "tree_sitter_skip_test_files": False,
                    "embed_timeout_seconds": 120
                },
                "expected_performance": "2-5x slower but significantly better search relevance"
            },
            "balanced": {
                "name": "Balanced",
                "description": "Good balance of speed and accuracy for most use cases",
                "use_cases": ["General development", "Code search", "Documentation"],
                "trade_offs": {
                    "pros": ["Reasonable speed", "Good accuracy", "Moderate resource usage"],
                    "cons": ["Not optimal for extreme cases"]
                },
                "config_changes": {
                    "chunking_strategy": "tokens",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 60,
                    "token_chunk_size": 800,
                    "token_chunk_overlap": 150
                },
                "expected_performance": "Good compromise between speed and accuracy"
            },
            "memory_optimized": {
                "name": "Memory Optimized",
                "description": "Minimal memory usage for resource-constrained environments",
                "use_cases": ["Limited RAM", "Docker containers", "Shared systems"],
                "trade_offs": {
                    "pros": ["Low memory footprint", "Stable performance", "Container-friendly"],
                    "cons": ["Slower processing", "Smaller batch sizes", "May timeout on large files"]
                },
                "config_changes": {
                    "batch_segment_threshold": 20,
                    "max_file_size_bytes": 256000,
                    "use_mmap_file_reading": True,
                    "tree_sitter_max_blocks_per_file": 50
                },
                "expected_performance": "Lower memory usage but slower processing"
            }
        }
    
    def _get_parameter_compatibility_matrix(self) -> Dict[str, Any]:
        """Get parameter compatibility and dependency information."""
        return {
            "dependencies": {
                "tree_sitter_*": {
                    "requires": "use_tree_sitter=true",
                    "description": "All tree_sitter_* parameters require Tree-sitter to be enabled"
                },
                "token_chunk_*": {
                    "requires": "chunking_strategy='tokens'",
                    "description": "Token chunking parameters only apply with token strategy"
                },
                "mmap_min_file_size_bytes": {
                    "requires": "use_mmap_file_reading=true",
                    "description": "Memory mapping threshold requires mmap to be enabled"
                }
            },
            "conflicts": {
                "chunking_strategy='treesitter' + use_tree_sitter=false": {
                    "description": "Tree-sitter chunking requires use_tree_sitter=true",
                    "resolution": "Set use_tree_sitter=true or change chunking_strategy"
                },
                "high_batch_threshold + low_memory": {
                    "description": "Large batch sizes may cause memory issues",
                    "resolution": "Reduce batch_segment_threshold or increase available memory"
                }
            },
            "recommendations": {
                "embedding_length": "Always verify this matches your Ollama model's output dimension",
                "timeout_values": "Increase timeouts for remote Ollama instances or slow hardware",
                "tree_sitter_limits": "Adjust Tree-sitter limits based on your codebase characteristics"
            }
        }
    
    def _get_troubleshooting_guide(self) -> Dict[str, Any]:
        """Get troubleshooting guide for common configuration issues."""
        return {
            "common_errors": {
                "embedding_length_mismatch": {
                    "symptoms": ["Vector dimension errors", "Qdrant insertion failures"],
                    "causes": ["embedding_length doesn't match model output"],
                    "solutions": [
                        "Check your Ollama model's embedding dimension",
                        "Update embedding_length in configuration",
                        "Recreate collections if dimension changed"
                    ]
                },
                "service_connectivity": {
                    "symptoms": ["Connection refused", "Timeout errors"],
                    "causes": ["Ollama or Qdrant not running", "Incorrect URLs"],
                    "solutions": [
                        "Verify services are running: docker ps or systemctl status",
                        "Check URLs are accessible: curl http://localhost:11434",
                        "Verify firewall and network configuration"
                    ]
                },
                "memory_issues": {
                    "symptoms": ["Out of memory errors", "System slowdown"],
                    "causes": ["Large batch sizes", "Big files", "Insufficient RAM"],
                    "solutions": [
                        "Reduce batch_segment_threshold",
                        "Enable use_mmap_file_reading",
                        "Reduce max_file_size_bytes",
                        "Use memory_optimized strategy"
                    ]
                },
                "slow_indexing": {
                    "symptoms": ["Very slow processing", "High CPU usage"],
                    "causes": ["Tree-sitter on large files", "Remote Ollama", "Large batches"],
                    "solutions": [
                        "Use speed_optimized strategy",
                        "Increase tree_sitter_max_file_size_bytes limit",
                        "Reduce batch_segment_threshold",
                        "Use local Ollama instance"
                    ]
                }
            },
            "performance_tuning": {
                "indexing_speed": [
                    "Use chunking_strategy='lines' for fastest processing",
                    "Disable Tree-sitter for speed-critical scenarios", 
                    "Increase batch_segment_threshold (with sufficient memory)",
                    "Use local Ollama instance instead of remote"
                ],
                "search_accuracy": [
                    "Enable Tree-sitter for semantic understanding",
                    "Use chunking_strategy='treesitter' or 'tokens'",
                    "Tune search_file_type_weights for your project",
                    "Adjust search_min_score based on result quality"
                ],
                "memory_usage": [
                    "Enable use_mmap_file_reading for large files",
                    "Reduce batch_segment_threshold",
                    "Set appropriate max_file_size_bytes limit",
                    "Use tree_sitter_max_blocks_per_file to limit extraction"
                ]
            }
        }
    
    def get_optimization_examples(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive example configurations for different use cases and optimization strategies.
        
        Returns:
            Dictionary of example configurations with detailed explanations
        """
        return {
            "fast_indexing": {
                "name": "Fast Indexing",
                "description": "Optimized for speed with minimal accuracy trade-offs",
                "use_cases": ["Large codebases", "CI/CD pipelines", "Quick prototyping"],
                "performance_impact": "2-5x faster indexing, basic semantic understanding",
                "config": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 100,
                    "embed_timeout_seconds": 30,
                    "max_file_size_bytes": 1048576,
                    "search_min_score": 0.3
                },
                "notes": [
                    "Best for time-sensitive scenarios",
                    "Good baseline accuracy for most searches",
                    "Minimal resource requirements"
                ]
            },
            "semantic_accuracy": {
                "name": "Semantic Accuracy",
                "description": "Maximum semantic understanding with Tree-sitter analysis",
                "use_cases": ["Code analysis", "Documentation generation", "Complex refactoring"],
                "performance_impact": "2-5x slower indexing, significantly better search relevance",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_max_blocks_per_file": 150,
                    "tree_sitter_skip_test_files": False,
                    "tree_sitter_skip_examples": False,
                    "embed_timeout_seconds": 120,
                    "batch_segment_threshold": 40,
                    "search_min_score": 0.4
                },
                "notes": [
                    "Best for understanding code structure and relationships",
                    "Includes test files for comprehensive coverage",
                    "Higher timeout to handle complex parsing"
                ]
            },
            "balanced": {
                "name": "Balanced Performance",
                "description": "Good balance of speed and accuracy for general use",
                "use_cases": ["Daily development", "Code search", "Documentation"],
                "performance_impact": "Moderate speed, good accuracy for most scenarios",
                "config": {
                    "chunking_strategy": "tokens",
                    "use_tree_sitter": False,
                    "token_chunk_size": 800,
                    "token_chunk_overlap": 150,
                    "batch_segment_threshold": 60,
                    "embed_timeout_seconds": 60,
                    "search_min_score": 0.4
                },
                "notes": [
                    "Recommended starting configuration",
                    "Token-based chunking respects code boundaries",
                    "Good compromise for most projects"
                ]
            },
            "memory_optimized": {
                "name": "Memory Optimized",
                "description": "Minimal memory usage for resource-constrained environments",
                "use_cases": ["Docker containers", "Limited RAM systems", "Shared environments"],
                "performance_impact": "Lower memory usage, slower processing",
                "config": {
                    "batch_segment_threshold": 20,
                    "max_file_size_bytes": 256000,
                    "use_mmap_file_reading": True,
                    "mmap_min_file_size_bytes": 32768,
                    "tree_sitter_max_blocks_per_file": 50,
                    "embed_timeout_seconds": 90
                },
                "notes": [
                    "Uses memory mapping for large files",
                    "Smaller batch sizes reduce memory spikes",
                    "Suitable for containers with memory limits"
                ]
            },
            "rust_project": {
                "name": "Rust Project Optimization",
                "description": "Optimized for Rust codebases with semantic understanding",
                "use_cases": ["Rust development", "Systems programming", "Performance-critical code"],
                "performance_impact": "Semantic chunking with Rust-specific optimizations",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_languages": ["rust"],
                    "tree_sitter_max_impl_blocks_per_file": 50,
                    "search_file_type_weights": {
                        ".rs": 1.4,
                        ".toml": 1.1
                    },
                    "search_path_boosts": [
                        {"pattern": "src/", "weight": 1.4},
                        {"pattern": "lib.rs", "weight": 1.5},
                        {"pattern": "main.rs", "weight": 1.3},
                        {"pattern": "tests/", "weight": 0.9}
                    ],
                    "search_language_boosts": {"rust": 1.2},
                    "extensions": [".rs", ".toml", ".md"]
                },
                "notes": [
                    "Focuses on Rust source files and Cargo.toml",
                    "Boosts main library and binary files",
                    "Semantic understanding of impl blocks and modules"
                ]
            },
            "typescript_vue_project": {
                "name": "TypeScript/Vue Project Optimization", 
                "description": "Optimized for TypeScript and Vue.js codebases",
                "use_cases": ["Frontend development", "Vue.js applications", "TypeScript projects"],
                "performance_impact": "Semantic chunking with frontend-specific optimizations",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_languages": ["typescript", "vue", "javascript"],
                    "search_file_type_weights": {
                        ".vue": 1.4,
                        ".ts": 1.3,
                        ".tsx": 1.3,
                        ".js": 1.1,
                        ".json": 0.8
                    },
                    "search_path_boosts": [
                        {"pattern": "src/", "weight": 1.3},
                        {"pattern": "components/", "weight": 1.5},
                        {"pattern": "views/", "weight": 1.3},
                        {"pattern": "composables/", "weight": 1.4},
                        {"pattern": "stores/", "weight": 1.3},
                        {"pattern": "node_modules/", "weight": 0.3}
                    ],
                    "search_language_boosts": {
                        "vue": 1.3,
                        "typescript": 1.2
                    },
                    "extensions": [".vue", ".ts", ".tsx", ".js", ".jsx", ".json", ".md"]
                },
                "notes": [
                    "Prioritizes Vue components and TypeScript files",
                    "Boosts common Vue.js directory patterns",
                    "Reduces weight of node_modules for cleaner results"
                ]
            },
            "python_project": {
                "name": "Python Project Optimization",
                "description": "Optimized for Python codebases with package structure awareness",
                "use_cases": ["Python development", "Data science", "Web applications"],
                "performance_impact": "Semantic chunking with Python-specific patterns",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_languages": ["python"],
                    "tree_sitter_max_functions_per_file": 75,
                    "tree_sitter_max_classes_per_file": 30,
                    "search_file_type_weights": {
                        ".py": 1.3,
                        ".pyx": 1.2,
                        ".pyi": 1.1,
                        ".ipynb": 0.9
                    },
                    "search_path_boosts": [
                        {"pattern": "src/", "weight": 1.3},
                        {"pattern": "__init__.py", "weight": 1.2},
                        {"pattern": "tests/", "weight": 0.9},
                        {"pattern": "__pycache__/", "weight": 0.1}
                    ],
                    "search_language_boosts": {"python": 1.2},
                    "extensions": [".py", ".pyx", ".pyi", ".ipynb", ".md", ".txt", ".yml", ".yaml"]
                },
                "notes": [
                    "Understands Python class and function structure",
                    "Boosts package initialization files",
                    "Includes Jupyter notebooks with lower priority"
                ]
            },
            "large_monorepo": {
                "name": "Large Monorepo",
                "description": "Optimized for very large repositories with multiple languages",
                "use_cases": ["Enterprise codebases", "Multi-language projects", "Large teams"],
                "performance_impact": "Balanced approach with selective Tree-sitter usage",
                "config": {
                    "chunking_strategy": "tokens",
                    "use_tree_sitter": True,
                    "tree_sitter_max_file_size_bytes": 262144,
                    "tree_sitter_max_blocks_per_file": 75,
                    "tree_sitter_skip_test_files": True,
                    "tree_sitter_skip_examples": True,
                    "batch_segment_threshold": 80,
                    "max_file_size_bytes": 524288,
                    "embed_timeout_seconds": 90,
                    "use_mmap_file_reading": True,
                    "search_max_results": 100,
                    "search_path_boosts": [
                        {"pattern": "packages/", "weight": 1.2},
                        {"pattern": "apps/", "weight": 1.2},
                        {"pattern": "libs/", "weight": 1.1},
                        {"pattern": "tools/", "weight": 0.9},
                        {"pattern": "docs/", "weight": 0.8}
                    ]
                },
                "notes": [
                    "Uses Tree-sitter selectively on smaller files",
                    "Memory mapping for efficient large file handling",
                    "Skips test files to focus on core functionality",
                    "Boosts common monorepo directory patterns"
                ]
            },
            "ci_cd_optimized": {
                "name": "CI/CD Pipeline",
                "description": "Optimized for automated builds and continuous integration",
                "use_cases": ["GitHub Actions", "Jenkins", "Automated testing"],
                "performance_impact": "Maximum speed with acceptable accuracy",
                "config": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 120,
                    "embed_timeout_seconds": 20,
                    "max_file_size_bytes": 524288,
                    "search_min_score": 0.3,
                    "skip_dot_files": True,
                    "tree_sitter_skip_test_files": True,
                    "auto_ignore_detection": True
                },
                "notes": [
                    "Prioritizes speed over semantic accuracy",
                    "Short timeouts to prevent pipeline delays",
                    "Aggressive filtering to reduce processing time",
                    "Suitable for automated code analysis"
                ]
            }
        } 
   
    def generate_config_template(self, template_name: str, base_config: Optional[Config] = None) -> Dict[str, Any]:
        """
        Generate a complete configuration template for a specific use case.
        
        Args:
            template_name: Name of the template to generate
            base_config: Optional base configuration to merge with template
            
        Returns:
            Complete configuration dictionary ready for use
            
        Raises:
            ValueError: If template_name is not recognized
        """
        examples = self.get_optimization_examples()
        
        if template_name not in examples:
            available = list(examples.keys())
            raise ValueError(f"Unknown template '{template_name}'. Available: {available}")
        
        template = examples[template_name]
        
        # Start with default configuration
        if base_config:
            config_dict = vars(base_config).copy()
        else:
            default_config = Config()
            config_dict = vars(default_config).copy()
        
        # Apply template overrides
        template_config = template["config"]
        for key, value in template_config.items():
            if hasattr(Config, key):
                config_dict[key] = value
        
        # Add template metadata
        config_dict["_template_info"] = {
            "name": template["name"],
            "description": template["description"],
            "use_cases": template["use_cases"],
            "performance_impact": template["performance_impact"],
            "notes": template.get("notes", [])
        }
        
        return config_dict
    
    def get_override_documentation(self) -> Dict[str, Any]:
        """
        Get documentation for configuration override parameters available in MCP tools.
        
        Returns:
            Dictionary containing override parameter documentation organized by tool
        """
        return {
            "index_tool_overrides": {
                "description": "Configuration parameters that can be overridden for index operations",
                "parameters": {
                    "embedding_length": {
                        "type": "integer",
                        "description": "Vector dimension for embeddings (must match model)",
                        "validation": "Must be positive integer matching model output"
                    },
                    "chunking_strategy": {
                        "type": "string",
                        "options": ["lines", "tokens", "treesitter"],
                        "description": "Strategy for splitting code into chunks"
                    },
                    "use_tree_sitter": {
                        "type": "boolean",
                        "description": "Enable semantic code structure analysis"
                    },
                    "batch_segment_threshold": {
                        "type": "integer",
                        "description": "Number of segments to batch for embedding",
                        "range": "10-200"
                    },
                    "embed_timeout_seconds": {
                        "type": "integer",
                        "description": "Timeout for embedding operations",
                        "range": "10-300"
                    },
                    "max_file_size_bytes": {
                        "type": "integer",
                        "description": "Maximum file size to process",
                        "range": "1024-10485760"
                    },
                    "tree_sitter_max_file_size_bytes": {
                        "type": "integer",
                        "description": "Maximum file size for Tree-sitter processing"
                    },
                    "tree_sitter_max_blocks_per_file": {
                        "type": "integer",
                        "description": "Maximum code blocks to extract per file"
                    },
                    "tree_sitter_skip_test_files": {
                        "type": "boolean",
                        "description": "Skip test files for Tree-sitter processing"
                    }
                },
                "examples": {
                    "speed_optimization": {
                        "chunking_strategy": "lines",
                        "use_tree_sitter": False,
                        "batch_segment_threshold": 100
                    },
                    "accuracy_optimization": {
                        "chunking_strategy": "treesitter",
                        "use_tree_sitter": True,
                        "tree_sitter_max_blocks_per_file": 150
                    }
                }
            },
            "search_tool_overrides": {
                "description": "Configuration parameters that can be overridden for search operations",
                "parameters": {
                    "search_min_score": {
                        "type": "float",
                        "description": "Minimum similarity score threshold",
                        "range": "0.0-1.0"
                    },
                    "search_max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "range": "1-500"
                    },
                    "search_file_type_weights": {
                        "type": "object",
                        "description": "File extension to score multiplier mapping",
                        "format": "{\".ext\": weight}"
                    },
                    "search_path_boosts": {
                        "type": "array",
                        "description": "Path pattern to score boost mapping",
                        "format": "[{\"pattern\": \"path/\", \"weight\": 1.2}]"
                    },
                    "search_language_boosts": {
                        "type": "object",
                        "description": "Programming language to score multiplier mapping"
                    },
                    "search_snippet_preview_chars": {
                        "type": "integer",
                        "description": "Number of characters in result snippets",
                        "range": "50-500"
                    }
                },
                "examples": {
                    "broad_search": {
                        "search_min_score": 0.2,
                        "search_max_results": 100
                    },
                    "precise_search": {
                        "search_min_score": 0.6,
                        "search_max_results": 20
                    },
                    "frontend_focused": {
                        "search_file_type_weights": {
                            ".vue": 1.4,
                            ".ts": 1.3,
                            ".js": 1.1
                        },
                        "search_path_boosts": [
                            {"pattern": "components/", "weight": 1.5},
                            {"pattern": "src/", "weight": 1.3}
                        ]
                    }
                }
            },
            "override_validation": {
                "description": "Rules for validating configuration overrides",
                "rules": [
                    "Override values must match parameter types",
                    "Numeric values must be within specified ranges",
                    "String values must be from allowed options where specified",
                    "Boolean values must be true or false",
                    "Object and array values must follow specified formats"
                ],
                "compatibility_checks": [
                    "chunking_strategy='treesitter' requires use_tree_sitter=true",
                    "tree_sitter_* parameters require use_tree_sitter=true",
                    "token_chunk_* parameters require chunking_strategy='tokens'"
                ]
            }
        }
    
    def validate_overrides(self, overrides: Dict[str, Any]) -> List[str]:
        """
        Validate configuration override parameters.
        
        Args:
            overrides: Dictionary of override parameters to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        override_doc = self.get_override_documentation()
        
        # Get all valid override parameters
        valid_params = set()
        for tool_overrides in override_doc.values():
            if "parameters" in tool_overrides:
                valid_params.update(tool_overrides["parameters"].keys())
        
        # Check for unknown parameters
        for key in overrides.keys():
            if key not in valid_params:
                errors.append(f"Unknown override parameter: {key}")
        
        # Validate specific parameters
        if "chunking_strategy" in overrides:
            valid_strategies = ["lines", "tokens", "treesitter"]
            if overrides["chunking_strategy"] not in valid_strategies:
                errors.append(f"chunking_strategy must be one of {valid_strategies}")
        
        if "search_min_score" in overrides:
            score = overrides["search_min_score"]
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                errors.append("search_min_score must be a number between 0 and 1")
        
        if "search_max_results" in overrides:
            max_results = overrides["search_max_results"]
            if not isinstance(max_results, int) or max_results <= 0:
                errors.append("search_max_results must be a positive integer")
        
        # Check compatibility rules
        if (overrides.get("chunking_strategy") == "treesitter" and 
            overrides.get("use_tree_sitter") is False):
            errors.append("chunking_strategy='treesitter' requires use_tree_sitter=true")
        
        # Check Tree-sitter parameter dependencies
        tree_sitter_params = [k for k in overrides.keys() if k.startswith("tree_sitter_")]
        if tree_sitter_params and overrides.get("use_tree_sitter") is False:
            errors.append(f"Tree-sitter parameters {tree_sitter_params} require use_tree_sitter=true")
        
        return errors