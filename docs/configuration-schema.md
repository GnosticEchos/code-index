# Configuration Schema

## Overview

The Code Index configuration system is organized into eight domain-specific sections, each backed by a dataclass. Configuration can be specified through JSON configuration files, environment variables, or CLI arguments. The system supports both nested (section-based) and flattened attribute access patterns.

## Configuration Sections

---

### core

Core system configuration for workspace paths, embedding services, and connection settings.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `workspace_path` | string | `"."` | No | Path to the workspace directory to index |
| `ollama_base_url` | string | `"http://localhost:11434"` | No | Base URL for the Ollama embedding service |
| `ollama_model` | string | `"nomic-embed-text:latest"` | No | Ollama model name for generating embeddings |
| `qdrant_url` | string | `"http://localhost:6333"` | No | URL for the Qdrant vector database |
| `qdrant_api_key` | string | `null` | No | API key for Qdrant authentication (if required) |
| `embedding_length` | integer | Auto-detected | No | Dimension of embedding vectors (auto-set based on model) |
| `embed_timeout_seconds` | integer | `60` | No | Timeout for embedding requests in seconds |

**Environment Variables:**
- `WORKSPACE_PATH` - Overrides `workspace_path`
- `OLLAMA_BASE_URL` - Overrides `ollama_base_url`
- `OLLAMA_MODEL` - Overrides `ollama_model`
- `QDRANT_URL` - Overrides `qdrant_url`
- `QDRANT_API_KEY` - Overrides `qdrant_api_key`
- `CODE_INDEX_EMBED_TIMEOUT` - Overrides `embed_timeout_seconds`

**Validation Rules:**
- `embed_timeout_seconds`: Minimum 1, maximum 3600
- `embedding_length`: Auto-populated based on model name if not set

**Example:**
```json
{
  "core": {
    "workspace_path": "/home/user/projects/my-app",
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "nomic-embed-text:latest",
    "qdrant_url": "http://localhost:6333",
    "qdrant_api_key": null,
    "embed_timeout_seconds": 60
  }
}
```

---

### files

File handling configuration for extensions, size limits, and processing behavior.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `extensions` | array[string] | See below | No | List of file extensions to index |
| `max_file_size_bytes` | integer | `1048576` (1 MB) | No | Maximum file size to process in bytes |
| `batch_segment_threshold` | integer | `60` | No | Threshold for segmenting batches |
| `exclude_files_path` | string | `null` | No | Path to file containing exclusion patterns |
| `timeout_log_path` | string | `"timeout_files.txt"` | No | Path to log file for timeout tracking |
| `skip_dot_files` | boolean | `true` | No | Skip files starting with a dot |
| `read_root_gitignore_only` | boolean | `true` | No | Only read gitignore from workspace root |

**Default Extensions:**
```json
[
  ".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx",
  ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php",
  ".swift", ".kt", ".scala", ".dart", ".lua", ".pl", ".pm",
  ".t", ".r", ".sql", ".html", ".css", ".scss", ".sass", ".less",
  ".md", ".markdown", ".rst", ".txt", ".json", ".xml", ".yaml", ".yml"
]
```

**Validation Rules:**
- `max_file_size_bytes`: Minimum 1024, maximum 104857600 (100 MB)
- `batch_segment_threshold`: Minimum 1, maximum 1000

**Example:**
```json
{
  "files": {
    "extensions": [".py", ".js", ".ts"],
    "max_file_size_bytes": 2097152,
    "batch_segment_threshold": 60,
    "exclude_files_path": "/path/to/exclusions.txt",
    "timeout_log_path": "timeout_files.txt",
    "skip_dot_files": true,
    "read_root_gitignore_only": true
  }
}
```

---

### ignore

Configuration for ignore patterns and automatic detection behavior.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `ignore_config_path` | string | `null` | No | Path to ignore configuration file |
| `ignore_override_pattern` | string | `null` | No | Single pattern to override ignores (legacy) |
| `ignore_override_patterns` | array[string] | `[]` | No | List of patterns to override ignores |
| `auto_ignore_detection` | boolean | `true` | No | Automatically detect ignore patterns |
| `apply_github_templates` | boolean | `true` | No | Apply GitHub gitignore templates |
| `apply_project_gitignore` | boolean | `true` | No | Apply project .gitignore files |
| `apply_global_ignores` | boolean | `true` | No | Apply global gitignore settings |
| `learn_from_indexing` | boolean | `false` | No | Learn new ignore patterns from indexing |

