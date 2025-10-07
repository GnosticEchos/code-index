"""
Corrected CLI with proper workspace targeting.

Fixes the workspace directory bug and ensures Test_CodeBase processing.
"""

import sys
import os
from pathlib import Path
from typing import List

from code_index.config import Config
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
from code_index.chunking import TreeSitterChunkingStrategy
from code_index.errors import ErrorHandler
from code_index.path_utils import PathUtils

def process_test_codebase(workspace: str = "/home/james/kanban_frontend/Test_CodeBase"):
    """Process only the Test_CodeBase directory with proper targeting."""
    
    print(f"🎯 Processing: {workspace}")
    
    # Verify directory exists
    if not Path(workspace).exists():
        print(f"❌ Directory not found: {workspace}")
        return 0, 0, 0
    
    # Create config with explicit workspace
    cfg = Config()
    cfg.workspace_path = workspace
    
    # Initialize scanner
    scanner = DirectoryScanner(cfg)
    
    # Get files from Test_CodeBase only
    files = scanner.scan_directory(workspace)
    
    # Filter to ensure we're only processing Test_CodeBase
    test_files = [f for f in files if str(f).startswith(str(workspace))]
    
    print(f"📁 Found {len(test_files)} files in Test_CodeBase")
    
    if not test_files:
        print("❌ No files found to process")
        return 0, 0, 0
    
    # Show files being processed
    for i, file_path in enumerate(test_files, 1):
        print(f"📁 [{i}/{len(test_files)}] {Path(file_path).name}")
    
    # Initialize parser
    chunking_strategy = TreeSitterChunkingStrategy(cfg)
    parser = CodeParser(cfg, chunking_strategy)
    
    processed_count = 0
    total_blocks = 0
    
    # Process each file
    for file_path in test_files:
        try:
            blocks = parser.parse_file(str(file_path))
            processed_count += 1
            total_blocks += len(blocks)
            print(f"✅ {Path(file_path).name}: {len(blocks)} blocks")
            
        except Exception as e:
            print(f"❌ {Path(file_path).name}: {e}")
            continue
    
    print(f"🎯 Test_CodeBase Complete: {processed_count} files, {total_blocks} blocks")
    return processed_count, total_blocks, 0

if __name__ == "__main__":
    process_test_codebase()
