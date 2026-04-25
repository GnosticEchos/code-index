# GitHub Actions CI/CD Configuration

This document describes the GitHub Actions workflows for building and releasing cross-platform binaries for the Code Index Tool.

## Repository Structure

```
.github/
├── workflows/
│   ├── release.yml       # Cross-platform release builds (triggers on tags)
│   └── ci.yml           # CI checks (tests, lint, type-check on push/PR)
```

## Workflows

### 1. Release Build (`release.yml`)

**Trigger**: Push to tags matching `v*` pattern (e.g., `v1.2.3`) or manual dispatch.

**Purpose**: Builds standalone binaries for all supported platforms and attaches them to a GitHub Release.

#### Build Matrix

| Platform | Architectures | Output Files |
|----------|--------------|--------------|
| Linux | x86_64, aarch64 | `code-index-linux-{arch}`, `code-index-mcp-linux-{arch}` |
| Windows | x86_64 | `code-index-windows-x86_64.exe`, `code-index-mcp-windows-x86_64.exe` |
| macOS | x86_64, arm64 | `code-index-macos-{arch}`, `code-index-mcp-macos-{arch}` |

#### Build Process

1. **Checkout**: Full repository checkout with tags
2. **Setup**: Install `uv`, Python 3.13, and Rust (for Nuitka)
3. **Dependencies**: Install all packages via `uv sync --all-extras --dev`
4. **Compile**: Run Nuitka compilation for both CLI and MCP binaries
5. **Upload**: Store artifacts for release creation

#### Release Creation

- Uses `softprops/action-gh-release@v2` to create/releases
- Automatically generates release notes
- Includes all 10 platform-specific binaries
- Adds SHA256 checksums for verification

#### Usage

**Create a release by pushing a tag**:

```bash
git tag v1.2.3
git push origin v1.2.3
```

**Manual dispatch**:
1. Go to Actions → "Build and Release Cross-Platform Binaries"
2. Click "Run workflow"
3. Select release type (prerelease/draft)

### 2. CI Checks (`ci.yml`)

**Trigger**: Push to `main`/`develop` branches or pull requests.

**Purpose**: Run tests, linting, and type checking on all platforms.

#### Jobs

1. **Test**: Run pytest on Ubuntu, macOS, Windows with Python 3.13
2. **Type Check**: Run mypy on source code
3. **Lint**: Run ruff for code quality
4. **Build Test**: Verify Nuitka compilation works (fast module mode)

## Binary Build Process

### Nuitka Configuration

The build scripts (`scripts/build/*.py`) use Nuitka with these key settings:

```python
# Common settings for all builds:
--mode=onefile                    # Single executable output
--clang                           # Use Clang compiler
--lto=no                          # Disable LTO for stability
--prefer-source-code             # Prefer .py files over .pyc
--onefile-tempdir-spec={CACHE_DIR}/nuitka/...  # Fast temp extraction
--remove-output                  # Clean build directory

# Package inclusion:
--include-package=code_index
--include-package=tree_sitter
--include-package=tree_sitter_language_pack
--include-package=qdrant_client
--include-package=fastmcp
--include-package=magika

# Bloat exclusion:
--nofollow-import-to=torch       # Exclude PyTorch
--nofollow-import-to=sympy       # Exclude SymPy
--nofollow-import-to=pytest      # Exclude test frameworks
```

### Platform-Specific Notes

#### Linux
- Uses `patchelf` for library dependency management
- Supports both x86_64 and ARM64 (Graviton)

#### Windows
- Requires LLVM/Clang 17+ for compilation
- Builds `.exe` executables

#### macOS
- Supports both Intel (x86_64) and Apple Silicon (arm64)
- App signing requires additional entitlements (see `build_macos.py`)

## Artifacts and Downloads

### Release Assets

Each release includes:

```
code-index-linux-x86_64          # Linux CLI (Intel/AMD)
code-index-linux-aarch64         # Linux CLI (ARM64)
code-index-mcp-linux-x86_64      # MCP Server (Linux Intel/AMD)
code-index-mcp-linux-aarch64     # MCP Server (Linux ARM64)
code-index-windows-x86_64.exe    # Windows CLI
code-index-mcp-windows-x86_64.exe # MCP Server (Windows)
code-index-macos-x86_64          # macOS CLI (Intel)
code-index-macos-arm64           # macOS CLI (Apple Silicon)
code-index-mcp-macos-x86_64      # MCP Server (macOS Intel)
code-index-mcp-macos-arm64       # MCP Server (macOS ARM64)
checksums.txt                    # SHA256 checksums
```

### Installation

**Linux/macOS**:

```bash
# Download the appropriate binary
curl -L https://github.com/owner/repo/releases/download/v1.2.3/code-index-linux-x86_64 -o code-index
chmod +x code-index

# Move to PATH
sudo mv code-index /usr/local/bin/
```

**Windows** (PowerShell):

```powershell
# Download the binary
Invoke-WebRequest -Uri "https://github.com/owner/repo/releases/download/v1.2.3/code-index-windows-x86_64.exe" -OutFile "code-index.exe"

# Move to PATH
Move-Item "code-index.exe" "C:\Program Files\code-index.exe"
```

## Secrets and Environment Variables

### Required Secrets

- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- `HOMEBREW_TAP_TOKEN`: (Optional) For updating Homebrew formula

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UV_VERSION` | uv package manager version | `0.4.21` |
| `PYTHON_VERSION` | Python version for builds | `3.13` |
| `NUITKA_TMPDIR` | Temporary directory for Nuitka builds | `/tmp/code-index-nuitka` |

## Troubleshooting

### Build Failures

**Issue**: Nuitka compilation fails with "module not found"

**Solution**: 
- Check `scripts/build/build_*.py` for `--include-package` statements
- Ensure all dependencies are in `pyproject.toml`

**Issue**: macOS binaries fail with code signing error

**Solution**:
- For distribution, set up Apple Developer certificate
- Update `build_macos.py` with signing flags

### Slow Builds

**Issue**: Release builds take >30 minutes

**Solution**:
- Enable `uv` caching in workflow
- Use GitHub Actions cache for `.venv` directory
- Consider `--lto=auto` if Rust version supports it

### Large Binary Size

**Issue**: Binaries exceed 100MB

**Solution**:
- Verify `--nofollow-import-to` exclusions (torch, sympy, etc.)
- Check `--noinclude-setuptools-mode=nofollow` is set
- Use UPX compression: add `--enable-plugin=upx` to Nuitka flags

## Contributing

### Adding New Platforms

1. Update `release.yml` build matrix
2. Add platform-specific build steps
3. Test on the target platform
4. Update documentation

### Updating Build Parameters

1. Modify `scripts/build/*.py` files
2. Test locally: `python scripts/build/build_cli.py`
3. Commit changes and push a test tag

## Performance Metrics

Typical build times:

| Platform | CLI Build | MCP Build | Total |
|----------|-----------|-----------|-------|
| Linux x86_64 | 3-5 min | 4-6 min | 7-11 min |
| macOS arm64 | 4-6 min | 5-7 min | 9-13 min |
| Windows x86_64 | 5-8 min | 6-9 min | 11-17 min |

## See Also

- [Nuitka Documentation](https://nuitka.net/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Code Index CLI Reference](../docs/cli-reference.md)
- [Build Scripts](../scripts/build/)
