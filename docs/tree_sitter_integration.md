# Tree-sitter Semantic Code Chunking Integration Guide

## Overview

The Tree-sitter integration provides **semantic code chunking** that extracts meaningful code blocks (functions, classes, methods) instead of arbitrary line segments. This dramatically improves search quality by ensuring code blocks maintain semantic coherence.

## Key Benefits

### Improved Search Quality
- **Semantic Blocks**: Functions, classes, methods maintain complete context
- **Better Relevance**: Search results match complete logical units
- **Reduced Noise**: Fewer fragmented code snippets in results

### Language Awareness
- **AST-based Parsing**: Uses Tree-sitter grammars for accurate parsing
- **40+ Languages Supported**: Python, JavaScript, TypeScript, Rust, Go, Java, Shell/Bash, Dart, Scala, Perl, Haskell, Elixir, Clojure, Erlang, OCaml, F#, VB/VB.NET, R, MATLAB, Julia, Groovy, Dockerfile, Makefile, CMake, Protocol Buffers, GraphQL, and more
- **Language-Specific Queries**: Customized extraction for each language

### Performance Optimization
- **Smart File Filtering**: Skip test files, generated code, build artifacts
- **Size Limits**: Prevent parsing of oversized files that slow down indexing
- **Caching**: Parser caching for repeated language usage
- **Efficient Queries**: Tree-sitter queries instead of naive AST traversal

## Supported languages and queries

Coverage is determined at runtime and should not be hard-coded in documentation. The authoritative sources are:
- Query definitions: [treesitter_queries.get_queries_for_language()](src/code_index/treesitter_queries.py:8)
- Language detection and mapping: [chunking.TreeSitterChunkingStrategy._get_language_key_for_path()](src/code_index/chunking.py:320) and [chunking.TreeSitterChunkingStrategy._fallback_language_detection()](src/code_index/chunking.py:438)

Guidance:
- Do not enumerate every supported language here. Instead, document a few common examples and point to the code as the source of truth.
- When a language has no specialized query, the system falls back to limited extraction; see [chunking.TreeSitterChunkingStrategy._extract_with_limits()](src/code_index/chunking.py:1143).

Examples (non-exhaustive):
- Python (.py): functions, classes via Tree-sitter queries
- TypeScript/TSX (.ts, .tsx): functions, classes, interfaces; JSX elements captured in TSX
- Rust (.rs): functions, impls, structs/enums with conservative limits to avoid timeouts
- Markdown/HTML/CSS: headings/elements/rules for better doc search

Refer to the code links above for the complete, current set.

## Configuration

### Basic Configuration
```json
{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter"
}
```

### Advanced Configuration Options

| Option | Description | Default | Type |
|--------|-------------|---------|------|
| `use_tree_sitter` | Enable Tree-sitter semantic parsing | `false` | `boolean` |
| `chunking_strategy` | Set to `"treesitter"` for semantic chunking | `"lines"` | `string` |
| `tree_sitter_max_file_size_bytes` | Max file size for Tree-sitter parsing | `524288` (512KB) | `integer` |
| `tree_sitter_max_blocks_per_file` | Max semantic blocks per file | `100` | `integer` |
| `tree_sitter_max_functions_per_file` | Max functions per file | `50` | `integer` |
| `tree_sitter_max_classes_per_file` | Max classes per file | `20` | `integer` |
| `tree_sitter_max_impl_blocks_per_file` | Max impl blocks per file | `30` | `integer` |
| `tree_sitter_skip_test_files` | Skip test/spec files | `true` | `boolean` |
| `tree_sitter_skip_examples` | Skip example/sample files | `true` | `boolean` |
| `tree_sitter_skip_patterns` | File patterns to skip | `[]` | `array` |

### Example Configuration
```json
{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter",
  "tree_sitter_max_file_size_bytes": 1048576,
  "tree_sitter_max_blocks_per_file": 50,
  "tree_sitter_max_functions_per_file": 30,
  "tree_sitter_max_classes_per_file": 15,
  "tree_sitter_skip_test_files": true,
  "tree_sitter_skip_examples": true,
  "tree_sitter_skip_patterns": [
    "*.min.js", "*.bundle.js", "*.min.css",
    "package-lock.json", "yarn.lock",
    "target/", "build/", "dist/", "node_modules/"
  ]
}
```

## Usage Examples

### Command Line Usage
```bash
# Enable Tree-sitter with a configuration file
echo '{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter"
}' > treesitter_config.json

# Index with semantic chunking
code-index index --config treesitter_config.json

# Search with semantic chunks
code-index search "authentication function"
```

