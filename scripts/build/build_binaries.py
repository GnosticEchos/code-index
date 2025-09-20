#!/usr/bin/env python3
"""
Master build script for creating both CLI and MCP server binaries using Nuitka.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return True if successful."""
    print(f"\n{description}")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    if result.returncode == 0:
        print(f"✓ {description} completed successfully")
        return True
    else:
        print(f"✗ {description} failed (exit code: {result.returncode})")
        return False

def build_cli_binary():
    """Build the CLI binary."""
    cmd = [
        "python", "-m", "nuitka",
        "--onefile",
        "--onefile-cache-mode=cached",  # Cache unpacked files for better performance
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        "--output-filename=code-index",
        "--remove-output",  # Clean up build files after compilation
        "--include-package=code_index",
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
        "src/bin/cli_entry.py"
    ]
    return run_command(cmd, "Building CLI binary")

def build_mcp_binary():
    """Build the MCP server binary."""
    cmd = [
        "python", "-m", "nuitka",
        "--onefile",
        "--onefile-cache-mode=cached",  # Cache unpacked files for better performance
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        "--output-filename=code-index-mcp",
        "--remove-output",  # Clean up build files after compilation
        "--include-package=code_index",
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
    return run_command(cmd, "Building MCP server binary")

def main():
    """Main build function."""
    print("Code Index Binary Builder")
    print("=" * 40)

    # Ensure dist directory exists
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    # Build CLI binary
    if not build_cli_binary():
        print("CLI binary build failed")
        sys.exit(1)

    # Build MCP binary
    if not build_mcp_binary():
        print("MCP binary build failed")
        sys.exit(1)

    print("\n" + "=" * 40)
    print("All binaries built successfully!")
    print(f"CLI binary: {dist_dir / 'code-index'}")
    print(f"MCP binary: {dist_dir / 'code-index-mcp'}")

if __name__ == "__main__":
    main()# Temporary change for stashing
# Temporary change for stashing
