# Phase 2 Scalability Features

This document describes the comprehensive scalability improvements implemented in Phase 2 of the code index project, addressing file size limitations and parser infrastructure gaps.

## Overview

Phase 2 scalability features enable the code index tool to handle large files (>256KB) that were previously excluded from indexing, and provide robust parsing strategies for unsupported file types. The implementation includes progressive/chunked indexing, streaming processing, memory optimization, and an extensible parser framework.

## Key Features

### 1. Progressive/Chunked Indexing for Large Files

**Problem**: Large files (>256KB) were completely excluded from indexing due to memory constraints and processing limitations.

**Solution**: Implemented progressive file processing with configurable chunk sizes based on file size and language type.

#### Features:
- **Automatic chunking**: Files are automatically processed in chunks when they exceed configurable thresholds
- **Language-aware chunking**: Different chunk sizes for different file types (Python: 64KB, Java: 256KB, etc.)
- **Progress tracking**: Real-time progress updates during chunked processing
- **Memory optimization**: Garbage collection between chunks to prevent memory leaks

#### Usage:
```python
from src.code_index.file_processing import FileProcessingService

file_service = FileProcessingService(error_handler)
result = file_service.process_file_with_memory_optimization(
    file_path="large_file.py",
    processor=my_processor_function,
    max_memory_usage_mb=100
)
```

### 2. Streaming Processing for Large Files

**Problem**: Loading entire large files into memory caused system crashes and timeouts.

**Solution**: Implemented streaming file processing that processes files in manageable chunks without loading them entirely into memory.

#### Features:
- **Streaming I/O**: Files are read and processed in streaming fashion
- **Configurable chunk sizes**: Adaptive chunk sizes based on file size (64KB-512KB)
- **Error recovery**: Graceful handling of I/O errors during streaming
- **Progress callbacks**: Optional progress tracking during streaming

#### Usage:
```python
# Stream process a large file
results = file_service.stream_process_large_file(
    file_path="huge_log_file.log",
    processor_callback=my_chunk_processor,
    chunk_size=128 * 1024  # 128KB chunks
)
```

### 3. Memory Usage Optimization

**Problem**: Large file processing could consume excessive memory, leading to system instability.

**Solution**: Implemented intelligent memory management with automatic strategy selection based on file size and available memory.

#### Features:
- **Strategy selection**: Automatically chooses between standard, chunked, or streaming processing
- **Memory monitoring**: Real-time memory usage tracking during processing
- **Adaptive thresholds**: Dynamic memory limits based on system capabilities
- **Garbage collection**: Automatic memory cleanup between processing chunks

#### Configuration:
```json
{
  "scalability": {
    "large_file_threshold": 262144,  // 256KB
    "streaming_threshold": 1048576,    // 1MB
    "max_memory_usage_mb": 100,
    "default_chunk_size": 65536        // 64KB
  }
}
```

### 4. Hybrid Parsing Strategies for Unsupported File Types

**Problem**: Plain text and other unsupported file types were not properly analyzed, leading to inconsistent indexing results.

**Solution**: Implemented a comprehensive hybrid parser system with fallback strategies for all file types.

#### Features:
- **Extensible parser framework**: Plugin-based architecture for custom parsers
- **Fallback strategies**: Automatic fallback to regex-based parsing when tree-sitter fails
- **Language-specific patterns**: Optimized regex patterns for different languages
- **Parser registration**: Dynamic parser registration and discovery system

#### Supported Fallback Parsers:
- **Plain text parser**: Line-based chunking for text files
- **Config file parser**: Structured parsing for JSON, YAML, XML, INI files
- **Log file parser**: Pattern-based parsing for log files
- **Markdown parser**: Header and section-based parsing
- **Generic parser**: Universal fallback for unknown file types

#### Usage:
```python
from src.code_index.hybrid_parsers import HybridParserManager

parser_manager = HybridParserManager(config)
result = parser_manager.parse_file(
    file_path="config.json",
    content=file_content,
    language_key="json"
)
```

### 5. Extensible Parser Framework

**Problem**: Adding support for new file types required complex code changes and deep system knowledge.

**Solution**: Implemented a modular parser framework with clear interfaces and registration mechanisms.

#### Features:
- **Plugin architecture**: Easy addition of new parsers without core system changes
- **Parser registration**: Dynamic parser registration via configuration
- **Performance monitoring**: Built-in performance tracking for all parsers
- **Fallback chains**: Hierarchical fallback strategies when primary parsers fail

#### Creating Custom Parsers:
```python
from src.code_index.hybrid_parsers import BaseParser

class MyCustomParser(BaseParser):
    def can_parse(self, file_path: str, content: str) -> bool:
        return file_path.endswith('.myext')
    
    def parse(self, content: str, file_path: str) -> Dict[str, Any]:
        # Custom parsing logic
        return {
            "blocks": extracted_blocks,
            "metadata": {"parser": "custom", "confidence": 0.8}
        }

# Register the parser
parser_manager.register_parser("my_custom", MyCustomParser())
```

### 6. Parser Performance Monitoring

**Problem**: No visibility into parser performance, making optimization difficult.

**Solution**: Comprehensive performance monitoring and statistics collection for all parsing operations.

#### Features:
- **Execution time tracking**: Detailed timing for each parser operation
- **Memory usage monitoring**: Memory consumption tracking during parsing
- **Success/failure rates**: Parser reliability metrics
- **Performance optimization**: Automatic optimization based on performance data