**Validation Rules:**
- `ignore_override_patterns`: Accepts comma-separated strings, arrays, or nested arrays

**Example:**
```json
{
  "ignore": {
    "ignore_config_path": null,
    "ignore_override_patterns": ["!important.log", "!*.test.ts"],
    "auto_ignore_detection": true,
    "apply_github_templates": true,
    "apply_project_gitignore": true,
    "apply_global_ignores": true,
    "learn_from_indexing": false
  }
}
```

---

### chunking

Configuration for text chunking strategies and size limits.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `chunking_strategy` | string | `"lines"` | No | Strategy for chunking text (`lines`, `tokens`, `treesitter`) |
| `token_chunk_size` | integer | `1000` | No | Number of tokens per chunk |
| `token_chunk_overlap` | integer | `200` | No | Number of overlapping tokens between chunks |
| `auto_extensions` | boolean | `false` | No | Automatically detect extensions for chunking |
| `language_chunk_sizes` | object | See below | No | Per-language chunk sizes in bytes |

**Enum Values:**
- `chunking_strategy`: `"lines"`, `"tokens"`, `"treesitter"`

**Default Language Chunk Sizes:**
```json
{
  "python": 65536,
  "javascript": 131072,
  "typescript": 131072,
  "java": 262144,
  "cpp": 262144,
  "rust": 131072,
  "go": 131072,
  "text": 32768,
  "markdown": 32768,
  "json": 65536,
  "xml": 131072,
  "yaml": 32768
}
```

**Validation Rules:**
- `token_chunk_size`: Minimum 100, maximum 10000
- `token_chunk_overlap`: Minimum 0, maximum 50% of `token_chunk_size`
- `language_chunk_sizes`: Values must be between 1024 and 1048576

**Example:**
```json
{
  "chunking": {
    "chunking_strategy": "lines",
    "token_chunk_size": 1000,
    "token_chunk_overlap": 200,
    "auto_extensions": false,
    "language_chunk_sizes": {
      "python": 65536,
      "javascript": 131072
    }
  }
}
```

---

### tree_sitter

Configuration for Tree-sitter parsing and semantic code extraction.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `use_tree_sitter` | boolean | `false` | No | Enable Tree-sitter parsing |
| `tree_sitter_languages` | array[string] | `null` | No | Specific languages to enable (null = all) |
| `tree_sitter_max_file_size_bytes` | integer | `524288` (512 KB) | No | Maximum file size for Tree-sitter parsing |
| `tree_sitter_min_block_chars_default` | integer | `30` | No | Default minimum characters per code block |
| `tree_sitter_min_block_chars` | integer | `null` | No | Override minimum block characters |
| `tree_sitter_min_block_chars_overrides` | object | `{}` | No | Per-language minimum block characters |
| `tree_sitter_max_blocks_per_file` | integer | `100` | No | Maximum blocks to extract per file |
| `tree_sitter_max_functions_per_file` | integer | `50` | No | Maximum functions per file |
| `tree_sitter_max_classes_per_file` | integer | `20` | No | Maximum classes per file |
| `tree_sitter_max_impl_blocks_per_file` | integer | `30` | No | Maximum implementation blocks per file |
| `tree_sitter_skip_test_files` | boolean | `true` | No | Skip test files during parsing |
| `tree_sitter_skip_examples` | boolean | `true` | No | Skip example files during parsing |
| `tree_sitter_skip_patterns` | array[string] | See below | No | Patterns to skip during parsing |
| `tree_sitter_debug_logging` | boolean | `false` | No | Enable debug logging for Tree-sitter |

**Environment Variables:**
- `TREE_SITTER_MIN_BLOCK_CHARS_DEFAULT` - Overrides `tree_sitter_min_block_chars_default`

**Default Skip Patterns:**
```json
[
  "*.min.js", "*.bundle.js", "*.min.css",
  "package-lock.json", "yarn.lock", "*.lock",
  "target/", "build/", "dist/",
  "__pycache__/", "node_modules/",
  "*.log", "*.tmp", "*.temp"
]
```

