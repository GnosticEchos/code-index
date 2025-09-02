"""
Cache utilities and manager for the code index tool.
- Centralizes cache directory resolution
- Provides reusable deletion helpers for cache artifacts
- Maintains backward-compatible CacheManager for per-file hash cache
"""
import json
import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Optional platformdirs support (preferred fallback)
try:
    from platformdirs import user_cache_dir as _user_cache_dir  # type: ignore
except Exception:  # pragma: no cover - import-time environment variance
    _user_cache_dir = None


def resolve_cache_dir(config: Optional[Any] = None) -> Path:
    """
    Determine the application cache directory for code_index.

    Resolution order:
    1) If config has attribute 'cache_dir' and it's a non-empty string/pathlike, use it.
    2) Use platformdirs.user_cache_dir('code_index') when available.
    3) XDG base dir semantics: $XDG_CACHE_HOME/code_index or ~/.cache/code_index

    Note: This function MUST NOT create the directory. Callers that write files
    may create it as needed; cleanup operations should treat a missing dir as a no-op.
    """
    # Config-provided directory (future-friendly)
    try:
        if config is not None:
            cfg_dir = getattr(config, "cache_dir", None)
            if cfg_dir:
                return Path(cfg_dir)
    except Exception:
        # Ignore config attribute errors; continue to fallback
        pass

    # Preferred: platformdirs
    if _user_cache_dir:
        try:
            return Path(_user_cache_dir("code_index"))
        except Exception:
            # Fall through to XDG fallback
            pass

    # XDG fallback
    xdg_base = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_base) if xdg_base else (Path.home() / ".cache")
    return base / "code_index"


def delete_collection_cache(canonical_id: str, config: Optional[Any] = None) -> int:
    """
    Delete cache file(s) for one canonical collection identifier.

    Inputs:
        canonical_id: 16-character hex id used in cache filename (not display name)
        config: Optional Config to honor a configured cache directory

    Behavior:
        - Remove file matching exactly 'cache_{id}.json' in the resolved cache dir.
        - Return integer count of files removed (0 or 1).
        - Missing directory: return 0 (no error).
        - On removal errors: log WARNING and continue.

    Logging:
        - INFO: final count removed
        - WARNING: individual file removal errors
    """
    cache_dir = resolve_cache_dir(config)
    if not cache_dir.exists():
        logger.info(f"Cache cleanup: removed 0 file(s) for collection id {canonical_id} (no cache dir)")
        return 0

    removed = 0
    target = cache_dir / f"cache_{canonical_id}.json"
    if target.exists():
        try:
            target.unlink()
            removed = 1
        except (OSError, IOError) as e:
            logger.warning(f"Cache cleanup: could not remove '{target}': {e}")

    logger.info(
        f"Cache cleanup: removed {removed} file(s) for collection id {canonical_id} from {cache_dir}"
    )
    return removed


def clear_all_caches(config: Optional[Any] = None) -> int:
    """
    Remove all collection cache artifacts.

    Behavior:
        - Remove all files matching 'cache_*.json' under the resolved cache directory.
        - Return integer count of files removed.
        - Missing directory: return 0 (no error).
        - On removal errors: log WARNING and continue.

    Logging:
        - INFO: final count removed
        - WARNING: individual file removal errors
    """
    cache_dir = resolve_cache_dir(config)
    if not cache_dir.exists():
        logger.info("Cache cleanup: removed 0 file(s) from cache directory (no cache dir)")
        return 0

    removed = 0
    try:
        for p in cache_dir.glob("cache_*.json"):
            if not p.is_file():
                continue
            try:
                p.unlink()
                removed += 1
            except (OSError, IOError) as e:
                logger.warning(f"Cache cleanup: could not remove '{p}': {e}")
    except Exception as e:  # pragma: no cover - unexpected filesystem errors
        logger.warning(f"Cache cleanup: directory scan error for '{cache_dir}': {e}")

    logger.info(f"Cache cleanup: removed {removed} file(s) from {cache_dir}")
    return removed


class CacheManager:
    """Manages file hashes to avoid reprocessing unchanged files."""

    def __init__(self, workspace_path: str, config: Optional[Any] = None):
        """Initialize cache manager for a workspace."""
        self.workspace_path = os.path.abspath(workspace_path)
        self._config = config
        self.cache_path = self._generate_cache_path()
        self.file_hashes: Dict[str, str] = self._load_cache()

    def _generate_cache_path(self) -> str:
        """Generate cache file path based on workspace path."""
        workspace_hash = hashlib.sha256(self.workspace_path.encode()).hexdigest()
        cache_dir = resolve_cache_dir(self._config)
        # Do not create the directory here; _save_cache will ensure it exists when writing
        return str(Path(cache_dir) / f"cache_{workspace_hash[:16]}.json")

    def _load_cache(self) -> Dict[str, str]:
        """Load cache from file."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                return {}
        return {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(self.file_hashes, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: Could not save cache to {self.cache_path}: {e}")

    def get_hash(self, file_path: str) -> Optional[str]:
        """Get hash for file path."""
        return self.file_hashes.get(file_path)

    def update_hash(self, file_path: str, file_hash: str) -> None:
        """Update hash for file path."""
        self.file_hashes[file_path] = file_hash
        self._save_cache()

    def delete_hash(self, file_path: str) -> None:
        """Delete hash for file path."""
        if file_path in self.file_hashes:
            del self.file_hashes[file_path]
            self._save_cache()

    def get_all_hashes(self) -> Dict[str, str]:
        """Get a copy of all file hashes."""
        return self.file_hashes.copy()

    def clear_cache(self) -> None:
        """Clear all cache data for this workspace."""
        self.file_hashes.clear()
        try:
            if os.path.exists(self.cache_path):
                os.remove(self.cache_path)
        except (IOError, OSError) as e:
            print(f"Warning: Could not delete cache file {self.cache_path}: {e}")