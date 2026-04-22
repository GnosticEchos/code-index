# Graph Report - src/code_index  (2026-04-22)

## Corpus Check
- 131 files · ~98,744 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2864 nodes · 12219 edges · 43 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 8555 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Core Batch & Strategy Design|Core Batch & Strategy Design]]
- [[_COMMUNITY_Batch Processing Lifecycle|Batch Processing Lifecycle]]
- [[_COMMUNITY_Batch Management Service|Batch Management Service]]
- [[_COMMUNITY_Parallel Execution & CLI Commands|Parallel Execution & CLI Commands]]
- [[_COMMUNITY_Collection & Cache Management|Collection & Cache Management]]
- [[_COMMUNITY_Utility & Chunking Primitives|Utility & Chunking Primitives]]
- [[_COMMUNITY_Embedding & Target Configuration|Embedding & Target Configuration]]
- [[_COMMUNITY_File Scanning & Recovery|File Scanning & Recovery]]
- [[_COMMUNITY_Query Result Caching|Query Result Caching]]
- [[_COMMUNITY_Language Configuration Builder|Language Configuration Builder]]
- [[_COMMUNITY_Performance Tracking & Memory|Performance Tracking & Memory]]
- [[_COMMUNITY_Directory Scanning & Language Detection|Directory Scanning & Language Detection]]
- [[_COMMUNITY_Parallel File Processing|Parallel File Processing]]
- [[_COMMUNITY_MCP Progress Reporting|MCP Progress Reporting]]
- [[_COMMUNITY_Centralized Error Handling|Centralized Error Handling]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]

## God Nodes (most connected - your core abstractions)
1. `Config` - 829 edges
2. `ErrorHandler` - 725 edges
3. `ErrorSeverity` - 690 edges
4. `ErrorCategory` - 690 edges
5. `ErrorContext` - 672 edges
6. `FileProcessingService` - 180 edges
7. `ServiceValidator` - 176 edges
8. `QdrantVectorStore` - 176 edges
9. `ConfigurationService` - 174 edges
10. `PathUtils` - 169 edges

## Surprising Connections (you probably didn't know these)
- `Config` --semantically_similar_to--> `ErrorHandler`  [INFERRED] [semantically similar]
  /home/james/kanban_frontend/code_index/src/code_index/config.py → src/code_index/errors.py
- `TreeSitterParserManager` --uses--> `Config`  [EXTRACTED]
  src/code_index/parser_manager.py → /home/james/kanban_frontend/code_index/src/code_index/config.py
- `HybridParserManager` --uses--> `Config`  [EXTRACTED]
  src/code_index/hybrid_parsers.py → /home/james/kanban_frontend/code_index/src/code_index/config.py
- `EnhancedDirectoryScanner` --uses--> `Config`  [EXTRACTED]
  src/code_index/enhanced_scanner.py → /home/james/kanban_frontend/code_index/src/code_index/config.py
- `Collection management for the code index tool.` --uses--> `Config`  [INFERRED]
  /home/james/kanban_frontend/code_index/src/code_index/collections.py → /home/james/kanban_frontend/code_index/src/code_index/config.py

## Hyperedges (group relationships)
- **Chunking Strategy Family** — chunking_chunking_strategy, chunking_line_chunking_strategy, chunking_token_chunking_strategy, chunking_tree_sitter_chunking_strategy [INFERRED]
- **Core System Services** — config_service_configuration_service, file_processing_file_processing_service, errors_error_handler, path_utils_path_utils, logging_utils_logging_configurator [INFERRED]
- **Metadata and Resource Management** — cache_cache_manager, collections_collection_manager, parser_manager_tree_sitter_parser_manager [INFERRED]

## Communities

### Community 0 - "Core Batch & Strategy Design"
Cohesion: 0.02
Nodes (510): BatchConfig, Group files by detected language., Create batches for retrying failed files., Get statistics about created batches., Configuration for batch processing., Manages file processing in optimized batches., Initialize batch manager., Load batch configuration from config. (+502 more)

