# Configuration Examples and Templates

This document provides comprehensive configuration examples and optimization templates for different use cases, project types, and performance requirements.

## Table of Contents

- [Quick Start Configurations](#quick-start-configurations)
- [Use Case Templates](#use-case-templates)
- [Language-Specific Configurations](#language-specific-configurations)
- [Performance Optimization Templates](#performance-optimization-templates)
- [Migration Guide](#migration-guide)
- [Benchmarking Examples](#benchmarking-examples)

## Quick Start Configurations

### Minimal Configuration

The absolute minimum configuration required to get started:

```json
{
  "embedding_length": 768
}
```

**Use case**: First-time setup with default Ollama and Qdrant services.

### Basic Configuration

A complete basic configuration with common settings:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "qdrant_api_key": null,
  "workspace_path": ".",
  "extensions": [".py", ".js", ".ts", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".md", ".json", ".yaml"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,
  "embed_timeout_seconds": 60,
  "chunking_strategy": "lines"
}
```

**Use case**: General-purpose development with balanced performance and accuracy.

### Comprehensive Configuration

A full configuration with all available options:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "qdrant_api_key": null,
  "workspace_path": ".",
  
  "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".dart", ".lua", ".r", ".sql", ".md", ".json", ".yaml", ".yml"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": true,
  "exclude_files_path": "ignore_files.txt",
  
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "token_chunk_size": 1000,
  "token_chunk_overlap": 200,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 100,
  "tree_sitter_skip_test_files": true,
  
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 120,
  "timeout_log_path": "timeout_files.txt",
  
  "search_min_score": 0.4,
  "search_max_results": 50,
  "search_snippet_preview_chars": 160,
  "search_file_type_weights": {
    ".ts": 1.30,
    ".tsx": 1.25,
    ".js": 1.20,
    ".jsx": 1.20,
    ".py": 1.15,
    ".rs": 1.10,
    ".go": 1.05,
    ".java": 1.05,
    ".cpp": 1.00,
    ".c": 1.00,
    ".md": 0.80,
    ".json": 0.70,
    ".yaml": 0.70,
    ".test.js": 0.30,
    ".spec.ts": 0.30
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.30},
    {"pattern": "lib/", "boost": 1.25},
    {"pattern": "core/", "boost": 1.35},
    {"pattern": "utils/", "boost": 1.15},
    {"pattern": "components/", "boost": 1.20},
    {"pattern": "services/", "boost": 1.25},
    {"pattern": "api/", "boost": 1.30},
    {"pattern": "docs/", "boost": 0.85},
    {"pattern": "test/", "boost": 0.40},
    {"pattern": "tests/", "boost": 0.40},
    {"pattern": "spec/", "boost": 0.35},
    {"pattern": "examples/", "boost": 0.60},
    {"pattern": "node_modules/", "boost": 0.10},
    {"pattern": "vendor/", "boost": 0.10}
  ],
  "search_language_boosts": {
    "typescript": 1.25,
    "javascript": 1.20,
    "python": 1.20,
    "rust": 1.15,
    "go": 1.10,
    "java": 1.05,
    "markdown": 0.80
  },
  "search_exclude_patterns": [
    "node_modules",
    ".git",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt"
  ]
}
```

**Use case**: Production environments requiring maximum configurability and fine-tuning.

## Use Case Templates

### Fast Indexing (CI/CD Pipeline)

Optimized for speed in automated environments:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".py", ".js", ".ts", ".rs", ".go", ".java"],
  "max_file_size_bytes": 524288,
  "auto_extensions": false,
  "exclude_files_path": "ci_ignore.txt",
  
  "chunking_strategy": "lines",
  "use_tree_sitter": false,
  
  "batch_segment_threshold": 100,
  "embed_timeout_seconds": 30,
  
  "search_min_score": 0.5,
  "search_max_results": 30
}
```

**Performance**: ~500-1000 files/minute  
**Memory usage**: ~100-200MB  
**Use case**: CI/CD pipelines, quick prototyping, large repository initial scans

### Semantic Accuracy (Research/Analysis)

Optimized for maximum semantic understanding:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".md"],
  "max_file_size_bytes": 2097152,
  "auto_extensions": true,
  
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 1048576,
  "tree_sitter_max_blocks_per_file": 200,
  "tree_sitter_skip_test_files": false,
  
  "batch_segment_threshold": 30,
  "embed_timeout_seconds": 300,
  
  "search_min_score": 0.3,
  "search_max_results": 100,
  "search_snippet_preview_chars": 300
}
```

**Performance**: ~50-150 files/minute  
**Memory usage**: ~400-800MB  
**Use case**: Code analysis, research, documentation generation, semantic code search

### Large Repository (Memory Optimized)

Optimized for processing very large codebases:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".py", ".js", ".ts", ".rs", ".go", ".java", ".cpp", ".c", ".h"],
  "max_file_size_bytes": 262144,
  "auto_extensions": false,
  "exclude_files_path": "large_repo_ignore.txt",
  
  "chunking_strategy": "tokens",
  "token_chunk_size": 600,
  "token_chunk_overlap": 100,
  "tree_sitter_max_file_size_bytes": 131072,
  
  "batch_segment_threshold": 20,
  "embed_timeout_seconds": 180,
  
  "search_min_score": 0.5,
  "search_max_results": 50
}
```

**Performance**: ~200-400 files/minute  
**Memory usage**: ~200-400MB  
**Use case**: Repositories with >10,000 files, limited memory environments

### Development Environment (Balanced)

Balanced configuration for daily development work:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".md", ".json", ".yaml"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": true,
  
  "chunking_strategy": "tokens",
  "token_chunk_size": 800,
  "token_chunk_overlap": 160,
  "use_tree_sitter": false,
  
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 120,
  
  "search_min_score": 0.4,
  "search_max_results": 50,
  "search_file_type_weights": {
    ".ts": 1.4,
    ".js": 1.3,
    ".py": 1.3,
    ".rs": 1.2,
    ".md": 0.8,
    ".test.js": 0.3,
    ".spec.ts": 0.3
  }
}
```

**Performance**: ~200-400 files/minute  
**Memory usage**: ~200-400MB  
**Use case**: Daily development, code exploration, feature development

## Language-Specific Configurations

### Python Projects

Optimized for Python codebases with scientific/data science libraries:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".py", ".pyx", ".pyi", ".ipynb", ".md", ".rst", ".txt", ".yaml", ".yml", ".toml", ".cfg", ".ini"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": false,
  "exclude_files_path": "python_ignore.txt",
  
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 150,
  "tree_sitter_skip_test_files": true,
  
  "batch_segment_threshold": 50,
  "embed_timeout_seconds": 120,
  
  "search_min_score": 0.4,
  "search_max_results": 60,
  "search_file_type_weights": {
    ".py": 1.50,
    ".pyi": 1.30,
    ".pyx": 1.20,
    ".ipynb": 1.10,
    ".md": 0.80,
    ".rst": 0.85,
    ".test.py": 0.25,
    ".conftest.py": 0.40
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.40},
    {"pattern": "lib/", "boost": 1.30},
    {"pattern": "core/", "boost": 1.50},
    {"pattern": "utils/", "boost": 1.20},
    {"pattern": "models/", "boost": 1.35},
    {"pattern": "services/", "boost": 1.30},
    {"pattern": "api/", "boost": 1.25},
    {"pattern": "tests/", "boost": 0.30},
    {"pattern": "test/", "boost": 0.30},
    {"pattern": "docs/", "boost": 0.80},
    {"pattern": "examples/", "boost": 0.60},
    {"pattern": "__pycache__/", "boost": 0.05},
    {"pattern": ".pytest_cache/", "boost": 0.05}
  ],
  "search_language_boosts": {
    "python": 1.40
  }
}
```

**Companion ignore file** (`python_ignore.txt`):
```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.tox/
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.venv/
venv/
ENV/
env/
```

### JavaScript/TypeScript Projects

Optimized for modern JavaScript/TypeScript applications:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".md", ".json", ".yaml", ".yml"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": false,
  "exclude_files_path": "js_ignore.txt",
  
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 120,
  "tree_sitter_skip_test_files": true,
  
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 120,
  
  "search_min_score": 0.4,
  "search_max_results": 50,
  "search_file_type_weights": {
    ".ts": 1.60,
    ".tsx": 1.55,
    ".js": 1.30,
    ".jsx": 1.35,
    ".vue": 1.40,
    ".svelte": 1.30,
    ".mjs": 1.20,
    ".cjs": 1.15,
    ".json": 0.70,
    ".md": 0.80,
    ".test.js": 0.20,
    ".test.ts": 0.20,
    ".spec.js": 0.20,
    ".spec.ts": 0.20,
    ".stories.js": 0.30,
    ".stories.ts": 0.30
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.50},
    {"pattern": "lib/", "boost": 1.30},
    {"pattern": "components/", "boost": 1.45},
    {"pattern": "pages/", "boost": 1.35},
    {"pattern": "utils/", "boost": 1.25},
    {"pattern": "services/", "boost": 1.30},
    {"pattern": "api/", "boost": 1.40},
    {"pattern": "hooks/", "boost": 1.25},
    {"pattern": "store/", "boost": 1.30},
    {"pattern": "types/", "boost": 1.20},
    {"pattern": "test/", "boost": 0.25},
    {"pattern": "tests/", "boost": 0.25},
    {"pattern": "__tests__/", "boost": 0.25},
    {"pattern": "stories/", "boost": 0.35},
    {"pattern": "docs/", "boost": 0.80},
    {"pattern": "node_modules/", "boost": 0.05},
    {"pattern": "dist/", "boost": 0.05},
    {"pattern": "build/", "boost": 0.05}
  ],
  "search_language_boosts": {
    "typescript": 1.50,
    "javascript": 1.30,
    "vue": 1.40
  }
}
```

