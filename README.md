# Code Index Tool

A high-precision Universal Structural Intelligence engine for codebase indexing and semantic search. It combines deep structural analysis with AI-driven content identification to create a relationship-native map of any codebase.

- **Universal Relationship Schema**: Surgical S-expression queries (908 records) for 200+ languages, identifying `class`, `function`, `import`, and `call` relationships.
- **AI Gatekeeper (Magika)**: Google's Magika Deep Learning model identifies files by structural patterns in the first 2KB, ensuring precise language routing.
- **High-Precision Search**: Semantic search weighted by structural importance, file type, and path.
- **Unified MCP Server**: Full Model Context Protocol server exposing indexing, search, and collection management tools to AI assistants.
- **Cross-Platform Binaries**: Standalone 37MB executables for Linux, macOS, and Windows with embedded Magika ONNX runtime.

## Core Intelligence Features

### 1. Universal Relationship Schema
Unlike generic chunking, Code Index understands the *nature* of code. It uses the Relationship-Native Query Forge to extract:
- **`class`**: Structural types (Structs, Enums, Interfaces, Modules).
- **`function`**: Callable logic (Methods, Procedures, Signatures).
- **`import`**: Dependency links (Cross-file imports, requires).
- **`call`**: Execution links (Method calls, qualified calls).

### 2. Magika AI Identification
Integrated Google's Magika model to provide 99%+ accuracy in file identification.
- **Intelligence**: Identifies content types by structural patterns rather than just extensions.
- **Tiered Detection**: `Magika (AI) -> Extension Map -> Generic Text` fallback.
- **Performance**: High-speed ONNX-based detection with minimal overhead.

### 3. Structural Chunking (Tree-sitter)
Uses modern Tree-sitter bindings (v0.23.x) to perform surgical extraction of code symbols.
- **Version-Aware**: Dual-API support for both dictionary-based and list-based capture returns.
- **Relationship-Native**: Every chunk is tagged with its relationship class (e.g., `type: function, name: validate`).

## MCP Server

This tool includes a complete **Model Context Protocol (MCP) server** that provides AI assistants with powerful code indexing and search capabilities.

### 🛠️ MCP Tools Overview

| Category          | Tool                  | Description                                |
|-------------------|------------------------|--------------------------------------------|
| 📊 **Indexing**   | `index`                | Index code files with high-precision structural analysis |
| 🔍 **Search**     | `search`               | Semantic search on relationship-native chunks |
| 📋 **Management** | `collections`          | Manage vector collections with workspace mapping |

## Quick Start

```bash
# Install package and dependencies
uv pip install -e .

# Index your codebase with Structural Intelligence
code-index index --use-tree-sitter

# Search relationship-native chunks
code-index search "authentication logic"

# Start MCP server for AI assistant integration
uv run code-index-mcp
```

## Configuration

Default file: `code_index.json`. 

| Option | Description | Default |
|--------|-------------|---------|
| `use_tree_sitter` | Enable high-precision structural analysis | `false` |
| `chunking_strategy` | Set to "treesitter" for relationship extraction | `"lines"` |
| `tree_sitter_min_block_chars` | Min chars for structural blocks | `5` |
| `tree_sitter_max_blocks_per_file` | Max semantic blocks per file | `100` |

## KiloCode Compatibility

- Collection naming matches KiloCode convention: `ws-` + SHA256(workspace_path).
- Payload fields (filePath, codeChunk, startLine, endLine, type) match KiloCode expectations.
- High-precision types (`class`, `function`, `import`, `call`) are fully supported.

## Build System

- Cross-platform binaries built with **Nuitka 2.7.16+**.
- Embedded Magika ONNX runtime for standalone AI detection.
- Static libpython linking issues resolved across all platforms.
- Build scripts: `scripts/build/`.

## License

MIT