**Validation Rules:**
- `tree_sitter_max_file_size_bytes`: Minimum 1024, maximum 10485760 (10 MB)
- `tree_sitter_max_blocks_per_file`: Minimum 1, maximum 1000
- `tree_sitter_max_functions_per_file`: Minimum 1, maximum 500
- `tree_sitter_max_classes_per_file`: Minimum 1, maximum 200
- `tree_sitter_max_impl_blocks_per_file`: Minimum 1, maximum 300
- `tree_sitter_min_block_chars_default`: Minimum 10, maximum 1000

**Example:**
```json
{
  "tree_sitter": {
    "use_tree_sitter": true,
    "tree_sitter_languages": ["python", "typescript", "rust"],
    "tree_sitter_max_file_size_bytes": 524288,
    "tree_sitter_min_block_chars_default": 30,
    "tree_sitter_max_blocks_per_file": 100,
    "tree_sitter_skip_test_files": true,
    "tree_sitter_skip_examples": true,
    "tree_sitter_debug_logging": false
  }
}
```

---

### search

Configuration for search behavior, scoring, and result limits.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `search_min_score` | number | `0.4` | No | Minimum similarity score for results (0-1) |
| `search_max_results` | integer | `50` | No | Maximum number of search results |
| `search_file_type_weights` | object | See below | No | Per-file-type scoring weights |
| `search_path_boosts` | array[object] | See below | No | Path-based score boosts |
| `search_language_boosts` | object | See below | No | Language-based score boosts |
| `search_exclude_patterns` | array[string] | `[]` | No | Patterns to exclude from search |
| `search_snippet_preview_chars` | integer | `500` | No | Characters to show in result snippets |
| `search_cache_enabled` | boolean | `false` | No | Enable search result caching |
| `search_cache_max_entries` | integer | `128` | No | Maximum cached search results |
| `search_cache_ttl_seconds` | integer | `null` | No | Cache TTL in seconds (null = no expiry) |

**Default File Type Weights:**
```json
{
  ".vue": 1.30,
  ".ts": 1.25,
  ".tsx": 1.25,
  ".rs": 1.20,
  ".surql": 1.25,
  ".js": 1.10,
  ".md": 0.80,
  ".txt": 0.60
}
```

**Default Path Boosts:**
```json
[
  {"pattern": "src/", "weight": 1.25},
  {"pattern": "components/", "weight": 1.25},
  {"pattern": "views/", "weight": 1.15},
  {"pattern": "docs/", "weight": 0.85},
  {"pattern": "console-export", "weight": 0.60},
  {"pattern": "Daisy_llms.txt", "weight": 0.60}
]
```

**Default Language Boosts:**
```json
{
  "typescript": 1.15,
  "rust": 1.10
}
```

**Validation Rules:**
- `search_min_score`: Minimum 0.0, maximum 1.0
- `search_max_results`: Minimum 1, maximum 1000
- `search_snippet_preview_chars`: Minimum 50, maximum 1000
- `search_cache_max_entries`: Minimum 1, maximum 10000

**Example:**
```json
{
  "search": {
    "search_min_score": 0.4,
    "search_max_results": 50,
    "search_file_type_weights": {
      ".py": 1.20,
      ".js": 1.10
    },
    "search_cache_enabled": false
  }
}
```

---

### performance

Performance tuning configuration for memory, parsing, and processing.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `use_mmap_file_reading` | boolean | `false` | No | Use memory-mapped file reading |
| `mmap_min_file_size_bytes` | integer | `65536` (64 KB) | No | Minimum file size for mmap |
| `enable_chunked_processing` | boolean | `true` | No | Enable chunked file processing |
| `large_file_threshold_bytes` | integer | `262144` (256 KB) | No | Threshold for large file handling |
| `streaming_threshold_bytes` | integer | `1048576` (1 MB) | No | Threshold for streaming processing |
| `default_chunk_size_bytes` | integer | `65536` (64 KB) | No | Default chunk size for processing |
| `max_chunk_size_bytes` | integer | `524288` (512 KB) | No | Maximum chunk size |
| `memory_optimization_threshold_mb` | integer | `100` | No | Memory threshold for optimization |
| `enable_progressive_indexing` | boolean | `true` | No | Enable progressive indexing |
| `chunk_size_optimization` | boolean | `true` | No | Optimize chunk sizes dynamically |
| `enable_fallback_parsers` | boolean | `true` | No | Enable fallback parsers |
| `fallback_parser_patterns` | object | See below | No | Patterns for fallback parser selection |
| `enable_hybrid_parsing` | boolean | `true` | No | Enable hybrid parsing mode |
| `parser_performance_monitoring` | boolean | `true` | No | Monitor parser performance |
| `max_parser_memory_mb` | integer | `50` | No | Maximum parser memory usage |
| `parser_timeout_seconds` | integer | `30` | No | Parser timeout in seconds |
| `enable_parser_caching` | boolean | `true` | No | Enable parser caching |
| `parser_cache_size` | integer | `50` | No | Maximum cached parsers |
| `enable_performance_monitoring` | boolean | `true` | No | Enable performance monitoring |
| `performance_stats_interval` | integer | `100` | No | Interval for stats reporting |
| `enable_memory_profiling` | boolean | `false` | No | Enable memory profiling |
| `memory_profiling_threshold_mb` | integer | `500` | No | Memory threshold for profiling |