**Companion ignore file** (`js_ignore.txt`):
```
node_modules/
dist/
build/
.next/
.nuxt/
.output/
.vercel/
.netlify/
coverage/
.nyc_output/
.cache/
.parcel-cache/
.vite/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.DS_Store
Thumbs.db
```

### Rust Projects

Optimized for Rust codebases:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".rs", ".toml", ".md", ".txt", ".yaml", ".yml"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": false,
  "exclude_files_path": "rust_ignore.txt",
  
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 150,
  "tree_sitter_skip_test_files": true,
  
  "batch_segment_threshold": 50,
  "embed_timeout_seconds": 120,
  
  "search_min_score": 0.4,
  "search_max_results": 50,
  "search_file_type_weights": {
    ".rs": 1.60,
    "Cargo.toml": 1.30,
    ".toml": 0.90,
    ".md": 0.80,
    "lib.rs": 1.70,
    "main.rs": 1.65,
    "mod.rs": 1.50
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.60},
    {"pattern": "lib/", "boost": 1.40},
    {"pattern": "core/", "boost": 1.50},
    {"pattern": "utils/", "boost": 1.25},
    {"pattern": "modules/", "boost": 1.35},
    {"pattern": "services/", "boost": 1.30},
    {"pattern": "api/", "boost": 1.35},
    {"pattern": "tests/", "boost": 0.40},
    {"pattern": "benches/", "boost": 0.30},
    {"pattern": "examples/", "boost": 0.60},
    {"pattern": "docs/", "boost": 0.80},
    {"pattern": "target/", "boost": 0.05}
  ],
  "search_language_boosts": {
    "rust": 1.50
  }
}
```

**Companion ignore file** (`rust_ignore.txt`):
```
target/
Cargo.lock
*.pdb
*.exe
*.dll
*.so
*.dylib
.cargo/
```

### Go Projects

Optimized for Go codebases:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "extensions": [".go", ".mod", ".sum", ".md", ".yaml", ".yml", ".json"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": false,
  "exclude_files_path": "go_ignore.txt",
  
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 120,
  "tree_sitter_skip_test_files": true,
  
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 120,
  
  "search_min_score": 0.4,
  "search_max_results": 50,
  "search_file_type_weights": {
    ".go": 1.50,
    "go.mod": 1.20,
    "go.sum": 0.60,
    ".md": 0.80,
    "_test.go": 0.30,
    "main.go": 1.60
  },
  "search_path_boosts": [
    {"pattern": "cmd/", "boost": 1.40},
    {"pattern": "pkg/", "boost": 1.35},
    {"pattern": "internal/", "boost": 1.45},
    {"pattern": "api/", "boost": 1.35},
    {"pattern": "service/", "boost": 1.30},
    {"pattern": "handler/", "boost": 1.25},
    {"pattern": "model/", "boost": 1.30},
    {"pattern": "util/", "boost": 1.20},
    {"pattern": "test/", "boost": 0.35},
    {"pattern": "testdata/", "boost": 0.25},
    {"pattern": "vendor/", "boost": 0.10},
    {"pattern": "docs/", "boost": 0.80}
  ],
  "search_language_boosts": {
    "go": 1.40
  }
}
```

