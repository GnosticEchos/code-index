"""
Test module for the PathUtils class.
"""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from code_index.path_utils import PathUtils
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


def test_path_utils_initialization():
    """Test PathUtils initialization."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    assert path_utils.error_handler == error_handler
    assert path_utils.workspace_root == Path("/test/workspace").resolve()


def test_normalize_path():
    """Test path normalization."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Test with absolute path
    normalized = path_utils.normalize_path("/test/workspace/file.py")
    assert normalized == str(Path("/test/workspace/file.py").resolve())
    
    # Test with relative path
    normalized = path_utils.normalize_path("file.py")
    # Should be resolved relative to workspace root
    expected = Path("/test/workspace/file.py").resolve()
    assert normalized == str(expected)


def test_normalize_path_with_none():
    """Test path normalization with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    normalized = path_utils.normalize_path(None)
    assert normalized is None


def test_is_path_safe_valid():
    """Test path safety validation with valid path."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Valid path within workspace
    is_safe = path_utils.is_path_safe("/test/workspace/file.py")
    assert is_safe == True


def test_is_path_safe_invalid():
    """Test path safety validation with invalid path."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Path outside workspace
    is_safe = path_utils.is_path_safe("/etc/passwd")
    assert is_safe == False


def test_is_path_safe_with_none():
    """Test path safety validation with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should be considered unsafe
    is_safe = path_utils.is_path_safe(None)
    assert is_safe == False


def test_make_path_relative():
    """Test making path relative to workspace."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Path within workspace
    relative_path = path_utils.make_path_relative("/test/workspace/subdir/file.py")
    assert relative_path == "subdir/file.py"
    
    # Path outside workspace (should return absolute path)
    relative_path = path_utils.make_path_relative("/etc/passwd")
    assert relative_path == "/etc/passwd"


def test_make_path_relative_with_none():
    """Test making path relative with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return None
    relative_path = path_utils.make_path_relative(None)
    assert relative_path is None


def test_get_path_segments():
    """Test getting path segments."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Normal path
    segments = path_utils.get_path_segments("/test/workspace/subdir/file.py")
    assert segments == ["test", "workspace", "subdir", "file.py"]
    
    # Path with Windows-style backslashes
    segments = path_utils.get_path_segments("test\\workspace\\subdir\\file.py")
    assert segments == ["test", "workspace", "subdir", "file.py"]
    
    # Path with mixed separators
    segments = path_utils.get_path_segments("test/workspace\\subdir/file.py")
    assert segments == ["test", "workspace", "subdir", "file.py"]


def test_get_path_segments_with_none():
    """Test getting path segments with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return empty list
    segments = path_utils.get_path_segments(None)
    assert segments == []


def test_get_path_segments_empty():
    """Test getting path segments with empty path."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Empty path should return empty list
    segments = path_utils.get_path_segments("")
    assert segments == []


def test_sanitize_path():
    """Test path sanitization."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Normal path
    sanitized = path_utils.sanitize_path("/test/workspace/file.py")
    assert sanitized == "/test/workspace/file.py"
    
    # Path with null bytes
    sanitized = path_utils.sanitize_path("/test/workspace/file\x00.py")
    assert sanitized == "/test/workspace/file.py"
    
    # Path with control characters
    sanitized = path_utils.sanitize_path("/test/workspace/file\n.py")
    assert sanitized == "/test/workspace/file.py"


def test_sanitize_path_with_none():
    """Test path sanitization with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return None
    sanitized = path_utils.sanitize_path(None)
    assert sanitized is None


def test_validate_and_normalize():
    """Test combined validation and normalization."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Valid path
    validated = path_utils.validate_and_normalize("/test/workspace/file.py")
    assert validated == str(Path("/test/workspace/file.py").resolve())
    
    # Invalid path (outside workspace)
    validated = path_utils.validate_and_normalize("/etc/passwd")
    assert validated is None


def test_validate_and_normalize_with_none():
    """Test combined validation and normalization with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return None
    validated = path_utils.validate_and_normalize(None)
    assert validated is None


def test_get_relative_path_segments():
    """Test getting relative path segments."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Path within workspace
    segments = path_utils.get_relative_path_segments("/test/workspace/subdir/file.py")
    assert segments == ["subdir", "file.py"]
    
    # Path outside workspace
    segments = path_utils.get_relative_path_segments("/etc/passwd")
    assert segments == ["etc", "passwd"]


def test_get_relative_path_segments_with_none():
    """Test getting relative path segments with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return empty list
    segments = path_utils.get_relative_path_segments(None)
    assert segments == []


def test_is_subpath():
    """Test checking if path is subpath of workspace."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Path within workspace
    is_subpath = path_utils.is_subpath("/test/workspace/subdir/file.py")
    assert is_subpath == True
    
    # Path outside workspace
    is_subpath = path_utils.is_subpath("/etc/passwd")
    assert is_subpath == False
    
    # Workspace root itself
    is_subpath = path_utils.is_subpath("/test/workspace")
    assert is_subpath == True


def test_is_subpath_with_none():
    """Test checking if path is subpath with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return False
    is_subpath = path_utils.is_subpath(None)
    assert is_subpath == False


def test_get_workspace_relative_path():
    """Test getting workspace-relative path."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Path within workspace
    relative_path = path_utils.get_workspace_relative_path("/test/workspace/subdir/file.py")
    assert relative_path == "subdir/file.py"
    
    # Path outside workspace
    relative_path = path_utils.get_workspace_relative_path("/etc/passwd")
    assert relative_path is None


def test_get_workspace_relative_path_with_none():
    """Test getting workspace-relative path with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return None
    relative_path = path_utils.get_workspace_relative_path(None)
    assert relative_path is None


def test_resolve_path():
    """Test path resolution."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # Resolve relative path
    resolved = path_utils.resolve_path("subdir/file.py")
    expected = Path("/test/workspace/subdir/file.py").resolve()
    assert resolved == str(expected)
    
    # Resolve absolute path
    resolved = path_utils.resolve_path("/absolute/path/file.py")
    expected = Path("/absolute/path/file.py").resolve()
    assert resolved == str(expected)


def test_resolve_path_with_none():
    """Test path resolution with None."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    
    # None path should return None
    resolved = path_utils.resolve_path(None)
    assert resolved is None


def test_path_utils_repr():
    """Test PathUtils string representation."""
    error_handler = ErrorHandler("test")
    path_utils = PathUtils(error_handler, "/test/workspace")
    repr_str = repr(path_utils)
    assert "PathUtils" in repr_str
    assert "/test/workspace" in repr_str