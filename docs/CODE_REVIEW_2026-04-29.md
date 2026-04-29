# Code Review: 2026-04-29

35 findings ranked in logical remediation order. Each finding includes file path, line numbers, severity, description, and suggested fix.

---

## Tier 1: Runtime Failures (fix immediately)

~~### 1. C3 — Bare QdrantClient import defeats graceful fallback~~
**File:** `src/code_index/vector_store.py:8`  
**Severity:** CRITICAL

Line 8 `from qdrant_client import QdrantClient` runs unconditionally and will crash before the conditional import at line 16 has a chance to set `QDRANT_AVAILABLE = False`.

**Fix:** Delete line 8. The conditional import at lines 15-20 already handles both paths.

---

~~### 2. C1 — Missing `__init__.py` in `services/treesitter/`~~
**File:** `src/code_index/services/treesitter/`  
**Severity:** CRITICAL

Seven `.py` files live in this directory with no `__init__.py`. Works as a namespace package on Python 3.3+ but is fragile — any other `treesitter` package on `sys.path` will silently shadow it, causing `ModuleNotFoundError`.

**Fix:** Add an empty `__init__.py`.

---

~~### 3. C4 — Circular import chain~~
**Files:** `src/code_index/chunking.py` ↔ `src/code_index/services/treesitter/tree_sitter_coordinator.py` ↔ `src/code_index/services/treesitter/resource_manager.py`  
**Severity:** CRITICAL

Import cycle: `chunking` → `coordinator` → `chunking` + `resource_manager` → `chunking`. Only works because of guarded late imports. Any eager import path triggers it.

**Fix:** Extract shared classes (`TreeSitterError`, `TreeSitterLanguageError`, `TreeSitterFileTooLargeError`) into a standalone `_exceptions.py` module with zero imports from `chunking`.

---

## Tier 2: Dead Code & Duplication (clean up)

~~### 4. C2 — Duplicate orchestrator classes~~
**Files:** `src/code_index/indexing/orchestrator.py` (234 lines)  
`src/code_index/services/shared/indexing_orchestrator.py`  
**Severity:** CRITICAL

`IndexOrchestrator` in `indexing/orchestrator.py` is dead code — never imported by the main pipeline. `IndexingOrchestrator` in `services/shared/` is the live version. Two copies will diverge.

**Fix:** Delete `indexing/orchestrator.py`.

---

~~### 5. L5 — Unused import `split_content`~~
**File:** `src/code_index/chunking.py:11`  
**Severity:** LOW

`from .utils import split_content` is imported but never used in this file (it is used in `block_extractor.py` and `vector_store.py`).

**Fix:** Remove the import.

---

## Tier 3: Error Handling Robustness

~~### 6. H3 — Call-stack inspection for test detection~~
**File:** `src/code_index/services/treesitter/resource_manager.py:243-269`  
**Severity:** HIGH

Uses `inspect.currentframe().f_back.f_code.co_name` to detect test context. Renaming or refactoring a test silently breaks this.

**Fix:** Inject a `_version_check_strategy` callable as a parameter instead of inspecting the call stack.

---

~~### 7. H4 — `__del__` methods with bare except~~
**Files:** `src/code_index/services/treesitter/resource_manager.py:282-286`  
`src/code_index/chunking.py:174-179`  
**Severity:** HIGH

`__del__` runs during interpreter shutdown when module globals may already be `None`. Bare `except Exception` can mask `ReferenceError`.

**Fix:** Add `None` guards and use `sys.stderr` for logging (logger may be torn down).

---

~~### 8. C5 — MCPErrorHandlerAdapter type mismatch~~
**File:** `src/code_index/mcp_server/server.py:64-101`  
**Severity:** CRITICAL

`MCPErrorHandlerAdapter.handle_error()` returns `ErrorResponse` but the interface it's replacing (`ErrorHandler.handle_error`) has a different signature. `MCPConfigurationManager` is aliased to `ConfigurationService` with incompatible interfaces.

**Fix:** Extract a formal `IErrorHandler` protocol/ABC and have both `ErrorHandler` and `MCPErrorHandlerAdapter` implement it.

---

~~### 9. L7 — Bare `except Exception` in weight functions~~
**File:** `src/code_index/vector_store.py:349-355`  
**Severity:** LOW

`_filetype_weight`, `_path_weight`, `_language_weight`, and `_exclude_match` all catch `Exception` on simple float coercion. Swallows unexpected errors like `AttributeError` (if `self._config` is somehow `None`).

