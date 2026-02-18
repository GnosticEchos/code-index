"""MCP Configuration Manager - manages configuration loading, validation,
and override application for the MCP server.
"""
from __future__ import annotations

import copy
import dataclasses
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from code_index.config import Config
from code_index.mcp_server.core.config_validator import (
    ConfigurationOverride,  # re-exported for consumers
    ConfigValidator,
)

# -------------------------------------------------------------------
# Type-checking sets used in _create_override_object
# -------------------------------------------------------------------
_INTEGER_FIELDS = frozenset({
    "embedding_length",
    "batch_segment_threshold",
    "search_max_results",
    "embed_timeout_seconds",
    "max_file_size_bytes",
    "tree_sitter_max_file_size_bytes",
    "tree_sitter_min_block_chars",
    "tree_sitter_max_blocks_per_file",
    "tree_sitter_max_functions_per_file",
    "tree_sitter_max_classes_per_file",
    "tree_sitter_max_impl_blocks_per_file",
    "token_chunk_size",
    "token_chunk_overlap",
    "mmap_min_file_size_bytes",
    "search_snippet_preview_chars",
})
_FLOAT_FIELDS = frozenset({"search_min_score"})
_BOOL_FIELDS = frozenset({
    "use_tree_sitter",
    "tree_sitter_skip_test_files",
    "tree_sitter_skip_examples",
    "tree_sitter_debug_logging",
    "use_mmap_file_reading",
    "auto_extensions",
    "skip_dot_files",
    "auto_ignore_detection",
})
_STR_FIELDS = frozenset({"chunking_strategy"})


