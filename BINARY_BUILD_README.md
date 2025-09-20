# Code Index Binary Creation Guide

This guide explains how to create standalone binaries for the Code Index tool using Nuitka across multiple platforms.
## Best Practices Implemented

### ✅ Performance Optimizations
- **Link Time Optimization (LTO)**: `--lto=yes` for better code optimization
- **Compiler Selection**: 
  - Linux: `--clang` for better performance
  - Windows: `--mingw64` (can be changed to MSVC for optimal performance)
  - macOS: `--clang` (Xcode default)
- **Static Linking**: `--static-libpython=yes` for better compatibility and performance
- **Onefile Caching**: `--onefile-cache-mode=cached` for faster startup

### ✅ Security Enhancements
- **Test Exclusion**: Comprehensive exclusion of test frameworks and modules
- **Clean Dependencies**: Only include necessary packages
- **Windows Metadata**: Company/product information for executable properties
- **macOS Code Signing Ready**: Prepared for code signing with proper bundle structure

### ✅ Deployment Optimization
- **Clean Builds**: `--remove-output` removes build artifacts
- **Cross-Platform Support**: Separate optimized scripts for each OS
- **Architecture Support**: macOS supports both Intel and Apple Silicon
- **Minimal Dependencies**: Virtual environment isolation

## Additional Recommendations

### For Production Deployment

1. **Code Signing** (Required for distribution):
   ```bash
   # macOS
   codesign -s "Developer ID Application" dist/code-index-macos
   
   # Windows
   signtool sign /f cert.pfx /p password dist/code-index-windows.exe
   ```

2. **Testing on Target Systems**:
   - Test on clean systems without development dependencies
   - Verify all functionality works as expected
   - Check startup time and memory usage

3. **Distribution Packaging**:
   - **Linux**: Consider creating `.deb` or `.rpm` packages
   - **Windows**: Use Inno Setup or similar for installers
   - **macOS**: Create `.dmg` files for distribution

### Performance Monitoring

1. **Benchmark Your Binaries**:
   ```bash
   time ./dist/code-index --help
   time ./dist/code-index-mcp --version
   ```

2. **Memory Usage Analysis**:
   - Monitor RAM usage during operation
   - Compare with Python script performance
   - Optimize based on findings

### Maintenance

1. **Regular Updates**:
   - Keep Nuitka updated to latest version
   - Update dependencies regularly
   - Rebuild binaries after major changes

2. **Version Control**:
   - Tag releases with binary versions
   - Keep build scripts in sync across platforms
   - Document any platform-specific requirements

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Ensure all dependencies are installed
   - Check Python version compatibility
   - Verify virtual environment is activated

2. **Runtime Issues**:
   - Test on target platform architecture
   - Check for missing system libraries
   - Verify file permissions

3. **Performance Issues**:
   - Compare with Python script baseline
   - Check for anti-virus interference (Windows)
   - Monitor system resources during execution

## Overview

The Code Index project supports building binaries for multiple platforms:
- **Linux**: x86_64, ARM64
- **Windows**: x86_64
- **macOS**: x86_64 (Intel), ARM64 (Apple Silicon), Universal

Both CLI and MCP server modes can be packaged into standalone executables that don't require Python to be installed on the target system.

## Prerequisites

### All Platforms
1. **Python 3.13+** with the project dependencies installed
2. **Nuitka** installed: `uv add --dev nuitka` or `pip install nuitka`

### Linux
- **GCC compiler** (for C compilation during build process)

### Windows
- **MSVC compiler** (Visual Studio Build Tools recommended)
- Windows 10+ or Windows Server 2016+

### macOS
- **Xcode Command Line Tools**: `xcode-select --install`
- macOS 10.15+ (Catalina or later)

## Project Structure

```
code_index/
├── src/
│   ├── bin/
│   │   ├── cli_entry.py          # Entry point for CLI binary
│   │   └── mcp_entry.py          # Entry point for MCP server binary
│   └── code_index/               # Main package
├── scripts/
│   └── build/
│       ├── build_cli.py          # Build script for CLI binary (Linux)
│       ├── build_mcp.py          # Build script for MCP server binary (Linux)
│       ├── build_binaries.py     # Master build script for both binaries (Linux)
│       ├── build_windows.py      # Windows build script
│       ├── build_macos.py        # macOS build script
│       └── build_cross_platform.py # Auto-detect platform and build
├── Makefile                     # Contains build targets for all platforms
└── dist/                        # Output directory for built binaries
```

