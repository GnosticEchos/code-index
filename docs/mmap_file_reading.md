# Memory-Mapped File Reading (mmap) Implementation

## Overview

The code index tool now supports memory-mapped file reading (`mmap`) as an alternative to traditional file reading (`read()`). This feature is designed to improve performance for large file processing while maintaining backward compatibility.

## Performance Characteristics

### mmap vs Traditional Reading

- **Traditional Reading (`read()`)**:
  - Reads entire file content into memory at once
  - Simple and reliable
  - Good for small to medium files
  - Higher memory usage for large files

- **Memory-Mapped Reading (`mmap`)**:
  - Maps file directly to virtual memory
  - Lower memory overhead for large files
  - Better performance for large files (>64KB)
  - Potential system call overhead for small files

## Configuration Options

The mmap feature is configurable through the following settings in [`config.py`](src/code_index/config.py):

```python
# Memory-mapped file reading configuration
self.use_mmap_file_reading: bool = False  # Enable/disable mmap
self.mmap_min_file_size_bytes: int = 64 * 1024  # 64KB minimum for mmap
```

### Environment Variables

You can also configure mmap via environment variables:

```bash
# Enable mmap file reading
export CODE_INDEX_USE_MMAP=true

# Set minimum file size for mmap (in bytes)
export CODE_INDEX_MMAP_MIN_SIZE=65536
```

## Usage

### Enabling mmap Globally

```python
from src.code_index.config import Config

config = Config()
config.use_mmap_file_reading = True
config.mmap_min_file_size_bytes = 128 * 1024  # 128KB minimum

# Use the configured parser
parser = CodeParser(config, chunking_strategy)
```

### Per-File Decision Making

The implementation automatically chooses the optimal method based on file size:

1. Files smaller than `mmap_min_file_size_bytes`: Use traditional reading
2. Files larger than `mmap_min_file_size_bytes`: Use mmap reading
3. If mmap fails: Fall back to traditional reading

## Performance Benchmarking

Use the provided benchmarking script to compare performance:

```bash
# Run comprehensive benchmarks
python benchmark_file_reading.py --sizes 1 10 100 500 1000 --iterations 20

# Test specific file sizes
python benchmark_file_reading.py --sizes 64 128 256 512 --output large_file_results.txt
```

### Expected Results

- **Small files (<64KB)**: Traditional reading is typically faster
- **Medium files (64KB-1MB)**: Performance varies by system
- **Large files (>1MB)**: mmap generally provides better performance

## Error Handling

The implementation includes robust error handling:

1. **File open errors**: Gracefully fall back to traditional reading
2. **mmap failures**: Automatic fallback with detailed warnings
3. **Unicode decode errors**: Handle encoding issues appropriately
4. **Empty files**: Return empty content without errors

## Memory Management

The mmap implementation ensures proper memory management:

- **Automatic cleanup**: mmap objects are properly closed using context managers
- **Resource limits**: Large files are handled efficiently
- **Fallback mechanism**: If mmap fails, traditional reading is used
- **No memory leaks**: All file handles are properly closed

## Best Practices

### When to Use mmap

- Processing large code files (>100KB)
- Indexing projects with many large files
- Memory-constrained environments
- Batch processing operations

### When to Use Traditional Reading

- Small files (<64KB)
- Systems with limited mmap support
- Debugging or development environments
- When consistent behavior is required

## Testing

Test the implementation with:

```bash
# Run basic functionality tests
python test_mmap_implementation.py

# Verify error handling
python test_mmap_implementation.py
```

## Troubleshooting

### Common Issues

1. **mmap not available**: Some systems may have limited mmap support
2. **Permission errors**: Ensure read access to target files
3. **Memory mapping failures**: Large files may exceed system limits

### Debug Mode

Enable debug output to see mmap decisions:

```python
import os
os.environ['CODE_INDEX_DEBUG_MMAP'] = 'true'
```

## Performance Tips

1. **Adjust minimum size**: Set `mmap_min_file_size_bytes` based on your typical file sizes
2. **Monitor memory usage**: Use system tools to observe memory behavior
3. **Test both methods**: Benchmark with your specific workload
4. **Consider file system**: mmap performance varies by filesystem type

## Compatibility

- **Python 3.6+**: Full support
- **Windows**: Limited mmap support (fallback to traditional)
- **Unix/Linux**: Full mmap support
- **macOS**: Full mmap support

## Future Enhancements

Potential improvements:
- Adaptive threshold based on system capabilities
- Per-file-type optimization
- Streaming processing for very large files
- Memory usage monitoring and throttling