**Fix:** Only catch `(TypeError, ValueError)`.

---

~~### 10. I3 — `print()` instead of `logger.error()`~~
**File:** `src/code_index/cli.py:182`  
**Severity:** INFO

`print(f"Failed to write timeout log to {log_path}: {exc}")` should use the application logger for consistency.

**Fix:** Replace `print` with `logger.error`.

---

## Tier 4: Configuration & Setup

~~### 11. M4 — `object.__setattr__` anti-pattern~~
**File:** `src/code_index/config.py:368-378`  
**Severity:** MEDIUM

Eight `object.__setattr__` calls as a workaround for overridden `__setattr__`.

**Fix:** Store sub-configs in `self._sections: Dict[str, Any] = {}` and delegate via `__getattr__`/`__setattr__` to the dict. Makes serialization trivial.

---

~~### 12. H1 — Unnecessary try/except on property~~
**File:** `src/code_index/embedder.py:20-31`  
**Severity:** HIGH

`model_identifier` wraps a simple string operation in `try/except AttributeError` that can never fire (`self.model` is always initialized in `__init__`). Swallows real errors.

**Fix:** Remove the try/except:
```python
@property
def model_identifier(self) -> str:
    m = (self.model or "")
    return m[:-7] if m.endswith(":latest") else m
```

---

~~### 13. L2 — Hardcoded model→dimension map~~
**File:** `src/code_index/config.py:147-158`  
**Severity:** LOW

Three models hardcoded. New models silently get 768 (fallback). Wrong dimensions cause silent Qdrant/Ollama mismatch.

**Fix:** Fallback to Ollama `/api/show` to query actual dimension, or make `embedding_length` required.

---

~~### 14. L4 — Magic number `fallback_chunk_size`~~
**File:** `src/code_index/services/treesitter/block_extractor.py:216`  
**Severity:** LOW

`getattr(self.config, "fallback_chunk_size", 5)` — no config dataclass defines this attribute. Always defaults to 5.

**Fix:** Add `fallback_chunk_size: int = 5` to `FileHandlingConfig` or `PerformanceConfig`.

---

~~### 15. I4 — Nondeterministic ordering from `set` input~~
**File:** `src/code_index/config.py:106-134`  
**Severity:** INFO

`normalize_ignore_override_patterns` accepts `set` as valid input, but deduplication via `not in normalized` relies on insertion order. Same set can produce different output on different calls.

**Fix:** Sort the result deterministically or document as intentional.

---

## Tier 5: Package & Dependency Hygiene

~~### 16. L9 — Stale duplicate dev dependency groups~~
**File:** `pyproject.toml`  
**Severity:** LOW

Both `[project.optional-dependencies] dev` and `[dependency-groups] dev` exist. `black` and `ruff` appear in different groups. Config drift.

**Fix:** Consolidate into one section. Remove `[dependency-groups]`.

---

~~### 17. I6 — Duplicate Nuitka directives~~
**Files:** `src/code_index/cli.py:15-19`, `src/code_index/mcp_server/server.py:14-18`  
**Severity:** INFO

Identical `# nuitka-project:` directives in two files. If one is updated, the other will drift.

**Fix:** Extract to a shared `.nuitka` config file or document the sync requirement.

---

## Tier 6: Code Organization & Maintainability

~~### 18. M1 — Overly long CLI function~~
**File:** `src/code_index/cli.py:264-426` (165 lines)  
**Severity:** MEDIUM

`_process_single_workspace` has 3 levels of nesting, an inner closure, try/finally, and exception handling. Violates SRP.

**Fix:** Extract TUI setup, result display, and timeout logging into helper functions.

---

~~### 19. M2 — Overly long search method~~
**File:** `src/code_index/services/core/search_service.py:59-286` (228 lines)  
**Severity:** MEDIUM

`search_code` duplicates the same `_error_result` pattern 4+ times. The pattern repeats in `search_similar_files` and `search_by_embedding`.

**Fix:** Extract `_error_result(query, errors, start_time)` helper, or use a decorator. The three methods share ~60% logic — extract the common pipeline.

---

~~### 20. H5 — Nested LRUCache inside SearchService~~
**File:** `src/code_index/services/core/search_service.py:702-740`  
**Severity:** HIGH

40-line class with threading lock, TTL, and ordered-dict management nested inside `SearchService`. Makes `SearchService` a god class.

**Fix:** Extract into `services/shared/lru_cache.py` with a proper public API. Inject as dependency.

---

