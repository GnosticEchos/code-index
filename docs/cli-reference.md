# Code Index CLI Reference

This document provides a complete, authoritative reference for the Code Index command-line interface. It complements the top-level [README.md](../README.md) by detailing every command, option, default, and behavior as implemented in [src/code_index/cli.py](src/code_index/cli.py), [src/code_index/collections_commands.py](src/code_index/collections_commands.py), [src/code_index/config.py](src/code_index/config.py), [src/code_index/vector_store.py](src/code_index/vector_store.py), and [src/code_index/chunking.py](src/code_index/chunking.py).

Sources of truth:
- [src/code_index/cli.py](src/code_index/cli.py)
- [src/code_index/collections_commands.py](src/code_index/collections_commands.py)
- [src/code_index/config.py](src/code_index/config.py)
- [src/code_index/vector_store.py](src/code_index/vector_store.py)
- [src/code_index/chunking.py](src/code_index/chunking.py)
- [pyproject.toml](pyproject.toml)

## Invocation and Installation Context

- Primary executable: code-index, defined in [pyproject.toml](pyproject.toml:33) via the console script entry point to [cli()](src/code_index/cli.py:29).
- Module invocation: python -m is not provided for this CLI; use the console script only.
- Global flags on [cli()](src/code_index/cli.py:29):
  - --verbose, -v: set logging to INFO level
  - --debug: set logging to DEBUG level

## Command Index

