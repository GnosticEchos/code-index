#!/usr/bin/env python3
"""
Windows build script for Code Index binaries using Nuitka.
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

def build_cli_binary():
    """Build the CLI binary for Windows."""
    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")
    
    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        "--onefile-cache-mode=cached",
        f"--python-for-scons={venv_python}",  # Use absolute path
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        "--output-filename=code-index-windows",
        "--remove-output",
        "--include-package=code_index",
        "--include-package=tree_sitter",
        "--include-package=tree_sitter_language_pack",
        "--include-package=langchain_text_splitters",
        "--include-package=pygments",
        "--include-package=qdrant_client",
        "--include-package=fastmcp",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=qdrant_client.local.tests",
        "--nofollow-import-to=tests",
        "--nofollow-import-to=*.tests",
        "--console=disable",
        "--windows-icon-from-ico=icon.ico",
        "--mingw64",
        "--lto=no",  # Disable LTO to avoid _Py_TriggerGC linker errors with Python 3.14
        "--windows-company-name=CodeIndex",
        "--windows-product-name=CodeIndex",
        "--windows-file-version=1.0.0.0",
        "--windows-product-version=1.0.0.0",
        "src/bin/cli_entry.py"
    ]
    return run_command(cmd, "Building Windows CLI binary")

def build_mcp_binary():
    """Build the MCP server binary for Windows."""
    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")
    
    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        "--onefile-cache-mode=cached",
        f"--python-for-scons={venv_python}",  # Use absolute path
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        "--output-filename=code-index-mcp-windows",
        "--remove-output",
        "--include-package=code_index",
        "--include-package=tree_sitter",
        "--include-package=tree_sitter_language_pack",
        "--include-package=langchain_text_splitters",
        "--include-package=pygments",
        "--include-package=qdrant_client",
        "--include-package=fastmcp",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=qdrant_client.local.tests",
        "--nofollow-import-to=tests",
        "--nofollow-import-to=*.tests",
        "--console=disable",
        "--windows-icon-from-ico=icon.ico",
        "--mingw64",
        "--lto=no",  # Disable LTO to avoid _Py_TriggerGC linker errors with Python 3.14
        "--windows-company-name=CodeIndex",
        "--windows-product-name=CodeIndex",
        "--windows-file-version=1.0.0.0",
        "--windows-product-version=1.0.0.0",
        "src/bin/mcp_entry.py"
    ]
    return run_command(cmd, "Building Windows MCP server binary")

def main():
    """Main Windows build function."""
    print("🪟 Code Index Windows Binary Builder")
    print("=" * 40)

    # Ensure dist directory exists
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    # Check prerequisites
    print("📋 Prerequisites check:")
    print("- MSVC compiler (Visual Studio Build Tools recommended)")
    print("- Windows 10+ or Windows Server 2016+")
    print("- icon.ico file for Windows executable icon (optional)")

    # Build CLI binary
    if not build_cli_binary():
        print("Windows CLI binary build failed")
        sys.exit(1)

    # Build MCP binary
    if not build_mcp_binary():
        print("Windows MCP binary build failed")
        sys.exit(1)

    print("\n" + "=" * 40)
    print("Windows binaries built successfully!")
    print(f"CLI binary: {dist_dir / 'code-index-windows.exe'}")
    print(f"MCP binary: {dist_dir / 'code-index-mcp-windows.exe'}")

    print("\n📋 Next steps:")
    print("1. Test the binaries on Windows")
    print("2. Consider code signing for distribution")
    print("3. Use signtool for digital signature if needed")

if __name__ == "__main__":
    main()