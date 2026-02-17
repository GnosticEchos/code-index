"""
Query result formatting service for Tree-sitter queries.

This module provides utilities for formatting and summarizing
query results for logging and debugging.
"""

import json
import logging
import traceback
from typing import List, Optional, Dict, Any, Tuple


def _safe_len(x) -> Optional[int]:
    """Safely get the length of an object."""
    try:
        return len(x)  # type: ignore[arg-type]
    except Exception:
        return None


def _summarize_capture_tuples(items, max_items: int = 3) -> List[Dict[str, Any]]:
    """Summarize capture tuple results."""
    summary: List[Dict[str, Any]] = []
    try:
        if not items:
            return summary
        count = 0
        for it in items:
            if isinstance(it, (tuple, list)) and len(it) >= 2:
                node = it[0]
                name = it[1]
            else:
                node = getattr(it, "node", None)
                name = getattr(it, "name", getattr(it, "index", None))
            node_type = None
            start = None
            end = None
            try:
                node_type = getattr(node, "type", None) or type(node).__name__
            except Exception:
                node_type = None
            try:
                start = getattr(node, "start_point", None)
            except Exception:
                start = None
            try:
                end = getattr(node, "end_point", None)
            except Exception:
                end = None
            summary.append({
                "name": str(name),
                "node_type": str(node_type) if node_type is not None else None,
                "start": start,
                "end": end,
            })
            count += 1
            if count >= max_items:
                break
    except Exception:
        pass
    return summary


def _summarize_capture_dicts(items, max_items: int = 3) -> List[Dict[str, Any]]:
    """
    Summarize mapping-like capture results. Supports:
    - dict[str, list[node]]
    - list[{'captures': dict[str, node or list[node]]}, ...]
    """
    summary: List[Dict[str, Any]] = []
    try:
        # Mapping form
        if hasattr(items, "items"):
            count = 0
            for k, v in list(items.items())[:max_items]:
                summary.append({"names": [str(k)], "count": _safe_len(v)})
                count += 1
                if count >= max_items:
                    break
            return summary
        # Sequence of match dicts with 'captures'
        if isinstance(items, (list, tuple)):
            count = 0
            for m in items:
                caps = None
                if isinstance(m, dict) and isinstance(m.get("captures"), dict):
                    caps = m.get("captures")
                elif hasattr(m, "captures") and isinstance(getattr(m, "captures"), dict):
                    caps = getattr(m, "captures")
                if isinstance(caps, dict):
                    names = [str(n) for n in list(caps.keys())[:max_items]]
                    try:
                        c = sum((_safe_len(v) or 1) for v in caps.values())
                    except Exception:
                        c = _safe_len(caps) or None
                    summary.append({"names": names, "count": c})
                    count += 1
                    if count >= max_items:
                        break
    except Exception:
        pass
    return summary


def _tb_excerpt(exc: BaseException, limit: int = 4) -> str:
    """Get a compact traceback excerpt."""
    try:
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__, limit=limit)
        if tb_lines and len(tb_lines) > 0:
            excerpt = "".join(tb_lines[-limit:])
            return " ".join(excerpt.split())
    except Exception:
        pass
    return f"{type(exc).__name__}: {exc}"


class AttemptRecord:
    """Record of a query execution attempt."""
    def __init__(self, name: str, call: str, available: Optional[bool] = None,
                 outcome: str = "unknown", length: Optional[int] = None,
                 sample: Optional[Any] = None, exc_type: Optional[str] = None,
                 exc_msg: Optional[str] = None, tb_excerpt: Optional[str] = None):
        self.name = name
        self.call = call
        self.available = available
        self.outcome = outcome
        self.length = length
        self.sample = sample
        self.exc_type = exc_type
        self.exc_msg = exc_msg
        self.tb_excerpt = tb_excerpt


def _log_attempts(logger: logging.Logger, attempts: List[AttemptRecord], 
                  level: int = logging.WARNING) -> None:
    """Log query execution attempts."""
    # Compact JSON line
    compact: List[Dict[str, Any]] = []
    for a in attempts or []:
        compact.append({
            "name": a.name,
            "outcome": a.outcome,
            "length": a.length,
            "exc_type": a.exc_type,
        })
    try:
        compact_json = json.dumps(compact, ensure_ascii=False)
    except Exception:
        compact_json = "[]"
    
    logger.log(level, f"[PARSING] All query APIs failed | Component: query_executor, Operation: execute_query | attempts_compact={compact_json}")
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Attempt breakdown (detailed):")
        for a in attempts or []:
            try:
                from dataclasses import asdict
                sanitized = asdict(a)
                if sanitized.get("sample") is not None:
                    sanitized["sample"] = repr(sanitized["sample"])[:400]
                logger.debug(json.dumps(sanitized, ensure_ascii=False, indent=2))
            except Exception:
                logger.debug(f"{a.name} | outcome={a.outcome} | length={a.length} | exc={a.exc_type}:{a.exc_msg}")


class QueryResultFormatter:
    """
    Service for formatting query execution results.
    
    Handles:
    - Capture result normalization
    - Result summarization
    - Error formatting
    """
    
    def __init__(self):
        """Initialize the QueryResultFormatter."""
        pass
    
    def normalize_capture_results(self, capture_results: List, query) -> List[Tuple[Any, str]]:
        """
        Normalize capture results to consistent format.
        
        Args:
            capture_results: Raw capture results from query execution
            query: Compiled query object
            
        Returns:
            List of (node, capture_name) tuples
        """
        normalized = []
        
        for capture in capture_results:
            try:
                if isinstance(capture, tuple) and len(capture) == 2:
                    node, name = capture
                    normalized.append((node, name))
                elif hasattr(capture, 'node') and hasattr(capture, 'index'):
                    node = capture.node
                    cap_idx = capture.index
                    name = self._get_capture_name(query, cap_idx, node)
                    normalized.append((node, name))
                elif isinstance(capture, dict) and 'node' in capture and 'name' in capture:
                    normalized.append((capture['node'], capture['name']))
            except Exception:
                continue
        
        return normalized
    
    def _get_capture_name(self, query, cap_idx: int, node) -> str:
        """Resolve a capture name across py-tree-sitter API variants."""
        try:
            # Preferred modern API
            if hasattr(query, "capture_name"):
                try:
                    return query.capture_name(cap_idx)  # type: ignore[attr-defined]
                except Exception:
                    pass
            # Legacy/common API
            names = getattr(query, "capture_names", None)
            if names:
                try:
                    return names[cap_idx]
                except Exception:
                    pass
        except Exception:
            pass
        
        # Final fallbacks
        try:
            return getattr(node, "type", str(cap_idx))
        except Exception:
            return str(cap_idx)
    
    def format_captures(self, capture_results) -> List[Dict[str, Any]]:
        """Format capture results for display."""
        if hasattr(capture_results, "items"):
            return _summarize_capture_dicts(capture_results)
        return _summarize_capture_tuples(capture_results)
