"""
Code Index Tool - A standalone code indexing tool using Ollama and Qdrant.
"""
# Tree-sitter error exports
from ._exceptions import (
    TreeSitterError as TreeSitterError,
    TreeSitterParserError as TreeSitterParserError,
    TreeSitterQueryError as TreeSitterQueryError,
    TreeSitterLanguageError as TreeSitterLanguageError,
    TreeSitterFileTooLargeError as TreeSitterFileTooLargeError
)