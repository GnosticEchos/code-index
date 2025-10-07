"""
Batch manager for processing files in optimized batches.

Handles file batching, memory management, and parallel processing coordination.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from dataclasses import dataclass

from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_batch_size: int = 10
    max_memory_mb: int = 512
    max_concurrent_batches: int = 3
    retry_attempts: int = 3
    retry_delay: float = 1.0


class BatchManager:
    """Manages file processing in optimized batches."""
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """Initialize batch manager."""
        self.config = config
        self.error_handler = error_handler
        self.batch_config = self._load_batch_config()
        
    def _load_batch_config(self) -> BatchConfig:
        """Load batch configuration from config."""
        return BatchConfig(
            max_batch_size=getattr(self.config, 'batch_size', 10),
            max_memory_mb=getattr(self.config, 'max_memory_mb', 512),
            max_concurrent_batches=getattr(self.config, 'max_concurrent_batches', 3),
            retry_attempts=getattr(self.config, 'retry_attempts', 3),
            retry_delay=getattr(self.config, 'retry_delay', 1.0)
        )
        
    def create_batches(self, files: List[Path], batch_size: Optional[int] = None) -> List[List[Path]]:
        """
        Create optimized batches from file list.
        
        Args:
            files: List of files to process
            batch_size: Override default batch size
            
        Returns:
            List of file batches
        """
        if not files:
            return []
            
        batch_size = batch_size or self.batch_config.max_batch_size
        
        # Sort files by size for memory optimization (larger files first)
        sorted_files = sorted(files, key=lambda f: f.stat().st_size, reverse=True)
        
        # Create batches
        batches = []
        current_batch = []
        current_batch_size = 0
        
        for file_path in sorted_files:
            file_size = file_path.stat().st_size
            
            # Check if adding this file would exceed batch limits
            if (len(current_batch) >= batch_size or 
                current_batch_size + file_size > self.batch_config.max_memory_mb * 1024 * 1024):
                
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_batch_size = 0
            
            current_batch.append(file_path)
            current_batch_size += file_size
            
        # Add remaining files
        if current_batch:
            batches.append(current_batch)
            
        return batches
        
    def estimate_memory_usage(self, batch: List[Path]) -> int:
        """Estimate memory usage for a batch in bytes."""
        total_size = sum(f.stat().st_size for f in batch)
        
        # Rough estimation: file size + processing overhead (2x)
        return total_size * 2
        
    def optimize_batches(self, files: List[Path]) -> List[List[Path]]:
        """Create optimized batches considering memory and processing time."""
        if not files:
            return []
            
        # Group by file type for parallel processing efficiency
        file_groups = self._group_by_language(files)
        
        all_batches = []
        for language, language_files in file_groups.items():
            language_batches = self.create_batches(language_files)
            all_batches.extend(language_batches)
            
        return all_batches
        
    def _group_by_language(self, files: List[Path]) -> Dict[str, List[Path]]:
        """Group files by detected language."""
        from .language_detector import LanguageDetector
        
        detector = LanguageDetector()
        groups = {}
        
        for file_path in files:
            language = detector.detect_language(str(file_path))
            if language not in groups:
                groups[language] = []
            groups[language].append(file_path)
            
        return groups
        
    def create_retry_batches(self, failed_files: List[Dict[str, Any]]) -> List[List[Path]]:
        """Create batches for retrying failed files."""
        if not failed_files:
            return []
            
        # Extract file paths from failed entries
        file_paths = [Path(f['filename']) for f in failed_files if 'filename' in f]
        
        # Create smaller batches for retry
        retry_batch_size = max(1, self.batch_config.max_batch_size // 2)
        return self.create_batches(file_paths, retry_batch_size)
        
    def get_batch_stats(self, batches: List[List[Path]]) -> Dict[str, Any]:
        """Get statistics about created batches."""
        total_files = sum(len(batch) for batch in batches)
        total_size = sum(sum(f.stat().st_size for f in batch) for batch in batches)
        
        return {
            'total_batches': len(batches),
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'average_batch_size': total_files / len(batches) if batches else 0,
            'largest_batch': max(len(batch) for batch in batches) if batches else 0,
            'smallest_batch': min(len(batch) for batch in batches) if batches else 0
        }
