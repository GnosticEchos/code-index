"""
Parser Management Service for Tree-sitter operations.

This service handles Tree-sitter parser lifecycle management, resource cleanup,
memory management, and parser validation. It provides a clean interface for
managing parsers across different programming languages with proper resource
monitoring and timeout mechanisms.
"""

import time
import weakref
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

from .config import Config
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity, error_handler


class ParserCreationError(Exception):
    """Exception raised when parser creation fails."""
    pass


class ParserTimeoutError(Exception):
    """Exception raised when parser operation times out."""
    pass


@dataclass
class ParserInfo:
    """Information about a Tree-sitter parser."""
    language: str
    parser: Any
    language_id: int
    created_at: float
    last_used: float
    use_count: int
    memory_usage: int
    is_valid: bool
    error_message: Optional[str] = None


class TreeSitterParserManager:
    """
    Service for managing Tree-sitter parsers across different languages.

    Provides:
    - Parser lifecycle management and caching
    - Resource cleanup and memory management
    - Parser validation and availability checking
    - Timeout mechanisms and resource monitoring
    - Performance tracking and optimization
    """

    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """
        Initialize the TreeSitterParserManager.

        Args:
            config: Configuration object
            error_handler: Optional error handler instance
        """
        self.config = config
        self.error_handler = error_handler or ErrorHandler()

        # Parser cache with metadata
        self._parser_cache: Dict[str, ParserInfo] = {}

        # Language cache for Tree-sitter languages
        self._language_cache: Dict[str, Any] = {}

        # Parser language ID mapping to detect language mismatches
        self._parser_language_ids: Dict[str, int] = {}

        # Resource monitoring
        self._resource_monitor = ParserResourceMonitor(config)

        # Cache settings
        self.max_cache_size = getattr(config, "tree_sitter_parser_cache_size", 50)
        self.cache_ttl_seconds = getattr(config, "tree_sitter_parser_cache_ttl", 600)  # 10 minutes
        self.parser_timeout_seconds = getattr(config, "tree_sitter_parser_timeout", 30)

        # Debug logging
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

    def get_parser(self, language: str) -> Optional[Any]:
        """
        Get a Tree-sitter parser for a language, creating if necessary.

        Args:
            language: Language key

        Returns:
            Parser object if successful, None otherwise
        """
        try:
            # Check cache first
            if language in self._parser_cache:
                cached_parser = self._parser_cache[language]
                if cached_parser.is_valid and self._is_cache_valid(cached_parser):
                    cached_parser.last_used = time.time()
                    cached_parser.use_count += 1
                    return cached_parser.parser
                else:
                    # Remove invalid cached parser
                    self._cleanup_parser(language)

            # Create new parser
            parser, language_obj = self._create_parser(language)
            if not parser or not language_obj:
                return None

            # Create parser info
            parser_info = ParserInfo(
                language=language,
                parser=parser,
                language_id=id(language_obj),
                created_at=time.time(),
                last_used=time.time(),
                use_count=1,
                memory_usage=self._resource_monitor.get_memory_usage(),
                is_valid=True
            )

            # Cache the parser
            if len(self._parser_cache) < self.max_cache_size:
                self._parser_cache[language] = parser_info
                self._parser_language_ids[language] = id(language_obj)

            return parser

        except Exception as e:
            error_context = ErrorContext(
                component="parser_manager",
                operation="get_parser",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return None

    def validate_parser(self, language: str) -> bool:
        """
        Validate that a parser for a language is available and working.

        Args:
            language: Language key

        Returns:
            True if parser is valid and available, False otherwise
        """
        try:
            parser = self.get_parser(language)
            if not parser:
                return False

            # Try to create a simple test tree to validate parser
            try:
                test_code = self._get_test_code_for_language(language)
                if test_code:
                    tree = parser.parse(bytes(test_code, "utf8"))
                    return tree is not None and tree.root_node is not None
                else:
                    # If no test code available, assume parser is valid if it exists
                    return True
            except Exception as e:
                if self._debug_enabled:
                    print(f"Parser validation failed for {language}: {e}")
                return False

        except Exception as e:
            error_context = ErrorContext(
                component="parser_manager",
                operation="validate_parser",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.VALIDATION, ErrorSeverity.LOW
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return False

    def cleanup_resources(self) -> int:
        """
        Clean up all cached parsers and resources.

        Returns:
            Number of parsers cleaned up
        """
        try:
            cleaned_count = len(self._parser_cache)

            # Clear parser cache
            self._parser_cache.clear()

            # Clear language cache
            self._language_cache.clear()

            # Clear language ID mapping
            self._parser_language_ids.clear()

            # Reset resource monitor
            self._resource_monitor.reset()

            if self._debug_enabled:
                print(f"Cleaned up {cleaned_count} parsers from cache")

            return cleaned_count

        except Exception as e:
            error_context = ErrorContext(
                component="parser_manager",
                operation="cleanup_resources"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.LOW
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return 0

    def cleanup_old_parsers(self) -> int:
        """
        Remove old/unused parsers from cache.

        Returns:
            Number of parsers removed
        """
        current_time = time.time()
        removed_count = 0

        # Remove parsers that haven't been used recently
        expired_parsers = []
        for language, parser_info in self._parser_cache.items():
            if current_time - parser_info.last_used > self.cache_ttl_seconds:
                expired_parsers.append(language)

        for language in expired_parsers:
            self._cleanup_parser(language)
            removed_count += 1

        if self._debug_enabled and removed_count > 0:
            print(f"Cleaned up {removed_count} expired parsers from cache")

        return removed_count

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about parser cache status.

        Returns:
            Dictionary with cache statistics
        """
        total_parsers = len(self._parser_cache)
        valid_parsers = sum(1 for p in self._parser_cache.values() if p.is_valid)
        total_memory = sum(p.memory_usage for p in self._parser_cache.values())

        return {
            "cache_size": total_parsers,
            "valid_parsers": valid_parsers,
            "invalid_parsers": total_parsers - valid_parsers,
            "total_memory_usage": total_memory,
            "average_memory_per_parser": total_memory / total_parsers if total_parsers > 0 else 0,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_cache_size": self.max_cache_size,
            "parser_timeout_seconds": self.parser_timeout_seconds
        }

    def get_parser_stats(self, language: str) -> Dict[str, Any]:
        """
        Get statistics for a specific language parser.

        Args:
            language: Language key

        Returns:
            Dictionary with language-specific parser statistics
        """
        if language not in self._parser_cache:
            return {
                "language": language,
                "cached": False,
                "use_count": 0,
                "memory_usage": 0,
                "uptime_seconds": 0
            }

        parser_info = self._parser_cache[language]
        uptime = time.time() - parser_info.created_at

        return {
            "language": language,
            "cached": True,
            "use_count": parser_info.use_count,
            "memory_usage": parser_info.memory_usage,
            "uptime_seconds": uptime,
            "last_used_seconds_ago": time.time() - parser_info.last_used,
            "is_valid": parser_info.is_valid
        }

    def preload_common_parsers(self) -> int:
        """
        Preload parsers for commonly used languages.

        Returns:
            Number of parsers preloaded
        """
        common_languages = [
            'python', 'javascript', 'typescript', 'rust', 'go', 'java', 'cpp', 'c'
        ]

        preloaded_count = 0
        for language in common_languages:
            try:
                parser = self.get_parser(language)
                if parser:
                    preloaded_count += 1
            except Exception:
                continue

        if self._debug_enabled:
            print(f"Preloaded {preloaded_count} parsers for common languages")

        return preloaded_count

    def _create_parser(self, language: str) -> tuple[Optional[Any], Optional[Any]]:
        """
        Create a new Tree-sitter parser for a language.

        Args:
            language: Language key

        Returns:
            Tuple of (parser, language_object) if successful, (None, None) otherwise
        """
        try:
            from tree_sitter import Parser

            # Get Tree-sitter language
            language_obj = self._get_tree_sitter_language(language)
            if not language_obj:
                raise ParserCreationError(f"Tree-sitter language not available for {language}")

            # Create parser
            parser = Parser()
            parser.language = language_obj

            if self._debug_enabled:
                print(f"Created parser for {language}")

            return parser, language_obj

        except Exception as e:
            error_context = ErrorContext(
                component="parser_manager",
                operation="_create_parser",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
            )
            if self._debug_enabled:
                print(f"Warning: {error_response.message}")
            return None, None

    def _get_tree_sitter_language(self, language: str):
        """
        Get Tree-sitter Language object for a language.

        Args:
            language: Language key

        Returns:
            Language object if available, None otherwise
        """
        try:
            # Check cache first
            if language in self._language_cache:
                return self._language_cache[language]

            # Load language
            import tree_sitter_language_pack as tsl
            language_obj = tsl.get_language(language)

            # Cache the language object
            self._language_cache[language] = language_obj

            return language_obj

        except Exception as e:
            if self._debug_enabled:
                print(f"Failed to load Tree-sitter language for {language}: {e}")
            return None

    def _cleanup_parser(self, language: str) -> None:
        """
        Clean up a specific parser from cache.

        Args:
            language: Language key
        """
        try:
            if language in self._parser_cache:
                del self._parser_cache[language]

            if language in self._parser_language_ids:
                del self._parser_language_ids[language]

            if language in self._language_cache:
                del self._language_cache[language]

        except Exception as e:
            if self._debug_enabled:
                print(f"Warning: Failed to cleanup parser for {language}: {e}")

    def _is_cache_valid(self, parser_info: ParserInfo) -> bool:
        """
        Check if a cached parser is still valid.

        Args:
            parser_info: Parser information object

        Returns:
            True if cache is valid, False otherwise
        """
        current_time = time.time()
        return current_time - parser_info.last_used <= self.cache_ttl_seconds

    def _get_test_code_for_language(self, language: str) -> Optional[str]:
        """
        Get test code for validating a parser.

        Args:
            language: Language key

        Returns:
            Test code string if available, None otherwise
        """
        test_code = {
            'python': 'def test(): pass',
            'javascript': 'function test() {}',
            'typescript': 'function test(): void {}',
            'rust': 'fn test() {}',
            'go': 'func test() {}',
            'java': 'class Test {}',
            'cpp': 'void test() {}',
            'c': 'void test() {}',
            'html': '<html></html>',
            'css': '.test {}',
            'json': '{"test": "value"}',
            'yaml': 'test: value',
            'markdown': '# Test',
            'sql': 'SELECT 1',
            'bash': 'echo "test"',
            'dockerfile': 'FROM alpine'
        }

        return test_code.get(language)


class ParserResourceMonitor:
    """
    Monitor and track resource usage for Tree-sitter parsers.
    """

    def __init__(self, config: Config):
        """
        Initialize the resource monitor.

        Args:
            config: Configuration object
        """
        self.config = config
        self._baseline_memory = self._get_current_memory_usage()

    def get_memory_usage(self) -> int:
        """
        Get current memory usage.

        Returns:
            Memory usage in bytes
        """
        try:
            current_memory = self._get_current_memory_usage()
            return max(0, current_memory - self._baseline_memory)
        except Exception:
            return 0

    def reset(self) -> None:
        """Reset the baseline memory usage."""
        self._baseline_memory = self._get_current_memory_usage()

    def _get_current_memory_usage(self) -> int:
        """
        Get current memory usage.

        Returns:
            Memory usage in bytes
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return 0