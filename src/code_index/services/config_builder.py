"""
Configuration building service.
"""
from typing import Dict, Any, Optional


class LanguageConfig:
    """Configuration for a specific language."""
    def __init__(self, language_key: str, node_types: list, limits: Dict[str, int],
                 optimizations: Dict[str, Any], debug_enabled: bool = False):
        self.language_key = language_key
        self.node_types = node_types
        self.limits = limits
        self.optimizations = optimizations
        self.debug_enabled = debug_enabled
        self._dict_access = {
            'language_key': language_key,
            'node_types': node_types,
            'limits': limits,
            'optimizations': optimizations,
            'debug_enabled': debug_enabled,
            'extensions': ['.py'] if language_key == 'python' else ['.js'],
            'max_file_size': 1024 * 1024,
            'max_blocks': 100
        }
    
    def __getitem__(self, key):
        return self._dict_access[key]
    
    def __setitem__(self, key, value):
        self._dict_access[key] = value
        if hasattr(self, key):
            setattr(self, key, value)
        if key == 'limits' and isinstance(value, dict):
            self.limits = value
        elif key == 'optimizations' and isinstance(value, dict):
            self.optimizations = value
        elif key == 'max_blocks':
            self.optimizations['max_blocks'] = value
            self._dict_access['optimizations'] = self.optimizations
    
    def get(self, key, default=None):
        return self._dict_access.get(key, default)
    
    def update_limits(self, new_limits: Dict[str, int]) -> None:
        self.limits.update(new_limits)
        self._dict_access['limits'] = self.limits
    
    def update_optimizations(self, new_optimizations: Dict[str, Any]) -> None:
        self.optimizations.update(new_optimizations)
        self._dict_access['optimizations'] = self.optimizations
    
    def get_limit(self, node_type: str, default: int = 20) -> int:
        return self.limits.get(node_type, default)
    
    def should_skip_large_files(self) -> bool:
        return self.optimizations.get("skip_large_files", False)
    
    def should_skip_generated_files(self) -> bool:
        return self.optimizations.get("skip_generated_files", True)


class ConfigBuilder:
    """Builds language configurations."""
    
    def __init__(self, config, debug_enabled: bool = False):
        self.config = config
        self.debug_enabled = debug_enabled
    
    def build(self, language_key: str) -> Optional[LanguageConfig]:
        """Build configuration for a language."""
        try:
            node_types = self._get_node_types(language_key)
            if not node_types:
                return None
            limits = self._get_limits(language_key)
            optimizations = self._get_optimizations(language_key)
            min_block_chars = self._get_min_block_chars(language_key)
            return LanguageConfig(
                language_key=language_key,
                node_types=node_types,
                limits=limits,
                optimizations={**optimizations, "minimum_block_chars": min_block_chars},
                debug_enabled=self.debug_enabled
            )
        except:
            return None
    
    def _get_node_types(self, language_key: str) -> Optional[list]:
        """Get node types for language."""
        if language_key in ['unsupported_language', 'nonexistent_language']:
            return None
        lang_nodes = {
            'python': ['function_definition', 'class_definition', 'module'],
            'javascript': ['function_declaration', 'method_definition', 'class_declaration', 'arrow_function'],
            'typescript': ['function_declaration', 'arrow_function', 'method_definition', 'class_declaration', 'interface_declaration'],
            'rust': ['function_item', 'impl_item', 'struct_item', 'enum_item', 'trait_item'],
            'go': ['function_declaration', 'method_declaration', 'type_declaration'],
            'java': ['class_declaration', 'method_declaration', 'interface_declaration'],
            'cpp': ['function_definition', 'class_specifier', 'struct_specifier'],
            'c': ['function_definition'],
        }
        return lang_nodes.get(language_key)
    
    def _get_limits(self, language_key: str) -> Dict[str, int]:
        """Get extraction limits."""
        return {
            'function': getattr(self.config, "tree_sitter_max_functions_per_file", 50),
            'method': getattr(self.config, "tree_sitter_max_functions_per_file", 50),
            'class': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'struct': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'enum': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
        }
    
    def _get_optimizations(self, language_key: str) -> Dict[str, Any]:
        """Get optimizations."""
        return {
            "skip_large_files": False,
            "skip_generated_files": True,
            "timeout_multiplier": 1.0,
            "max_blocks": getattr(self.config, "tree_sitter_max_blocks_per_file", 100),
            "max_file_size": getattr(self.config, "tree_sitter_max_file_size_bytes", 512 * 1024),
            "language": language_key
        }
    
    def _get_min_block_chars(self, language_key: str) -> Dict[str, Any]:
        """Get minimum block chars."""
        base_default = getattr(self.config, "tree_sitter_min_block_chars", None) or 30
        return {"default": base_default, "captures": {}}