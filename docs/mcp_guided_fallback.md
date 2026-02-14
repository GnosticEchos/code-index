# MCP Guided Fallback Flow

## Objective
Provide MCP users with clear, actionable guidance whenever a requested operation is better handled by the CLI or requires capabilities not exposed through MCP. This keeps the experience DRY while minimizing confusion.

## Trigger Conditions
1. **Unsupported Parameters**: User supplies options only available via CLI (e.g., advanced ignore overrides, destructive collection operations beyond MCP scope).
2. **Scale Thresholds**: Index tool estimates workspace size beyond MCP comfort (e.g., >1000 files or multi-workspace batches) and recommends CLI for resilience.
3. **Error Scenarios**: Service connectivity failures or validation issues where CLI diagnostic flags would help (verbosity, debug logging).
4. **Explicit Requests**: MCP user asks for operations flagged as CLI-only in parity matrix.

## Response Structure
Each MCP tool response should optionally include a `guidance` array of objects:
```json
{
  "success": false,
  "error": "Parameter validation failed",
  "guidance": [
    {
      "reason": "workspacelist contains 5 entries; batch indexing is more stable via CLI",
      "cli_command": "code-index index --workspacelist /path/to/list.txt --config code_index.json",
      "docs": "docs/cli-reference.md#index-command"
    }
  ]
}
```
- `reason`: short explanation referencing parity matrix.
- `cli_command`: copy-pastable command tailored to current workspace/config.
- `docs`: optional link to relevant documentation section.

## Implementation Steps
1. **Guidance Helper** (`src/code_index/mcp_server/core/guidance.py`):
   - Functions to build CLI commands using current parameters.
   - Templates per tool (index/search/collections).
2. **Tool Integration**:
   - Index/Search/Collections tools call helper whenever trigger condition met.
   - Merge guidance into responses without altering existing success payloads.
3. **Parity Matrix Hook**:
   - Annotate each row in `docs/cli_vs_mcp_parity.md` with `guidance_id` to keep maintenance DRY.
   - Guidance helper references matrix metadata to keep messaging consistent.
4. **Testing**:
   - Extend MCP tool tests to assert guidance emitted for known gaps (e.g., advanced ignore overrides request).
   - Snapshot recommended CLI commands for stability.

## Documentation Updates
- Update `docs/cli_vs_mcp_parity.md` to mention guidance flow.
- Mention in `docs/mcp_search_enhancements.md` (diagnostics section) that verbose mode lists guidance reasons when fallback recommended.
- Add FAQ entry: “When MCP suggests using CLI” with examples.
