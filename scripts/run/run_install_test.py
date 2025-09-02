#!/usr/bin/env python3
"""
Script to run the installation test for the code index tool.
"""
import os
import sys
import subprocess


def run_installation_test():
    """Run the installation test."""
    print("Running installation test for Code Index Tool")
    print("========================================")
    
    if os.path.exists("test_installation.py"):
        print("Starting installation test...")
        result = subprocess.run(['python', 'test_installation.py'])
        if result.returncode == 0:
            print("✓ Installation test completed successfully")
            return True
        else:
            print("✗ Installation test failed")
            return False
    else:
        print("✗ test_installation.py not found")
        return False


def main():
    """Main function."""
    if run_installation_test():
        print("\nInstallation test completed successfully!")
        return 0
    else:
        print("\nInstallation test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())