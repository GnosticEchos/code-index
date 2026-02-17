"""
Query result normalization service.
"""
from typing import List, Tuple, Any, Dict


class QueryNormalizer:
    """Normalizes query capture results to consistent format."""
    
    def get_capture_name(self, query, cap_idx: int, node) -> str:
        """Resolve capture name across API variants."""
        try:
            if hasattr(query, "capture_name"):
                try:
                    return query.capture_name(cap_idx)
                except (AttributeError, TypeError, IndexError):
                    pass
            names = getattr(query, "capture_names", None)
            if names:
                try:
                    return names[cap_idx]
                except (AttributeError, TypeError, IndexError):
                    pass
        except (AttributeError, TypeError):
            pass
        try:
            return getattr(node, "type", str(cap_idx))
        except (AttributeError, TypeError):
            return str(cap_idx)
    
    def process_cursor_capture(self, query, cap) -> Tuple[Any, str]:
        """Process a QueryCursor capture result."""
        try:
            if isinstance(cap, (tuple, list)):
                if len(cap) >= 3:
                    node, cap_idx = cap[0], cap[1]
                elif len(cap) >= 2:
                    node, cap_idx = cap[0], cap[1]
                else:
                    return None
            else:
                node = getattr(cap, "node", None)
                cap_idx = getattr(cap, "index", None)
            if node is not None and cap_idx is not None:
                name = self.get_capture_name(query, cap_idx, node)
                return (node, name)
        except (AttributeError, TypeError, ValueError, IndexError):
            pass
        return None
    
    def normalize_capture_results(self, capture_results) -> List[dict]:
        """Normalize capture results to consistent format for tests."""
        if not capture_results:
            return []
        normalized = []
        try:
            items_iter = capture_results.items() if hasattr(capture_results, "items") else []
            for capture_type, captures in items_iter:
                for entry in captures or []:
                    if isinstance(entry, dict) and ("node" in entry):
                        node = entry.get("node")
                        if node is None:
                            continue
                        normalized.append({
                            "type": capture_type,
                            "node": node,
                            "name": entry.get("name", ""),
                            "start_point": entry.get("start_point"),
                            "end_point": entry.get("end_point"),
                        })
                        continue
                    if isinstance(entry, dict):
                        name_key = f"{capture_type}.name"
                        if name_key in entry and len(entry.keys()) > 1:
                            node = entry[name_key]
                            if node is not None:
                                normalized.append({
                                    "type": capture_type,
                                    "node": node,
                                    "name": capture_type,
                                    "start_point": getattr(node, "start_point", None),
                                    "end_point": getattr(node, "end_point", None),
                                })
                        continue
        except (AttributeError, TypeError, ValueError):
            return []
        return normalized
    
    def normalize_captures_with_query(self, capture_results, query) -> List[Tuple[Any, str]]:
        """Normalize various capture result shapes into [(node, name)] tuples."""
        if not capture_results:
            return []
        tuples = []
        if isinstance(capture_results, list):
            for cap in capture_results:
                try:
                    if isinstance(cap, (tuple, list)) and len(cap) >= 2:
                        node, name = cap[0], cap[1]
                        tuples.append((node, name))
                    elif hasattr(cap, "node") and hasattr(cap, "index"):
                        node = cap.node
                        idx = cap.index
                        name = self.get_capture_name(query, idx, node)
                        tuples.append((node, name))
                    elif isinstance(cap, dict) and "node" in cap:
                        node = cap.get("node")
                        name = cap.get("name") or cap.get("type") or ""
                        if node is not None:
                            tuples.append((node, name))
                except (AttributeError, TypeError, ValueError):
                    continue
            return tuples
        if hasattr(capture_results, "items"):
            normalized = self.normalize_capture_results(capture_results)
            for entry in normalized:
                node = entry.get("node")
                name = entry.get("name") or entry.get("type") or ""
                if node is not None:
                    tuples.append((node, name))
            return tuples
        return tuples
    
    def reconstruct_from_matches(self, matches, query) -> List[Tuple[Any, str]]:
        """Reconstruct captures from Query.matches() results."""
        captures = []
        try:
            for match in matches or []:
                if isinstance(match, dict) and isinstance(match.get("captures"), dict):
                    for cap_name, node in (match.get("captures") or {}).items():
                        if not str(cap_name).endswith(".name"):
                            continue
                        base = str(cap_name).split(".", 1)[0]
                        if node is not None:
                            captures.append((node, base))
                    continue
                match_captures = getattr(match, "captures", [])
                if isinstance(match_captures, dict):
                    for cap_name, node in (match_captures or {}).items():
                        if not str(cap_name).endswith(".name"):
                            continue
                        base = str(cap_name).split(".", 1)[0]
                        if node is not None:
                            captures.append((node, base))
                    continue
                if match_captures:
                    for capture in match_captures:
                        if isinstance(capture, tuple) and len(capture) == 2:
                            node, name = capture
                            base = str(name).split(".", 1)[0]
                            captures.append((node, base))
                        else:
                            node = getattr(capture, "node", None)
                            idx = getattr(capture, "index", None)
                            if node is not None and idx is not None:
                                try:
                                    name = query.capture_names[idx]
                                except (AttributeError, TypeError, IndexError):
                                    name = str(idx)
                                base = str(name).split(".", 1)[0]
                                captures.append((node, base))
        except (AttributeError, TypeError, ValueError):
            pass
        return captures