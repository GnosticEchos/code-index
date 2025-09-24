"""
Language Detection Service for the code index tool.

This service provides language detection capabilities based on file paths,
extensions, and content analysis. It supports multiple programming languages
and integrates with ConfigurationService for language-specific settings.
"""

import os
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from .config import Config
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity, error_handler
from .config_service import ConfigurationService as ConfigService


class LanguageDetectionError(Exception):
    """Base exception for language detection errors."""
    pass


class UnsupportedLanguageError(LanguageDetectionError):
    """Exception raised when language is not supported."""
    pass


class LanguageDetector:
    """
    Service for detecting programming languages from file paths and content.

    Provides:
    - File extension-based language detection
    - Language validation and support checking
    - Language-specific configuration integration
    - Caching for performance optimization
    """

    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """
        Initialize the LanguageDetector.

        Args:
            config: Configuration object
            error_handler: Optional error handler instance
        """
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = ConfigService(self.error_handler)

        # Language mappings for file extensions
        self._extension_to_language: Dict[str, str] = self._build_extension_mapping()

        # Language mappings for filenames (without extensions)
        self._filename_to_language: Dict[str, str] = self._build_filename_mapping()

        # Cache for detected languages
        self._language_cache: Dict[str, Optional[str]] = {}

        # Supported languages set
        self._supported_languages: Set[str] = set(self._extension_to_language.values()) | set(self._filename_to_language.values())

    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect the programming language for a given file path.

        Args:
            file_path: Path to the file

        Returns:
            Language key if detected, None if not supported
        """
        try:
            # Check cache first
            if file_path in self._language_cache:
                return self._language_cache[file_path]

            # Try filename-based detection first (for special files like CMakeLists.txt)
            language = self._detect_by_filename(file_path)

            # Try extension-based detection if filename failed
            if not language:
                language = self._detect_by_extension(file_path)

            # Cache the result
            self._language_cache[file_path] = language

            return language

        except Exception as e:
            error_context = ErrorContext(
                component="language_detection",
                operation="detect_language",
                file_path=file_path
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.LOW
            )
            print(f"Warning: {error_response.message}")
            return None

    def is_language_supported(self, language: str) -> bool:
        """
        Check if a language is supported by the system.

        Args:
            language: Language key to check

        Returns:
            True if supported, False otherwise
        """
        return language in self._supported_languages

    def validate_language(self, language: str) -> bool:
        """
        Validate that a language is properly configured and available.

        Args:
            language: Language key to validate

        Returns:
            True if valid and available, False otherwise
        """
        try:
            if not self.is_language_supported(language):
                return False

            # Check if language-specific configuration is available
            try:
                # This would typically check if Tree-sitter language pack supports it
                # For now, we'll assume all supported languages are valid
                return True
            except Exception as e:
                error_context = ErrorContext(
                    component="language_detection",
                    operation="validate_language",
                    additional_data={"language": language}
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.LOW
                )
                print(f"Warning: {error_response.message}")
                return False

        except Exception as e:
            error_context = ErrorContext(
                component="language_detection",
                operation="validate_language",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.VALIDATION, ErrorSeverity.LOW
            )
            print(f"Warning: {error_response.message}")
            return False

    def get_supported_languages(self) -> Set[str]:
        """
        Get all supported language keys.

        Returns:
            Set of supported language keys
        """
        return self._supported_languages.copy()

    def get_language_for_extension(self, extension: str) -> Optional[str]:
        """
        Get language for a specific file extension.

        Args:
            extension: File extension (with or without leading dot)

        Returns:
            Language key if found, None otherwise
        """
        ext = extension.lstrip('.').lower()
        return self._extension_to_language.get(ext)

    def get_extension_for_language(self, language: str) -> List[str]:
        """
        Get all file extensions associated with a language.

        Args:
            language: Language key

        Returns:
            List of file extensions for the language
        """
        extensions = []
        for ext, lang in self._extension_to_language.items():
            if lang == language:
                extensions.append(f".{ext}")
        return extensions

    def clear_cache(self) -> None:
        """Clear the language detection cache."""
        self._language_cache.clear()

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the language detection cache.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._language_cache),
            "supported_languages_count": len(self._supported_languages),
            "extensions_count": len(self._extension_to_language),
            "filenames_count": len(self._filename_to_language)
        }

    def _detect_by_extension(self, file_path: str) -> Optional[str]:
        """
        Detect language based on file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language key if detected, None otherwise
        """
        try:
            _, ext = os.path.splitext(file_path)
            ext = ext.lstrip('.').lower()

            if ext in self._extension_to_language:
                return self._extension_to_language[ext]

            return None

        except Exception:
            return None

    def _detect_by_filename(self, file_path: str) -> Optional[str]:
        """
        Detect language based on filename (for files without extensions).

        Args:
            file_path: Path to the file

        Returns:
            Language key if detected, None otherwise
        """
        try:
            filename = os.path.basename(file_path).lower()

            if filename in self._filename_to_language:
                return self._filename_to_language[filename]

            return None

        except Exception:
            return None

    def _build_extension_mapping(self) -> Dict[str, str]:
        """
        Build the extension to language mapping.

        Returns:
            Dictionary mapping file extensions to language keys
        """
        return {
            # Core programming languages
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'tsx': 'tsx',
            'jsx': 'javascript',
            'go': 'go',
            'java': 'java',
            'cpp': 'cpp',
            'cc': 'cpp',
            'cxx': 'cpp',
            'c': 'c',
            'h': 'c',
            'hpp': 'cpp',
            'rs': 'rust',
            'cs': 'csharp',
            'rb': 'ruby',
            'php': 'php',
            'kt': 'kotlin',
            'kts': 'kotlin',
            'swift': 'swift',
            'lua': 'lua',
            'dart': 'dart',
            'scala': 'scala',
            'pl': 'perl',
            'pm': 'perl',
            'hs': 'haskell',
            'lhs': 'haskell',
            'ex': 'elixir',
            'exs': 'elixir',
            'clj': 'clojure',
            'cljs': 'clojure',
            'erl': 'erlang',
            'hrl': 'erlang',
            'ml': 'ocaml',
            'mli': 'ocaml',
            'fs': 'fsharp',
            'fsx': 'fsharp',
            'fsi': 'fsharp',
            'vb': 'vb',
            'r': 'r',
            'm': 'matlab',
            'jl': 'julia',
            'groovy': 'groovy',
            'zig': 'zig',
            'v': 'v',
            'nim': 'nim',
            'tcl': 'tcl',
            'm': 'objc',
            'mm': 'objcpp',

            # Web and markup languages
            'html': 'html',
            'htm': 'html',
            'css': 'css',
            'scss': 'scss',
            'sass': 'sass',
            'less': 'less',
            'vue': 'vue',
            'svelte': 'svelte',
            'astro': 'astro',

            # Configuration and data formats
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'toml': 'toml',
            'xml': 'xml',
            'ini': 'ini',
            'csv': 'csv',
            'tsv': 'tsv',

            # System and infrastructure
            'sh': 'bash',
            'bash': 'bash',
            'zsh': 'bash',
            'fish': 'fish',
            'ps1': 'powershell',
            'dockerfile': 'dockerfile',
            'makefile': 'makefile',
            'cmake': 'cmake',
            'tf': 'terraform',
            'tfvars': 'terraform',
            'proto': 'proto',
            'thrift': 'thrift',

            # Documentation and text
            'md': 'markdown',
            'markdown': 'markdown',
            'rst': 'rst',
            'org': 'org',
            'tex': 'latex',
            'txt': 'text/plain',  # Add text files support

            # Database and query languages
            'sql': 'sql',
            'surql': 'sql',
            'graphql': 'graphql',
            'gql': 'graphql',

            # Smart contracts
            'sol': 'solidity',

            # Hardware description
            'sv': 'systemverilog',
            'svh': 'systemverilog',
            'vhd': 'vhdl',
            'verilog': 'verilog',
        }

    def _build_filename_mapping(self) -> Dict[str, str]:
        """
        Build the filename to language mapping.

        Returns:
            Dictionary mapping filenames to language keys
        """
        return {
            'dockerfile': 'dockerfile',
            'makefile': 'makefile',
            'cmakelists.txt': 'cmake',
            'CMakeLists.txt': 'cmake',  # Add uppercase version for test compatibility
            'cargo.toml': 'toml',
            'pyproject.toml': 'toml',
            'package.json': 'json',
            'tsconfig.json': 'json',
            'requirements.txt': 'text/plain',  # Add requirements files support
            'requirements-dev.txt': 'text/plain',
            'ci_ignore.txt': 'text/plain',
            'fast-indexing.json': 'json',
            'semantic-accuracy.json': 'json',
        }

    def get_language_config(self, language: str) -> Dict[str, Any]:
        """
        Get language-specific configuration from ConfigurationService.

        Args:
            language: Language key

        Returns:
            Dictionary with language-specific settings
        """
        try:
            # This would integrate with ConfigurationService to get language-specific settings
            # For now, return default configuration
            return {
                'language': language,
                'supported': self.is_language_supported(language),
                'extensions': self.get_extension_for_language(language),
                'has_tree_sitter_support': self._has_tree_sitter_support(language),
                'default_config': self._get_default_language_config(language)
            }
        except Exception as e:
            error_context = ErrorContext(
                component="language_detection",
                operation="get_language_config",
                additional_data={"language": language}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.LOW
            )
            print(f"Warning: {error_response.message}")
            return {
                'language': language,
                'supported': False,
                'error': str(e)
            }

    def _has_tree_sitter_support(self, language: str) -> bool:
        """
        Check if a language has Tree-sitter support.

        Args:
            language: Language key

        Returns:
            True if Tree-sitter support is available
        """
        # This would check if tree-sitter-language-pack has the language
        # For now, assume most common languages have support
        tree_sitter_supported = {
            'python', 'javascript', 'typescript', 'tsx', 'go', 'java', 'cpp', 'c',
            'rust', 'csharp', 'ruby', 'php', 'kotlin', 'swift', 'lua', 'dart',
            'scala', 'bash', 'html', 'css', 'scss', 'json', 'yaml', 'markdown',
            'sql', 'dockerfile', 'toml', 'xml', 'cmake'
        }
        return language in tree_sitter_supported

    def _get_default_language_config(self, language: str) -> Dict[str, Any]:
        """
        Get default configuration for a language.

        Args:
            language: Language key

        Returns:
            Dictionary with default language configuration
        """
        # Language-specific default configurations
        defaults = {
            'python': {
                'max_file_size_mb': 10,
                'skip_patterns': ['__pycache__', '.pyc', '.pyo'],
                'test_patterns': ['test_', '_test', 'tests/']
            },
            'rust': {
                'max_file_size_mb': 5,
                'skip_patterns': ['target/', 'build/', 'dist/'],
                'test_patterns': ['test', 'tests/', 'benches/']
            },
            'javascript': {
                'max_file_size_mb': 8,
                'skip_patterns': ['node_modules/', 'dist/', 'build/'],
                'test_patterns': ['test', 'spec', '__test__']
            },
            'typescript': {
                'max_file_size_mb': 8,
                'skip_patterns': ['node_modules/', 'dist/', 'build/'],
                'test_patterns': ['test', 'spec', '__test__']
            }
        }

        return defaults.get(language, {
            'max_file_size_mb': 10,
            'skip_patterns': [],
            'test_patterns': []
        })