"""
Utility functions for the code index tool.
"""
import hashlib
import os
from typing import List, Set
from pathlib import Path


def get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()



def load_gitignore_patterns(directory: str) -> Set[str]:
    """Load .gitignore patterns from a directory."""
    patterns = set()
    gitignore_path = os.path.join(directory, ".gitignore")
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.add(line)
        except (IOError, OSError):
            pass
    return patterns


def matches_pattern(file_path: str, patterns: Set[str], root_dir: str) -> bool:
    """Check if a file path matches any of the ignore patterns."""
    relative_path = os.path.relpath(file_path, root_dir)
    
    for pattern in patterns:
        # Handle absolute patterns
        if pattern.startswith("/"):
            if relative_path.startswith(pattern[1:]):
                return True
        # Handle patterns with wildcards
        elif "*" in pattern or "?" in pattern:
            import fnmatch
            if fnmatch.fnmatch(relative_path, pattern):
                return True
        # Handle directory patterns
        elif pattern.endswith("/"):
            if relative_path.startswith(pattern) or relative_path.startswith(pattern[:-1]):
                return True
        # Handle exact matches
        else:
            if relative_path == pattern:
                return True
            # Check if it's a directory match
            if relative_path.startswith(pattern + os.sep):
                return True
    return False


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    return [
        ".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx", 
        ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php",
        ".swift", ".kt", ".scala", ".dart", ".lua", ".pl", ".pm",
        ".t", ".r", ".sql", ".html", ".css", ".scss", ".sass", ".less",
        ".md", ".markdown", ".rst", ".txt", ".json", ".xml", ".yaml", ".yml"
    ]


def is_supported_file(file_path: str) -> bool:
    """Check if a file is supported based on its extension."""
    _, ext = os.path.splitext(file_path.lower())
    return ext in get_supported_extensions()


def normalize_path(path: str) -> str:
    """Normalize a path to use forward slashes."""
    return str(Path(path).as_posix())
def augment_extensions_with_pygments(base_extensions: List[str]) -> List[str]:
    """Augment a list of extensions using Pygments lexers' filename patterns.

    If Pygments is unavailable, returns base_extensions and prints a warning.
    """
    try:
        from pygments.lexers import get_all_lexers  # type: ignore
    except Exception:
        print("Auto-extensions requested but 'pygments' is not installed; proceeding with configured extensions only.")
        return base_extensions

    discovered: Set[str] = set()
    try:
        for lex in get_all_lexers():
            # get_all_lexers() yields tuples: (name, aliases, filenames, mimetypes)
            filenames = []
            if len(lex) >= 3 and lex[2]:
                filenames = lex[2]
            for pattern in filenames:
                # Common patterns like "*.py", "*.rs", "*.vue"
                if isinstance(pattern, str) and pattern.startswith("*."):
                    ext = pattern[1:].lower()  # ".*" -> ".ext"
                    discovered.add(ext)
    except Exception:
        # If anything goes wrong, don't fail hard; just return base list
        return list(dict.fromkeys([e.lower() for e in base_extensions]))

    merged = list(dict.fromkeys([e.lower() for e in (list(base_extensions) + list(discovered))]))
    return merged