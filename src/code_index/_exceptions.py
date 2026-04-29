"""
Tree-sitter exception classes.

Extracted from chunking.py to break circular import chain:
  chunking -> coordinator -> chunking
All Tree-sitter-related exceptions live here with zero internal dependencies.
"""


class TreeSitterError(Exception):
    """Base exception for Tree-sitter related errors."""
    pass


class TreeSitterParserError(TreeSitterError):
    """Exception raised when Tree-sitter parser encounters an error."""
    pass


class TreeSitterQueryError(TreeSitterError):
    """Exception raised when Tree-sitter query compilation or execution fails."""
    pass


class TreeSitterLanguageError(TreeSitterError):
    """Exception raised when Tree-sitter language loading fails."""
    pass


class TreeSitterFileTooLargeError(TreeSitterError):
    """Exception raised when a file exceeds the maximum size for Tree-sitter processing."""
    pass
