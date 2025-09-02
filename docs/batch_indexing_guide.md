# Enhanced Batch Indexing Guide

## Overview

The enhanced batch indexing system provides flexible, configurable batch processing of multiple workspaces with advanced features for performance optimization and workflow management.

## Key Features

### Flexible Workspace Input
- **File-based input**: Newline-delimited workspace paths from file
- **Command-line input**: Multiple `--workspace` arguments
- **Mixed input**: Combine file and command-line workspaces
- **Duplicate elimination**: Automatic deduplication while preserving order

### Advanced Workflow Management
- **Sequential processing**: Process workspaces one at a time with configurable delays
- **Concurrent processing**: Future enhancement for parallel indexing
- **Resume capability**: Continue from last failed workspace
- **Dry-run mode**: Plan batch operations without executing

### Performance Optimization
- **Smart delays**: Configurable wait time between workspaces
- **File size limits**: Prevent processing of oversized files
- **Timeout management**: Configurable timeouts per workspace
- **Resource monitoring**: Future enhancement for system resource tracking

### Detailed Logging and Monitoring
- **Comprehensive logs**: Detailed activity logging with timestamps
- **Progress tracking**: Real-time progress updates
- **Error handling**: Robust error handling with detailed diagnostics
- **Failure recovery**: Resume from interruption points

## Usage Examples

### Basic Batch Indexing
```bash
# Create workspace list file
echo -e "/path/to/project1\n/path/to/project2\n/path/to/project3" > workspace_list.txt

# Run basic batch indexing
python scripts/utilities/batch_indexer.py --workspace-list workspace_list.txt
```

### Advanced Batch Indexing with Tree-sitter
```bash
# Run batch indexing with semantic chunking
python scripts/utilities/batch_indexer.py \
  --workspace-list workspace_list.txt \
  --use-tree-sitter \
  --chunking-strategy treesitter \
  --embed-timeout 1200 \
  --delay 60
```

### Mixed Input Sources
```bash
# Combine file-based and command-line workspaces
python scripts/utilities/batch_indexer.py \
  --workspace-list workspace_list.txt \
  --workspace /additional/project1 \
  --workspace /additional/project2
```

### Resume from Failure
```bash
# Resume from last failed workspace
python scripts/utilities/batch_indexer.py \
  --workspace-list workspace_list.txt \
  --resume
```

### Dry-run Planning
```bash
# See what would be indexed without actually indexing
python scripts/utilities/batch_indexer.py \
  --workspace-list workspace_list.txt \
  --dry-run
```

## Configuration Options

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--workspace-list` | Path to file containing newline-delimited workspace paths | None |
| `--workspace` | Workspace paths (can be specified multiple times) | None |
| `--config` | Configuration file template | `code_index.json` |
| `--embed-timeout` | Embedding timeout in seconds | `600` |
| `--concurrent` | Enable concurrent indexing | `False` (sequential) |
| `--delay` | Delay between workspaces in seconds | `30` |
| `--resume` | Resume from last failed workspace | `False` |
| `--dry-run` | Show what would be indexed without actually indexing | `False` |

### Workspace List File Format
```
# Comments start with #
# Blank lines are ignored

/path/to/project1
/path/to/project2
/path/to/project3

# Additional projects
/more/projects/project4
/more/projects/project5
```

### Configuration File Template
```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  "embedding_length": 768,
  "chunking_strategy": "lines",
  "token_chunk_size": 1000,
  "token_chunk_overlap": 200,
  "auto_extensions": false,
  "exclude_files_path": null,
  "timeout_log_path": "timeout_files.txt",
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 60,
  "search_min_score": 0.4,
  "search_max_results": 50,
  "use_tree_sitter": false,
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_max_blocks_per_file": 100,
  "tree_sitter_max_functions_per_file": 50,
  "tree_sitter_max_classes_per_file": 20,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock",
    "target/", "build/", "dist/", "node_modules/", "__pycache__/"
  ]
}
```

## Workflow Examples

### Daily Indexing Routine
```bash
# Create daily workspace list
echo -e "/home/user/projects/project1\n/home/user/projects/project2" > daily_workspaces_$(date +%Y%m%d).txt

# Run daily indexing with resume capability
python scripts/utilities/batch_indexer.py \
  --workspace-list daily_workspaces_$(date +%Y%m%d).txt \
  --embed-timeout 1800 \
  --delay 45 \
  --resume \
  --config daily_config.json
```

### Weekly Deep Indexing
```bash
# Create weekly workspace list with Tree-sitter
find /home/user/projects -type d -name ".git" | sed 's/\/\.git$//' > weekly_workspaces_$(date +%Y%U).txt

