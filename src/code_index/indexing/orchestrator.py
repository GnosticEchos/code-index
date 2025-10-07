"""
Index orchestrator for coordinating indexing workflows.

Central coordinator that manages the indexing process across multiple
files and services while maintaining clean separation of concerns.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from datetime import datetime

from ..config import Config
from ..models import IndexingResult, ProcessingStats
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from .file_processor import FileProcessor
from .batch_manager import BatchManager
from .progress_tracker import ProgressTracker
from .error_recovery import ErrorRecoveryService
from ..ui.progress_manager import ProgressManager
from ..ui.file_scroller import FileScroller
from ..ui.status_panel import StatusPanel


class IndexOrchestrator:
    """Orchestrates the indexing process across multiple services."""
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """Initialize the index orchestrator."""
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        
        # Initialize components
        self.file_processor = FileProcessor(config, error_handler)
        self.batch_manager = BatchManager(config, error_handler)
        self.progress_tracker = ProgressTracker(config, error_handler)
        self.error_recovery = ErrorRecoveryService(config, error_handler)
        
        # TUI components
        self.progress_manager = ProgressManager()
        self.file_scroller = FileScroller()
        self.status_panel = StatusPanel()
        
    async def index_workspace(self, workspace_path: str) -> IndexingResult:
        """Orchestrate complete workspace indexing with TUI."""
        start_time = datetime.now()
        
        try:
            workspace = Path(workspace_path)
            if not workspace.exists():
                raise ValueError(f"Workspace does not exist: {workspace_path}")
                
            # Discover files
            files = await self._discover_files(workspace)
            if not files:
                return IndexingResult(
                    workspace_path=workspace_path,
                    total_files=0,
                    processed_files=0,
                    failed_files=0,
                    total_blocks=0,
                    processing_time=0.0,
                    errors=[],
                    warnings=["No files found to process"]
                )
                
            # Setup TUI
            with self.progress_manager.start_live_display():
                self._setup_tui(files, workspace.name)
                
                # Process files in batches
                batches = self.batch_manager.create_batches(files)
                results = await self._process_batches(batches)
                
                # Finalize
                processing_time = (datetime.now() - start_time).total_seconds()
                return self._create_result(workspace_path, results, processing_time)
                
        except Exception as e:
            context = ErrorContext(
                component="index_orchestrator",
                operation="index_workspace",
                additional_data={"workspace": workspace_path}
            )
            error_response = self.error_handler.handle_error(
                e, context, ErrorCategory.INDEXING, ErrorSeverity.HIGH
            )
            
            return IndexingResult(
                workspace_path=workspace_path,
                total_files=0,
                processed_files=0,
                failed_files=0,
                total_blocks=0,
                processing_time=0.0,
                errors=[error_response.message],
                warnings=[]
            )
            
    async def _discover_files(self, workspace: Path) -> List[Path]:
        """Discover all code files in workspace."""
        try:
            files = []
            for file_path in workspace.rglob("*"):
                if file_path.is_file() and self._should_process_file(file_path):
                    files.append(file_path)
                    
            return sorted(files)
            
        except Exception as e:
            context = ErrorContext(
                component="index_orchestrator",
                operation="discover_files",
                additional_data={"workspace": str(workspace)}
            )
            self.error_handler.handle_error(
                e, context, ErrorCategory.FILESYSTEM, ErrorSeverity.MEDIUM
            )
            return []
            
    def _setup_tui(self, files: List[Path], workspace_name: str):
        """Setup TUI components for processing."""
        # Start overall progress
        self.overall_task_id = self.progress_manager.create_overall_task(len(files))
        
        # Add files to scroller (if file_scroller exists)
        if hasattr(self, 'file_scroller'):
            for file_path in files:
                self.file_scroller.add_file(str(file_path), file_path.stat().st_size)
            
        # Start status tracking (if status_panel exists)
        if hasattr(self, 'status_panel'):
            self.status_panel.start_operation(f"Indexing {workspace_name}")
            self.status_panel.update_stats(
                total_files=len(files),
                estimated_blocks=sum(self._estimate_blocks(f) for f in files)
            )
        
    async def _process_batches(self, batches: List[List[Path]]) -> List[Dict[str, Any]]:
        """Process file batches with progress tracking."""
        results = []
        
        for batch_idx, batch in enumerate(batches):
            batch_results = await self._process_single_batch(batch, batch_idx)
            results.extend(batch_results)
            
        return results
        
    async def _process_single_batch(self, batch: List[Path], batch_idx: int) -> List[Dict[str, Any]]:
        """Process a single batch of files."""
        batch_results = []
        
        for file_path in batch:
            try:
                # Start file processing
                file_task_id = self.progress_manager.create_file_task(
                    str(file_path),
                    self._estimate_blocks(file_path)
                )
                
                # Process file
                result = await self.file_processor.process_file(file_path)
                
                # Update progress
                self.progress_manager.update_overall_progress(
                    self.overall_task_id,
                    len(batch_results) + 1,
                    len(batch)
                )
                self.progress_manager.update_file_progress(
                    file_task_id,
                    result.get('blocks', 0),
                    self._estimate_blocks(file_path)
                )
                
                # Update file scroller and status panel if they exist
                if hasattr(self, 'file_scroller'):
                    self.file_scroller.complete_file(str(file_path), result.get('blocks', 0))
                if hasattr(self, 'status_panel'):
                    self.status_panel.update_stats(
                        files_processed=len([r for r in batch_results if not r.get('error')])
                    )
                
                batch_results.append(result)
                
            except Exception as e:
                error_result = await self.error_recovery.handle_file_error(file_path, e)
                batch_results.append(error_result)
                
        return batch_results
        
    def _create_result(self, workspace_path: str, results: List[Dict[str, Any]], 
                      processing_time: float) -> IndexingResult:
        """Create final indexing result."""
        total_files = len(results)
        processed_files = sum(1 for r in results if not r.get('error'))
        failed_files = total_files - processed_files
        total_blocks = sum(r.get('blocks', 0) for r in results)
        
        # Collect errors and warnings
        errors = [r['error'] for r in results if r.get('error')]
        warnings = [w for r in results for w in r.get('warnings', [])]
        
        return IndexingResult(
            workspace_path=workspace_path,
            total_files=total_files,
            processed_files=processed_files,
            failed_files=failed_files,
            total_blocks=total_blocks,
            processing_time=processing_time,
            errors=errors,
            warnings=warnings
        )
        
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language using enhanced detector."""
        from .language_detector import LanguageDetector
        detector = LanguageDetector()
        return detector.detect_language(file_path)
        
    def _estimate_blocks(self, file_path: Path) -> int:
        """Estimate number of code blocks in file."""
        try:
            if not file_path.exists():
                return 0
                
            size = file_path.stat().st_size
            if size == 0:
                return 0
                
            # Rough estimation based on file size
            return max(1, size // 250)  # Average 250 bytes per block
            
        except Exception:
            return 1
