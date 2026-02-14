# Configuration Reference

## Overview
The `Config` object (`src/code_index/config.py`) is composed of eight sections that mirror the CLI configuration schema. Each section is backed by a dataclass and may be addressed through flattened attributes (e.g. `config.workspace_path`) or nested dictionary keys.

**For a complete configuration schema reference, see [Configuration Schema](./configuration-schema.md).**

```
Config
├── core (CoreConfig)
├── files (FileHandlingConfig)
├── ignore (IgnoreConfig)
├── chunking (ChunkingConfig)
├── tree_sitter (TreeSitterConfig)
├── search (SearchConfig)
├── performance (PerformanceConfig)
└── logging (LoggingConfig)
```

The flattened mapping is defined by `Config.SECTION_ATTR_MAP`. When writing JSON configuration files, keys may target either full sections (e.g. `{"tree_sitter": {...}}`) or flattened attributes (e.g. `{"use_tree_sitter": true}`).

## Section Summaries
- **Core** (`core`): workspace location, embedding model endpoints, and embed timeout. The model name auto-populates `embedding_length` when not provided.
- **Files** (`files`): input file extensions, maximum file size, and gitignore behavior.
- **Ignore** (`ignore`): sources for ignore rules and user-defined override patterns.
- **Chunking** (`chunking`): default chunking strategy and per-language chunk sizing.
- **Tree-sitter** (`tree_sitter`): Tree-sitter toggles, maximum blocks, skip rules, and debug logging flag.
- **Search** (`search`): scoring thresholds, per-extension weights, and path/language boosts.
- **Performance** (`performance`): streaming thresholds, fallback parser settings, and parser performance monitoring options.
- **Logging** (`logging`): component log levels used by `logging.config.dictConfig`.

## Serialization Helpers
`Config.to_nested_dict()` returns the dataclass structure grouped by section, while `Config.to_dict()` flattens values using `SECTION_ATTR_MAP`. JSON files saved through `Config.save()` match the flattened schema.

`Config.from_file(path)` loads JSON and automatically applies environment overrides such as `CODE_INDEX_EMBED_TIMEOUT`. `Config.update_from_dict(data)` accepts either section dictionaries or flattened keys, allowing layered overrides (default → file → workspace → CLI).

## Authoring JSON
A minimal `code_index.json` file might look like:

```json
{
  "workspace_path": ".",
  "use_tree_sitter": true,
  "tree_sitter": {
    "tree_sitter_max_blocks_per_file": 80
  },
  "performance": {
    "streaming_threshold_bytes": 3145728
  }
}
```

The CLI accepts overrides (`code-index index --chunking-strategy treesitter`) and merges them using `ConfigurationService.apply_cli_overrides()`.

## Testing Expectations
All configuration round-trip tests should:
- Serialize with `Config.to_dict()` or `Config.save()`.
- Reload using `Config.from_file()` or by constructing a fresh `Config()` and calling `update_from_dict()`.
- Assert that overridden fields survive the round trip and that unaffected sections retain defaults.

## Related Documentation
- **[Configuration Schema](./configuration-schema.md)** - Complete JSON schema with all options, types, defaults, validation rules, and examples
