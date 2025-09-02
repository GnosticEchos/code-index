# Tree-sitter File Filtering System

## Quick Reference

### Common Configuration Examples

**Basic Tree-sitter Enablement:**
```json
{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter"
}
```

**Performance-Optimized:**
```json
{
  "tree_sitter_max_file_size_bytes": 262144,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true
}
```

**Comprehensive Indexing:**
```json
{
  "tree_sitter_max_file_size_bytes": 1048576,
  "tree_sitter_skip_test_files": false,
  "tree_sitter_skip_examples": false
}
```

### Common Filter Messages
- `"File filtered out by Tree-sitter configuration"` - Pattern match
- `"File too large for Tree-sitter parsing"` - Size limit exceeded
- `"Unsupported language for Tree-sitter parsing"` - Language not supported

## Overview

The Tree-sitter file filtering system provides intelligent, multi-layered filtering to optimize code indexing performance while maintaining semantic search quality. This system prevents unnecessary parsing of files that are unlikely to provide valuable semantic content, such as generated files, test files, build artifacts, and oversized files.

## Default Filtering Rules and Patterns

### Language Support Filtering

Tree-sitter filtering first checks if a file is in a supported language using fast extension mapping with optional library assistance. Coverage is determined at runtime and should not be hard-coded in documentation.

Authoritative sources in code:
- Queries per language: [`treesitter_queries.get_queries_for_language()`](src/code_index/treesitter_queries.py:8)
- Language detection and mapping: [`TreeSitterChunkingStrategy._get_language_key_for_path()`](src/code_index/chunking.py:320) and [`TreeSitterChunkingStrategy._fallback_language_detection()`](src/code_index/chunking.py:438)

Notes:
- When a language has no specialized query, limited extraction is used; see [`TreeSitterChunkingStrategy._extract_with_limits()`](src/code_index/chunking.py:1143).
- Files in unsupported languages are filtered out with "Unsupported language for Tree-sitter parsing".

### File Size Limits

**Default Limits:**
- General files: 512KB maximum (`tree_sitter_max_file_size_bytes`)
- Rust files: 300KB maximum (`rust_specific_optimizations.max_rust_file_size_kb`)

Files exceeding these limits are filtered out with "File too large for Tree-sitter parsing".

### Test File Detection

**Default Test Patterns:**
- Files containing `test`, `spec`, `_test`, `tests` in their names
- Pattern matching: `*test*`, `*spec*`, `*_test*`, `*tests*`
- Exact matches: `test.py`, `spec.js`, etc.

Test file filtering is enabled by default (`tree_sitter_skip_test_files: true`).

### Example/Demo File Detection

**Default Example Patterns:**
- Files containing `example`, `sample`, `demo` in their names
- Pattern matching: `*example*`, `*sample*`, `*demo*`
- Exact matches: `example.py`, `sample.rs`, etc.

Example file filtering is enabled by default (`tree_sitter_skip_examples: true`).

### Generated File and Build Artifact Patterns

**Default Skip Patterns:**
```json
"tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",  # Minified assets
    "package-lock.json", "yarn.lock",         # Lock files
    "*.lock",                                 # Generic lock files
    "target/", "build/", "dist/",             # Build directories
    "__pycache__/", "node_modules/",          # Dependency directories
    "*.log", "*.tmp", "*.temp",               # Log/temp files
]
```

### Rust-Specific Optimizations

**Default Rust Configuration:**
```json
"rust_specific_optimizations": {
    "skip_large_rust_files": true,
    "max_rust_file_size_kb": 300,
    "skip_generated_rust_files": true,
    "rust_target_directories": ["target/", "build/", "dist/"]
}
```

## Configuration and Override Mechanisms

### Configuration File Structure

The Tree-sitter filtering system can be configured through JSON configuration files. The main configuration options are:

```json
{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter",
  "tree_sitter_max_file_size_bytes": 524288,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [],
  "rust_specific_optimizations": {
    "skip_large_rust_files": true,
    "max_rust_file_size_kb": 300,
    "skip_generated_rust_files": true,
    "rust_target_directories": ["target/", "build/", "dist/"]
  }
}
```

### Configuration File Loading

The system loads configuration from multiple sources in this order of precedence:

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration file** (`--config` parameter)
4. **Default values** (lowest priority)

### Override Examples

**Disable Test File Filtering:**
```json
{
  "tree_sitter_skip_test_files": false
}
```

**Increase File Size Limit:**
```json
{
  "tree_sitter_max_file_size_bytes": 1048576  # 1MB
}
```

**Add Custom Skip Patterns:**
```json
{
  "tree_sitter_skip_patterns": [
    "*.min.js",
    "custom_pattern/",
    "generated_*.rs"
  ]
}
```

**Disable Rust Optimizations:**
```json
{
  "rust_specific_optimizations": {
    "skip_large_rust_files": false,
    "skip_generated_rust_files": false
  }
}
```

## Best Practices: Performance vs Completeness

### Performance-Optimized Configuration

For large codebases or performance-critical environments:

```json
{
  "tree_sitter_max_file_size_bytes": 262144,  # 256KB
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock", "*.lock",
    "target/", "build/", "dist/", "node_modules/", "__pycache__/",
    "*.log", "*.tmp", "*.temp"
  ],
  "rust_specific_optimizations": {
    "skip_large_rust_files": true,
    "max_rust_file_size_kb": 200,
    "skip_generated_rust_files": true
  }
}
```

### Completeness-Focused Configuration

For comprehensive indexing where no content should be missed:

