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
from code_index.services.shared.command_context import CommandContext
from code_index.services.command.config_overrides import build_index_overrides, build_search_overrides
from code_index.logging_utils import LoggingConfigurator

# Global error handler instance
error_handler = ErrorHandler()
command_context = CommandContext(error_handler)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (INFO level)')
@click.option('--debug', is_flag=True, help='Enable debug logging (DEBUG level)')
@click.option('--log-treesitter', is_flag=True, default=False, help='Enable detailed Tree-sitter logging')
@click.option('--log-embedding', is_flag=True, default=False, help='Enable detailed embedding logging')
@click.pass_context
def cli(ctx, verbose: bool, debug: bool, log_treesitter: bool, log_embedding: bool):
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
        h.setFormatter(_logging.Formatter("%(levelname)s [file=%(current_file)s lang=%(current_language)s] %(message)s"))
        setattr(h, "_code_index_cli", True)
        root_logger.addHandler(h)
    LoggingConfigurator.ensure_context_filter()
    LoggingConfigurator.ensure_processing_logger()
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = level
    ctx.obj.setdefault("logging_components", {})
    if log_treesitter:
        ctx.obj["logging_components"]["code_index.treesitter"] = logging.DEBUG
    if log_embedding:
        ctx.obj["logging_components"]["code_index.embedding"] = logging.DEBUG


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

    log_dir = os.path.dirname(log_path) or "."
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            for path in sorted(paths):
                f.write(f"{path}\n")
    except OSError as exc:
        print(f"Failed to write timeout log to {log_path}: {exc}")


def _load_exclude_list(workspace_path: str, exclude_files_path: str | None) -> Set[str]:
    """Load exclude list as normalized relative paths from workspace root."""
    # Initialize file processing service with error handler
    file_processor = FileProcessingService(error_handler)
    return file_processor.load_exclude_list(workspace_path, exclude_files_path, "load_exclude_list")


@cli.command()
@click.pass_context
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
@click.option('--no-progress', is_flag=True, help='Disable progress UI (enabled by default)')
@click.option('--progress', is_flag=True, help='Force enable progress UI (default behaviour)')
def index(ctx, workspace: str, config: str, workspacelist: str | None, embed_timeout: int | None, retry_list: str | None, timeout_log: str | None,
          ignore_config: str | None, ignore_override_pattern: str | None, auto_ignore_detection: bool,
          use_tree_sitter: bool, chunking_strategy: str | None, no_progress: bool, progress: bool):
    """Index code files in workspace with enhanced features.
    
    Features:
    - Smart collection management with metadata storage
    - Intelligent ignore pattern system with GitHub templates
    - Semantic code chunking with Tree-sitter (when enabled)
    - KiloCode compatibility for seamless tool integration
    - Configurable file type weighting and advanced settings
    - Batch workspace processing via workspace list files
    """
    logging_overrides = dict(ctx.obj.get("logging_components", {})) if ctx and ctx.obj else {}

    use_progress_ui = False if no_progress else True
    if progress:
        use_progress_ui = True

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
                    use_tree_sitter, chunking_strategy, logging_overrides,
                    use_progress_ui=use_progress_ui
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
        use_tree_sitter, chunking_strategy, logging_overrides,
        use_progress_ui=use_progress_ui
    )


