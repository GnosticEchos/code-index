#!/usr/bin/env python3
"""
Dump Tree-sitter node types for a given source file using a specified language.

Usage:
  PYTHONPATH=. python scripts/utilities/ts_dump_node_types.py vue /path/to/file.vue [--limit 200]

This parses the file with tree_sitter_language_pack's language (e.g. 'vue'),
traverses the syntax tree, and prints counts of node.type occurrences to help
author grammar-aligned queries in [src_code_index.treesitter_queries.get_queries_for_language()].
"""
import sys
import argparse
from collections import Counter
from typing import Any, Optional

def get_language(lang_key: str):
    try:
        import tree_sitter_language_pack as tsl  # type: ignore
        return tsl.get_language(lang_key)
    except Exception as e:
        print(f"ERROR: failed to load language '{lang_key}': {e}", file=sys.stderr)
        return None

def build_parser(language) -> Optional[Any]:
    try:
        from tree_sitter import Parser  # type: ignore
    except Exception as e:
        print(f"ERROR: tree_sitter not available: {e}", file=sys.stderr)
        return None
    try:
        parser = Parser()
        parser.language = language
        return parser
    except Exception as e:
        print(f"ERROR: failed to initialize parser: {e}", file=sys.stderr)
        return None

def traverse(node, counter: Counter, max_nodes: int, visited: list) -> None:
    if len(visited) >= max_nodes:
        return
    visited.append(node)
    try:
        t = getattr(node, "type", "")
        if t:
            counter[t] += 1
    except Exception:
        pass
    try:
        for child in getattr(node, "children", []):
            if len(visited) >= max_nodes:
                break
            traverse(child, counter, max_nodes, visited)
    except Exception:
        pass

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("language_key", help="Language key to load from tree_sitter_language_pack (e.g., vue, typescript)")
    parser.add_argument("filepath", help="Path to the source file to parse")
    parser.add_argument("--limit", type=int, default=2000, help="Max nodes to visit (default: 2000)")
    args = parser.parse_args()

    language = get_language(args.language_key)
    if language is None:
        sys.exit(2)

    ts_parser = build_parser(language)
    if ts_parser is None:
        sys.exit(2)

    try:
        with open(args.filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: cannot read file '{args.filepath}': {e}", file=sys.stderr)
        sys.exit(2)

    try:
        tree = ts_parser.parse(bytes(content, "utf-8"))
        root = tree.root_node
    except Exception as e:
        print(f"ERROR: parse failed: {e}", file=sys.stderr)
        sys.exit(2)

    counter: Counter = Counter()
    traverse(root, counter, args.limit, [])

    print(f"# Node type counts for {args.filepath} (language={args.language_key}, limit={args.limit})")
    for t, c in counter.most_common():
        print(f"{t}: {c}")

if __name__ == "__main__":
    main()