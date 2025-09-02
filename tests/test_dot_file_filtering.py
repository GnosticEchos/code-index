#!/usr/bin/env python3
"""
Test script to verify dot file filtering behavior.
"""
import os
import tempfile
import shutil
from pathlib import Path
from code_index.config import Config
from code_index.scanner import DirectoryScanner

def create_test_environment():
    """Create a test environment with various dot files."""
    test_dir = tempfile.mkdtemp(prefix="test_dot_files_")
    print(f"Creating test environment in: {test_dir}")
    
    # Create various files and directories
    test_files = [
        "normal_file.py",
        "another_file.js",
        ".hidden_file",
        ".env",
        ".gitignore",
        ".config/file.txt",
        "subdir/normal_file.py",
        "subdir/.hidden_in_subdir",
        ".venv/python_file.py",
        "node_modules/index.js"
    ]
    
    for file_path in test_files:
        full_path = os.path.join(test_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if not os.path.isdir(full_path):
            with open(full_path, 'w') as f:
                f.write(f"# Test content for {file_path}\n")
    
    # Create .gitignore with some patterns
    gitignore_path = os.path.join(test_dir, ".gitignore")
    with open(gitignore_path, 'w') as f:
        f.write("node_modules/\n")
        f.write("*.env\n")
        f.write(".venv/\n")
    
    return test_dir

def test_dot_file_filtering():
    """Test the dot file filtering functionality."""
    test_dir = create_test_environment()
    
    try:
        # Test with default configuration (should skip dot files)
        config = Config()
        config.workspace_path = test_dir
        scanner = DirectoryScanner(config)
        
        print("Testing with default configuration (skip_dot_files=True)...")
        files, skipped = scanner.scan_directory(test_dir)
        print(f"Found {len(files)} files, skipped {skipped} files")
        print("Files found:", [os.path.basename(f) for f in files])
        
        # Test with backward compatibility (should not skip dot files)
        config.skip_dot_files = False
        config.read_root_gitignore_only = False
        
        print("\nTesting with backward compatibility (skip_dot_files=False)...")
        files2, skipped2 = scanner.scan_directory(test_dir)
        print(f"Found {len(files2)} files, skipped {skipped2} files")
        print("Files found:", [os.path.basename(f) for f in files2])
        
        # Verify .gitignore is still processed for ignore patterns (not indexed as content)
        print(f"\n.gitignore should be used for ignore patterns but not indexed as content:")
        gitignore_indexed = any('.gitignore' in f for f in files)
        gitignore_indexed2 = any('.gitignore' in f for f in files2)
        print(f"With filtering: .gitignore indexed = {gitignore_indexed}")
        print(f"Without filtering: .gitignore indexed = {gitignore_indexed2}")
        
        # The key test: with filtering should find fewer files (dot files excluded)
        # but both should process .gitignore for ignore patterns
        dot_files_excluded = len(files) < len(files2)
        print(f"Dot files excluded: {dot_files_excluded}")
        
        # Use assert instead of return
        assert dot_files_excluded, "Dot files should be excluded when filtering is enabled"
        
    finally:
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    success = test_dot_file_filtering()
    if success:
        print("\n✅ Test passed! Dot file filtering is working correctly.")
    else:
        print("\n❌ Test failed! Dot file filtering is not working as expected.")