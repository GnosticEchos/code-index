#!/usr/bin/env python3
"""
Fix import errors in services directory.
Run with: uv run python fix_imports.py
"""
import subprocess
import re
import os
import sys

def run_tests():
    """Run pytest and capture output."""
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/", "-v", "--tb=short", "-x"],
        capture_output=True,
        text=True,
        cwd="/home/james/kanban_frontend/code_index"
    )
    return result.stdout + result.stderr

def fix_import(error_line):
    """Parse error line and fix the import."""
    # Example: src/code_index/services/batch/batch_processor.py:29: from ..command.batch_scheduler import BatchScheduler
    # Should be: from ..batch.batch_scheduler import BatchScheduler
    
    # Extract the file path and the wrong import
    match = re.search(r'(src/code_index/services/[\w/]+.py):\d+:.*?(from \.\.[\w.]+ import)', error_line)
    if not match:
        return None
    
    filepath = match.group(1)
    wrong_import = match.group(2)
    
    # Determine the correct import based on the file location
    # The file is in a service subdirectory, so we need to figure out where the imported module actually is
    
    with open(filepath, "r") as f:
        content = f.read()
    
    # Find the wrong import line and fix it
    # Pattern: from ..wrong_dir.module import -> from ..correct_dir.module import
    
    # Extract the module name from the import
    module_match = re.search(r'from \.\.(\w+)\.(\w+) import', wrong_import)
    if not module_match:
        return None
    
    wrong_dir = module_match.group(1)
    module_name = module_match.group(2)
    
    # Check which directory the module is actually in
    correct_dir = None
    service_dirs = ["batch", "command", "core", "embedding", "query", "shared", "treesitter"]
    
    for dir_name in service_dirs:
        module_path = f"/home/james/kanban_frontend/code_index/src/code_index/services/{dir_name}/{module_name}.py"
        if os.path.exists(module_path):
            correct_dir = dir_name
            break
    
    if correct_dir and correct_dir != wrong_dir:
        correct_import = f"from ..{correct_dir}.{module_name} import"
        old_import = f"from ..{wrong_dir}.{module_name} import"
        
        if old_import in content:
            content = content.replace(old_import, correct_import)
            with open(filepath, "w") as f:
                f.write(content)
            print(f"Fixed: {filepath}")
            print(f"  {old_import} -> {correct_import}")
            return True
    
    return False

def main():
    """Main loop."""
    max_iterations = 100
    for i in range(max_iterations):
        print(f"\n=== Iteration {i+1} ===")
        output = run_tests()
        
        # Check if tests passed
        if "error" not in output.lower() or "passed" in output.lower():
            print("Tests passed!")
            break
        
        # Find the first import error
        lines = output.split("\n")
        for line in lines:
            if "ModuleNotFoundError" in line or "ImportError" in line:
                print(f"Error: {line}")
                if fix_import(line):
                    break
        else:
            print("No more errors found!")
            break
    
    print("\nDone!")

if __name__ == "__main__":
    main()
