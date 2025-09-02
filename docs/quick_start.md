# Quick Start Guide

## Getting Started with Enhanced Features

This guide will help you get started with the enhanced features of the code index tool, including Tree-sitter semantic chunking, intelligent ignore patterns, smart collections, and KiloCode compatibility.

## Prerequisites

Make sure you have the required dependencies installed:

```bash
# Install the tool
pip install -e .

# Install Tree-sitter language pack (for semantic chunking)
pip install tree-sitter-language-pack
```

## Basic Usage

### 1. Simple Indexing (Legacy)
```bash
# Basic indexing with line-based chunking (default)
code-index index --workspace /path/to/your/project
```

### 2. Enhanced Indexing with Tree-sitter
```bash
# Index with semantic code chunking
code-index index --workspace /path/to/your/project --use-tree-sitter

# Or use configuration file for persistent settings
echo '{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter"
}' > treesitter_config.json

code-index index --workspace /path/to/your/project --config treesitter_config.json
```

### 3. Smart Collection Management
```bash
# List all collections with human-readable workspace paths
code-index collections list

# View detailed information about a collection
code-index collections info ws-491a59846b84697a

# Delete a collection (careful - this removes all data!)
code-index collections delete ws-491a59846b84697a

# Prune old collections to free up storage
code-index collections prune --older-than 30
```

## Configuration Examples

### Basic Configuration with Tree-sitter
```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "workspace_path": ".",
  "extensions": [".py", ".js", ".ts", ".rs", ".go", ".java"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,
  "embedding_length": 768,
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter",
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock",
    "target/", "build/", "dist/", "node_modules/"
  ]
}
```

### Advanced Configuration with Ignore Patterns
```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "workspace_path": ".",
  "extensions": [".py", ".js", ".ts", ".rs", ".go", ".java"],
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,
  "embedding_length": 768,
  "auto_ignore_detection": true,
  "apply_github_templates": true,
  "apply_project_gitignore": true,
  "apply_global_ignores": true,
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter",
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 100,
  "tree_sitter_max_functions_per_file": 50,
  "tree_sitter_max_classes_per_file": 20,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock",
    "target/", "build/", "dist/", "node_modules/"
  ]
}
```

## Searching Indexed Content

### Basic Search
```bash
# Search with default settings
code-index search "authentication function"

# Search with custom configuration
code-index search --config treesitter_config.json "database connection"

# Search with higher minimum score for more precise results
code-index search --min-score 0.6 "REST API endpoint"
```

### Advanced Search Options
```bash
# Search with more results
code-index search --max-results 100 "error handling"

# Search specific workspace
code-index search --workspace /path/to/your/project "configuration loading"
```

## KiloCode Integration

### Compatibility Benefits
When you index a workspace with our tool, KiloCode will:

1. ✅ **Recognize** the collection as already indexed
2. ✅ **Use** our semantic chunks for `code_search`
3. ✅ **Skip** re-indexing the workspace
4. ✅ **Benefit** from our enhanced ignore patterns
5. ✅ **Share** the same Qdrant collections

### Verification
```bash
# Index with our tool
code-index index --workspace /path/to/your/project --use-tree-sitter

# Check that collection was created
code-index collections list

# Open the same workspace in KiloCode - it should:
# 1. Generate the same collection name
# 2. Find the collection already exists
# 3. Recognize it as valid
# 4. Use our semantic chunks for searches
# 5. NOT re-index the workspace
```

## Performance Tips

### 1. Optimize File Size Limits
```json
{
  "max_file_size_bytes": 524288,  // 512KB for regular files
  "tree_sitter_max_file_size_bytes": 262144  // 256KB for Tree-sitter parsing
}
```

### 2. Configure Ignore Patterns
```json
{
  "auto_ignore_detection": true,
  "apply_github_templates": true,
  "apply_project_gitignore": true,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true
}
```

### 3. Limit Semantic Blocks
```json
{
  "tree_sitter_max_blocks_per_file": 50,
  "tree_sitter_max_functions_per_file": 30,
  "tree_sitter_max_classes_per_file": 15
}
```

## Troubleshooting

### Common Issues

#### Tree-sitter Not Working
```bash
# Install Tree-sitter language pack
pip install tree-sitter-language-pack

# Verify installation
python -c "import tree_sitter_language_pack; print('Tree-sitter installed successfully')"
```

#### Large Files Slowing Down Indexing
```bash
# Reduce file size limits in config
{
  "max_file_size_bytes": 262144,  // 256KB
  "tree_sitter_max_file_size_bytes": 131072  // 128KB
}
```

#### Too Many Irrelevant Files Being Indexed
```bash
# Enable smart ignore detection
{
  "auto_ignore_detection": true,
  "apply_github_templates": true,
  "apply_project_gitignore": true
}
```

### Debugging Commands
```bash
# Enable verbose logging
export DEBUG_LOGGING=1

# Test Tree-sitter on specific file
code-index index --workspace /path/to/single/file.py --config debug_config.json

# Check collection information
code-index collections info ws-491a59846b84697a
```

## Advanced Features

### 1. Batch Indexing
```bash
# Create batch configuration
echo '{
  "workspaces": [
    "/path/to/project1",
    "/path/to/project2",
    "/path/to/project3"
  ],
  "use_tree_sitter": true
}' > batch_config.json

# Run batch indexing
python scripts/batch_indexer.py --config batch_config.json
```

### 2. Custom Ignore Patterns
```bash
# Use custom ignore configuration
code-index index --ignore-config /path/to/custom_ignore.txt

# Override ignore patterns
code-index index --ignore-override-pattern "*.log,temp/"
```

### 3. Retry Failed Files
```bash
# Index with timeout logging
code-index index --workspace /path/to/large/project --embed-timeout 30 --timeout-log timeouts.txt

# Retry only failed files with longer timeout
code-index index --workspace /path/to/large/project --retry-list timeouts.txt --embed-timeout 120
```

## Best Practices

### 1. Configuration Management
```bash
# Create project-specific configuration
cp code_index.json project_config.json
# Edit project_config.json for project-specific settings

# Use different configurations for different purposes
code-index index --config project_config.json
code-index search --config project_config.json "function name"
```

### 2. Collection Management
```bash
# Regular cleanup of old collections
code-index collections prune --older-than 30

# Monitor collection sizes
code-index collections list --detailed
```

### 3. Performance Monitoring
```bash
# Use timeout logging to identify slow files
code-index index --timeout-log slow_files.txt

# Review and optimize
cat slow_files.txt | head -10
```

## Next Steps

1. **Try Tree-sitter**: Experiment with semantic chunking for better search results
2. **Configure Ignore Patterns**: Enable smart filtering for cleaner indexing
3. **Integrate with KiloCode**: Verify seamless compatibility with your workflow
4. **Explore Advanced Features**: Batch indexing, custom configurations, and more

The enhanced code index tool provides powerful features for semantic code indexing while maintaining full compatibility with KiloCode and offering superior performance and flexibility.