# Debug Mode Rules (Non-Obvious Only)

- Enable verbose logging: `code-index --debug index ...` sets root logger to DEBUG; use `--log-treesitter` / `--log-embedding` for targeted subsystem logging
- Processing progress logger (`code_index.processing`) has `propagate=False` and its own handler — it won't appear in root logger output
- `LoggingContextFilter` injects `%(current_file)s` and `%(current_language)s` into log records — check these fields for file-specific debugging
- MCP server logs to stderr only (`logging.StreamHandler(sys.stderr)`) — stdout is reserved for MCP protocol messages
- pytest cache is at `/tmp/pytest_cache` (not default `.pytest_cache`) — set in `pytest.ini`
- `ConfigurationService` has a `DEBUG: Explicit config path` print statement left in `_apply_workspace_config` — this is an accidental debug print, not a feature
- `ServiceValidator` connectivity checks are skipped when `test_mode=True` or `skip_service_validation=True` — errors during tests may indicate these flags are missing
- Tests use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.mcp` — use `-m` to filter
