"""
Path utilities for the code index tool.
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class PathUtils:
    """
    Centralized utilities for path operations and validation.

    This class consolidates path handling logic that was previously
    scattered across multiple modules.
    """

    def __init__(self, error_handler: ErrorHandler, workspace_root: Optional[str] = None):
        """
        Initialize the PathUtils.

        Args:
            error_handler: ErrorHandler instance for structured error handling
            workspace_root: Optional workspace root directory for path operations
        """
        self.error_handler = error_handler
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None

    def normalize_path(self, path: str) -> str:
        """
        Normalize a path to use consistent separators and resolve relative components.

        Args:
            path: Path to normalize

        Returns:
            Normalized path string
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="normalize_path",
            additional_data={"original_path": path}
        )

        try:
            if path is None:
                return None

            if not path:
                return ""

            # Use pathlib for robust path normalization
            path_obj = Path(path)

            # If workspace root is set and path is relative, resolve relative to workspace
            if self.workspace_root and not path_obj.is_absolute():
                path_obj = self.workspace_root / path_obj

            normalized = path_obj.resolve()

            # Convert back to string with forward slashes for consistency
            return str(normalized).replace('\\', '/')

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            # Return original path if normalization fails
            return path or ""

    def resolve_workspace_path(self, path: str, workspace_root: str) -> str:
        """
        Resolve a path relative to the workspace root.
 
        Args:
            path: Path to resolve (can be relative or absolute)
            workspace_root: Root directory of the workspace
 
        Returns:
            Absolute path resolved relative to workspace root
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="resolve_workspace_path",
            additional_data={"path": path, "workspace_root": workspace_root}
        )
 
        try:
            # Normalize workspace root
            normalized_workspace = self.normalize_path(workspace_root)
 
            # Ensure workspace root exists; resolve() will return an absolute path even if it doesn't exist,
            # so explicitly check filesystem existence to avoid masking invalid workspace roots.
            if not normalized_workspace or not os.path.exists(normalized_workspace):
                raise ValueError("Invalid workspace root")
 
            # If path is already absolute, normalize it
            if os.path.isabs(path):
                return self.normalize_path(path)
 
            # Resolve relative to workspace without allowing path resolution to escape unexpectedly
            workspace_path = Path(normalized_workspace)
            resolved_path = (workspace_path / path).resolve()
            return str(resolved_path).replace('\\', '/')
 
        except Exception as e:
            # Surface the error so callers/tests can handle it explicitly
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            raise e

    def calculate_relative_path(self, absolute_path: str, base_path: str) -> str:
        """
        Calculate the relative path from base_path to absolute_path.

        Args:
            absolute_path: Absolute path to calculate relative path for
            base_path: Base path to calculate relative to

        Returns:
            Relative path from base_path to absolute_path
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="calculate_relative_path",
            additional_data={"absolute_path": absolute_path, "base_path": base_path}
        )

        try:
            # Normalize both paths
            normalized_absolute = self.normalize_path(absolute_path)
            normalized_base = self.normalize_path(base_path)

            if not normalized_absolute or not normalized_base:
                raise ValueError("Invalid path provided")

            # Use pathlib for relative path calculation
            abs_path = Path(normalized_absolute)
            base_path_obj = Path(normalized_base)

            try:
                relative_path = abs_path.relative_to(base_path_obj)
                return str(relative_path).replace('\\', '/')
            except ValueError:
                # If paths are not relative, return absolute path
                return normalized_absolute

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            # Return absolute path as fallback
            return absolute_path

    def validate_path_access(self, path: str, required_permissions: str = "read") -> Tuple[bool, Optional[str]]:
        """
        Validate that a path is accessible with the required permissions.

        Args:
            path: Path to validate
            required_permissions: Required permissions ("read", "write", "execute")

        Returns:
            Tuple of (is_valid, error_message)
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="validate_path_access",
            file_path=path,
            additional_data={"required_permissions": required_permissions}
        )

        try:
            if not path or not path.strip():
                return False, "Empty path provided"

            # Normalize path
            normalized_path = self.normalize_path(path)

            # Check if path exists
            if not os.path.exists(normalized_path):
                return False, f"Path does not exist: {normalized_path}"

            # Check required permissions
            if required_permissions == "read" or required_permissions == "execute":
                if not os.access(normalized_path, os.R_OK):
                    return False, f"Path is not readable: {normalized_path}"

            if required_permissions == "write":
                if not os.access(normalized_path, os.W_OK):
                    return False, f"Path is not writable: {normalized_path}"

            if required_permissions == "execute":
                if not os.access(normalized_path, os.X_OK):
                    return False, f"Path is not executable: {normalized_path}"

            return True, None

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return False, str(e)

    def is_path_within_workspace(self, path: str, workspace_root: str) -> bool:
        """
        Check if a path is within the workspace root directory.

        Args:
            path: Path to check
            workspace_root: Workspace root directory

        Returns:
            True if path is within workspace
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="is_path_within_workspace",
            additional_data={"path": path, "workspace_root": workspace_root}
        )

        try:
            # Normalize both paths
            normalized_path = self.normalize_path(path)
            normalized_workspace = self.normalize_path(workspace_root)

            if not normalized_path or not normalized_workspace:
                return False

            # Use pathlib for robust containment check
            path_obj = Path(normalized_path)
            workspace_obj = Path(normalized_workspace)

            try:
                path_obj.relative_to(workspace_obj)
                return True
            except ValueError:
                return False

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return False

    def get_path_segments(self, path: str, max_segments: int = 5) -> List[str]:
        """
        Split a path into segments for efficient filtering.
 
        Args:
            path: Path to split
            max_segments: Maximum number of segments to return
 
        Returns:
            List of path segments
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="get_path_segments",
            file_path=path,
            additional_data={"max_segments": max_segments}
        )
 
        try:
            if not path:
                return []
 
            # Normalize Windows-style backslashes to forward slashes first
            unified = path.replace('\\', '/')
 
            # If absolute path (after unifying), perform full normalization and preserve absolute-ness
            if os.path.isabs(unified):
                normalized_path = self.normalize_path(unified)
                if not normalized_path:
                    return []
                path_to_split = normalized_path.lstrip('/')
            else:
                # For relative paths, avoid resolving to absolute; just normalize separators
                path_to_split = Path(unified).as_posix().lstrip('./')
 
            # Split and filter empty segments
            segments = [s for s in path_to_split.split('/') if s]
 
            # Limit to max_segments
            return segments[:max_segments]
 
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return []

    def find_common_path_prefix(self, paths: List[str]) -> Optional[str]:
        """
        Find the common path prefix among multiple paths.
 
        Args:
            paths: List of paths to find common prefix for
 
        Returns:
            Common path prefix, or None if no common prefix found
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="find_common_path_prefix",
            additional_data={"paths_count": len(paths)}
        )
 
        try:
            if not paths:
                return None
 
            if len(paths) == 1:
                return self.normalize_path(paths[0])
 
            # Prefer to compute common prefix among absolute paths only (ignore relative paths)
            absolute_inputs = [p for p in paths if p and os.path.isabs(p)]
            if absolute_inputs:
                normalized_paths = [self.normalize_path(p) for p in absolute_inputs]
            else:
                # Fallback: normalize all paths (could be relative)
                normalized_paths = [self.normalize_path(p) for p in paths if p]
 
            if not normalized_paths:
                return None
 
            # Start with first path as potential prefix
            common_prefix = normalized_paths[0]
 
            # Check each subsequent path
            for path in normalized_paths[1:]:
                # Find common prefix between current common_prefix and path
                common_prefix = self._find_common_prefix(common_prefix, path)
                if not common_prefix:
                    return None
 
            return common_prefix
 
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return None

    def _find_common_prefix(self, path1: str, path2: str) -> Optional[str]:
        """Find common prefix between two paths."""
        try:
            path1_parts = path1.split('/')
            path2_parts = path2.split('/')
 
            # Remove empty parts
            path1_parts = [p for p in path1_parts if p]
            path2_parts = [p for p in path2_parts if p]
 
            # Find common parts
            common_parts = []
            for p1, p2 in zip(path1_parts, path2_parts):
                if p1 == p2:
                    common_parts.append(p1)
                else:
                    break
 
            if common_parts:
                prefix = '/'.join(common_parts)
                # Preserve leading slash if both inputs were absolute
                if path1.startswith('/') and path2.startswith('/'):
                    return '/' + prefix
                return prefix
            else:
                return None
 
        except Exception:
            return None

    def sanitize_path_for_storage(self, path: str) -> str:
        """
        Sanitize a path for safe storage in databases or file systems.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path string
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="sanitize_path_for_storage",
            file_path=path
        )

        try:
            if path is None:
                return None

            if not path:
                return ""

            # First remove dangerous characters that could cause path resolution to fail
            cleaned_path = path.replace('\x00', '').replace('\\\\', '/')
            # Remove all control characters
            cleaned_path = ''.join(c for c in cleaned_path if ord(c) >= 32)

            # Use pathlib for robust path handling
            path_obj = Path(cleaned_path)

            # Resolve the path to handle .. and . components
            try:
                resolved = path_obj.resolve()
            except (OSError, RuntimeError):
                # If resolution fails, try to clean the path manually
                resolved = path_obj

            # Convert to string and do final cleanup
            sanitized = str(resolved)

            # Remove any remaining .. patterns (shouldn't be any after resolve, but just in case)
            while '..' in sanitized:
                sanitized = sanitized.replace('..', '')

            # Additional cleanup for backslashes and repeated slashes
            sanitized = sanitized.replace('\\\\', '/').replace('//', '/')

            # Handle mixed separators and remaining dangerous patterns
            while '\\\\' in sanitized or '//' in sanitized:
                sanitized = sanitized.replace('\\\\', '/').replace('//', '/')

            # Preserve leading slash for absolute paths
            if path.startswith('/') or path.startswith('\\'):
                if not sanitized.startswith('/'):
                    sanitized = '/' + sanitized

            return sanitized

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return path

    def join_path(self, *paths: str) -> str:
        """
        Join multiple path components into a single path.

        Args:
            *paths: Path components to join

        Returns:
            Joined path string
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="join_path",
            additional_data={"paths": paths}
        )

        try:
            if not paths:
                return ""

            # Use pathlib for robust path joining
            joined_path = Path(*paths)
            return str(joined_path).replace('\\', '/')

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            # Fallback to string joining with forward slashes
            return "/".join(paths).replace('\\', '/')

    def is_path_safe(self, path: str) -> bool:
        """
        Check if a path is safe (within workspace and accessible).

        Args:
            path: Path to check

        Returns:
            True if path is safe, False otherwise
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="is_path_safe",
            file_path=path
        )

        try:
            if not path:
                return False

            # Normalize path
            normalized_path = self.normalize_path(path)

            # Check if path is within workspace (if workspace is set)
            if self.workspace_root:
                try:
                    Path(normalized_path).relative_to(self.workspace_root)
                except ValueError:
                    return False

            # Check if path exists and is readable (only if it exists)
            if os.path.exists(normalized_path):
                if not os.access(normalized_path, os.R_OK):
                    return False

            return True

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return False

    def make_path_relative(self, path: str, base_path: Optional[str] = None) -> Optional[str]:
        """
        Make a path relative to a base path.

        Args:
            path: Path to make relative
            base_path: Base path to make relative to (defaults to workspace_root)

        Returns:
            Relative path or None if cannot be made relative
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="make_path_relative",
            file_path=path,
            additional_data={"base_path": base_path}
        )

        try:
            if not path:
                return None

            # Use workspace_root as base if no base_path provided
            if base_path is None:
                base_path = str(self.workspace_root) if self.workspace_root else None

            if not base_path:
                return path

            # Normalize both paths
            normalized_path = self.normalize_path(path)
            normalized_base = self.normalize_path(base_path)

            # Calculate relative path
            try:
                path_obj = Path(normalized_path)
                base_obj = Path(normalized_base)
                relative_path = path_obj.relative_to(base_obj)
                return str(relative_path).replace('\\', '/')
            except ValueError:
                # Cannot make relative, return absolute path
                return normalized_path

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return None

    def sanitize_path(self, path: str) -> str:
        """
        Sanitize a path by removing dangerous components.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="sanitize_path",
            file_path=path
        )

        try:
            if path is None:
                return None

            if not path:
                return ""

            # First remove dangerous characters that could cause path resolution to fail
            cleaned_path = path.replace('\x00', '').replace('\\\\', '/')

            # Remove all control characters
            cleaned_path = ''.join(c for c in cleaned_path if ord(c) >= 32)

            # Use pathlib for robust path handling
            path_obj = Path(cleaned_path)

            # Resolve the path to handle .. and . components
            try:
                resolved = path_obj.resolve()
            except (OSError, RuntimeError):
                # If resolution fails, try to clean the path manually
                resolved = path_obj

            # Convert to string and do final cleanup
            sanitized = str(resolved)

            # Remove any remaining .. patterns (shouldn't be any after resolve, but just in case)
            while '..' in sanitized:
                sanitized = sanitized.replace('..', '')

            # Additional cleanup for backslashes and repeated slashes
            sanitized = sanitized.replace('\\\\', '/').replace('//', '/')

            # Handle mixed separators and remaining dangerous patterns
            while '\\\\' in sanitized or '//' in sanitized:
                sanitized = sanitized.replace('\\\\', '/').replace('//', '/')

            # Preserve leading slash for absolute paths
            if path.startswith('/') or path.startswith('\\'):
                if not sanitized.startswith('/'):
                    sanitized = '/' + sanitized

            return sanitized

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return path or ""

    def validate_and_normalize(self, path: str) -> Optional[str]:
        """
        Validate and normalize a path.

        Args:
            path: Path to validate and normalize

        Returns:
            Validated and normalized path, or None if invalid
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="validate_and_normalize",
            file_path=path
        )

        try:
            if not path:
                return None

            # Normalize path
            normalized = self.normalize_path(path)

            # Check if path is within workspace (if workspace is set)
            if self.workspace_root:
                try:
                    Path(normalized).relative_to(self.workspace_root)
                except ValueError:
                    return None

            return normalized

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return None

    def get_relative_path_segments(self, path: str) -> List[str]:
        """
        Get relative path segments for a path.

        Args:
            path: Path to get segments for

        Returns:
            List of path segments
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="get_relative_path_segments",
            file_path=path
        )

        try:
            if not path:
                return []

            # Get relative path from workspace root
            if self.workspace_root:
                try:
                    relative_path = Path(path).relative_to(self.workspace_root)
                    segments = [str(segment) for segment in relative_path.parts]
                    return segments
                except ValueError:
                    pass

            # Fallback to regular path segments
            return self.get_path_segments(path)

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return []

    def is_subpath(self, path: str, parent_path: Optional[str] = None) -> bool:
        """
        Check if path is a subpath of parent_path.

        Args:
            path: Path to check
            parent_path: Parent path to check against (defaults to workspace_root)

        Returns:
            True if path is a subpath of parent_path
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="is_subpath",
            file_path=path,
            additional_data={"parent_path": parent_path}
        )

        try:
            if not path:
                return False

            # Use workspace_root as parent if no parent_path provided
            if parent_path is None:
                parent_path = str(self.workspace_root) if self.workspace_root else None

            if not parent_path:
                return False

            # Normalize both paths
            normalized_path = self.normalize_path(path)
            normalized_parent = self.normalize_path(parent_path)

            # Check if path is within parent
            try:
                Path(normalized_path).relative_to(Path(normalized_parent))
                return True
            except ValueError:
                return False

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return False

    def get_workspace_relative_path(self, path: str) -> Optional[str]:
        """
        Get path relative to workspace root.

        Args:
            path: Path to get relative path for

        Returns:
            Path relative to workspace root, or None if not within workspace
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="get_workspace_relative_path",
            file_path=path
        )

        try:
            if not path or not self.workspace_root:
                return None

            # Normalize path
            normalized_path = self.normalize_path(path)

            # Get relative path
            try:
                relative_path = Path(normalized_path).relative_to(self.workspace_root)
                return str(relative_path).replace('\\', '/')
            except ValueError:
                # Path is outside workspace, return None
                return None

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return None

    def resolve_path(self, path: str) -> Optional[str]:
        """
        Resolve a path to its absolute form.

        Args:
            path: Path to resolve

        Returns:
            Resolved absolute path, or None if cannot be resolved
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="resolve_path",
            file_path=path
        )

        try:
            if not path:
                return None

            # Use pathlib for robust path resolution
            path_obj = Path(path)

            # If workspace root is set and path is relative, resolve relative to workspace
            if self.workspace_root and not path_obj.is_absolute():
                path_obj = self.workspace_root / path_obj

            resolved = path_obj.resolve()
            return str(resolved).replace('\\', '/')

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return None

    def __repr__(self) -> str:
        """
        String representation of PathUtils.

        Returns:
            String representation including workspace_root
        """
        workspace_info = f"workspace_root={self.workspace_root}" if self.workspace_root else "workspace_root=None"
        return f"<{self.__class__.__name__} {workspace_info}>"

    def get_file_extension(self, path: str) -> str:
        """
        Get the file extension from a path.

        Args:
            path: Path to get extension from

        Returns:
            File extension (including the dot)
        """
        error_context = ErrorContext(
            component="path_utils",
            operation="get_file_extension",
            file_path=path
        )

        try:
            if not path:
                return ""

            # Use pathlib for robust extension extraction
            path_obj = Path(path)
            return path_obj.suffix.lower()

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            # Fallback to string splitting
            parts = path.split('.')
            return "." + parts[-1].lower() if len(parts) > 1 else ""