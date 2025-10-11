"""Configuration management for the code index tool with domain-specific sections."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass, field, replace, is_dataclass
from typing import Dict, List, Optional, Any, Tuple


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value is not None else default


def _default_extensions() -> List[str]:
    return [
        ".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx",
        ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php",
        ".swift", ".kt", ".scala", ".dart", ".lua", ".pl", ".pm",
        ".t", ".r", ".sql", ".html", ".css", ".scss", ".sass", ".less",
        ".md", ".markdown", ".rst", ".txt", ".json", ".xml", ".yaml", ".yml",
    ]


def _default_tree_sitter_skip_patterns() -> List[str]:
    return [
        "*.min.js", "*.bundle.js", "*.min.css",
        "package-lock.json", "yarn.lock",
        "*.lock",
        "target/", "build/", "dist/",
        "__pycache__/", "node_modules/",
        "*.log", "*.tmp", "*.temp",
    ]


def _default_search_file_type_weights() -> Dict[str, float]:
    return {
        ".vue": 1.30,
        ".ts": 1.25,
        ".tsx": 1.25,
        ".rs": 1.20,
        ".surql": 1.25,
        ".js": 1.10,
        ".md": 0.80,
        ".txt": 0.60,
    }


def _default_search_path_boosts() -> List[Dict[str, Any]]:
    return [
        {"pattern": "src/", "weight": 1.25},
        {"pattern": "components/", "weight": 1.25},
        {"pattern": "views/", "weight": 1.15},
        {"pattern": "docs/", "weight": 0.85},
        {"pattern": "console-export", "weight": 0.60},
        {"pattern": "Daisy_llms.txt", "weight": 0.60},
    ]


def _default_search_language_boosts() -> Dict[str, float]:
    return {
        "typescript": 1.15,
        "rust": 1.10,
    }


def _default_language_chunk_sizes() -> Dict[str, int]:
    return {
        "python": 64 * 1024,
        "javascript": 128 * 1024,
        "typescript": 128 * 1024,
        "java": 256 * 1024,
        "cpp": 256 * 1024,
        "rust": 128 * 1024,
        "go": 128 * 1024,
        "text": 32 * 1024,
        "markdown": 32 * 1024,
        "json": 64 * 1024,
        "xml": 128 * 1024,
        "yaml": 32 * 1024,
    }


def _default_fallback_parser_patterns() -> Dict[str, List[str]]:
    return {
        "text": ["*.txt", "*.log", "*.md", "*.rst"],
        "config": ["*.ini", "*.cfg", "*.conf", "*.properties"],
        "data": ["*.csv", "*.tsv", "*.json", "*.xml", "*.yaml"],
        "documentation": ["*.md", "*.rst", "*.txt"],
        "plain_text": ["*.txt", "*.log", "*.out", "*.err"],
    }


def normalize_ignore_override_patterns(value: Any) -> List[str]:
    """Normalize ignore override patterns into a deduplicated list of strings."""

    normalized: List[str] = []

    def _append_unique(pattern: str) -> None:
        if pattern and pattern not in normalized:
            normalized.append(pattern)

    def _process(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, str):
            text = item.replace("\n", " ")
            for part in text.split(","):
                # Allow whitespace-separated values inside each comma chunk
                for candidate in part.strip().split():
                    cleaned = candidate.strip()
                    if cleaned:
                        _append_unique(cleaned)
            return
        if isinstance(item, (list, tuple, set)):
            for inner in item:
                _process(inner)
            return
        raise TypeError("Ignore override patterns must be strings or iterables of strings")

    _process(value)
    return normalized


@dataclass
class CoreConfig:
    workspace_path: str = field(default_factory=lambda: _env_str("WORKSPACE_PATH", "."))
    ollama_base_url: str = field(default_factory=lambda: _env_str("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: _env_str("OLLAMA_MODEL", "nomic-embed-text:latest"))
    qdrant_url: str = field(default_factory=lambda: _env_str("QDRANT_URL", "http://localhost:6333"))
    qdrant_api_key: Optional[str] = field(default_factory=lambda: _env_str("QDRANT_API_KEY"))
    embedding_length: Optional[int] = None
    embed_timeout_seconds: int = field(default_factory=lambda: _env_int("CODE_INDEX_EMBED_TIMEOUT", 60))

    def refresh_embedding_length(self) -> None:
        if self.embedding_length not in (None, 0):
            return
        model_name = (self.ollama_model or "").lower()
        if "nomic-embed-text" in model_name:
            self.embedding_length = 768
        elif "qwen3-embedding" in model_name or "qwen" in model_name:
            self.embedding_length = 1024
        elif "text-embedding-3-large" in model_name:
            self.embedding_length = 3584
        else:
            self.embedding_length = 768


@dataclass
class FileHandlingConfig:
    extensions: List[str] = field(default_factory=_default_extensions)
    max_file_size_bytes: int = 1 * 1024 * 1024
    batch_segment_threshold: int = 60
    exclude_files_path: Optional[str] = None
    timeout_log_path: str = "timeout_files.txt"
    skip_dot_files: bool = True
    read_root_gitignore_only: bool = True


@dataclass
class IgnoreConfig:
    ignore_config_path: Optional[str] = None
    ignore_override_pattern: Optional[str] = None
    ignore_override_patterns: List[str] = field(default_factory=list)
    auto_ignore_detection: bool = True
    apply_github_templates: bool = True
    apply_project_gitignore: bool = True
    apply_global_ignores: bool = True
    learn_from_indexing: bool = False


@dataclass
class ChunkingConfig:
    chunking_strategy: str = "lines"
    token_chunk_size: int = 1000
    token_chunk_overlap: int = 200
    auto_extensions: bool = False
    language_chunk_sizes: Dict[str, int] = field(default_factory=_default_language_chunk_sizes)


@dataclass
class TreeSitterConfig:
    use_tree_sitter: bool = False
    tree_sitter_languages: Optional[List[str]] = None
    tree_sitter_max_file_size_bytes: int = 512 * 1024
    tree_sitter_min_block_chars_default: int = field(default_factory=lambda: _env_int("TREE_SITTER_MIN_BLOCK_CHARS_DEFAULT", 30))
    tree_sitter_min_block_chars: Optional[int] = None
    tree_sitter_min_block_chars_overrides: Dict[str, int] = field(default_factory=dict)
    tree_sitter_max_blocks_per_file: int = 100
    tree_sitter_max_functions_per_file: int = 50
    tree_sitter_max_classes_per_file: int = 20
    tree_sitter_max_impl_blocks_per_file: int = 30
    tree_sitter_skip_test_files: bool = True
    tree_sitter_skip_examples: bool = True
    tree_sitter_skip_patterns: List[str] = field(default_factory=_default_tree_sitter_skip_patterns)
    tree_sitter_debug_logging: bool = False


@dataclass
class SearchConfig:
    search_min_score: float = 0.4
    search_max_results: int = 50
    search_file_type_weights: Dict[str, float] = field(default_factory=_default_search_file_type_weights)
    search_path_boosts: List[Dict[str, Any]] = field(default_factory=_default_search_path_boosts)
    search_language_boosts: Dict[str, float] = field(default_factory=_default_search_language_boosts)
    search_exclude_patterns: List[str] = field(default_factory=list)
    search_snippet_preview_chars: int = 160


@dataclass
class PerformanceConfig:
    use_mmap_file_reading: bool = False
    mmap_min_file_size_bytes: int = 64 * 1024
    enable_chunked_processing: bool = True
    large_file_threshold_bytes: int = 256 * 1024
    streaming_threshold_bytes: int = 1024 * 1024
    default_chunk_size_bytes: int = 64 * 1024
    max_chunk_size_bytes: int = 512 * 1024
    memory_optimization_threshold_mb: int = 100
    enable_progressive_indexing: bool = True
    chunk_size_optimization: bool = True
    enable_fallback_parsers: bool = True
    fallback_parser_patterns: Dict[str, List[str]] = field(default_factory=_default_fallback_parser_patterns)
    enable_hybrid_parsing: bool = True
    parser_performance_monitoring: bool = True
    max_parser_memory_mb: int = 50
    parser_timeout_seconds: int = 30
    enable_parser_caching: bool = True
    parser_cache_size: int = 50
    enable_performance_monitoring: bool = True
    performance_stats_interval: int = 100
    enable_memory_profiling: bool = False
    memory_profiling_threshold_mb: int = 500


@dataclass
class LoggingConfig:
    component_levels: Dict[str, Any] = field(default_factory=dict)


class Config:
    """Configuration class composed of domain-specific settings."""

    SECTION_NAMES = {
        "core",
        "files",
        "ignore",
        "chunking",
        "tree_sitter",
        "search",
        "performance",
        "logging",
    }

    SECTION_ATTR_MAP: Dict[str, Tuple[str, str]] = {
        # Core
        "workspace_path": ("core", "workspace_path"),
        "ollama_base_url": ("core", "ollama_base_url"),
        "ollama_model": ("core", "ollama_model"),
        "qdrant_url": ("core", "qdrant_url"),
        "qdrant_api_key": ("core", "qdrant_api_key"),
        "embedding_length": ("core", "embedding_length"),
        "embed_timeout_seconds": ("core", "embed_timeout_seconds"),
        # File handling
        "extensions": ("files", "extensions"),
        "max_file_size_bytes": ("files", "max_file_size_bytes"),
        "batch_segment_threshold": ("files", "batch_segment_threshold"),
        "exclude_files_path": ("files", "exclude_files_path"),
        "timeout_log_path": ("files", "timeout_log_path"),
        "skip_dot_files": ("files", "skip_dot_files"),
        "read_root_gitignore_only": ("files", "read_root_gitignore_only"),
        # Ignore
        "ignore_config_path": ("ignore", "ignore_config_path"),
        "ignore_override_pattern": ("ignore", "ignore_override_pattern"),
        "ignore_override_patterns": ("ignore", "ignore_override_patterns"),
        "auto_ignore_detection": ("ignore", "auto_ignore_detection"),
        "apply_github_templates": ("ignore", "apply_github_templates"),
        "apply_project_gitignore": ("ignore", "apply_project_gitignore"),
        "apply_global_ignores": ("ignore", "apply_global_ignores"),
        "learn_from_indexing": ("ignore", "learn_from_indexing"),
        # Chunking
        "chunking_strategy": ("chunking", "chunking_strategy"),
        "token_chunk_size": ("chunking", "token_chunk_size"),
        "token_chunk_overlap": ("chunking", "token_chunk_overlap"),
        "auto_extensions": ("chunking", "auto_extensions"),
        "language_chunk_sizes": ("chunking", "language_chunk_sizes"),
        # Tree-sitter
        "use_tree_sitter": ("tree_sitter", "use_tree_sitter"),
        "tree_sitter_languages": ("tree_sitter", "tree_sitter_languages"),
        "tree_sitter_max_file_size_bytes": ("tree_sitter", "tree_sitter_max_file_size_bytes"),
        "tree_sitter_min_block_chars_default": ("tree_sitter", "tree_sitter_min_block_chars_default"),
        "tree_sitter_min_block_chars": ("tree_sitter", "tree_sitter_min_block_chars"),
        "tree_sitter_min_block_chars_overrides": ("tree_sitter", "tree_sitter_min_block_chars_overrides"),
        "tree_sitter_max_blocks_per_file": ("tree_sitter", "tree_sitter_max_blocks_per_file"),
        "tree_sitter_max_functions_per_file": ("tree_sitter", "tree_sitter_max_functions_per_file"),
        "tree_sitter_max_classes_per_file": ("tree_sitter", "tree_sitter_max_classes_per_file"),
        "tree_sitter_max_impl_blocks_per_file": ("tree_sitter", "tree_sitter_max_impl_blocks_per_file"),
        "tree_sitter_skip_test_files": ("tree_sitter", "tree_sitter_skip_test_files"),
        "tree_sitter_skip_examples": ("tree_sitter", "tree_sitter_skip_examples"),
        "tree_sitter_skip_patterns": ("tree_sitter", "tree_sitter_skip_patterns"),
        "tree_sitter_debug_logging": ("tree_sitter", "tree_sitter_debug_logging"),
        # Search
        "search_min_score": ("search", "search_min_score"),
        "search_max_results": ("search", "search_max_results"),
        "search_file_type_weights": ("search", "search_file_type_weights"),
        "search_path_boosts": ("search", "search_path_boosts"),
        "search_language_boosts": ("search", "search_language_boosts"),
        "search_exclude_patterns": ("search", "search_exclude_patterns"),
        "search_snippet_preview_chars": ("search", "search_snippet_preview_chars"),
        # Performance
        "use_mmap_file_reading": ("performance", "use_mmap_file_reading"),
        "mmap_min_file_size_bytes": ("performance", "mmap_min_file_size_bytes"),
        "enable_chunked_processing": ("performance", "enable_chunked_processing"),
        "large_file_threshold_bytes": ("performance", "large_file_threshold_bytes"),
        "streaming_threshold_bytes": ("performance", "streaming_threshold_bytes"),
        "default_chunk_size_bytes": ("performance", "default_chunk_size_bytes"),
        "max_chunk_size_bytes": ("performance", "max_chunk_size_bytes"),
        "memory_optimization_threshold_mb": ("performance", "memory_optimization_threshold_mb"),
        "enable_progressive_indexing": ("performance", "enable_progressive_indexing"),
        "chunk_size_optimization": ("performance", "chunk_size_optimization"),
        "enable_fallback_parsers": ("performance", "enable_fallback_parsers"),
        "fallback_parser_patterns": ("performance", "fallback_parser_patterns"),
        "enable_hybrid_parsing": ("performance", "enable_hybrid_parsing"),
        "parser_performance_monitoring": ("performance", "parser_performance_monitoring"),
        "max_parser_memory_mb": ("performance", "max_parser_memory_mb"),
        "parser_timeout_seconds": ("performance", "parser_timeout_seconds"),
        "enable_parser_caching": ("performance", "enable_parser_caching"),
        "parser_cache_size": ("performance", "parser_cache_size"),
        "enable_performance_monitoring": ("performance", "enable_performance_monitoring"),
        "performance_stats_interval": ("performance", "performance_stats_interval"),
        "enable_memory_profiling": ("performance", "enable_memory_profiling"),
        "memory_profiling_threshold_mb": ("performance", "memory_profiling_threshold_mb"),
        # Logging
        "logging_component_levels": ("logging", "component_levels"),
    }

    def __init__(
        self,
        core: Optional[CoreConfig] = None,
        files: Optional[FileHandlingConfig] = None,
        ignore: Optional[IgnoreConfig] = None,
        chunking: Optional[ChunkingConfig] = None,
        tree_sitter: Optional[TreeSitterConfig] = None,
        search: Optional[SearchConfig] = None,
        performance: Optional[PerformanceConfig] = None,
        logging: Optional[LoggingConfig] = None,
    ) -> None:
        object.__setattr__(self, "core", replace(core) if core else CoreConfig())
        object.__setattr__(self, "files", replace(files) if files else FileHandlingConfig())
        object.__setattr__(self, "ignore", replace(ignore) if ignore else IgnoreConfig())
        object.__setattr__(self, "chunking", replace(chunking) if chunking else ChunkingConfig())
        object.__setattr__(self, "tree_sitter", replace(tree_sitter) if tree_sitter else TreeSitterConfig())
        object.__setattr__(self, "search", replace(search) if search else SearchConfig())
        object.__setattr__(self, "performance", replace(performance) if performance else PerformanceConfig())
        object.__setattr__(self, "logging", replace(logging) if logging else LoggingConfig())

        # Refresh derived values and environment overrides
        self.core.refresh_embedding_length()

    # ------------------------------------------------------------------
    # Attribute access bridging
    # ------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        section_path = self.SECTION_ATTR_MAP.get(name)
        if section_path is None:
            raise AttributeError(f"Config has no attribute {name!r}")
        section_name, attr_name = section_path
        section = object.__getattribute__(self, section_name)
        return getattr(section, attr_name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.SECTION_NAMES:
            if value is None or not is_dataclass(value):
                raise TypeError(f"Section {name} must be initialized with a dataclass instance")
            object.__setattr__(self, name, replace(value))
            return

        section_path = self.SECTION_ATTR_MAP.get(name)
        if section_path is not None:
            section_name, attr_name = section_path
            section = object.__getattribute__(self, section_name)
            setattr(section, attr_name, value)
            if (section_name, attr_name) == ("core", "ollama_model"):
                self.core.refresh_embedding_length()
            return

        object.__setattr__(self, name, value)

    # ------------------------------------------------------------------
    # Legacy serialization helpers (to be refined in later steps)
    # ------------------------------------------------------------------
    def to_nested_dict(self) -> Dict[str, Any]:
        return {
            "core": self._section_to_dict(self.core),
            "files": self._section_to_dict(self.files),
            "ignore": self._section_to_dict(self.ignore),
            "chunking": self._section_to_dict(self.chunking),
            "tree_sitter": self._section_to_dict(self.tree_sitter),
            "search": self._section_to_dict(self.search),
            "performance": self._section_to_dict(self.performance),
            "logging": self._section_to_dict(self.logging),
        }

    def to_dict(self) -> Dict[str, Any]:
        nested = self.to_nested_dict()
        flattened: Dict[str, Any] = {}
        for key, (section_name, attr_name) in self.SECTION_ATTR_MAP.items():
            flattened[key] = nested[section_name][attr_name]
        return flattened

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        config = cls()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            config.update_from_dict(data)

        config.embed_timeout_seconds = _env_int("CODE_INDEX_EMBED_TIMEOUT", config.embed_timeout_seconds)
        config.core.refresh_embedding_length()
        return config

    def save(self, config_path: str) -> None:
        data = self.to_dict()
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def __str__(self) -> str:
        return (
            "Config("
            f"ollama_base_url={self.ollama_base_url}, "
            f"ollama_model={self.ollama_model}, "
            f"qdrant_url={self.qdrant_url}, "
            f"workspace_path={self.workspace_path}, "
            f"extensions_count={len(self.extensions)}, "
            f"embedding_length={self.embedding_length}, "
            f"chunking_strategy={self.chunking_strategy})"
        )

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            if key in self.SECTION_NAMES and isinstance(value, dict):
                section = object.__getattribute__(self, key)
                for inner_key, inner_value in value.items():
                    if hasattr(section, inner_key) and inner_key in self.SECTION_ATTR_MAP:
                        setattr(self, inner_key, inner_value)
                continue

            if key in self.SECTION_ATTR_MAP:
                setattr(self, key, value)

    @staticmethod
    def _section_to_dict(section: Any) -> Dict[str, Any]:
        if not is_dataclass(section):
            raise TypeError("Section must be a dataclass instance")
        result: Dict[str, Any] = {}
        for field_name in section.__dataclass_fields__:
            result[field_name] = deepcopy(getattr(section, field_name))
        return result
