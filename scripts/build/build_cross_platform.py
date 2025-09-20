#!/usr/bin/env python3
"""
Cross-platform build script for Code Index binaries.
Automatically detects the operating system and calls the appropriate build script.
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def detect_platform():
    """Detect the current platform."""
    system = platform.system()
    machine = platform.machine()

    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    else:
        print(f"❌ Unsupported platform: {system}")
        return None

def check_requirements():
    """Check basic requirements for building."""
    # Check Python version
    if sys.version_info < (3, 13):
        print(f"⚠️  Python {sys.version_info.major}.{sys.version_info.minor} detected")
        print("   Recommended: Python 3.13+ for best compatibility")

    # Check if we're in the right directory
    if not Path("src/code_index/__init__.py").exists():
        print("❌ Not in the correct project directory")
        print("   Please run this script from the project root")
        return False

    # Check if dist directory exists
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    return True

def build_linux():
    """Build binaries for Linux."""
    print("🐧 Building for Linux...")

    # Use the existing Linux build script
    script_path = "scripts/build/build_binaries.py"
    if not Path(script_path).exists():
        print(f"❌ Linux build script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path]
    result = subprocess.run(cmd, cwd=os.getcwd())

    return result.returncode == 0

def build_windows():
    """Build binaries for Windows."""
    print("🪟 Building for Windows...")

    script_path = "scripts/build/build_windows.py"
    if not Path(script_path).exists():
        print(f"❌ Windows build script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path]
    result = subprocess.run(cmd, cwd=os.getcwd())

    return result.returncode == 0

def build_macos():
    """Build binaries for macOS."""
    print("🍎 Building for macOS...")

    script_path = "scripts/build/build_macos.py"
    if not Path(script_path).exists():
        print(f"❌ macOS build script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path]
    result = subprocess.run(cmd, cwd=os.getcwd())

    return result.returncode == 0

def show_build_summary():
    """Show a summary of built binaries."""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ No dist directory found")
        return

    print("\n📦 Build Summary:")
    print("=" * 40)

    binaries = list(dist_dir.glob("*"))
    if not binaries:
        print("No binaries found in dist/")
        return

    # Group binaries by platform
    linux_bins = [b for b in binaries if "linux" in b.name.lower()]
    windows_bins = [b for b in binaries if "windows" in b.name.lower() or b.name.endswith(".exe")]
    macos_bins = [b for b in binaries if "macos" in b.name.lower()]

    if linux_bins:
        print("🐧 Linux binaries:")
        for bin in sorted(linux_bins):
            size = bin.stat().st_size / (1024 * 1024)  # Size in MB
            print(".1f")

    if windows_bins:
        print("🪟 Windows binaries:")
        for bin in sorted(windows_bins):
            size = bin.stat().st_size / (1024 * 1024)  # Size in MB
            print(".1f")

    if macos_bins:
        print("🍎 macOS binaries:")
        for bin in sorted(macos_bins):
            size = bin.stat().st_size / (1024 * 1024)  # Size in MB
            print(".1f")

def main():
    """Main cross-platform build function."""
    print("🚀 Code Index Cross-Platform Binary Builder")
    print("=" * 50)

    if not check_requirements():
        sys.exit(1)

    platform_name = detect_platform()
    if not platform_name:
        sys.exit(1)

    print(f"Detected platform: {platform_name}")
    print(f"Architecture: {platform.machine()}")

    # Build based on platform
    success = False
    if platform_name == "linux":
        success = build_linux()
    elif platform_name == "windows":
        success = build_windows()
    elif platform_name == "macos":
        success = build_macos()

    if success:
        print("\n✅ Build completed successfully!")
        show_build_summary()

        print("\n📋 Next steps:")
        print("1. Test the binaries on your system")
        print("2. Distribute to target platforms as needed")
        print("3. Consider code signing for macOS/Windows distribution")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()# Temporary change for stashing
# Temporary change for stashing
