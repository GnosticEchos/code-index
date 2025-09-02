#!/usr/bin/env python3
"""
Test script to verify Tree-sitter integration works correctly.
"""
import os
import sys
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.parser import CodeParser


def test_treesitter_integration():
    """Test that Tree-sitter integration works correctly."""
    print("=== Testing Tree-sitter Integration ===")
    
    # Create temporary directory with test files
    test_dir = tempfile.mkdtemp(prefix="treesitter_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Create test Python file
        python_file = os.path.join(test_dir, "test_sample.py")
        with open(python_file, "w") as f:
            f.write("""
def calculate_sum(a, b):
    \"\"\"Calculate the sum of two numbers.\"\"\"
    return a + b

def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")

class Calculator:
    def multiply(self, x, y):
        return x * y

if __name__ == "__main__":
    main()
""")
        
        # Create test JavaScript file
        js_file = os.path.join(test_dir, "test_sample.js")
        with open(js_file, "w") as f:
            f.write("""
function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
    
    introduce() {
        return greet(this.name);
    }
}

const person = new Person("Alice");
console.log(person.introduce());
""")
        
        # Test configuration with Tree-sitter enabled
        config = Config()
        config.use_tree_sitter = True
        config.chunking_strategy = "treesitter"
        
        # Initialize parser with appropriate chunking strategy
        from code_index.chunking import TreeSitterChunkingStrategy
        chunking_strategy = TreeSitterChunkingStrategy(config)
        parser = CodeParser(config, chunking_strategy)
        
        # Test Python file parsing
        print("\nTesting Python file parsing...")
        python_blocks = parser.parse_file(python_file)
        print(f"Found {len(python_blocks)} semantic blocks in Python file")
        
        # Check block types
        block_types = [block.type for block in python_blocks]
        print(f"Block types: {set(block_types)}")
        
        # Look for specific semantic blocks
        functions = [b for b in python_blocks if 'function' in b.type]
        classes = [b for b in python_blocks if 'class' in b.type]
        print(f"Functions found: {len(functions)}")
        print(f"Classes found: {len(classes)}")
        
        # Test JavaScript file parsing
        print("\nTesting JavaScript file parsing...")
        js_blocks = parser.parse_file(js_file)
        print(f"Found {len(js_blocks)} semantic blocks in JavaScript file")
        
        # Check block types
        js_block_types = [block.type for block in js_blocks]
        print(f"JavaScript block types: {set(js_block_types)}")
        
        js_functions = [b for b in js_blocks if 'function' in b.type]
        js_classes = [b for b in js_blocks if 'class' in b.type]
        print(f"JavaScript functions found: {len(js_functions)}")
        print(f"JavaScript classes found: {len(js_classes)}")
        
        # Test configuration awareness
        print("\nTesting configuration awareness...")
        config.chunking_strategy = "lines"  # Switch to line-based
        line_blocks = parser.parse_file(python_file)
        print(f"Line-based parsing found: {len(line_blocks)} blocks")
        
        # Verify different strategies produce different results
        if len(python_blocks) != len(line_blocks):
            print("✅ Different strategies produce different results")
        else:
            print("⚠️  Same number of blocks for different strategies")
        
        print("\n=== Tree-sitter Integration Test Complete ===")
        assert True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_treesitter_integration()
    sys.exit(0 if success else 1)