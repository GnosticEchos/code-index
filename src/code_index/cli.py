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
    """Process a single workspace and return (processed_count, total_blocks, timed_out_files_count)."""
    # Initialize FileProcessingService for this function
    file_processor = FileProcessingService(error_handler)

    # Load configuration using FileProcessingService
    if file_processor.validate_file_path(config):
        cfg = Config.from_file(config)
    else:
        cfg = Config()
        cfg.workspace_path = workspace
        cfg.save(config)
    
    # Update workspace path if specified
    if workspace != '.':
        cfg.workspace_path = workspace

    # Apply CLI overrides
    if embed_timeout is not None:
        try:
            cfg.embed_timeout_seconds = int(embed_timeout)
        except ValueError:
            pass
    if timeout_log:
        cfg.timeout_log_path = timeout_log
    
    # Apply ignore-related CLI overrides
    if ignore_config:
        cfg.ignore_config_path = ignore_config
    if ignore_override_pattern:
        cfg.ignore_override_pattern = ignore_override_pattern
    cfg.auto_ignore_detection = auto_ignore_detection

    # Determine chunking strategy
    strategy_name = chunking_strategy or getattr(cfg, "chunking_strategy", "lines")
    if use_tree_sitter:
        strategy_name = "treesitter"

    if strategy_name == "treesitter":
        chunking_strategy_impl = TreeSitterChunkingStrategy(cfg)
    elif strategy_name == "tokens":
        chunking_strategy_impl = TokenChunkingStrategy(cfg)
    else:
        chunking_strategy_impl = LineChunkingStrategy(cfg)

    # Initialize components (embedder will read updated cfg)
    scanner = DirectoryScanner(cfg)
    parser = CodeParser(cfg, chunking_strategy_impl)
    embedder = OllamaEmbedder(cfg)
    vector_store = QdrantVectorStore(cfg)
    cache_manager = CacheManager(cfg.workspace_path, cfg)
    
    # Initialize PathUtils for centralized path operations
    path_utils = PathUtils(error_handler, cfg.workspace_path)
    
    # Validate configuration
    print("Validating configuration...")
    validation_result = embedder.validate_configuration()
    if not validation_result["valid"]:
        print(f"Error: {validation_result['error']}")
        sys.exit(1)
    
    print("Configuration is valid.")
    
    # Initialize vector store (will fail fast if embedding_length missing)
    print("Initializing vector store...")
    try:
        vector_store.initialize()
        print("Vector store initialized.")
    except Exception as e:
        error_context = ErrorContext(
            component="cli",
            operation="initialize_vector_store"
        )
        error_response = error_handler.handle_error(e, error_context, ErrorCategory.DATABASE, ErrorSeverity.CRITICAL)
        print(f"Error: {error_response.message}")
        sys.exit(1)
    
    # If retry-list is supplied, process ONLY those paths and SKIP full workspace scan
    bypass_cache_for: Set[str] = set()
    if retry_list:
        print(f"Using retry list: {retry_list} (skipping workspace scan)")
        retry_rel = _load_path_list(retry_list, cfg.workspace_path)

        # Load excludes and effective extensions (with optional auto-augmentation)
        excluded_relpaths = _load_exclude_list(cfg.workspace_path, getattr(cfg, "exclude_files_path", None))
        base_exts = [e.lower() for e in getattr(cfg, "extensions", [])]
        if getattr(cfg, "auto_extensions", False):
            base_exts = file_processor.augment_extensions_with_pygments(base_exts)
        ext_set = set(base_exts)

        # Filter files using centralized FileProcessingService
        criteria = {
            "workspace_path": cfg.workspace_path,
            "exclude_patterns": excluded_relpaths,
            "extensions": ext_set,
            "max_file_size": cfg.max_file_size_bytes,
            "skip_binary": True
        }

        chosen_abs = file_processor.filter_files_by_criteria(retry_rel, criteria)

        if not chosen_abs:
            print("No retry-list files to process after filtering.")
            return (0, 0, 0)

        file_paths = chosen_abs
        bypass_cache_for = {path_utils.get_workspace_relative_path(p) or path_utils.normalize_path(p) for p in chosen_abs}
        print(f"Found {len(file_paths)} files from retry list to process")
    else:
        # Scan directory to get set of valid files (respects .gitignore/size/extensions/excludes)
        print(f"Scanning directory: {cfg.workspace_path}")
        scanned_paths, skipped_count = scanner.scan_directory()
        file_paths = scanned_paths
        print(f"Found {len(file_paths)} files to process ({skipped_count} skipped)")

    # Process files
    print("Processing files...")
    processed_count = 0
    total_blocks = 0
    timed_out_files: Set[str] = set()
    
    with tqdm(total=len(file_paths), desc="Processing files") as pbar:
        for file_path in file_paths:
            rel_path = path_utils.get_workspace_relative_path(file_path) or path_utils.normalize_path(file_path)
            try:
                # Check if file has changed (unless bypassed due to retry-list)
                if rel_path not in bypass_cache_for:
                    current_hash = file_processor.get_file_hash(file_path)
                    cached_hash = cache_manager.get_hash(file_path)
                    if current_hash == cached_hash:
                        # File hasn't changed, skip processing
                        pbar.update(1)
                        continue
                else:
                    current_hash = file_processor.get_file_hash(file_path)

                # Parse file into blocks
                blocks = parser.parse_file(file_path)
                if not blocks:
                    # Update cache even if no blocks were generated (unless bypass? decide to still cache)
                    cache_manager.update_hash(file_path, current_hash)
                    pbar.update(1)
                    continue
                
                # Generate embeddings
                texts = [block.content for block in blocks if block.content.strip()]
                if not texts:
                    cache_manager.update_hash(file_path, current_hash)
                    pbar.update(1)
                    continue
                
                # Batch embeddings for efficiency
                batch_size = cfg.batch_segment_threshold
                all_embeddings: List[List[float]] = []
                embedding_failed = False
                
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    try:
                        embedding_response = embedder.create_embeddings(batch_texts)
                        all_embeddings.extend(embedding_response["embeddings"])
                    except ReadTimeout:
                        timed_out_files.add(rel_path)
                        embedding_failed = True
                        print(f"Timeout: Embedding request timed out for {rel_path}")
                        break
                    except Exception as e:
                        error_context = ErrorContext(
                            component="cli",
                            operation="embed_batch",
                            file_path=rel_path
                        )
                        error_response = error_handler.handle_network_error(e, error_context, "Ollama")
                        print(f"Warning: {error_response.message}")
                        embedding_failed = True
                        break

                if embedding_failed or len(all_embeddings) < len(texts) and len(all_embeddings) == 0:
                    # Do not cache as processed to allow retry
                    pbar.update(1)
                    continue
                
                # Prepare points for vector store
                points = []
                for i, block in enumerate(blocks):
                    if i >= len(all_embeddings):
                        break
                    import uuid
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{file_path}:{block.start_line}:{block.end_line}"))
                    point = {
                        "id": point_id,
                        "vector": all_embeddings[i],
                        "payload": {
                            "filePath": rel_path,
                            "codeChunk": block.content,
                            "startLine": block.start_line,
                            "endLine": block.end_line,
                            "type": block.type,
                            "embedding_model": embedder.model_identifier
                        }
                    }
                    points.append(point)
                
                # Delete existing points for this file and upsert new ones
                try:
                    vector_store.delete_points_by_file_path(rel_path)
                except Exception:
                    # Ignore errors if file wasn't previously indexed
                    pass
                
                try:
                    vector_store.upsert_points(points)
                except Exception as e:
                    msg = str(e).lower()
                    if "timed out" in msg:
                        timed_out_files.add(rel_path)
                        print(f"Timeout: Upsert timed out for {rel_path}")
                        # Do not cache to allow retry
                        pbar.update(1)
                        continue
                    else:
                        error_context = ErrorContext(
                            component="cli",
                            operation="upsert_points",
                            file_path=rel_path
                        )
                        error_response = error_handler.handle_error(e, error_context, ErrorCategory.DATABASE, ErrorSeverity.MEDIUM)
                        print(f"Warning: {error_response.message}")
                        # Do not cache, allow retry on next run
                        pbar.update(1)
                        continue
                
                # Update cache
                cache_manager.update_hash(file_path, current_hash)
                
                processed_count += 1
                total_blocks += len(blocks)
                pbar.update(1)
                pbar.set_postfix({"blocks": total_blocks})
                
            except Exception as e:
                error_context = ErrorContext(
                    component="cli",
                    operation="process_file",
                    file_path=rel_path
                )
                error_response = error_handler.handle_file_error(e, error_context, "file_processing")
                print(f"Warning: {error_response.message}")
                pbar.update(1)
    
    # Write timeout log if any
    timeout_log_path = cfg.timeout_log_path
    if timeout_log_path and timed_out_files:
        # Normalize log path to absolute using PathUtils
        log_path_abs = path_utils.resolve_path(timeout_log_path) or path_utils.join_path(cfg.workspace_path, timeout_log_path)
        _write_timeout_log(timed_out_files, log_path_abs)

    print(f"Processed {processed_count} files with {total_blocks} code blocks.")
    print(f"Timeouts: {len(timed_out_files)} file(s). Timeout log: {timeout_log_path}")
    print("To retry only failed files with a longer timeout, run: "
          "code-index index --workspace <...> --retry-list <timeout_log> --embed-timeout <seconds>")
    
    return processed_count, total_blocks, len(timed_out_files)


