#!/usr/bin/env python3
"""
Tree-sitter Search Test Script

This script specifically tests Tree-sitter semantic chunking functionality
and its impact on search quality and performance.
"""

import sys
import os
import time
import json
import argparse
import tempfile
from typing import List, Dict, Any
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore
from code_index.chunking import TreeSitterChunkingStrategy


class TreeSitterSearchTester:
    """Test Tree-sitter semantic chunking and search functionality."""
    
    def __init__(self, config_path: str):
        """Initialize the tester with configuration."""
        self.config = Config.from_file(config_path)
        self.embedder = OllamaEmbedder(self.config)
        self.vector_store = QdrantVectorStore(self.config)
        
    def validate_tree_sitter_environment(self) -> bool:
        """Validate that Tree-sitter environment is properly configured."""
        print("=== Tree-sitter Environment Validation ===")
        
        try:
            # Test Tree-sitter imports
            import tree_sitter_language_pack as tsl
            from tree_sitter import Parser, Query
            print("✅ Tree-sitter packages are installed")
            
            # Test language detection
            chunking_strategy = TreeSitterChunkingStrategy(self.config)
            test_files = [
                "test.py",
                "test.js", 
                "test.rs",
                "test.go",
                "test.java"
            ]
            
            for test_file in test_files:
                language_key = chunking_strategy._get_language_key_for_path(test_file)
                print(f"  {test_file} → {language_key}")
            
            return True
            
        except ImportError as e:
            print(f"❌ Tree-sitter packages not installed: {e}")
            print("Install with: pip install tree-sitter-language-pack")
            return False
        except Exception as e:
            print(f"❌ Tree-sitter validation failed: {e}")
            return False
    
    def test_tree_sitter_chunking(self) -> Dict[str, Any]:
        """Test Tree-sitter chunking functionality with sample code."""
        print("\n=== Testing Tree-sitter Chunking ===")
        
        # Create temporary test files
        test_dir = tempfile.mkdtemp(prefix="treesitter_test_")
        results = {}
        
        test_files = {
            "python_test.py": '''
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

class Calculator:
    """A simple calculator class."""
    
    def multiply(self, x, y):
        """Multiply two numbers."""
        return x * y
        
    def divide(self, x, y):
        """Divide two numbers."""
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
''',
            "javascript_test.js": '''
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
''',
            "rust_test.rs": '''
fn calculate_sum(a: i32, b: i32) -> i32 {
    a + b
}

struct Calculator {
    value: i32,
}

impl Calculator {
    fn new() -> Self {
        Calculator { value: 0 }
    }
    
    fn add(&mut self, x: i32) {
        self.value += x;
    }
}

enum Operation {
    Add(i32),
    Subtract(i32),
}
'''
        }
        
        chunking_strategy = TreeSitterChunkingStrategy(self.config)
        
        for filename, code in test_files.items():
            file_path = os.path.join(test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(code.strip())
            
            print(f"\n--- Testing {filename} ---")
            
            try:
                # Test file processing eligibility
                should_process = chunking_strategy._should_process_file_for_treesitter(file_path)
                print(f"Should process: {should_process}")
                
                if should_process:
                    # Test chunking
                    file_hash = "test_hash_" + filename
                    blocks = chunking_strategy._chunk_text_treesitter(code, file_path, file_hash)
                    
                    print(f"Found {len(blocks)} semantic blocks:")
                    for i, block in enumerate(blocks):
                        print(f"  {i+1}. {block.type}: {block.identifier}")
                        print(f"     Lines {block.start_line}-{block.end_line}")
                        print(f"     Content: {block.content[:50].replace(chr(10), ' ')}...")
                    
                    results[filename] = {
                        "success": True,
                        "blocks_count": len(blocks),
                        "block_types": [block.type for block in blocks],
                        "sample_content": blocks[0].content[:100] if blocks else ""
                    }
                else:
                    results[filename] = {
                        "success": False,
                        "reason": "File filtered out by Tree-sitter configuration"
                    }
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                results[filename] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Clean up
        import shutil
        shutil.rmtree(test_dir)
        
        return results
    
    def test_tree_sitter_search_quality(self) -> Dict[str, Any]:
        """Test search quality with Tree-sitter semantic chunks."""
        print("\n=== Testing Tree-sitter Search Quality ===")
        
        semantic_queries = [
            "python function definition",
            "javascript class constructor", 
            "rust struct implementation",
            "calculate sum function",
            "class with methods"
        ]
        
        results = {}
        
        for query in semantic_queries:
            print(f"\n--- Query: '{query}' ---")
            
            try:
                embedding_response = self.embedder.create_embeddings([query])
                query_vector = embedding_response["embeddings"][0]
                
                search_results = self.vector_store.search(
                    query_vector=query_vector,
                    min_score=0.1,
                    max_results=10
                )
                
                print(f"Found {len(search_results)} results")
                
                semantic_results = []
                for i, result in enumerate(search_results):
                    payload = result.get("payload", {})
                    file_path = payload.get("filePath", "Unknown")
                    content = payload.get("codeChunk", "")
                    score = result.get("score", 0)
                    
                    # Check if result appears to be semantic (not just lines)
                    is_semantic = any(
                        keyword in content.lower() 
                        for keyword in ['def ', 'class ', 'function ', 'struct ', 'impl ']
                    )
                    
                    semantic_results.append({
                        "file": file_path,
                        "score": score,
                        "is_semantic": is_semantic,
                        "content_preview": content[:100].replace('\n', ' ')
                    })
                
                semantic_count = sum(1 for r in semantic_results if r["is_semantic"])
                semantic_ratio = semantic_count / len(semantic_results) if semantic_results else 0
                
                print(f"Semantic results: {semantic_count}/{len(semantic_results)} ({semantic_ratio:.1%})")
                
                results[query] = {
                    "total_results": len(search_results),
                    "semantic_results": semantic_count,
                    "semantic_ratio": semantic_ratio,
                    "top_score": search_results[0]["score"] if search_results else 0,
                    "sample_results": semantic_results[:3]
                }
                
            except Exception as e:
                print(f"Error searching for '{query}': {e}")
                results[query] = {
                    "error": str(e)
                }
        
        return results
    
    def compare_chunking_strategies(self) -> Dict[str, Any]:
        """Compare Tree-sitter vs line-based chunking."""
        print("\n=== Comparing Chunking Strategies ===")
        
        from code_index.chunking import LineChunkingStrategy, TreeSitterChunkingStrategy
        
        test_code = '''
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

class Calculator:
    """A simple calculator class."""
    
    def multiply(self, x, y):
        """Multiply two numbers."""
        return x * y
        
    def divide(self, x, y):
        """Divide two numbers."""
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y

# Some utility functions
def helper_function():
    return "helper"
'''
        
        line_strategy = LineChunkingStrategy(self.config)
        tree_sitter_strategy = TreeSitterChunkingStrategy(self.config)
        
        file_path = "test.py"
        file_hash = "test_hash"
        
        # Create a temporary file for chunking
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            # Line-based chunking
            file_hash = "test_hash_comparison"
            line_blocks = line_strategy.chunk(test_code, temp_file, file_hash)
            
            # Tree-sitter chunking
            tree_sitter_blocks = []
            try:
                tree_sitter_blocks = tree_sitter_strategy._chunk_text_treesitter(test_code, temp_file, file_hash)
            except Exception as e:
                print(f"Tree-sitter chunking failed: {e}")
                tree_sitter_blocks = line_strategy.chunk(test_code, temp_file, file_hash)
        finally:
            # Clean up temp file
            import os
            os.unlink(temp_file)
        
        comparison = {
            "line_based": {
                "blocks_count": len(line_blocks),
                "block_types": list(set(block.type for block in line_blocks)),
                "avg_lines_per_block": sum((block.end_line - block.start_line + 1) for block in line_blocks) / len(line_blocks) if line_blocks else 0
            },
            "tree_sitter": {
                "blocks_count": len(tree_sitter_blocks),
                "block_types": list(set(block.type for block in tree_sitter_blocks)),
                "avg_lines_per_block": sum((block.end_line - block.start_line + 1) for block in tree_sitter_blocks) / len(tree_sitter_blocks) if tree_sitter_blocks else 0
            }
        }
        
        print(f"Line-based: {comparison['line_based']['blocks_count']} blocks, types: {comparison['line_based']['block_types']}")
        print(f"Tree-sitter: {comparison['tree_sitter']['blocks_count']} blocks, types: {comparison['tree_sitter']['block_types']}")
        
        return comparison
    
    def run_comprehensive_tree_sitter_test(self) -> Dict[str, Any]:
        """Run comprehensive Tree-sitter testing."""
        print("🚀 Starting Comprehensive Tree-sitter Test Suite")
        print("=" * 60)
        
        # Validate environment
        if not self.validate_tree_sitter_environment():
            return {"overall_status": "failed", "error": "Tree-sitter environment validation failed"}
        
        all_results = {}
        
        # Run all test categories
        all_results["chunking_test"] = self.test_tree_sitter_chunking()
        all_results["search_quality"] = self.test_tree_sitter_search_quality()
        all_results["strategy_comparison"] = self.compare_chunking_strategies()
        
        # Generate summary
        summary = self._generate_summary(all_results)
        
        print("\n" + "=" * 60)
        print("🎉 Tree-sitter Test Suite Completed!")
        print(f"Overall status: {summary['overall_status']}")
        
        return {
            "overall_status": "success",
            "summary": summary,
            "detailed_results": all_results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary report."""
        chunking_results = results.get("chunking_test", {})
        search_results = results.get("search_quality", {})
        comparison_results = results.get("strategy_comparison", {})
        
        # Calculate chunking success rate
        chunking_success = sum(1 for r in chunking_results.values() if r.get("success", False))
        chunking_total = len(chunking_results)
        chunking_success_rate = chunking_success / chunking_total if chunking_total > 0 else 0
        
        # Calculate average semantic ratio
        semantic_ratios = [r.get("semantic_ratio", 0) for r in search_results.values() if isinstance(r, dict)]
        avg_semantic_ratio = sum(semantic_ratios) / len(semantic_ratios) if semantic_ratios else 0
        
        return {
            "chunking_success_rate": chunking_success_rate,
            "avg_semantic_ratio": avg_semantic_ratio,
            "overall_status": "success" if chunking_success_rate > 0.5 and avg_semantic_ratio > 0.3 else "partial",
            "chunking_details": {
                "successful_files": chunking_success,
                "total_files": chunking_total
            },
            "search_details": {
                "queries_tested": len(search_results),
                "avg_semantic_ratio": avg_semantic_ratio
            }
        }


def main():
    """Main function to run Tree-sitter tests."""
    parser = argparse.ArgumentParser(description="Test Tree-sitter semantic chunking functionality")
    parser.add_argument("--config", default="search_with_original_model.json", 
                       help="Path to configuration file")
    parser.add_argument("--output", help="Output file for test results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    tester = TreeSitterSearchTester(args.config)
    results = tester.run_comprehensive_tree_sitter_test()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")
    
    return 0 if results.get("overall_status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())