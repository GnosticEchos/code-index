# Usage Guide — Code Index Tool

This guide explains how to use the standalone code index tool with any workspace. It covers basic setup, indexing, search, and safe reset operations. For the complete command reference, see [docs/cli-reference.md](docs/cli-reference.md). The implementation lives under [src/code_index/](src/code_index/).

Note: This product is independent and not tied to any external application. Examples below are generic and do not assume any specific project.

## Prerequisites
- Python 3.13+
- Ollama running with an embedding model (default URL http://localhost:11434)
- Qdrant server (default URL http://localhost:6333)
- Optional: uv for environment management

## Quick setup
1) Create and activate a virtual environment (example with uv)
   ```bash
   uv venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2) Install the tool in editable mode from this repository root
   ```bash
   uv pip install -e .
   ```
3) Create a minimal configuration file (embedding_length must match your model)
   ```bash
   cat > code_index.json << 'EOF'
   { "embedding_length": 768, "workspace_path": "." }
   EOF
   ```

## Index your workspace
Run the index command from your workspace root (or pass --workspace):
```bash
code-index index --workspace . --config code_index.json
```
What happens:
- Scans files respecting ignore rules and size limits
- Splits files into chunks (line-based by default; token or Tree-sitter optional)
- Generates embeddings via Ollama and upserts points into Qdrant
- Caches file hashes to avoid reprocessing unchanged files

See indexing options in [src/code_index/cli.py](src/code_index/cli.py) and the full reference in [docs/cli-reference.md](docs/cli-reference.md).

## Search your indexed code
Find relevant code with semantic search:
```bash
code-index search "function to parse JSON" --config code_index.json
```
Useful flags:
- --min-score FLOAT (default from config)
- --max-results INT (default from config)
- --json to print machine-readable results

Search implementation touches [src/code_index/embedder.py](src/code_index/embedder.py) and [src/code_index/vector_store.py](src/code_index/vector_store.py).

## Global reset (destructive)
Delete ALL Qdrant collections (metadata included by default) and clear local cache:
```bash
code-index collections clear-all --yes
```
Safety tips:
- Preview without deleting: code-index collections clear-all --dry-run
- Preserve metadata: code-index collections clear-all --keep-metadata
- Delete a single collection only: code-index collections delete COLLECTION_NAME

Commands are implemented under [src/code_index/collections_commands.py](src/code_index/collections_commands.py).

## Troubleshooting
- Ollama connectivity: ensure the service is running and the model is available (e.g., nomic-embed-text:latest).
- Qdrant connectivity: verify URL/API key and service status.
- Required configuration: embedding_length must be set before creating a collection.
- Timeouts: increase embed timeout via config or --embed-timeout; use --retry-list to re-run only failed files.

For exhaustive flags, behaviors, and examples, see [docs/cli-reference.md](docs/cli-reference.md).