**Companion ignore file** (`go_ignore.txt`):
```
vendor/
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test
*.out
go.work
go.work.sum
```

## Performance Optimization Templates

### High-Speed Template (CI/CD)

Maximum speed for automated environments:

```json
{
  "embedding_length": 768,
  "extensions": [".py", ".js", ".ts", ".rs", ".go"],
  "max_file_size_bytes": 262144,
  "auto_extensions": false,
  "chunking_strategy": "lines",
  "use_tree_sitter": false,
  "batch_segment_threshold": 150,
  "embed_timeout_seconds": 20,
  "search_min_score": 0.6,
  "search_max_results": 25
}
```

**Expected performance**: 800-1200 files/minute  
**Memory usage**: 50-150MB

### Memory-Constrained Template

For environments with limited RAM (<2GB available):

```json
{
  "embedding_length": 768,
  "extensions": [".py", ".js", ".ts", ".rs"],
  "max_file_size_bytes": 131072,
  "auto_extensions": false,
  "chunking_strategy": "lines",
  "use_tree_sitter": false,
  "batch_segment_threshold": 15,
  "embed_timeout_seconds": 60,
  "search_min_score": 0.5,
  "search_max_results": 30
}
```

**Expected performance**: 200-400 files/minute  
**Memory usage**: 50-100MB