### Community 1 - "Batch Processing Lifecycle"
Cohesion: 0.02
Nodes (147): BatchProcessingResult, TreeSitterBatchProcessor service for batch processing operations.  This service, Process multiple files efficiently by grouping by language with parallel process, Process language groups in parallel using ThreadPoolExecutor.                  A, Process language groups sequentially (fallback for small batches or when paralle, Group files by language for efficient processing.          Args:             fil, Result of batch processing operation., Optimize configuration for batch processing (delegated to scheduler). (+139 more)

### Community 2 - "Batch Management Service"
Cohesion: 0.03
Nodes (171): BatchManager, Batch manager for processing files in optimized batches.  Handles file batching,, Get list of file paths to process.                  Args:             workspace:, Create batches from file list for memory-efficient processing., Process files with optional parallel execution.                  Args:, Process files in parallel using ThreadPoolExecutor., Process files sequentially., Process batches in parallel.                  Args:             batches: List of (+163 more)

### Community 3 - "Parallel Execution & CLI Commands"
Cohesion: 0.02
Nodes (83): CommandExecutor, CommandResult, create_command_executor(), Command executor module for executing configuration commands.  This module handl, Execute export config command., Execute reset to defaults command., Factory function to create a CommandExecutor., Result of a configuration command operation. (+75 more)

### Community 4 - "Collection & Cache Management"
Cohesion: 0.02
Nodes (143): clear_all_caches(), delete_collection_cache(), Determine the application cache directory for code_index.      Resolution order:, Delete cache file(s) for one canonical collection identifier.      Inputs:, Remove all collection cache artifacts.      Behavior:         - Remove all files, resolve_cache_dir(), cli(), search() (+135 more)

### Community 5 - "Utility & Chunking Primitives"
Cohesion: 0.02
Nodes (72): ABC, calculate_optimal_batch_size(), create_batches_from_texts(), estimate_text_memory_usage(), get_memory_efficient_batch_size(), Calculate optimal batch size based on memory constraints., Estimate memory usage for embedding a list of texts., Create batches from a list of texts. (+64 more)

### Community 6 - "Embedding & Target Configuration"
Cohesion: 0.02
Nodes (92): Show search result processing information., search_info(), Generate embeddings for texts using Ollama API.                  Args:, EmbeddingCache, Initialize the embedding cache.          Args:             max_size: Maximum num, Get an embedding from the cache.          Args:             key: The cache key., Store an embedding in the cache.          Args:             key: The cache key., Clear all entries from the cache and reset statistics. (+84 more)

### Community 7 - "File Scanning & Recovery"
Cohesion: 0.03
Nodes (72): _process_single_workspace(), Index workspace with real-time file processing display., ErrorRecoveryService, FileScroller, File scroller for TUI file processing display., Add a file to the scroller., Ensure a file entry exists, adding it if necessary., Display files being processed in TUI operations. (+64 more)

### Community 8 - "Query Result Caching"
Cohesion: 0.04
Nodes (80): QueryCache, Query caching service for Tree-sitter queries.  This module provides caching fun, Service for caching query results.          Handles:     - Query result caching, Initialize the QueryCache., Set a cached query result., Get a cached query result if present., Return the cache bucket for a specific language (test helper)., Invalidate the cache for a language or a specific query key. (+72 more)

### Community 9 - "Language Configuration Builder"
Cohesion: 0.03
Nodes (44): ConfigBuilder, LanguageConfig, Configuration building service., Get extraction limits., Get minimum block chars., Builds language configurations., Build configuration for a language., Configuration for a specific language. (+36 more)

### Community 10 - "Performance Tracking & Memory"
Cohesion: 0.04
Nodes (57): BatchProgressTracker, Track progress during batch processing operations., Initialize the progress tracker.                  Args:             total_items:, Start tracking progress., Log current progress., Mark processing as complete and return statistics., create_memory_manager(), MemoryManager (+49 more)

### Community 11 - "Directory Scanning & Language Detection"
Cohesion: 0.05
Nodes (45): EnhancedDirectoryScanner, Enhanced directory scanner with smart ignore pattern integration., Enhanced directory scanner with smart ignore pattern integration., Initialize enhanced directory scanner with configuration., Load exclude list as normalized relative paths from workspace root., Compute effective extension set with optional auto-augmentation., Check if a file/directory should be skipped as a dot file., Recursively scan directory for supported files with enhanced ignore patterns. (+37 more)

### Community 12 - "Parallel File Processing"
Cohesion: 0.06
Nodes (21): ParallelProcessingError, ProcessingResult, Result of processing a single file., Process files in parallel.                  Args:             files: List of fil, Process files and maintain order of results., Exception raised when parallel processing fails., Process files and return results as they complete., Wrap processing function with timing and error handling. (+13 more)

### Community 13 - "MCP Progress Reporting"
Cohesion: 0.09
Nodes (18): BatchProgressInfo, ProgressReporter, ProgressUpdate, Progress Reporter for MCP Server  Provides progress reporting for long-running o, Start tracking a batch operation.                  Args:             total_batch, Update progress for batch operations.                  Args:             batch_n, Progress information for long-running operations, Mark a batch as complete and record timing.                  Args:             b (+10 more)

### Community 14 - "Centralized Error Handling"
Cohesion: 0.08
Nodes (13): Handle a general error with full context and structured response.          Args:, Handle validation errors specifically.          Args:             error: The val, Handle file system errors specifically.          Args:             error: The fi, Handle network/API errors specifically.          Args:             error: The ne, Handle service connection errors with specific guidance.          Args:, Handle configuration errors specifically.          Args:             error: The, Handle unknown/unexpected errors.          Args:             error: The unexpect, Auto-detect error category based on exception type and context. (+5 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (14): create_parallel_executor(), ParallelExecutor, Parallel executor module for parallel file processing.  This module handles para, Wrap processing function with timing., Create a result dictionary., Create an error result., Update progress tracking., Execute files in batches. (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (13): ConfigPersistence, create_persistence(), Configuration persistence module for MCP server.  This module handles configurat, Handles configuration documentation, templates, and optimization examples., Get optimization strategies., Get comprehensive configuration documentation., Get parameter compatibility information., Get troubleshooting guide. (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (11): create_query_builder(), QueryBuilder, Query builder module for building configuration queries.  This module handles bu, Builds queries for configuration query operations., Build a status query., Build a config validation query., Build a search query., Build a file status query. (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (12): CommandParser, create_command_parser(), ParsedCommand, Command parser module for parsing configuration commands.  This module handles p, Factory function to create a CommandParser., Parsed command result., Parses and validates configuration commands., Parse save config command. (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (10): create_filter_builder(), FilterBuilder, Filter builder module for building filters in configuration queries.  This modul, Builds filters for configuration query operations., Build a filter for checking if a file is processed., Build a filter for workspace validity., Build a filter for project type detection., Build a filter for service health. (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (8): ParallelProgressTracker, Parallel progress tracker module for tracking progress in concurrent operations., Thread-safe progress tracker for parallel operations.          Tracks progress a, Initialize the progress tracker.                  Args:             total: Total, Increment the completed count.                  Args:             count: Number, Get current progress.                  Returns:             Tuple of (completed,, Check if processing is complete., Get elapsed time since tracking started.

### Community 21 - "Community 21"
Cohesion: 0.22
Nodes (5): PathResolver, Path resolution service., Get path relative to base., Get language from file path., Resolves and normalizes file paths.

### Community 22 - "Community 22"
Cohesion: 0.28
Nodes (7): BatchProcessingResult, create_error_result(), create_success_result(), Batch processing result model and related utilities.  This module contains the B, Result of batch processing operation., Create an error result for batch processing failures., Create a success result for batch processing.

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (5): FileFilter, File filtering service., Check if file should be processed., Filter list of files., Filters files based on patterns and rules.

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (4): Check if overall system is healthy., Get the health percentage of services., Get the indexing coverage percentage., Get a summary of the system status.

### Community 25 - "Community 25"
Cohesion: 0.25
Nodes (8): CacheManager, TreeSitterChunkingStrategy, EnhancedDirectoryScanner, ErrorHandler, FileProcessingService, HybridParserManager, TreeSitterParserManager, PathUtils

### Community 26 - "Community 26"
Cohesion: 0.33
Nodes (3): Get the success rate as a percentage., Get the failure rate as a percentage., Get a summary of the processing statistics.

### Community 27 - "Community 27"
Cohesion: 0.4
Nodes (3): CommandResult, Command result module for CQRS command operations.  This module defines the Comm, Result of a configuration command operation.

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (4): BatchManager, FileProcessor, IndexingOrchestrator, IndexingService

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): ConfigurationService

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Ensure the global context filter is attached to the root logger and its handlers

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Create a dedicated handler for processing progress so it appears even in minimal

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Apply per-component logging levels, creating handlers when stricter than root.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return a dictionary with resolved numeric logging levels.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Get the query cache dictionary.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Get the maximum cache size.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Get the TTL in seconds, or None if disabled.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): LineChunkingStrategy

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): TokenChunkingStrategy

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): GitignoreTemplateManager

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): LoggingConfigurator

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): CodeBlock

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): utils

## Knowledge Gaps
- **435 isolated node(s):** `Cache utilities and manager for the code index tool. - Centralizes cache directo`, `Determine the application cache directory for code_index.      Resolution order:`, `Delete cache file(s) for one canonical collection identifier.      Inputs:`, `Remove all collection cache artifacts.      Behavior:         - Remove all files`, `Manages file hashes to avoid reprocessing unchanged files.` (+430 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 29`** (1 nodes): `ConfigurationService`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Ensure the global context filter is attached to the root logger and its handlers`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Create a dedicated handler for processing progress so it appears even in minimal`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Apply per-component logging levels, creating handlers when stricter than root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return a dictionary with resolved numeric logging levels.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Get the query cache dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Get the maximum cache size.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Get the TTL in seconds, or None if disabled.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `LineChunkingStrategy`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `TokenChunkingStrategy`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `GitignoreTemplateManager`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `LoggingConfigurator`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `CodeBlock`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `utils`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Core Batch & Strategy Design` to `Batch Processing Lifecycle`, `Batch Management Service`, `Parallel Execution & CLI Commands`, `Collection & Cache Management`, `Utility & Chunking Primitives`, `Embedding & Target Configuration`, `File Scanning & Recovery`, `Query Result Caching`, `Language Configuration Builder`, `Directory Scanning & Language Detection`, `Community 16`, `Community 17`, `Community 25`?**
  _High betweenness centrality (0.243) - this node is a cross-community bridge._
- **Why does `ErrorHandler` connect `Core Batch & Strategy Design` to `Batch Processing Lifecycle`, `Batch Management Service`, `Parallel Execution & CLI Commands`, `Collection & Cache Management`, `Utility & Chunking Primitives`, `Embedding & Target Configuration`, `File Scanning & Recovery`, `Query Result Caching`, `Language Configuration Builder`, `Directory Scanning & Language Detection`, `Centralized Error Handling`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `ErrorSeverity` connect `Core Batch & Strategy Design` to `Batch Processing Lifecycle`, `Batch Management Service`, `Parallel Execution & CLI Commands`, `Collection & Cache Management`, `Utility & Chunking Primitives`, `Embedding & Target Configuration`, `File Scanning & Recovery`, `Query Result Caching`, `Language Configuration Builder`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 808 inferred relationships involving `Config` (e.g. with `CollectionManager` and `Collection management for the code index tool.`) actually correct?**
  _`Config` has 808 INFERRED edges - model-reasoned connections that need verification._
- **Are the 702 inferred relationships involving `ErrorHandler` (e.g. with `CorrectedIndexer` and `Indexer that properly targets Test_CodeBase.`) actually correct?**
  _`ErrorHandler` has 702 INFERRED edges - model-reasoned connections that need verification._
- **Are the 687 inferred relationships involving `ErrorSeverity` (e.g. with `ParserResult` and `BaseFallbackParser`) actually correct?**
  _`ErrorSeverity` has 687 INFERRED edges - model-reasoned connections that need verification._
- **Are the 687 inferred relationships involving `ErrorCategory` (e.g. with `ParserResult` and `BaseFallbackParser`) actually correct?**
  _`ErrorCategory` has 687 INFERRED edges - model-reasoned connections that need verification._