# Run weekly deep indexing with semantic chunking
python scripts/utilities/batch_indexer.py \
  --workspace-list weekly_workspaces_$(date +%Y%U).txt \
  --use-tree-sitter \
  --chunking-strategy treesitter \
  --embed-timeout 3600 \
  --delay 120 \
  --config weekly_config.json
```

### Emergency Recovery
```bash
# Resume from previous failure
python scripts/utilities/batch_indexer.py \
  --workspace-list workspace_list.txt \
  --resume \
  --embed-timeout 7200 \
  --delay 15
```

## Performance Considerations

### Resource Management
1. **Sequential Processing**: Default mode prevents resource contention
2. **Configurable Delays**: Allows system recovery between workspaces
3. **Timeout Management**: Prevents hanging on problematic workspaces
4. **Memory Cleanup**: Future enhancement for resource cleanup

### File Size Management
1. **Smart Filtering**: Skip test, example, and generated files
2. **Size Limits**: Configurable file size thresholds
3. **Batch Processing**: Process large workspaces in manageable chunks

### System Monitoring
1. **Progress Tracking**: Real-time updates on indexing progress
2. **Resource Usage**: Future enhancement for monitoring CPU/memory
3. **Error Diagnostics**: Detailed error reporting for troubleshooting

## Integration with Other Tools

### KiloCode Compatibility
- **Shared Collections**: Both tools use identical Qdrant collections
- **No Duplicate Work**: KiloCode recognizes our indexing as complete
- **Seamless Search**: KiloCode can search our indexed content
- **Unified Workflow**: Single indexing pass serves both tools

### CI/CD Integration
```yaml
# GitHub Actions example
name: Code Index Update
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  index-code:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install tree-sitter-language-pack
      
      - name: Run batch indexing
        run: |
          python scripts/utilities/batch_indexer.py \
            --workspace-list workspace_list.txt \
            --config ci_config.json \
            --embed-timeout 3600
```

### Automation Scripts
```bash
#!/bin/bash
# nightly_index.sh

# Create workspace list
find /home/user/projects -maxdepth 2 -type d -name ".git" | sed 's/\/\.git$//' > workspace_list.txt

# Run nightly indexing
python scripts/utilities/batch_indexer.py \
  --workspace-list workspace_list.txt \
  --config nightly_config.json \
  --embed-timeout 7200 \
  --delay 60 \
  --resume

# Clean up
rm -f workspace_list.txt

echo "Nightly indexing complete at $(date)"
```

## Troubleshooting

### Common Issues

#### Workspace Not Found
```
⚠️ Directory not found: /path/to/nonexistent/project
```
**Solution**: Verify workspace paths exist and are accessible

#### Timeout Issues
```
⏱️ Timeout: /path/to/large/project
```
**Solution**: Increase `--embed-timeout` or use `--resume` to continue

#### Configuration Errors
```
❌ Error: Config error: Please set 'embedding_length' in code_index.json
```
**Solution**: Verify configuration file has required fields

### Advanced Debugging

#### Verbose Logging
```bash
# Enable debug logging
export DEBUG_LOGGING=1
python scripts/utilities/batch_indexer.py --workspace-list workspace_list.txt
```

#### Monitor Progress
```bash
# Watch log file in real-time
tail -f batch_index_log_*.txt
```

#### Check Failed Workspaces
```bash
# Check which workspaces failed
cat batch_failed_workspaces_*.txt
```

## Best Practices

### Workspace List Management
1. **Version Control**: Store workspace lists in version control
2. **Regular Updates**: Update lists when projects are added/removed
3. **Comments**: Use comments to document workspace purposes
4. **Sorting**: Sort by priority or size for optimal processing

### Configuration Management
1. **Environment-specific configs**: Separate configs for dev/prod
2. **Backup configs**: Keep copies of working configurations
3. **Document changes**: Track config changes and their effects
4. **Test configs**: Validate configs before batch runs

### Performance Optimization
1. **Batch by size**: Group similarly-sized workspaces together
2. **Schedule wisely**: Run during low-usage periods
3. **Monitor resources**: Watch CPU/memory during indexing
4. **Adjust timeouts**: Tune timeouts based on workspace characteristics

### Error Handling
1. **Use resume mode**: Always use `--resume` for long-running batches
2. **Check logs regularly**: Monitor for errors and warnings
3. **Test small batches first**: Validate workflow with small test sets
4. **Have rollback plans**: Know how to recover from failures

The enhanced batch indexing system provides powerful, flexible batch processing capabilities while maintaining reliability and performance optimization.