#!/usr/bin/env python3
"""Complete tree-sitter integration debug."""

import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.code_index.language_detection import LanguageDetector
from src.code_index.config import Config
from src.code_index.indexing.language_detector import LanguageDetector as NewDetector

def debug_tree_sitter():
    print("🔍 COMPLETE TREE-SITTER DEBUG")
    print("=" * 60)
    
    # Test workspace
    workspace = "/home/james/kanban_frontend/Test_CodeBase"
    config = Config()
    
    # Test both detectors
    old_detector = LanguageDetector(config)
    new_detector = NewDetector()
    
    files = list(Path(workspace).rglob("*"))
    code_files = [f for f in files if f.is_file() and f.suffix in {'.py', '.rs', '.ts', '.js', '.vue'}]
    
    print(f"📁 Found {len(code_files)} code files")
    
    for file_path in code_files[:10]:
        old_lang = old_detector.detect_language(str(file_path))
        new_lang = new_detector.detect_language(str(file_path))
        
        print(f"🔍 {file_path.name}")
        print(f"   Old: {old_lang}")
        print(f"   New: {new_lang}")
        print(f"   Extension: {file_path.suffix}")
        print()

if __name__ == "__main__":
    debug_tree_sitter()
