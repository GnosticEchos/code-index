# MCP Server Troubleshooting Guide

This guide covers common issues, error messages, and solutions when using the Code Index MCP Server.

## Table of Contents

- [Server Startup Issues](#server-startup-issues)
- [Configuration Problems](#configuration-problems)
- [Service Connection Issues](#service-connection-issues)
- [Indexing Problems](#indexing-problems)
- [Search Issues](#search-issues)
- [Collection Management Problems](#collection-management-problems)
- [Performance Issues](#performance-issues)
- [Error Message Reference](#error-message-reference)

## Server Startup Issues

### Server Won't Start

**Symptoms**:
- MCP server fails to initialize
- Connection refused errors
- Import errors

**Common Causes & Solutions**:

1. **Missing Dependencies**:
   ```bash
   # Install all required dependencies
   uv pip install -e .
   
   # Check for missing optional dependencies
   pip install langchain-text-splitters  # For token chunking
   pip install pygments                  # For auto-extensions
   ```

2. **Python Version Compatibility**:
   ```bash
   # Check Python version (requires 3.13+)
   python --version
   
   # Use correct Python version
   uv venv --python 3.13
   ```

3. **Configuration File Issues**:
   ```bash
   # Check if config file exists and is valid JSON
   cat code_index.json | python -m json.tool
   
   # Create minimal config if missing
   echo '{"embedding_length": 768}' > code_index.json
   ```

### Permission Errors

**Error**: `Permission denied when accessing workspace`

**Solutions**:
```bash
# Check workspace permissions
ls -la /path/to/workspace

# Fix permissions if needed
chmod -R 755 /path/to/workspace

# Run with appropriate user permissions
sudo -u appropriate_user python -m code_index.mcp_server.server
```

## Configuration Problems

### Missing embedding_length

**Error**: `embedding_length must be set in configuration`

**Explanation**: The embedding dimension must match your Ollama model's output dimension.

**Solutions**:

1. **For nomic-embed-text (most common)**:
   ```json
   {
     "embedding_length": 768
   }
   ```

2. **For other models**:
   ```bash
   # Check model info
   ollama show your-model-name
   
   # Common dimensions:
   # nomic-embed-text: 768
   # all-minilm: 384
   # text-embedding-ada-002: 1536
   ```

3. **Auto-detect dimension** (if unsure):
   ```python
   # Test embedding to get dimension
   import requests
   response = requests.post("http://localhost:11434/api/embeddings", json={
       "model": "nomic-embed-text:latest",
       "prompt": "test"
   })
   dimension = len(response.json()["embedding"])
   print(f"Embedding dimension: {dimension}")
   ```

### Invalid Configuration Values

**Error**: `Invalid configuration parameter: <parameter>`

**Common Issues**:

1. **Invalid chunking_strategy**:
   ```json
   {
     "chunking_strategy": "treesitter"  // Valid: "lines", "tokens", "treesitter"
   }
   ```

2. **Invalid file size limits**:
   ```json
   {
     "max_file_size_bytes": 1048576,           // 1MB in bytes
     "tree_sitter_max_file_size_bytes": 524288 // 512KB in bytes
   }
   ```

3. **Invalid search parameters**:
   ```json
   {
     "search_min_score": 0.4,    // Must be 0.0-1.0
     "search_max_results": 50    // Must be positive integer
   }
   ```

## Service Connection Issues

### Ollama Connection Problems

**Error**: `Failed to connect to Ollama service`

**Diagnostic Steps**:

1. **Check if Ollama is running**:
   ```bash
   # Test Ollama API
   curl http://localhost:11434/api/tags
   
   # Should return list of available models
   ```

2. **Verify model availability**:
   ```bash
   # List installed models
   ollama list
   
   # Pull required model if missing
   ollama pull nomic-embed-text:latest
   ```

3. **Test embedding generation**:
   ```bash
   # Test embedding API
   curl -X POST http://localhost:11434/api/embeddings \
     -H "Content-Type: application/json" \
     -d '{"model": "nomic-embed-text:latest", "prompt": "test"}'
   ```

4. **Check Ollama configuration**:
   ```json
   {
     "ollama_base_url": "http://localhost:11434",
     "ollama_model": "nomic-embed-text:latest"
   }
   ```

**Common Solutions**:

- **Start Ollama**: `ollama serve`
- **Change port**: Update `ollama_base_url` if Ollama runs on different port
- **Network issues**: Use `http://127.0.0.1:11434` instead of `localhost`
- **Firewall**: Ensure port 11434 is accessible

### Qdrant Connection Problems

**Error**: `Failed to connect to Qdrant service`

**Diagnostic Steps**:

1. **Check if Qdrant is running**:
   ```bash
   # Test Qdrant API
   curl http://localhost:6333/collections
   
   # Should return collections list (may be empty)
   ```

2. **Verify Qdrant configuration**:
   ```json
   {
     "qdrant_url": "http://localhost:6333",
     "qdrant_api_key": null  // or your API key
   }
   ```

3. **Test with Docker**:
   ```bash
   # Start Qdrant with Docker
   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
   
   # Or with persistent storage
   docker run -p 6333:6333 -p 6334:6334 \
     -v $(pwd)/qdrant_storage:/qdrant/storage \
     qdrant/qdrant
   ```

**Common Solutions**:

- **Start Qdrant**: Use Docker or native installation
- **Check port**: Ensure port 6333 is accessible
- **API key**: Set `qdrant_api_key` if authentication is required
- **Network**: Use `http://127.0.0.1:6333` instead of `localhost`

## Indexing Problems

### Embedding Timeouts

**Error**: `Embedding timeout for file: <filename>`

**Symptoms**:
- Files listed in `timeout_files.txt`
- Incomplete indexing
- Long processing times

**Solutions**:

1. **Increase timeout**:
   ```python
   index(
       workspace="/path/to/project",
       embed_timeout=300  # 5 minutes instead of default 60 seconds
   )
   ```

2. **Retry failed files**:
   ```python
   # After initial indexing with timeouts
   index(
       workspace="/path/to/project",
       retry_list="timeout_files.txt",
       embed_timeout=300
   )
   ```

3. **Reduce batch size**:
   ```json
   {
     "batch_segment_threshold": 30  // Smaller batches, default is 60
   }
   ```

4. **Skip large files**:
   ```json
   {
     "max_file_size_bytes": 524288  // 512KB instead of 1MB
   }
   ```

### Tree-sitter Parsing Errors

**Error**: `Tree-sitter parsing failed for <filename>`

**Symptoms**:
- Fallback to line-based chunking
- Warning messages about unsupported languages

**Solutions**:

1. **Check supported languages**:
   ```python
   # Tree-sitter supports: Python, JavaScript, TypeScript, Rust, Go, Java, C++, C#
   # For other languages, use "lines" or "tokens" chunking
   ```

2. **Adjust Tree-sitter limits**:
   ```json
   {
     "tree_sitter_max_file_size_bytes": 262144,  // 256KB limit
     "tree_sitter_max_blocks_per_file": 50,      // Fewer blocks per file
     "tree_sitter_skip_test_files": true         // Skip test files
   }
   ```

3. **Use alternative chunking**:
   ```python
   index(
       workspace="/path/to/project",
       chunking_strategy="tokens"  // Use token-based instead
   )
   ```

### Large Repository Issues

**Symptoms**:
- Very long indexing times
- Memory usage issues
- Process killed by system

**Solutions**:

1. **Use CLI for initial indexing**:
   ```bash
   # Use CLI tool for large repositories
   code-index index --workspace /large/project --embed-timeout 300
   ```

2. **Batch processing**:
   ```python
   # Create workspace list for batch processing
   with open("workspaces.txt", "w") as f:
       f.write("/project/src\n")
       f.write("/project/lib\n")
       f.write("/project/tests\n")
   
   index(workspacelist="workspaces.txt")
   ```

3. **Optimize configuration**:
   ```json
   {
     "max_file_size_bytes": 262144,        // 256KB limit
     "batch_segment_threshold": 20,        // Smaller batches
     "tree_sitter_max_file_size_bytes": 131072  // 128KB for Tree-sitter
   }
   ```

## Search Issues

### No Search Results

**Error**: `No results found for query`

**Diagnostic Steps**:

1. **Check if workspace is indexed**:
   ```python
   collections_result = collections(subcommand="list")
   print(collections_result)  # Should show collections for your workspace
   ```

2. **Verify collection has data**:
   ```python
   collections(subcommand="info", collection_name="ws-your-collection-id")
   ```

3. **Lower search threshold**:
   ```python
   search(
       query="your query",
       min_score=0.2,  # Lower threshold
       max_results=100  # More results
   )
   ```

4. **Try broader queries**:
   ```python
   # Instead of: "specific function name"
   # Try: "function" or "authentication" or "database"
   ```

### Poor Search Quality

**Symptoms**:
- Irrelevant results
- Missing expected results
- Low scores for relevant code

**Solutions**:

1. **Adjust file type weights**:
   ```python
   search(
       query="your query",
       search_file_type_weights={
           ".ts": 2.0,      # Boost TypeScript
           ".js": 1.5,      # Boost JavaScript
           ".test.js": 0.1  # Reduce test files
       }
   )
   ```

2. **Use path boosts**:
   ```json
   {
     "search_path_boosts": [
       {"pattern": "src/", "boost": 1.5},
       {"pattern": "lib/", "boost": 1.3},
       {"pattern": "test/", "boost": 0.5}
     ]
   }
   ```

3. **Improve indexing quality**:
   ```python
   # Re-index with Tree-sitter for better semantic chunks
   index(
       workspace="/path/to/project",
       chunking_strategy="treesitter",
       use_tree_sitter=True
   )
   ```

## Collection Management Problems

### Collection Not Found

**Error**: `Collection not found: <collection_name>`

**Solutions**:

1. **List available collections**:
   ```python
   collections(subcommand="list")
   ```

2. **Check collection naming**:
   ```bash
   # Collections are named: ws-<16-char-hash>
   # Based on workspace path hash
   ```

3. **Re-index if collection missing**:
   ```python
   index(workspace="/path/to/workspace")
   ```

### Destructive Operation Confirmation

**Issue**: Confirmation prompts in automated scripts

**Solutions**:

1. **Use yes parameter**:
   ```python
   collections(subcommand="delete", collection_name="ws-abc123", yes=True)
   ```

2. **Handle confirmation in code**:
   ```python
   try:
       result = collections(subcommand="clear-all")
       # Handle confirmation prompt
   except Exception as e:
       # Handle confirmation denial
   ```

## Performance Issues

### Slow Indexing

**Symptoms**:
- Indexing takes very long time
- High CPU/memory usage
- Frequent timeouts

**Solutions**:

1. **Optimize chunking strategy**:
   ```json
   {
     "chunking_strategy": "lines",  // Fastest option
     "use_tree_sitter": false       // Disable for speed
   }
   ```

2. **Reduce batch sizes**:
   ```json
   {
     "batch_segment_threshold": 20,  // Smaller batches
     "max_file_size_bytes": 262144   // Skip large files
   }
   ```

3. **Filter file types**:
   ```json
   {
     "extensions": [".py", ".js", ".ts"],  // Only essential types
     "auto_extensions": false              // Disable auto-detection
   }
   ```

### Slow Search

**Symptoms**:
- Search queries take long time
- High memory usage during search

**Solutions**:

1. **Limit result set**:
   ```python
   search(
       query="your query",
       min_score=0.6,   # Higher threshold
       max_results=20   # Fewer results
   )
   ```

2. **Optimize Qdrant**:
   ```bash
   # Use Qdrant with more memory
   docker run -p 6333:6333 -p 6334:6334 \
     -e QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=32 \
     qdrant/qdrant
   ```

## Error Message Reference

### Configuration Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `embedding_length must be set` | Missing dimension config | Set `embedding_length` to match model |
| `Invalid chunking_strategy` | Wrong strategy name | Use "lines", "tokens", or "treesitter" |
| `Configuration file not found` | Missing config file | Create `code_index.json` with defaults |

### Service Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Ollama connection failed` | Ollama not running | Start Ollama with `ollama serve` |
| `Qdrant connection failed` | Qdrant not accessible | Start Qdrant service |
| `Model not found` | Missing Ollama model | Pull model with `ollama pull` |

### Operation Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Workspace not found` | Invalid path | Check workspace path exists |
| `Permission denied` | Access rights | Fix file/directory permissions |
| `Embedding timeout` | Large files/slow model | Increase timeout, reduce batch size |

### Search Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `No collection found` | Workspace not indexed | Run index tool first |
| `Invalid query` | Empty/invalid query | Provide non-empty search query |
| `Score threshold too high` | No results above threshold | Lower `min_score` parameter |

## Getting Help

If you encounter issues not covered in this guide:

1. **Check logs**: Enable debug logging for detailed error information
2. **Verify services**: Ensure Ollama and Qdrant are running and accessible
3. **Test CLI**: Try equivalent CLI commands to isolate MCP-specific issues
4. **Check configuration**: Validate JSON syntax and parameter values
5. **Review examples**: Compare your usage with working examples

### Debug Logging

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run your MCP operations with debug output
```

### Service Health Checks

Quick health check script:

```bash
#!/bin/bash
echo "Checking Ollama..."
curl -s http://localhost:11434/api/tags > /dev/null && echo "✓ Ollama OK" || echo "✗ Ollama failed"

echo "Checking Qdrant..."
curl -s http://localhost:6333/collections > /dev/null && echo "✓ Qdrant OK" || echo "✗ Qdrant failed"

echo "Checking config..."
python -c "import json; json.load(open('code_index.json'))" && echo "✓ Config OK" || echo "✗ Config invalid"
```