### High-Accuracy Template

Maximum semantic understanding:

```json
{
  "embedding_length": 768,
  "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".md"],
  "max_file_size_bytes": 2097152,
  "auto_extensions": true,
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 1048576,
  "tree_sitter_max_blocks_per_file": 300,
  "tree_sitter_skip_test_files": false,
  "batch_segment_threshold": 20,
  "embed_timeout_seconds": 600,
  "search_min_score": 0.25,
  "search_max_results": 150,
  "search_snippet_preview_chars": 400
}
```

**Expected performance**: 30-80 files/minute  
**Memory usage**: 500-1000MB

## Migration Guide

### From CLI to MCP Server

If you're currently using the CLI tool and want to migrate to the MCP server:

#### 1. Preserve Existing Configuration

Your existing `code_index.json` configuration file will work with the MCP server without changes.

#### 2. CLI to MCP Tool Mapping

| CLI Command | MCP Tool | Example |
|-------------|----------|---------|
| `code-index index --workspace /path` | `index(workspace="/path")` | Direct parameter mapping |
| `code-index search "query"` | `search(query="query")` | Direct parameter mapping |
| `code-index collections list` | `collections(subcommand="list")` | Subcommand parameter |

#### 3. Configuration Override Migration

CLI flags become MCP parameters:

```bash
# CLI
code-index index --workspace /path --embed-timeout 300 --use-tree-sitter

# MCP
index(
    workspace="/path",
    embed_timeout=300,
    use_tree_sitter=True
)
```

#### 4. Environment Variable Compatibility

All environment variables work the same way:

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export QDRANT_URL="http://localhost:6333"
export CODE_INDEX_EMBED_TIMEOUT="120"
```

### From Basic to Advanced Configuration

#### Step 1: Start with Basic

```json
{
  "embedding_length": 768,
  "chunking_strategy": "lines"
}
```

#### Step 2: Add File Filtering

```json
{
  "embedding_length": 768,
  "chunking_strategy": "lines",
  "extensions": [".py", ".js", ".ts", ".rs"],
  "max_file_size_bytes": 524288
}
```

#### Step 3: Optimize Performance

```json
{
  "embedding_length": 768,
  "chunking_strategy": "tokens",
  "token_chunk_size": 800,
  "token_chunk_overlap": 160,
  "extensions": [".py", ".js", ".ts", ".rs"],
  "max_file_size_bytes": 524288,
  "batch_segment_threshold": 40
}
```

#### Step 4: Add Search Optimization

```json
{
  "embedding_length": 768,
  "chunking_strategy": "tokens",
  "token_chunk_size": 800,
  "token_chunk_overlap": 160,
  "extensions": [".py", ".js", ".ts", ".rs"],
  "max_file_size_bytes": 524288,
  "batch_segment_threshold": 40,
  "search_file_type_weights": {
    ".ts": 1.5,
    ".js": 1.3,
    ".py": 1.4,
    ".rs": 1.2
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.3},
    {"pattern": "test/", "boost": 0.4}
  ]
}
```

#### Step 5: Enable Semantic Chunking

```json
{
  "embedding_length": 768,
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 100,
  "extensions": [".py", ".js", ".ts", ".rs"],
  "max_file_size_bytes": 524288,
  "batch_segment_threshold": 30,
  "search_file_type_weights": {
    ".ts": 1.5,
    ".js": 1.3,
    ".py": 1.4,
    ".rs": 1.2
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.3},
    {"pattern": "test/", "boost": 0.4}
  ]
}
```

## Benchmarking Examples

### Performance Comparison Script

```python
import time
import json
from typing import Dict, Any