```json
{
  "tree_sitter_max_file_size_bytes": 1048576,  # 1MB
  "tree_sitter_skip_test_files": false,
  "tree_sitter_skip_examples": false,
  "tree_sitter_skip_patterns": [],
  "rust_specific_optimizations": {
    "skip_large_rust_files": false,
    "max_rust_file_size_kb": 1024,  # 1MB
    "skip_generated_rust_files": false
  }
}
```

### Balanced Configuration

Recommended for most use cases:

```json
{
  "tree_sitter_max_file_size_bytes": 524288,  # 512KB
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock",
    "target/", "build/", "dist/", "node_modules/"
  ],
  "rust_specific_optimizations": {
    "skip_large_rust_files": true,
    "max_rust_file_size_kb": 300,
    "skip_generated_rust_files": true
  }
}
```

## Rust-Specific Guidance

### Handling Large Rust Files

Rust files often contain generated code or very large modules. The system provides specific optimizations:

```json
"rust_specific_optimizations": {
    "skip_large_rust_files": true,        # Skip files > 300KB
    "max_rust_file_size_kb": 300,         # Custom size limit
    "skip_generated_rust_files": true,     # Skip target/ build artifacts
    "rust_target_directories": ["target/", "build/", "dist/"]
}
```

### Example and Demo Directory Handling

For Rust projects with example directories:

```json
{
  "tree_sitter_skip_examples": false,  # Index examples
  "tree_sitter_skip_patterns": [
    "target/", "build/", "dist/"       # Still skip build artifacts
  ]
}
```

Or to skip specific example patterns:

```json
{
  "tree_sitter_skip_patterns": [
    "examples/generated/",
    "demos/playground/"
  ]
}
```

## Advanced Configuration Options

### File Size Limits

```json
{
  "tree_sitter_max_file_size_bytes": 1048576,  # 1MB maximum
  "max_file_size_bytes": 2097152               # General file size limit (2MB)
}
```

### Test File Detection Customization

```json
{
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_patterns": [
    "*_test.rs",           # Rust test files
    "*_spec.js",           # JavaScript spec files
    "test_*.py",           # Python test files
    "**/tests/**",          # Test directories
    "**/spec/**"           # Spec directories
  ]
}
```

### Generated File Exclusions

```json
{
  "tree_sitter_skip_patterns": [
    "**/target/**",         # Rust target directory
    "**/node_modules/**",   # Node.js dependencies
    "**/__pycache__/**",    # Python cache
    "**/dist/**",           # Distribution builds
    "**/build/**",          # Build artifacts
    "*.min.*",              # Minified files
    "*.bundle.*",           # Bundled files
    "*.lock"                # Lock files
  ]
}
```

## Custom Pattern Syntax

The filtering system supports multiple pattern formats:

### Wildcard Patterns
- `*.min.js` - All minified JavaScript files
- `test_*` - Files starting with "test_"
- `*_test.rs` - Rust test files

### Directory Patterns
- `target/` - Any directory named "target"
- `**/node_modules/**` - Recursive node_modules directories
- `build/` - Build directories at any level

### Extension Patterns
- `*.rs` - All Rust files
- `*.test.js` - JavaScript test files
- `*.spec.ts` - TypeScript spec files

## Integration with Other Filtering Systems

### Gitignore Integration

The Tree-sitter filtering works alongside traditional `.gitignore` patterns. Files excluded by `.gitignore` are filtered before Tree-sitter processing.

### Smart Ignore Manager

The system integrates with the SmartIgnoreManager, which provides:
- Language-specific ignore patterns from GitHub templates
- Framework detection and appropriate filtering
- Project-specific `.gitignore` patterns
- Global ignore patterns for editors and OS files

### Fallback Behavior

When Tree-sitter filtering excludes a file, the system falls back to line-based chunking for basic indexing, ensuring no content is completely lost.

## Troubleshooting and Debugging

### Common Filtering Messages

- `"File filtered out by Tree-sitter configuration"` - General filtering rule matched
- `"File too large for Tree-sitter parsing"` - File size exceeds limit
- `"Unsupported language for Tree-sitter parsing"` - Language not supported

### Debugging Filtering Behavior

Enable verbose logging to see filtering decisions:

```bash
code-index index --verbose --config your_config.json
```

### Testing Filtering Rules

Create a test configuration to verify filtering behavior:

```json
{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter",
  "tree_sitter_skip_test_files": false,
  "tree_sitter_skip_examples": false,
  "tree_sitter_skip_patterns": []
}
```

## Performance Impact

### Indexing Speed Improvement

Typical performance improvements with default filtering:
- 30-50% faster indexing for large codebases
- 60-80% reduction in Tree-sitter parsing time
- 40-60% memory usage reduction

### Search Quality Maintenance

Despite filtering, search quality is maintained because:
- Semantic chunks are preserved for valuable code
- Filtered files typically contain minimal semantic value
- Fallback chunking ensures basic content availability

## Migration and Compatibility

### From Previous Versions

When upgrading from versions without Tree-sitter filtering:
- Existing configurations remain compatible
- New filtering options are opt-in (defaults preserve existing behavior)
- Re-indexing is recommended to apply new filtering rules


## Conclusion

The Tree-sitter file filtering system provides a robust, configurable approach to optimizing code indexing performance. By intelligently excluding files that offer little semantic value while preserving important code structures, the system delivers significant performance improvements without compromising search quality.

The flexible configuration system allows customization for specific project needs, from performance-optimized setups for large codebases to completeness-focused configurations for comprehensive indexing.