# Code Index Tool Scripts

This directory contains utility scripts organized by function to help with various aspects of code indexing and management.

## Directory Structure

### `/utilities` - Core Utility Scripts
Essential tools for managing the code index system:
- `delete_all_collections.py` - Completely wipe all Qdrant collections and cache
- `batch_indexer.py` - Process multiple workspaces in batch mode
- `migrate_to_kilocode.py` - Migration tools for KiloCode compatibility
- `check_status.py` - Check indexing status and progress
- `collection_summary.py` - Summarize collection information

### `/testing` - Testing and Verification Scripts
Tools for testing and verifying the indexing system:
- `verify_env.py` - Verify environment setup and dependencies
- `test_qdrant.py` - Test Qdrant connectivity and functionality
- `test_models.py` - Test embedding model availability and performance
- `demo_ignore_system.py` - Demonstrate ignore pattern system

### `/workspace` - Workspace Management Scripts
Tools for discovering and managing workspaces:
- `find_workspaces.py` - Discover potential workspaces for indexing

### `/demo` - Demonstration Scripts
Example scripts showing various features (legacy):
- Various demo scripts for different functionalities

### `/run` - Execution Scripts
Runner scripts for executing tests and demos (legacy):
- Various execution wrapper scripts

## Usage Examples

### Delete All Collections (Clean Start)
```bash
python utilities/delete_all_collections.py
```

### Batch Index Multiple Workspaces
```bash
python utilities/batch_indexer.py --config batch_config.json
```

### Check Indexing Status
```bash
python utilities/check_status.py
```

### Verify Environment Setup
```bash
python testing/verify_env.py
```

### Test Qdrant Connectivity
```bash
python testing/test_qdrant.py
```

## Best Practices

1. **Use utilities scripts** for routine management tasks
2. **Use testing scripts** to verify system health
3. **Refer to demo scripts** for feature examples
4. **Use run scripts** for executing test suites

All scripts are designed to work with the installed code_index package and follow the same configuration patterns as the main CLI tool.