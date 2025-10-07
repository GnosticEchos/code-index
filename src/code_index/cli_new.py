"""
Command-line interface for the code index tool with new architecture.
"""
import logging.handlers
import os
import sys
import json
import logging
import click
from typing import List, Optional, Set
from datetime import datetime
from pathlib import Path
import logging as _logging

from code_index.config import Config
from code_index.config_service import ConfigurationService as ConfigLoaderService
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
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

# Import NEW SERVICES
from code_index.services import IndexingService, SearchService, ConfigurationService as ConfigurationQueryService
from code_index.search import SearchValidationService, SearchResultProcessor, SearchStrategyFactory, EmbeddingGenerator
from code_index.ui import TUIInterface
from code_index.collections import CollectionManager
from code_index.collections_commands import list_collections, collection_info, delete_collection, prune_collections, clear_all_collections
from code_index.services import HealthService, WorkspaceService

# Global error handler instance
error_handler = ErrorHandler()

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (INFO level)')
@click.option('--debug', is_flag=True, help='Enable debug logging (DEBUG level)')
@click.pass_context
def cli(ctx, verbose: bool, debug: bool):
    """Standalone code index tool with new architecture."""
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
@click.option('--tui', is_flag=True, help='Enable TUI progress display')
@click.option('--tui-workspace', type=str, default='Test_CodeBase', help='Workspace for TUI display')
@click.option('--health-check', is_flag=True, help='Perform health checks before indexing')
@click.option('--workspace-check', is_flag=True, help='Validate workspace configuration')
def index(ctx, workspace: str, config: str, workspacelist: str | None, embed_timeout: int | None, retry_list: str | None, timeout_log: str | None,
           ignore_config: str | None, ignore_override_pattern: str | None, auto_ignore_detection: bool,
           use_tree_sitter: bool, chunking_strategy: str | None, tui: bool, tui_workspace: str, health_check: bool, workspace_check: bool):
    """Index code files in workspace with enhanced features and TUI integration."""
    
    # Add health check functionality
    if health_check:
        try:
            health_service = HealthService(ctx.obj["error_handler"])
            config_service = ConfigLoaderService(ctx.obj["error_handler"])
            config = config_service.load_with_fallback(config_path=config, workspace_path=workspace, overrides=cli_overrides)
            
            print("🔍 Performing health checks...")
            health_results = health_service.check_health(config)
            
            # Check if all services are healthy
            all_healthy = all(result.get("is_healthy", False) for result in health_results)
            if not all_healthy:
                print("❌ Health checks failed:")
                for result in health_results:
                    status = "✅" if result.get("is_healthy", False) else "❌"
                    service_name = result.get("service", "unknown")
                    error = result.get("error", "No error" if result.get("is_healthy", False) else "Check configuration and service connectivity")
                    response_time = result.get("response_time_ms", 0)
                    print(f"  {status} {service_name}: {error} (response: {response_time}ms)")
                print("Health checks failed. Fix configuration and retry.")
                sys.exit(1)
            else:
                print("✅ All services are healthy. Proceeding with workspace validation...")
        
        except Exception as e:
            ctx.obj["error_handler"].log_error(
                "Failed to perform health checks",
                ErrorCategory.SYSTEM,
                ErrorSeverity.MEDIUM
            )
            print(f"Error performing health checks: {e}")
            sys.exit(1)
    
    # Add workspace validation functionality
    if workspace_check:
        try:
            workspace_service = WorkspaceService(ctx.obj["error_handler"])
            config_service = ConfigLoaderService(ctx.obj["error_handler"])
            config = config_service.load_with_fallback(config_path=config, workspace_path=workspace, overrides=cli_overrides)
            
            print("📁 Validating workspace...")
            workspace_result = workspace_service.validate_workspace(workspace, config)
            
            if not workspace_result.valid:
                print("❌ Workspace validation failed:")
                print(f"  Error: {workspace_result.error}")
                print(f"  Actionable guidance: {', '.join(workspace_result.get('actionable_guidance', []))}")
                print("Workspace validation failed. Fix configuration and retry.")
                sys.exit(1)
            else:
                print("✅ Workspace is valid. Proceeding with TUI mode check...")
        
        except Exception as e:
            ctx.obj["error_handler"].log_error(
                "Failed to validate workspace",
                ErrorCategory.FILE_SYSTEM,
                ErrorSeverity.MEDIUM
            )
            print(f"Error validating workspace: {e}")
            sys.exit(1)
    
    # Handle TUI mode
    if tui:
        from code_index.tui_integration import TUIInterface
        tui_interface = TUIInterface(error_handler)
        print("TUI mode enabled - redirecting to TUI interface...")
        # Pass all parameters to TUI interface
        result = tui_interface.start_indexing(
            workspace=workspace,
            config=config,
            workspacelist=workspacelist,
            embed_timeout=embed_timeout,
            retry_list=retry_list,
            timeout_log=timeout_log,
            ignore_config=ignore_config,
            ignore_override_pattern=ignore_override_pattern,
            auto_ignore_detection=auto_ignore_detection,
            use_tree_sitter=use_tree_sitter,
            chunking_strategy=chunking_strategy,
            tui_workspace=tui_workspace
        )
        return

    # Handle workspace list processing
    if workspacelist:
        workspaces = []
        # Initialize file processing service with error handler
        file_processor = FileProcessingService(error_handler)
        workspaces = file_processor.load_workspace_list(workspacelist, "load_workspace_list")
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
                # Process each workspace individually using NEW IndexingService
                config_service = ConfigLoaderService(error_handler)
                cfg = config_service.load_with_fallback(
                    config_path=config,
                    workspace_path=workspace_path,
                    overrides={
                    'workspace_path': Path(workspace_path).resolve().parent if Path(workspace_path).is_relative_to('.') else workspace_path
                }
                )
                
                # Use NEW IndexingService
                indexing_service = IndexingService(ctx.obj["error_handler"])
                result = indexing_service.index_workspace(workspace_path, cfg)
                total_processed += result.processed_files
                total_blocks += result.total_blocks
                total_timeouts += len(result.timed_out_files)
            except Exception as e:
                print(f"Error processing workspace {workspace_path}: {e}")
                continue
        
        print(f"\nBatch processing completed:")
        print(f"  Total workspaces processed: {len(workspaces)}")
        print(f"  Total files processed: {total_processed}")
        print(f"  Total code blocks: {total_blocks}")
        print(f"  Total timeouts: {total_timeouts}")
        return

    # Single workspace processing using NEW IndexingService
    # Initialize ConfigurationService for centralized configuration management
    config_service = ConfigLoaderService(ctx.obj["error_handler"])
    
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
    
    # Force absolute workspace path
    cfg.workspace_path = os.path.abspath(workspace)
    
    # Verify workspace exists and has files
    if not os.path.exists(cfg.workspace_path):
        print(f"ERROR: Workspace does not exist: {cfg.workspace_path}")
        return
    
    # Use NEW IndexingService for indexing
    indexing_service = IndexingService(ctx.obj["error_handler"])
    result = indexing_service.index_workspace(workspace, cfg)
    
    # Use NEW services for status display
    config_service = ConfigurationQueryService(ctx.obj["error_handler"])
    status_info = config_service.get_status(cfg, include_health=False, include_workspace=True)

    print(f"\n📊 Indexing COMPLETED")
    print("-" * 40)
    print(f"📁 Workspace: {status_info.get('workspace_info', {}).get('workspace_path', 'not configured')}")
    print(f"🔧 Configuration loaded: {status_info.get('config_with_health', False)}")
    print(f"⚙️  Response time: {status_info.get('response_time_ms', 0)} ms")
    print(f"✅ Overall status: {status_info.get('config_validation', {}).get('valid', False)}")
    print(f"📄 Files processed: {result.processed_files}")
    print(f"📊 Total blocks: {result.total_blocks}")
    print(f"📋 Timed out files: {len(result.timed_out_files)} file(s) timed out")
    print(f"⚙️  Processing time: {result.processing_time_seconds:.2f} seconds")
    print("To retry only failed files with a longer timeout, run: "
          "code-index index --workspace <...> --retry-list <timeout_log> --embed-timeout <seconds>")

