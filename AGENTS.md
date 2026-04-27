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
