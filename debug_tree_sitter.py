#!/usr/bin/env python3
"""Debug tree-sitter integration step by step."""

import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.code_index.language_detection import LanguageDetector
from src.code_index.config import Config

print("🔍 DEBUGGING TREE-SITTER INTEGRATION")
print("=" * 50)

# Test workspace
test_workspace = "/home/james/kanban_frontend/Test_CodeBase"
config = Config()

# Step 1: Language Detection
detector = LanguageDetector(config)
print(f"✅ LanguageDetector initialized: {type(detector)}")

# Step 2: Test files
files = list(Path(test_workspace).rglob("*"))
print(f"📁 Found {len(files)} files")

# Step 3: Language detection for each file
for file_path in files[:5]:  # Test first 5 files
    if file_path.is_file():
        language = detector.detect_language(str(file_path))
        print(f"🔍 {file_path.name} -> {language}")

print("=" * 50)
print("✅ Tree-sitter integration debug complete")
