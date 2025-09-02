"""
Enhanced directory scanner with smart ignore pattern integration.
"""
import os
from typing import List, Set, Tuple
from code_index.config import Config
from code_index.utils import (
    is_binary_file,
    load_gitignore_patterns,
    matches_pattern,
    normalize_path,
    augment_extensions_with_pygments,
)
from code_index.smart_ignore_manager import SmartIgnoreManager


class EnhancedDirectoryScanner:
    """Enhanced directory scanner with smart ignore pattern integration."""
    
    def __init__(self, config: Config):
        """Initialize enhanced directory scanner with configuration."""
        self.config = config
        self.workspace_path = os.path.abspath(config.workspace_path)
        
        # Initialize smart ignore manager
        self.ignore_manager = SmartIgnoreManager(
            self.workspace_path, 
            config=getattr(config, '__dict__', {})
        )
    
    def _load_exclude_list(self) -> Set[str]:
        """Load exclude list as normalized relative paths from workspace root."""
        excluded: Set[str] = set()
        path = getattr(self.config, "exclude_files_path", None)
        if not path:
            return excluded
        # Allow absolute or relative path to exclude file
        exclude_file_path = path
        if not os.path.isabs(exclude_file_path):
            exclude_file_path = os.path.join(self.workspace_path, exclude_file_path)
        if not os.path.exists(exclude_file_path):
            return excluded
        try:
            with open(exclude_file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Normalize each line to relpath
                    if os.path.isabs(line):
                        rel = os.path.relpath(line, self.workspace_path)
                    else:
                        rel = line
                    # Normalize consistently
                    rel = os.path.normpath(rel)
                    excluded.add(rel)
        except (OSError, IOError):
            # Non-fatal: treat as no excludes
            return excluded
        return excluded

    def _compute_extension_set(self) -> Set[str]:
        """Compute effective extension set with optional auto-augmentation."""
        base = [e.lower() for e in getattr(self.config, "extensions", [])]
        if getattr(self.config, "auto_extensions", False):
            base = augment_extensions_with_pygments(base)
        return set(base)
def _should_skip_dot_file(self, name: str) -> bool:
        """Check if a file/directory should be skipped as a dot file."""
        if not getattr(self.config, 'skip_dot_files', True):
            return False
            
        # Skip dot files/directories except .gitignore
        if name.startswith('.'):
            return name != '.gitignore'
        return False

    def scan_directory(self, directory: str = None) -> Tuple[List[str], int]:
        """
        Recursively scan directory for supported files with enhanced ignore patterns.
        
        Args:
            directory: Directory to scan (defaults to workspace path)
            
        Returns:
            Tuple of (file_paths, skipped_count)
        """
        if directory is None:
            directory = self.workspace_path
        
        directory = os.path.abspath(directory)
        file_paths: List[str] = []
        skipped_count = 0
        
        # Load traditional ignore patterns and excludes
        ignore_patterns = load_gitignore_patterns(directory)
        excluded_relpaths = self._load_exclude_list()
        ext_set = self._compute_extension_set()
        
        # Walk through directory
        for root, dirs, files in os.walk(directory):
            # Early filtering: remove dot directories except .gitignore
            if getattr(self.config, 'skip_dot_files', True):
                dirs[:] = [d for d in dirs if not self._should_skip_dot_file(d)]
            
            # Remove ignored directories (traditional approach)
            dirs[:] = [d for d in dirs if not matches_pattern(os.path.join(root, d), ignore_patterns, directory)]
            
            # Early filtering: remove dot files except .gitignore
            if getattr(self.config, 'skip_dot_files', True):
                files = [f for f in files if not self._should_skip_dot_file(f)]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.workspace_path)
                rel_norm = os.path.normpath(rel_path)

                # Check exclude list (normalized)
                if rel_norm in excluded_relpaths:
                    skipped_count += 1
                    continue

                # Check if file should be ignored by traditional .gitignore patterns
                if matches_pattern(file_path, ignore_patterns, directory):
                    skipped_count += 1
                    continue
                
                # Check if file should be ignored by smart ignore patterns
                if self.ignore_manager.should_ignore_file(file_path):
                    skipped_count += 1
                    continue
                
                # Check file size early
                try:
                    if os.path.getsize(file_path) > self.config.max_file_size_bytes:
                        skipped_count += 1
                        continue
                except (OSError, IOError):
                    skipped_count += 1
                    continue
                
                # Check extension support (case-insensitive)
                _, ext = os.path.splitext(file.lower())
                if ext not in ext_set:
                    skipped_count += 1
                    continue
                
                # Check if file is binary
                if is_binary_file(file_path):
                    skipped_count += 1
                    continue
                
                file_paths.append(file_path)
        
        return file_paths, skipped_count