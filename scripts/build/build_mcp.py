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
        "--include-package=code_index",  # Include the entire package
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
