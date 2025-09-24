"""
Virtual environment validation utilities for testing infrastructure.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class VirtualEnvironmentValidator:
    """Validate virtual environment setup for testing."""

    @staticmethod
    def validate_venv_setup() -> Dict[str, Any]:
        """
        Validate that the virtual environment is properly set up.

        Returns:
            Dict containing validation results and any issues found
        """
        results = {
            'valid': True,
            'issues': [],
            'recommendations': []
        }

        # Check if we're in a virtual environment
        if not VirtualEnvironmentValidator._is_in_venv():
            results['valid'] = False
            results['issues'].append(
                "Not running in a virtual environment. "
                "Please activate the virtual environment before running tests."
            )
            results['recommendations'].append(
                "Run: source .venv/bin/activate (Linux/Mac) or .venv\\Scripts\\activate (Windows)"
            )

        # Check if .venv directory exists
        venv_path = Path('.venv')
        if not venv_path.exists():
            results['valid'] = False
            results['issues'].append(
                "Virtual environment directory '.venv' not found in project root."
            )
            results['recommendations'].append(
                "Create virtual environment: python -m venv .venv"
            )
        else:
            # Check if .venv/bin/python exists
            python_path = venv_path / 'bin' / 'python'
            if not python_path.exists():
                results['valid'] = False
                results['issues'].append(
                    f"Python executable not found at {python_path}"
                )
                results['recommendations'].append(
                    "Recreate virtual environment: rm -rf .venv && python -m venv .venv"
                )

        # Check if required packages are installed
        if venv_path.exists():
            missing_packages = VirtualEnvironmentValidator._check_required_packages()
            if missing_packages:
                results['valid'] = False
                results['issues'].append(
                    f"Missing required packages in virtual environment: {', '.join(missing_packages)}"
                )
                results['recommendations'].append(
                    "Install requirements: .venv/bin/pip install -r requirements.txt -r requirements-dev.txt"
                )

        return results

    @staticmethod
    def _is_in_venv() -> bool:
        """Check if we're currently running in a virtual environment."""
        # Check for common virtual environment indicators
        return (
            hasattr(sys, 'real_prefix') or  # virtualenv
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or  # venv
            'VIRTUAL_ENV' in os.environ  # Any virtual environment
        )

    @staticmethod
    def _check_required_packages() -> list:
        """Check if required packages are installed in the virtual environment."""
        missing_packages = []

        # List of critical packages that should be available
        critical_packages = [
            'pytest',
            'tree_sitter',
            'qdrant_client',
            'ollama'
        ]

        try:
            # Try to import each package
            for package in critical_packages:
                try:
                    __import__(package.replace('-', '_'))
                except ImportError:
                    missing_packages.append(package)
        except Exception:
            # If we can't check, assume packages are missing
            missing_packages.extend(critical_packages)

        return missing_packages

    @staticmethod
    def create_venv_setup_script() -> str:
        """Generate a script to set up the virtual environment."""
        script = '''#!/bin/bash
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
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
fi

echo "Virtual environment setup complete!"
echo "To activate manually, run: source .venv/bin/activate"
'''

        return script

    @staticmethod
    def print_validation_report(results: Dict[str, Any]) -> None:
        """Print a formatted validation report."""
        print("\n" + "="*60)
        print("VIRTUAL ENVIRONMENT VALIDATION REPORT")
        print("="*60)

        if results['valid']:
            print("✅ Virtual environment is properly configured!")
        else:
            print("❌ Virtual environment has issues:")

            for issue in results['issues']:
                print(f"  • {issue}")

            if results['recommendations']:
                print("\n📋 Recommendations:")
                for recommendation in results['recommendations']:
                    print(f"  • {recommendation}")

        print("="*60 + "\n")

    @staticmethod
    def run_tests_with_venv_validation() -> int:
        """
        Run tests with virtual environment validation.

        Returns:
            Exit code (0 for success, 1 for validation failure)
        """
        # Validate virtual environment
        results = VirtualEnvironmentValidator.validate_venv_setup()

        if not results['valid']:
            VirtualEnvironmentValidator.print_validation_report(results)
            return 1

        # If validation passes, run tests
        try:
            # Use the virtual environment Python
            python_path = Path('.venv') / 'bin' / 'python'
            cmd = [str(python_path), '-m', 'pytest', 'tests/', '-v']

            print(f"Running tests with: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=Path.cwd())

            return result.returncode

        except Exception as e:
            print(f"Error running tests: {e}")
            return 1