@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
@click.option('--min-score', type=float, default=None, help='Minimum similarity score (0.0-1.0)')
@click.option('--max-results', type=int, default=None, help='Maximum number of results')
@click.option('--json', 'json_output', is_flag=True, help='Output results as JSON')
@click.option('--search-strategy', type=click.Choice(['text', 'similarity', 'embedding']), default=None, help='Search strategy for search operations')
@click.option('--search-min-score', type=float, default=None, help='Minimum similarity score (0.0-1.0)')
@click.option('--search-max-results', type=int, default=None, help='Maximum number of results to return')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (INFO level)')
@click.option('--debug', is_flag=True, help='Enable debug logging (DEBUG level)')
@click.pass_context
@click.argument('query')
def search(ctx, workspace: str, config: str, min_score: float, max_results: int, json_output: bool, search_strategy: str, query: str, verbose: bool, debug: bool):
    """Search indexed code using semantic similarity with NEW SearchService."""
    # Handle logging levels
    if debug:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        for handler in root_logger.handlers:
            if getattr(handler, "_code_index_cli", True):
                handler.setLevel(logging.DEBUG)
    elif verbose:
        root_logger.setLevel(logging.INFO)
        for handler in root_logger.handlers:
            if getattr(handler, "_code_index_cli", True):
                handler.setLevel(logging.INFO)
    
    # Initialize ConfigurationService for centralized configuration management
    config_service = ConfigurationQueryService(ctx.obj["error_handler"])
    
    # Prepare CLI overrides
    cli_overrides = {}
    if min_score is not None:
        cli_overrides['search_min_score'] = min_score
    if max_results is not None:
        cli_overrides['search_max_results'] = max_results
    if search_strategy is not None:
        cli_overrides['search_strategy'] = search_strategy
    
    # Load configuration with fallback and CLI overrides
    config = config_service.load_with_fallback(
        config_path=config,
        workspace_path=workspace,
        overrides=cli_overrides
    )
    
    # Use NEW SearchService with NEW search architecture
    search_service = SearchService(ctx.obj["error_handler"])
    
    # Execute search using the service
    result = search_service.search_code(query, config)
    
    if not result.is_successful():
        ctx.obj["error_handler"].log_error(
            "search failed: result not successful",
            ErrorCategory.SEARCH,
            ErrorSeverity.MEDIUM
        )
        sys.exit(1)
    
    if not result.has_matches():
        print("No results found.")
        return
    
    # Use SearchResultProcessor for result formatting
    result_processor = SearchResultProcessor(ctx.obj["error_handler"])
    
    if json_output:
        # Use SearchResultProcessor for JSON output formatting
        output = result_processor.format_json_output(result, config)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return
    
    # Use SearchResultProcessor for result display formatting
    formatted_results = result_processor.format_results(result, config)
    
    print(f"Found {result.total_found} results:")
    for i, match in enumerate(formatted_results, 1):
        result = match.get("result")
        score = match.get("score", 0.3)
        adjusted_score = match.get("adjusted_score", 0.3)
        file_path = match.get("file_path", "unknown")
        start_line = match.get("start_line", 0)
        end_line = match.get("end_line", 0)
        preview = match.get("preview", "No preview available")
        print(f"\n{i}. Score: {score:.3f} (adj {adjusted_score:.3f}")
        print(f"   File: {file_path}:{start_line}-{end_line}")
        print(f"   Preview: {preview}")

