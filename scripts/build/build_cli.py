#!/usr/bin/env python3
"""
Build script for CLI binary using Nuitka.
"""

import subprocess
import sys
import os

def build_cli_binary():
    """Build the CLI binary using Nuitka."""
    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")
    
    cmd = [
        venv_python, "-m", "nuitka",
        "--onefile",  # Create a single executable file
        f"--python-for-scons={venv_python}",  # Use absolute path
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--output-filename=code-index",
        "--output-dir=dist",
        "--remove-output",  # Clean up build files after compilation
        "--include-package=code_index",  # Include the entire package
        "--include-package=tree_sitter",
        "--include-package=tree_sitter_language_pack",
        "--include-package=langchain_text_splitters",
        "--include-package=pygments",
        "--include-package=qdrant_client",
        "--include-package=fastmcp",
        # Exclude test files and unwanted modules
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=qdrant_client.local.tests",
        "--nofollow-import-to=tests",
        "--nofollow-import-to=*.tests",
        # Performance optimizations
        "--clang",  # Use Clang for better performance
        "--lto=no",  # Disable LTO to avoid _Py_TriggerGC linker errors with Python 3.14
        "src/bin/cli_entry.py"
    ]

    print("Building CLI binary with Nuitka...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=os.getcwd())
    if result.returncode == 0:
        print("CLI binary built successfully: dist/code-index")
    else:
        print(f"Failed to build CLI binary (exit code: {result.returncode})")
        sys.exit(1)

if __name__ == "__main__":
    build_cli_binary()
# Temporary change for stashing
# Temporary change for stashing
