"""
Debug CLI with enhanced file processing display.

Adds real-time file processing to the working tree-sitter system.
"""

import sys
import os
from pathlib import Path
from typing import List, Set

from code_index.config import Config
from code_index.config_service import ConfigurationService
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
from code_index.chunking import TreeSitterChunkingStrategy
from code_index.errors import ErrorHandler
from code_index.path_utils import PathUtils
from .tui_integration import tui

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
        
        # Initialize TUI
        tui.start_processing(len(files), workspace)
        
        # Initialize parser
        chunking_strategy = TreeSitterChunkingStrategy(cfg)
        parser = CodeParser(cfg, chunking_strategy)
        
        processed_count = 0
        total_blocks = 0
        timed_out_files = 0
        
        # Process files with display
        for i, file_path in enumerate(files, 1):
            try:
                tui.update_file(file_path, i, len(files))
                
                # Parse file
                blocks = parser.parse_file(file_path)
                processed_count += 1
                total_blocks += len(blocks)
                
            except Exception as e:
                if self.error_handler:
                    self.error_handler.handle_error(e, None)
                timed_out_files += 1
                continue
        
        tui.complete_processing(processed_count, total_blocks, 149.70)  # Mock time
        
        return processed_count, total_blocks, timed_out_files

# Quick test function
def test_debug_processing():
    """Test the debug processing."""
    service = DebugIndexingService()
    workspace = "/home/james/kanban_frontend/Test_CodeBase"
    
    print("🔍 Testing debug file processing...")
    processed, blocks, timeouts = service.index_workspace_debug(workspace)
    
    print(f"✅ Complete: {processed} files, {blocks} blocks, {timeouts} timeouts")
