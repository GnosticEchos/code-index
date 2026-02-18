#!/usr/bin/env python3
"""
macOS build script for Code Index binaries using Nuitka.
Supports Intel, Apple Silicon, and universal binaries.
"""

import subprocess
import sys
import os
import platform
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

def get_architecture():
    """Get the current macOS architecture."""
    machine = platform.machine()
    if machine == "x86_64":
        return "x86_64"
    elif machine == "arm64":
        return "arm64"
    else:
        return "unknown"

def build_cli_binary(architecture="auto", universal=False):
    """Build the CLI binary for macOS."""
    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")
    
    arch_suffix = ""
    if architecture != "auto":
        arch_suffix = f"-{architecture}"
    elif universal:
        arch_suffix = "-universal"

    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        "--onefile-cache-mode=cached",
        f"--python-for-scons={venv_python}",  # Use absolute path
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        f"--output-filename=code-index-macos{arch_suffix}",
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
        "--macos-create-app-bundle",
        "--macos-app-name=CodeIndex",
        "--macos-app-version=1.0.0",
        "--clang",
        "--lto=no",  # Disable LTO to avoid _Py_TriggerGC linker errors with Python 3.14
        "--macos-app-icon=icon.icns"
    ]

    # Add architecture-specific flags
    if universal:
        cmd.extend(["--macos-target-arch=arm64", "--macos-target-arch=x86_64"])
    elif architecture != "auto":
        cmd.extend([f"--macos-target-arch={architecture}"])

    cmd.append("src/bin/cli_entry.py")
    return run_command(cmd, f"Building macOS CLI binary ({architecture if architecture != 'auto' else get_architecture()})")

def build_mcp_binary(architecture="auto", universal=False):
    """Build the MCP server binary for macOS."""
    # Get absolute path to venv python to avoid symlink issues
    venv_python = os.path.abspath(".venv/bin/python")
    
    arch_suffix = ""
    if architecture != "auto":
        arch_suffix = f"-{architecture}"
    elif universal:
        arch_suffix = "-universal"

    cmd = [
        venv_python, "-m", "nuitka",
        "--mode=onefile",
        "--onefile-cache-mode=cached",
        f"--python-for-scons={venv_python}",  # Use absolute path
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        f"--output-filename=code-index-mcp-macos{arch_suffix}",
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
        "--macos-create-app-bundle",
        "--macos-app-name=CodeIndex",
        "--macos-app-version=1.0.0",
        "--clang",
        "--lto=no",  # Disable LTO to avoid _Py_TriggerGC linker errors with Python 3.14
        "--macos-app-icon=icon.icns"
    ]

    # Add architecture-specific flags
    if universal:
        cmd.extend(["--macos-target-arch=arm64", "--macos-target-arch=x86_64"])
    elif architecture != "auto":
        cmd.extend([f"--macos-target-arch={architecture}"])

    cmd.append("src/bin/mcp_entry.py")
    return run_command(cmd, f"Building macOS MCP server binary ({architecture if architecture != 'auto' else get_architecture()})")

def show_architecture_selection():
    """Show architecture selection menu."""
    print("\n🍎 macOS Architecture Selection")
    print("=" * 35)
    print("Current architecture:", get_architecture())
    print("\nAvailable options:")
    print("1. Intel (x86_64) only")
    print("2. Apple Silicon (arm64) only")
    print("3. Universal (both Intel and Apple Silicon)")
    print("4. Auto-detect (build for current architecture)")

def get_user_choice():
    """Get user's architecture choice."""
    while True:
        try:
            choice = input("\nSelect architecture (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            print("Invalid choice. Please select 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\nBuild cancelled by user.")
            sys.exit(1)

def main():
    """Main macOS build function."""
    print("🍎 Code Index macOS Binary Builder")
    print("=" * 40)

    # Ensure dist directory exists
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    # Check prerequisites
    print("📋 Prerequisites check:")
    print("- Xcode Command Line Tools: xcode-select --install")
    print("- macOS 10.15+ (Catalina or later)")
    print("- icon.icns file for macOS app icon (optional)")

    # Check if universal flag is passed
    universal = "--universal" in sys.argv

    if universal:
        print("Building universal binaries (Intel + Apple Silicon)...")
        architecture = "universal"
    else:
        # Show architecture selection
        show_architecture_selection()
        choice = get_user_choice()

        if choice == '1':
            architecture = "x86_64"
        elif choice == '2':
            architecture = "arm64"
        elif choice == '3':
            architecture = "universal"
        else:  # choice == '4'
            architecture = "auto"

    # Build CLI binary
    if not build_cli_binary(architecture, universal):
        print("macOS CLI binary build failed")
        sys.exit(1)

    # Build MCP binary
    if not build_mcp_binary(architecture, universal):
        print("macOS MCP binary build failed")
        sys.exit(1)

    print("\n" + "=" * 40)
    print("macOS binaries built successfully!")
    arch_suffix = ""
    if architecture != "auto":
        arch_suffix = f"-{architecture}"
    elif universal:
        arch_suffix = "-universal"
    print(f"CLI binary: {dist_dir / f'code-index-macos{arch_suffix}'}")
    print(f"MCP binary: {dist_dir / f'code-index-mcp-macos{arch_suffix}'}")

    print("\n📋 Next steps:")
    print("1. Test the binaries on macOS")
    print("2. Consider code signing for distribution:")
    print("   codesign --sign 'Developer ID Application' dist/code-index-macos*")

if __name__ == "__main__":
    main()