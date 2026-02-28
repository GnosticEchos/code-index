# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Critical Environment Rules
- **Python 3.13 only** — 3.14 unsupported by Nuitka (linking issues with `_Py_TriggerGC`)
- **`uv` is mandatory** — never use `pip` or `venv` directly; use `uv run` / `uv pip`
- Nuitka builds require `--lto=no --clang` for Python 3.13+ stability

## Commands
- Install: `uv pip install -e .`
- Test all: `uv run pytest tests/ -v`
- Test single: `uv run pytest tests/test_basic.py::test_config -v`
- Lint: `black --check .` / `flake8` / `mypy`
- Build binaries: `uv run python scripts/build/build_cross_platform.py`

## Non-Obvious Architecture
- CLI and MCP server **share logic** via [`CommandContext`](src/code_index/services/shared/command_context.py) — never duplicate business logic between them
- MCP server uses [`MCPErrorHandlerAdapter`](src/code_index/mcp_server/server.py:36) to bridge MCP errors to core [`ErrorHandler`](src/code_index/errors.py)
- Services use CQRS: commands in `services/command/`, queries in `services/query/`, shared in `services/shared/`
- [`ConfigurationService`](src/code_index/config_service.py) loads config from 5 prioritized sources (CLI > workspace > env > file > defaults)
- `pythonpath` in [`pytest.ini`](pytest.ini:39) adds both `.venv` site-packages AND `src/` — imports use `code_index.*` not `src.code_index.*`

## Coding Gotchas
- **NEVER** use `print()` for errors in service layers — use [`ErrorHandler`](src/code_index/errors.py) and [`logging_utils.py`](src/code_index/logging_utils.py)
- Rich TUI components in `src/code_index/ui/` for progress display — not tqdm in services
- Services accept [`IndexingDependencies`](src/code_index/services/shared/indexing_dependencies.py) or [`CommandContext`](src/code_index/services/shared/command_context.py) — inject mocks for tests
- Constants live in [`constants.py`](src/code_index/constants.py) — don't hardcode timeouts, batch sizes, or thresholds
- Entry points: CLI = `code_index.cli:cli`, MCP = `code_index.mcp_server.server:sync_main`
- `asyncio_mode = auto` in pytest.ini — async tests need no explicit decorator

## Service Size Limits
- Simple services/helpers: ~200 lines
- Core services (parsers, executors): 400-650 lines max
- Hard rule: < 20 methods per class, no mixed responsibilities

## Code Style (non-obvious)
- Black 88-char line length, target `py313`
- Flake8: `max-complexity = 18`, ignores `E203, E501, W503, B950`
- Type hints required; use `from __future__ import annotations` for forward refs
