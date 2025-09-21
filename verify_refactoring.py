#!/usr/bin/env python3
"""
Simple verification script for the FileProcessingService refactoring.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

def test_refactoring():
    """Test that the refactored function works correctly."""
    print("🔍 Testing FileProcessingService refactoring...")
    
    # Test 1: Check that the function exists and can be imported
    try:
        from code_index.cli import _process_single_workspace
        print("✅ Function _process_single_workspace can be imported")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Check that FileProcessingService is used in the function
    try:
        import ast
        import inspect
        
        # Get the function source
        source = inspect.getsource(_process_single_workspace)
        tree = ast.parse(source)
        
        # Count FileProcessingService instantiations
        instantiations = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'id') and node.func.id == 'FileProcessingService':
                    instantiations += 1
                elif hasattr(node.func, 'attr') and node.func.attr == 'FileProcessingService':
                    instantiations += 1
        
        print(f"📊 Found {instantiations} FileProcessingService instantiation(s)")
        
        if instantiations == 1:
            print("✅ SUCCESS: Only one FileProcessingService instantiation found!")
            return True
        else:
            print(f"❌ FAILURE: Expected 1 instantiation, found {instantiations}")
            return False
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

if __name__ == "__main__":
    success = test_refactoring()
    sys.exit(0 if success else 1)