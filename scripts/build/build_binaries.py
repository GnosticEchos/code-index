#!/usr/bin/env python3
"""
Master build script for creating both CLI and MCP server binaries using Nuitka.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

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

def build_cli_binary(extra_args=None):
    """Build the CLI binary."""
    if extra_args is None:
        extra_args = []

    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")

    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        "--onefile-cache-mode=cached",  # Cache unpacked files for better performance
        f"--python-for-scons={venv_python}",  # Use absolute path
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

    # Add extra arguments passed from command line, but filter out problematic static libpython flag
    filtered_extra_args = [arg for arg in extra_args if not arg.startswith('--static-libpython')]
    cmd.extend(filtered_extra_args)

    return run_command(cmd, "Building CLI binary")

def build_mcp_binary(extra_args=None):
    """Build the MCP server binary."""
    if extra_args is None:
        extra_args = []

    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")

    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        "--onefile-cache-mode=cached",  # Cache unpacked files for better performance
        f"--python-for-scons={venv_python}",  # Use absolute path
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

    # Add extra arguments passed from command line, but filter out problematic static libpython flag
    filtered_extra_args = [arg for arg in extra_args if not arg.startswith('--static-libpython')]
    cmd.extend(filtered_extra_args)

    return run_command(cmd, "Building MCP server binary")

def main():
    """Main build function."""
    print("Code Index Binary Builder")
    print("=" * 40)

    # Parse extra arguments from command line
    extra_args = []
    if len(sys.argv) > 1:
        # Skip the script name (sys.argv[0])
        extra_args = sys.argv[1:]
        print(f"Extra Nuitka arguments: {extra_args}")

    # Ensure dist directory exists
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    # Build CLI binary
    if not build_cli_binary(extra_args):
        print("CLI binary build failed")
        sys.exit(1)

    # Build MCP binary
    if not build_mcp_binary(extra_args):
        print("MCP binary build failed")
        sys.exit(1)

    print("\n" + "=" * 40)
    print("All binaries built successfully!")
    print(f"CLI binary: {dist_dir / 'code-index'}")
    print(f"MCP binary: {dist_dir / 'code-index-mcp'}")

if __name__ == "__main__":
    main()
