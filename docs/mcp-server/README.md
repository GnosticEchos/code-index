# Code Index MCP Server

A Model Context Protocol (MCP) server that provides LLM agents with powerful code indexing and semantic search capabilities. Built on the robust Code Index tool, this server exposes three primary tools through a standardized MCP interface for seamless integration with AI development workflows.

## Overview

The Code Index MCP Server transforms the existing CLI-based code indexing tool into an MCP-compliant service that LLM agents can interact with directly. It provides:

- **Semantic Code Indexing**: Index entire codebases with advanced chunking strategies
- **Natural Language Search**: Find code using natural language queries
- **Collection Management**: Safely manage indexed collections and vector databases

## Quick Start

### Prerequisites

- Python 3.13+
- Ollama with embedding models (e.g., `nomic-embed-text:latest`)
- Qdrant vector database server
- `uv` for environment management (recommended)

### Installation

```bash
# Clone and install the code index tool
git clone <repository-url>
cd code-index-tool

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

### Basic Setup

1. **Start required services:**
   ```bash
   # Start Ollama (in separate terminal)
   ollama serve
   
   # Pull embedding model
   ollama pull nomic-embed-text:latest
   
   # Start Qdrant (in separate terminal)
   docker run -p 6333:6333 qdrant/qdrant
   ```

2. **Configure the MCP server:**
   ```bash
   # Create configuration file
   echo '{
     "embedding_length": 768,
     "ollama_base_url": "http://localhost:11434",
     "ollama_model": "nomic-embed-text:latest",
     "qdrant_url": "http://localhost:6333"
   }' > code_index.json
   ```

3. **Start the MCP server:**
   ```bash
   python -m code_index.mcp_server.server
   ```

## MCP Tools Reference

### 1. Index Tool

**Purpose**: Index code repositories for semantic search

**Usage**:
```python
# Basic indexing
index(workspace="/path/to/project")

# Advanced indexing with Tree-sitter
index(
    workspace="/path/to/project",
    chunking_strategy="treesitter",
    use_tree_sitter=True,
    embed_timeout=120
)

# Batch indexing multiple workspaces
index(workspacelist="/path/to/workspace_list.txt")
```

**Key Parameters**:
- `workspace` (str): Directory to index (default: current directory)
- `chunking_strategy` (str): "lines", "tokens", or "treesitter"
- `use_tree_sitter` (bool): Force semantic chunking
- `embed_timeout` (int): Timeout for embedding operations
- `workspacelist` (str): File with multiple workspace paths

**Performance Warnings**:
- Large repositories (>1000 files) may take significant time
- Tree-sitter chunking increases processing time but improves semantic accuracy
- Consider running CLI equivalent for very large codebases

### 2. Search Tool

**Purpose**: Perform semantic searches on indexed code

**Usage**:
```python
# Basic search
search(query="authentication middleware")

# Advanced search with filtering
search(
    query="error handling patterns",
    min_score=0.6,
    max_results=20,
    search_file_type_weights={".ts": 1.5, ".js": 1.2}
)
```

**Key Parameters**:
- `query` (str, required): Natural language search query
- `workspace` (str): Workspace to search (default: current directory)
- `min_score` (float): Minimum similarity threshold (0.0-1.0)
- `max_results` (int): Maximum results to return (1-500)

**Search Features**:
- Natural language queries
- File type weighting for relevance
- Path-based result boosting
- Language-specific scoring adjustments

### 3. Collections Tool

**Purpose**: Manage indexed collections safely

**Usage**:
```python
# List all collections
collections(subcommand="list")

# Get detailed collection info
collections(subcommand="info", collection_name="ws-abc123def456")

# Delete specific collection (with confirmation)
collections(subcommand="delete", collection_name="ws-abc123def456")

# Delete all collections (with confirmation)
collections(subcommand="clear-all")

# Bypass confirmation for automation
collections(subcommand="clear-all", yes=True)
```

**Subcommands**:
- `list`: Show all collections with workspace mappings
- `info`: Detailed information about a specific collection
- `delete`: Remove a specific collection (destructive)
- `prune`: Remove collections older than specified days (destructive)
- `clear-all`: Remove all collections and cache (destructive)

**Safety Features**:
- Confirmation prompts for destructive operations
- Detailed operation previews
- Graceful error handling and recovery

## Configuration

### Configuration File Structure

The MCP server uses the same configuration system as the CLI tool. Create a `code_index.json` file:

```json
{
  "embedding_length": 768,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "qdrant_api_key": null,
  "workspace_path": ".",
  "extensions": [".rs", ".ts", ".vue", ".js", ".py", ".md", ".json"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,
  "embed_timeout_seconds": 60,
  "chunking_strategy": "lines",
  "use_tree_sitter": false,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 100,
  "search_file_type_weights": {
    ".vue": 1.30,
    ".ts": 1.25,
    ".js": 1.20,
    ".py": 1.15,
    ".rs": 1.10,
    ".md": 0.80
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.25},
    {"pattern": "lib/", "boost": 1.20},
    {"pattern": "docs/", "boost": 0.85},
    {"pattern": "test/", "boost": 0.70}
  ]
}
```

### Environment Variables

Override configuration with environment variables:

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="nomic-embed-text:latest"
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your-api-key"
export CODE_INDEX_EMBED_TIMEOUT="120"
```

