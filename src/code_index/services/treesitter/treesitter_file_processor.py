"""
TreeSitter file processor service.

Handles file filtering, validation, and language-specific processing for Tree-sitter operations.
Extracted from file_processor.py to reduce file size.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path


class TreeSitterFileProcessor:
    """
    Service for processing and validating files for Tree-sitter operations.
    Handles file filtering, language-specific optimizations, file size validation, path-based filtering.
    """

    def __init__(self, config, error_handler=None):
        self.config = config
        self.error_handler = error_handler
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)
        self.enable_chunked_processing = getattr(config, "enable_chunked_processing", True)
        self.large_file_threshold = getattr(config, "large_file_threshold_bytes", 256 * 1024)
        self.streaming_threshold = getattr(config, "streaming_threshold_bytes", 1024 * 1024)
        self.default_chunk_size = getattr(config, "default_chunk_size_bytes", 64 * 1024)
        self.memory_threshold_mb = getattr(config, "memory_optimization_threshold_mb", 100)
        self.enable_progressive_indexing = getattr(config, "enable_progressive_indexing", True)
        monitoring_config = getattr(config, "monitoring", {})
        self.enable_performance_tracking = monitoring_config.get("enable_performance_tracking", False)
        self.log_mmap_metrics = monitoring_config.get("log_mmap_metrics", False)
        self.log_resource_usage = monitoring_config.get("log_resource_usage", False)
        self.log_per_file_metrics = monitoring_config.get("log_per_file_metrics", False)
        self.log_memory_usage = monitoring_config.get("log_memory_usage", False)
        self.log_mmap_statistics = monitoring_config.get("log_mmap_statistics", False)
        self.log_cache_performance = monitoring_config.get("log_cache_performance", False)
        self.log_cache_efficiency = monitoring_config.get("log_cache_efficiency", False)
        self.enable_detailed_logging = monitoring_config.get("enable_detailed_logging", False)
        self.performance_report_interval = monitoring_config.get("performance_report_interval", 30)
        self.log_file_processing_times = monitoring_config.get("log_file_processing_times", False)
        self.track_cross_platform_compatibility = monitoring_config.get("track_cross_platform_compatibility", False)

    def validate_file(self, file_path: str) -> bool:
        """Validate if a file should be processed by Tree-sitter."""
        try:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return False
            if not self._validate_file_size(file_path):
                return False
            return self._should_process_file_for_treesitter(file_path)
        except Exception:
            return False

    def _validate_file_size(self, file_path: str) -> bool:
        """Validate file size against Tree-sitter limits."""
        try:
            max_size = getattr(self.config, "tree_sitter_max_file_size_bytes", 512 * 1024)
            file_size = os.path.getsize(file_path)
            return file_size <= max_size
        except (OSError, IOError):
            return False

    def _should_process_file_for_treesitter(self, file_path: str) -> bool:
        """Apply smart filtering like ignore patterns."""
        try:
            generated_dirs = ['target/', 'build/', 'dist/', 'node_modules/', '__pycache__/']
            if any(gen_dir in file_path for gen_dir in generated_dirs):
                return False
            if os.path.getsize(file_path) == 0:
                return False
            with open(file_path, 'rb') as f:
                if b'\0' in f.read(1024):
                    return False
            return True
        except Exception:
            return False

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive information about a file."""
        info = {"path": file_path, "exists": False, "is_file": False, "size_bytes": 0, "extension": "",
                "is_valid": False, "should_process": False, "language_key": None, "optimizations": {}}
        try:
            path_obj = Path(file_path)
            if path_obj.exists() and path_obj.is_file():
                info["exists"] = info["is_file"] = True
                info["size_bytes"] = path_obj.stat().st_size
                info["extension"] = path_obj.suffix.lower()
                info["is_valid"] = self.validate_file(file_path)
                info["should_process"] = info["is_valid"]
        except Exception:
            pass
        return info

    def _get_file_language(self, file_path: str) -> Optional[str]:
        """Get language key for a file."""
        try:
            from ...language_detection import LanguageDetector
            language_detector = LanguageDetector(self.config, self.error_handler)
            return language_detector.detect_language(file_path)
        except Exception:
            return None

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except (OSError, IOError):
            return 0