### Programmatic Usage
```python
from code_index.config import Config
from code_index.parser import CodeParser

# Configure Tree-sitter
config = Config()
config.use_tree_sitter = True
config.chunking_strategy = "treesitter"

# Parse files with semantic chunks
parser = CodeParser(config)
blocks = parser.parse_file("src/main.py")

# Each block is a semantic unit
for block in blocks:
    print(f"{block.type}: {block.identifier}")
    print(f"Lines {block.start_line}-{block.end_line}")
    print(block.content[:100] + "...")
```

## Performance Considerations

### File Size Limits
Large files (>512KB) are automatically filtered out because:
- **Memory Usage**: Tree-sitter loads entire file into memory and builds a full AST
- **Parsing Time**: Larger files take exponentially more time to parse
- **Semantic Value**: Most valuable code is in reasonably sized files

### Smart Filtering
Files are filtered before parsing to avoid unnecessary work:
```python
# Skipped patterns (configurable)
skip_patterns = [
    "*.min.js", "*.bundle.js",     # Minified JavaScript
    "package-lock.json", "yarn.lock",  # Lock files
    "target/", "build/", "dist/",     # Build directories
    "*_test*", "*spec*",              # Test files
    "node_modules/", "__pycache__/"  # Dependency directories
]
```

### Caching Strategy
- **Parser Caching**: One parser per language, reused across files
- **Query Caching**: Language-specific queries cached
- **Result Caching**: Future enhancement for repeated parsing


## Troubleshooting

### Common Issues

#### Tree-sitter Parser Not Loading
```
Warning: Failed to load Tree-sitter parser for python
```
**Solution**: Ensure `tree-sitter-language-pack` is installed:
```bash
pip install tree-sitter-language-pack
```

#### File Too Large
```
File too large for Tree-sitter parsing
```
**Solution**: Increase `tree_sitter_max_file_size_bytes` in config or filter large files.

#### No Semantic Blocks Found
```
Warning: Tree-sitter parsing failed, falling back to line-based splitting
```
**Solution**: Check file content and language support.

### Debugging Tips

#### Enable Verbose Logging
```json
{
  "use_tree_sitter": true,
  "chunking_strategy": "treesitter",
  "debug_logging": true
}
```

#### Test Specific Files
```bash
# Test Tree-sitter on a single file
code-index index --workspace /path/to/single/file.py --config debug_config.json
```

#### Validate Language Detection
```python
from code_index.parser import CodeParser
from code_index.config import Config

config = Config()
parser = CodeParser(config)

# Test language detection
language = parser._get_language_key_for_path("test.py")
print(f"Detected language: {language}")  # Should print "python"
```

## Future Enhancements

### Planned Features
1. **Custom Queries**: User-defined Tree-sitter queries per language
2. **Nested Block Extraction**: Extract nested functions/methods
3. **Cross-reference Tracking**: Track function calls and dependencies
4. **Incremental Parsing**: Only re-parse changed files
5. **Advanced Caching**: Persistent parser caching across sessions

### Performance Improvements
1. **Parallel Parsing**: Concurrent Tree-sitter parsing for multiple files
2. **Memory Optimization**: Streaming parsing for large files
3. **Query Optimization**: Compiled queries for faster execution
4. **Lazy Loading**: Load parsers only when needed

## Technical Details

### Architecture Overview
```
File Input → Language Detection → Tree-sitter Parser → AST → Semantic Queries → Code Blocks
```

### Language Detection Flow
1. **File Extension Mapping**: `.py` → `python`
2. **Fallback Detection**: Use `whats_that_code` for uncertain extensions
3. **Parser Loading**: Load cached or create new Tree-sitter parser
4. **Language Validation**: Verify language is supported

### Semantic Extraction Process
1. **Tree-sitter Parsing**: Convert text to AST
2. **Language-specific Queries**: Apply queries for functions/classes
3. **Node Extraction**: Extract relevant AST nodes
4. **Content Slicing**: Extract text content with precise line numbers
5. **Block Creation**: Create `CodeBlock` objects with metadata

### Query-based Extraction
Instead of naive AST traversal, we use Tree-sitter queries:
```python
# Python example query
python_query = """
    (function_definition name: (identifier) @name) @function
    (class_definition name: (identifier) @name) @class
    (module) @module
"""

# Execute query - only gets relevant nodes
captures = query.captures(root_node)
```

This approach is dramatically more efficient than visiting every AST node.