# Tree-sitter Language Pack Upgrade Analysis (v0.10.0 -> v1.6.2)

## 1. Executive Summary
This document analyzes the transition from the legacy `tree-sitter-language-pack` v0.10.0 to the modern v1.6.2 (and the latest v1.10.x line). The upgrade represents a significant architectural shift from a pre-bundled Python wheel to a high-performance **Rust-powered core** with on-demand parser delivery.

**Primary Goal:** Expand codebase support from ~170 to **305+ languages** while maintaining the high specificity of our current semantic extraction.

---

## 2. Architecture Comparison

| Feature | Legacy (v0.10.0) | Modern (v1.6.2+) | Impact |
| :--- | :--- | :--- | :--- |
| **Parser Delivery** | Bundled `.so` files in Wheel | **On-demand downloads** | Smaller install size; requires first-use network/cache check. |
| **Core Engine** | Pure Python wrapper | **Rust Core (Polyglot)** | Faster parsing and thread-safe execution. |
| **Language Count** | ~170 | **305+** | Massive expansion in "Long Tail" (Astro, Nim, Zig, SurQL). |
| **Primary API** | `get_language()` | `process(source, lang)` | New API provides built-in AST-aware chunking. |

---

## 3. Language Support Matrix & Specificity Delta

This table highlights the transition for key languages and the strategy to avoid losing specificity.

| Language | Current Support (v0.10.0) | v1.6.2 Capability | Upgrade Strategy |
| :--- | :--- | :--- | :--- |
| **TypeScript / TSX** | **High Specificity**: Custom queries for arrow-function assignments. | **Built-in**: Handles standard decls. | **KEEP** custom queries to preserve arrow-function extraction. |
| **Rust** | **High Specificity**: Captures full `impl` and `trait` blocks. | **Built-in**: Focuses on method decls. | **KEEP** custom queries for block-level context (critical for RAG). |
| **Python** | **Medium**: Basic func/class extraction. | **Enhanced**: Automatic decorator/docstring handling. | **ADOPT** new `process()` API or enhance queries with docstring captures. |
| **SurrealDB (.surql)** | **NONE** (Line Fallback) | **NATIVE Support** | **NEW**: Implement queries for `DEFINE`, `SELECT`, and `EVENT`. |
| **Astro** | **NONE** (Line Fallback) | **NATIVE Support** | **NEW**: Extract `frontmatter`, `script`, and `component` blocks. |
| **Nim** | **NONE** | **NATIVE Support** | **NEW**: Extract `proc`, `method`, and `type` blocks. |
| **Bicep / IaC** | **NONE** | **NATIVE Support** | **NEW**: Extract `resource`, `module`, and `output` units. |
| **Zig** | **NONE** | **NATIVE Support** | **NEW**: Extract `fn`, `struct`, and `pub` exports. |

---

## 4. Preserving Specificity (The "No-Loss" Rule)

To ensure we do not lose the "Special Sauce" currently in `src/code_index/treesitter_queries.py`, we will adopt a **Multi-Tier Extraction Strategy**:

### Tier 1: Surgical (Existing)
For languages where we have hand-tuned queries (Python, JS, TS, Rust, Go), we continue to use our existing query strings. The `tree-sitter.Query` object in the new version is fully compatible with our strings.

### Tier 2: Standard (New)
For the 250+ "Long Tail" languages (e.g., Cairo, Bitbake, Nim), we use the new `tsl.process()` API. This provides a baseline level of specificity (functions/classes) that is vastly superior to our current "Line Chunking" fallback.

### Tier 3: Standardized Captures
We should align our capture names with the new v1.6.2 standards to simplify future maintenance:
- `@function` → `@definition.function`
- `@class` → `@definition.class`
- `@method` → `@definition.method`

---

## 5. Required Changes for Support

### A. Parser Lifecycle (`src/code_index/parser_manager.py`)
- **Initialization**: Implement `tsl.init(core_langs)` to pre-download critical parsers during system startup.
- **On-Demand Loading**: Update `get_parser` to handle the asynchronous nature of the first parser download (it is synchronous but involves an IO hit).

### B. Query Integration (`src/code_index/treesitter_queries.py`)
- Replace the `None` values for languages like `zig`, `nim`, and `surql` with active query strings.
- Implement a fallback mechanism: `if custom_query: run_query() else: tsl.process()`.

### C. Dependency Management (`pyproject.toml`)
- Update `tree-sitter-language-pack` to `^1.6.2`.
- Update `tree-sitter` bindings to `^0.25.0`.

---

## 6. Implementation Checklist

1. [ ] **Research Phase**: Finalize the list of "Core 8" languages for pre-downloading.
2. [ ] **Strategy Phase**: Draft the new capture mappings for `surql` and `astro`.
3. [ ] **Execution Phase**: Update `pyproject.toml` and run `uv sync`.
4. [ ] **Execution Phase**: Refactor `ParserManager` to support on-demand caching.
5. [ ] **Execution Phase**: Implement the `Tier 2` (Standard) fallback in `TreeSitterBlockExtractor`.
6. [ ] **Validation Phase**: Run `pytest tests/test_rust_optimizations.py` to ensure no regression in Rust block context.
7. [ ] **Validation Phase**: Add a new test case for `Nim` or `SurQL` to verify the upgrade's success.
