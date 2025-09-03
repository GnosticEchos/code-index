# MCP Server Performance Optimization Guide

This guide provides comprehensive strategies for optimizing the performance of the Code Index MCP Server across different use cases, repository sizes, and hardware configurations.

## Table of Contents

- [Performance Overview](#performance-overview)
- [Indexing Performance](#indexing-performance)
- [Search Performance](#search-performance)
- [Memory Optimization](#memory-optimization)
- [Configuration Strategies](#configuration-strategies)
- [Hardware Recommendations](#hardware-recommendations)
- [Benchmarking and Monitoring](#benchmarking-and-monitoring)

## Performance Overview

### Key Performance Factors

1. **Repository Size**: Number of files and total size
2. **Chunking Strategy**: Lines vs tokens vs Tree-sitter
3. **Embedding Model**: Model size and inference speed
4. **Hardware**: CPU, memory, and storage performance
5. **Network**: Latency to Ollama and Qdrant services
6. **Configuration**: Batch sizes, timeouts, and limits

### Performance Metrics

- **Indexing Speed**: Files per second, total indexing time
- **Search Latency**: Time from query to results
- **Memory Usage**: Peak memory during operations
- **Storage Efficiency**: Vector database size vs source code size
- **Accuracy**: Search result relevance and recall

## Indexing Performance

### Chunking Strategy Optimization

#### 1. Lines Chunking (Fastest)

**Best for**: Large repositories, initial indexing, CI/CD pipelines

```json
{
  "chunking_strategy": "lines",
  "use_tree_sitter": false,
  "max_file_size_bytes": 1048576,
  "batch_segment_threshold": 100
}
```

**Performance characteristics**:
- **Speed**: ~500-1000 files/minute
- **Memory**: Low, ~100-200MB peak
- **Accuracy**: Good for keyword-based searches

#### 2. Token Chunking (Balanced)

**Best for**: Medium repositories, balanced performance/accuracy

```json
{
  "chunking_strategy": "tokens",
  "token_chunk_size": 800,
  "token_chunk_overlap": 160,
  "batch_segment_threshold": 60
}
```

**Performance characteristics**:
- **Speed**: ~200-400 files/minute
- **Memory**: Medium, ~200-400MB peak
- **Accuracy**: Better semantic boundaries

#### 3. Tree-sitter Chunking (Most Accurate)

**Best for**: Critical codebases, semantic accuracy priority

```json
{
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_file_size_bytes": 262144,
  "tree_sitter_max_blocks_per_file": 50,
  "tree_sitter_skip_test_files": true,
  "batch_segment_threshold": 30
}
```

**Performance characteristics**:
- **Speed**: ~50-150 files/minute
- **Memory**: High, ~400-800MB peak
- **Accuracy**: Best semantic understanding

### Batch Size Optimization

#### Small Repositories (<1000 files)

```json
{
  "batch_segment_threshold": 100,
  "embed_timeout_seconds": 60
}
```

#### Medium Repositories (1000-10000 files)

```json
{
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 120
}
```

#### Large Repositories (>10000 files)

```json
{
  "batch_segment_threshold": 30,
  "embed_timeout_seconds": 300,
  "max_file_size_bytes": 524288
}
```

### File Filtering Optimization

#### Aggressive Filtering (Speed Priority)

```json
{
  "extensions": [".py", ".js", ".ts", ".rs"],
  "max_file_size_bytes": 262144,
  "auto_extensions": false,
  "exclude_files_path": "aggressive_ignore.txt"
}
```

Create `aggressive_ignore.txt`:
```
node_modules/
.git/
dist/
build/
*.min.js
*.bundle.js
*.test.js
*.spec.js
```

#### Comprehensive Filtering (Accuracy Priority)

```json
{
  "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".dart", ".lua", ".r", ".sql", ".md", ".json", ".yaml", ".yml"],
  "max_file_size_bytes": 1048576,
  "auto_extensions": true
}
```

### Parallel Processing Strategies

#### Workspace Batching

For very large codebases, split into logical chunks:

```python
# Create workspace list for parallel processing
workspaces = [
    "/project/src/frontend",
    "/project/src/backend", 
    "/project/src/shared",
    "/project/tests"
]

# Process each workspace separately
for workspace in workspaces:
    index(workspace=workspace, embed_timeout=300)
```

#### Multi-stage Indexing

```python
# Stage 1: Core source files only
index(
    workspace="/project",
    extensions=[".py", ".js", ".ts"],
    chunking_strategy="treesitter"
)

# Stage 2: Documentation and configs
index(
    workspace="/project", 
    extensions=[".md", ".json", ".yaml"],
    chunking_strategy="lines"
)
```

## Search Performance

### Query Optimization

#### Efficient Query Patterns

```python
# Good: Specific, focused queries
search(query="authentication middleware express")
search(query="database connection pool")
search(query="error handling try catch")

# Avoid: Very broad or vague queries
search(query="code")  # Too broad
search(query="function")  # Too generic
```

#### Result Set Optimization

```python
# For interactive use
search(
    query="your query",
    min_score=0.6,      # Higher threshold
    max_results=20      # Reasonable limit
)

# For comprehensive analysis
search(
    query="your query", 
    min_score=0.4,      # Lower threshold
    max_results=100     # More results
)
```

### Ranking Optimization

#### File Type Weighting

```json
{
  "search_file_type_weights": {
    ".ts": 1.5,         // Boost TypeScript
    ".js": 1.3,         // Boost JavaScript  
    ".py": 1.4,         // Boost Python
    ".rs": 1.2,         // Boost Rust
    ".md": 0.8,         // Reduce documentation
    ".json": 0.6,       // Reduce config files
    ".test.js": 0.3,    // Minimize test files
    ".spec.ts": 0.3     // Minimize spec files
  }
}
```

#### Path-based Boosting

```json
{
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.4},
    {"pattern": "lib/", "boost": 1.3},
    {"pattern": "core/", "boost": 1.5},
    {"pattern": "utils/", "boost": 1.2},
    {"pattern": "test/", "boost": 0.4},
    {"pattern": "tests/", "boost": 0.4},
    {"pattern": "docs/", "boost": 0.7},
    {"pattern": "examples/", "boost": 0.6}
  ]
}
```

#### Language-specific Boosting

```json
{
  "search_language_boosts": {
    "typescript": 1.3,
    "javascript": 1.2,
    "python": 1.4,
    "rust": 1.2,
    "go": 1.1,
    "markdown": 0.8
  }
}
```

## Memory Optimization

### Memory-Efficient Configuration

#### Low Memory Profile (<4GB RAM)

```json
{
  "chunking_strategy": "lines",
  "batch_segment_threshold": 20,
  "max_file_size_bytes": 262144,
  "tree_sitter_max_file_size_bytes": 131072,
  "search_max_results": 50
}
```

#### Medium Memory Profile (4-8GB RAM)

```json
{
  "chunking_strategy": "tokens", 
  "batch_segment_threshold": 40,
  "max_file_size_bytes": 524288,
  "tree_sitter_max_file_size_bytes": 262144,
  "search_max_results": 100
}
```

#### High Memory Profile (>8GB RAM)

```json
{
  "chunking_strategy": "treesitter",
  "batch_segment_threshold": 80,
  "max_file_size_bytes": 1048576,
  "tree_sitter_max_file_size_bytes": 524288,
  "search_max_results": 200
}
```

### Memory Monitoring

```python
import psutil
import os

def monitor_memory():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")

# Monitor during indexing
monitor_memory()
index(workspace="/path/to/project")
monitor_memory()
```

## Configuration Strategies

### Language-Specific Optimizations

#### Python Projects

```json
{
  "extensions": [".py", ".pyx", ".pyi"],
  "chunking_strategy": "treesitter",
  "tree_sitter_skip_test_files": true,
  "search_file_type_weights": {
    ".py": 1.5,
    ".pyi": 1.2,
    ".test.py": 0.3
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.4},
    {"pattern": "lib/", "boost": 1.3},
    {"pattern": "tests/", "boost": 0.4}
  ]
}
```

#### JavaScript/TypeScript Projects

```json
{
  "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"],
  "chunking_strategy": "treesitter", 
  "tree_sitter_skip_test_files": true,
  "search_file_type_weights": {
    ".ts": 1.6,
    ".tsx": 1.5,
    ".js": 1.3,
    ".jsx": 1.4,
    ".test.js": 0.2,
    ".spec.ts": 0.2
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.5},
    {"pattern": "components/", "boost": 1.4},
    {"pattern": "utils/", "boost": 1.3},
    {"pattern": "node_modules/", "boost": 0.1}
  ]
}
```

#### Rust Projects

```json
{
  "extensions": [".rs", ".toml"],
  "chunking_strategy": "treesitter",
  "tree_sitter_max_blocks_per_file": 100,
  "search_file_type_weights": {
    ".rs": 1.5,
    "Cargo.toml": 1.2,
    ".toml": 0.8
  },
  "search_path_boosts": [
    {"pattern": "src/", "boost": 1.5},
    {"pattern": "lib/", "boost": 1.4},
    {"pattern": "tests/", "boost": 0.5},
    {"pattern": "target/", "boost": 0.1}
  ]
}
```

### Use Case Optimizations

#### CI/CD Pipeline (Speed Priority)

```json
{
  "chunking_strategy": "lines",
  "use_tree_sitter": false,
  "batch_segment_threshold": 100,
  "max_file_size_bytes": 524288,
  "embed_timeout_seconds": 30,
  "extensions": [".py", ".js", ".ts", ".rs", ".go"],
  "auto_extensions": false
}
```

#### Development Environment (Balanced)

```json
{
  "chunking_strategy": "tokens",
  "token_chunk_size": 800,
  "token_chunk_overlap": 160,
  "batch_segment_threshold": 60,
  "embed_timeout_seconds": 120,
  "tree_sitter_max_file_size_bytes": 262144
}
```

#### Research/Analysis (Accuracy Priority)

```json
{
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  "tree_sitter_max_blocks_per_file": 200,
  "batch_segment_threshold": 30,
  "embed_timeout_seconds": 300,
  "search_min_score": 0.3,
  "search_max_results": 200
}
```

## Hardware Recommendations

### Minimum Requirements

- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 4GB
- **Storage**: 10GB free space
- **Network**: 100 Mbps for remote services

**Expected Performance**:
- Small repos (<1000 files): 5-10 minutes
- Medium repos (1000-5000 files): 15-30 minutes

### Recommended Configuration

- **CPU**: 4+ cores, 3.0+ GHz
- **RAM**: 8GB+
- **Storage**: SSD with 50GB+ free space
- **Network**: 1 Gbps for optimal service communication

**Expected Performance**:
- Small repos: 2-5 minutes
- Medium repos: 5-15 minutes
- Large repos (5000-20000 files): 20-60 minutes

### High-Performance Configuration

- **CPU**: 8+ cores, 3.5+ GHz
- **RAM**: 16GB+
- **Storage**: NVMe SSD with 100GB+ free space
- **Network**: Local services (Ollama/Qdrant on same machine)

**Expected Performance**:
- Small repos: <2 minutes
- Medium repos: 2-8 minutes
- Large repos: 10-30 minutes
- Very large repos (>20000 files): 30-120 minutes

### Service Optimization

#### Ollama Optimization

```bash
# Use GPU acceleration if available
OLLAMA_GPU=1 ollama serve

# Increase concurrent requests
OLLAMA_MAX_LOADED_MODELS=2 ollama serve

# Optimize for embedding models
OLLAMA_KEEP_ALIVE=5m ollama serve
```

#### Qdrant Optimization

```bash
# High-performance Qdrant configuration
docker run -p 6333:6333 -p 6334:6334 \
  -e QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=64 \
  -e QDRANT__SERVICE__MAX_WORKERS=4 \
  -e QDRANT__STORAGE__PERFORMANCE__MAX_SEARCH_THREADS=4 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

## Benchmarking and Monitoring

### Performance Benchmarking

#### Indexing Benchmark Script

```python
import time
import psutil
import os

def benchmark_indexing(workspace, config_overrides=None):
    """Benchmark indexing performance."""
    start_time = time.time()
    start_memory = psutil.Process(os.getpid()).memory_info().rss
    
    # Run indexing
    result = index(workspace=workspace, **(config_overrides or {}))
    
    end_time = time.time()
    end_memory = psutil.Process(os.getpid()).memory_info().rss
    
    duration = end_time - start_time
    memory_used = (end_memory - start_memory) / 1024 / 1024  # MB
    
    print(f"Indexing Results:")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Files processed: {result.get('files_processed', 0)}")
    print(f"  Files per second: {result.get('files_processed', 0) / duration:.1f}")
    print(f"  Memory used: {memory_used:.1f} MB")
    print(f"  Peak memory: {end_memory / 1024 / 1024:.1f} MB")
    
    return {
        "duration": duration,
        "files_processed": result.get('files_processed', 0),
        "files_per_second": result.get('files_processed', 0) / duration,
        "memory_used_mb": memory_used,
        "peak_memory_mb": end_memory / 1024 / 1024
    }

# Benchmark different strategies
strategies = ["lines", "tokens", "treesitter"]
for strategy in strategies:
    print(f"\nBenchmarking {strategy} chunking:")
    benchmark_indexing("/path/to/test/project", {
        "chunking_strategy": strategy
    })
```

#### Search Benchmark Script

```python
def benchmark_search(queries, workspace="/path/to/project"):
    """Benchmark search performance."""
    results = []
    
    for query in queries:
        start_time = time.time()
        search_results = search(query=query, workspace=workspace)
        end_time = time.time()
        
        duration = end_time - start_time
        result_count = len(search_results)
        
        results.append({
            "query": query,
            "duration": duration,
            "result_count": result_count,
            "results_per_second": result_count / duration if duration > 0 else 0
        })
        
        print(f"Query: '{query}'")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Results: {result_count}")
    
    return results

# Test with common query types
test_queries = [
    "authentication middleware",
    "database connection",
    "error handling",
    "user interface component",
    "API endpoint handler"
]

benchmark_search(test_queries)
```

### Monitoring and Alerting

#### Performance Monitoring

```python
import logging
import time
from functools import wraps

def performance_monitor(func):
    """Decorator to monitor function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            logging.error(f"Function {func.__name__} failed: {e}")
        
        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss
        
        duration = end_time - start_time
        memory_delta = (end_memory - start_memory) / 1024 / 1024
        
        logging.info(f"Performance: {func.__name__}")
        logging.info(f"  Duration: {duration:.3f}s")
        logging.info(f"  Memory delta: {memory_delta:.1f}MB")
        logging.info(f"  Success: {success}")
        
        return result
    return wrapper

# Use with MCP tools
@performance_monitor
def monitored_index(*args, **kwargs):
    return index(*args, **kwargs)

@performance_monitor  
def monitored_search(*args, **kwargs):
    return search(*args, **kwargs)
```

### Performance Tuning Checklist

#### Before Indexing
- [ ] Services running (Ollama, Qdrant)
- [ ] Sufficient disk space (3x source code size)
- [ ] Appropriate chunking strategy selected
- [ ] File filters configured
- [ ] Batch size optimized for hardware
- [ ] Timeout values set appropriately

#### During Indexing
- [ ] Monitor memory usage
- [ ] Watch for timeout errors
- [ ] Check embedding service performance
- [ ] Monitor disk I/O

#### After Indexing
- [ ] Verify collection creation
- [ ] Test search performance
- [ ] Check result quality
- [ ] Review timeout logs
- [ ] Measure total indexing time

#### Search Optimization
- [ ] Test query patterns
- [ ] Adjust score thresholds
- [ ] Optimize result limits
- [ ] Configure file type weights
- [ ] Set up path boosts

This comprehensive performance optimization guide should help you achieve optimal performance for your specific use case and hardware configuration.