"""
Progress tracker for monitoring indexing operations.

Provides real-time progress tracking, performance metrics, and status reporting.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..config import Config
from ..errors import ErrorHandler


class ProgressTracker:
    """Tracks indexing progress with performance metrics."""
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """Initialize progress tracker."""
        self.config = config
        self.error_handler = error_handler
        self.start_time = None
        self.stats = {}
        self.errors = []
        self.warnings = []
        
    def start_operation(self, operation_name: str, total_files: int) -> None:
        """Start tracking a new indexing operation."""
        self.start_time = datetime.now()
        self.stats = {
            'operation_name': operation_name,
            'total_files': total_files,
            'processed_files': 0,
            'failed_files': 0,
            'total_blocks': 0,
            'start_time': self.start_time,
            'current_file': None,
            'files_per_second': 0.0,
            'blocks_per_second': 0.0,
            'estimated_completion': None
        }
        
    def update_progress(self, file_path: str, blocks: int, success: bool = True) -> None:
        """Update progress for a processed file."""
        if not self.start_time:
            return
            
        self.stats['current_file'] = file_path
        self.stats['total_blocks'] += blocks
        
        if success:
            self.stats['processed_files'] += 1
        else:
            self.stats['failed_files'] += 1
            
        # Calculate performance metrics
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > 0:
            self.stats['files_per_second'] = self.stats['processed_files'] / elapsed
            self.stats['blocks_per_second'] = self.stats['total_blocks'] / elapsed
            
            # Estimate completion time
            remaining_files = self.stats['total_files'] - self.stats['processed_files']
            if self.stats['files_per_second'] > 0:
                eta_seconds = remaining_files / self.stats['files_per_second']
                self.stats['estimated_completion'] = datetime.now() + timedelta(seconds=eta_seconds)
                
    def get_progress_stats(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        if not self.start_time:
            return {}
            
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            **self.stats,
            'elapsed_seconds': elapsed,
            'progress_percentage': (self.stats['processed_files'] / max(self.stats['total_files'], 1)) * 100,
            'success_rate': (self.stats['processed_files'] / max(self.stats['total_files'], 1)) * 100,
            'estimated_remaining_seconds': max(0, (self.stats['total_files'] - self.stats['processed_files']) / max(self.stats['files_per_second'], 0.1))
        }
        
    def add_error(self, file_path: str, error: str) -> None:
        """Add processing error."""
        self.errors.append({
            'file_path': file_path,
            'error': error,
            'timestamp': datetime.now()
        })
        
    def add_warning(self, file_path: str, warning: str) -> None:
        """Add processing warning."""
        self.warnings.append({
            'file_path': file_path,
            'warning': warning,
            'timestamp': datetime.now()
        })
        
    def complete_operation(self) -> Dict[str, Any]:
        """Complete tracking and return final statistics."""
        if not self.start_time:
            return {}
            
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        final_stats = {
            **self.stats,
            'end_time': end_time,
            'total_time_seconds': total_time,
            'final_success_rate': (self.stats['processed_files'] / max(self.stats['total_files'], 1)) * 100,
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'average_blocks_per_file': self.stats['total_blocks'] / max(self.stats['processed_files'], 1)
        }
        
        return final_stats
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for reporting."""
        stats = self.get_progress_stats()
        
        return {
            'files_processed': stats.get('processed_files', 0),
            'total_time': stats.get('elapsed_seconds', 0),
            'files_per_second': stats.get('files_per_second', 0),
            'blocks_per_second': stats.get('blocks_per_second', 0),
            'memory_efficiency': self._calculate_memory_efficiency(),
            'processing_efficiency': self._calculate_processing_efficiency()
        }
        
    def _calculate_memory_efficiency(self) -> float:
        """Calculate memory efficiency score."""
        # Placeholder - would integrate with memory monitoring
        return 0.85  # 85% efficiency
        
    def _calculate_processing_efficiency(self) -> float:
        """Calculate processing efficiency score."""
        # Placeholder - would integrate with processing metrics
        return 0.90  # 90% efficiency
        
    def is_operation_complete(self) -> bool:
        """Check if operation is complete."""
        return self.stats.get('processed_files', 0) + self.stats.get('failed_files', 0) >= self.stats.get('total_files', 0)
        
    def get_eta_string(self) -> str:
        """Get estimated time of arrival as string."""
        stats = self.get_progress_stats()
        eta_seconds = stats.get('estimated_remaining_seconds', 0)
        
        if eta_seconds < 60:
            return f"{int(eta_seconds)}s"
        elif eta_seconds < 3600:
            return f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
        else:
            hours = int(eta_seconds / 3600)
            minutes = int((eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
