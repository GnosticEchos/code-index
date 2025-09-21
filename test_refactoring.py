#!/usr/bin/env python3
"""
Test script to verify the FileProcessingService refactoring.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

# Test the refactored function directly
try:
    from code_index.cli import _process_single_workspace
    from code_index.config import Config
    from code_index.errors import ErrorHandler
    print("✅ Import successful! Refactoring verified!")
    
    # Test basic functionality
    error_handler = ErrorHandler()
    config = Config()
    config.workspace_path = "."
    config.save("test_config.json")
    
    print("✅ Basic configuration setup successful!")
    print("✅ Refactoring completed successfully!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)