## Build Scripts

### Cross-Platform Build (Recommended)

Build binaries for your current platform automatically:

```bash
# Using Python script
python scripts/build/build_cross_platform.py

# Using Makefile
make build-cross-platform
```

**Note:** Cross-platform building means building for the current platform only. You cannot build Windows binaries on Linux or vice versa. To create binaries for all platforms, you need to run the build on each target platform.

### Platform-Specific Builds

#### Linux
```bash
# Build both binaries
python scripts/build/build_binaries.py
make build-binaries

# Build CLI only
python scripts/build/build_cli.py
make build-cli

# Build MCP only
python scripts/build/build_mcp.py
make build-mcp
```

#### Windows
```bash
# Build both binaries
python scripts/build/build_windows.py
make build-windows
```

#### macOS
```bash
# Interactive build (choose architecture)
python scripts/build/build_macos.py
make build-macos

# Build universal binaries (Intel + Apple Silicon)
make build-macos-universal
```

## Nuitka Configuration

### Linux Configuration (Optimized)
```bash
--onefile
--onefile-cache-mode=cached
--assume-yes-for-downloads
--output-dir=dist
--remove-output
--include-package=code_index
--include-package=tree_sitter
--include-package=tree_sitter_language_pack
--include-package=langchain_text_splitters
--include-package=pygments
--include-package=qdrant_client
--include-package=fastmcp
--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_yaml/queries=code_index/tree_sitter_queries
--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_c-sharp/queries=code_index/tree_sitter_queries
--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_embedded_template/queries=code_index/tree_sitter_queries
--nofollow-import-to=pytest
--nofollow-import-to=setuptools
--nofollow-import-to=unittest
--nofollow-import-to=doctest
--nofollow-import-to=qdrant_client.local.tests
--nofollow-import-to=tests
--nofollow-import-to=*.tests
--lto=yes
--clang
--static-libpython=yes
```

### Windows Configuration (Optimized)
```bash
--onefile
--onefile-cache-mode=cached
--assume-yes-for-downloads
--output-dir=dist
--remove-output
--include-package=code_index
--include-package=tree_sitter
--include-package=tree_sitter_language_pack
--include-package=langchain_text_splitters
--include-package=pygments
--include-package=qdrant_client
--include-package=fastmcp
--include-data-dir=.venv/Lib/site-packages/tree_sitter_yaml/queries=code_index/tree_sitter_queries
--include-data-dir=.venv/Lib/site-packages/tree_sitter_c-sharp/queries=code_index/tree_sitter_queries
--include-data-dir=.venv/Lib/site-packages/tree_sitter_embedded_template/queries=code_index/tree_sitter_queries
--nofollow-import-to=pytest
--nofollow-import-to=setuptools
--nofollow-import-to=unittest
--nofollow-import-to=doctest
--nofollow-import-to=qdrant_client.local.tests
--nofollow-import-to=tests
--nofollow-import-to=*.tests
--windows-disable-console
--windows-icon-from-ico=icon.ico
--mingw64
--static-libpython=yes
--lto=yes
--windows-company-name=CodeIndex
--windows-product-name=CodeIndex
--windows-file-version=1.0.0.0
--windows-product-version=1.0.0.0
```

### macOS Configuration (Optimized)
```bash
--onefile
--onefile-cache-mode=cached
--assume-yes-for-downloads
--output-dir=dist
--remove-output
--include-package=code_index
--include-package=tree_sitter
--include-package=tree_sitter_language_pack
--include-package=langchain_text_splitters
--include-package=pygments
--include-package=qdrant_client
--include-package=fastmcp
--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_yaml/queries=code_index/tree_sitter_queries
--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_c-sharp/queries=code_index/tree_sitter_queries
--include-data-dir=.venv/lib/python3.13/site-packages/tree_sitter_embedded_template/queries=code_index/tree_sitter_queries
--nofollow-import-to=pytest
--nofollow-import-to=setuptools
--nofollow-import-to=unittest
--nofollow-import-to=doctest
--nofollow-import-to=qdrant_client.local.tests
--nofollow-import-to=tests
--nofollow-import-to=*.tests
--macos-create-app-bundle
--macos-app-name=CodeIndex
--macos-app-version=1.0.0
--static-libpython=yes
--clang
--lto=yes
--macos-app-icon=icon.icns
```# Temporary change for stashing
# Temporary change for stashing
