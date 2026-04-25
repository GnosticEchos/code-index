# Code Index Tool Project Structure

This document explains the current structure of the Code Index Tool project.

## Directory Structure

```
code_index/
├── src/                      # Source code
│   └── code_index/           # Main package
│       ├── __init__.py       # Package initialization
│       ├── cli.py            # Command-line interface (entry point)
│       ├── config.py         # Configuration management (dataclasses)
│       ├── embedder.py       # Ollama embedding generation
│       ├── vector_store.py   # Qdrant vector storage and search
│       ├── chunking.py       # Code chunking strategies (line, token, treesitter)
│       ├── utils.py          # Utility functions (hashing, binary detection)
│       ├── smart_ignore_manager.py  # Ignore pattern management
│       ├── treesitter_queries.py    # Tree-sitter query definitions
│       │
│       ├── indexing/         # Indexing subsystem
│       │   ├── __init__.py
│       │   ├── orchestrator.py      # Coordinates indexing workflow
│       │   ├── file_processor.py    # Processes individual files
│       │   ├── batch_manager.py     # Batch processing logic
│       │   ├── language_detector.py # Language detection
│       │   ├── progress_tracker.py  # Progress reporting
│       │   ├── error_recovery.py    # Error handling and recovery
│       │   └── __init__.py
│       │
│       ├── search/           # Search subsystem
│       │   ├── __init__.py
│       │   ├── embedding_generator.py         # Generates query embeddings
│       │   ├── similarity_search_strategy.py  # Vector similarity search
│       │   ├── text_search_strategy.py        # Full-text fallback
│       │   ├── embedding_search_strategy.py   # Combined search
│       │   ├── result_processor.py            # Post-processing and ranking
│       │   ├── strategy_factory.py            # Strategy selection
│       │   ├── validation_service.py          # Search validation
│       │   └── query_cache.py                 # Caching for search
│       │
│       ├── services/         # Service layer (business logic)
│       │   ├── __init__.py   # Re-exports services via _SUBMODULE_MAP
│       │   │
│       │   ├── core/         # Core services
│       │   │   ├── configuration_service.py  # Config loading/validation
│       │   │   ├── indexing_service.py       # High-level indexing operations
│       │   │   └── search_service.py          # High-level search operations
│       │   │
│       │   ├── query/        # Query services
│       │   │   ├── query_compiler.py          # Compiles queries
│       │   │   ├── query_embedding_cache.py   # Caches embeddings
│       │   │   ├── query_result_formatter.py  # Formats results
│       │   │   ├── configuration_query_service.py  # Config queries
│       │   │   └── query_cache.py             # Generic query caching
│       │   │
│       │   ├── shared/       # Shared utilities
│       │   │   ├── command_context.py         # Context for command execution
│       │   │   ├── indexing_dependencies.py   # Dependency injection
│       │   │   ├── indexing_orchestrator.py   # Orchestrates indexing
│       │   │   ├── file_processing_helpers.py # File processing utilities
│       │   │   ├── filter_builder.py          # Builds file filters
│       │   │   ├── path_resolver.py           # Path resolution utilities
│       │   │   ├── resource_allocator.py      # Resource allocation
│       │   │   ├── resource_monitor.py        # Resource monitoring
│       │   │   ├── resource_cleanup.py        # Resource cleanup
│       │   │   ├── result_ranker.py           # Ranks search results
│       │   │   ├── search_cache.py            # Search result caching
│       │   │   ├── search_result_processor.py # Processes search results
│       │   │   ├── search_strategy_selector.py # Selects search strategy
│       │   │   ├── workspace_service.py       # Workspace operations
│       │   │   └── health_service.py          # Health checks
│       │   │
│       │   └── treesitter/   # Tree-sitter specialized services
│       │       ├── block_extractor.py    # Extracts code blocks
│       │       ├── block_parser.py       # Parses code blocks
│       │       ├── block_filter.py       # Filters extracted blocks
│       │       ├── file_processor.py     # Tree-sitter file processing
│       │       ├── relationship_extractor.py  # Extracts relationships
│       │       ├── resource_manager.py   # Manages Tree-sitter resources
│       │       ├── tree_sitter_coordinator.py # Coordinates parsing
│       │       └── treesitter_file_processor.py # File-level processing
│       │
│       ├── mcp_server/       # Model Context Protocol server
│       │   ├── __init__.py
│       │   ├── server.py     # MCP server main entry point
│       │   │
│       │   ├── core/         # Core MCP functionality
│       │   │   ├── config_manager.py      # MCP configuration
│       │   │   ├── config_persistence.py  # Config storage
│       │   │   ├── config_validator.py    # Config validation
│       │   │   ├── error_handler.py       # Error handling
│       │   │   ├── operation_estimator.py # Operation estimation
│       │   │   ├── progress_reporter.py   # Progress reporting
│       │   │   ├── resource_manager.py    # Resource lifecycle
│       │   │   ├── mcp_memory_manager.py  # Memory management
│       │   │   ├── mcp_resource_models.py # Data models
│       │   │   └── mcp_resource_utils.py  # Resource utilities
│       │   │
│       │   └── tools/        # MCP tool implementations
│       │       ├── index_tool.py       # Index tool (with estimation)
│       │       ├── search_tool.py      # Search tool
│       │       └── collections_tool.py  # Collections management tool
│       │
│       ├── collections.py    # Collection manager (Qdrant collections)
│       ├── cache.py          # File hash caching
│       ├── errors.py         # Error definitions
│       ├── models.py         # Data models and dataclasses
│       ├── path_utils.py     # Path utilities
│       ├── service_validation.py  # Service validation
│       ├── helptree_handler.py    # Help tree generation
│       ├── ui/               # User interface components
│       │   ├── progress_manager.py  # Progress bar management
│       │   ├── status_panel.py      # Status display
│       │   ├── file_scroller.py     # File scrolling UI
│       │   ├── tui_integration.py   # Terminal UI integration
│       │   └── __init__.py
│       │
│       └── queries/          # Tree-sitter query definitions
│           └── queries_minimal.jsonl  # 908 relationship queries
│
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   ├── test_*.py            # Unit and integration tests
│   └── comprehensive/       # Comprehensive test suites
│
├── docs/                    # Documentation
│   ├── README.md
│   ├── cli-reference.md     # Complete CLI reference
│   ├── configuration-schema.md  # Configuration documentation
│   ├── language-support.md  # Supported languages
│   ├── mcp-server/          # MCP server documentation
│   │   ├── README.md
│   │   ├── api-reference.md
│   │   ├── configuration-examples.md
│   │   └── troubleshooting.md
│   └── development/         # Developer documentation
│       ├── GETTING_STARTED.md
│       └── PROJECT_STRUCTURE.md  # This file
│
├── scripts/                 # Utility scripts
│   ├── setup_venv.sh        # Virtual environment setup
│   └── run_search_validation.sh  # Search validation runner
│
├── pyproject.toml           # Project metadata and dependencies
├── requirements.txt         # Production dependencies (legacy)
├── requirements-dev.txt    # Development dependencies (legacy)
├── uv.lock                 # uv lock file (current)
├── README.md               # Project README
├── AGENTS.md               # Agent guidelines
└── .kilocode/              # KiloCode configuration
    └── rules-*/            # Mode-specific agent rules
```

