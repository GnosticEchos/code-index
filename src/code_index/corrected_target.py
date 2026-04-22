#!/usr/bin/env python3
"""
Corrected CLI that properly targets Test_CodeBase and respects configuration.

Fixes:
1. Workspace parameter targeting
2. Model configuration respect
3. Real-time file processing display
"""

import os
from pathlib import Path

from code_index.config import Config
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
from code_index.chunking import TreeSitterChunkingStrategy
from code_index.errors import ErrorHandler

class CorrectedIndexer:
    """Indexer that properly targets Test_CodeBase."""
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        
    def process_test_codebase(self, 
                            workspace: str = "/home/james/kanban_frontend/Test_CodeBase",
                            model: str = "dengcao/Qwen3-Embedding-0.6B:F16") -> dict:
        """Process Test_CodeBase with proper targeting."""
        
        print("=" * 60)
        print("🎯 CORRECTED INDEXING START")
        print("=" * 60)
        print(f"📁 Target workspace: {workspace}")
        print(f"🤖 Target model: {model}")
        
        # Verify workspace
        if not os.path.exists(workspace):
            print(f"❌ ERROR: Workspace does not exist: {workspace}")
            return {"error": "workspace_not_found"}
        
        # List workspace contents
        print("\n📋 Workspace contents:")
        files = [f for f in os.listdir(workspace) 
                if os.path.isfile(os.path.join(workspace, f))]
        
        print(f"📄 Found {len(files)} files:")
        for i, f in enumerate(files, 1):
            print(f"   {i}. {f}")
        
        # Filter for code files
        code_extensions = {'.py', '.rs', '.ts', '.js', '.vue', '.html', '.json'}
        code_files = [f for f in files 
                     if Path(f).suffix.lower() in code_extensions]
        
        print(f"\n💻 Code files: {len(code_files)}")
        
        if not code_files:
            print("❌ No code files found")
            return {"files_found": 0, "blocks_processed": 0}
        
        # Create config with explicit targeting
        cfg = Config()
        cfg.workspace_path = workspace
        cfg.model_name = model
        cfg.use_tree_sitter = True
        cfg.chunking_strategy = "treesitter"
        
        print("\n⚙️  Configuration:")
        print(f"   workspace_path: {cfg.workspace_path}")
        print(f"   model_name: {cfg.model_name}")
        print(f"   use_tree_sitter: {cfg.use_tree_sitter}")
        print(f"   chunking_strategy: {cfg.chunking_strategy}")
        
        # Initialize components
        scanner = DirectoryScanner(cfg)
        chunking_strategy = TreeSitterChunkingStrategy(cfg)
        parser = CodeParser(cfg, chunking_strategy)
        
        # Process files with progress
        processed_files = []
        total_blocks = 0
        
        print(f"\n🚀 Processing {len(code_files)} files...")
        print("-" * 40)
        
        for i, filename in enumerate(code_files, 1):
            file_path = os.path.join(workspace, filename)
            print(f"📁 [{i}/{len(code_files)}] {filename}")
            
            try:
                blocks = parser.parse_file(file_path)
                processed_files.append(filename)
                total_blocks += len(blocks)
                print(f"   ✅ {len(blocks)} blocks extracted")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("-" * 40)
        print("✅ COMPLETE!")
        print(f"   Files processed: {len(processed_files)}")
        print(f"   Total blocks: {total_blocks}")
        
        return {
            "files_processed": len(processed_files),
            "total_blocks": total_blocks,
            "files": processed_files
        }

if __name__ == "__main__":
    indexer = CorrectedIndexer()
    result = indexer.process_test_codebase()
    print(f"\n📊 Result: {result}")
