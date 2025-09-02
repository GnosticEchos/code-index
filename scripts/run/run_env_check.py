#!/usr/bin/env python3
"""
Script to run the environment verification for the code index tool.
"""
import os
import sys
import subprocess


def run_env_verification():
    """Run the environment verification."""
    print("Running environment verification for Code Index Tool")
    print("==============================================")
    
    if os.path.exists("verify_env.py"):
        print("Starting environment verification...")
        result = subprocess.run(['python', 'verify_env.py'])
        if result.returncode == 0:
            print("✓ Environment verification completed successfully")
            return True
        else:
            print("✗ Environment verification failed")
            return False
    else:
        print("✗ verify_env.py not found")
        return False


def main():
    """Main function."""
    if run_env_verification():
        print("\nEnvironment verification completed successfully!")
        return 0
    else:
        print("\nEnvironment verification failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())