## Architecture Overview

The Code Index Tool follows a modern service-oriented architecture with clear separation of concerns:

### Entry Points

- **CLI**: `src/code_index/cli.py` - Main command-line interface providing `code-index` commands
- **MCP Server**: `src/code_index/mcp_server/server.py` - Model Context Protocol server

### Core Components

#### Configuration (`config.py`, `services/core/configuration_service.py`)
Centralized configuration management using dataclasses with eight domain-specific sections:
- `core`: Workspace paths, Ollama/Qdrant connection settings
- `files`: File handling (extensions, size limits)
- `ignore`: Ignore pattern configuration
- `chunking`: Chunking strategy and parameters (including `auto_extensions`)
- `tree_sitter`: Tree-sitter parsing configuration
- `search`: Search behavior and scoring
- `performance`: Performance tuning
- `logging`: Log level configuration

Configuration resolution order: CLI flags → Environment variables → Workspace config (`code_index.json`) → Defaults.

#### Indexing Pipeline (`indexing/` subsystem)
```
Orchestrator → FileProcessor → ChunkingStrategy → Embedder → VectorStore
```
- **Orchestrator**: Coordinates the indexing workflow, manages batch processing
- **FileProcessor**: Scans directories, filters files, applies ignore rules
- **Chunking**: Three strategies: LineChunkingStrategy, TokenChunkingStrategy, TreeSitterChunkingStrategy
- **Embedder**: OllamaEmbedder generates embeddings with timeout handling
- **VectorStore**: QdrantVectorStore manages collections and point upserts

#### Search Pipeline (`search/` subsystem)
```
Query → EmbeddingGenerator → StrategySelector → SearchExecution → ResultProcessor
```
- **EmbeddingGenerator**: Converts queries to vectors
- **StrategySelector**: Chooses between vector, text, or hybrid search
- **ResultProcessor**: Applies file type weights, path boosts, language boosts, formats output

#### Services Layer (`services/`)
Business logic organized by domain:
- **Core services**: Configuration, indexing, search (high-level operations)
- **Query services**: Query compilation, caching, result formatting
- **Shared services**: Common utilities (dependency injection, filtering, monitoring)
- **Tree-sitter services**: Specialized semantic parsing services

#### MCP Server (`mcp_server/`)
Model Context Protocol integration:
- **Server**: FastMCP-based server with tool registration
- **Core**: Configuration, error handling, progress reporting, operation estimation
- **Tools**: `index_tool`, `search_tool`, `collections_tool` - MCP wrappers around core services

### Key Implementation Details

- **Tree-sitter**: Uses `tree-sitter-language-pack` v1.6.2 (Python 3.13 compatible). Parser resources have a 30-minute max age (`TREE_SITTER_MAX_RESOURCE_AGE = 1800`) and are recycled during long-running operations.
- **Caching**: Multi-level caching (file hash cache, query embedding cache, search result cache)
- **Progress Reporting**: Singleton progress bar via `ProgressManager` with in-place path swapping
- **Error Handling**: Structured error responses with actionable guidance via `ErrorHandler`
- **Validation**: Configuration validated at load time; embedding dimensions auto-detected based on model name

### Data Flow

**Indexing:**
1. CLI/MCP receives `index` command
2. Configuration loaded and validated
3. Workspace scanned with ignore filtering
4. Files chunked according to strategy
5. Embeddings generated via Ollama
6. Vectors upserted to Qdrant with metadata payloads
7. Cache updated for processed files

**Search:**
1. CLI/MCP receives `search` command
2. Query embedded using same model
3. Qdrant similarity search executed
4. Results weighted by file type, path, language
5. Snippets generated and formatted
6. Returned with scores and metadata

## Development Notes

- **Python version**: 3.13 only (3.14 incompatible with Nuitka)
- **Package manager**: `uv` mandatory (no direct `pip` usage)
- **Line length**: Black formatter with 88-character limit
- **Type hints**: Required throughout; use `from __future__ import annotations`
- **Testing**: `uv run pytest tests/ -v`
- **Binary builds**: `make build-all` (requires Nuitka)
