# Code Index Tool Project Structure

This document explains the structure of the code index tool project.

## Directory Structure

```
code_index/
├── src/                    # Source code
│   ├── __init__.py        # Package initialization
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Configuration management
│   ├── scanner.py        # Directory scanning
│   ├── parser.py         # Code parsing
│   ├── embedder.py       # Ollama embedding generation
│   ├── vector_store.py   # Qdrant vector storage
│   ├── cache.py          # File hash caching
│   └── utils.py          # Utility functions
├── tests/                # Test files
│   ├── __init__.py
│   ├── test_basic.py     # Basic functionality tests
│   └── test_cli.py       # CLI command tests
├── README.md             # Project overview
├── USAGE.md              # Usage instructions
├── pyproject.toml        # Package configuration
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── Makefile              # Development commands
├── example.py            # Example usage script
├── demonstrate.py        # Demonstration script
├── verify_env.py         # Environment verification
├── test_installation.py  # Installation test
├── setup_dev_env.sh      # Development environment setup
├── install_and_use.sh    # Installation and usage demonstration
└── .gitignore            # Git ignore patterns
```

## Key Components

### src/cli.py
The main command-line interface that provides the `code-index` command with subcommands:
- `index`: Index code files in a workspace
- `search`: Search indexed code files
- `clear`: Clear index data

### src/config.py
Configuration management that handles:
- Ollama settings (base URL, model)
- Qdrant settings (URL, API key)
- Workspace settings (path, file extensions)
- Search parameters (min score, max results)

### src/scanner.py
Directory scanning functionality that:
- Recursively scans directories for files
- Filters files by supported extensions
- Respects .gitignore patterns
- Skips binary files and large files

### src/parser.py
Code parsing functionality that:
- Parses files into code blocks
- Implements simple line-based chunking
- Can be extended with tree-sitter for more sophisticated parsing

### src/embedder.py
Ollama integration that:
- Generates embeddings for text
- Validates Ollama configuration
- Handles API communication

### src/vector_store.py
Qdrant integration that:
- Manages vector collections
- Stores and retrieves embeddings
- Provides search functionality
- Handles file-based point deletion

### src/cache.py
File hash caching that:
- Tracks file changes to avoid reprocessing
- Persists cache to disk
- Manages cache updates and invalidation

### src/utils.py
Utility functions for:
- File hash calculation
- Binary file detection
- .gitignore pattern loading
- File path normalization

## Development Workflow

1. **Setup**: Run `./setup_dev_env.sh` to create a virtual environment and install dependencies
2. **Testing**: Use `make test` to run tests
3. **Linting**: Use `make lint` to check code style
4. **Formatting**: Use `make format` to format code with black
5. **Example**: Run `make example` to see example usage

## Extending the Tool

The tool is designed to be extensible:
- Add new file types by updating the supported extensions list
- Implement more sophisticated parsing by enhancing the parser module
- Add new embedding providers by creating new embedder classes
- Extend CLI functionality by adding new commands to cli.py