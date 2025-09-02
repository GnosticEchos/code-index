#!/usr/bin/env python3
"""
Script to run all tests for the code index tool.
"""
import os
import sys
import subprocess


def run_tests():
    """Run all tests."""
    print("Running all tests for Code Index Tool")
    print("=================================")
    
    # Run basic tests
    print("\n1. Running basic tests...")
    result = subprocess.run(['python', '-m', 'pytest', 'tests/test_basic.py', '-v'])
    if result.returncode != 0:
        print("✗ Basic tests failed")
        return False
    else:
        print("✓ Basic tests passed")
    
    # Run CLI tests
    print("\n2. Running CLI tests...")
    result = subprocess.run(['python', '-m', 'pytest', 'tests/test_cli.py', '-v'])
    if result.returncode != 0:
        print("✗ CLI tests failed")
        return False
    else:
        print("✓ CLI tests passed")
    
    # Run integration tests
    print("\n3. Running integration tests...")
    result = subprocess.run(['python', '-m', 'pytest', 'tests/test_integration.py', '-v'])
    if result.returncode != 0:
        print("✗ Integration tests failed")
        return False
    else:
        print("✓ Integration tests passed")
    
    print("\n✓ All tests passed!")
    return True


def main():
    """Main function."""
    if run_tests():
        print("\nAll tests completed successfully!")
        return 0
    else:
        print("\nSome tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
