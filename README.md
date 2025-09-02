# Code Index Tool

A standalone code indexing tool that uses Ollama for embeddings and Qdrant for vector storage. It provides fast, configurable, and resilient indexing for many programming languages, with KiloCode-compatible collections and payloads.

- Index code files from any directory
- Generate embeddings using Ollama
- Store embeddings in Qdrant vector database
- Search indexed code using semantic search
- Multi-strategy chunking: lines, tokens (LangChain), and Tree-sitter, with graceful fallbacks
- File change detection to avoid reprocessing
- Configurable Ollama and Qdrant endpoints
- Config-first embedding length (required via config.embedding_length)
- Token-based chunking option using LangChain TokenTextSplitter with approximate line mapping
- Auto-extensions discovery via Pygments (augment supported extensions)
- Configurable embed timeout (config/env/CLI), timeout logging, and retry-list processing
- Exclude arbitrary files via a newline-separated path list (config.exclude_files_path)
- Enhanced collection management with workspace path mapping
- Smart ignore patterns (community templates, project .gitignore, global ignores)
- Memory-mapped file reading (mmap) for improved large-file performance (config-only)
- KiloCode-compatible collection naming and payload fields

Notes:
- No synonym-expansion query rewriting or interactive search prompts are implemented.
- No built-in concurrent batch scheduler/resumer; batch processing is supported via a workspace list file.

## KiloCode Compatibility

This tool produces Qdrant collections KiloCode can use directly:
- Collection naming matches KiloCode convention: “ws-” + SHA256(workspace_path) prefix
- Payload fields match KiloCode expectations: filePath, codeChunk, startLine, endLine, type
- Both tools can use the same collections without duplication

See the CLI entry points [cli.index()](src/code_index/cli.py:154), [cli.search()](src/code_index/cli.py:471), and collection commands in [collections_commands.py](src/code_index/collections_commands.py) including collections clear-all.

## Requirements

- Python 3.13+
- Ollama with an embedding model available
- Qdrant server
- Optional: uv for environment management

## Windows Development Notes

If you are developing on Windows, please note the following differences:

**1. Makefile:** This project uses a `Makefile` for common tasks. On Windows, you should use the `Makefile.windows` file, which is designed for the `cmd.exe` shell.
   ```shell
   # Example: running the 'clean' command on Windows
   make -f Makefile.windows clean
   ```

**2. Virtual Environment:** To activate the virtual environment, use the following command:
   ```shell
   .\venv\Scripts\activate
   ```

**3. Configuration File:** The `cat` command is not available in `cmd.exe`. Create the `code_index.json` file manually in the root of the project and paste the JSON configuration into it.

