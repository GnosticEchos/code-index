#!/usr/bin/env python3
"""
Build script for MCP server binary using Nuitka.
"""

import subprocess
import sys
import os

def build_mcp_binary():
    """Build the MCP server binary using Nuitka."""
    cmd = [
        "python", "-m", "nuitka",
        "--onefile",  # Create a single executable file
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
        "--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_yaml/queries=code_index/tree_sitter_queries",
        "--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_c-sharp/queries=code_index/tree_sitter_queries",
        "--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_embedded_template/queries=code_index/tree_sitter_queries",
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
        "src/bin/mcp_entry.py"
    ]

    print("Building MCP server binary with Nuitka...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=os.getcwd())
    if result.returncode == 0:
        print("MCP server binary built successfully: dist/code-index-mcp")
    else:
        print(f"Failed to build MCP server binary (exit code: {result.returncode})")
        sys.exit(1)

if __name__ == "__main__":
    build_mcp_binary()# Temporary change for stashing
# Temporary change for stashing
