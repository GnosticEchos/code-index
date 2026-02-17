"""Helpers for building configuration override dictionaries for CLI and MCP."""

from __future__ import annotations

from typing import Dict, Optional


def build_index_overrides(
    *,
    embed_timeout: Optional[int] = None,
    timeout_log: Optional[str] = None,
    ignore_config: Optional[str] = None,
    ignore_override_pattern: Optional[str] = None,
    auto_ignore_detection: Optional[bool] = None,
    use_tree_sitter: Optional[bool] = None,
    chunking_strategy: Optional[str] = None,
) -> Dict[str, object]:
    overrides: Dict[str, object] = {}

    if embed_timeout is not None:
        overrides["embed_timeout_seconds"] = embed_timeout
    if timeout_log:
        overrides["timeout_log_path"] = timeout_log
    if ignore_config:
        overrides["ignore_config_path"] = ignore_config
    if ignore_override_pattern:
        overrides["ignore_override_pattern"] = ignore_override_pattern
    if auto_ignore_detection is not None:
        overrides["auto_ignore_detection"] = auto_ignore_detection

    if use_tree_sitter:
        overrides["use_tree_sitter"] = True
        overrides["chunking_strategy"] = "treesitter"
    elif chunking_strategy:
        overrides["chunking_strategy"] = chunking_strategy

    return overrides


def build_search_overrides(
    *,
    min_score: Optional[float] = None,
    max_results: Optional[int] = None,
) -> Dict[str, object]:
    overrides: Dict[str, object] = {}

    if min_score is not None:
        overrides["search_min_score"] = min_score
    if max_results is not None:
        overrides["search_max_results"] = max_results

    return overrides
