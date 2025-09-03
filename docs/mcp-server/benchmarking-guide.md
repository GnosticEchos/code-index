# MCP Server Benchmarking Guide

This guide provides comprehensive benchmarking methodologies, performance comparison examples, and optimization validation techniques for the Code Index MCP Server.

## Table of Contents

- [Benchmarking Overview](#benchmarking-overview)
- [Performance Metrics](#performance-metrics)
- [Benchmarking Scripts](#benchmarking-scripts)
- [Configuration Comparisons](#configuration-comparisons)
- [Before/After Analysis](#beforeafter-analysis)
- [Hardware Impact Analysis](#hardware-impact-analysis)
- [Optimization Validation](#optimization-validation)

## Benchmarking Overview

### Why Benchmark?

Benchmarking helps you:
- **Choose optimal configurations** for your specific use case
- **Validate performance improvements** after configuration changes
- **Compare different chunking strategies** and their trade-offs
- **Identify bottlenecks** in your indexing pipeline
- **Make data-driven decisions** about hardware and configuration

### Benchmarking Principles

1. **Consistent Environment**: Use the same hardware, services, and test data
2. **Multiple Runs**: Average results across multiple runs to account for variance
3. **Isolated Changes**: Test one configuration change at a time
4. **Realistic Data**: Use representative codebases for your use case
5. **Comprehensive Metrics**: Measure speed, memory, accuracy, and resource usage

## Performance Metrics

### Primary Metrics

| Metric | Description | Good Value | Measurement |
|--------|-------------|------------|-------------|
| **Files/Second** | Indexing throughput | >100 files/sec | Files processed ÷ Total time |
| **Memory Usage** | Peak memory consumption | <500MB | Process RSS memory |
| **Search Latency** | Time to return results | <1 second | Query time |
| **Accuracy Score** | Search result relevance | >0.6 avg score | Average adjusted score |

### Secondary Metrics

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Startup Time** | Time to initialize services | Service connection time |
| **Storage Efficiency** | Vector DB size vs source size | Qdrant collection size ÷ Source code size |
| **Error Rate** | Percentage of failed operations | Errors ÷ Total operations |
| **Resource Utilization** | CPU and disk usage | System monitoring |

## Benchmarking Scripts

### Comprehensive Benchmark Suite

```python
import time
import psutil
import os
import json
import statistics
from typing import Dict, List, Any
from pathlib import Path

class MCPBenchmark:
    """Comprehensive benchmarking suite for MCP server."""
    
    def __init__(self, workspace: str, test_queries: List[str]):
        self.workspace = workspace
        self.test_queries = test_queries
        self.results = {}
        
    def benchmark_configuration(self, config: Dict[str, Any], name: str, runs: int = 3) -> Dict[str, Any]:
        """Benchmark a specific configuration across multiple runs."""
        print(f"\n=== Benchmarking {name} ===")
        
        run_results = []
        
        for run in range(runs):
            print(f"Run {run + 1}/{runs}...")
            
            # Clean up before each run
            self._cleanup_collections()
            
            # Measure indexing performance
            index_result = self._benchmark_indexing(config)
            
            # Measure search performance
            search_result = self._benchmark_search()
            
            # Combine results
            run_result = {
                **index_result,
                **search_result,
                "run": run + 1
            }
            run_results.append(run_result)
        
        # Calculate averages and statistics
        averaged_result = self._calculate_statistics(run_results, name)
        self.results[name] = averaged_result
        
        return averaged_result
    
    def _benchmark_indexing(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark indexing performance."""
        # Monitor system resources
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss
        start_time = time.time()
        
        try:
            # Run indexing
            result = index(workspace=self.workspace, **config)
            
            end_time = time.time()
            end_memory = process.memory_info().rss
            
            duration = end_time - start_time
            memory_used = (end_memory - start_memory) / 1024 / 1024  # MB
            peak_memory = end_memory / 1024 / 1024  # MB
            
            files_processed = result.get('files_processed', 0)
            files_per_second = files_processed / duration if duration > 0 else 0
            
            return {
                "index_success": True,
                "index_duration": duration,
                "files_processed": files_processed,
                "files_per_second": files_per_second,
                "memory_used_mb": memory_used,
                "peak_memory_mb": peak_memory,
                "total_segments": result.get('total_segments', 0),
                "timeout_files": len(result.get('timeout_files', []))
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                "index_success": False,
                "index_duration": duration,
                "index_error": str(e),
                "files_processed": 0,
                "files_per_second": 0,
                "memory_used_mb": 0,
                "peak_memory_mb": 0,
                "total_segments": 0,
                "timeout_files": 0
            }
    
    def _benchmark_search(self) -> Dict[str, Any]:
        """Benchmark search performance across test queries."""
        search_results = []
        
        for query in self.test_queries:
            start_time = time.time()
            
            try:
                results = search(query=query, workspace=self.workspace)
                end_time = time.time()
                
                duration = end_time - start_time
                result_count = len(results)
                avg_score = statistics.mean([r['adjustedScore'] for r in results]) if results else 0
                top_score = max([r['adjustedScore'] for r in results]) if results else 0
                
                search_results.append({
                    "query": query,
                    "success": True,
                    "duration": duration,
                    "result_count": result_count,
                    "avg_score": avg_score,
                    "top_score": top_score
                })
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                
                search_results.append({
                    "query": query,
                    "success": False,
                    "duration": duration,
                    "error": str(e),
                    "result_count": 0,
                    "avg_score": 0,
                    "top_score": 0
                })
        
        # Calculate search statistics
        successful_searches = [r for r in search_results if r['success']]
        
        if successful_searches:
            avg_search_duration = statistics.mean([r['duration'] for r in successful_searches])
            avg_result_count = statistics.mean([r['result_count'] for r in successful_searches])
            avg_search_score = statistics.mean([r['avg_score'] for r in successful_searches])
            search_success_rate = len(successful_searches) / len(search_results)
        else:
            avg_search_duration = 0
            avg_result_count = 0
            avg_search_score = 0
            search_success_rate = 0
        
        return {
            "search_success_rate": search_success_rate,
            "avg_search_duration": avg_search_duration,
            "avg_result_count": avg_result_count,
            "avg_search_score": avg_search_score,
            "search_details": search_results
        }
    
    def _calculate_statistics(self, run_results: List[Dict], name: str) -> Dict[str, Any]:
        """Calculate statistics across multiple runs."""
        # Extract numeric metrics
        numeric_metrics = [
            'index_duration', 'files_processed', 'files_per_second',
            'memory_used_mb', 'peak_memory_mb', 'total_segments',
            'avg_search_duration', 'avg_result_count', 'avg_search_score'
        ]
        
        stats = {"configuration_name": name, "runs": len(run_results)}
        
        for metric in numeric_metrics:
            values = [r.get(metric, 0) for r in run_results if r.get('index_success', True)]
            
            if values:
                stats[f"{metric}_mean"] = statistics.mean(values)
                stats[f"{metric}_median"] = statistics.median(values)
                stats[f"{metric}_stdev"] = statistics.stdev(values) if len(values) > 1 else 0
                stats[f"{metric}_min"] = min(values)
                stats[f"{metric}_max"] = max(values)
        
        # Calculate success rates
        index_successes = sum(1 for r in run_results if r.get('index_success', False))
        stats['index_success_rate'] = index_successes / len(run_results)
        
        return stats
    
    def _cleanup_collections(self):
        """Clean up collections before each run."""
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass  # Ignore cleanup errors
    
    def compare_configurations(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """Compare multiple configurations and generate report."""
        print("\n" + "="*80)
        print("CONFIGURATION COMPARISON REPORT")
        print("="*80)
        
        # Run benchmarks for each configuration
        for name, config in configs.items():
            self.benchmark_configuration(config, name)
        
        # Generate comparison table
        self._print_comparison_table()
        
        # Generate recommendations
        self._print_recommendations()
    
    def _print_comparison_table(self):
        """Print formatted comparison table."""
        if not self.results:
            return
        
        print(f"\n{'Configuration':<20} {'Files/Sec':<12} {'Memory(MB)':<12} {'Search(ms)':<12} {'Accuracy':<10}")
        print("-" * 70)
        
        for name, result in self.results.items():
            files_per_sec = result.get('files_per_second_mean', 0)
            memory_mb = result.get('peak_memory_mb_mean', 0)
            search_ms = result.get('avg_search_duration_mean', 0) * 1000
            accuracy = result.get('avg_search_score_mean', 0)
            
            print(f"{name:<20} {files_per_sec:<12.1f} {memory_mb:<12.1f} {search_ms:<12.1f} {accuracy:<10.3f}")
    
    def _print_recommendations(self):
        """Print performance recommendations."""
        if not self.results:
            return
        
        print("\n" + "="*50)
        print("RECOMMENDATIONS")
        print("="*50)
        
        # Find best performers
        best_speed = max(self.results.items(), key=lambda x: x[1].get('files_per_second_mean', 0))
        best_memory = min(self.results.items(), key=lambda x: x[1].get('peak_memory_mb_mean', float('inf')))
        best_accuracy = max(self.results.items(), key=lambda x: x[1].get('avg_search_score_mean', 0))
        
        print(f"🚀 Fastest indexing: {best_speed[0]} ({best_speed[1].get('files_per_second_mean', 0):.1f} files/sec)")
        print(f"💾 Lowest memory: {best_memory[0]} ({best_memory[1].get('peak_memory_mb_mean', 0):.1f} MB)")
        print(f"🎯 Best accuracy: {best_accuracy[0]} ({best_accuracy[1].get('avg_search_score_mean', 0):.3f} avg score)")
        
        # Performance analysis
        print(f"\nPerformance Analysis:")
        for name, result in self.results.items():
            issues = []
            
            if result.get('files_per_second_mean', 0) < 50:
                issues.append("slow indexing")
            if result.get('peak_memory_mb_mean', 0) > 500:
                issues.append("high memory usage")
            if result.get('avg_search_duration_mean', 0) > 2:
                issues.append("slow search")
            if result.get('avg_search_score_mean', 0) < 0.4:
                issues.append("low accuracy")
            
            if issues:
                print(f"⚠️  {name}: {', '.join(issues)}")
            else:
                print(f"✅ {name}: good performance")
    
    def export_results(self, filename: str):
        """Export benchmark results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults exported to {filename}")

# Example usage
def run_comprehensive_benchmark():
    """Run a comprehensive benchmark comparing different configurations."""
    
    # Test workspace and queries
    workspace = "/path/to/test/project"
    test_queries = [
        "authentication middleware",
        "database connection",
        "error handling",
        "user interface component",
        "API endpoint handler"
    ]
    
    # Configurations to test
    configs = {
        "fast": {
            "chunking_strategy": "lines",
            "batch_segment_threshold": 100,
            "max_file_size_bytes": 262144
        },
        "balanced": {
            "chunking_strategy": "tokens",
            "token_chunk_size": 800,
            "batch_segment_threshold": 60
        },
        "accurate": {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True,
            "batch_segment_threshold": 30
        },
        "memory_optimized": {
            "chunking_strategy": "lines",
            "batch_segment_threshold": 20,
            "max_file_size_bytes": 131072
        }
    }
    
    # Run benchmark
    benchmark = MCPBenchmark(workspace, test_queries)
    benchmark.compare_configurations(configs)
    benchmark.export_results("benchmark_results.json")

if __name__ == "__main__":
    run_comprehensive_benchmark()
```

### Quick Performance Test

```python
def quick_performance_test(workspace: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Quick performance test for a single configuration."""
    
    print("Running quick performance test...")
    
    # Measure indexing
    start_time = time.time()
    start_memory = psutil.Process(os.getpid()).memory_info().rss
    
    index_result = index(workspace=workspace, **config)
    
    end_time = time.time()
    end_memory = psutil.Process(os.getpid()).memory_info().rss
    
    # Calculate metrics
    duration = end_time - start_time
    memory_used = (end_memory - start_memory) / 1024 / 1024
    files_processed = index_result.get('files_processed', 0)
    files_per_second = files_processed / duration if duration > 0 else 0
    
    # Test search performance
    search_start = time.time()
    search_results = search(query="test query", workspace=workspace)
    search_duration = time.time() - search_start
    
    result = {
        "indexing": {
            "duration_seconds": duration,
            "files_processed": files_processed,
            "files_per_second": files_per_second,
            "memory_used_mb": memory_used,
            "peak_memory_mb": end_memory / 1024 / 1024
        },
        "search": {
            "duration_seconds": search_duration,
            "result_count": len(search_results),
            "avg_score": sum(r['adjustedScore'] for r in search_results) / len(search_results) if search_results else 0
        }
    }
    
    print(f"Indexing: {files_per_second:.1f} files/sec, {memory_used:.1f} MB")
    print(f"Search: {search_duration*1000:.1f}ms, {len(search_results)} results")
    
    return result
```

## Configuration Comparisons

### Chunking Strategy Comparison

```python
def compare_chunking_strategies(workspace: str):
    """Compare different chunking strategies."""
    
    strategies = {
        "lines": {
            "chunking_strategy": "lines"
        },
        "tokens": {
            "chunking_strategy": "tokens",
            "token_chunk_size": 800,
            "token_chunk_overlap": 160
        },
        "treesitter": {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True
        }
    }
    
    results = {}
    
    for name, config in strategies.items():
        print(f"\nTesting {name} chunking...")
        
        # Clean collections
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        
        # Benchmark
        result = quick_performance_test(workspace, config)
        results[name] = result
        
        print(f"{name}: {result['indexing']['files_per_second']:.1f} files/sec")
    
    # Print comparison
    print("\n" + "="*60)
    print("CHUNKING STRATEGY COMPARISON")
    print("="*60)
    print(f"{'Strategy':<12} {'Speed':<15} {'Memory':<15} {'Search':<15}")
    print("-" * 60)
    
    for name, result in results.items():
        speed = f"{result['indexing']['files_per_second']:.1f} files/sec"
        memory = f"{result['indexing']['peak_memory_mb']:.1f} MB"
        search = f"{result['search']['duration_seconds']*1000:.1f} ms"
        
        print(f"{name:<12} {speed:<15} {memory:<15} {search:<15}")
    
    return results
```

### Batch Size Optimization

```python
def optimize_batch_size(workspace: str, batch_sizes: List[int] = [20, 40, 60, 80, 100]):
    """Find optimal batch size for the given workspace."""
    
    results = {}
    
    for batch_size in batch_sizes:
        print(f"\nTesting batch size {batch_size}...")
        
        config = {
            "chunking_strategy": "lines",
            "batch_segment_threshold": batch_size
        }
        
        # Clean collections
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        
        # Benchmark
        result = quick_performance_test(workspace, config)
        results[batch_size] = result
    
    # Find optimal batch size
    optimal_batch = max(results.items(), key=lambda x: x[1]['indexing']['files_per_second'])
    
    print(f"\n🎯 Optimal batch size: {optimal_batch[0]} ({optimal_batch[1]['indexing']['files_per_second']:.1f} files/sec)")
    
    return results, optimal_batch[0]
```

## Before/After Analysis

### Configuration Change Impact

```python
def analyze_configuration_change(workspace: str, before_config: Dict, after_config: Dict, change_description: str):
    """Analyze the impact of a configuration change."""
    
    print(f"\n=== Analyzing: {change_description} ===")
    
    # Benchmark before configuration
    print("Testing BEFORE configuration...")
    try:
        collections(subcommand="clear-all", yes=True)
    except:
        pass
    before_result = quick_performance_test(workspace, before_config)
    
    # Benchmark after configuration
    print("Testing AFTER configuration...")
    try:
        collections(subcommand="clear-all", yes=True)
    except:
        pass
    after_result = quick_performance_test(workspace, after_config)
    
    # Calculate improvements
    speed_improvement = (after_result['indexing']['files_per_second'] / before_result['indexing']['files_per_second'] - 1) * 100
    memory_change = after_result['indexing']['peak_memory_mb'] - before_result['indexing']['peak_memory_mb']
    search_improvement = (before_result['search']['duration_seconds'] / after_result['search']['duration_seconds'] - 1) * 100
    
    # Print analysis
    print(f"\n📊 IMPACT ANALYSIS: {change_description}")
    print("-" * 50)
    print(f"Indexing speed: {speed_improvement:+.1f}% ({before_result['indexing']['files_per_second']:.1f} → {after_result['indexing']['files_per_second']:.1f} files/sec)")
    print(f"Memory usage: {memory_change:+.1f} MB ({before_result['indexing']['peak_memory_mb']:.1f} → {after_result['indexing']['peak_memory_mb']:.1f} MB)")
    print(f"Search speed: {search_improvement:+.1f}% ({before_result['search']['duration_seconds']*1000:.1f} → {after_result['search']['duration_seconds']*1000:.1f} ms)")
    
    # Recommendations
    if speed_improvement > 10:
        print("✅ Significant speed improvement!")
    elif speed_improvement > 0:
        print("🟡 Modest speed improvement")
    else:
        print("❌ Speed regression")
    
    if memory_change < -50:
        print("✅ Significant memory reduction!")
    elif memory_change < 0:
        print("🟡 Memory usage reduced")
    elif memory_change > 100:
        print("❌ Significant memory increase")
    
    return {
        "before": before_result,
        "after": after_result,
        "improvements": {
            "speed_percent": speed_improvement,
            "memory_mb": memory_change,
            "search_percent": search_improvement
        }
    }

# Example usage
before_config = {
    "chunking_strategy": "lines",
    "batch_segment_threshold": 60
}

after_config = {
    "chunking_strategy": "tokens",
    "token_chunk_size": 800,
    "batch_segment_threshold": 40
}

analyze_configuration_change(
    "/path/to/project",
    before_config,
    after_config,
    "Switching from lines to token chunking"
)
```

## Hardware Impact Analysis

### Memory Constraint Testing

```python
def test_memory_constraints(workspace: str, memory_limits: List[int] = [128, 256, 512, 1024]):
    """Test performance under different memory constraints."""
    
    results = {}
    
    for memory_limit in memory_limits:
        print(f"\nTesting with {memory_limit}MB memory constraint...")
        
        # Configure for memory limit
        if memory_limit <= 256:
            config = {
                "chunking_strategy": "lines",
                "batch_segment_threshold": 15,
                "max_file_size_bytes": 131072
            }
        elif memory_limit <= 512:
            config = {
                "chunking_strategy": "lines",
                "batch_segment_threshold": 30,
                "max_file_size_bytes": 262144
            }
        else:
            config = {
                "chunking_strategy": "tokens",
                "batch_segment_threshold": 60,
                "max_file_size_bytes": 524288
            }
        
        # Test configuration
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        
        result = quick_performance_test(workspace, config)
        results[memory_limit] = result
        
        # Check if memory limit was exceeded
        if result['indexing']['peak_memory_mb'] > memory_limit:
            print(f"⚠️  Memory limit exceeded: {result['indexing']['peak_memory_mb']:.1f}MB > {memory_limit}MB")
        else:
            print(f"✅ Within memory limit: {result['indexing']['peak_memory_mb']:.1f}MB")
    
    return results
```

### CPU Core Scaling

```python
def analyze_cpu_scaling(workspace: str):
    """Analyze how performance scales with CPU cores."""
    
    cpu_count = psutil.cpu_count()
    print(f"System has {cpu_count} CPU cores")
    
    # Test different batch sizes to simulate CPU utilization
    batch_sizes = [20, 40, 60, 80, 100, 120]
    results = {}
    
    for batch_size in batch_sizes:
        if batch_size > cpu_count * 20:  # Skip if too high for CPU count
            continue
            
        config = {
            "chunking_strategy": "lines",
            "batch_segment_threshold": batch_size
        }
        
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        
        result = quick_performance_test(workspace, config)
        results[batch_size] = result
        
        print(f"Batch {batch_size}: {result['indexing']['files_per_second']:.1f} files/sec")
    
    # Find optimal batch size for this CPU
    optimal = max(results.items(), key=lambda x: x[1]['indexing']['files_per_second'])
    recommended_batch = optimal[0]
    
    print(f"\n🎯 Recommended batch size for {cpu_count} cores: {recommended_batch}")
    print(f"   Performance: {optimal[1]['indexing']['files_per_second']:.1f} files/sec")
    
    return results, recommended_batch
```

## Optimization Validation

### A/B Testing Framework

```python
def ab_test_configurations(workspace: str, config_a: Dict, config_b: Dict, runs: int = 5):
    """A/B test two configurations with statistical significance."""
    
    print("Running A/B test...")
    
    results_a = []
    results_b = []
    
    # Run multiple tests for each configuration
    for i in range(runs):
        print(f"Run {i+1}/{runs}")
        
        # Test configuration A
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        result_a = quick_performance_test(workspace, config_a)
        results_a.append(result_a['indexing']['files_per_second'])
        
        # Test configuration B
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        result_b = quick_performance_test(workspace, config_b)
        results_b.append(result_b['indexing']['files_per_second'])
    
    # Calculate statistics
    mean_a = statistics.mean(results_a)
    mean_b = statistics.mean(results_b)
    stdev_a = statistics.stdev(results_a) if len(results_a) > 1 else 0
    stdev_b = statistics.stdev(results_b) if len(results_b) > 1 else 0
    
    improvement = (mean_b / mean_a - 1) * 100
    
    print(f"\n📊 A/B TEST RESULTS")
    print("-" * 30)
    print(f"Configuration A: {mean_a:.1f} ± {stdev_a:.1f} files/sec")
    print(f"Configuration B: {mean_b:.1f} ± {stdev_b:.1f} files/sec")
    print(f"Improvement: {improvement:+.1f}%")
    
    # Simple significance test (t-test would be more rigorous)
    if abs(improvement) > 10 and stdev_a < mean_a * 0.1 and stdev_b < mean_b * 0.1:
        print("✅ Statistically significant difference")
    else:
        print("🟡 Difference may not be significant")
    
    return {
        "config_a_mean": mean_a,
        "config_b_mean": mean_b,
        "improvement_percent": improvement,
        "significant": abs(improvement) > 10
    }
```

### Regression Testing

```python
def regression_test(workspace: str, baseline_config: Dict, test_configs: Dict[str, Dict]):
    """Test for performance regressions against a baseline."""
    
    print("Running regression test against baseline...")
    
    # Establish baseline
    try:
        collections(subcommand="clear-all", yes=True)
    except:
        pass
    baseline_result = quick_performance_test(workspace, baseline_config)
    baseline_speed = baseline_result['indexing']['files_per_second']
    
    print(f"Baseline performance: {baseline_speed:.1f} files/sec")
    
    # Test each configuration
    results = {}
    regressions = []
    
    for name, config in test_configs.items():
        try:
            collections(subcommand="clear-all", yes=True)
        except:
            pass
        
        result = quick_performance_test(workspace, config)
        speed = result['indexing']['files_per_second']
        change = (speed / baseline_speed - 1) * 100
        
        results[name] = {
            "speed": speed,
            "change_percent": change,
            "regression": change < -5  # 5% regression threshold
        }
        
        if change < -5:
            regressions.append(name)
        
        status = "❌" if change < -5 else "✅" if change > 5 else "🟡"
        print(f"{status} {name}: {speed:.1f} files/sec ({change:+.1f}%)")
    
    if regressions:
        print(f"\n⚠️  Performance regressions detected in: {', '.join(regressions)}")
    else:
        print(f"\n✅ No performance regressions detected")
    
    return results, regressions
```

This comprehensive benchmarking guide provides the tools and methodologies needed to systematically evaluate and optimize the performance of your Code Index MCP Server configuration.