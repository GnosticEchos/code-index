# CLI vs MCP Feature Parity Matrix

| Capability | CLI Support | MCP Support | Gap / Notes | Proposed Resolution |
|------------|-------------|-------------|-------------|---------------------|
| Indexing command availability | `code-index index` with full options | `index` MCP tool | MCP tool omits several CLI overrides due to FastMCP constraints | Add preset profiles or selective overrides (embed timeout, chunking, Tree-sitter toggle) |
| Workspacelist batch indexing | Supported via `--workspacelist` | MCP validator parses `workspacelist` parameter, but execution limited | Need confirmation MCP can iterate multiple workspaces; ensure parity or guide to CLI | If not practical, include CLI guidance when workspacelist > N workspaces |
| Chunking strategy | CLI `--chunking-strategy` + auto Tree-sitter behavior | MCP params exist but limited validation | Align parameter names/descriptions; ensure compatibility with CLI defaults | Document supported combos; add validation mirroring CLI |
| Tree-sitter toggles | CLI exposes `--use-tree-sitter`, skip test/examples, overrides | MCP exposes basic `use_tree_sitter` flag only | Missing granular TS overrides | Either expose limited subset explicitly or guide to CLI for advanced TS config |
| Ignore/Include overrides | CLI uses config overrides (`ignore_override_pattern`, etc.) | MCP removed overrides | Gap: cannot adjust ignore patterns via MCP | Provide curated override options or instruct user to edit config/CLI |
| Embed timeout / performance flags | CLI supports `--embed-timeout`, `--max-file-size`, etc. | MCP only exposes `embed_timeout` | Expand MCP parameter set for critical perf toggles | Prioritize embed timeout + streaming threshold |
| Search min/max score | CLI `--min-score`, `--max-results` | MCP parameters supported via overrides | Parity achieved | N/A |
| Search boosts (file type/path/language) | CLI config/overrides | MCP lacks override access | Users cannot tune boosts via MCP | Add preset search profiles with curated boosts |
| Search cache toggles | CLI config allows enabling cache | MCP currently no cache control | Users cannot enable/disable cache via MCP | Add parameter to toggle cache + TTL |
| Logging / verbosity | CLI `-v/--debug` | MCP limited to server logs | Need consistent diagnostics surface | Provide verbose flag returning metadata in MCP response |
| Collection management commands | CLI `code-index collections ...` | MCP `collections` tool mirrors list/info/delete/clear | Parity mostly achieved | Document that prune not implemented or guide to CLI |
| Error handling guidance | CLI `ErrorHandler` prints actionable tips | MCP `MCPErrorHandler` similar but separate code path | Some messages diverge | Introduce shared helper so both surfaces share text |
| Progress reporting | CLI streaming logs | MCP index tool uses estimator but limited live updates | Search tool lacks progress metadata | Add optional progress callbacks or summary metadata |
| Guided CLI fallback | CLI not needed | MCP lacks automatic suggestions when feature missing | Provide CLI command suggestions in MCP responses | Implement guidance helper |

## Notes
- Matrix derived from `src/code_index/cli.py`, `src/code_index/mcp_server/tools/*.py`, and associated services/tests.
- FastMCP parameter limitations noted in tool docstrings (“Configuration overrides removed due to FastMCP limitations”).
- Some features intentionally CLI-only (e.g., destructive operations) but should emit explicit guidance when invoked through MCP.
