#!/usr/bin/env python3
"""
Script to run the benchmark for the code index tool.
"""
import os
import sys
import subprocess


def run_benchmark():
    """Run the benchmark."""
    print("Running benchmark for Code Index Tool")
    print("=================================")
    
    if os.path.exists("benchmark.py"):
        print("Starting benchmark...")
        result = subprocess.run(['python', 'benchmark.py'])
        if result.returncode == 0:
            print("✓ Benchmark completed successfully")
            return True
        else:
            print("✗ Benchmark failed")
            return False
    else:
        print("✗ benchmark.py not found")
        return False


def main():
    """Main function."""
    if run_benchmark():
        print("\nBenchmark completed successfully!")
        return 0
    else:
        print("\nBenchmark failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())