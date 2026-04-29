"""
Legacy tree-sitter queries module - DEPRECATED.

All consumers have been migrated to UniversalSchemaService (queries_minimal.jsonl).
This file is kept as a reference only.

See: services/query/universal_schema_service.py
See: queries/queries_minimal.jsonl
"""

import logging

logger = logging.getLogger(__name__)


def get_queries_for_language(language_key: str):
    """
    DEPRECATED: Use UniversalSchemaService.get_all_queries_combined() instead.
    
    Returns None to indicate queries should be loaded from the schema file.
    """
    logger.debug(f"treesitter_queries.get_queries_for_language({language_key}) called - "
                 "migrate to UniversalSchemaService")
    return None


def validate_queries_for_language(language_key: str):
    """DEPRECATED: No-op. Query validation is handled by UniversalSchemaService."""
    return False


def validate_all_queries():
    """DEPRECATED: No-op. Query validation is handled by UniversalSchemaService."""
    return False


def test_query_compilation(language_key):
    """DEPRECATED: No-op. Query compilation is handled by UniversalSchemaService."""
    return False


def test_all_query_compilations():
    """DEPRECATED: No-op. Query compilation is handled by UniversalSchemaService."""
    return False
