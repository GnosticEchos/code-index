# MCP Server API Reference

Complete reference documentation for all MCP tools, parameters, and configuration options provided by the Code Index MCP Server.

## Table of Contents

- [Tool Overview](#tool-overview)
- [Index Tool](#index-tool)
- [Search Tool](#search-tool)
- [Collections Tool](#collections-tool)
- [Configuration Reference](#configuration-reference)
- [Error Responses](#error-responses)
- [Data Types](#data-types)

## Tool Overview

The Code Index MCP Server provides three primary tools:

| Tool | Purpose | Destructive | Long-Running |
|------|---------|-------------|--------------|
| `index` | Index code repositories | No | Yes |
| `search` | Search indexed code | No | No |
| `collections` | Manage collections | Yes* | No |

*Some collections operations are destructive and require confirmation.

## Index Tool

### Function Signature

```python
async def index(
    workspace: str = ".",
    config: Optional[str] = None,
    workspacelist: Optional[str] = None,
    embed_timeout: Optional[int] = None,
    chunking_strategy: Optional[str] = None,
    use_tree_sitter: Optional[bool] = None,
    **config_overrides
) -> Dict[str, Any]
```

### Parameters

#### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `workspace` | `str` | `"."` | Path to the directory to index |
| `config` | `str` | `None` | Path to configuration file (auto-created if missing) |
| `workspacelist` | `str` | `None` | Path to file containing multiple workspace paths |
| `embed_timeout` | `int` | `None` | Override embedding timeout in seconds |
| `chunking_strategy` | `str` | `None` | Chunking method: "lines", "tokens", or "treesitter" |
| `use_tree_sitter` | `bool` | `None` | Force Tree-sitter chunking regardless of strategy |

#### Configuration Override Parameters

All configuration parameters can be overridden for individual operations:

| Parameter | Type | Description |
|-----------|------|-------------|
| `embedding_length` | `int` | Vector dimension (must match model) |
| `batch_segment_threshold` | `int` | Number of segments per batch |
| `max_file_size_bytes` | `int` | Maximum file size to process |
| `tree_sitter_max_file_size_bytes` | `int` | Maximum file size for Tree-sitter |
| `tree_sitter_max_blocks_per_file` | `int` | Maximum blocks per file for Tree-sitter |
| `tree_sitter_skip_test_files` | `bool` | Skip test files in Tree-sitter mode |
| `token_chunk_size` | `int` | Token chunk size for token strategy |
| `token_chunk_overlap` | `int` | Token overlap for token strategy |
| `extensions` | `List[str]` | File extensions to process |
| `auto_extensions` | `bool` | Auto-detect extensions via Pygments |
| `exclude_files_path` | `str` | Path to file exclusion list |
| `timeout_log_path` | `str` | Path to timeout log file |

### Return Value

```python
{
    "success": bool,
    "files_processed": int,
    "files_skipped": int,
    "total_segments": int,
    "processing_time_seconds": float,
    "collection_name": str,
    "workspace_path": str,
    "timeout_files": List[str],
    "warnings": List[str],
    "error": bool,           # Only present if error occurred
    "error_type": str,       # Only present if error occurred
    "message": str,          # Only present if error occurred
    "actionable_guidance": List[str]  # Only present if error occurred
}
```

### Usage Examples

#### Basic Indexing

```python
# Index current directory
result = index()

# Index specific workspace
result = index(workspace="/path/to/project")

# Index with configuration file
result = index(
    workspace="/path/to/project",
    config="/path/to/custom_config.json"
)
```

#### Advanced Indexing

```python
# Tree-sitter chunking with custom timeout
result = index(
    workspace="/path/to/project",
    chunking_strategy="treesitter",
    use_tree_sitter=True,
    embed_timeout=300
)

# Token-based chunking with custom parameters
result = index(
    workspace="/path/to/project",
    chunking_strategy="tokens",
    token_chunk_size=800,
    token_chunk_overlap=160,
    batch_segment_threshold=40
)

# High-performance configuration
result = index(
    workspace="/path/to/project",
    chunking_strategy="lines",
    batch_segment_threshold=100,
    max_file_size_bytes=524288,
    embed_timeout=60
)
```

#### Batch Processing

```python
# Create workspace list file
with open("workspaces.txt", "w") as f:
    f.write("/project/frontend\n")
    f.write("/project/backend\n")
    f.write("/project/shared\n")

# Process multiple workspaces
result = index(workspacelist="workspaces.txt")
```

### Performance Considerations

- **Large repositories**: Consider using CLI tool for initial indexing
- **Tree-sitter**: Slower but more accurate semantic chunking
- **Batch size**: Smaller batches for stability, larger for speed
- **Timeouts**: Increase for large files or slow embedding models

## Search Tool

### Function Signature

```python
async def search(
    query: str,
    workspace: str = ".",
    min_score: Optional[float] = None,
    max_results: Optional[int] = None,
    **search_overrides
) -> List[Dict[str, Any]]
```

### Parameters

#### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | Required | Natural language search query |
| `workspace` | `str` | `"."` | Workspace to search |
| `min_score` | `float` | `None` | Minimum similarity score (0.0-1.0) |
| `max_results` | `int` | `None` | Maximum number of results |

#### Search Override Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `search_min_score` | `float` | Minimum similarity threshold |
| `search_max_results` | `int` | Maximum results to return |
| `search_snippet_preview_chars` | `int` | Length of code snippets |
| `search_file_type_weights` | `Dict[str, float]` | File type relevance weights |
| `search_path_boosts` | `List[Dict]` | Path-based result boosting |
| `search_language_boosts` | `Dict[str, float]` | Language-specific boosts |
| `search_exclude_patterns` | `List[str]` | Patterns to exclude from results |

### Return Value

```python
[
    {
        "filePath": str,
        "startLine": int,
        "endLine": int,
        "type": str,
        "score": float,
        "adjustedScore": float,
        "snippet": str,
        "language": str,
        "fileSize": int
    },
    # ... more results
]
```

### Usage Examples

#### Basic Search

```python
# Simple search
results = search(query="authentication middleware")

# Search with custom thresholds
results = search(
    query="database connection",
    min_score=0.6,
    max_results=20
)
```

#### Advanced Search with Weighting

```python
# Custom file type weighting
results = search(
    query="error handling",
    search_file_type_weights={
        ".ts": 2.0,      # Strongly favor TypeScript
        ".js": 1.5,      # Favor JavaScript
        ".py": 1.3,      # Favor Python
        ".test.js": 0.2, # Minimize test files
        ".md": 0.8       # Reduce documentation
    }
)

# Path-based boosting
results = search(
    query="API endpoints",
    search_path_boosts=[
        {"pattern": "src/", "boost": 1.5},
        {"pattern": "api/", "boost": 2.0},
        {"pattern": "test/", "boost": 0.3}
    ]
)

# Language-specific boosting
results = search(
    query="async functions",
    search_language_boosts={
        "typescript": 1.5,
        "javascript": 1.3,
        "python": 1.2
    }
)
```

#### Precision Search

```python
# High-precision search
results = search(
    query="security vulnerability patterns",
    min_score=0.8,
    max_results=10,
    search_file_type_weights={".ts": 2.0, ".js": 1.8},
    search_exclude_patterns=["test", "spec", "mock"]
)
```

### Search Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `filePath` | `str` | Relative path to the file |
| `startLine` | `int` | Starting line number of the code block |
| `endLine` | `int` | Ending line number of the code block |
| `type` | `str` | Type of code block (function, class, etc.) |
| `score` | `float` | Raw similarity score from vector search |
| `adjustedScore` | `float` | Score after applying weights and boosts |
| `snippet` | `str` | Code snippet preview |
| `language` | `str` | Detected programming language |
| `fileSize` | `int` | File size in bytes |

## Collections Tool

### Function Signature

```python
async def collections(
    subcommand: str,
    collection_name: Optional[str] = None,
    older_than_days: Optional[int] = None,
    yes: bool = False,
    detailed: bool = False,
    **options
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `subcommand` | `str` | Required | Operation: "list", "info", "delete", "prune", "clear-all" |
| `collection_name` | `str` | `None` | Collection name (required for "info" and "delete") |
| `older_than_days` | `int` | `None` | Age threshold for "prune" operation |
| `yes` | `bool` | `False` | Skip confirmation for destructive operations |
| `detailed` | `bool` | `False` | Show detailed information |

### Subcommands

#### list

List all available collections.

```python
# Basic list
result = collections(subcommand="list")

# Detailed list with full paths
result = collections(subcommand="list", detailed=True)
```

**Return Value**:
```python
{
    "collections": [
        {
            "name": str,
            "points": int,
            "workspace_path": str,
            "created_date": str,
            "indexed_date": str,
            "status": str
        }
    ],
    "total_collections": int,
    "total_points": int
}
```

#### info

Get detailed information about a specific collection.

```python
result = collections(
    subcommand="info",
    collection_name="ws-abc123def456"
)
```

**Return Value**:
```python
{
    "collection_name": str,
    "workspace_path": str,
    "points": int,
    "vectors": int,
    "status": str,
    "created_date": str,
    "indexed_date": str,
    "config": {
        "embedding_length": int,
        "model": str,
        "chunking_strategy": str
    },
    "statistics": {
        "files_indexed": int,
        "total_segments": int,
        "average_score": float
    }
}
```

#### delete

Delete a specific collection.

```python
# With confirmation prompt
result = collections(
    subcommand="delete",
    collection_name="ws-abc123def456"
)

# Skip confirmation
result = collections(
    subcommand="delete", 
    collection_name="ws-abc123def456",
    yes=True
)
```

**Return Value**:
```python
{
    "deleted": bool,
    "collection_name": str,
    "cache_cleaned": bool,
    "message": str
}
```

#### prune

Delete collections older than specified days.

```python
# Prune collections older than 30 days
result = collections(
    subcommand="prune",
    older_than_days=30
)

# Skip confirmation
result = collections(
    subcommand="prune",
    older_than_days=30,
    yes=True
)
```

**Return Value**:
```python
{
    "pruned_collections": List[str],
    "total_pruned": int,
    "total_points_removed": int,
    "message": str
}
```

#### clear-all

Delete all collections and clear cache.

```python
# With confirmation prompt
result = collections(subcommand="clear-all")

# Skip confirmation
result = collections(subcommand="clear-all", yes=True)
```

**Return Value**:
```python
{
    "deleted_collections": List[str],
    "total_deleted": int,
    "cache_cleared": bool,
    "message": str
}
```

## Configuration Reference

### Core Configuration

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "qdrant_api_key": null,
  "workspace_path": "."
}
```

### File Processing Configuration

```json
{
  "extensions": [".py", ".js", ".ts", ".rs", ".go", ".java"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": false,
  "exclude_files_path": null
}
```

### Chunking Configuration

```json
{
  "chunking_strategy": "lines",
  "token_chunk_size": 1000,
  "token_chunk_overlap": 200,
  "use_tree_sitter": false,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 100,
  "tree_sitter_skip_test_files": true
}
```

### Performance Configuration

```json
{
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 60,
  "timeout_log_path": "timeout_files.txt"
}
```

### Search Configuration

```json
{
  "search_min_score": 0.4,
  "search_max_results": 50,
  "search_snippet_preview_chars": 160,
  "search_file_type_weights": {
    ".ts": 1.25,
    ".js": 1.20,
    ".py": 1.15,
    ".md": 0.80
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.25},
    {"pattern": "test/", "boost": 0.70}
  ],
  "search_language_boosts": {
    "typescript": 1.20,
    "python": 1.15
  },
  "search_exclude_patterns": ["node_modules", ".git"]
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama service URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `nomic-embed-text:latest` |
| `QDRANT_URL` | Qdrant service URL | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant API key | `null` |
| `WORKSPACE_PATH` | Default workspace path | `.` |
| `CODE_INDEX_EMBED_TIMEOUT` | Embedding timeout | `60` |

## Error Responses

All tools return structured error responses when operations fail:

```python
{
    "error": True,
    "error_type": str,
    "message": str,
    "details": Dict[str, Any],
    "actionable_guidance": List[str]
}
```

### Error Types

| Error Type | Description | Common Causes |
|------------|-------------|---------------|
| `configuration_error` | Invalid configuration | Missing embedding_length, invalid parameters |
| `service_connection_error` | Service unavailable | Ollama/Qdrant not running |
| `workspace_error` | Workspace issues | Path not found, permission denied |
| `operation_error` | Operation failed | Embedding timeout, vector store error |
| `validation_error` | Parameter validation failed | Invalid parameter values |
| `safety_error` | Safety check failed | Destructive operation without confirmation |

### Example Error Responses

#### Configuration Error

```python
{
    "error": True,
    "error_type": "configuration_error",
    "message": "embedding_length must be set in configuration",
    "details": {
        "missing_field": "embedding_length",
        "suggested_values": [768, 1024, 3584]
    },
    "actionable_guidance": [
        "Set embedding_length in code_index.json to match your model",
        "For nomic-embed-text, use 768",
        "Check your model documentation for the correct dimension"
    ]
}
```

#### Service Connection Error

```python
{
    "error": True,
    "error_type": "service_connection_error",
    "message": "Failed to connect to Ollama service",
    "details": {
        "service": "Ollama",
        "base_url": "http://localhost:11434",
        "model": "nomic-embed-text:latest"
    },
    "actionable_guidance": [
        "Start Ollama service with: ollama serve",
        "Pull the required model: ollama pull nomic-embed-text:latest",
        "Check if Ollama is running on the correct port"
    ]
}
```

## Data Types

### Configuration Override

```python
@dataclass
class ConfigurationOverride:
    embedding_length: Optional[int] = None
    chunking_strategy: Optional[str] = None
    use_tree_sitter: Optional[bool] = None
    batch_segment_threshold: Optional[int] = None
    embed_timeout_seconds: Optional[int] = None
    max_file_size_bytes: Optional[int] = None
    tree_sitter_max_file_size_bytes: Optional[int] = None
    tree_sitter_max_blocks_per_file: Optional[int] = None
    tree_sitter_skip_test_files: Optional[bool] = None
    search_min_score: Optional[float] = None
    search_max_results: Optional[int] = None
    search_file_type_weights: Optional[Dict[str, float]] = None
    search_path_boosts: Optional[List[Dict[str, Any]]] = None
```

### Search Result

```python
@dataclass
class SearchResult:
    filePath: str
    startLine: int
    endLine: int
    type: str
    score: float
    adjustedScore: float
    snippet: str
    language: str
    fileSize: int
```

### Collection Info

```python
@dataclass
class CollectionInfo:
    name: str
    workspace_path: str
    points: int
    vectors: int
    status: str
    created_date: str
    indexed_date: str
    config: Dict[str, Any]
    statistics: Dict[str, Any]
```

This API reference provides complete documentation for all MCP tools and their parameters. Use it as a comprehensive guide for integrating the Code Index MCP Server into your applications.