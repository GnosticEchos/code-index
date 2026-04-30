"""
Debug CLI with enhanced file processing display.

Adds real-time file processing to the working tree-sitter system.
"""

import logging

from code_index.config import Config
from code_index.config_service import ConfigurationService
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
from code_index.chunking import TreeSitterChunkingStrategy
from code_index.ui.tui_integration import TUIInterface

# Configure module logger
logger = logging.getLogger(__name__)


class DebugIndexingService:
    """Enhanced indexing service with real-time file display."""
    
    def __init__(self, error_handler=None):
        self.error_handler = error_handler
        self.config_service = ConfigurationService(error_handler)
        
    def index_workspace_debug(self, workspace: str, config_path: str = "code_index.json") -> tuple[int, int, int]:
        """Index workspace with real-time file processing display."""
        
        # Create config with workspace path
        cfg = Config()
        cfg.workspace_path = workspace
        
        # Initialize scanner with config
        scanner = DirectoryScanner(cfg)
        
        # Get files to process
        files = scanner.scan_directory(workspace)
        
        # Initialize TUI with error handling
        tui_interface = None
        overall_task_id = None
        use_tui = True
        
        try:
            tui_interface = TUIInterface()
            overall_task_id = tui_interface.start_indexing(len(files))
            if overall_task_id is None:
                use_tui = False
                logger.warning("TUI initialization returned no task ID, using simple progress")
        except Exception as e:
            use_tui = False
            logger.warning(f"TUI initialization failed: {e}, using simple progress")
        
        # Initialize parser
        chunking_strategy = TreeSitterChunkingStrategy(cfg)
        parser = CodeParser(cfg, chunking_strategy)
        
        processed_count = 0
        total_blocks = 0
        timed_out_files = 0
        
        # Process files with display
        for i, file_path in enumerate(files, 1):
            try:
                if use_tui and tui_interface and overall_task_id is not None:
                    tui_interface.update_indexing_progress(
                        overall_task_id=overall_task_id,
                        completed_files=i,
                        total_files=len(files),
                        current_file=str(file_path),
                        speed=100.0,
                        eta=1.0,
                        total_blocks=0,
                        processed_blocks=0,
                        language_info="Processing"
                    )
                else:
                    # Simple logging fallback when TUI is unavailable
                    logger.debug("Processing file %d/%d: %s", i, len(files), file_path)
                
                # Parse file
                blocks = parser.parse_file(file_path)  # type: ignore[arg-type]
                processed_count += 1
                total_blocks += len(blocks)
                
            except Exception as e:
                if self.error_handler:
                    self.error_handler.handle_error(e, None)
                timed_out_files += 1
                continue
        
        # Final update
        if use_tui and tui_interface and overall_task_id is not None:
            tui_interface.update_indexing_progress(
                overall_task_id=overall_task_id,
                completed_files=len(files),
                total_files=len(files),
                current_file="Complete",
                speed=0.0,
                eta=0.0,
                total_blocks=total_blocks,
                processed_blocks=total_blocks,
                language_info="Done"
            )
        
        if tui_interface:
            tui_interface.close()
        
        return processed_count, total_blocks, timed_out_files


# Quick test function
def test_debug_processing():
    """Test the debug processing."""
    service = DebugIndexingService()
    workspace = "/home/james/kanban_frontend/Test_CodeBase"
    
    logger.info("Starting debug file processing for workspace: %s", workspace)
    processed, blocks, timeouts = service.index_workspace_debug(workspace)
    
    logger.info("Debug processing complete: %d files, %d blocks, %d timeouts", processed, blocks, timeouts)
    return processed, blocks, timeouts