def benchmark_configuration(config: Dict[str, Any], workspace: str, name: str):
    """Benchmark a specific configuration."""
    print(f"\n=== Benchmarking {name} ===")
    
    start_time = time.time()
    
    try:
        result = index(workspace=workspace, **config)
        
        end_time = time.time()
        duration = end_time - start_time
        
        files_processed = result.get('files_processed', 0)
        files_per_second = files_processed / duration if duration > 0 else 0
        
        print(f"✓ Success")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Files processed: {files_processed}")
        print(f"  Files/second: {files_per_second:.1f}")
        print(f"  Total segments: {result.get('total_segments', 0)}")
        
        return {
            "success": True,
            "duration": duration,
            "files_processed": files_processed,
            "files_per_second": files_per_second,
            "total_segments": result.get('total_segments', 0)
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✗ Failed: {e}")
        print(f"  Duration: {duration:.1f}s")
        
        return {
            "success": False,
            "duration": duration,
            "error": str(e)
        }

# Test configurations
configs = {
    "fast": {
        "chunking_strategy": "lines",
        "batch_segment_threshold": 100,
        "max_file_size_bytes": 262144
    },
    "balanced": {
        "chunking_strategy": "tokens",
        "token_chunk_size": 800,
        "batch_segment_threshold": 60
    },
    "accurate": {
        "chunking_strategy": "treesitter",
        "use_tree_sitter": True,
        "batch_segment_threshold": 30
    }
}

# Run benchmarks
workspace = "/path/to/test/project"
results = {}

for name, config in configs.items():
    results[name] = benchmark_configuration(config, workspace, name)

# Print summary
print("\n=== BENCHMARK SUMMARY ===")
for name, result in results.items():
    if result["success"]:
        print(f"{name:>10}: {result['files_per_second']:>6.1f} files/sec, {result['duration']:>6.1f}s total")
    else:
        print(f"{name:>10}: FAILED - {result['error']}")
```

### Search Quality Comparison

```python
def compare_search_quality(queries: list, configs: dict):
    """Compare search quality across different configurations."""
    
    results = {}
    
    for config_name, config in configs.items():
        print(f"\n=== Testing {config_name} configuration ===")
        
        # Re-index with this configuration
        index_result = index(workspace="/test/project", **config)
        
        config_results = []
        
        for query in queries:
            search_results = search(
                query=query,
                workspace="/test/project",
                **config.get('search_overrides', {})
            )
            
            config_results.append({
                "query": query,
                "result_count": len(search_results),
                "avg_score": sum(r['adjustedScore'] for r in search_results) / len(search_results) if search_results else 0,
                "top_score": max(r['adjustedScore'] for r in search_results) if search_results else 0
            })
        
        results[config_name] = config_results
    
    # Print comparison
    print("\n=== SEARCH QUALITY COMPARISON ===")
    for query in queries:
        print(f"\nQuery: '{query}'")
        for config_name in configs.keys():
            query_result = next(r for r in results[config_name] if r['query'] == query)
            print(f"  {config_name:>10}: {query_result['result_count']:>3} results, avg={query_result['avg_score']:.3f}, top={query_result['top_score']:.3f}")

# Test different search configurations
search_configs = {
    "default": {},
    "strict": {
        "search_overrides": {
            "search_min_score": 0.7,
            "search_max_results": 20
        }
    },
    "comprehensive": {
        "search_overrides": {
            "search_min_score": 0.3,
            "search_max_results": 100
        }
    }
}

test_queries = [
    "authentication middleware",
    "database connection",
    "error handling",
    "user interface component",
    "API endpoint"
]

compare_search_quality(test_queries, search_configs)
```

This comprehensive configuration guide provides templates and examples for every common use case, helping you optimize the Code Index MCP Server for your specific needs.