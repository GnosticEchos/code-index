# Simple Makefile for code index tool

.PHONY: help install test clean

help:
	@echo "Code Index Tool Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install     - Install the package in development mode"
	@echo "  test        - Run tests"
	@echo "  clean       - Clean build artifacts"

install:
	uv pip install -e .

test:
	python -m pytest tests/ -v

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete# Temporary change for stashing
# Temporary change for stashing
