# Code Index Tool

A standalone code indexing tool that uses Ollama for embeddings and Qdrant for vector storage, based on the kilocode code-index functionality.

## Features

- Index code files from any directory
- Generate embeddings using Ollama
- Store embeddings in Qdrant vector database
- Search indexed code using semantic search
- Support for multiple programming languages including Rust, TypeScript, Vue, and SurrealDB Query Language (Surql)
- File change detection to avoid reprocessing
- Configurable Ollama and Qdrant endpoints
- Config-first embedding length (required via config.embedding_length)
- Token-based chunking option using LangChain TokenTextSplitter with approximate line mapping
- Auto-extensions discovery via Pygments (augment supported extensions)
- Configurable embed timeout (config/env/CLI), timeout logging, and retry-list processing
- Exclude arbitrary files with a newline-separated path list

## Requirements

- Python 3.13+
- Ollama with embedding models
- Qdrant server
- `uv` for environment management (recommended)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd code-index-tool

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

## Usage

```bash
# Index a directory
code-index index --workspace /path/to/code

# Search indexed code
code-index search "function to parse JSON"

# Global reset: delete ALL collections and clear cache (destructive)
code-index collections clear-all --yes
```

## Configuration

The tool can be configured using a JSON configuration file:

```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "qdrant_api_key": null,
  "workspace_path": ".",
  "extensions": [".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx", ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".md", ".json", ".yaml", ".yml"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,

  "embedding_length": 768,
  "embed_timeout_seconds": 60,
  "chunking_strategy": "lines",
  "token_chunk_size": 1000,
  "token_chunk_overlap": 200,
  "auto_extensions": false,
  "exclude_files_path": null,
  "timeout_log_path": "timeout_files.txt"
}
```

You can also set configuration via environment variables:
- `OLLAMA_BASE_URL` - Ollama base URL (default: http://localhost:11434)
- `OLLAMA_MODEL` - Ollama model to use (default: nomic-embed-text:latest)
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)
- `QDRANT_API_KEY` - Qdrant API key (optional)
- `WORKSPACE_PATH` - Workspace path (default: .)
- `CODE_INDEX_EMBED_TIMEOUT` - Embedding timeout in seconds (overrides config.embed_timeout_seconds)

## Supported Languages

- Rust (.rs)
- TypeScript (.ts)
- Vue (.vue)
- SurrealDB Query Language (.surql)
- JavaScript (.js)
- Python (.py)
- React (.jsx, .tsx)
- Go (.go)
- Java (.java)
- C++ (.cpp, .hpp)
- C (.c, .h)
- C# (.cs)
- Ruby (.rb)
- PHP (.php)
- Swift (.swift)
- Kotlin (.kt)
- Scala (.scala)
- Dart (.dart)
- Lua (.lua)
- Perl (.pl, .pm)
- R (.r)
- SQL (.sql)
- HTML (.html)
- CSS (.css, .scss, .sass, .less)
- Markdown (.md, .markdown)
- reStructuredText (.rst)
- Text (.txt)
- JSON (.json)
- XML (.xml)
- YAML (.yaml, .yml)

## How It Works

1. **File Scanning**: The tool recursively scans the specified directory for supported files, respecting .gitignore patterns.

2. **Code Parsing**: Files are parsed into meaningful code blocks. For now, a simple line-based chunking approach is used, but this could be enhanced with tree-sitter parsing in the future.

3. **Embedding Generation**: Ollama is used to generate vector embeddings for each code block.

4. **Vector Storage**: Embeddings are stored in Qdrant with metadata about the file path, line numbers, and content.

5. **Caching**: File hashes are cached to avoid reprocessing unchanged files.

6. **Search**: Semantic search is performed by generating an embedding for the query and finding similar vectors in Qdrant.

## Example Workflow

```bash
# Index your codebase
code-index index --workspace /path/to/your/project

# Search for specific functionality
code-index search "database connection function"

# Search with custom parameters
code-index search "API endpoint" --min-score 0.5 --max-results 20
```

## Development

For development and testing scripts, see the `scripts/` directory and documentation in `docs/development/`.

## License

MIT
## Advanced Features

### Config-first Embedding Length
- You must set a dimension that matches your embedding model:
  - In config file: `"embedding_length": 768` (example)
  - If missing, initialization fails with a clear error.
- File: [config.py](../src/code_index/config.py#L1)
- Enforcement: [QdrantVectorStore.initialize](../src/code_index/vector_store.py#L80)

### Token-based Chunking
- Enable LangChain-based token chunking via config:
  - `"chunking_strategy": "tokens"`
  - `"token_chunk_size": 1000`
  - `"token_chunk_overlap": 200`
- Approximate line mapping is preserved for UI display.
- Fallback: If langchain-text-splitters is unavailable, tool falls back to line-based with a warning.
- File: [parser.py](../src/code_index/parser.py#L1)

### Auto-extensions (Pygments)
- When `"auto_extensions": true`, extensions from Pygments lexers are merged into your configured list.
- If Pygments is missing, a non-fatal warning is logged and configured extensions are used unchanged.
- Files: [utils.py](../src/code_index/utils.py#L78), [scanner.py](../src/code_index/scanner.py#L1)

### Exclude File List
- Exclude arbitrary files using a newline-separated list (relative to workspace):
  - `"exclude_files_path": "ignore_files.txt"`
- Absolute paths inside the file are normalized to relative paths.
- Comments beginning with `#` and blank lines are ignored.
- File: [scanner.py](../src/code_index/scanner.py#L1)

### Timeout, Retry-list, and Logging
- Configure embedding timeout by:
  - Config: `"embed_timeout_seconds": 60`
  - Env: `CODE_INDEX_EMBED_TIMEOUT=120`
  - CLI: `--embed-timeout 180`
- Timeouts (embedding ReadTimeout, upsert “timed out”) are collected and written to a log (default `timeout_files.txt`, configurable via `"timeout_log_path"` or `--timeout-log`).
- Retry only failed files:
  - `code-index index --workspace <root> --retry-list timeout_files.txt --embed-timeout 180`
  - In retry-list mode, the tool skips scanning the workspace and processes only the listed files, still respecting excludes, extension filters, size limits, and binary checks.
- Files: [embedder.py](../src/code_index/embedder.py#L1), [cli.py](../src/code_index/cli.py#L1)

## Examples

### Minimal Config with New Keys
```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "workspace_path": ".",
  "extensions": [".rs", ".ts", ".vue", ".js", ".py", ".md", ".json", ".yaml", ".yml"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,

  "embedding_length": 768,
  "embed_timeout_seconds": 60,
  "chunking_strategy": "lines",
  "token_chunk_size": 1000,
  "token_chunk_overlap": 200,
  "auto_extensions": false,
  "exclude_files_path": "ignore_files.txt",
  "timeout_log_path": "timeout_files.txt"
}
```

### Retry Only Failed Files With Longer Timeout
```bash
# Using venv created via uv or python -m venv
code-index index \
  --workspace /path/to/workspace \
  --config code_index.json \
  --retry-list timeout_files.txt \
  --embed-timeout 180 \
  --timeout-log timeout_files.txt
```

### Token-based Chunking
```json
{
  "chunking_strategy": "tokens",
  "token_chunk_size": 800,
  "token_chunk_overlap": 160
}
```

### Auto-extensions
```json
{
  "auto_extensions": true
}
```