@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
@click.option('--include-health', is_flag=True, help='Include health information')
@click.option('--include-workspace', is_flag=True, help='Include workspace information')
def health(ctx, workspace: str, config: str, include_health: bool, include_workspace: bool):
    """Check system health and configuration status."""
    try:
        # Initialize services
        health_service = HealthService(ctx.obj["error_handler"])
        config_service = ConfigurationQueryService(ctx.obj["error_handler"])
        
        # Load configuration
        config = config_service.load_with_fallback(config_path=config, workspace_path=workspace)
        
        # Get status information
        status_info = config_service.get_status(config, include_health=include_health, include_workspace=include_workspace)
        
        # Display status information
        print("🔧 System Status")
        print("-" * 40)
        print(f"📊 Overall status: {status_info.get('config_validation', {}).get('valid', 'Unknown')}")
        print(f"⚙️  Response time: {status_info.get('response_time_ms', 0)} ms")
        print(f"✅ Config loaded: {status_info.get('config_with_health', 'Unknown')}")
        
        if include_health and status_info.get('config_with_health', False):
            print("\n🔍 Health Checks")
            print("-" * 40)
            health_results = health_service.check_health(config)
            for result in health_results:
                status = "✅" if result.get("is_healthy", False) else "❌"
                service_name = result.get("service", "unknown")
                error = result.get("error", "No error" if result.get("is_healthy", False) else "Check configuration and service connectivity")
                response_time = result.get("response_time_ms", 0)
                last_check = result.get("last_check_timestamp", "Unknown")
                print(f"{status} {service_name}: {error} (response: {response_time}ms, last check: {last_check})")
        
        if include_workspace and status_info.get('workspace_info', {}).get('workspace_path', 'not configured'):
            print("\n📁 Workspace Info")
            print("-" * 40)
            workspace_info = status_info.get('workspace_info', {})
            print(f"📁 Workspace: {workspace_info.get('workspace_path', 'not configured')}")
            print(f"📊 Files: {workspace_info.get('total_files', 0)}")
            print(f"🔧 Languages: {workspace_info.get('languages', 'Unknown')}")
        
        if status_info.get('error'):
            print(f"\n❌ Error: {status_info.get('error')}")
            return
        
    except Exception as e:
        ctx.obj["error_handler"].log_error(
            "Failed to check health status",
            ErrorCategory.SYSTEM,
            ErrorSeverity.MEDIUM
        )
        print(f"Error checking health status: {e}")
        sys.exit(1)

