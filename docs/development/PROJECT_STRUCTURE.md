# Code Index Tool Project Structure

This document explains the structure of the code index tool project.

## Directory Structure

```
code_index/
├── src/                    # Source code
│   ├── bin/               # Entry points
│   │   ├── cli_entry.py   # CLI binary entry point
│   │   └── mcp_entry.py   # MCP server binary entry point
│   ├── code_index/        # Main package
│   │   ├── __init__.py    # Package initialization
│   │   ├── cache.py       # File hash caching
│   │   ├── chunking.py    # Code chunking strategies
│   │   ├── cli.py         # Command-line interface
│   │   ├── collections_commands.py # Collections management commands
│   │   ├── collections.py # Collections management
│   │   ├── config_service.py # Configuration service
│   │   ├── config.py      # Configuration management
│   │   ├── embedder.py    # Ollama embedding generation
│   │   ├── enhanced_scanner.py # Enhanced directory scanning
│   │   ├── errors.py      # Error definitions
│   │   ├── fast_language_detector.py # Language detection
│   │   ├── file_processing.py # File processing utilities
│   │   ├── gitignore_manager.py # Gitignore pattern management
│   │   ├── hybrid_parsers.py # Hybrid parsing strategies
│   │   ├── language_detection.py # Language detection
│   │   ├── models.py      # Data models
│   │   ├── parser_manager.py # Parser management
│   │   ├── parser.py      # Code parsing
│   │   ├── path_utils.py  # Path utilities
│   │   ├── query_manager.py # Query management
│   │   ├── scanner.py     # Directory scanning
│   │   ├── service_validation.py # Service validation
│   │   ├── smart_ignore_manager.py # Smart ignore patterns
│   │   ├── treesitter_queries.py # Tree-sitter query management
│   │   ├── utils.py       # Utility functions
│   │   ├── vector_store.py # Qdrant vector storage
│   │   ├── mcp_server/   # MCP server implementation
│   │   │   ├── __init__.py
│   │   │   ├── server.py  # MCP server main
│   │   │   ├── core/      # Core MCP functionality
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config_manager.py
│   │   │   │   ├── error_handler.py
│   │   │   │   ├── operation_estimator.py
│   │   │   │   ├── progress_reporter.py
│   │   │   │   └── resource_manager.py
│   │   │   └── tools/     # MCP tools
│   │   │       ├── __init__.py
│   │   │       ├── collections_tool.py
│   │   │       ├── index_tool.py
│   │   │       └── search_tool.py
│   │   └── services/      # Service layer
│   │       ├── __init__.py
│   │       ├── batch_processor.py
│   │       ├── block_extractor.py
│   │       ├── config_manager.py
│   │       ├── configuration_service.py
│   │       ├── file_processor.py
│   │       ├── indexing_service.py
│   │       ├── query_executor.py
│   │       ├── resource_manager.py
│   │       └── search_service.py
├── tests/                # Test files
│   ├── __init__.py
│   ├── conftest.py       # Test configuration
│   ├── test_*.py         # Various test files
│   └── comprehensive/    # Comprehensive tests
├── docs/                 # Documentation
│   ├── README.md
│   ├── cli-reference.md
│   ├── mcp-server/
│   └── development/
├── scripts/              # Utility scripts
│   ├── build/            # Build scripts
│   ├── run/              # Runtime scripts
│   └── utilities/        # Utility scripts
├── config/               # Configuration examples
├── pyproject.toml        # Package configuration
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── Makefile              # Development commands
├── BINARY_BUILD_README.md # Binary build guide
└── .gitignore            # Git ignore patterns
```

## Key Components

### src/bin/cli_entry.py & src/bin/mcp_entry.py
Entry points for the CLI and MCP server binaries, created using Nuitka for standalone executables.

### src/code_index/cli.py
The main command-line interface that provides the `code-index` command with subcommands:
- `index`: Index code files in a workspace with advanced chunking strategies
- `search`: Search indexed code files with semantic matching
- `collections`: Manage indexed collections (list, info, delete, prune, clear-all)

### src/code_index/config.py & src/code_index/config_service.py
Configuration management that handles:
- Ollama settings (base URL, model, embedding dimensions)
- Qdrant settings (URL, API key)
- Workspace settings (path, file extensions, ignore patterns)
- Search parameters (min score, max results, weighting)
- Tree-sitter settings (chunking limits, language support)

### src/code_index/scanner.py & src/code_index/enhanced_scanner.py
Directory scanning functionality that:
- Recursively scans directories for files
- Filters files by supported extensions and language detection
- Respects .gitignore patterns and smart ignore rules
- Skips binary files and large files
- Supports multiple ignore configuration sources

### src/code_index/parser.py & src/code_index/parser_manager.py
Code parsing functionality that:
- Supports multiple parsing strategies (line-based, token-based, Tree-sitter)
- Implements Tree-sitter integration for semantic code chunking
- Handles language-specific parsing with fallback mechanisms
- Manages parser selection based on file type and configuration

### src/code_index/embedder.py
Ollama integration that:
- Generates embeddings for text chunks
- Validates Ollama configuration and connectivity
- Handles API communication and error recovery
- Supports different embedding models and dimensions

### src/code_index/vector_store.py
Qdrant integration that:
- Manages vector collections with metadata
- Stores and retrieves embeddings with payload data
- Provides semantic search functionality
- Handles collection lifecycle and point management

### src/code_index/cache.py
File hash caching that:
- Tracks file changes to avoid reprocessing
- Persists cache to disk with efficient storage
- Manages cache updates and invalidation
- Supports retry mechanisms for failed operations

### src/code_index/mcp_server/
Model Context Protocol server implementation:
- **server.py**: Main MCP server with tool registration
- **core/**: Core functionality (config management, error handling, progress reporting)
- **tools/**: MCP tool implementations (index, search, collections)

### src/code_index/services/
Service layer providing high-level operations:
- **indexing_service.py**: Orchestrates the indexing process
- **search_service.py**: Handles search operations
- **batch_processor.py**: Manages batch processing
- **file_processor.py**: Processes individual files
- **resource_manager.py**: Manages system resources

### src/code_index/chunking.py
Implements multiple chunking strategies:
- **LineChunkingStrategy**: Simple line-based splitting
- **TokenChunkingStrategy**: Token-aware splitting with overlap
- **TreeSitterChunkingStrategy**: Semantic code structure parsing

### src/code_index/utils.py & src/code_index/path_utils.py
Utility functions for:
- File hash calculation and binary detection
- Path normalization and manipulation
- Gitignore pattern loading and matching
- Language detection and file type handling

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