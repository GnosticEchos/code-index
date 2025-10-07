#!/usr/bin/env python3
"""
Fixed CLI that properly targets Test_CodeBase and respects configuration.

Usage: python fixed_cli.py /home/james/kanban_frontend/Test_CodeBase
"""

import os
import sys
from pathlib import Path

def process_workspace(workspace_path):
    """Process a specific workspace with proper targeting."""
    
    print("🎯 FIXED WORKSPACE PROCESSING")
    print("=" * 60)
    print(f"📁 Target: {workspace_path}")
    
    # Ensure absolute path
    workspace_path = os.path.abspath(workspace_path)
    
    if not os.path.exists(workspace_path):
        print(f"❌ ERROR: Directory does not exist: {workspace_path}")
        return
    
    # List files directly
    files = []
    for ext in ['.py', '.rs', '.ts', '.js', '.vue', '.html', '.json']:
        files.extend(Path(workspace_path).glob(f'*{ext}'))
    
    print(f"📄 Found {len(files)} code files:")
    for f in files:
        print(f"   📄 {f.name}")
    
    if not files:
        print("❌ No code files found")
        return
    
    # Process with tree-sitter
    try:
        from code_index.config import Config
        from code_index.parser import CodeParser
        from code_index.chunking import TreeSitterChunkingStrategy
        
        cfg = Config()
        cfg.workspace_path = workspace_path
        cfg.use_tree_sitter = True
        cfg.chunking_strategy = "treesitter"
        
        chunking_strategy = TreeSitterChunkingStrategy(cfg)
        parser = CodeParser(cfg, chunking_strategy)
        
        total_blocks = 0
        print(f"\n🚀 Processing {len(files)} files...")
        print("-" * 40)
        
        for i, file_path in enumerate(files, 1):
            print(f"📁 [{i}/{len(files)}] {file_path.name}")
            
            try:
                blocks = parser.parse_file(str(file_path))
                total_blocks += len(blocks)
                print(f"   ✅ {len(blocks)} blocks extracted")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("-" * 40)
        print(f"✅ COMPLETE!")
        print(f"   Files processed: {len(files)}")
        print(f"   Total blocks: {total_blocks}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")

if __name__ == "__main__":
    workspace = "/home/james/kanban_frontend/Test_CodeBase"
    process_workspace(workspace)
