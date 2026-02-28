# Architect Mode Rules (Non-Obvious Only)

- MCP server and CLI MUST share business logic through `CommandContext` — the `MCPErrorHandlerAdapter` bridges MCP's dict-based errors to the core `ErrorResponse` dataclass pattern
- Config priority chain: CLI overrides (100) > workspace config (90) > env vars (80) > config file (70) > defaults (10) — implemented in `ConfigurationService._sources`
- `_ConfigPath` in `server.py` is a `str` subclass that tracks both raw and absolute paths and overrides `__eq__`/`__hash__` — existing code depends on this dual-identity behavior
- The `services/__init__.__getattr__` lazy-loads submodules via `_SUBMODULE_MAP` for backward compatibility — any service reorganization must update this map
- `resource_manager` in the MCP server manages Ollama/Qdrant connection lifecycles via FastMCP's lifespan pattern — connections are registered, not created, by the server
- Service size hard limits exist: < 20 methods/class, simple services ~200 LOC, core services 400-650 LOC max
- All environment variable overrides are validated against an explicit `allowed_keys` whitelist in `ConfigurationService._apply_validated_override` — new config keys must be added there
- Tree-sitter resources have a 30-minute max age (`TREE_SITTER_MAX_RESOURCE_AGE`) — long-running indexing operations recycle parsers