~~### 21. I5 — Inline extension mapping duplicates LanguageDetector~~
**File:** `src/code_index/services/treesitter/block_extractor.py:274-278`  
**Severity:** INFO

A tiny inline `{py: python, js: javascript, ...}` dict duplicates `LanguageDetector`. Will diverge when the detector is enhanced.

**Fix:** Import and delegate to the canonical `LanguageDetector`.

---

~~### 22. I1 — `_ConfigPath` subclasses `str` with custom `__eq__`~~
**File:** `src/code_index/mcp_server/server.py:46-61`  
**Severity:** INFO

Overriding `__eq__` on a `str` subclass without careful `__hash__` parity can break dict lookups.

**Fix:** Use a `@dataclass` with two `str` fields instead of subclassing `str`.

---

~~### 23. I8 — Direct access to delegate private attributes~~
**File:** `src/code_index/services/treesitter/resource_manager.py:38-47`  
**Severity:** INFO

Accesses `_resources`, `_resource_refs`, `_resource_lock`, `_parsers` directly from delegate services, piercing encapsulation.

**Fix:** Add public accessor methods to `ResourceAllocator`, `ResourceCleanup`, `ResourceMonitor`.

---

## Tier 7: Performance

~~### 24. M3 — `deepcopy(config)` on every dependency load~~
**File:** `src/code_index/services/shared/command_context.py:145-153`  
**Severity:** MEDIUM

Every call to `load_*_dependencies()` does `copy.deepcopy(config)` — O(n) copy of a large nested config. Hot paths (search) feel this.

**Fix:** Use `dataclasses.replace()` on only the affected sub-configs.

---

~~### 25. L11 — Entire file read for MD5 hashing~~
**File:** `src/code_index/indexing/file_processor.py:180-187`  
**Severity:** LOW

`content = f.read()` loads entire file into memory. Concurrent indexing of many 1MB files adds memory pressure.

**Fix:** Stream with incremental `hashlib.md5(f.read(65536))`.

---

~~### 26. L6 — FileProcessingService created per helper call~~
**File:** `src/code_index/cli.py:157-168`  
**Severity:** LOW

Each call to `_load_workspace_list` and `_load_path_list` creates a new `FileProcessingService`. Should be cached.

**Fix:** Extract `FileProcessingService` instantiation to module level or cache it on first use.

---

~~### 27. L8 — `import time` inside method body~~
**Files:** `src/code_index/embedder.py:82`, `src/code_index/vector_store.py:79`  
**Severity:** LOW

`import time` inside method bodies. Trivially hoistable to module level.

**Fix:** Move `import time` to the top of both files.

---

## Tier 8: Correctness

~~### 28. H2 — Contradictory `reset()` + `delete()` on same parser~~
**File:** `src/code_index/services/treesitter/resource_manager.py:214-238`  
**Severity:** HIGH

`_reset_parser` calls `parser.reset()` then `parser.delete()` — mutually exclusive semantics. After `delete()`, the `reset()` was wasted.

**Fix:** If the intent is teardown: remove `reset()`, keep `delete()`. If intent is reset for reuse: remove `delete()`, keep the parser in `_parsers`.

---

~~### 29. M5 — Substring matching for path exclusion~~
**File:** `src/code_index/vector_store.py:383-395`  
**Severity:** MEDIUM

Pattern `"src"` matches `foosrcbar/` or `misc/src-helper/`. Should use glob semantics consistent with `.gitignore`.

**Fix:** Use `fnmatch` or `pathlib.PurePath` matching.

---

~~### 30. L10 — `_is_payload_valid` checks key existence, not type~~
**File:** `src/code_index/vector_store.py:441-447`  
**Severity:** LOW

A payload with `{"filePath": None, "startLine": None}` passes validation, then crashes when `startLine` is used as an integer.

**Fix:** Add `isinstance` assertions: `isinstance(payload.get("filePath"), str)`.

---

~~### 31. L3 — Dot-file check is over-broad~~
**File:** `src/code_index/indexing/file_processor.py:194-196`  
**Severity:** LOW

`any(part.startswith('.') for part in file_path.parts)` skips `.gitignore`, `.env`, and any file in a hidden directory. Only the first component should be checked for dot-directory skip.

**Fix:** Check only the first path part, or make dot-file behavior configurable.

---

### 32. M6 — Fragile workspace isolation via path prefixes
**File:** `src/code_index/vector_store.py:449-534`  
**Severity:** MEDIUM

Workspace isolation relies on path segment prefix filtering + a metadata collection that silently fails on error (line 249: `except Exception as e: ... pass`).