### Configuration Overrides

Override configuration per operation:

```python
# Override embedding timeout for this indexing operation
index(
    workspace="/large/project",
    embed_timeout=300,  # 5 minutes for large files
    batch_segment_threshold=30  # Smaller batches
)

# Override search parameters
search(
    query="database queries",
    search_min_score=0.7,  # Higher threshold
    search_max_results=10   # Fewer results
)
```

## Error Handling and Troubleshooting

### Common Issues

#### 1. Missing embedding_length Configuration

**Error**: `embedding_length must be set in configuration`

**Solution**:
```json
{
  "embedding_length": 768  // For nomic-embed-text
  // or 1024 for other models
}
```

#### 2. Service Connection Failures

**Ollama Connection Error**:
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull required model
ollama pull nomic-embed-text:latest
```

**Qdrant Connection Error**:
```bash
# Check Qdrant is running
curl http://localhost:6333/collections

# Start Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant
```

#### 3. Embedding Timeouts

**Symptoms**: Files listed in timeout logs, incomplete indexing

**Solutions**:
- Increase `embed_timeout` parameter
- Use retry functionality with timeout logs
- Consider smaller batch sizes for large files

```python
# Retry failed files with longer timeout
index(
    workspace="/path/to/project",
    retry_list="timeout_files.txt",
    embed_timeout=300
)
```

#### 4. Large Repository Performance

**Symptoms**: Very long indexing times, memory issues

**Solutions**:
- Use CLI tool for initial indexing of large repositories
- Enable Tree-sitter chunking for better semantic accuracy
- Adjust batch sizes and file size limits

```bash
# Use CLI for large repositories
code-index index --workspace /large/project --use-tree-sitter --embed-timeout 300
```

### Error Response Format

All tools return structured error responses:

```json
{
  "error": true,
  "error_type": "configuration_error",
  "message": "embedding_length must be set in configuration",
  "details": {
    "missing_field": "embedding_length",
    "suggested_values": [768, 1024, 3584]
  },
  "actionable_guidance": [
    "Set embedding_length in code_index.json to match your model",
    "For nomic-embed-text, use 768",
    "For larger models, check model documentation"
  ]
}
```

## Performance Optimization

### Indexing Performance

1. **Choose appropriate chunking strategy**:
   - `lines`: Fastest, good for general use
   - `tokens`: Balanced performance and semantic quality
   - `treesitter`: Best semantic accuracy, slower processing

2. **Optimize batch sizes**:
   ```json
   {
     "batch_segment_threshold": 30,  // Smaller batches for stability
     "max_file_size_bytes": 524288   // Skip very large files
   }
   ```

3. **Use Tree-sitter selectively**:
   ```json
   {
     "tree_sitter_max_file_size_bytes": 262144,  // 256KB limit
     "tree_sitter_skip_test_files": true         // Skip test files
   }
   ```

### Search Performance

1. **Adjust result limits**:
   ```python
   search(
       query="your query",
       min_score=0.6,      # Higher threshold = fewer results
       max_results=20      # Limit result set size
   )
   ```

2. **Use file type weighting**:
   ```json
   {
     "search_file_type_weights": {
       ".ts": 1.5,   // Boost TypeScript files
       ".test.js": 0.5  // Reduce test file relevance
     }
   }
   ```

## Integration Examples

### Basic Workflow

```python
# 1. Index a codebase
result = index(workspace="/path/to/project")
if result.get("error"):
    print(f"Indexing failed: {result['message']}")
else:
    print(f"Indexed {result['files_processed']} files")

# 2. Search for code
results = search(query="authentication middleware")
for result in results:
    print(f"Found in {result['filePath']}:{result['startLine']}")
    print(f"Score: {result['adjustedScore']:.3f}")
    print(f"Code: {result['snippet']}")

# 3. Manage collections
collections_list = collections(subcommand="list")
for collection in collections_list["collections"]:
    print(f"Collection: {collection['name']} ({collection['points']} points)")
```

### Advanced Configuration

```python
# High-accuracy indexing for critical projects
index(
    workspace="/critical/project",
    chunking_strategy="treesitter",
    use_tree_sitter=True,
    tree_sitter_max_blocks_per_file=200,
    embed_timeout=300
)

# Precision search with custom weighting
search(
    query="security vulnerability patterns",
    min_score=0.8,
    max_results=10,
    search_file_type_weights={
        ".ts": 2.0,      # Heavily favor TypeScript
        ".js": 1.5,      # Favor JavaScript
        ".test.js": 0.1  # Minimize test files
    }
)
```

## Next Steps

- [Configuration Examples](configuration-examples.md) - Detailed configuration templates
- [Performance Optimization Guide](performance-optimization.md) - Advanced tuning
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [API Reference](api-reference.md) - Complete parameter documentation

## Support

For issues and questions:
1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review configuration examples for your use case
3. Consult the CLI documentation for equivalent operations
4. Check service logs for detailed error information