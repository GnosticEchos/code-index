"""
Code Index Tool - A standalone code indexing tool using Ollama and Qdrant.
"""
# Tree-sitter error exports
from .chunking import (
    TreeSitterError,
    TreeSitterParserError,
    TreeSitterQueryError,
    TreeSitterLanguageError,
    TreeSitterFileTooLargeError
)