#!/usr/bin/env python3
"""
Build script for MCP server binary using Nuitka.
"""

import subprocess
import sys
import os
import shutil

# Our project-specific temp directory
NUITKA_TMPDIR = "/tmp/code-index-nuitka"


def run_command(cmd, description):
    """Run a command with project-specific temp directory cleanup."""
    print(f"\n{description}")
    print(f"Command: {' '.join(cmd)}")
    
    # Clean up our temp directory at start (in case previous build crashed)
    if os.path.exists(NUITKA_TMPDIR):
        print(f"Cleaning old build temp: {NUITKA_TMPDIR}")
        shutil.rmtree(NUITKA_TMPDIR, ignore_errors=True)
    
    # Create fresh temp directory
    os.makedirs(NUITKA_TMPDIR, exist_ok=True)
    
    # Set TMPDIR for this build
    env = os.environ.copy()
    env["TMPDIR"] = NUITKA_TMPDIR
    print(f"Using temp directory: {NUITKA_TMPDIR}")
    
    try:
        result = subprocess.run(cmd, cwd=os.getcwd(), env=env)
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            print(f"✗ {description} failed (exit code: {result.returncode})")
            return False
    finally:
        # Always clean up our temp directory after build
        if os.path.exists(NUITKA_TMPDIR):
            print(f"Cleaning up temp directory: {NUITKA_TMPDIR}")
            shutil.rmtree(NUITKA_TMPDIR, ignore_errors=True)


def build_mcp_binary():
    """Build the MCP server binary using Nuitka."""
    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")
    
    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",  # Create a single executable file
        f"--python-for-scons={venv_python}",  # Use absolute path
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--output-filename=code-index-mcp",
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
        "src/bin/mcp_entry.py"
    ]

    print("Building MCP server binary with Nuitka...")
    
    if run_command(cmd, "Building MCP server binary"):
        print("MCP server binary built successfully: dist/code-index-mcp")
    else:
        print("Failed to build MCP server binary")
        sys.exit(1)

if __name__ == "__main__":
    build_mcp_binary()
