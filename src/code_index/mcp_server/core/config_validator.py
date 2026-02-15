"""
Configuration validator module for MCP server config validation.

This module handles configuration validation including override validation,
compatibility checking, and parameter verification.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ValidationResult:
    """Result of validation operation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class ConfigurationOverride:
    """
    Represents configuration parameters that can be overridden per operation.
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
        """Validate override parameters for type correctness and compatibility."""
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
        """Get dictionary of non-None override fields."""
        return {
            field: value for field, value in asdict(self).items() 
            if value is not None
        }


class ConfigValidator:
    """
    Validates configuration and override parameters.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def validate_config(self, config) -> ValidationResult:
        """Validate configuration for required fields and consistency."""
        errors = []
        warnings = []
        
        # Check required fields
        if config.embedding_length is None:
            errors.append("embedding_length must be set in configuration")
        
        # Validate chunking strategy
        valid_strategies = ["lines", "tokens", "treesitter"]
        if config.chunking_strategy not in valid_strategies:
            errors.append(f"chunking_strategy must be one of {valid_strategies}")
        
        # Validate numeric ranges
        if config.search_min_score < 0 or config.search_min_score > 1:
            errors.append("search_min_score must be between 0 and 1")
        
        if config.search_max_results <= 0:
            errors.append("search_max_results must be positive")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=[]
        )
    
    def validate_overrides(self, overrides: Dict[str, Any]) -> List[str]:
        """Validate configuration override parameters."""
        errors = []
        
        # Get all valid override parameters
        valid_params = self._get_valid_override_params()
        
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
    
    def _get_valid_override_params(self) -> set:
        """Get set of valid override parameter names."""
        return set(ConfigurationOverride.__dataclass_fields__.keys())
    
    def check_override_compatibility(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Check compatibility of override parameters and suggest corrections."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            override_obj = ConfigurationOverride(**overrides)
            validation_errors = override_obj.validate()
            
            if validation_errors:
                result["valid"] = False
                result["errors"] = validation_errors
            
            # Check for common compatibility issues
            if override_obj.chunking_strategy == "treesitter" and override_obj.use_tree_sitter is None:
                result["suggestions"].append("Consider setting use_tree_sitter=true for treesitter chunking strategy")
            
            if override_obj.use_tree_sitter is True and override_obj.chunking_strategy == "lines":
                result["warnings"].append("Tree-sitter enabled but using line-based chunking - consider 'treesitter' strategy")
            
            if override_obj.batch_segment_threshold is not None and override_obj.batch_segment_threshold > 100:
                result["warnings"].append("Large batch_segment_threshold may cause memory issues")
            
            if override_obj.embed_timeout_seconds is not None and override_obj.embed_timeout_seconds < 30:
                result["warnings"].append("Short embed_timeout_seconds may cause timeouts on slower systems")
            
        except Exception as e:
            result["valid"] = False
            result["errors"].append(str(e))
        
        return result


def create_validator(logger=None) -> ConfigValidator:
    """Factory function to create a ConfigValidator."""
    return ConfigValidator(logger)
