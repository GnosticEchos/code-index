"""
Command-line interface for the code index tool.
"""
import os
import sys
import json
import logging
import click
from tqdm import tqdm
from typing import List, Set
from requests.exceptions import ReadTimeout

from code_index.config import Config
from code_index.config_service import ConfigurationService as ConfigurationLoaderService
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore
from code_index.cache import CacheManager
from code_index.collections import CollectionManager
from code_index.collections_commands import list_collections, collection_info, delete_collection, prune_collections, clear_all_collections
from code_index.chunking import (
    ChunkingStrategy,
    LineChunkingStrategy,
    TokenChunkingStrategy,
    TreeSitterChunkingStrategy,
)
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from code_index.file_processing import FileProcessingService
from code_index.path_utils import PathUtils
from code_index.service_validation import ServiceValidator
from code_index.services import IndexingService, SearchService, ConfigurationService as ConfigurationQueryService

# Global error handler instance
error_handler = ErrorHandler()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (INFO level)')
@click.option('--debug', is_flag=True, help='Enable debug logging (DEBUG level)')
@click.pass_context
def cli(ctx, verbose: bool, debug: bool):
    """Standalone code index tool."""
    # Initialize global logging once; default WARNING
    import logging as _logging
    level = _logging.DEBUG if debug else (_logging.INFO if verbose else _logging.WARNING)
    root_logger = _logging.getLogger()
    root_logger.setLevel(level)
    # Attach a single stream handler with simple formatter
    handler_found = False
    for h in list(root_logger.handlers):
        if getattr(h, "_code_index_cli", False):
            handler_found = True
            h.setLevel(level)
    if not handler_found:
        h = _logging.StreamHandler()
        h.setLevel(level)
        h.setFormatter(_logging.Formatter("%(levelname)s: %(message)s"))
        setattr(h, "_code_index_cli", True)
        root_logger.addHandler(h)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = level


@cli.group()
def collections():
    """Manage collections with smart workspace mapping.
    
    Features:
    - List collections with human-readable workspace paths
    - View detailed collection information and statistics
    - Delete collections with metadata cleanup
    - Prune old collections with smart retention policies
    - Clear all collections (global reset) with cache cleanup
    - KiloCode-compatible collection naming and structure
    """
    pass


# Register collection commands
collections.add_command(list_collections, name='list')
collections.add_command(collection_info, name='info')
collections.add_command(delete_collection, name='delete')
collections.add_command(prune_collections, name='prune')
collections.add_command(clear_all_collections, name='clear-all')


def _load_path_list(path_file: str, workspace: str) -> List[str]:
    """Load newline-separated paths; normalize to relpath from workspace. Ignore blank/comment lines."""
    # Initialize file processing service with error handler
    file_processor = FileProcessingService(error_handler)
    return file_processor.load_path_list(path_file, workspace, "load_path_list")


def _load_workspace_list(workspace_list_file: str) -> List[str]:
    """Load workspace list file containing directory paths. Skip empty lines and comments."""
    # Initialize file processing service with error handler
    file_processor = FileProcessingService(error_handler)
    return file_processor.load_workspace_list(workspace_list_file, "load_workspace_list")


def _write_timeout_log(paths: Set[str], log_path: str) -> None:
    """Write unique, sorted list of timed-out file paths to log file."""
    if not log_path:
        return

    # Initialize file processing service with error handler
    file_processor = FileProcessingService(error_handler)

    # Ensure directory exists using PathUtils
    path_utils = PathUtils(error_handler)
    log_dir = path_utils.normalize_path(os.path.dirname(log_path) or ".")
    os.makedirs(log_dir, exist_ok=True)

    lines = sorted(paths)
    try:
        # Use FileProcessingService to write the file
        content = "\n".join(lines)
        if lines:
            content += "\n"

        # Write file using FileProcessingService (we'll need to add this method)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(content)
    except (OSError, IOError):
        print(f"Warning: Could not write timeout log to {log_path}")


def _load_exclude_list(workspace_path: str, exclude_files_path: str | None) -> Set[str]:
    """Load exclude list as normalized relative paths from workspace root."""
    # Initialize file processing service with error handler
    file_processor = FileProcessingService(error_handler)
    return file_processor.load_exclude_list(workspace_path, exclude_files_path, "load_exclude_list")


