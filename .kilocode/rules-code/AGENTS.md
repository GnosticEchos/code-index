# Code Mode Rules (Non-Obvious Only)

- Always inject dependencies via `CommandContext` or `IndexingDependencies` — never instantiate `OllamaEmbedder`/`QdrantVectorStore` directly in service logic
- Use `ErrorHandler.handle_error()` with `ErrorContext(component=..., operation=...)` — raw exceptions must not leak to CLI/MCP output
- `ConfigurationService` caches by key `config_path:workspace_path:hash(overrides)` — call `clear_cache()` if config changes mid-session
- The `services/__init__.py` has a `_SUBMODULE_MAP` for backward-compat imports — add new services there when reorganizing
- `push_logging_context()` / `reset_logging_context()` from `logging_utils.py` must wrap file processing to inject `current_file` and `current_language` into log records
- Tree-sitter chunk strategy requires `use_tree_sitter=True` AND `chunking_strategy="treesitter"` — setting only one silently fails validation
- All path operations must go through `PathUtils` which validates paths stay within workspace boundaries
- Test fixtures: use `ConfigurationService(test_mode=True)` to skip actual Ollama/Qdrant connectivity checks
