"""
QueryCursor execution patterns for Tree-sitter queries.
"""
from typing import List, Tuple, Any
from .query_result_formatter import _safe_len, _summarize_capture_tuples, _summarize_capture_dicts, _tb_excerpt, AttemptRecord


class QueryCursorExecutor:
    """Executes queries using QueryCursor API with multiple patterns."""
    
    def __init__(self, debug_enabled: bool = False):
        self.debug_enabled = debug_enabled
    
    def _record(self, executor, attempt):
        try:
            if not hasattr(executor, "_cursor_attempt_records"):
                executor._cursor_attempt_records = []
            executor._cursor_attempt_records.append(attempt)
        except:
            pass
    
    def exec_p1(self, q, rn, QC, ex):
        """Pattern 1: cursor.exec(); cursor.captures()"""
        c = QC()
        c.exec(q, rn)
        r = []
        try:
            for cap in c.captures():
                p = ex._process_cursor_capture(q, cap)
                if p:
                    r.append(p)
            self._record(ex, AttemptRecord("QueryCursor.captures(list)", "QC().captures()", True, "success" if r else "empty", _safe_len(r), _summarize_capture_tuples(r)))
        except Exception as e:
            self._record(ex, AttemptRecord("QueryCursor.captures(list)", "QC().captures()", True, "exception", exc_type=type(e).__name__, tb_excerpt=_tb_excerpt(e)))
        return r

    def exec_p2(self, q, rn, QC, ex):
        """Pattern 2: cursor.captures(node, query)"""
        c = QC()
        r = []
        try:
            items = c.captures(rn, q)
            for cap in items:
                p = ex._process_cursor_capture(q, cap)
                if p:
                    r.append(p)
            d = hasattr(items, "items")
            self._record(ex, AttemptRecord("QueryCursor.captures(dict)" if d else "QueryCursor.captures(list)", "captures(rn,q)", True, "success" if r else "empty", _safe_len(items), _summarize_capture_dicts(items) if d else _summarize_capture_tuples(r)))
        except Exception as e:
            self._record(ex, AttemptRecord("QueryCursor.captures", "captures(rn,q)", True, "exception", exc_type=type(e).__name__, tb_excerpt=_tb_excerpt(e)))
        return r

    def exec_p3(self, q, rn, QC, ex):
        """Pattern 3: QueryCursor(query, node)"""
        c = QC(q, rn)
        r = []
        try:
            for cap in c:
                p = ex._process_cursor_capture(q, cap)
                if p:
                    r.append(p)
            self._record(ex, AttemptRecord("QueryCursor.__iter__", "QC(q,rn)", True, "success" if r else "empty", _safe_len(r), _summarize_capture_tuples(r)))
        except Exception as e:
            self._record(ex, AttemptRecord("QueryCursor.__iter__", "QC(q,rn)", True, "exception", exc_type=type(e).__name__, tb_excerpt=_tb_excerpt(e)))
        return r

    def exec_p4(self, q, rn, QC, ex):
        """Pattern 4: matches() then captures() fallback"""
        try:
            c = QC(q)
        except:
            try:
                c = QC()
            except:
                return []
        r = []
        lab = "QM.matches"
        try:
            if not hasattr(c, 'matches'):
                raise AttributeError("no matches")
            items = c.matches(rn)
            lab = "QM.matches(dict)" if (isinstance(items, dict) or (hasattr(items, "__iter__") and items and isinstance(list(items)[0], dict))) else "QM.matches(list)"
            if hasattr(items, "__iter__"):
                for m in items if isinstance(items, (list, tuple)) else items:
                    if isinstance(m, dict) and isinstance(m.get("captures"), dict):
                        for cn, node in (m.get("captures") or {}).items():
                            if str(cn).endswith(".name"):
                                r.append((node, str(cn).split(".", 1)[0]))
                    elif hasattr(m, "items"):
                        cm = m[1] if isinstance(m, (list, tuple)) and len(m) >= 2 else getattr(m, "captures", {})
                        if isinstance(cm, dict):
                            for cn, nodes in cm.items():
                                if str(cn).endswith(".name"):
                                    for n in (nodes or []):
                                        r.append((n, str(cn).split(".", 1)[0]))
                    else:
                        for cap in getattr(m, "captures", []):
                            p = ex._process_cursor_capture(q, cap)
                            if p:
                                r.append(p)
            self._record(ex, AttemptRecord(lab, "QM().matches(rn)", True, "success" if r else "empty", _safe_len(r), _summarize_capture_dicts(items) if "dict" in lab else _summarize_capture_tuples(r)))
        except Exception as e:
            self._record(ex, AttemptRecord("QM.matches", "QM().matches(rn)", True, "exception", exc_type=type(e).__name__, tb_excerpt=_tb_excerpt(e)))
        if not r:
            try:
                items = c.captures(rn)
                if hasattr(items, "items"):
                    for cn, nodes in items.items():
                        if str(cn).endswith(".name"):
                            for n in (nodes or []):
                                r.append((n, str(cn).split(".", 1)[0]))
                    self._record(ex, AttemptRecord("QM.captures(dict)", "QC().captures(rn)", True, "success" if r else "empty", _safe_len(r), _summarize_capture_dicts(items)))
                else:
                    for cap in items if isinstance(items, (list, tuple)) else items:
                        p = ex._process_cursor_capture(q, cap)
                        if p:
                            r.append(p)
                    self._record(ex, AttemptRecord("QM.captures(list)", "QC().captures(rn)", True, "success" if r else "empty", _safe_len(r), _summarize_capture_tuples(r)))
            except Exception as e:
                self._record(ex, AttemptRecord("QM.captures", "QC().captures(rn)", True, "exception", exc_type=type(e).__name__, tb_excerpt=_tb_excerpt(e)))
        return r