**Default Fallback Parser Patterns:**
```json
{
  "text": ["*.txt", "*.log", "*.md", "*.rst"],
  "config": ["*.ini", "*.cfg", "*.conf", "*.properties"],
  "data": ["*.csv", "*.tsv", "*.json", "*.xml", "*.yaml"],
  "documentation": ["*.md", "*.rst", "*.txt"],
  "plain_text": ["*.txt", "*.log", "*.out", "*.err"]
}
```

**Validation Rules:**
- `mmap_min_file_size_bytes`: Minimum 4096, maximum 1048576
- `large_file_threshold_bytes`: Minimum 10240, maximum 10485760
- `streaming_threshold_bytes`: Minimum 65536, maximum 104857600
- `default_chunk_size_bytes`: Minimum 4096, maximum 1048576
- `max_chunk_size_bytes`: Minimum 16384, maximum 2097152
- `memory_optimization_threshold_mb`: Minimum 10, maximum 1000
- `max_parser_memory_mb`: Minimum 10, maximum 500
- `parser_timeout_seconds`: Minimum 1, maximum 300
- `parser_cache_size`: Minimum 1, maximum 200
- `performance_stats_interval`: Minimum 1, maximum 10000
- `memory_profiling_threshold_mb`: Minimum 50, maximum 2000

**Example:**
```json
{
  "performance": {
    "use_mmap_file_reading": false,
    "enable_chunked_processing": true,
    "large_file_threshold_bytes": 262144,
    "streaming_threshold_bytes": 1048576,
    "enable_progressive_indexing": true,
    "chunk_size_optimization": true,
    "enable_fallback_parsers": true,
    "enable_hybrid_parsing": true,
    "parser_performance_monitoring": true,
    "enable_performance_monitoring": true
  }
}
```

---

### logging

Logging configuration for component-level log control.

| Option | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| `component_levels` | object | `{}` | No | Log levels per component |

**Component Level Structure:**
```json
{
  "component_name": "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
}
```

**Example:**
```json
{
  "logging": {
    "component_levels": {
      "indexing": "DEBUG",
      "search": "INFO",
      "parser": "WARNING",
      "embedder": "ERROR"
    }
  }
}
```

---

## Configuration Examples

### Minimal Configuration

The bare minimum configuration for getting started:

```json
{
  "core": {
    "workspace_path": "."
  }
}
```

### Development Configuration

Optimized for development with debugging enabled:

```json
{
  "core": {
    "workspace_path": ".",
    "ollama_model": "nomic-embed-text:latest",
    "embed_timeout_seconds": 120
  },
  "files": {
    "extensions": [".py", ".js", ".ts", ".jsx", ".tsx"],
    "skip_dot_files": true
  },
  "tree_sitter": {
    "use_tree_sitter": true,
    "tree_sitter_debug_logging": true,
    "tree_sitter_skip_test_files": false
  },
  "search": {
    "search_min_score": 0.3,
    "search_max_results": 100,
    "search_cache_enabled": true
  },
  "performance": {
    "enable_performance_monitoring": true,
    "enable_memory_profiling": true
  },
  "logging": {
    "component_levels": {
      "indexing": "DEBUG",
      "parser": "DEBUG"
    }
  }
}
```

### Production Configuration

