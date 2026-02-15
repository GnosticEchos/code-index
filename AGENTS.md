# AGENTS.md - Code Index Tool Guidelines

[MODE: RESEARCH] | [MODE: INNOVATE] | [MODE: PLAN] | [MODE: EXECUTE] | [MODE: REVIEW]

## Project Overview
`code-index` is a high-performance semantic code indexing and search system. It leverages **Ollama** for vector embeddings and **Qdrant** for vector storage. The project provides both a **CLI** and an **MCP (Model Context Protocol) server** to enable AI assistants to interact with codebases semantically.

## Core Mandates

### 1. Environment & Tooling
- **Python Version**: **Python 3.13 is MANDATORY**. Python 3.14 is currently unsupported by Nuitka (linking issues like `_Py_TriggerGC`).
- **Dependency Management**: **`uv` is MANDATORY**. Never use `pip` or `venv` directly. Use `uv run` for executing scripts and `uv pip` for management.
- **Build System**: Nuitka 2.7.16+ is used for binary builds. Always use `--lto=no` and `--clang` when building binaries to ensure stability across platforms.

### 2. Architectural Patterns
- **Facade & Orchestration**: 
    - `IndexingService` acts as the primary facade.
    - `IndexingOrchestrator` coordinates the workflow by delegating to specialized services in `src/code_index/indexing/`.
- **Dependency Injection**: Services should accept `IndexingDependencies` or `CommandContext` to facilitate modularity and testability.
- **CQRS Principles**: Maintain clear separation between state-changing commands and data-retrieval queries.
- **MCP Integration**: The MCP server MUST share logic with the CLI via `CommandContext` to ensure behavioral parity. Use `MCPErrorHandlerAdapter` to bridge MCP-specific error reporting with the core `ErrorHandler`.

### Service Size Guidelines
Services should generally stay under 200 lines, but more nuanced limits apply based on service complexity:

**Recommended Service Line Limits:**
- **Core services** (parsers, executors, complex logic): 400-500 lines
- **Simple services** (helpers, caches): 200 lines  
- **Facade/Orchestrator services**: 300 lines

**Conditions to EXCEED the limit:**
1. Multiple API strategies/fallback patterns
2. Complex state management (resource pooling, multi-layer caching)
3. Well-documented with clear docstrings
4. Low cyclomatic complexity (methods are short and focused)
5. Has existing test coverage
6. Single Responsibility Principle is followed (< 20 methods per class)

**Conditions to NOT exceed:**
1. More than 20 methods in a single class
2. Duplicate code exists
3. Mixed responsibilities in one file
4. Difficult to test in isolation

### 3. Coding Standards & Quality
- **Error Handling**: **NEVER** use raw `print()` for errors in service layers. Use the centralized `ErrorHandler` located in `src/code_index/errors.py`.
- **UI & Feedback**: Use the Rich-based TUI components (`ProgressManager`, `FileScroller`, `StatusPanel`) in `src/code_index/ui/` for long-running operations.
- **Logging**: Use structured logging via `logging_utils.py`. Prohibit `print()` in any background or service logic.
- **Formatting**:
    - **Black**: 88 characters line length.
    - **MyPy**: Strict typing where feasible.
    - **Flake8**: Compliance with project linting rules.

### 4. Testing Requirements
- **Framework**: `pytest` with `pytest-asyncio` for async operations.
- **Mocks**: Use dependency injection to supply mocks for `OllamaEmbedder` and `QdrantVectorStore` in unit tests.
- **Coverage**: Every new service or significant refactor must include corresponding tests in the `tests/` directory.

## Implementation Workflow (RIPER-5)
All agents MUST follow the RIPER-5 protocol (RESEARCH, INNOVATE, PLAN, EXECUTE, REVIEW) as defined in the project configuration. Never skip the PLAN mode or move to EXECUTE without explicit user approval.

## Binary Build Configuration
When modifying build scripts, ensure the following Nuitka flags are preserved:
- `--onefile`
- `--clang`
- `--lto=no` (Critical for Python 3.13+ stability)
- `--include-package` for all core dependencies (tree-sitter, qdrant-client, fastmcp, etc.)
