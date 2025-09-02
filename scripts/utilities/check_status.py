#!/usr/bin/env python3
"""
Script to monitor the status of ongoing indexing processes.
"""
import os
import sys
import time
import subprocess
from pathlib import Path

def check_indexing_status():
    """Check the status of indexing processes."""
    print("=== Code Index Tool Status ===")
    
    # Check if batch indexing is running
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        indexing_processes = [line for line in lines if 'batch_indexer.py' in line and 'grep' not in line]
        
        if indexing_processes:
            print("🟢 Batch indexing is running:")
            for process in indexing_processes:
                parts = process.split()
                if len(parts) > 10:
                    print(f"   PID: {parts[1]} - {' '.join(parts[10:])}")
        else:
            print("⚪ No batch indexing processes running")
    except Exception as e:
        print(f"Error checking processes: {e}")
    
    # Check log files
    log_files = list(Path('.').glob('batch_index*.log'))
    if log_files:
        print(f"\n📝 Found {len(log_files)} batch index log files:")
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"   {log_file.name} ({size} bytes)")
    else:
        print("\n📝 No batch index log files found")
    
    # Check Qdrant collections
    try:
        result = subprocess.run([
            sys.executable, '-m', 'code_index.cli', 'collections', 'list'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if 'No collections found' in result.stdout:
            print("\n📦 No collections currently exist")
        else:
            print("\n📦 Current collections:")
            print(result.stdout)
    except Exception as e:
        print(f"\nError checking collections: {e}")
    
    print("\n=== Status Check Complete ===")

if __name__ == "__main__":
    check_indexing_status()