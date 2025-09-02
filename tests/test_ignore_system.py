#!/usr/bin/env python3
"""
Test script for the enhanced ignore pattern system.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.fast_language_detector import FastLanguageDetector
from code_index.gitignore_manager import GitignoreTemplateManager
from code_index.smart_ignore_manager import SmartIgnoreManager


def test_language_detection():
    """Test language detection capabilities."""
    print("=== Testing Language Detection ===")
    
    # Initialize detector
    config = Config()
    detector = FastLanguageDetector(config)
    
    # Test on current directory
    workspace_path = os.path.dirname(os.path.abspath(__file__))
    print(f"Testing on workspace: {workspace_path}")
    
    # Detect languages
    languages = detector.detect_languages(workspace_path)
    print(f"Detected languages: {languages}")
    
    # Detect frameworks
    frameworks = detector.detect_frameworks(workspace_path)
    print(f"Detected frameworks: {frameworks}")
    

def test_gitignore_templates():
    """Test gitignore template retrieval."""
    print("\n=== Testing Gitignore Templates ===")
    
    # Initialize template manager
    config = Config()
    template_manager = GitignoreTemplateManager(config=config)
    
    # Test Python template
    print("Testing Python template...")
    python_patterns = template_manager.get_language_template("Python")
    print(f"Python template patterns: {len(python_patterns)}")
    if python_patterns:
        print(f"Sample patterns: {python_patterns[:5]}")
    
    # Test Node template
    print("Testing Node template...")
    node_patterns = template_manager.get_language_template("Node")
    print(f"Node template patterns: {len(node_patterns)}")
    if node_patterns:
        print(f"Sample patterns: {node_patterns[:5]}")


def test_smart_ignore_manager():
    """Test smart ignore manager."""
    print("\n=== Testing Smart Ignore Manager ===")
    
    # Initialize smart ignore manager
    workspace_path = os.path.dirname(os.path.abspath(__file__))
    config = Config()
    config.workspace_path = workspace_path
    ignore_manager = SmartIgnoreManager(workspace_path, config)
    
    # Get all ignore patterns
    print("Getting all ignore patterns...")
    patterns = ignore_manager.get_all_ignore_patterns()
    print(f"Total patterns: {len(patterns)}")
    
    # Test file matching
    test_files = [
        "__pycache__/test.pyc",
        "node_modules/react/index.js", 
        "dist/bundle.js",
        "src/main.py",
        ".git/config",
        "build/output.exe",
        "README.md",
        "requirements.txt"
    ]
    
    print("Testing file matching...")
    for test_file in test_files:
        should_ignore = ignore_manager.should_ignore_file(test_file)
        print(f"  {test_file}: {'IGNORE' if should_ignore else 'INDEX'}")


if __name__ == "__main__":
    test_language_detection()
    test_gitignore_templates()
    test_smart_ignore_manager()
    print("\n=== All tests completed ===")