@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
@click.option('--config-only', is_flag=True, help='Only validate configuration, skip workspace validation')
def workspace(ctx, workspace: str, config: str, config_only: bool):
    """Validate workspace configuration and display workspace information."""
    try:
        # Initialize services
        workspace_service = WorkspaceService(ctx.obj["error_handler"])
        config_service = ConfigurationQueryService(ctx.obj["error_handler"])
        
        # Load configuration
        config = config_service.load_with_fallback(config_path=config, workspace_path=workspace)
        
        # Validate configuration
        validation_result = config_service.validate_config(config)
        print("🔧 Workspace Configuration")
        print("-" * 40)
        print(f"📊 Config validation: {'✅ Valid' if validation_result.valid else '❌ Invalid'}")
        if not validation_result.valid:
            print(f"❌ Error: {validation_result.error}")
            print(f"📋 Actionable guidance: {', '.join(validation_result.get('actionable_guidance', []))}")
            return
        
        if not config_only:
            # Validate workspace
            workspace_result = workspace_service.validate_workspace(workspace, config)
            print(f"📁 Workspace validation: {'✅ Valid' if workspace_result.valid else '❌ Invalid'}")
            if not workspace_result.valid:
                print(f"❌ Error: {workspace_result.error}")
                print(f"📋 Actionable guidance: {', '.join(workspace_result.get('actionable_guidance', []))}")
                return
        
        # Get workspace information
        workspace_info = workspace_service.get_workspace_info(workspace)
        
        # Display workspace information
        print("📁 Workspace Information")
        print("-" * 40)
        print(f"📁 Path: {workspace_info.get('workspace_path', 'not configured')}")
        print(f"📊 Total files: {workspace_info.get('total_files', 0)}")
        print(f"🔧 Languages: {workspace_info.get('languages', 'Unknown')}")
        print(f"📋 Project type: {workspace_info.get('project_type', 'Unknown')}")
        print(f"📁 Workspace ID: {workspace_info.get('workspace_id', 'Unknown')}")
        
        if config.workspace_path:
            print("\n📋 Configuration")
            print("-" * 40)
            print(f"🔧 Chunking strategy: {getattr(config, 'chunking_strategy', 'Unknown')}")
            print(f"🔧 Search strategy: {getattr(config, 'search_strategy', 'Unknown')}")
            print(f"🔧 Search min score: {getattr(config, 'search_min_score', 'not configured')}")
            print(f"🔧 Search max results: {getattr(config, 'search_max_results', 'not configured')}")
        
        if validation_result.details.get('response_time_ms'):
            print(f"⚙️  Response time: {validation_result.details.get('response_time_ms', 0)} ms")
        
        if validation_result.error:
            print(f"\n❌ Error: {validation_result.error}")
            return
        
    except Exception as e:
        ctx.obj["error_handler"].log_error(
            "Failed to validate workspace",
            ErrorCategory.SYSTEM,
            ErrorSeverity.MEDIUM
        )
        print(f"Error validating workspace: {e}")
        sys.exit(1)

