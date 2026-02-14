# MCP Search Enhancements Design

## Goals
1. Preserve DRY/CQRS principles by reusing `CommandContext` and `SearchService` while exposing user-friendly controls in MCP.
2. Prioritize search robustness (configurability, diagnostics) since MCP’s primary value is interactive search.
3. Respect FastMCP parameter limits by using curated profiles/presets instead of dumping every CLI flag.

## Proposed Enhancements

### 1. Search Profiles
- **Concept:** Offer a `profile` parameter (e.g., `"default"`, `"broad"`, `"strict"`).
- **Mapping:** Each profile translates to specific overrides (min score, boost presets) via `build_search_overrides` or new helper.
- **Implementation Hooks:**
  - Update `search_tool.py` to accept `profile` (validated enum) and merge with explicit `min_score`/`max_results` if provided.
  - Store presets centrally (e.g., `src/code_index/search_profiles.py`) to keep CLI/MCP parity.

### 2. Cache Control Parameters
- **Need:** CLI config now supports search cache; MCP should toggle it.
- **Plan:**
  - Add optional params `cache_enabled: bool` and `cache_ttl_seconds: int` to MCP tool.
  - Pass through `CommandContext.load_search_dependencies` via overrides or temporary config mutation.
  - Responses should echo whether cache was used (see diagnostics section).

### 3. Diagnostics / Verbose Flag
- **Purpose:** Mirror CLI `--debug` insights.
- **Approach:** optional `verbose: bool` parameter causing response to include:
  - `collection_name`, `workspace_path` used.
  - Effective `min_score`, `max_results`, profile name.
  - Cache hit/miss info (needs SearchService to expose via return metadata or log hook).
- **Implementation Idea:** Extend `SearchResult` with `diagnostics` dict or wrap MCP response with `metadata` block.

### 4. Error Guidance Unification
- **Current State:** `MCPErrorHandler` vs CLI `ErrorHandler` produce similar but diverging text.
- **Action:**
  - Extract shared helper (e.g., `errors/guidance.py`) returning actionable bullet lists.
  - CLI `ErrorHandler` and MCP adapter both consume helper to ensure identical guidance.

### 5. Parameter Validation Parity
- **Additions:**
  - Reuse CLI validators (e.g., min/max score bounds) inside MCP tool to avoid duplication.
  - When invalid, return structured errors referencing CLI help if relevant.

### 6. Streaming / Partial Results (Future)
- **Idea:** Provide optional `stream: bool` to emit batches via FastMCP context `ctx.send_event`. Requires further FastMCP support; note as stretch goal.

## File Touchpoints
- `src/code_index/mcp_server/tools/search_tool.py` (parameter parsing, response metadata)
- `src/code_index/services/search_service.py` (expose diagnostics, cache hit info)
- `src/code_index/search_profiles.py` (new helper)
- `src/code_index/errors/guidance.py` (shared messaging)
- Tests: `tests/test_mcp_server.py`, `tests/test_mcp_integration.py`, `tests/test_search_service.py`
