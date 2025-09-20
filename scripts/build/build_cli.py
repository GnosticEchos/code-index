#!/usr/bin/env python3
"""
Build script for CLI binary using Nuitka.
"""

import subprocess
import sys
import os

def build_cli_binary():
    """Build the CLI binary using Nuitka."""
    cmd = [
        "python", "-m", "nuitka",
        "--onefile",  # Create a single executable file
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--output-filename=code-index",
        "--output-dir=dist",
        "--include-package=code_index",  # Include the entire package
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
    build_cli_binary()# Temporary change for stashing
# Temporary change for stashing
