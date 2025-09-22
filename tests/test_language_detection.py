"""
Unit tests for the Language Detection Service.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from code_index.language_detection import LanguageDetector, UnsupportedLanguageError
from code_index.config import Config
from code_index.errors import ErrorHandler


class TestLanguageDetector:
    """Test cases for LanguageDetector class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config()

    @pytest.fixture
    def error_handler(self):
        """Create a test error handler."""
        return ErrorHandler()

    @pytest.fixture
    def language_detector(self, config, error_handler):
        """Create a LanguageDetector instance for testing."""
        return LanguageDetector(config, error_handler)

    def test_detect_language_python(self, language_detector):
        """Test language detection for Python files."""
        assert language_detector.detect_language("test.py") == "python"
        assert language_detector.detect_language("script.py") == "python"
        assert language_detector.detect_language("module.py") == "python"

    def test_detect_language_javascript(self, language_detector):
        """Test language detection for JavaScript files."""
        assert language_detector.detect_language("app.js") == "javascript"
        assert language_detector.detect_language("component.jsx") == "javascript"
        assert language_detector.detect_language("script.js") == "javascript"

    def test_detect_language_typescript(self, language_detector):
        """Test language detection for TypeScript files."""
        assert language_detector.detect_language("app.ts") == "typescript"
        assert language_detector.detect_language("component.tsx") == "tsx"
        assert language_detector.detect_language("types.ts") == "typescript"

    def test_detect_language_rust(self, language_detector):
        """Test language detection for Rust files."""
        assert language_detector.detect_language("main.rs") == "rust"
        assert language_detector.detect_language("lib.rs") == "rust"
        assert language_detector.detect_language("Cargo.toml") == "toml"

    def test_detect_language_go(self, language_detector):
        """Test language detection for Go files."""
        assert language_detector.detect_language("main.go") == "go"
        assert language_detector.detect_language("server.go") == "go"

    def test_detect_language_java(self, language_detector):
        """Test language detection for Java files."""
        assert language_detector.detect_language("Main.java") == "java"
        assert language_detector.detect_language("Test.java") == "java"

    def test_detect_language_cpp(self, language_detector):
        """Test language detection for C++ files."""
        assert language_detector.detect_language("main.cpp") == "cpp"
        assert language_detector.detect_language("header.hpp") == "cpp"
        assert language_detector.detect_language("source.cxx") == "cpp"

    def test_detect_language_c(self, language_detector):
        """Test language detection for C files."""
        assert language_detector.detect_language("main.c") == "c"
        assert language_detector.detect_language("header.h") == "c"

    def test_detect_language_web_frameworks(self, language_detector):
        """Test language detection for web frameworks."""
        assert language_detector.detect_language("App.vue") == "vue"
        assert language_detector.detect_language("Component.svelte") == "svelte"
        assert language_detector.detect_language("Page.astro") == "astro"

    def test_detect_language_config_files(self, language_detector):
        """Test language detection for configuration files."""
        assert language_detector.detect_language("package.json") == "json"
        assert language_detector.detect_language("tsconfig.json") == "json"
        assert language_detector.detect_language("pyproject.toml") == "toml"
        assert language_detector.detect_language("config.yaml") == "yaml"
        assert language_detector.detect_language("config.yml") == "yaml"

    def test_detect_language_special_filenames(self, language_detector):
        """Test language detection for special filenames."""
        assert language_detector.detect_language("Dockerfile") == "dockerfile"
        assert language_detector.detect_language("Makefile") == "makefile"
        assert language_detector.detect_language("CMakeLists.txt") == "cmake"

    def test_detect_language_unsupported_extension(self, language_detector):
        """Test language detection for unsupported file extensions."""
        assert language_detector.detect_language("unknown.xyz") is None
        assert language_detector.detect_language("test.unknown") is None

    def test_detect_language_no_extension(self, language_detector):
        """Test language detection for files without extensions."""
        assert language_detector.detect_language("README") is None
        assert language_detector.detect_language("LICENSE") is None

    def test_is_language_supported(self, language_detector):
        """Test language support checking."""
        assert language_detector.is_language_supported("python") is True
        assert language_detector.is_language_supported("javascript") is True
        assert language_detector.is_language_supported("typescript") is True
        assert language_detector.is_language_supported("rust") is True
        assert language_detector.is_language_supported("unknown_language") is False

    def test_validate_language(self, language_detector):
        """Test language validation."""
        assert language_detector.validate_language("python") is True
        assert language_detector.validate_language("javascript") is True
        assert language_detector.validate_language("unknown_language") is False

    def test_get_supported_languages(self, language_detector):
        """Test getting supported languages."""
        supported = language_detector.get_supported_languages()
        assert isinstance(supported, set)
        assert "python" in supported
        assert "javascript" in supported
        assert "typescript" in supported
        assert "rust" in supported

    def test_get_language_for_extension(self, language_detector):
        """Test getting language for extension."""
        assert language_detector.get_language_for_extension("py") == "python"
        assert language_detector.get_language_for_extension("js") == "javascript"
        assert language_detector.get_language_for_extension("ts") == "typescript"
        assert language_detector.get_language_for_extension("rs") == "rust"
        assert language_detector.get_language_for_extension("xyz") is None

    def test_get_extension_for_language(self, language_detector):
        """Test getting extensions for language."""
        python_exts = language_detector.get_extension_for_language("python")
        assert ".py" in python_exts

        js_exts = language_detector.get_extension_for_language("javascript")
        assert ".js" in js_exts
        assert ".jsx" in js_exts

        unknown_exts = language_detector.get_extension_for_language("unknown")
        assert unknown_exts == []

    def test_cache_functionality(self, language_detector):
        """Test language detection caching."""
        # First call should cache the result
        result1 = language_detector.detect_language("test.py")
        assert result1 == "python"

        # Second call should use cache
        result2 = language_detector.detect_language("test.py")
        assert result2 == "python"

        # Check cache info
        cache_info = language_detector.get_cache_info()
        assert cache_info["cache_size"] == 1
        assert cache_info["supported_languages_count"] > 0

    def test_clear_cache(self, language_detector):
        """Test cache clearing."""
        # Add something to cache
        language_detector.detect_language("test.py")
        assert language_detector.get_cache_info()["cache_size"] == 1

        # Clear cache
        language_detector.clear_cache()
        assert language_detector.get_cache_info()["cache_size"] == 0

    def test_get_language_config(self, language_detector):
        """Test getting language-specific configuration."""
        config = language_detector.get_language_config("python")
        assert config["language"] == "python"
        assert config["supported"] is True
        assert "extensions" in config
        assert "has_tree_sitter_support" in config

    def test_get_language_config_unsupported(self, language_detector):
        """Test getting configuration for unsupported language."""
        config = language_detector.get_language_config("unknown_language")
        assert config["language"] == "unknown_language"
        assert config["supported"] is False
        assert "extensions" in config
        assert "has_tree_sitter_support" in config
        assert "default_config" in config

    def test_error_handling(self, language_detector):
        """Test error handling in language detection."""
        # Test with invalid file path
        result = language_detector.detect_language("")
        assert result is None

        result = language_detector.detect_language(None)
        assert result is None

    @patch('code_index.language_detection.LanguageDetector._detect_by_extension')
    def test_extension_detection_error_handling(self, mock_detect, language_detector):
        """Test error handling in extension detection."""
        mock_detect.side_effect = Exception("Test error")

        result = language_detector.detect_language("test.py")
        assert result is None

    @patch('code_index.language_detection.LanguageDetector._detect_by_filename')
    def test_filename_detection_error_handling(self, mock_detect, language_detector):
        """Test error handling in filename detection."""
        mock_detect.side_effect = Exception("Test error")

        result = language_detector.detect_language("Dockerfile")
        assert result is None

    def test_language_detection_with_complex_paths(self, language_detector):
        """Test language detection with complex file paths."""
        # Test with nested paths
        assert language_detector.detect_language("/path/to/project/src/main.py") == "python"
        assert language_detector.detect_language("./relative/path/component.tsx") == "tsx"
        assert language_detector.detect_language("../parent/dir/lib.rs") == "rust"

        # Test with spaces and special characters
        assert language_detector.detect_language("my project/file.py") == "python"
        assert language_detector.detect_language("file-with-dashes.js") == "javascript"

    def test_case_sensitivity(self, language_detector):
        """Test case sensitivity in language detection."""
        # Extensions should be case-insensitive
        assert language_detector.detect_language("file.PY") == "python"
        assert language_detector.detect_language("file.JS") == "javascript"
        assert language_detector.detect_language("file.TS") == "typescript"

        # Filenames should be case-insensitive
        assert language_detector.detect_language("DOCKERFILE") == "dockerfile"
        assert language_detector.detect_language("MAKEFILE") == "makefile"

    def test_multiple_dots_in_filename(self, language_detector):
        """Test language detection with multiple dots in filename."""
        assert language_detector.detect_language("my.test.file.py") == "python"
        assert language_detector.detect_language("component.test.tsx") == "tsx"
        assert language_detector.detect_language("file.min.js") == "javascript"

    def test_hidden_files(self, language_detector):
        """Test language detection for hidden files."""
        assert language_detector.detect_language(".gitignore") is None
        assert language_detector.detect_language(".hidden.py") == "python"
        assert language_detector.detect_language(".config.js") == "javascript"