#!/bin/bash
# Virtual Environment Setup Script
# This script sets up the virtual environment for testing

set -e

echo "Setting up virtual environment for testing..."

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
uv pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    uv pip install -r requirements.txt
fi

if [ -f "requirements-dev.txt" ]; then
    uv pip install -r requirements-dev.txt
fi

echo "Virtual environment setup complete!"
echo "To activate manually, run: source .venv/bin/activate"
echo ""
echo "To run tests with validation, use:"
echo "  python -m pytest tests/ -v"
echo "or:"
echo "  .venv/bin/python -m pytest tests/ -v"