@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
@click.option('--workspacelist', type=str, default=None, help='Path to file containing list of workspace directories to process')
@click.option('--embed-timeout', type=int, default=None, help='Override embedding timeout (seconds) for this run')
@click.option('--retry-list', type=str, default=None, help='Path to file with newline-separated relative paths to reprocess')
@click.option('--timeout-log', type=str, default=None, help='Override timeout log path for this run')
@click.option('--ignore-config', type=str, default=None, help='Path to custom ignore configuration file')
@click.option('--ignore-override-pattern', type=str, default=None, help='Override ignore patterns')
@click.option('--auto-ignore-detection', is_flag=True, show_default=True, default=True, help='Enable automatic ignore pattern detection')
@click.option('--use-tree-sitter', is_flag=True, help='Enable semantic code chunking with Tree-sitter')
@click.option('--chunking-strategy', type=click.Choice(['lines', 'tokens', 'treesitter']), default=None, help='Chunking strategy: lines (default), tokens, or treesitter')
def index(workspace: str, config: str, workspacelist: str | None, embed_timeout: int | None, retry_list: str | None, timeout_log: str | None,
          ignore_config: str | None, ignore_override_pattern: str | None, auto_ignore_detection: bool,
          use_tree_sitter: bool, chunking_strategy: str | None):
    """Index code files in workspace with enhanced features.
    
    Features:
    - Smart collection management with metadata storage
    - Intelligent ignore pattern system with GitHub templates
    - Semantic code chunking with Tree-sitter (when enabled)
    - KiloCode compatibility for seamless tool integration
    - Configurable file type weighting and advanced settings
    - Batch workspace processing via workspace list files
    """
    # Handle workspace list processing
    if workspacelist:
        workspaces = _load_workspace_list(workspacelist)
        if not workspaces:
            print(f"Error: No valid workspaces found in {workspacelist}")
            sys.exit(1)
        
        print(f"Processing {len(workspaces)} workspaces from {workspacelist}")
        total_processed = 0
        total_blocks = 0
        total_timeouts = 0
        
        for i, workspace_path in enumerate(workspaces, 1):
            print(f"\n[{i}/{len(workspaces)}] Processing workspace: {workspace_path}")
            try:
                # Process each workspace individually
                processed, blocks, timeouts = _process_single_workspace(
                    workspace_path, config, embed_timeout, retry_list, timeout_log,
                    ignore_config, ignore_override_pattern, auto_ignore_detection,
                    use_tree_sitter, chunking_strategy
                )
                total_processed += processed
                total_blocks += blocks
                total_timeouts += timeouts
            except Exception as e:
                print(f"Error processing workspace {workspace_path}: {e}")
                continue
        
        print(f"\nBatch processing completed:")
        print(f"  Total workspaces processed: {len(workspaces)}")
        print(f"  Total files processed: {total_processed}")
        print(f"  Total code blocks: {total_blocks}")
        print(f"  Total timeouts: {total_timeouts}")
        return
    
    # Single workspace processing (original logic)
    _process_single_workspace(
        workspace, config, embed_timeout, retry_list, timeout_log,
        ignore_config, ignore_override_pattern, auto_ignore_detection,
        use_tree_sitter, chunking_strategy
    )


