#!/usr/bin/env python3
"""
Script to run all demonstrations for the code index tool.
"""
import os
import sys
import subprocess


def run_demonstration(script_name, description):
    """Run a single demonstration script."""
    print(f"\n{description}")
    print("-" * len(description))
    
    if os.path.exists(script_name):
        result = subprocess.run(['python', script_name])
        if result.returncode == 0:
            print(f"✓ {script_name} completed successfully")
            return True
        else:
            print(f"✗ {script_name} failed")
            return False
    else:
        print(f"✗ {script_name} not found")
        return False


def run_all_demonstrations():
    """Run all demonstration scripts."""
    print("Running all demonstrations for Code Index Tool")
    print("==========================================")
    
    demos = [
        ("verify_env.py", "1. Verifying environment setup"),
        ("test_installation.py", "2. Testing installation"),
        ("list_demos.py", "3. Listing available demonstrations"),
    ]
    
    results = []
    for script, description in demos:
        result = run_demonstration(script, description)
        results.append(result)
    
    print("\n" + "=" * 50)
    if all(results):
        print("✓ All demonstrations completed successfully!")
        return True
    else:
        print("✗ Some demonstrations failed!")
        return False


def main():
    """Main function."""
    if run_all_demonstrations():
        print("\nAll demonstrations completed successfully!")
        print("\nTo run individual demonstrations:")
        print("  python verify_env.py")
        print("  python test_installation.py")
        print("  python list_demos.py")
        print("  python demo_workspace.py")
        print("  python demonstrate.py")
        return 0
    else:
        print("\nSome demonstrations failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())