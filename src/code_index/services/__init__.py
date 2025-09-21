"""
Services for CQRS pattern implementation.

This package contains command and query services that separate
business logic from presentation layer concerns.
"""

from .indexing_service import IndexingService

__all__ = ['IndexingService']