**4. `tree-sitter` Compilation:** The `tree-sitter` dependency requires a C++ compiler. If you run into installation errors, you will need to install the **Visual Studio Build Tools**. You can download them from the official [Visual Studio website](https://visualstudio.microsoft.com/visual-cpp-build-tools/). Ensure that the "C++ build tools" workload is selected during installation.

## Quick Start

```bash
# For Windows users, please see the "Windows Development Notes" section above for platform-specific commands.
# Clone the repository
git clone <repository-url>
cd code_index

# Create virtual environment with uv (optional)
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install package and dependencies
uv pip install -e .

# Optional: improve language detection for Tree-sitter file routing
uv pip install whats-that-code

# Create configuration file
cat > code_index.json << 'EOF'
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "workspace_path": ".",
  "extensions": [".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,
  "embedding_length": 768,
  "embed_timeout_seconds": 60,
  "chunking_strategy": "lines",
  "use_tree_sitter": false
}
EOF

# Index your codebase
code-index index

# Search indexed code
code-index search "function to parse JSON"

# Global reset: delete ALL collections and clear cache (destructive)
code-index collections clear-all --yes
```

Tip:
- Set embedding_length to match your model’s dimensionality (e.g., 1024 for some Qwen models, 768 for nomic-embed-text).

## CLI Commands

Full reference: [docs/cli-reference.md](docs/cli-reference.md)

Primary entry points:
- [cli.index()](src/code_index/cli.py:154)
- [cli.search()](src/code_index/cli.py:471)

### Index Command

```bash
code-index index [--workspace PATH] [--config FILE] [--workspacelist FILE] \
                 [--embed-timeout SECONDS] [--retry-list FILE] [--timeout-log FILE] \
                 [--ignore-config FILE] [--ignore-override-pattern PATTERN] \
                 [--auto-ignore-detection] \
                 [--use-tree-sitter] [--chunking-strategy lines|tokens|treesitter]
```

Indexes code files in the specified workspace.

Options:
- --workspace: Workspace path (default: current directory)
- --config: Configuration file (default: code_index.json)
- --workspacelist: Path to file containing newline-delimited absolute directory paths to process (batch)
- --embed-timeout: Override embedding timeout (seconds) for this run
- --retry-list: Path to file with newline-separated relative file paths to reprocess only
- --timeout-log: Override timeout log path for this run (default from config.timeout_log_path)
- --ignore-config: Path to custom ignore configuration file
- --ignore-override-pattern: Additional ignore pattern(s) to apply
- --auto-ignore-detection: Enable automatic ignore detection (default: enabled). To disable, set auto_ignore_detection to false in the configuration file.
- --use-tree-sitter: Force Tree-sitter-based semantic chunking for this run (overrides --chunking-strategy and config)
- --chunking-strategy: lines (default), tokens, or treesitter

Batch indexing:
```bash
# Prepare a list of workspaces (absolute paths), one per line
printf "/path/to/project1\n/path/to/project2\n" > workspace_list.txt

# Process all listed workspaces sequentially
code-index index --workspacelist workspace_list.txt --use-tree-sitter
```

Retry only failed files after timeouts (exact guidance printed after a run):
```bash
code-index index --workspace <your-workspace> --retry-list <timeout_files.txt> --embed-timeout <seconds>
```

### Search Command

```bash
code-index search QUERY [--config FILE] [--min-score SCORE] [--max-results COUNT] [--json]
```

Searches indexed code using semantic search.

Options:
- QUERY: Search query text
- --config: Configuration file (default: code_index.json)
- --min-score: Minimum similarity score (default: 0.4, from config.search_min_score)
- --max-results: Maximum number of results (default: 50, from config.search_max_results)
- --json: Output results as JSON; snippet preview length uses config.search_snippet_preview_chars (default: 160)

Implementation details:
- Vector search and ranking: [vector_store.QdrantVectorStore.search()](src/code_index/vector_store.py:300)
- Adjusted scores apply file-type, path, and language weighting from configuration

### Collections Management

```bash
code-index collections list [--detailed]
code-index collections info COLLECTION_NAME
code-index collections delete COLLECTION_NAME
code-index collections prune [--older-than DAYS]
code-index collections clear-all [--yes|-y] [--dry-run] [--keep-metadata]
```

Manages Qdrant collections and metadata mapping.

- list: Show collections, with optional detailed view
- info: Show collection status and mapped workspace path (when available)
- delete: Remove a collection (with confirmation)
- prune: Delete collections older than the specified days (default: 30)

See collection commands in [collections_commands.py](src/code_index/collections_commands.py).

## Configuration

JSON-first configuration (default file: code_index.json). See [config.Config](src/code_index/config.py:9) for fields and defaults.

Example:
```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "qdrant_api_key": null,
  "workspace_path": ".",
  "extensions": [".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,

  "search_min_score": 0.4,
  "search_max_results": 50,

  "search_file_type_weights": {
    ".vue": 1.30,
    ".ts": 1.25,
    ".tsx": 1.25,
    ".rs": 1.20,
    ".surql": 1.25,
    ".js": 1.10,
    ".md": 0.80,
    ".txt": 0.60
  },
  "search_path_boosts": [
    {"pattern": "src/", "weight": 1.25},
    {"pattern": "components/", "weight": 1.25},
    {"pattern": "views/", "weight": 1.15},
    {"pattern": "docs/", "weight": 0.85}
  ],
  "search_language_boosts": {
    "vue": 1.20,
    "typescript": 1.15,
    "rust": 1.10
  },
  "search_exclude_patterns": [],
  "search_snippet_preview_chars": 160,

  "embedding_length": 768,
  "embed_timeout_seconds": 60,

  "chunking_strategy": "lines",
  "token_chunk_size": 1000,
  "token_chunk_overlap": 200,

  "auto_extensions": false,
  "exclude_files_path": null,
  "timeout_log_path": "timeout_files.txt",

  "auto_ignore_detection": true,

  "skip_dot_files": true,
  "read_root_gitignore_only": true,

  "use_mmap_file_reading": false,
  "mmap_min_file_size_bytes": 65536,

  "use_tree_sitter": false,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_min_block_chars": 50,
  "tree_sitter_max_blocks_per_file": 100,
  "tree_sitter_max_functions_per_file": 50,
  "tree_sitter_max_classes_per_file": 20,
  "tree_sitter_max_impl_blocks_per_file": 30,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock",
    "target/", "build/", "dist/", "node_modules/", "__pycache__/"
  ]
}
```

Environment variables supported:
- OLLAMA_BASE_URL — Ollama base URL (default: http://localhost:11434)
- OLLAMA_MODEL — Ollama model to use (default: nomic-embed-text:latest)
- QDRANT_URL — Qdrant server URL (default: http://localhost:6333)
- QDRANT_API_KEY — Qdrant API key (optional)
- WORKSPACE_PATH — Workspace path (default: .)
- CODE_INDEX_EMBED_TIMEOUT — Embedding timeout in seconds (overrides config.embed_timeout_seconds)

Note:
- Memory-mapped file reading is controlled by configuration only (no env var toggle).
- For Tree-sitter language detection, installing whats-that-code is optional; a manual extension mapping fallback is used otherwise.

## Performance Tuning

The default settings offer a good balance of speed and reliability for most projects. However, if you feel that indexing is sluggish, especially on repositories with many large files, you might want to try adjusting the file reading mechanism for better performance.

### Memory-Mapped File Reading (mmap)

This tool supports memory-mapped (mmap) file reading, a technique that can significantly reduce memory usage and speed up processing for larger files. Instead of loading an entire file into memory, `mmap` allows the operating system to efficiently load parts of the file on demand.

**When to use it:** If you are indexing a repository with numerous source files larger than a few megabytes, enabling `use_mmap_file_reading` can lead to noticeable improvements. For projects with mostly small files, the standard file reading method is often sufficient.

These settings are available in your `code_index.json`:

| Option                   | Description                                                                    | Default        |
| ------------------------ | ------------------------------------------------------------------------------ | -------------- |
| `use_mmap_file_reading`    | Set to `true` to enable memory-mapped file reading.                            | `false`        |
| `mmap_min_file_size_bytes` | The minimum file size to use mmap for. Smaller files will use the standard method. | `65536` (64KB) |

### Tree-sitter Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| use_tree_sitter | Enable semantic code chunking with Tree-sitter | false |
| chunking_strategy | Set to "treesitter" for semantic chunking | "lines" |
| tree_sitter_max_file_size_bytes | Max file size for Tree-sitter parsing | 512KB |
| tree_sitter_min_block_chars | Min chars for semantic blocks | 50 |
| tree_sitter_max_blocks_per_file | Max semantic blocks per file | 100 |
| tree_sitter_max_functions_per_file | Max functions per file | 50 |
| tree_sitter_max_classes_per_file | Max classes per file | 20 |
| tree_sitter_max_impl_blocks_per_file | Max impl blocks per file | 30 |
| tree_sitter_skip_test_files | Skip test/spec files | true |
| tree_sitter_skip_examples | Skip example/sample files | true |
| tree_sitter_skip_patterns | File patterns to skip | [...] |

## How It Works

1. File Scanning
   - Recursively scans the directory for supported files, honoring ignore patterns (community templates, .gitignore, and global rules when enabled).
2. File Reading
   - Chooses traditional or memory-mapped reading based on config thresholds; gracefully falls back on errors. See [parser.CodeParser](src/code_index/parser.py:13).
3. Chunking
   - Splits files into code blocks using the configured strategy:
     - Line-based ([chunking.LineChunkingStrategy](src/code_index/chunking.py:53))
     - Token-based via LangChain ([chunking.TokenChunkingStrategy](src/code_index/chunking.py:101))
     - Tree-sitter semantic blocks with robust multi-API fallbacks ([chunking.TreeSitterChunkingStrategy](src/code_index/chunking.py:163))
4. Embedding Generation
   - Uses Ollama’s /api/embed with configurable timeouts. See [embedder.OllamaEmbedder](src/code_index/embedder.py:9).
5. Vector Storage
   - Stores vectors and KiloCode-compatible payloads in Qdrant with path segment indexes for filtering. See [vector_store.QdrantVectorStore](src/code_index/vector_store.py:13).
6. Caching
   - Caches file hashes to skip unchanged files.
7. Search
   - Performs similarity search and applies adjustedScore weighting by file type, path, and language.

Operational notes:
- Typical startup shows “Validating configuration…”, vector store init, “Scanning directory: …”
- Tree-sitter will warn and fall back to line-based when queries or parsers aren’t available for a file
- Timeouts are recorded; summary prints:
  - “Timeouts: N file(s). Timeout log: timeout_files.txt”
  - “To retry only failed files… code-index index --workspace <...> --retry-list <timeout_log> --embed-timeout <seconds>”
- On shutdown after Tree-sitter runs, resources are cleaned up

## Development

- Primary entry points: [src/code_index/cli.py](src/code_index/cli.py)
- Tests (if present) may adjust search thresholds for specific scenarios
- See also: [pyproject.toml](pyproject.toml) for dependencies and the console script entrypoint

## License

MIT