- Indexing: [index](#index)
- Search: [search](#search)
- Collections:
  - [collections list](#collections-list)
  - [collections info](#collections-info)
  - [collections delete](#collections-delete)
  - [collections prune](#collections-prune)
  - [collections clear-all](#collections-clear-all)

## index

Defined by [index()](src/code_index/cli.py:154).

Synopsis

`code-index index [OPTIONS]`

Description

Index code files in a workspace, create/update the Qdrant collection, and write semantic vectors and payloads. Supports Tree-sitter chunking, batch workspace processing, and robust timeout/retry handling.

Important:
- Configuration must specify embedding_length before first run; see [QdrantVectorStore.initialize()](src/code_index/vector_store.py:128).
- The configuration file is auto-created with defaults on first run if missing; see [Config.from_file()](src/code_index/config.py:130) and [Config.save()](src/code_index/config.py:150).

Options

- --workspace PATH
  - Type: string
  - Default: '.'
  - Maps to Config.workspace_path.
- --config PATH
  - Type: string
  - Default: 'code_index.json'
  - The JSON configuration to load/save; if absent, created with defaults.
- --workspacelist FILE
  - Type: string (path to text file)
  - Default: None
  - Each non-empty, non-comment line must be an existing directory; processes them sequentially with per-workspace stats and a final summary.
- --embed-timeout SECONDS
  - Type: int
  - Default: None (uses Config.embed_timeout_seconds; default 60; env override supported)
  - Overrides only for this run. See env CODE_INDEX_EMBED_TIMEOUT and [Config.__init__()](src/code_index/config.py:12).
- --retry-list FILE
  - Type: string (path to text file of newline-separated relative or absolute file paths)
  - Default: None
  - When provided, skips scanning and processes only files that remain after filtering by excludes, size, extension, and binary checks.
- --timeout-log FILE
  - Type: string (path)
  - Default: None (uses Config.timeout_log_path if not provided; default 'timeout_files.txt')
  - When timeouts occur (embedding/upsert), unique file relpaths are written; see [_write_timeout_log()](src/code_index/cli.py:100).
- --ignore-config FILE
  - Type: string (path)
  - Default: None
  - Overrides Config.ignore_config_path for this run.
- --ignore-override-pattern PATTERN
  - Type: string
  - Default: None
  - Sets Config.ignore_override_pattern for this run.
- --auto-ignore-detection
  - Type: flag (single-form)
  - Default: True (show_default=True)
  - Sets Config.auto_ignore_detection. No negative form is available.
- --use-tree-sitter
  - Type: flag
  - Default: False
  - Forces Tree-sitter chunking regardless of configured chunking_strategy.
- --chunking-strategy [lines|tokens|treesitter]
  - Type: choice
  - Default: None (uses Config.chunking_strategy; default 'lines')
  - Selects the chunking implementation; superseded by --use-tree-sitter.

Behavior and side effects

- Config loading/creation:
  - If --config exists, loads with [Config.from_file()](src/code_index/config.py:130). Otherwise creates defaults via [Config()](src/code_index/config.py:12) and [save](src/code_index/config.py:150), setting workspace_path to --workspace.
- CLI overrides precedence:
  - Index-time flags override loaded config for the current run (embed timeout, timeout log, ignore options, auto_ignore_detection, chunking strategy).
  - Environment variable CODE_INDEX_EMBED_TIMEOUT overrides file config after load; see [Config.from_file()](src/code_index/config.py:141).
- Chunking strategy resolution:
  - Name = --chunking-strategy or Config.chunking_strategy; --use-tree-sitter forces 'treesitter'.
  - Implementations: [LineChunkingStrategy](src/code_index/chunking.py:53), [TokenChunkingStrategy](src/code_index/chunking.py:101), [TreeSitterChunkingStrategy](src/code_index/chunking.py:163).
- Scanning:
  - If --retry-list is set, no workspace scan; candidate paths are normalized and filtered by excludes (Config.exclude_files_path), max_file_size_bytes (default 1MB), extensions (Config.extensions possibly augmented by Pygments if Config.auto_extensions), and binary detection.
  - Otherwise, scans the workspace respecting ignore rules, size, extensions; prints counts.
- Embedding:
  - Batches of size Config.batch_segment_threshold (default 60).
  - HTTP read timeouts add file to timed_out_files; batch aborts and the file is not cached so it can be retried.
- Vector store operations:
  - Initializes Qdrant; if Config.embedding_length is missing/invalid, initialization fails fast; see [QdrantVectorStore.initialize()](src/code_index/vector_store.py:128).
  - For each file: delete prior points for that file then upsert new points with payload fields filePath, codeChunk, startLine, endLine, type; pathSegments index is maintained for efficient filtering; see [upsert_points()](src/code_index/vector_store.py:254).
- Caching:
  - Per-file hash cache prevents re-embedding unchanged files, except for files in --retry-list which bypass the cache.
- Timeout log:
  - If any timeouts occurred and a log path is configured (from flag or Config.timeout_log_path), a sorted unique list of relpaths is written to disk.

Exit codes and error conditions

- 1 if:
  - No valid workspaces were found in --workspacelist.
  - Embedding configuration validation failed.
  - Vector store initialization failed.
  - Unhandled exceptions in processing cause early termination in batch summary.
- 0 on successful completion.

Examples

- Basic indexing (first run creates code_index.json):
  - echo '{&#34;embedding_length&#34;: 768}' > code_index.json
  - code-index index --workspace .
- Use Tree-sitter chunking with longer embed timeout:
  - code-index index --use-tree-sitter --embed-timeout 120
- Batch multiple workspaces:
  - printf &#34;/abs/path/to/project-a\n/abs/path/to/project-b\n&#34; > workspaces.txt
  - code-index index --workspacelist workspaces.txt --embed-timeout 90
- Retry only timed-out files from previous run:
  - code-index index --retry-list timeout_files.txt --embed-timeout 180
- Respect a custom ignore configuration:
  - code-index index --ignore-config .code-index-ignore

Notes/Pitfalls

- embedding_length is required before first successful index; set it in code_index.json to match your embedder’s output dimension (e.g., 768 or 1024).
- Tree-sitter parsing applies size and count limits (see defaults in [Config.__init__()](src/code_index/config.py:37)); files larger than 512KB are skipped by Tree-sitter and fall back to line-based chunking.
- Workspace scan and retry-list filtering enforce max_file_size_bytes (default 1MB), extension allowlist, and binary-file detection.
- If upsert or embedding calls time out, the file is not cached and remains eligible for retry; use --retry-list with the timeout log.
- Pygments-based extension auto-augmentation only applies when Config.auto_extensions is true.

## search

Defined by [search()](src/code_index/cli.py:471).

Synopsis

`code-index search [OPTIONS] "query text"`

Description

Embed the query using the configured embedder and perform a vector search in the workspace’s Qdrant collection, returning results with both raw score and adjustedScore based on file type, path, and language boosts.

Options

- --workspace PATH
  - Type: string
  - Default: '.'
- --config PATH
  - Type: string
  - Default: 'code_index.json'
- --min-score FLOAT
  - Type: float
  - Default: None (uses Config.search_min_score; default 0.4)
- --max-results INT
  - Type: int
  - Default: None (uses Config.search_max_results; default 50)
- --json
  - Type: flag
  - Default: False
  - Output results as JSON array with fields: filePath, startLine, endLine, type, score, adjustedScore, snippet (preview length Config.search_snippet_preview_chars; default 160).

Behavior and side effects

- Loads/creates config as with index.
- Validates embedding configuration via [OllamaEmbedder.validate_configuration()](src/code_index/cli.py:262) before embedding.
- Generates query embedding then queries Qdrant with score_threshold and limit derived from Config and any CLI overrides; see [QdrantVectorStore.search()](src/code_index/vector_store.py:300).
- Results are post-processed with file/path/language multipliers and sorted by adjustedScore; see [QdrantVectorStore._filetype_weight()](src/code_index/vector_store.py:206), [QdrantVectorStore._path_weight()](src/code_index/vector_store.py:214), [QdrantVectorStore._language_weight()](src/code_index/vector_store.py:231).

Exit codes and error conditions

- 1 if:
  - Embedding configuration validation fails
  - Query embedding fails
  - Qdrant search fails
- 0 on success.

Examples

- Simple search with defaults:
  - code-index search "function to parse JSON"
- Adjust thresholds and limit:
  - code-index search --min-score 0.55 --max-results 25 "jwt verify middleware"
- JSON output (preview width from config, default 160 chars):
  - code-index search --json "update board title mutation"

## collections clear-all

Synopsis

`code-index collections clear-all [--yes|-y] [--dry-run] [--keep-metadata]`

Description

Deletes all Qdrant collections discovered via the connected client, including the metadata collection named `code_index_metadata` by default. After deletions (unless --dry-run), removes all local cache artifacts matching cache_*.json from the application cache directory. This is a destructive, global operation intended to reset the entire instance rather than a single workspace.

Flags

- --yes, -y
  - Type: flag
  - Default: False
  - Skip confirmation prompt.
- --dry-run
  - Type: flag
  - Default: False
  - Show the collections that would be deleted (including metadata by default) and exit without deleting or clearing cache.
- --keep-metadata
  - Type: flag
  - Default: False
  - Preserve the `code_index_metadata` collection (exclude it from deletion targets).

Behavior and side effects

- Discovery: uses the Qdrant client behind the collections manager to call get_collections(), then extracts names.
- Targets: all discovered collection names; by default includes `code_index_metadata`. With --keep-metadata, metadata is excluded.
- Operation: for each target, calls client.delete_collection(name). 404/"not found" is treated as already deleted. Other errors are logged and do not abort the run.
- Summary: prints a user-facing summary of total found, deleted, already absent, and failed.
- Cache cleanup: unless --dry-run, removes all files matching cache_*.json from the resolved application cache directory and prints “Cache: removed N file(s) from application cache directory.”

Safety

- Destructive: removes all Qdrant collections (global). Use --dry-run to inspect targets first.
- Confirmation required unless --yes is provided.

Examples

- code-index collections clear-all --dry-run
- code-index collections clear-all --yes
- code-index collections clear-all --keep-metadata
- code-index collections clear-all --yes --debug

Notes

- This command deletes all Qdrant collections including `code_index_metadata` by default, then clears local cache files (cache_*.json). It does not target a single workspace; use “collections delete <name>” to remove one collection.

## collections list

Defined by [list_collections()](src/code_index/collections_commands.py:11) and exposed under [collections](src/code_index/cli.py:35).

Synopsis

`code-index collections list [--detailed]`

Description

Lists all Qdrant collections managed by Code Index, printing name, points, and mapped workspace path (when available via metadata).

Options

- --detailed
  - Type: flag
  - Default: False
  - Print full workspace paths without truncation.

Behavior

- Connects using default [Config()](src/code_index/config.py:12) and [CollectionManager](src/code_index/collections_commands.py:18).
- Prints 'No collections found.' when none are present.

Exit codes

- 1 on error; 0 on success.

## collections info

Defined by [collection_info()](src/code_index/collections_commands.py:47).

Synopsis

`code-index collections info COLLECTION_NAME`

Description

Displays detailed information about a specific collection: name, status, points, vectors, and, when available, the associated workspace path from the metadata collection.

Behavior

- Uses [CollectionManager](src/code_index/collections_commands.py:53).
- Attempts to read workspace mapping from the metadata collection 'code_index_metadata'.

Exit codes

- 1 on error; 0 on success.

## collections delete

Defined by [delete_collection()](src/code_index/collections_commands.py:93).

Synopsis

`code-index collections delete COLLECTION_NAME`

Description

Deletes the specified collection from Qdrant. Also removes the local cache entry for the deleted collection (cache_{canonical-id}.json) when the canonical id can be resolved (payload probe or ws-<hex16> naming). If the canonical id is unknown, cache cleanup is skipped. See [delete_collection()](src/code_index/collections_commands.py:116) and [delete_collection_cache()](src/code_index/cache.py).

Safety

- Destructive: permanently deletes the collection.
- Confirmation prompt required ('y' to continue).

Exit codes

- 1 on error; 0 on success.

## collections prune

Defined by [prune_collections()](src/code_index/collections_commands.py:115).

Synopsis

`code-index collections prune [--older-than DAYS]`

Description

Deletes old collections according to an age threshold.

Options

- --older-than DAYS
  - Type: int
  - Default: 30
  - Prunes collections older than the specified number of days.

Exit codes

- 1 on error; 0 on success.

## Configuration and Precedence

- Configuration file: JSON, default 'code_index.json'. Created automatically with defaults on first use if missing; see [Config.save()](src/code_index/config.py:150).
- Environment variables (read on process start and/or in [Config.from_file()](src/code_index/config.py:130)):
  - OLLAMA_BASE_URL (default 'http://localhost:11434')
  - OLLAMA_MODEL (default 'nomic-embed-text:latest')
  - QDRANT_URL (default 'http://localhost:6333')
  - QDRANT_API_KEY (default None)
  - WORKSPACE_PATH (default '.')
  - CODE_INDEX_EMBED_TIMEOUT (int; overrides embed_timeout_seconds after file load; default 60)
- CLI flag precedence:
  - For index: --embed-timeout, --timeout-log, ignore flags, --use-tree-sitter, --chunking-strategy, --workspace override the loaded config for that run.
  - For search: --min-score, --max-results, --workspace override config for that run.
- Required configuration:
  - embedding_length must be set before collection creation; see [QdrantVectorStore.initialize()](src/code_index/vector_store.py:159) error path on missing/invalid size.

## Collections Naming and Management

- Naming convention: [QdrantVectorStore._generate_collection_name()](src/code_index/vector_store.py:62)
  - Format: 'ws-' + first 16 hex chars of sha256(abs(workspace_path)).
- Metadata mapping: [QdrantVectorStore._store_collection_metadata()](src/code_index/vector_store.py:92)
  - Maintains 'code_index_metadata' collection with fields: collection_name, workspace_path, created_date, indexed_date.
- Index payload schema: created by [index()](src/code_index/cli.py:392) before upsert
  - payload keys: filePath, codeChunk, startLine, endLine, type; plus pathSegments for filtering; creation via [upsert_points()](src/code_index/vector_store.py:264-283).
- Deletion behaviors:
  - Per-file: [delete_points_by_file_path()](src/code_index/vector_store.py:387) uses pathSegments filter.
  - All points: [clear_collection()](src/code_index/vector_store.py:415).
  - Entire collection: [delete_collection()](src/code_index/vector_store.py:425).

## Chunking and Language Parsing Options

- CLI control:
  - --chunking-strategy: lines (default via config), tokens, treesitter.
  - --use-tree-sitter: forces Tree-sitter regardless of config.
- Implementations:
  - [LineChunkingStrategy](src/code_index/chunking.py:53):
    - Internal defaults: min_block_chars=50, max_block_chars=1000; splits by accumulated line length with tolerance.
  - [TokenChunkingStrategy](src/code_index/chunking.py:101):
    - Uses a token-based splitter from langchain-text-splitters with Config.token_chunk_size (default 1000) and Config.token_chunk_overlap (default 200). Falls back to line-based if the package is unavailable.
  - [TreeSitterChunkingStrategy](src/code_index/chunking.py:163):
    - Honors Config.tree_sitter_max_file_size_bytes (default 512KB) and various per-file limits (max blocks, functions, classes, impl blocks).
    - Skips tests/examples by default; configurable via config.
    - On any Tree-sitter error or unsupported language, falls back to line-based; see robust fallback path.
- Batch size for embeddings is orthogonal to chunking and set by Config.batch_segment_threshold (default 60).

## Search and Ranking Details

- API: [QdrantVectorStore.search()](src/code_index/vector_store.py:300)
- Defaults (from [Config.__init__()](src/code_index/config.py:71)):
  - search_min_score: 0.4
  - search_max_results: 50
  - search_snippet_preview_chars: 160
- Result payload fields:
  - id, score (Qdrant), adjustedScore (score multiplied by weights), payload { filePath, codeChunk, startLine, endLine, type }.
- Ranking adjustments (multiplicative):
  - File type weights: Config.search_file_type_weights (e.g., .vue 1.30, .ts 1.25, .md 0.80).
  - Path boosts: Config.search_path_boosts (e.g., 'src/' 1.25, 'docs/' 0.85).
  - Language boosts: Config.search_language_boosts (e.g., 'vue' 1.20).
- Excludes:
  - search_exclude_patterns: substring filters applied to filePath before scoring.
- Sorting:
  - Stable sort by adjustedScore then raw score, descending.

## Safety and Destructive Operations

- code-index collections clear-all: destructive deletion of all collections (metadata included by default) and cache cleanup; requires confirmation unless --yes.
- code-index collections delete: destructive deletion of a collection (prompts for confirmation).
- code-index collections prune: destructive for matched collections (no per-collection prompt).

## Troubleshooting

- Missing embedding_length in config
  - Symptom: initialization error from [QdrantVectorStore.initialize()](src/code_index/vector_store.py:166).
  - Fix: set embedding_length in code_index.json to match your embed model dimension.
- Vector size mismatch with existing collection
  - Symptom: Qdrant upsert/search errors indicating size mismatch.
  - Fix: ensure embedding_length matches your embedder; if the collection was created with a different size, delete the collection via 'code-index collections delete COLLECTION_NAME' or use a different workspace path/config.
- Qdrant connection issues
  - Symptom: initialization failures or search failures.
  - Fix: set QDRANT_URL and QDRANT_API_KEY correctly; ensure the service is reachable.
- Embedding timeouts
  - Symptom: 'Timeout' messages; files listed in timeout log.
  - Fix: increase --embed-timeout (index) or CODE_INDEX_EMBED_TIMEOUT; retry using --retry-list with the timeout log.
- Tree-sitter errors or large files
  - Symptom: warnings and fallback to line-based splitting.
  - Fix: adjust Tree-sitter config (max sizes/limits) or use line/token chunking.