**Fix:** Store `workspace_hash` as a payload field in every Qdrant point and filter on it directly. Remove metadata-collection dependency.

---

## Tier 9: Future Roadmap

### 33. Collection naming strategy
**File:** `src/code_index/vector_store.py`  
**Intent:** Replace opaque `ws-{sha256(path)[:16]}` collection names with user-defined names or folder-name defaults.

**Current:** `ws-{sha256(abspath)[:16]}` — 16-char hex hash, fixed length, opaque.

**Proposed:**
```python
def _collection_name(self, workspace_path: str, user_name: Optional[str] = None) -> str:
    if user_name:
        return f"ws-{sanitize(user_name)}"
    folder = Path(workspace_path).name
    return f"ws-{sanitize(folder)}"
```

Change propagates to:
- `QdrantVectorStore._get_or_create_collection()`
- `CollectionManager` (list, info, delete, prune)
- `SearchService` (workspace resolution)
- Metadata collection schema (store both `collection_name` and `workspace_name`)
- MCP `collections` tool output formatting

---

## Quick Reference: All Items

| # | Tier | Severity | Area | File |
|---|------|----------|------|------|
~~| 1 | Tier 1 | CRITICAL | Import failure | `vector_store.py:8` |~~
~~| 2 | Tier 1 | CRITICAL | Package structure | `services/treesitter/` |~~
~~| 3 | Tier 1 | CRITICAL | Circular import | `chunking.py` ↔ `coordinator.py` |~~
~~| 4 | Tier 2 | CRITICAL | Dead code | `indexing/orchestrator.py` |~~
~~| 5 | Tier 2 | LOW | Unused import | `chunking.py:11` |~~
~~| 6 | Tier 3 | HIGH | Stack inspection | `resource_manager.py:243-269` |~~
~~| 7 | Tier 3 | HIGH | `__del__` safety | `resource_manager.py`, `chunking.py` |~~
~~| 8 | Tier 3 | CRITICAL | Type mismatch | `mcp_server/server.py:64-101` |~~
~~| 9 | Tier 3 | LOW | Bare except | `vector_store.py:349-355` |~~
~~| 10 | Tier 3 | INFO | Print vs logger | `cli.py:182` |~~
~~| 11 | Tier 4 | MEDIUM | Config pattern | `config.py:368-378` |~~
~~| 12 | Tier 4 | HIGH | Dead error guard | `embedder.py:20-31` |~~
~~| 13 | Tier 4 | LOW | Hardcoded map | `config.py:147-158` |~~
~~| 14 | Tier 4 | LOW | Magic number | `block_extractor.py:216` |~~
~~| 15 | Tier 4 | INFO | Nondeterminism | `config.py:106-134` |~~
~~| 16 | Tier 5 | LOW | Dep drift | `pyproject.toml` |~~
~~| 17 | Tier 5 | INFO | Drift risk | `cli.py`, `server.py` |~~
~~| 18 | Tier 6 | MEDIUM | Long function | `cli.py:264-426` |~~
~~| 19 | Tier 6 | MEDIUM | Long function | `search_service.py:59-286` |~~
~~| 20 | Tier 6 | HIGH | God class | `search_service.py:702-740` |~~
~~| 21 | Tier 6 | INFO | Duplicate mapping | `block_extractor.py:274-278` |~~
| 22 | Tier 6 | INFO | `str` subclass | `mcp_server/server.py:46-61` |
~~| 23 | Tier 6 | INFO | Encapsulation | `resource_manager.py:38-47` |~~
~~| 24 | Tier 7 | MEDIUM | Deep copy | `command_context.py:145-153` |~~
~~| 25 | Tier 7 | LOW | Memory | `file_processor.py:180-187` |~~
~~| 26 | Tier 7 | LOW | Redundant init | `cli.py:157-168` |~~
~~| 27 | Tier 7 | LOW | Local import | `embedder.py:82`, `vector_store.py:79` |~~
~~| 28 | Tier 8 | HIGH | Semantics | `resource_manager.py:214-238` |~~
~~| 29 | Tier 8 | MEDIUM | Substring match | `vector_store.py:383-395` |~~
~~| 30 | Tier 8 | LOW | Type check | `vector_store.py:441-447` |~~
~~| 31 | Tier 8 | LOW | Over-broad filter | `file_processor.py:194-196` |~~
| 32 | Tier 8 | MEDIUM | Isolation | `vector_store.py:449-534` |
| 33 | Tier 9 | — | Collection naming | `vector_store.py` (future) |
