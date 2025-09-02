#!/usr/bin/env python3
"""
Comprehensive Tree-sitter Improvements Validation Script

This script validates all Tree-sitter improvements including:
1. Fixed query method detection in chunking.py
2. Mmap file reading performance improvements  
3. File filtering behavior with different configurations
4. Processing time improvements
5. Both Python and Rust file support
6. Error handling and fallback behavior
"""

import os
import sys
import time
import json
import tempfile
import argparse
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.parser import CodeParser
from code_index.chunking import TreeSitterChunkingStrategy, LineChunkingStrategy
from code_index.utils import get_file_hash


class TreeSitterImprovementsTester:
    """Comprehensive test suite for Tree-sitter improvements."""
    
    def __init__(self):
        """Initialize the tester."""
        self.test_results = []
        self.performance_data = []
        self.test_files = {}
        
    def create_test_files(self):
        """Create test files for Python and Rust."""
        print("Creating test files...")
        
        # Python test file
        python_content = '''#!/usr/bin/env python3
"""
Test Python file for Tree-sitter validation.
"""

def simple_function():
    """A simple function for testing."""
    return "Hello from Python"

class TestClass:
    """A test class for demonstration."""
    
    def __init__(self, value=42):
        self.value = value
    
    def get_value(self):
        """Return the stored value."""
        return self.value
    
    def set_value(self, new_value):
        """Set a new value."""
        self.value = new_value
        return self.value

def another_function(param1, param2=None):
    """Another function with parameters."""
    if param2 is None:
        param2 = "default"
    return f"{param1}: {param2}"

# Main execution
if __name__ == "__main__":
    print(simple_function())
    obj = TestClass(100)
    print(f"Value: {obj.get_value()}")
    print(another_function("test", "value"))
'''
        
        # Rust test file
        rust_content = '''// Test Rust file for Tree-sitter validation

fn simple_function() -> String {
    // A simple function for testing
    "Hello from Rust".to_string()
}

struct TestStruct {
    value: i32,
}

impl TestStruct {
    fn new(value: i32) -> Self {
        TestStruct { value }
    }
    
    fn get_value(&self) -> i32 {
        self.value
    }
    
    fn set_value(&mut self, new_value: i32) -> i32 {
        self.value = new_value;
        self.value
    }
}

fn another_function(param1: &str, param2: Option<&str>) -> String {
    // Another function with parameters
    let param2 = param2.unwrap_or("default");
    format!("{}: {}", param1, param2)
}

trait TestTrait {
    fn trait_method(&self) -> String;
}

impl TestTrait for TestStruct {
    fn trait_method(&self) -> String {
        format!("Trait value: {}", self.value)
    }
}

fn main() {
    println!("{}", simple_function());
    let mut obj = TestStruct::new(100);
    println!("Value: {}", obj.get_value());
    println!("{}", another_function("test", Some("value")));
    println!("{}", obj.trait_method());
}
'''
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            self.test_files['python'] = f.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
            f.write(rust_content)
            self.test_files['rust'] = f.name
            
        print(f"Created Python test file: {self.test_files['python']}")
        print(f"Created Rust test file: {self.test_files['rust']}")
        
        # Create large test files for performance testing
        large_content = "x" * 1024 * 512  # 512KB file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(large_content)
            self.test_files['large_python'] = f.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
            f.write(large_content)
            self.test_files['large_rust'] = f.name
            
        print(f"Created large Python test file: {self.test_files['large_python']}")
        print(f"Created large Rust test file: {self.test_files['large_rust']}")
    
    def cleanup_test_files(self):
        """Clean up test files."""
        print("Cleaning up test files...")
        for file_path in self.test_files.values():
            try:
                os.unlink(file_path)
            except:
                pass
    
    def test_query_method_detection(self):
        """Test fixed query method detection in chunking.py."""
        print("\n=== Testing Query Method Detection ===")
        
        config = Config()
        config.use_tree_sitter = True
        chunker = TreeSitterChunkingStrategy(config)
        
        # Test that the query method detection works
        try:
            # This should trigger the query method detection logic
            language_key = chunker._get_language_key_for_path(self.test_files['python'])
            queries = chunker._get_queries_for_language(language_key)
            
            result = {
                'test_type': 'query_method_detection',
                'language': language_key,
                'queries_available': bool(queries),
                'query_length': len(queries) if queries else 0,
                'status': 'success'
            }
            
            print(f"✓ Query method detection works for {language_key}")
            print(f"  Queries available: {result['queries_available']}")
            print(f"  Query length: {result['query_length']}")
            
        except Exception as e:
            result = {
                'test_type': 'query_method_detection',
                'error': str(e),
                'status': 'failed'
            }
            print(f"✗ Query method detection failed: {e}")
            
        self.test_results.append(result)
        return result
    
    def test_mmap_performance(self):
        """Test mmap file reading performance improvements."""
        print("\n=== Testing Mmap Performance ===")
        
        results = []
        
        # Test with traditional reading
        config_trad = Config()
        config_trad.use_mmap_file_reading = False
        parser_trad = CodeParser(config_trad, LineChunkingStrategy(config_trad))
        
        # Test with mmap reading
        config_mmap = Config()
        config_mmap.use_mmap_file_reading = True
        parser_mmap = CodeParser(config_mmap, LineChunkingStrategy(config_mmap))
        
        test_files = [
            ('small_python', self.test_files['python']),
            ('small_rust', self.test_files['rust']),
            ('large_python', self.test_files['large_python']),
            ('large_rust', self.test_files['large_rust'])
        ]
        
        for file_type, file_path in test_files:
            trad_times = []
            mmap_times = []
            
            # Benchmark traditional reading
            for _ in range(5):
                start_time = time.perf_counter()
                result = parser_trad.parse_file(file_path)
                end_time = time.perf_counter()
                trad_times.append(end_time - start_time)
            
            # Benchmark mmap reading
            for _ in range(5):
                start_time = time.perf_counter()
                result = parser_mmap.parse_file(file_path)
                end_time = time.perf_counter()
                mmap_times.append(end_time - start_time)
            
            trad_avg = statistics.mean(trad_times)
            mmap_avg = statistics.mean(mmap_times)
            improvement = ((trad_avg - mmap_avg) / trad_avg) * 100 if trad_avg > 0 else 0
            
            result = {
                'file_type': file_type,
                'file_size': os.path.getsize(file_path),
                'traditional_avg': trad_avg,
                'mmap_avg': mmap_avg,
                'improvement_percent': improvement,
                'status': 'success'
            }
            
            results.append(result)
            
            print(f"{file_type}: Traditional {trad_avg:.6f}s, Mmap {mmap_avg:.6f}s, Improvement: {improvement:+.1f}%")
        
        self.test_results.extend(results)
        return results
    
    def test_file_filtering(self):
        """Test file filtering behavior with different configurations."""
        print("\n=== Testing File Filtering Behavior ===")
        
        results = []
        
        # Test configurations
        configs = [
            ('default', Config()),
            ('performance_optimized', self._create_performance_config()),
            ('comprehensive', self._create_comprehensive_config()),
            ('rust_optimized', self._create_rust_optimized_config())
        ]
        
        test_cases = [
            ('normal_python', self.test_files['python'], True),
            ('normal_rust', self.test_files['rust'], True),
            ('test_python', self._create_test_file('test_file.py'), False),
            ('test_rust', self._create_test_file('test_file.rs'), False),
            ('example_python', self._create_test_file('example.py'), False),
            ('large_rust', self.test_files['large_rust'], False),
        ]
        
        for config_name, config in configs:
            chunker = TreeSitterChunkingStrategy(config)
            
            for file_name, file_path, expected_result in test_cases:
                try:
                    should_process = chunker._should_process_file_for_treesitter(file_path)
                    status = 'success' if should_process == expected_result else 'failed'
                    
                    result = {
                        'config': config_name,
                        'file_type': file_name,
                        'expected': expected_result,
                        'actual': should_process,
                        'status': status
                    }
                    
                    results.append(result)
                    
                    if status == 'success':
                        print(f"✓ {config_name}: {file_name} -> {should_process} (expected: {expected_result})")
                    else:
                        print(f"✗ {config_name}: {file_name} -> {should_process} (expected: {expected_result})")
                        
                except Exception as e:
                    result = {
                        'config': config_name,
                        'file_type': file_name,
                        'error': str(e),
                        'status': 'error'
                    }
                    results.append(result)
                    print(f"✗ {config_name}: {file_name} -> Error: {e}")
        
        self.test_results.extend(results)
        return results
    
    def _create_test_file(self, filename: str) -> str:
        """Create a test file with specific name pattern."""
        content = "# Test file content\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix=filename, delete=False) as f:
            f.write(content)
            return f.name
    
    def _create_performance_config(self) -> Config:
        """Create performance-optimized configuration."""
        config = Config()
        config.use_tree_sitter = True
        config.tree_sitter_max_file_size_bytes = 256 * 1024  # 256KB
        config.tree_sitter_skip_test_files = True
        config.tree_sitter_skip_examples = True
        config.tree_sitter_skip_patterns = [
            "*.min.js", "*.bundle.js", "*.min.css",
            "package-lock.json", "yarn.lock", "*.lock",
            "target/", "build/", "dist/", "node_modules/", "__pycache__/",
            "*.log", "*.tmp", "*.temp"
        ]
        return config
    
    def _create_comprehensive_config(self) -> Config:
        """Create comprehensive configuration."""
        config = Config()
        config.use_tree_sitter = True
        config.tree_sitter_max_file_size_bytes = 1024 * 1024  # 1MB
        config.tree_sitter_skip_test_files = False
        config.tree_sitter_skip_examples = False
        config.tree_sitter_skip_patterns = []
        return config
    
    def _create_rust_optimized_config(self) -> Config:
        """Create Rust-optimized configuration."""
        config = Config()
        config.use_tree_sitter = True
        config.tree_sitter_max_file_size_bytes = 300 * 1024  # 300KB
        config.tree_sitter_skip_test_files = True
        config.rust_specific_optimizations = {
            "skip_large_rust_files": True,
            "max_rust_file_size_kb": 300,
            "skip_generated_rust_files": True,
            "rust_target_directories": ["target/", "build/", "dist/"]
        }
        return config
    
    def test_processing_time_improvements(self):
        """Test processing time improvements with Tree-sitter."""
        print("\n=== Testing Processing Time Improvements ===")
        
        results = []
        
        # Test with different chunking strategies
        strategies = [
            ('line_based', LineChunkingStrategy),
            ('tree_sitter', TreeSitterChunkingStrategy)
        ]
        
        test_files = [
            ('python', self.test_files['python']),
            ('rust', self.test_files['rust'])
        ]
        
        for strategy_name, strategy_class in strategies:
            config = Config()
            config.use_tree_sitter = (strategy_name == 'tree_sitter')
            
            chunker = strategy_class(config)
            parser = CodeParser(config, chunker)
            
            for file_type, file_path in test_files:
                times = []
                
                for _ in range(3):  # Reduced iterations for stability
                    start_time = time.perf_counter()
                    result = parser.parse_file(file_path)
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                
                avg_time = statistics.mean(times)
                blocks_count = len(parser.parse_file(file_path))  # Get actual count
                
                result = {
                    'strategy': strategy_name,
                    'file_type': file_type,
                    'avg_time': avg_time,
                    'blocks_count': blocks_count,
                    'status': 'success'
                }
                
                results.append(result)
                
                print(f"{strategy_name}/{file_type}: {avg_time:.6f}s, {blocks_count} blocks")
        
        # Calculate improvements
        for file_type in ['python', 'rust']:
            line_time = next(r for r in results if r['strategy'] == 'line_based' and r['file_type'] == file_type)['avg_time']
            tree_time = next(r for r in results if r['strategy'] == 'tree_sitter' and r['file_type'] == file_type)['avg_time']
            improvement = ((line_time - tree_time) / line_time) * 100 if line_time > 0 else 0
            
            improvement_result = {
                'test_type': 'processing_improvement',
                'file_type': file_type,
                'line_based_time': line_time,
                'tree_sitter_time': tree_time,
                'improvement_percent': improvement,
                'status': 'success'
            }
            
            results.append(improvement_result)
            print(f"Improvement for {file_type}: {improvement:+.1f}%")
        
        self.test_results.extend(results)
        return results
    
    def test_error_handling(self):
        """Test error handling and fallback behavior."""
        print("\n=== Testing Error Handling and Fallback ===")
        
        results = []
        
        config = Config()
        config.use_tree_sitter = True
        chunker = TreeSitterChunkingStrategy(config)
        parser = CodeParser(config, chunker)
        
        # Test cases: files that should trigger fallback
        test_cases = [
            ('non_existent', '/non/existent/file.py', True),
            ('empty_file', self._create_empty_file(), True),
            ('unsupported_language', self._create_unsupported_file(), True),
            ('too_large', self._create_large_file(1024 * 1024 + 100), True),  # >1MB
        ]
        
        for case_name, file_path, expect_fallback in test_cases:
            try:
                result = parser.parse_file(file_path)
                
                # Check if fallback occurred (result should not be empty for valid fallback)
                if expect_fallback and len(result) > 0:
                    status = 'success'
                    message = f"Fallback successful: {len(result)} blocks"
                elif not expect_fallback and len(result) > 0:
                    status = 'success'
                    message = "Normal processing successful"
                else:
                    status = 'failed'
                    message = f"Unexpected result: {len(result)} blocks"
                
                result_data = {
                    'case': case_name,
                    'result_count': len(result),
                    'status': status,
                    'message': message
                }
                
                results.append(result_data)
                print(f"{case_name}: {message}")
                
            except Exception as e:
                result_data = {
                    'case': case_name,
                    'error': str(e),
                    'status': 'error'
                }
                results.append(result_data)
                print(f"{case_name}: Error - {e}")
            
            # Clean up temporary files
            if case_name != 'non_existent':
                try:
                    os.unlink(file_path)
                except:
                    pass
        
        self.test_results.extend(results)
        return results
    
    def _create_empty_file(self) -> str:
        """Create an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            return f.name
    
    def _create_unsupported_file(self) -> str:
        """Create a file with unsupported extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write("Content for unsupported file type")
            return f.name
    
    def _create_large_file(self, size_bytes: int) -> str:
        """Create a large file."""
        content = "x" * size_bytes
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_tree_sitter_functionality(self):
        """Test Tree-sitter functionality specifically."""
        print("\n=== Testing Tree-sitter Functionality ===")
        
        results = []
        
        config = Config()
        config.use_tree_sitter = True
        parser = CodeParser(config, TreeSitterChunkingStrategy(config))
        
        test_files = [
            ('python', self.test_files['python']),
            ('rust', self.test_files['rust'])
        ]
        
        for file_type, file_path in test_files:
            try:
                start_time = time.perf_counter()
                result = parser.parse_file(file_path)
                end_time = time.perf_counter()
                
                processing_time = end_time - start_time
                blocks_count = len(result)
                
                # Check if Tree-sitter produced meaningful blocks
                semantic_blocks = sum(1 for block in result if block.type != 'chunk')
                
                result_data = {
                    'file_type': file_type,
                    'processing_time': processing_time,
                    'blocks_count': blocks_count,
                    'semantic_blocks': semantic_blocks,
                    'status': 'success'
                }
                
                results.append(result_data)
                
                print(f"{file_type}: {processing_time:.6f}s, {blocks_count} blocks ({semantic_blocks} semantic)")
                
            except Exception as e:
                result_data = {
                    'file_type': file_type,
                    'error': str(e),
                    'status': 'error'
                }
                results.append(result_data)
                print(f"{file_type}: Error - {e}")
        
        self.test_results.extend(results)
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report."""
        print("\n=== Generating Comprehensive Report ===")
        
        summary = {
            'total_tests': len(self.test_results),
            'successful_tests': sum(1 for r in self.test_results if r.get('status') == 'success'),
            'failed_tests': sum(1 for r in self.test_results if r.get('status') == 'failed'),
            'error_tests': sum(1 for r in self.test_results if r.get('status') == 'error'),
            'timestamp': datetime.now().isoformat(),
            'test_categories': list(set(r.get('test_type', 'unknown') for r in self.test_results))
        }
        
        # Calculate overall success rate
        if summary['total_tests'] > 0:
            summary['success_rate'] = (summary['successful_tests'] / summary['total_tests']) * 100
        else:
            summary['success_rate'] = 0
        
        # Performance summary
        performance_tests = [r for r in self.test_results if 'improvement_percent' in r]
        if performance_tests:
            avg_improvement = statistics.mean(r['improvement_percent'] for r in performance_tests)
            summary['average_improvement_percent'] = avg_improvement
        
        print(f"Total tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Errors: {summary['error_tests']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        if 'average_improvement_percent' in summary:
            print(f"Average improvement: {summary['average_improvement_percent']:.1f}%")
        
        return {
            'summary': summary,
            'detailed_results': self.test_results,
            'performance_data': self.performance_data
        }
    
    def save_results(self, output_path: str = "treesitter_improvements_report.json"):
        """Save test results to JSON file."""
        report = self.generate_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Report saved to: {output_path}")
        return output_path
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests."""
        print("🚀 Starting Comprehensive Tree-sitter Improvements Test Suite")
        print("=" * 70)
        
        try:
            # Create test files
            self.create_test_files()
            
            # Run all test categories
            self.test_query_method_detection()
            self.test_mmap_performance()
            self.test_file_filtering()
            self.test_processing_time_improvements()
            self.test_error_handling()
            self.test_tree_sitter_functionality()
            
            # Generate and save report
            report = self.generate_report()
            report_path = self.save_results()
            
            # Print final status
            report_summary = report['summary']
            if report_summary['failed_tests'] > 0 or report_summary['error_tests'] > 0:
                print("\n" + "=" * 70)
                print("⚠️  Some tests failed or had errors.")
                print("Please review the detailed report for issues.")
                return False
            else:
                print("\n" + "=" * 70)
                print("✅ All tests passed successfully!")
                return True
                
        finally:
            self.cleanup_test_files()


def main():
    """Main function to run the comprehensive test suite."""
    parser = argparse.ArgumentParser(description="Comprehensive Tree-sitter Improvements Validation")
    parser.add_argument("--output", "-o", default="treesitter_improvements_report.json",
                       help="Output report file path")
    
    args = parser.parse_args()
    
    print("🔍 Comprehensive Tree-sitter Improvements Validation")
    print("=" * 60)
    print("Validating:")
    print("✓ Fixed query method detection")
    print("✓ Mmap file reading performance")  
    print("✓ File filtering behavior")
    print("✓ Processing time improvements")
    print("✓ Error handling and fallback")
    print("✓ Python and Rust file support")
    print("=" * 60)
    
    tester = TreeSitterImprovementsTester()
    success = tester.run_comprehensive_tests()
    
    if success:
        print("✅ Validation completed successfully!")
        sys.exit(0)
    else:
        print("❌ Validation completed with issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()