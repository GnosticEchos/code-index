"""
Block filter module for filtering Tree-sitter extracted blocks.

This module handles block filtering based on content thresholds and capture types.
"""

from typing import Optional, Dict, Any


# Captures that are just identifiers (names) and should be skipped
IDENTIFIER_CAPTURES = {
    "name",
    "identifier",
    "function_name",
    "class_name",
    "method_name",
    "variable_name",
    "property_identifier",
    "type_identifier",
    "field_identifier",
}


# Captures that represent structural code elements
STRUCTURAL_CAPTURES = {
    "module",
    "component",
    "function",
    "function_definition",
    "function_declaration",
    "method_definition",
    "method_declaration",
    "class",
    "class_definition",
    "class_declaration",
    "impl",
    "impl_item",
    "struct",
    "struct_item",
    "enum",
    "enum_item",
    "trait",
    "trait_item",
    "template",
    "template_element",
}


class BlockFilter:
    """
    Filter for determining which blocks should be kept based on configured thresholds.
    """
    
    def __init__(self, config, min_block_chars: int = 30):
        self.config = config
        self.min_block_chars = min_block_chars
        self._capture_minimums: Dict[str, int] = {}
        self._structural_captures = STRUCTURAL_CAPTURES
        self._identifier_captures = IDENTIFIER_CAPTURES
    
    def prepare_minimums(self, language_key: str, config_manager=None) -> None:
        """Load default and capture-specific minimum thresholds for a language."""
        self._capture_minimums = {}
        self.min_block_chars = getattr(self.config, "tree_sitter_min_block_chars_default", 30)
        
        if not config_manager:
            return

        try:
            language_config = config_manager.get_language_config(language_key)
            if not language_config:
                return

            if isinstance(language_config, dict):
                optimizations = language_config.get("optimizations", {})
            else:
                optimizations = getattr(language_config, "optimizations", {})

            minimum_data = optimizations.get("minimum_block_chars") if isinstance(optimizations, dict) else None
            if not isinstance(minimum_data, dict):
                return

            default_value = minimum_data.get("default")
            if isinstance(default_value, int):
                self.min_block_chars = default_value

            captures = minimum_data.get("captures")
            if isinstance(captures, dict):
                for name, value in captures.items():
                    if isinstance(value, int):
                        self._capture_minimums[name] = value
        except Exception:
            pass
    
    def threshold_for_capture(self, capture_name: str) -> int:
        """Return the configured threshold for a capture name."""
        return self._capture_minimums.get(capture_name, self.min_block_chars)
    
    def should_keep_capture(
        self,
        capture_name: str,
        content_length: int,
        parent_capture: Optional[str] = None
    ) -> bool:
        """
        Decide whether to retain a capture based on configured thresholds and parent context.
        
        Args:
            capture_name: Name of the capture
            content_length: Length of the captured content
            parent_capture: Parent capture name if available
            
        Returns:
            True if the capture should be kept
        """
        # Skip identifier captures - they only contain names
        if capture_name in self._identifier_captures:
            return False
        
        threshold = self.threshold_for_capture(capture_name)
        
        # Structural captures must meet threshold
        if capture_name in self._structural_captures:
            return content_length >= threshold
        
        # Non-structural captures need either threshold or a structural parent
        if content_length >= threshold:
            return True
        if parent_capture and parent_capture in self._structural_captures:
            return True
        
        return False
    
    def filter_blocks(
        self,
        blocks: list,
        max_blocks: int = 100
    ) -> list:
        """
        Filter blocks to meet maximum limit while preserving quality.
        
        Args:
            blocks: List of CodeBlock objects
            max_blocks: Maximum number of blocks to return
            
        Returns:
            Filtered list of blocks
        """
        if len(blocks) <= max_blocks:
            return blocks
        
        # Sort by content length (larger first) to keep most substantial blocks
        sorted_blocks = sorted(
            blocks,
            key=lambda b: len(b.content) if b.content else 0,
            reverse=True
        )
        
        return sorted_blocks[:max_blocks]


def create_block_filter(config, min_block_chars: int = 30) -> BlockFilter:
    """Factory function to create a BlockFilter instance."""
    return BlockFilter(config, min_block_chars)