@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
@click.option('--min-score', type=float, default=None, help='Minimum similarity score (0.0-1.0)')
@click.option('--max-results', type=int, default=None, help='Maximum number of results')
@click.option('--json', 'json_output', is_flag=True, help='Output results as JSON')
@click.argument('query')
def search(workspace: str, config: str, min_score: float, max_results: int, json_output: bool, query: str):
    """Search indexed code using semantic similarity."""
    # Load configuration using FileProcessingService
    file_processor = FileProcessingService(error_handler)
    if file_processor.validate_file_path(config):
        cfg = Config.from_file(config)
    else:
        cfg = Config()
        cfg.workspace_path = workspace
        cfg.save(config)
    
    # Update workspace path if specified
    if workspace != '.':
        cfg.workspace_path = workspace
    
    # Apply CLI overrides
    if min_score is not None:
        cfg.search_min_score = min_score
    if max_results is not None:
        cfg.search_max_results = max_results
    
    # Initialize components
    embedder = OllamaEmbedder(cfg)
    vector_store = QdrantVectorStore(cfg)
    
    # Validate configuration
    validation_result = embedder.validate_configuration()
    if not validation_result["valid"]:
        print(f"Error: {validation_result['error']}")
        sys.exit(1)
    
    # Generate query embedding
    try:
        embedding_response = embedder.create_embeddings([query])
        query_vector = embedding_response["embeddings"][0]
    except Exception as e:
        print(f"Error generating embedding for query: {e}")
        sys.exit(1)
    
    # Perform search
    try:
        results = vector_store.search(
            query_vector=query_vector,
            min_score=cfg.search_min_score,
            max_results=cfg.search_max_results
        )
    except Exception as e:
        print(f"Error searching: {e}")
        sys.exit(1)
    
    # Display results
    if not results:
        print("No results found.")
        return

    if json_output:
        preview_len = getattr(cfg, "search_snippet_preview_chars", 160)
        output = []
        for result in results:
            payload = result.get("payload", {}) or {}
            chunk = payload.get("codeChunk", "") or ""
            snippet = (chunk[:preview_len]).replace("\n", " ")
            output.append({
                "filePath": payload.get("filePath", ""),
                "startLine": payload.get("startLine", 0),
                "endLine": payload.get("endLine", 0),
                "type": payload.get("type", ""),
                "score": float(result.get("score", 0.0) or 0.0),
                "adjustedScore": float(result.get("adjustedScore", result.get("score", 0.0)) or 0.0),
                "snippet": snippet,
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print(f"Found {len(results)} results:")
    preview_len = getattr(cfg, "search_snippet_preview_chars", 160)
    for i, result in enumerate(results, 1):
        score = float(result.get("score", 0.0) or 0.0)
        adjusted = float(result.get("adjustedScore", score) or score)
        payload = result.get("payload", {}) or {}
        file_path = payload.get("filePath", "unknown")
        start_line = payload.get("startLine", 0)
        end_line = payload.get("endLine", payload.get("EndLine", 0))
        content_preview = (payload.get("codeChunk", "") or "")[:preview_len].replace('\n', ' ')
        print(f"\n{i}. Score: {score:.3f} (adj {adjusted:.3f})")
        print(f"   File: {file_path}:{start_line}-{end_line}")
        print(f"   Preview: {content_preview}...")

