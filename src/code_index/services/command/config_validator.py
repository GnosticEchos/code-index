"""
Configuration validation service.
"""
from typing import Dict, Any, Optional


class ConfigValidator:
    """Validates Tree-sitter configuration."""
    
    def validate(self, config) -> bool:
        """Validate Tree-sitter configuration."""
        try:
            required_configs = [
                "tree_sitter_max_file_size_bytes",
                "tree_sitter_max_blocks_per_file",
                "tree_sitter_min_block_chars"
            ]
            for config_key in required_configs:
                if not hasattr(config, config_key):
                    return False
            max_file_size = getattr(config, "tree_sitter_max_file_size_bytes", 512 * 1024) or 512 * 1024
            max_blocks = getattr(config, "tree_sitter_max_blocks_per_file", 100) or 100
            min_chars = getattr(config, "tree_sitter_min_block_chars", 50) or 50
            if max_file_size < 1024:
                return False
            if max_blocks < 1:
                return False
            if min_chars < 1:
                return False
            return True
        except (AttributeError, TypeError, ValueError):
            return False
    
    def is_invalid_query(self, query_string: str) -> bool:
        """Check if query is invalid."""
        invalid_indicators = ['invalid_syntax', 'missing_closing_paren', 'unmatched_paren', 'syntax_error', 'undefined_node_type']
        query_lower = query_string.lower()
        return any(indicator in query_lower for indicator in invalid_indicators)