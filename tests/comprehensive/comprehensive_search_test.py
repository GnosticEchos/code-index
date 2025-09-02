#!/usr/bin/env python3
"""
Comprehensive Search Test Script for Code-Index Search Functionality

This script systematically tests all aspects of the code-index search functionality,
including basic queries, semantic queries, score thresholds, result limits, file types,
and performance measurements.
"""

import sys
import os
import time
import json
import argparse
import statistics
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore


class ComprehensiveSearchTester:
    """Comprehensive test suite for code-index search functionality."""
    
    def __init__(self, config_path: str):
        """Initialize the tester with configuration."""
        self.config = Config.from_file(config_path)
        self.embedder = OllamaEmbedder(self.config)
        self.vector_store = QdrantVectorStore(self.config)
        self.test_results = []
        self.performance_metrics = []
        
    def validate_environment(self) -> bool:
        """Validate that the environment is properly configured."""
        print("=== Environment Validation ===")
        
        # Validate Ollama configuration
        print("Validating Ollama configuration...")
        validation_result = self.embedder.validate_configuration()
        if not validation_result["valid"]:
            print(f"❌ Ollama validation failed: {validation_result['error']}")
            return False
        print("✅ Ollama configuration is valid")
        
        # Validate Qdrant connection
        print("Validating Qdrant connection...")
        try:
            collections = self.vector_store.client.get_collections()
            print(f"✅ Qdrant connection successful ({len(collections.collections)} collections)")
        except Exception as e:
            print(f"❌ Qdrant connection failed: {e}")
            return False
        
        # Validate collection exists
        print(f"Checking collection '{self.vector_store.collection_name}'...")
        if not self.vector_store.collection_exists():
            print(f"❌ Collection '{self.vector_store.collection_name}' does not exist")
            return False
        print("✅ Collection exists")
        
        return True
    
    def test_basic_queries(self) -> List[Dict[str, Any]]:
        """Test basic search queries."""
        print("\n=== Testing Basic Search Queries ===")
        
        basic_queries = [
            "search",
            "function",
            "class", 
            "test",
            "import",
            "export",
            "return",
            "def",
            "let",
            "const"
        ]
        
        results = []
        for query in basic_queries:
            result = self._run_search_test(
                query=query,
                test_type="basic",
                min_score=0.1,
                max_results=10
            )
            results.append(result)
        
        return results
    
    def test_semantic_queries(self) -> List[Dict[str, Any]]:
        """Test semantic code-specific queries."""
        print("\n=== Testing Semantic Code-Specific Queries ===")
        
        semantic_queries = [
            "authentication",
            "database",
            "API endpoint",
            "configuration",
            "error handling",
            "logging",
            "file operations",
            "network request",
            "user interface",
            "data validation"
        ]
        
        results = []
        for query in semantic_queries:
            result = self._run_search_test(
                query=query,
                test_type="semantic",
                min_score=0.1,
                max_results=10
            )
            results.append(result)
        
        return results
    
    def test_score_thresholds(self, query: str = "function") -> List[Dict[str, Any]]:
        """Test search with different score thresholds."""
        print(f"\n=== Testing Score Thresholds for query: '{query}' ===")
        
        thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
        results = []
        
        for threshold in thresholds:
            result = self._run_search_test(
                query=query,
                test_type=f"score_threshold_{threshold}",
                min_score=threshold,
                max_results=20
            )
            results.append(result)
        
        return results
    
    def test_result_limits(self, query: str = "class") -> List[Dict[str, Any]]:
        """Test search with different result limits."""
        print(f"\n=== Testing Result Limits for query: '{query}' ===")
        
        limits = [5, 10, 20, 50, 100]
        results = []
        
        for limit in limits:
            result = self._run_search_test(
                query=query,
                test_type=f"result_limit_{limit}",
                min_score=0.1,
                max_results=limit
            )
            results.append(result)
        
        return results
    
    def test_file_types(self) -> List[Dict[str, Any]]:
        """Test search across different file types."""
        print("\n=== Testing File Type Filtering ===")
        
        file_types = [
            (".py", "Python"),
            (".js", "JavaScript"),
            (".ts", "TypeScript"),
            (".md", "Markdown"),
            (".json", "JSON"),
            (".rs", "Rust"),
            (".html", "HTML"),
            (".css", "CSS")
        ]
        
        results = []
        for extension, description in file_types:
            # This is a simplified test - actual file type filtering would need
            # to be implemented in the search method
            result = self._run_search_test(
                query=f"{description} code",
                test_type=f"file_type_{extension}",
                min_score=0.1,
                max_results=5
            )
            results.append(result)
        
        return results
    
    def test_performance(self, query: str = "search", iterations: int = 5) -> Dict[str, Any]:
        """Measure search performance."""
        print(f"\n=== Performance Testing for query: '{query}' ===")
        
        response_times = []
        result_counts = []
        
        for i in range(iterations):
            start_time = time.time()
            
            embedding_response = self.embedder.create_embeddings([query])
            query_vector = embedding_response["embeddings"][0]
            
            results = self.vector_store.search(
                query_vector=query_vector,
                min_score=0.1,
                max_results=10
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            response_times.append(response_time)
            result_counts.append(len(results))
            
            print(f"Iteration {i+1}: {response_time:.2f}ms, {len(results)} results")
        
        return {
            "query": query,
            "iterations": iterations,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "std_dev_response_time": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "avg_result_count": statistics.mean(result_counts),
            "response_times": response_times,
            "result_counts": result_counts
        }
    
    def test_error_cases(self) -> List[Dict[str, Any]]:
        """Test error handling and edge cases."""
        print("\n=== Testing Error Cases and Edge Conditions ===")
        
        error_cases = [
            # Empty query
            {"query": "", "expected_error": True},
            # Very long query
            {"query": "x" * 1000, "expected_error": False},
            # Special characters
            {"query": "!@#$%^&*()_+-=[]{}|;:,.<>?", "expected_error": False},
            # Non-ASCII characters
            {"query": "café résumé naïve", "expected_error": False},
            # Code-like syntax
            {"query": "def function(): return True", "expected_error": False},
        ]
        
        results = []
        for case in error_cases:
            try:
                result = self._run_search_test(
                    query=case["query"],
                    test_type="error_case",
                    min_score=0.1,
                    max_results=5,
                    expect_error=case["expected_error"]
                )
                results.append(result)
            except Exception as e:
                if case["expected_error"]:
                    results.append({
                        "test_type": "error_case",
                        "query": case["query"],
                        "status": "expected_failure",
                        "error": str(e),
                        "results_count": 0,
                        "response_time": 0
                    })
                else:
                    results.append({
                        "test_type": "error_case",
                        "query": case["query"],
                        "status": "unexpected_failure",
                        "error": str(e),
                        "results_count": 0,
                        "response_time": 0
                    })
        
        return results
    
    def _run_search_test(self, query: str, test_type: str, min_score: float, 
                        max_results: int, expect_error: bool = False) -> Dict[str, Any]:
        """Run a single search test and return results."""
        start_time = time.time()
        
        try:
            embedding_response = self.embedder.create_embeddings([query])
            query_vector = embedding_response["embeddings"][0]
            
            results = self.vector_store.search(
                query_vector=query_vector,
                min_score=min_score,
                max_results=max_results
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Verify results match actual content (simplified check)
            valid_results = []
            for result in results:
                payload = result.get("payload", {})
                if all(key in payload for key in ["filePath", "codeChunk", "startLine", "endLine"]):
                    valid_results.append(result)
            
            status = "success" if not expect_error else "unexpected_success"
            
            return {
                "test_type": test_type,
                "query": query,
                "min_score": min_score,
                "max_results": max_results,
                "status": status,
                "results_count": len(results),
                "valid_results_count": len(valid_results),
                "response_time": response_time,
                "timestamp": datetime.now().isoformat(),
                "results_sample": results[:3] if results else []  # Sample of first 3 results
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            status = "expected_failure" if expect_error else "unexpected_failure"
            
            return {
                "test_type": test_type,
                "query": query,
                "min_score": min_score,
                "max_results": max_results,
                "status": status,
                "error": str(e),
                "results_count": 0,
                "response_time": response_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        print("🚀 Starting Comprehensive Search Test Suite")
        print(f"Workspace: {self.config.workspace_path}")
        print(f"Collection: {self.vector_store.collection_name}")
        print(f"Model: {self.config.ollama_model}")
        print("=" * 60)
        
        # Validate environment first
        if not self.validate_environment():
            return {"overall_status": "failed", "error": "Environment validation failed"}
        
        all_results = {}
        
        # Run all test categories
        all_results["basic_queries"] = self.test_basic_queries()
        all_results["semantic_queries"] = self.test_semantic_queries()
        all_results["score_thresholds"] = self.test_score_thresholds()
        all_results["result_limits"] = self.test_result_limits()
        all_results["file_types"] = self.test_file_types()
        all_results["performance"] = self.test_performance()
        all_results["error_cases"] = self.test_error_cases()
        
        # Generate summary report
        summary = self._generate_summary_report(all_results)
        
        print("\n" + "=" * 60)
        print("🎉 Comprehensive Test Suite Completed!")
        print(f"Total tests executed: {summary['total_tests']}")
        print(f"Successful tests: {summary['successful_tests']}")
        print(f"Failed tests: {summary['failed_tests']}")
        print(f"Overall status: {summary['overall_status']}")
        
        return {
            "overall_status": "success",
            "summary": summary,
            "detailed_results": all_results,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "workspace_path": self.config.workspace_path,
                "collection_name": self.vector_store.collection_name,
                "ollama_model": self.config.ollama_model,
                "embedding_length": self.config.embedding_length
            }
        }
    
    def _generate_summary_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary report from test results."""
        total_tests = 0
        successful_tests = 0
        failed_tests = 0
        
        for category, category_results in results.items():
            if category == "performance":
                continue  # Performance tests are measured differently
                
            for result in category_results:
                total_tests += 1
                if result.get("status") == "success":
                    successful_tests += 1
                else:
                    failed_tests += 1
        
        # Calculate performance metrics
        performance_metrics = {}
        if "performance" in results:
            perf = results["performance"]
            performance_metrics = {
                "avg_response_time_ms": perf["avg_response_time"],
                "min_response_time_ms": perf["min_response_time"],
                "max_response_time_ms": perf["max_response_time"],
                "response_time_std_dev": perf["std_dev_response_time"],
                "avg_results_per_query": perf["avg_result_count"]
            }
        
        overall_status = "success" if failed_tests == 0 else "partial_failure" if successful_tests > 0 else "complete_failure"
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "overall_status": overall_status,
            "performance_metrics": performance_metrics,
            "test_categories": list(results.keys())
        }
    
    def save_results(self, results: Dict[str, Any], output_path: str = "search_test_results.json"):
        """Save test results to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📊 Results saved to: {output_path}")
    
    def print_detailed_report(self, results: Dict[str, Any]):
        """Print a detailed report of test results."""
        print("\n" + "=" * 60)
        print("📋 DETAILED TEST REPORT")
        print("=" * 60)
        
        summary = results.get("summary", {})
        print(f"Overall Status: {summary.get('overall_status', 'unknown')}")
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Successful: {summary.get('successful_tests', 0)}")
        print(f"Failed: {summary.get('failed_tests', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        
        if "performance_metrics" in summary:
            print("\n📈 Performance Metrics:")
            perf = summary["performance_metrics"]
            print(f"  Average Response Time: {perf.get('avg_response_time_ms', 0):.2f}ms")
            print(f"  Min Response Time: {perf.get('min_response_time_ms', 0):.2f}ms")
            print(f"  Max Response Time: {perf.get('max_response_time_ms', 0):.2f}ms")
            print(f"  Response Time Std Dev: {perf.get('response_time_std_dev', 0):.2f}ms")
            print(f"  Average Results per Query: {perf.get('avg_results_per_query', 0):.1f}")
        
        # Print category summaries
        detailed = results.get("detailed_results", {})
        for category, category_results in detailed.items():
            if category == "performance":
                continue
                
            success_count = sum(1 for r in category_results if r.get("status") == "success")
            total_count = len(category_results)
            
            print(f"\n📊 {category.replace('_', ' ').title()}:")
            print(f"  Success: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
            
            # Show sample failures
            failures = [r for r in category_results if r.get("status") != "success"]
            if failures and len(failures) <= 3:
                for failure in failures:
                    print(f"    ❌ {failure.get('query', 'Unknown')}: {failure.get('error', 'Unknown error')}")


def main():
    """Main function to run the comprehensive search test."""
    parser = argparse.ArgumentParser(description="Comprehensive Search Test Script")
    parser.add_argument("--config", default="search_with_original_model.json",
                       help="Path to configuration file")
    parser.add_argument("--output", default="search_test_results.json",
                       help="Output file for test results")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    print("🔍 Comprehensive Search Test Script")
    print("=" * 50)
    
    try:
        # Initialize tester
        tester = ComprehensiveSearchTester(args.config)
        
        # Run comprehensive test suite
        results = tester.run_comprehensive_test_suite()
        
        # Save results
        tester.save_results(results, args.output)
        
        # Print detailed report
        tester.print_detailed_report(results)
        
        # Exit with appropriate code
        if results["overall_status"] == "success":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()