@cli.command()
@click.option('--workspace', default='.', help='Workspace path')
@click.option('--config', default='code_index.json', help='Configuration file')
def validate_config(ctx, workspace: str, config: str):
    """Validate search configuration."""
    try:
        # Initialize services
        validation_service = SearchValidationService(ctx.obj["error_handler"])
        config_service = ConfigurationQueryService(ctx.obj["error_handler"])
        
        # Load configuration
        config = config_service.load_with_fallback(config_path=config, workspace_path=workspace)
        
        # Validate search configuration
        validation_result = validation_service.validate_search_config(config)
        
        # Display validation results
        print("🔍 Search Configuration Validation")
        print("-" * 40)
        print(f"📊 Overall status: {'✅ Valid' if validation_result.valid else '❌ Invalid'}")
        print(f"⚙️  Response time: {validation_result.details.get('response_time_ms', 0)} ms")
        
        if not validation_result.valid:
            print(f"❌ Error: {validation_result.error}")
            print(f"📋 Actionable guidance: {', '.join(validation_result.get('actionable_guidance', []))}")
            return
        
        # Display configuration details
        print("📋 Configuration Details")
        print("-" * 40)
        print(f"🔧 Search strategy: {getattr(config, 'search_strategy', 'not configured')}")
        print(f"🔧 Search min score: {getattr(config, 'search_min_score', 'not configured')}")
        print(f"🔧 Search max results: {getattr(config, 'search_max_results', 'not configured')}")
        print(f"🔧 Workspace path: {getattr(config, 'workspace_path', 'not configured')}")
        print(f"🔧 Config loaded: {config.config_with_health}")
        
        if validation_result.details.get('response_time_ms'):
            print(f"⚙️  Response time: {validation_result.details.get('response_time_ms', 0)} ms")
        
        if validation_result.error:
            print(f"\n❌ Error: {validation_result.error}")
            return
        
    except Exception as e:
        ctx.obj["error_handler"].log_error(
            "Failed to validate configuration",
            ErrorCategory.CONFIGURATION,
            ErrorSeverity.MEDIUM
        )
        print(f"Error validating configuration: {e}")
        sys.exit(1)

@cli.command()
def search_strategies():
    """Show available search strategies."""
    try:
        # Initialize SearchStrategyFactory
        strategy_factory = SearchStrategyFactory()
        
        # Get available strategies
        available_strategies = strategy_factory.get_available_strategies()
        
        # Display strategies
        print("🔍 Available Search Strategies")
        print("-" * 40)
        print("Available strategies:")
        for strategy in available_strategies:
            description = strategy_factory.get_strategy_description(strategy)
            print(f"  • {strategy}: {description}")
        
        print("\n📋 Strategy Selection")
        print("-" * 40)
        print("Use --search-strategy option with search command to select a strategy:")
        print("  • text: Fast keyword-based search")
        print("  • similarity: Vector similarity search (default)")
        print("  • embedding: Deep semantic search with embeddings")
        
        print("\n💡 Examples")
        print("-" * 40)
        print("  code-index search --search-strategy text \"error handling\" --min-score 0.4 --workspace ./src --config code_index.json")
        print("  code-index search --search-strategy similarity \"database connection\" --min-score 0.4 --workspace ./src --config code_index.json")
        print("  code-index search --search-strategy embedding \"authentication middleware\" --min-score 0.4 --workspace ./src --config code_index.json")
    except Exception as e:
        print(f"Error getting search strategies: {e}")
        sys.exit(1)

@cli.command()
def search_info():
    """Show search result processing information."""
    try:
        # Display basic search information
        print("🔍 Search Result Processing Info")
        print("-" * 40)
        print("Search processing information:")
        print("  • Min query length: 2 characters")
        print("  • Allowed characters: letters, numbers, spaces, underscores, hyphens")
        
        print("\n📋 Available Search Strategies")
        print("-" * 40)
        print("  • text: Fast keyword-based search")
        print("  • similarity: Vector similarity search (default)")
        print("  • embedding: Deep semantic search with embeddings")
        
        print("\n💡 Examples")
        print("-" * 40)
        print("  code-index search \"error handling\" --min-score 0.4 --workspace ./src --config code_index.json")
        print("  code-index search \"database connection\" --min-score 0.4 --workspace ./src --config code_index.json")
    except Exception as e:
        error_context = ErrorContext(
            component="cli",
            operation="search_info"
        )
        error_handler.handle_error(
            e,
            error_context,
            ErrorCategory.SERVICE,
            ErrorSeverity.MEDIUM
        )
        print(f"Error getting search info: {e}")
        sys.exit(1)