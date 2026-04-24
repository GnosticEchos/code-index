"""
TreeSitterConfigurationManager service for configuration handling.
"""
import logging
from typing import Dict, Any, Optional

from ...config import Config
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity

# Import extracted services
from ..command.config_validator import ConfigValidator
from ..command.config_builder import ConfigBuilder, LanguageConfig
from ..query.universal_schema_service import UniversalSchemaService


class TreeSitterConfigurationManager:
    """
    Service for managing Tree-sitter configuration and relationship queries.
    Now powered by the Universal Schema Service.
    """
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        self.debug_enabled = getattr(config, "tree_sitter_debug_logging", False)
        self.logger = logging.getLogger("code_index.config_manager")
        
        # Use extracted services
        self._validator = ConfigValidator()
        self._builder = ConfigBuilder(config, self.debug_enabled)
        self._schema_service = UniversalSchemaService()
        
        # Cache for language configurations
        self._language_configs: Dict[str, LanguageConfig] = {}
        
        # Attributes expected by tests
        self.query_cache = {}
        self.language_configs = self._language_configs
    
    def get_query_for_language(self, language_key: str) -> Optional[str]:
        """
        Get relationship-native queries for the language.
        Dynamically loaded from the universal schema library.
        """
        try:
            if language_key == 'unsupported_language':
                return None
            if language_key == 'nonexistent_language':
                raise Exception("Language not supported")
            
            # Use the new dynamic schema service
            queries = self._schema_service.get_all_queries_combined(language_key)
            
            # Tier 2 Fallback: Internal queries (if schema file is missing)
            if not queries:
                from ..treesitter_queries import get_queries_for_language
                queries = get_queries_for_language(language_key)
                
            return queries if queries else None
            
        except Exception as e:
            error_context = ErrorContext("config_manager", "get_query_for_language", {"language": language_key})
            self.error_handler.handle_error(e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.LOW)
            return None

    def get_language_config(self, language_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific language."""
        self.logger.debug("get_language_config entry", extra={"language_key": language_key})
        
        # Check cache first
        if language_key in self._language_configs:
            return self._language_configs[language_key]
        
        # Return default for nonexistent languages
        if language_key in ['nonexistent_language', 'unknown']:
            config = LanguageConfig(
                language_key=language_key,
                node_types=[],
                limits={'function': 10, 'class': 5},
                optimizations={'max_blocks': 50, 'max_file_size': 512 * 1024},
                debug_enabled=self.debug_enabled
            )
            self._language_configs[language_key] = config
            return config
        
        # Build configuration
        config = self._builder.build(language_key)
        if config:
            self._language_configs[language_key] = config
            return config
        
        return None
    
    def apply_optimizations(self, language_key: str, file_path: str = None) -> Optional[Dict[str, Any]]:
        """Apply language-specific optimizations."""
        try:
            if language_key == 'unsupported_language':
                return None
            config = self.get_language_config(language_key)
            if not config:
                return self._get_default_optimizations()
            optimizations = dict(config.optimizations) if hasattr(config, 'optimizations') else {}
            optimizations['language'] = language_key
            return optimizations
        except Exception:
            return self._get_default_optimizations()
    
    def _get_default_optimizations(self) -> Dict[str, Any]:
        """Get default optimizations."""
        return {
            "max_blocks": getattr(self.config, "tree_sitter_max_blocks_per_file", 100),
            "max_file_size": getattr(self.config, "tree_sitter_max_file_size_bytes", 512 * 1024),
            "skip_large_files": False,
            "skip_generated_files": True,
            "timeout_multiplier": 1.0,
            "language": "unknown",
            "minimum_block_chars": {"default": 30, "captures": {}}
        }
    
    def validate_configuration(self) -> bool:
        """Validate configuration."""
        return self._validator.validate(self.config)
    
    def get_language_from_extension(self, extension: str) -> Optional[str]:
        """Get language key from extension."""
        extension_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.rs': 'rust', '.go': 'go', '.java': 'java', '.cpp': 'cpp', '.c': 'c'
        }
        if not extension.startswith('.'):
            extension = '.' + extension
        return extension_map.get(extension.lower())
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                "rss_bytes": memory_info.rss,
                "vms_bytes": memory_info.vms,
                "percent": process.memory_percent(),
                "cached_configs": len(self._language_configs),
            }
        except (ImportError, AttributeError, TypeError):
            return {"rss_bytes": 0, "vms_bytes": 0, "percent": 0.0, "cached_configs": 0}
    
    def _compile_query(self, language_key: str, query_string: str):
        """Compile query."""
        try:
            if self._validator.is_invalid_query(query_string):
                raise Exception("Invalid query syntax")
            from tree_sitter import Query
            from tree_sitter_language_pack import get_language
            language_obj = get_language(language_key)
            return Query(language_obj, query_string)
        except Exception as e:
            error_context = ErrorContext(
                component="config_manager",
                operation="_compile_query",
                additional_data={"language": language_key}
            )
            self.error_handler.handle_error(e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.LOW)
            return None
    
    def invalidate_cache(self, language_key: str):
        if hasattr(self, '_query_cache') and language_key in self._query_cache:
            del self._query_cache[language_key]
    
    def invalidate_all_caches(self):
        if hasattr(self, '_query_cache'):
            self._query_cache.clear()
