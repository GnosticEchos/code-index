"""
Directory scanner for the code index tool.
"""
import os
import logging
from typing import List, Set, Tuple
from code_index.config import Config
from code_index.smart_ignore_manager import SmartIgnoreManager
from code_index.file_processing import FileProcessingService
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from code_index.path_utils import PathUtils

logger = logging.getLogger(__name__)


class DirectoryScanner:
    """Scans directories for code files."""
    
    def __init__(self, config: Config):
        """Initialize directory scanner with configuration."""
        self.config = config
        # Initialize path utilities first
        self.path_utils = PathUtils(ErrorHandler())
        self.workspace_path = self.path_utils.normalize_path(config.workspace_path)
        self.ignore_manager = SmartIgnoreManager(self.workspace_path, config)
        # Initialize file processing service
        self.file_processor = FileProcessingService(ErrorHandler())
    
    def _load_exclude_list(self) -> Set[str]:
        """Load exclude list as normalized relative paths from workspace root."""
        # Use the file processing service initialized in the class
        path = getattr(self.config, "exclude_files_path", None)
        return self.file_processor.load_exclude_list(self.workspace_path, path, "load_exclude_list")

    def _compute_extension_set(self) -> Set[str]:
        """Compute effective extension set with optional auto-augmentation."""
        base = [e.lower() for e in getattr(self.config, "extensions", [])]
        if getattr(self.config, "auto_extensions", False):
            base = self.file_processor.augment_extensions_with_pygments(base)
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
        Recursively scan directory for supported files.
        
        Args:
            directory: Directory to scan (defaults to workspace path)
            
        Returns:
            Tuple of (file_paths, skipped_count)
        """
        if directory is None:
            directory = self.workspace_path

        directory = self.path_utils.normalize_path(directory)
        file_paths: List[str] = []
        skipped_count = 0
        
        # Load ignore patterns and excludes
        self.ignore_manager.get_all_ignore_patterns() # Prime the cache
        excluded_relpaths = self._load_exclude_list()
        ext_set = self._compute_extension_set()
        
        # Walk through directory
        for root, dirs, files in os.walk(directory):
            # Early filtering: remove dot directories except .gitignore
            if getattr(self.config, 'skip_dot_files', True):
                dirs[:] = [d for d in dirs if not self._should_skip_dot_file(d)]
            
            # Remove ignored directories
            original_dirs = list(dirs)
            dirs[:] = []
            for d in original_dirs:
                dir_path = self.path_utils.join_path(root, d)
                if not self.ignore_manager.should_ignore_file(dir_path):
                    dirs.append(d)
                else:
                    logger.debug("Skipping directory: %s (ignored)", dir_path)
                    skipped_count += 1

            # Early filtering: remove dot files except .gitignore
            if getattr(self.config, 'skip_dot_files', True):
                files = [f for f in files if not self._should_skip_dot_file(f)]

            for file in files:
                file_path = self.path_utils.resolve_workspace_path(self.path_utils.join_path(root, file), self.workspace_path)
                rel_path = self.path_utils.calculate_relative_path(file_path, self.workspace_path)
                rel_norm = self.path_utils.normalize_path(rel_path)

                # Check exclude list (normalized)
                if rel_norm in excluded_relpaths:
                    logger.debug("Skipping file: %s (in exclude list)", file_path)
                    skipped_count += 1
                    continue

                # Check if file should be ignored
                if self.ignore_manager.should_ignore_file(file_path):
                    logger.debug("Skipping file: %s (ignored)", file_path)
                    skipped_count += 1
                    continue
                
                # Check file size early
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > self.config.max_file_size_bytes:
                        logger.debug("Skipping file: %s (file size %s > %s)", file_path, file_size, self.config.max_file_size_bytes)
                        skipped_count += 1
                        continue
                except (OSError, IOError):
                    logger.debug("Skipping file: %s (cannot get size)", file_path)
                    skipped_count += 1
                    continue
                
                # Check extension support (case-insensitive)
                ext = self.path_utils.get_file_extension(file)
                if ext not in ext_set:
                    logger.debug("Skipping file: %s (extension %s not in %s)", file_path, ext, ext_set)
                    skipped_count += 1
                    continue
                
                # Check if file is binary
                if self.file_processor.is_binary_file(file_path):
                    logger.debug("Skipping file: %s (binary)", file_path)
                    skipped_count += 1
                    continue
                
                file_paths.append(file_path)
        
        return file_paths, skipped_count