#### Performance Metrics:
```json
{
  "parser_stats": {
    "total_operations": 1500,
    "successful_operations": 1425,
    "failed_operations": 75,
    "average_processing_time_ms": 45.2,
    "memory_usage_mb": 12.5,
    "slowest_parsers": ["cpp", "java"],
    "fastest_parsers": ["python", "javascript"]
  }
}
```

## Configuration

### File Size Limits
```json
{
  "scalability": {
    "large_file_threshold": 262144,      // 256KB - threshold for large file handling
    "streaming_threshold": 1048576,        // 1MB - threshold for streaming processing
    "max_file_size_bytes": 10485760,     // 10MB - maximum supported file size
    "memory_limit_mb": 500                 // Maximum memory usage for processing
  }
}
```

### Chunk Sizes by Language
```json
{
  "language_chunk_sizes": {
    "python": 65536,       // 64KB
    "javascript": 131072,  // 128KB
    "typescript": 131072,  // 128KB
    "java": 262144,        // 256KB
    "cpp": 262144,         // 256KB
    "rust": 131072,        // 128KB
    "go": 131072,          // 128KB
    "text": 32768,         // 32KB
    "markdown": 32768,     // 32KB
    "json": 65536,         // 64KB
    "xml": 131072,         // 128KB
    "yaml": 32768          // 32KB
  }
}
```

### Parser Configuration
```json
{
  "parsers": {
    "enable_fallback_parsers": true,
    "fallback_confidence_threshold": 0.5,
    "max_fallback_blocks": 100,
    "performance_monitoring": true,
    "parser_timeout_seconds": 30
  }
}
```

## Usage Examples

### Basic Large File Processing
```python
from src.code_index.file_processing import FileProcessingService
from src.code_index.errors import ErrorHandler

error_handler = ErrorHandler()
file_service = FileProcessingService(error_handler)

# Process a large file with automatic chunking
result = file_service.load_file_with_chunking(
    file_path="large_source_file.py",
    chunk_size=128 * 1024,  // 128KB chunks
    progress_callback=my_progress_callback
)

for chunk in result:
    if chunk.get("error"):
        print(f"Error in chunk {chunk['chunk_index']}: {chunk['error']}")
    else:
        process_chunk(chunk["chunk_data"])
```

### Advanced Memory-Optimized Processing
```python
def my_processor(content: str, chunk_index: int, is_complete: bool) -> Dict[str, Any]:
    # Custom processing logic
    return {"processed": True, "blocks": extract_blocks(content)}

result = file_service.process_file_with_memory_optimization(
    file_path="huge_file.java",
    processor=my_processor,
    max_memory_usage_mb=200
)

print(f"Processing completed: {result['success']}")
print(f"Memory used: {result['memory_usage_mb']}MB")
print(f"Strategy used: {result['strategy_used']}")
```

### Hybrid Parser Usage
```python
from src.code_index.hybrid_parsers import HybridParserManager

parser_manager = HybridParserManager(config)

# Parse a file with automatic fallback
result = parser_manager.parse_file_with_fallback(
    file_path="config.yaml",
    content=yaml_content,
    language_key="yaml"
)

if result["success"]:
    print(f"Found {len(result['blocks'])} blocks")
    print(f"Parser used: {result['parser_used']}")
    print(f"Confidence: {result['confidence']}")
else:
    print(f"Parsing failed: {result['error']}")
```

## Performance Benefits

### Before Phase 2:
- ❌ Files >256KB completely excluded
- ❌ Memory crashes with large files
- ❌ No support for plain text/config files
- ❌ No performance visibility
- ❌ Manual parser implementation required

### After Phase 2:
- ✅ Files up to 10MB+ supported
- ✅ Memory usage capped and optimized
- ✅ Comprehensive fallback parser support
- ✅ Detailed performance monitoring
- ✅ Easy parser extension framework

## Migration Guide

### For Existing Users:
1. **No breaking changes**: All existing functionality remains unchanged
2. **Automatic benefits**: Large file support is automatically enabled
3. **Optional configuration**: New features can be configured as needed
4. **Backward compatibility**: All existing parsers continue to work

### Enabling New Features:
```json
{
  "scalability": {
    "enable_large_file_support": true,
    "enable_fallback_parsers": true,
    "enable_performance_monitoring": true
  }
}
```

## Testing

Comprehensive test suite with 23+ tests covering:
- Large file chunking and streaming
- Memory optimization strategies
- Fallback parser functionality
- Performance monitoring
- Configuration integration
- End-to-end processing scenarios

Run tests:
```bash
python -m pytest tests/test_scalability_features.py -v
```

## Future Enhancements

### Planned Improvements:
1. **Distributed processing**: Support for processing very large files across multiple nodes
2. **Incremental parsing**: Resume capability for interrupted large file processing
3. **Smart caching**: Intelligent caching of parsed blocks for repeated operations
4. **ML-enhanced parsing**: Machine learning-based parser selection and optimization
5. **Real-time monitoring**: Live performance dashboards and alerting

### Community Contributions:
- Parser plugins for new languages and file types
- Performance optimization strategies
- Memory usage improvements
- New fallback parsing techniques

## Conclusion

Phase 2 scalability features transform the code index tool from a limited file processor into a robust, enterprise-ready system capable of handling files of any size with intelligent parsing strategies. The implementation provides immediate benefits while maintaining backward compatibility and offering extensive customization options for advanced use cases.