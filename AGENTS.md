# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Intelligence Mandates (2024-2025 Architecture)
- **Universal Structural Intelligence**: Every code chunk must be relationship-native. Use the 908-record `UniversalSchemaService` to extract `class`, `function`, `import`, and `call` types.
- **Magika Gatekeeper**: Use `MagikaDetector` for AI-driven content identification before applying Tree-sitter parsers.
- **Structural Integrity**: `TreeSitterBlockExtractor` uses modern v0.25.x bindings. Always pass an explicit `Language` object to `RelationshipBlockExtractor`.

## Critical Environment Rules
- **Python 3.13 only** — 3.14 unsupported by Nuitka (linking issues with `_Py_TriggerGC`)
- **`uv` is mandatory** — never use `pip` or `venv` directly; use `uv run` / `uv pip`
- **ABI Constraint**: Pin `tree-sitter-language-pack` to 1.6.2 for Python 3.13 compatibility.

## High-Precision Extraction
- **Unified Schema**: `RelationshipBlockExtractor` categorizes code into 4 classes:
  - `class`: Structural definitions (Structs, Enums, Interfaces, Modules)
  - `function`: Callable logic (Methods, Procedures, Signatures)
  - `import`: Dependency links (Cross-file imports, requires)
  - `call`: Execution links (Method calls, qualified calls)
- **Version-Aware Querying**: Use `tree_sitter.QueryCursor(query).captures(node)` which returns a dict of `{capture_name: [nodes]}`.

## Commands
- Install: `uv pip install -e .`
- Test all: `uv run pytest tests/ -v`
- Test single: `uv run pytest tests/test_treesitter_block_extractor_new.py -v`
- Build binaries: `make build-all` (Builds Linux, macOS, and Windows)

## Non-Obvious Architecture
- **CQRS**: Commands in `services/command/`, queries in `services/query/`.
- **Progress Protocol**: `ProgressManager` enforces a singleton overall bar. File paths must swap in-place to prevent "Double Bar" regression.
- **Universal Forge**: 908 relationship queries live in `src/code_index/queries/queries_minimal.jsonl`.
- **Extraction Result**: `ExtractionResult` must include `high_precision` metadata flag when relationship extraction succeeds.

## Coding Gotchas
- **NEVER** increment `total_extractions` on cache hits in `TreeSitterBlockExtractor`.
- **ABI Safety**: Avoid `_Py_` internal symbols; stay within the public Python C-API for Nuitka stability.
- **Mmap Safety**: `MmapFileProcessor` must handle `PermissionError` and `ValueError` fallbacks gracefully.

## Code Style
- Black 88-char line length, target `py313`.
- Type hints required; use `from __future__ import annotations` for forward refs.
- Documentation: Maintain 1:1 parity between CLI and MCP tool descriptions.

## Testing
- Integration tests requiring external services (Ollama/Qdrant) are marked with `@pytest.mark.integration`
- CI runs exclude integration tests: `pytest -m "not integration"`
- Integration tests that cannot run in CI are skipped with `@pytest.mark.skip` and clear reason

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **code-index** (7403 symbols, 12801 relationships, 221 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/code-index/context` | Codebase overview, check index freshness |
| `gitnexus://repo/code-index/clusters` | All functional areas |
| `gitnexus://repo/code-index/processes` | All execution flows |
| `gitnexus://repo/code-index/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