class MCPConfigurationManager:
    """Manages configuration loading, validation, and override application
    for the MCP code-index server.
    """

    def __init__(self, config_path: str = "code_index.json") -> None:
        self.config_path: str = config_path
        self._base_config: Optional[Config] = None
        self._validator = ConfigValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_config(self) -> Config:
        """Load and validate configuration from *config_path*.

        Creates a default configuration file if it does not yet exist.

        Returns:
            Validated :class:`Config` object (also stored as
            ``self._base_config``).

        Raises:
            ValueError: When the loaded configuration fails validation.
        """
        if not os.path.exists(self.config_path):
            config = Config()
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            config.save(self.config_path)
        else:
            config = Config.from_file(self.config_path)

        try:
            self._validate_config(config)
        except ValueError as exc:
            raise ValueError(f"Configuration validation failed: {exc}") from exc

        self._base_config = config
        return config

    def apply_overrides(
        self, base_config: Config, overrides: Dict[str, Any]
    ) -> Config:
        """Apply *overrides* on top of *base_config*, returning a new Config.

        The original *base_config* is left unchanged.

        Raises:
            ValueError: When overrides are invalid or mutually incompatible.
        """
        override_obj = self._create_override_object(overrides)
        errors = override_obj.validate()
        if errors:
            raise ValueError(
                f"Configuration override validation failed: {'; '.join(errors)}"
            )

        new_config = copy.deepcopy(base_config)
        override_field_names = {
            f.name for f in dataclasses.fields(ConfigurationOverride)
        }
        for key, value in overrides.items():
            if key in override_field_names:
                try:
                    setattr(new_config, key, value)
                except (AttributeError, TypeError):
                    pass

        return new_config

    def get_available_overrides(self) -> List[str]:
        """Return a list of all supported override parameter names."""
        return [f.name for f in dataclasses.fields(ConfigurationOverride)]

    def check_override_compatibility(
        self, overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check *overrides* for hard errors, soft warnings, and suggestions.

        Returns:
            dict with keys ``valid`` (bool), ``errors``, ``warnings``,
            and ``suggestions`` (each a list of strings).
        """
        return self._validator.check_override_compatibility(overrides)

    def get_config_documentation(self) -> Dict[str, Any]:
        """Return structured documentation for all configuration parameters."""
        return {
            "categories": {
                "core": {
                    "description": "Core service connection settings",
                    "parameters": [
                        "ollama_base_url",
                        "ollama_model",
                        "qdrant_url",
                        "embedding_length",
                        "embed_timeout_seconds",
                    ],
                },
                "performance": {
                    "description": "Performance and throughput tuning",
                    "parameters": [
                        "batch_segment_threshold",
                        "use_mmap_file_reading",
                        "mmap_min_file_size_bytes",
                    ],
                },
                "chunking": {
                    "description": "Code chunking and segmentation strategy",
                    "parameters": [
                        "chunking_strategy",
                        "use_tree_sitter",
                        "token_chunk_size",
                        "token_chunk_overlap",
                    ],
                },
                "search": {
                    "description": "Search result filtering and scoring",
                    "parameters": ["search_min_score", "search_max_results"],
                },
                "advanced": {
                    "description": "Advanced tree-sitter and parser settings",
                    "parameters": [
                        "tree_sitter_max_file_size_bytes",
                        "tree_sitter_skip_test_files",
                    ],
                },
            },
            "examples": {
                "basic": {
                    "embedding_length": 768,
                    "chunking_strategy": "lines",
                },
                "treesitter_semantic": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "embedding_length": 768,
                },
            },
            "optimization_strategies": {
                "fast_indexing": {
                    "description": "Optimized for indexing speed",
                    "settings": {
                        "chunking_strategy": "lines",
                        "use_tree_sitter": False,
                    },
                },
                "maximum_accuracy": {
                    "description": "Optimized for semantic search accuracy",
                    "settings": {
                        "chunking_strategy": "treesitter",
                        "use_tree_sitter": True,
                    },
                },
            },
            "parameter_compatibility": {
                "treesitter_requires_flag": (
                    "chunking_strategy='treesitter' requires use_tree_sitter=true"
                ),
                "token_params_require_strategy": (
                    "token_chunk_* parameters require chunking_strategy='tokens'"
                ),
            },
            "troubleshooting": {
                "embed_timeouts": "Increase embed_timeout_seconds (default: 60)",
                "memory_pressure": "Reduce batch_segment_threshold",
                "poor_search_quality": (
                    "Lower search_min_score or increase search_max_results"
                ),
            },
        }

    def get_optimization_examples(self) -> Dict[str, Any]:
        """Return pre-built optimisation example configurations."""
        return {
            "fast_indexing": {
                "description": "Optimized for maximum indexing throughput",
                "overrides": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 30,
                    "embed_timeout_seconds": 30,
                },
            },
            "maximum_accuracy": {
                "description": "Optimized for best semantic search accuracy",
                "overrides": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "embedding_length": 768,
                    "batch_segment_threshold": 60,
                },
            },
            "balanced": {
                "description": "Balanced performance and accuracy",
                "overrides": {
                    "chunking_strategy": "tokens",
                    "token_chunk_size": 1000,
                    "batch_segment_threshold": 60,
                },
            },
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_config(self, config: Config) -> None:
        """Raise :exc:`ValueError` if *config* contains invalid values."""
        result = self._validator.validate_config(config)
        if not result.valid:
            raise ValueError("; ".join(result.errors))

    def _create_override_object(
        self, overrides: Dict[str, Any]
    ) -> ConfigurationOverride:
        """Build a :class:`ConfigurationOverride` from a raw dict.

        Unknown keys are silently ignored.

        Raises:
            ValueError: If any supplied value has the wrong Python type.
        """
        override_field_names = {
            f.name for f in dataclasses.fields(ConfigurationOverride)
        }
        type_errors: List[str] = []
        kwargs: Dict[str, Any] = {}

        for key, value in overrides.items():
            if key not in override_field_names:
                continue

            if key in _INTEGER_FIELDS:
                # bool is a subclass of int – reject booleans for integer fields
                if not isinstance(value, int) or isinstance(value, bool):
                    type_errors.append(
                        f"{key} must be an integer, got {type(value).__name__}"
                    )
                    continue
            elif key in _FLOAT_FIELDS:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    type_errors.append(
                        f"{key} must be a number, got {type(value).__name__}"
                    )
                    continue
            elif key in _BOOL_FIELDS:
                if not isinstance(value, bool):
                    type_errors.append(
                        f"{key} must be a boolean, got {type(value).__name__}"
                    )
                    continue
            elif key in _STR_FIELDS:
                if not isinstance(value, str):
                    type_errors.append(
                        f"{key} must be a string, got {type(value).__name__}"
                    )
                    continue

            kwargs[key] = value

        if type_errors:
            raise ValueError(
                f"Invalid override parameters: {'; '.join(type_errors)}"
            )

        return ConfigurationOverride(**kwargs)
