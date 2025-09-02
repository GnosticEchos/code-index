#!/usr/bin/env python3
"""
Tree-sitter language symbol dumper.

Usage:
  PYTHONPATH=. python scripts/utilities/ts_dump_symbols.py vue
  PYTHONPATH=. python scripts/utilities/ts_dump_symbols.py typescript

This uses tree_sitter_language_pack to load the language and enumerates all
grammar symbols (node types) available in the current environment. Helpful
for aligning queries in [src_code_index.treesitter_queries.get_queries_for_language()].
"""
import sys
from typing import List

def dump_symbols(lang_key: str) -> List[str]:
    try:
        import tree_sitter_language_pack as tsl  # type: ignore
        language = tsl.get_language(lang_key)
    except Exception as e:
        print(f"ERROR: failed to load language '{lang_key}': {e}")
        return []
    # Try symbol enumeration across bindings
    names: List[str] = []
    # tree_sitter.Language typically exposes symbol_count and symbol_name
    count = getattr(language, "symbol_count", None)
    symbol_name = getattr(language, "symbol_name", None)
    if callable(symbol_name) and isinstance(count, int) and count > 0:
        for i in range(count):
            try:
                name = symbol_name(i)
            except Exception:
                continue
            if not name or not isinstance(name, str):
                continue
            # Filter out aliases for clarity if needed; keep everything for now
            names.append(name)
    else:
        # Fallback: attempt to access capture_names if available (rare at Language level)
        caps = getattr(language, "capture_names", None)
        if isinstance(caps, (list, tuple)):
            names.extend([str(x) for x in caps if isinstance(x, str)])
    # Deduplicate and sort
    return sorted(set(names))

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/utilities/ts_dump_symbols.py <language_key>")
        sys.exit(1)
    lang_key = sys.argv[1]
    names = dump_symbols(lang_key)
    if not names:
        print(f"No symbols found for '{lang_key}' or unable to enumerate symbols.")
        sys.exit(2)
    print(f"# Symbols for language '{lang_key}' (count={len(names)})")
    for n in names:
        print(n)

if __name__ == "__main__":
    main()