def _process_single_workspace(workspace: str, config: str, embed_timeout: int | None, retry_list: str | None,
                                timeout_log: str | None, ignore_config: str | None, ignore_override_pattern: str | None,
                                auto_ignore_detection: bool, use_tree_sitter: bool, chunking_strategy: str | None) -> tuple[int, int, int]:
    """Process a single workspace using IndexingService and return (processed_count, total_blocks, timed_out_files_count)."""
    # Initialize ConfigurationService for centralized configuration management
    config_service = ConfigurationLoaderService(error_handler)

    # Prepare CLI overrides
    cli_overrides = {}
    if embed_timeout is not None:
        cli_overrides['embed_timeout_seconds'] = embed_timeout
    if timeout_log:
        cli_overrides['timeout_log_path'] = timeout_log
    if ignore_config:
        cli_overrides['ignore_config_path'] = ignore_config
    if ignore_override_pattern:
        cli_overrides['ignore_override_pattern'] = ignore_override_pattern
    if auto_ignore_detection is not None:
        cli_overrides['auto_ignore_detection'] = auto_ignore_detection
    if use_tree_sitter:
        cli_overrides['use_tree_sitter'] = True
        cli_overrides['chunking_strategy'] = 'treesitter'
    elif chunking_strategy:
        cli_overrides['chunking_strategy'] = chunking_strategy

    # Load configuration with fallback and CLI overrides
    cfg = config_service.load_with_fallback(
        config_path=config,
        workspace_path=workspace,
        overrides=cli_overrides
    )

    # Initialize IndexingService
    indexing_service = IndexingService(error_handler)

    # Execute indexing using the service
    result = indexing_service.index_workspace(workspace, cfg)

    # Display results
    if result.is_successful():
        print(f"Successfully processed {result.processed_files} files with {result.total_blocks} code blocks.")
    else:
        print(f"Indexing completed with errors: {len(result.errors)} errors")
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more errors")

    if result.has_warnings():
        print(f"Warnings: {len(result.warnings)} warnings")
        for warning in result.warnings[:3]:  # Show first 3 warnings
            print(f"  - {warning}")
        if len(result.warnings) > 3:
            print(f"  ... and {len(result.warnings) - 3} more warnings")

    if result.timed_out_files:
        print(f"Timeouts: {len(result.timed_out_files)} file(s) timed out")

        # Write timeout log if specified
        if timeout_log:
            # Normalize log path to absolute using PathUtils
            path_utils = PathUtils(error_handler, cfg.workspace_path)
            log_path_abs = path_utils.resolve_path(timeout_log) or path_utils.join_path(cfg.workspace_path, timeout_log)
            _write_timeout_log(set(result.timed_out_files), log_path_abs)
            print(f"Timeout log written to: {log_path_abs}")

    print(f"Processing time: {result.processing_time_seconds:.2f} seconds")
    print("To retry only failed files with a longer timeout, run: "
          "code-index index --workspace <...> --retry-list <timeout_log> --embed-timeout <seconds>")

    return result.processed_files, result.total_blocks, len(result.timed_out_files)


@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
@click.option('--min-score', type=float, default=None, help='Minimum similarity score (0.0-1.0)')
@click.option('--max-results', type=int, default=None, help='Maximum number of results')
@click.option('--json', 'json_output', is_flag=True, help='Output results as JSON')
@click.argument('query')
def search(workspace: str, config: str, min_score: float, max_results: int, json_output: bool, query: str):
    """Search indexed code using semantic similarity."""
    # Initialize ConfigurationService for centralized configuration management
    config_service = ConfigurationLoaderService(error_handler)

    # Prepare CLI overrides for search parameters
    cli_overrides = {}
    if min_score is not None:
        cli_overrides['search_min_score'] = min_score
    if max_results is not None:
        cli_overrides['search_max_results'] = max_results

    # Load configuration with fallback and CLI overrides
    cfg = config_service.load_with_fallback(
        config_path=config,
        workspace_path=workspace,
        overrides=cli_overrides
    )

    # Initialize SearchService
    search_service = SearchService(error_handler)

    # Execute search using the service
    result = search_service.search_code(query, cfg)

    # Display results
    if not result.is_successful():
        print(f"Search completed with errors: {len(result.errors)} errors")
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more errors")
        return

    if not result.has_matches():
        print("No results found.")
        return

    if json_output:
        output = []
        for match in result.matches:
            output.append({
                "filePath": match.file_path,
                "startLine": match.start_line,
                "endLine": match.end_line,
                "type": match.match_type,
                "score": match.score,
                "adjustedScore": match.adjusted_score,
                "snippet": match.code_chunk[:160].replace("\n", " "),  # Preview first 160 chars
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print(f"Found {result.total_found} results:")
    for i, match in enumerate(result.matches, 1):
        print(f"\n{i}. Score: {match.score:.3f} (adj {match.adjusted_score:.3f})")
        print(f"   File: {match.file_path}:{match.start_line}-{match.end_line}")
        print(f"   Preview: {match.code_chunk[:160].replace('\n', ' ')}...")

