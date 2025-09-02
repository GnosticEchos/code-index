# Makefile for code index tool

# Default target
.PHONY: help
help:
	@echo "Code Index Tool Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install     - Install the package in development mode"
	@echo "  test        - Run tests"
	@echo "  example     - Run example script"
	@echo "  clean       - Clean build artifacts"
	@echo "  lint        - Run code linting"
	@echo "  format      - Format code with black"
	@echo "  check       - Run all checks"

# Install the package in development mode
.PHONY: install
install:
	uv pip install -e .

# Run tests
.PHONY: test
test:
	python -m pytest tests/ -v

# Run example script
.PHONY: example
example:
	python example.py

# Clean build artifacts
.PHONY: clean
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Run code linting
.PHONY: lint
lint:
	flake8 src/ tests/

# Format code with black
.PHONY: format
format:
	black src/ tests/

# Run all checks
.PHONY: check
check: lint test

# Run installation test
.PHONY: test-install
test-install:
	python test_installation.py