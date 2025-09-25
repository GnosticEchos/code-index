# Simple Makefile for code index tool

.PHONY: help install test clean build-cross-platform build-binaries build-cli build-mcp build-windows build-macos build-macos-universal

help:
	@echo "Code Index Tool Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install                 - Install the package in development mode"
	@echo "  test                    - Run tests"
	@echo "  clean                   - Clean build artifacts"
	@echo "  build-cross-platform    - Build binaries for current platform (auto-detect)"
	@echo "  build-binaries          - Build both CLI and MCP binaries for current platform"
	@echo "  build-cli               - Build CLI binary only"
	@echo "  build-mcp               - Build MCP server binary only"
	@echo "  build-windows           - Build Windows binaries"
	@echo "  build-macos             - Build macOS binaries (interactive architecture selection)"
	@echo "  build-macos-universal   - Build macOS universal binaries (Intel + Apple Silicon)"

install:
	uv pip install -e .

test:
	.venv/bin/python -m pytest tests/ -v

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete# Temporary change for stashing
# Temporary change for stashing

# Binary build targets
build-cross-platform:
	@echo "Building binaries for current platform..."
	python scripts/build/build_cross_platform.py

build-binaries:
	@echo "Building both CLI and MCP binaries..."
	python scripts/build/build_binaries.py

build-cli:
	@echo "Building CLI binary only..."
	python scripts/build/build_cli.py

build-mcp:
	@echo "Building MCP server binary only..."
	python scripts/build/build_mcp.py

build-windows:
	@echo "Building Windows binaries..."
	@if [ -f "scripts/build/build_windows.py" ]; then \
		python scripts/build/build_windows.py; \
	else \
		echo "Error: build_windows.py not found. Please create the Windows build script first."; \
		exit 1; \
	fi

build-macos:
	@echo "Building macOS binaries (interactive architecture selection)..."
	@if [ -f "scripts/build/build_macos.py" ]; then \
		python scripts/build/build_macos.py; \
	else \
		echo "Error: build_macos.py not found. Please create the macOS build script first."; \
		exit 1; \
	fi

build-macos-universal:
	@echo "Building macOS universal binaries (Intel + Apple Silicon)..."
	@if [ -f "scripts/build/build_macos.py" ]; then \
		python scripts/build/build_macos.py --universal; \
	else \
		echo "Error: build_macos.py not found. Please create the macOS build script first."; \
		exit 1; \
	fi