def _process_single_workspace(workspace: str, config: str, embed_timeout: int | None, retry_list: str | None,
                                timeout_log: str | None, ignore_config: str | None, ignore_override_pattern: str | None,
                                auto_ignore_detection: bool, use_tree_sitter: bool, chunking_strategy: str | None,
                                logging_overrides: dict[str, int] | None = None, *,
                                use_progress_ui: bool = True) -> tuple[int, int, int]:
    """Process a single workspace using IndexingService and return (processed_count, total_blocks, timed_out_files_count)."""
    logger.debug("Processing workspace: %s", workspace)
    logger.debug("Config path: %s", config)
    
    cli_overrides = build_index_overrides(
        embed_timeout=embed_timeout,
        timeout_log=timeout_log,
        ignore_config=ignore_config,
        ignore_override_pattern=ignore_override_pattern,
        auto_ignore_detection=auto_ignore_detection,
        use_tree_sitter=use_tree_sitter,
        chunking_strategy=chunking_strategy,
    )
    logger.debug("CLI overrides: %s", cli_overrides)

    deps = command_context.load_index_dependencies(
        workspace_path=workspace,
        config_path=config,
        overrides=cli_overrides,
        logging_overrides=logging_overrides,
    )
    cfg = deps.config

    # Force absolute workspace path
    cfg.workspace_path = os.path.abspath(workspace)
    logger.debug("Forced workspace_path: %s", cfg.workspace_path)

    # Verify workspace exists
    if not os.path.exists(cfg.workspace_path):
        print(f"❌ ERROR: Workspace does not exist: {cfg.workspace_path}")
        return 0, 0, 0

    # List workspace contents
    files = [f for f in os.listdir(cfg.workspace_path)
             if os.path.isfile(os.path.join(cfg.workspace_path, f))]
    logger.debug("Files in workspace: %d", len(files))
    for f in files[:5]:
        logger.debug("   File: %s", f)

    progress_manager = None
    file_scroller = None
    status_panel = None
    overall_task_id = None
    tui_failed = False

    indexing_service = deps.indexing_service

    logger.debug("Starting tree-sitter processing (enabled=%s max_file_size=%s)", cfg.use_tree_sitter, cfg.tree_sitter_max_file_size_bytes)

    result = None

    def progress_hook(file_path: str, processed: int, total: int, status: str, blocks: int) -> None:
        nonlocal overall_task_id
        if tui_failed:
            # Fallback to proper logging if TUI failed
            if status == "init":
                logger.info("Initializing indexing... Total files to process: %d", total)
            elif status == "start":
                logger.debug("Processing file: %s", file_path)
            elif status == "success":
                logger.info("Completed: %s (%d blocks)", file_path, blocks)
            elif status == "skipped":
                logger.debug("Skipped (unchanged): %s", file_path)
            elif status == "error":
                logger.warning("Error processing file: %s", file_path)
            logger.info("Progress: %d/%d (%d%%) files", processed, total, (processed*100//total if total > 0 else 0))
            return
            
        if not progress_manager or not overall_task_id:
            if not progress_manager:
                return
            if total <= 0:
                return
            overall_task_id = progress_manager.create_overall_task(total)

        current_display = file_path if status != "init" and file_path else "Processing Files"
        progress_manager.update_overall_progress(overall_task_id, processed, total, current_display)

        if file_scroller:
            file_scroller.ensure_file(file_path)
            if status == "start":
                file_scroller.update_status(file_path, "processing")
            elif status == "success":
                file_scroller.update_status(file_path, "success", f"Blocks: {blocks}")
            elif status == "skipped":
                file_scroller.update_status(file_path, "skipped", "Unchanged")
            elif status == "error":
                file_scroller.update_status(file_path, "error")

        if status_panel:
            progress_manager.update_status(f"Processed {processed}/{total} files")

    try:
        if use_progress_ui:
            try:
                from code_index.ui.progress_manager import ProgressManager
                from code_index.ui.file_scroller import FileScroller
                from code_index.ui.status_panel import StatusPanel
                progress_manager = ProgressManager()
                if not progress_manager.enabled:
                    tui_failed = True
                    logger.warning("TUI initialization failed, falling back to simple progress display")
                else:
                    file_scroller = FileScroller()
                    status_panel = StatusPanel(progress_manager.console)
                    if progress_manager.start_live_display() is None:
                        tui_failed = True
                        logger.warning("Failed to start live display, falling back to simple progress display")
            except Exception as e:
                tui_failed = True
                logger.warning(f"TUI initialization failed: {type(e).__name__}: {e}, falling back to simple progress display")

        result = indexing_service.index_workspace(
            workspace,
            cfg,
            progress_callback=progress_hook if use_progress_ui else None,
        )

    finally:
        if progress_manager:
            progress_manager.close()

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
            path_utils = PathUtils(error_handler, cfg.workspace_path)
            candidate = timeout_log if os.path.isabs(timeout_log) else os.path.join(cfg.workspace_path, timeout_log)
            normalized = path_utils.validate_and_normalize(candidate)
            if not normalized or not path_utils.is_path_within_workspace(normalized, cfg.workspace_path):
                print("Timeout log path is outside workspace; skipping write.")
            else:
                _write_timeout_log(set(result.timed_out_files), normalized)
                print(f"Timeout log written to: {normalized}")

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
    cli_overrides = build_search_overrides(
        min_score=min_score,
        max_results=max_results,
    )

    deps = command_context.load_search_dependencies(
        workspace_path=workspace,
        config_path=config,
        overrides=cli_overrides,
    )
    
    result = deps.search_service.search_code(query, deps.config)

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

    def create_code_snippet(code_chunk: str, preview_length: int) -> str:
        """
        Create a well-formatted code snippet for search results.
        
        Args:
            code_chunk: Full code content
            preview_length: Maximum length for the snippet
            
        Returns:
            Formatted code snippet with proper truncation
        """
        if not code_chunk:
            return ""
        
        # Clean up the code chunk - preserve some structure but make it readable
        lines = code_chunk.split('\n')
        
        # Remove excessive empty lines but preserve some structure
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not prev_empty:
                    cleaned_lines.append("")
                    prev_empty = True
            else:
                cleaned_lines.append(line.rstrip())
                prev_empty = False
        
        # Join back and truncate
        cleaned_code = '\n'.join(cleaned_lines).strip()
        
        if len(cleaned_code) <= preview_length:
            return cleaned_code
        
        # Truncate at word boundary if possible
        truncated = cleaned_code[:preview_length]
        
        # Try to truncate at a reasonable boundary (space, newline, or punctuation)
        for boundary in ['\n', ' ', ';', ',', ')', '}', ']']:
            last_boundary = truncated.rfind(boundary)
            if last_boundary > preview_length * 0.8:  # Don't truncate too early
                truncated = truncated[:last_boundary + 1]
                break
        
        return truncated.rstrip() + "..."

    if json_output:
        output = []
        preview_chars = getattr(deps.config, "search_snippet_preview_chars", 500)
        for match in result.matches:
            snippet = create_code_snippet(match.code_chunk, preview_chars)
            output.append({
                "filePath": match.file_path,
                "startLine": match.start_line,
                "endLine": match.end_line,
                "type": match.match_type,
                "score": match.score,
                "adjustedScore": match.adjusted_score,
                "snippet": snippet.replace("\n", "\\n"),
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print(f"Found {result.total_found} results:")
    preview_chars = getattr(deps.config, "search_snippet_preview_chars", 500)
    for i, match in enumerate(result.matches, 1):
        print(f"\n{i}. Score: {match.score:.3f} (adj {match.adjusted_score:.3f})")
        print(f"   File: {match.file_path}:{match.start_line}-{match.end_line}")
        snippet = create_code_snippet(match.code_chunk, preview_chars)
        print(f"   Preview:\n{snippet}")

