# Ask Mode Rules (Non-Obvious Only)

- `src/code_index/` is the package root but imports use `code_index.*` (not `src.code_index.*`) because `src/` is on `pythonpath` via `pytest.ini`
- `services/` has 6 sub-packages: `core/`, `command/`, `query/`, `batch/`, `embedding/`, `treesitter/`, `shared/` — the `__init__.py` re-exports everything with a backward-compat `_SUBMODULE_MAP`
- `config_service.py` (ConfigurationService) is the real config loader; `config.py` (Config class) is just the data model — don't confuse them
- Two separate search paths exist: `src/code_index/search/` (strategy pattern for search) vs `services/core/search_service.py` (the facade)
- `models.py` contains all result dataclasses (`IndexingResult`, `SearchResult`, `SearchMatch`, etc.) — not in the services that use them
- The MCP server entry point `sync_main()` parses `--config`/`-c` from `sys.argv` only when called with default `config_path` — programmatic calls bypass this
- `code_index.json` is the default config filename, but workspace-specific overrides also check `.code_index.json`, `.code_index.yaml`, `.code_index.yml`
