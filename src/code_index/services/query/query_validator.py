"""
Query validation service for Tree-sitter queries.

This module provides query API validation and capability detection
for different Tree-sitter versions.
"""

import logging
from typing import Dict, Any


class QueryValidator:
    """
    Service for validating query API capabilities.
    
    Handles:
    - Query API method detection
    - QueryCursor availability checking
    - Recommended method determination
    """
    
    def __init__(self, debug_enabled: bool = False):
        """
        Initialize the QueryValidator.
        
        Args:
            debug_enabled: Whether to enable debug logging
        """
        self.debug_enabled = debug_enabled
        self.logger = logging.getLogger("code_index.query_validator")
    
    def validate_query_api(self, query) -> Dict[str, Any]:
        """
        Validate available query API methods.
        
        Args:
            query: Compiled query object
            
        Returns:
            Dictionary with API availability information
        """
        api_info: Dict[str, Any] = {
            "has_captures": False,
            "has_matches": False,
            "has_capture_names": False,
            "has_capture_name": False,
            "query_cursor_available": False,
            "cursor_has_captures": False,
            "cursor_has_matches": False,
            "recommended_method": "unknown",
            "probe_errors": {},
        }
        
        try:
            # Check Query methods - check both hasattr and actual values
            try:
                api_info["has_captures"] = hasattr(query, "captures") and bool(getattr(query, "captures", False))
            except Exception as e:
                api_info["has_captures"] = False
                api_info["probe_errors"]["captures"] = f"{type(e).__name__}: {e}"
            try:
                api_info["has_matches"] = hasattr(query, "matches") and bool(getattr(query, "matches", False))
            except Exception as e:
                api_info["has_matches"] = False
                api_info["probe_errors"]["matches"] = f"{type(e).__name__}: {e}"
            
            api_info["has_capture_names"] = hasattr(query, "capture_names")
            api_info["has_capture_name"] = hasattr(query, "capture_name")
            
            # Check QueryCursor availability (attempt instantiation to ensure availability)
            try:
                from tree_sitter import QueryCursor  # type: ignore
                try:
                    qc = QueryCursor()  # instantiation may be patched to raise in tests
                    api_info["query_cursor_available"] = True
                    # Probe callability without executing queries
                    try:
                        api_info["cursor_has_captures"] = hasattr(qc, "captures")
                        api_info["cursor_has_matches"] = hasattr(qc, "matches")
                    except Exception as e:
                        api_info["probe_errors"]["cursor_attrs"] = f"{type(e).__name__}: {e}"
                except Exception as e:
                    api_info["query_cursor_available"] = False
                    api_info["probe_errors"]["QueryCursor()"] = f"{type(e).__name__}: {e}"
            except Exception as e:
                api_info["query_cursor_available"] = False
                api_info["probe_errors"]["import_QueryCursor"] = f"{type(e).__name__}: {e}"
            
            # Determine recommended method
            if api_info["has_captures"]:
                api_info["recommended_method"] = "captures"
            elif api_info["has_matches"]:
                api_info["recommended_method"] = "matches"
            elif api_info["query_cursor_available"]:
                api_info["recommended_method"] = "query_cursor"
            else:
                api_info["recommended_method"] = "none_available"
                
        except Exception as e:
            if self.debug_enabled:
                self.logger.debug(f"Error validating query API: {e}")
        
        # Emit detail at DEBUG when toggled
        if self.debug_enabled:
            self.logger.debug(f"validate_query_api detail: {api_info}")
        return api_info
    
    def _validate_query_api(self, query) -> bool:
        """Private boolean wrapper around validate_query_api for tests."""
        info = self.validate_query_api(query)
        return bool(
            info.get("has_captures", False)
            or info.get("has_matches", False)
            or info.get("query_cursor_available", False)
        )
    
    def _validate_query_api_info(self, query) -> Dict[str, Any]:
        """Return detailed API capability information (private helper)."""
        return self.validate_query_api(query)
