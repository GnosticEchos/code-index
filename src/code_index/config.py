"""
Configuration management for the code index tool.
"""
import json
import os
from typing import List, Optional


class Config:
    """Configuration class for the code index tool."""
    
    def __init__(self):
        """Initialize with default configuration."""
        # Core endpoints and workspace
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "nomic-embed-text:latest")
        self.qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY")
        self.workspace_path: str = os.getenv("WORKSPACE_PATH", ".")
        
        # File handling and scanning
        self.extensions: List[str] = [
            ".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx",
            ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php",
            ".swift", ".kt", ".scala", ".dart", ".lua", ".pl", ".pm",
            ".t", ".r", ".sql", ".html", ".css", ".scss", ".sass", ".less",
            ".md", ".markdown", ".rst", ".txt", ".json", ".xml", ".yaml", ".yml"
        ]
        self.max_file_size_bytes: int = 1 * 1024 * 1024  # 1MB
        self.batch_segment_threshold: int = 60
        
        # Chunking strategy configuration
        self.chunking_strategy: str = "lines"  # "lines", "tokens", or "treesitter"
        self.token_chunk_size: int = 1000
        self.token_chunk_overlap: int = 200
        
        # Tree-sitter configuration (new)
        self.use_tree_sitter: bool = False
        self.tree_sitter_languages: Optional[List[str]] = None
        # Smart limit: Most valuable code is in reasonably-sized files
        # Generated/minified files (>512KB) are typically not semantically valuable
        self.tree_sitter_max_file_size_bytes: int = 512 * 1024  # 512KB
        self.tree_sitter_min_block_chars: Optional[int] = None
        self.tree_sitter_max_blocks_per_file: int = 100
        self.tree_sitter_max_functions_per_file: int = 50
        self.tree_sitter_max_classes_per_file: int = 20
        self.tree_sitter_max_impl_blocks_per_file: int = 30
        self.tree_sitter_skip_test_files: bool = True
        self.tree_sitter_skip_examples: bool = True
        # Debug logging for Tree-sitter internals
        self.tree_sitter_debug_logging: bool = False
        
        # File type filtering (like ignore patterns for Tree-sitter)
        self.tree_sitter_skip_patterns: List[str] = [
            "*.min.js", "*.bundle.js", "*.min.css",  # Minified assets
            "package-lock.json", "yarn.lock",         # Lock files
            "*.lock",                                 # Generic lock files
            "target/", "build/", "dist/",             # Build directories
            "__pycache__/", "node_modules/",          # Dependency directories
            "*.log", "*.tmp", "*.temp",               # Log/temp files
        ]
        
        # Ignore pattern configuration
        self.ignore_config_path: Optional[str] = None
        self.ignore_override_pattern: Optional[str] = None
        self.auto_ignore_detection: bool = True
        self.apply_github_templates: bool = True
        self.apply_project_gitignore: bool = True
        self.apply_global_ignores: bool = True
        self.learn_from_indexing: bool = False
        self.search_min_score: float = 0.4
        self.search_max_results: int = 50

        # Search ranking configuration (file-type/path/language weighting)
        self.search_file_type_weights: dict = {
            ".vue": 1.30,
            ".ts": 1.25,
            ".tsx": 1.25,
            ".rs": 1.20,
            ".surql": 1.25,
            ".js": 1.10,
            ".md": 0.80,
            ".txt": 0.60,
        }
        self.search_path_boosts: list = [
            {"pattern": "src/", "weight": 1.25},
            {"pattern": "components/", "weight": 1.25},
            {"pattern": "views/", "weight": 1.15},
            {"pattern": "docs/", "weight": 0.85},
            {"pattern": "console-export", "weight": 0.60},
            {"pattern": "Daisy_llms.txt", "weight": 0.60},
        ]
        self.search_language_boosts: dict = {
            "vue": 1.20,
            "typescript": 1.15,
            "rust": 1.10,
        }
        self.search_exclude_patterns: list = []
        self.search_snippet_preview_chars: int = 160
         
        # Dot file handling configuration
        self.skip_dot_files: bool = True
        self.read_root_gitignore_only: bool = True

        # New configuration fields (config-first behavior)
        # Set default embedding_length based on model if None
        model_name = self.ollama_model.lower()
        if "nomic-embed-text" in model_name:
            self.embedding_length: Optional[int] = 768
        elif "qwen3-embedding" in model_name or "qwen" in model_name:
            self.embedding_length: Optional[int] = 1024
        elif "text-embedding-3-large" in model_name:
            self.embedding_length: Optional[int] = 3584
        else:
            # Default fallback for unknown models
            self.embedding_length: Optional[int] = 768

        # Timeout for embedding calls: default 60, may be overridden by env CODE_INDEX_EMBED_TIMEOUT
        embed_timeout_env = os.getenv("CODE_INDEX_EMBED_TIMEOUT")
        try:
            self.embed_timeout_seconds: int = int(embed_timeout_env) if embed_timeout_env else 60
        except ValueError:
            self.embed_timeout_seconds = 60

        # Auto-extensions augmentation via Pygments lexers
        self.auto_extensions: bool = False

        # Optional path to a file containing newline-separated relative paths to exclude permanently
        self.exclude_files_path: Optional[str] = None

        # Path where timed out files are recorded
        self.timeout_log_path: str = "timeout_files.txt"
        
        # Memory-mapped file reading configuration
        self.use_mmap_file_reading: bool = False
        self.mmap_min_file_size_bytes: int = 64 * 1024  # 64KB minimum for mmap
        
        # Scalability configuration for large file handling
        self.enable_chunked_processing: bool = True
        self.large_file_threshold_bytes: int = 256 * 1024  # 256KB threshold for large files
        self.streaming_threshold_bytes: int = 1024 * 1024  # 1MB threshold for streaming
        self.default_chunk_size_bytes: int = 64 * 1024  # 64KB default chunk size
        self.max_chunk_size_bytes: int = 512 * 1024  # 512KB max chunk size
        self.memory_optimization_threshold_mb: int = 100  # 100MB memory usage threshold
        self.enable_progressive_indexing: bool = True
        self.chunk_size_optimization: bool = True
        
        # Parser scalability configuration
        self.enable_fallback_parsers: bool = True
        self.enable_hybrid_parsing: bool = True
        self.parser_performance_monitoring: bool = True
        self.max_parser_memory_mb: int = 50  # 50MB max memory per parser
        self.parser_timeout_seconds: int = 30  # 30 second timeout for parsing operations
        self.enable_parser_caching: bool = True
        self.parser_cache_size: int = 50  # Maximum 50 parsers in cache
        
        # File type specific chunking configuration
        self.language_chunk_sizes: dict = {
            "python": 64 * 1024,      # Python files tend to be smaller
            "javascript": 128 * 1024, # JS files can be larger
            "typescript": 128 * 1024,
            "java": 256 * 1024,       # Java files are often larger
            "cpp": 256 * 1024,
            "rust": 128 * 1024,
            "go": 128 * 1024,
            "text": 32 * 1024,        # Text files can use smaller chunks
            "markdown": 32 * 1024,
            "json": 64 * 1024,
            "xml": 128 * 1024,
            "yaml": 32 * 1024
        }
        
        # Fallback parser configuration
        self.fallback_parser_patterns: dict = {
            "text": ["*.txt", "*.log", "*.md", "*.rst"],
            "config": ["*.ini", "*.cfg", "*.conf", "*.properties"],
            "data": ["*.csv", "*.tsv", "*.json", "*.xml", "*.yaml"],
            "documentation": ["*.md", "*.rst", "*.txt"],
            "plain_text": ["*.txt", "*.log", "*.out", "*.err"]
        }
        
        # Performance monitoring configuration
        self.enable_performance_monitoring: bool = True
        self.performance_stats_interval: int = 100  # Collect stats every 100 operations
        self.enable_memory_profiling: bool = False
        self.memory_profiling_threshold_mb: int = 500  # Profile when memory usage > 500MB
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from a JSON file."""
        config = cls()
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = json.load(f)
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        # Respect env override for embedding timeout after file load
        # CODE_INDEX_EMBED_TIMEOUT (int) takes precedence over saved config
        embed_timeout_env = os.getenv("CODE_INDEX_EMBED_TIMEOUT")
        if embed_timeout_env:
            try:
                config.embed_timeout_seconds = int(embed_timeout_env)
            except ValueError:
                # Ignore invalid env value; keep previously loaded config value
                pass
        return config
    
    def save(self, config_path: str) -> None:
        """Save configuration to a JSON file."""
        data = {
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "qdrant_url": self.qdrant_url,
            "qdrant_api_key": self.qdrant_api_key,
            "workspace_path": self.workspace_path,
            "extensions": self.extensions,
            "max_file_size_bytes": self.max_file_size_bytes,
            "batch_segment_threshold": self.batch_segment_threshold,
            "search_min_score": self.search_min_score,
            "search_max_results": self.search_max_results,

            # Search ranking configuration
            "search_file_type_weights": self.search_file_type_weights,
            "search_path_boosts": self.search_path_boosts,
            "search_language_boosts": self.search_language_boosts,
            "search_exclude_patterns": self.search_exclude_patterns,
            "search_snippet_preview_chars": self.search_snippet_preview_chars,

            # New keys
            "embedding_length": self.embedding_length,
            "embed_timeout_seconds": self.embed_timeout_seconds,
            "chunking_strategy": self.chunking_strategy,
            "token_chunk_size": self.token_chunk_size,
            "token_chunk_overlap": self.token_chunk_overlap,
            "auto_extensions": self.auto_extensions,
            "exclude_files_path": self.exclude_files_path,
            "timeout_log_path": self.timeout_log_path,
            "auto_ignore_detection": self.auto_ignore_detection,
            # Dot file handling configuration
            "skip_dot_files": self.skip_dot_files,
            "read_root_gitignore_only": self.read_root_gitignore_only,
            # Memory-mapped file reading configuration
            "use_mmap_file_reading": self.use_mmap_file_reading,
            "mmap_min_file_size_bytes": self.mmap_min_file_size_bytes,

            # Tree-sitter configuration
            "use_tree_sitter": self.use_tree_sitter,
            "tree_sitter_languages": self.tree_sitter_languages,
            "tree_sitter_max_file_size_bytes": self.tree_sitter_max_file_size_bytes,
            "tree_sitter_min_block_chars": self.tree_sitter_min_block_chars,
            "tree_sitter_max_blocks_per_file": self.tree_sitter_max_blocks_per_file,
            "tree_sitter_max_functions_per_file": self.tree_sitter_max_functions_per_file,
            "tree_sitter_max_classes_per_file": self.tree_sitter_max_classes_per_file,
            "tree_sitter_max_impl_blocks_per_file": self.tree_sitter_max_impl_blocks_per_file,
            "tree_sitter_skip_test_files": self.tree_sitter_skip_test_files,
            "tree_sitter_skip_examples": self.tree_sitter_skip_examples,
            "tree_sitter_skip_patterns": self.tree_sitter_skip_patterns,
            "tree_sitter_debug_logging": self.tree_sitter_debug_logging,
        }
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return (
            f"Config(ollama_base_url={self.ollama_base_url}, "
            f"ollama_model={self.ollama_model}, "
            f"qdrant_url={self.qdrant_url}, "
            f"workspace_path={self.workspace_path}, "
            f"extensions_count={len(self.extensions)}, "
            f"embedding_length={self.embedding_length}, "
            f"chunking_strategy={self.chunking_strategy})"
        )