Optimized for production performance:

```json
{
  "core": {
    "workspace_path": "/app/src",
    "ollama_base_url": "http://ollama:11434",
    "qdrant_url": "http://qdrant:6333",
    "embed_timeout_seconds": 30
  },
  "files": {
    "max_file_size_bytes": 2097152,
    "batch_segment_threshold": 100,
    "skip_dot_files": true
  },
  "ignore": {
    "auto_ignore_detection": true,
    "learn_from_indexing": true
  },
  "chunking": {
    "chunking_strategy": "treesitter",
    "token_chunk_size": 1500,
    "auto_extensions": true
  },
  "tree_sitter": {
    "use_tree_sitter": true,
    "tree_sitter_max_file_size_bytes": 1048576,
    "tree_sitter_max_blocks_per_file": 200,
    "tree_sitter_skip_test_files": true,
    "tree_sitter_debug_logging": false
  },
  "search": {
    "search_min_score": 0.5,
    "search_max_results": 25,
    "search_cache_enabled": true,
    "search_cache_ttl_seconds": 3600
  },
  "performance": {
    "use_mmap_file_reading": true,
    "enable_chunked_processing": true,
    "enable_progressive_indexing": true,
    "chunk_size_optimization": true,
    "enable_hybrid_parsing": true,
    "parser_performance_monitoring": true,
    "enable_parser_caching": true,
    "enable_performance_monitoring": true,
    "enable_memory_profiling": false
  }
}
```

### Full Configuration

Complete configuration with all options specified:

```json
{
  "core": {
    "workspace_path": ".",
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "nomic-embed-text:latest",
    "qdrant_url": "http://localhost:6333",
    "qdrant_api_key": null,
    "embedding_length": 768,
    "embed_timeout_seconds": 60
  },
  "files": {
    "extensions": [
      ".rs", ".ts", ".vue", ".js", ".py", ".jsx", ".tsx",
      ".go", ".java", ".cpp", ".c", ".h", ".md"
    ],
    "max_file_size_bytes": 1048576,
    "batch_segment_threshold": 60,
    "exclude_files_path": null,
    "timeout_log_path": "timeout_files.txt",
    "skip_dot_files": true,
    "read_root_gitignore_only": true
  },
  "ignore": {
    "ignore_config_path": null,
    "ignore_override_pattern": null,
    "ignore_override_patterns": [],
    "auto_ignore_detection": true,
    "apply_github_templates": true,
    "apply_project_gitignore": true,
    "apply_global_ignores": true,
    "learn_from_indexing": false
  },
  "chunking": {
    "chunking_strategy": "lines",
    "token_chunk_size": 1000,
    "token_chunk_overlap": 200,
    "auto_extensions": false,
    "language_chunk_sizes": {
      "python": 65536,
      "javascript": 131072,
      "typescript": 131072
    }
  },
  "tree_sitter": {
    "use_tree_sitter": false,
    "tree_sitter_languages": null,
    "tree_sitter_max_file_size_bytes": 524288,
    "tree_sitter_min_block_chars_default": 30,
    "tree_sitter_min_block_chars": null,
    "tree_sitter_min_block_chars_overrides": {},
    "tree_sitter_max_blocks_per_file": 100,
    "tree_sitter_max_functions_per_file": 50,
    "tree_sitter_max_classes_per_file": 20,
    "tree_sitter_max_impl_blocks_per_file": 30,
    "tree_sitter_skip_test_files": true,
    "tree_sitter_skip_examples": true,
    "tree_sitter_skip_patterns": [
      "*.min.js", "node_modules/", "__pycache__/"
    ],
    "tree_sitter_debug_logging": false
  },
  "search": {
    "search_min_score": 0.4,
    "search_max_results": 50,
    "search_file_type_weights": {
      ".ts": 1.25,
      ".rs": 1.20,
      ".js": 1.10
    },
    "search_path_boosts": [
      {"pattern": "src/", "weight": 1.25},
      {"pattern": "components/", "weight": 1.25}
    ],
    "search_language_boosts": {
      "typescript": 1.15,
      "rust": 1.10
    },
    "search_exclude_patterns": [],
    "search_snippet_preview_chars": 500,
    "search_cache_enabled": false,
    "search_cache_max_entries": 128,
    "search_cache_ttl_seconds": null
  },
  "performance": {
    "use_mmap_file_reading": false,
    "mmap_min_file_size_bytes": 65536,
    "enable_chunked_processing": true,
    "large_file_threshold_bytes": 262144,
    "streaming_threshold_bytes": 1048576,
    "default_chunk_size_bytes": 65536,
    "max_chunk_size_bytes": 524288,
    "memory_optimization_threshold_mb": 100,
    "enable_progressive_indexing": true,
    "chunk_size_optimization": true,
    "enable_fallback_parsers": true,
    "fallback_parser_patterns": {
      "text": ["*.txt", "*.log", "*.md"],
      "config": ["*.ini", "*.cfg", "*.conf"]
    },
    "enable_hybrid_parsing": true,
    "parser_performance_monitoring": true,
    "max_parser_memory_mb": 50,
    "parser_timeout_seconds": 30,
    "enable_parser_caching": true,
    "parser_cache_size": 50,
    "enable_performance_monitoring": true,
    "performance_stats_interval": 100,
    "enable_memory_profiling": false,
    "memory_profiling_threshold_mb": 500
  },
  "logging": {
    "component_levels": {
      "indexing": "INFO",
      "search": "INFO",
      "parser": "WARNING"
    }
  }
}
```

---

## JSON Schema

For validation purposes, here is the complete JSON Schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Code Index Configuration",
  "description": "Configuration schema for the Code Index tool",
  "properties": {
    "core": {
      "type": "object",
      "properties": {
        "workspace_path": {"type": "string", "default": "."},
        "ollama_base_url": {"type": "string", "format": "uri", "default": "http://localhost:11434"},
        "ollama_model": {"type": "string", "default": "nomic-embed-text:latest"},
        "qdrant_url": {"type": "string", "format": "uri", "default": "http://localhost:6333"},
        "qdrant_api_key": {"type": ["string", "null"], "default": null},
        "embedding_length": {"type": ["integer", "null"], "default": null},
        "embed_timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 3600, "default": 60}
      }
    },
    "files": {
      "type": "object",
      "properties": {
        "extensions": {"type": "array", "items": {"type": "string"}},
        "max_file_size_bytes": {"type": "integer", "minimum": 1024, "maximum": 104857600, "default": 1048576},
        "batch_segment_threshold": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 60},
        "exclude_files_path": {"type": ["string", "null"], "default": null},
        "timeout_log_path": {"type": "string", "default": "timeout_files.txt"},
        "skip_dot_files": {"type": "boolean", "default": true},
        "read_root_gitignore_only": {"type": "boolean", "default": true}
      }
    },
    "ignore": {
      "type": "object",
      "properties": {
        "ignore_config_path": {"type": ["string", "null"], "default": null},
        "ignore_override_pattern": {"type": ["string", "null"], "default": null},
        "ignore_override_patterns": {"type": "array", "items": {"type": "string"}, "default": []},
        "auto_ignore_detection": {"type": "boolean", "default": true},
        "apply_github_templates": {"type": "boolean", "default": true},
        "apply_project_gitignore": {"type": "boolean", "default": true},
        "apply_global_ignores": {"type": "boolean", "default": true},
        "learn_from_indexing": {"type": "boolean", "default": false}
      }
    },
    "chunking": {
      "type": "object",
      "properties": {
        "chunking_strategy": {"type": "string", "enum": ["lines", "tokens", "treesitter"], "default": "lines"},
        "token_chunk_size": {"type": "integer", "minimum": 100, "maximum": 10000, "default": 1000},
        "token_chunk_overlap": {"type": "integer", "minimum": 0, "default": 200},
        "auto_extensions": {"type": "boolean", "default": false},
        "language_chunk_sizes": {"type": "object", "additionalProperties": {"type": "integer"}}
      }
    },
    "tree_sitter": {
      "type": "object",
      "properties": {
        "use_tree_sitter": {"type": "boolean", "default": false},
        "tree_sitter_languages": {"type": ["array", "null"], "items": {"type": "string"}},
        "tree_sitter_max_file_size_bytes": {"type": "integer", "minimum": 1024, "maximum": 10485760, "default": 524288},
        "tree_sitter_min_block_chars_default": {"type": "integer", "minimum": 10, "maximum": 1000, "default": 30},
        "tree_sitter_min_block_chars": {"type": ["integer", "null"]},
        "tree_sitter_min_block_chars_overrides": {"type": "object", "additionalProperties": {"type": "integer"}},
        "tree_sitter_max_blocks_per_file": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
        "tree_sitter_max_functions_per_file": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50},
        "tree_sitter_max_classes_per_file": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
        "tree_sitter_max_impl_blocks_per_file": {"type": "integer", "minimum": 1, "maximum": 300, "default": 30},
        "tree_sitter_skip_test_files": {"type": "boolean", "default": true},
        "tree_sitter_skip_examples": {"type": "boolean", "default": true},
        "tree_sitter_skip_patterns": {"type": "array", "items": {"type": "string"}},
        "tree_sitter_debug_logging": {"type": "boolean", "default": false}
      }
    },
    "search": {
      "type": "object",
      "properties": {
        "search_min_score": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.4},
        "search_max_results": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 50},
        "search_file_type_weights": {"type": "object", "additionalProperties": {"type": "number"}},
        "search_path_boosts": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "pattern": {"type": "string"},
              "weight": {"type": "number"}
            },
            "required": ["pattern", "weight"]
          }
        },
        "search_language_boosts": {"type": "object", "additionalProperties": {"type": "number"}},
        "search_exclude_patterns": {"type": "array", "items": {"type": "string"}, "default": []},
        "search_snippet_preview_chars": {"type": "integer", "minimum": 50, "maximum": 1000, "default": 500},
        "search_cache_enabled": {"type": "boolean", "default": false},
        "search_cache_max_entries": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 128},
        "search_cache_ttl_seconds": {"type": ["integer", "null"]}
      }
    },
    "performance": {
      "type": "object",
      "properties": {
        "use_mmap_file_reading": {"type": "boolean", "default": false},
        "mmap_min_file_size_bytes": {"type": "integer", "minimum": 4096, "maximum": 1048576, "default": 65536},
        "enable_chunked_processing": {"type": "boolean", "default": true},
        "large_file_threshold_bytes": {"type": "integer", "minimum": 10240, "maximum": 10485760, "default": 262144},
        "streaming_threshold_bytes": {"type": "integer", "minimum": 65536, "maximum": 104857600, "default": 1048576},
        "default_chunk_size_bytes": {"type": "integer", "minimum": 4096, "maximum": 1048576, "default": 65536},
        "max_chunk_size_bytes": {"type": "integer", "minimum": 16384, "maximum": 2097152, "default": 524288},
        "memory_optimization_threshold_mb": {"type": "integer", "minimum": 10, "maximum": 1000, "default": 100},
        "enable_progressive_indexing": {"type": "boolean", "default": true},
        "chunk_size_optimization": {"type": "boolean", "default": true},
        "enable_fallback_parsers": {"type": "boolean", "default": true},
        "fallback_parser_patterns": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
        "enable_hybrid_parsing": {"type": "boolean", "default": true},
        "parser_performance_monitoring": {"type": "boolean", "default": true},
        "max_parser_memory_mb": {"type": "integer", "minimum": 10, "maximum": 500, "default": 50},
        "parser_timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300, "default": 30},
        "enable_parser_caching": {"type": "boolean", "default": true},
        "parser_cache_size": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
        "enable_performance_monitoring": {"type": "boolean", "default": true},
        "performance_stats_interval": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 100},
        "enable_memory_profiling": {"type": "boolean", "default": false},
        "memory_profiling_threshold_mb": {"type": "integer", "minimum": 50, "maximum": 2000, "default": 500}
      }
    },
    "logging": {
      "type": "object",
      "properties": {
        "component_levels": {"type": "object", "additionalProperties": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}, "default": {}}
      }
    }
  }
}
```

---

## Configuration Loading Order

Configuration values are resolved in the following priority order (highest to lowest):

1. **CLI Arguments** - Direct command-line overrides
2. **Environment Variables** - Variables like `WORKSPACE_PATH`, `OLLAMA_MODEL`
3. **Workspace Configuration** - `code_index.json` in the workspace root
4. **Default Values** - Built-in defaults defined in `src/code_index/config.py`

---

## Related Documentation

- [Configuration Overview](./configuration.md) - General configuration guide
- [Architecture Summary](./ARCHITECTURE_SUMMARY.md) - System architecture overview
