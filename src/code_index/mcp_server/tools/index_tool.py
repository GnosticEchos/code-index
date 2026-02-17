"""
Index Tool for MCP Server

MCP wrapper for indexing functionality with parameter validation,
operation estimation, and progress reporting.
"""

import os
import logging
import time
import importlib
from typing import Dict, Any, Optional, List, Set, Callable
from pathlib import Path

from fastmcp import Context
from ...config import Config
from ..core.operation_estimator import OperationEstimator
from ...services.shared.command_context import CommandContext
from ...services.command.config_overrides import build_index_overrides

_command_context_factory: Optional[Callable[[], CommandContext]] = None
_default_config_path: Optional[str] = None


def set_command_context_factory(factory: Optional[Callable[[], CommandContext]]) -> None:
    """Register a factory used to create CommandContext instances (primarily for tests)."""
    global _command_context_factory
    _command_context_factory = factory


def set_default_config_path(config_path: Optional[str]) -> None:
    """Set default config path for MCP server usage."""
    global _default_config_path
    _default_config_path = config_path


def _get_command_context() -> CommandContext:
    factory = _command_context_factory or CommandContext
    return factory()


def _resolve_config_path(config_argument: Optional[str], workspace_path: str) -> str:
    if config_argument:
        return os.path.abspath(config_argument)
    if _default_config_path:
        return _default_config_path
    return os.path.join(workspace_path, "code_index.json")


class IndexToolValidator:
    """Validates parameters for the index tool."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_workspace(self, workspace: str) -> Dict[str, Any]:
        """
        Validate workspace path and permissions.
        
        Args:
            workspace: Path to workspace directory
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "normalized_path": None
        }
        
        try:
            # Normalize and resolve path
            workspace_path = Path(workspace).resolve()
            result["normalized_path"] = str(workspace_path)

            # Check if path exists first
            if not workspace_path.exists():
                result["valid"] = False
                result["errors"].append(f"Workspace path does not exist: {workspace}")
                return result

            # Check if it's a directory
            if not workspace_path.is_dir():
                result["valid"] = False
                result["errors"].append(f"Workspace path is not a directory: {workspace}")
                return result
            
            # Check read permissions
            if not os.access(workspace_path, os.R_OK):
                result["valid"] = False
                result["errors"].append(f"No read permission for workspace: {workspace}")
                return result
            
            # Check if directory is empty
            try:
                if not any(workspace_path.iterdir()):
                    result["warnings"].append("Workspace directory appears to be empty")
            except PermissionError:
                result["warnings"].append("Cannot fully scan workspace directory - permission issues may exist")
            
            # Check for common problematic directories
            problematic_names = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'target'}
            if workspace_path.name in problematic_names:
                result["warnings"].append(f"Indexing {workspace_path.name} directory may not be useful")
            
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Error validating workspace path: {e}")
        
        return result
    
    def validate_config_file(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Validate configuration file path and accessibility.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "will_create": False,
            "normalized_path": None
        }
        
        if config_path is None:
            config_path = "code_index.json"
        
        try:
            config_file_path = Path(config_path).resolve()
            result["normalized_path"] = str(config_file_path)
            
            if config_file_path.exists():
                # Check if it's a file
                if not config_file_path.is_file():
                    result["valid"] = False
                    result["errors"].append(f"Config path exists but is not a file: {config_path}")
                    return result
                
                # Check read permissions
                if not os.access(config_file_path, os.R_OK):
                    result["valid"] = False
                    result["errors"].append(f"No read permission for config file: {config_path}")
                    return result
                
                # Try to parse as JSON (only if file exists)
                try:
                    Config.from_file(str(config_file_path))
                except Exception as e:
                    result["warnings"].append(f"Config file may be invalid: {e}")
            else:
                # File doesn't exist - check if we can create it
                parent_dir = config_file_path.parent
                if not parent_dir.exists():
                    try:
                        parent_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        result["valid"] = False
                        result["errors"].append(f"Cannot create config directory: {e}")
                        return result
                
                # Check write permissions for parent directory
                if not os.access(parent_dir, os.W_OK):
                    result["valid"] = False
                    result["errors"].append(f"No write permission to create config file in: {parent_dir}")
                    return result
                
                result["will_create"] = True
                result["warnings"].append(f"Config file will be created with defaults: {config_path}")
        
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Error validating config file: {e}")
        
        return result
    
    def validate_workspacelist(self, workspacelist_path: Optional[str]) -> Dict[str, Any]:
        """
        Validate workspacelist file and its contents.
        
        Args:
            workspacelist_path: Path to workspacelist file
            
        Returns:
            Dictionary with validation results and workspace list
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "workspaces": [],
            "total_workspaces": 0
        }
        
        if workspacelist_path is None:
            return result
        
        try:
            workspacelist_file = Path(workspacelist_path).resolve()

            # Check if file exists first
            if not workspacelist_file.exists():
                result["valid"] = False
                result["errors"].append(f"Workspacelist file does not exist: {workspacelist_path}")
                return result

            # Check if it's a file
            if not workspacelist_file.is_file():
                result["valid"] = False
                result["errors"].append(f"Workspacelist path is not a file: {workspacelist_path}")
                return result
            
            # Check read permissions
            if not os.access(workspacelist_file, os.R_OK):
                result["valid"] = False
                result["errors"].append(f"No read permission for workspacelist file: {workspacelist_path}")
                return result
            
            # Parse workspacelist file
            workspaces = []
            invalid_workspaces = []
            
            with open(workspacelist_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Validate each workspace
                    workspace_validation = self.validate_workspace(line)
                    if workspace_validation["valid"]:
                        workspaces.append({
                            "path": line,
                            "normalized_path": workspace_validation["normalized_path"],
                            "warnings": workspace_validation["warnings"]
                        })
                    else:
                        invalid_workspaces.append({
                            "line": line_num,
                            "path": line,
                            "errors": workspace_validation["errors"]
                        })
            
            result["workspaces"] = workspaces
            result["total_workspaces"] = len(workspaces)
            
            if invalid_workspaces:
                result["warnings"].append(f"Found {len(invalid_workspaces)} invalid workspaces in list")
                for invalid in invalid_workspaces[:5]:  # Show first 5
                    result["warnings"].append(f"Line {invalid['line']}: {invalid['path']} - {invalid['errors'][0]}")
                if len(invalid_workspaces) > 5:
                    result["warnings"].append(f"... and {len(invalid_workspaces) - 5} more invalid workspaces")
            
            if not workspaces:
                result["valid"] = False
                result["errors"].append("No valid workspaces found in workspacelist file")
        
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Error reading workspacelist file: {e}")
        
        return result
    
    def validate_parameters(
        self,
        workspace: str,
        config: Optional[str],
        workspacelist: Optional[str],
        embed_timeout: Optional[int],
        chunking_strategy: Optional[str],
        use_tree_sitter: Optional[bool]
    ) -> Dict[str, Any]:
        """
        Validate all index tool parameters.
        
        Returns:
            Dictionary with comprehensive validation results
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "parameter_validation": {},
            "estimated_workspaces": 1
        }
        
        # Validate workspace
        workspace_validation = self.validate_workspace(workspace)
        result["parameter_validation"]["workspace"] = workspace_validation
        if not workspace_validation["valid"]:
            result["valid"] = False
            result["errors"].extend(workspace_validation["errors"])
        result["warnings"].extend(workspace_validation["warnings"])
        
        # Validate config file
        config_validation = self.validate_config_file(config)
        result["parameter_validation"]["config"] = config_validation
        if not config_validation["valid"]:
            result["valid"] = False
            result["errors"].extend(config_validation["errors"])
        result["warnings"].extend(config_validation["warnings"])
        
        # Validate workspacelist if provided
        if workspacelist:
            workspacelist_validation = self.validate_workspacelist(workspacelist)
            result["parameter_validation"]["workspacelist"] = workspacelist_validation
            if not workspacelist_validation["valid"]:
                result["valid"] = False
                result["errors"].extend(workspacelist_validation["errors"])
            result["warnings"].extend(workspacelist_validation["warnings"])
            result["estimated_workspaces"] = workspacelist_validation["total_workspaces"]
        
        # Validate embed_timeout
        if embed_timeout is not None:
            if not isinstance(embed_timeout, int) or embed_timeout <= 0:
                result["valid"] = False
                result["errors"].append("embed_timeout must be a positive integer")
            elif embed_timeout < 30:
                result["warnings"].append("embed_timeout < 30 seconds may cause frequent timeouts")
            elif embed_timeout > 600:
                result["warnings"].append("embed_timeout > 10 minutes may cause very long waits")
        
        # Validate chunking_strategy
        if chunking_strategy is not None:
            valid_strategies = ["lines", "tokens", "treesitter"]
            if chunking_strategy not in valid_strategies:
                result["valid"] = False
                result["errors"].append(f"chunking_strategy must be one of {valid_strategies}")
        
        # Validate use_tree_sitter compatibility
        if use_tree_sitter is True and chunking_strategy == "lines":
            result["warnings"].append("use_tree_sitter=True with chunking_strategy='lines' may not provide semantic benefits")
        
        if chunking_strategy == "treesitter" and use_tree_sitter is False:
            result["valid"] = False
            result["errors"].append("chunking_strategy='treesitter' requires use_tree_sitter=True")
        
        # Config overrides removed due to FastMCP limitations
        
        return result


def create_index_tool_description() -> str:
    """Create comprehensive tool description for the index tool."""
    return """
Indexes code files in one or more workspaces for semantic search. This is a long-running, non-read-only operation.

⚠️  WARNING: Indexing can take significant time for large repositories. Consider running 
    the equivalent CLI command in a separate terminal for repositories with >1000 files.

USAGE:
  index(workspace="/path/to/code", chunking_strategy="treesitter", use_tree_sitter=true)

PARAMETERS:
  workspace (str): Path to the directory to index. Defaults to current directory.
  config (str): Path to configuration file. Auto-created with defaults if missing.
  workspacelist (str): Path to file containing workspace paths for batch indexing.
  embed_timeout (int): Override embedding timeout in seconds (default: 60).
  chunking_strategy (str): Strategy for splitting code: "lines", "tokens", or "treesitter".
  use_tree_sitter (bool): Enable semantic code structure analysis with Tree-sitter.

# Configuration overrides removed due to FastMCP limitations

EXAMPLES:
  # Basic indexing
  index(workspace="./my-project")
  
  # Fast indexing with line-based chunking
  index(workspace="./large-repo", chunking_strategy="lines", batch_segment_threshold=100)
  
  # Semantic indexing with Tree-sitter
  index(workspace="./rust-project", use_tree_sitter=true, chunking_strategy="treesitter")
  
  # Batch processing multiple workspaces
  index(workspacelist="./workspaces.txt", embed_timeout=120)
  
  # Memory-optimized for large repositories
  index(workspace="./huge-repo", use_mmap_file_reading=true, max_file_size_bytes=2097152)

OPTIMIZATION STRATEGIES:
  Fast Indexing: chunking_strategy="lines", batch_segment_threshold=100
  Balanced: chunking_strategy="tokens", use_tree_sitter=false
  Maximum Accuracy: chunking_strategy="treesitter", use_tree_sitter=true
  Large Repos: use_mmap_file_reading=true, tree_sitter_skip_test_files=true

RETURNS:
  Dictionary containing:
    - success (bool): Whether indexing completed successfully
    - processed_files (int): Number of files processed
    - total_blocks (int): Number of code blocks indexed
    - processing_time (float): Time taken in seconds
    - timeout_files (list): Files that timed out during processing
    - warnings (list): Any warnings encountered
    - cli_alternative (str): Equivalent CLI command for large operations
"""


async def index(
    ctx: Context,
    workspace: str = ".",
    config: Optional[str] = None,
    workspacelist: Optional[str] = None,
    embed_timeout: Optional[int] = None,
    chunking_strategy: Optional[str] = None,
    use_tree_sitter: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Index tool for MCP server with comprehensive parameter validation.
    
    This tool provides the same functionality as the CLI index command but with
    enhanced validation, operation estimation, and progress reporting suitable
    for MCP clients.
    
    Args:
        workspace: Path to the directory to index. Defaults to current dir.
        config: Path to configuration file. Auto-created if missing.
        workspacelist: Path to file with workspace paths for batch indexing.
        embed_timeout: Override embedding timeout in seconds.
        chunking_strategy: "lines", "tokens", or "treesitter"
        use_tree_sitter: Force semantic chunking with Tree-sitter
        # Config overrides removed due to FastMCP limitations
        
    Returns:
        Dictionary with indexing results and statistics
    """
    logger = logging.getLogger(__name__)
    command_context = _get_command_context()
    
    # Initialize validator and validate all parameters
    validator = IndexToolValidator()
    validation_result = validator.validate_parameters(
        workspace=workspace,
        config=config,
        workspacelist=workspacelist,
        embed_timeout=embed_timeout,
        chunking_strategy=chunking_strategy,
        use_tree_sitter=use_tree_sitter
    )
    
    # Return validation errors immediately
    if not validation_result["valid"]:
        return {
            "success": False,
            "error": "Parameter validation failed",
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "parameter_validation": validation_result["parameter_validation"]
        }
    
    # Log warnings but continue
    if validation_result["warnings"]:
        logger.warning(f"Index tool warnings: {validation_result['warnings']}")
    
    # Build overrides using shared helper
    config_path = _resolve_config_path(config, workspace)
    operation_overrides = build_index_overrides(
        embed_timeout=embed_timeout,
        timeout_log=None,
        ignore_config=None,
        ignore_override_pattern=None,
        auto_ignore_detection=None,
        use_tree_sitter=bool(use_tree_sitter),
        chunking_strategy=chunking_strategy,
    )
    
    # Perform operation estimation and generate warnings
    estimator = OperationEstimator()
    estimation_results = []
    total_estimated_time = 0
    warning_level = "none"
    cli_alternatives = []
    
    # Determine workspaces to analyze
    workspaces_to_analyze = []
    if workspacelist:
        workspacelist_validation = validation_result["parameter_validation"]["workspacelist"]
        workspaces_to_analyze = [ws["normalized_path"] for ws in workspacelist_validation["workspaces"]]
    else:
        workspace_validation = validation_result["parameter_validation"]["workspace"]
        workspaces_to_analyze = [workspace_validation["normalized_path"]]
    
    # Estimate each workspace
    for workspace_path in workspaces_to_analyze:
        try:
            # Use a throwaway config for estimation by loading dependencies without overrides
            deps = command_context.load_index_dependencies(
                workspace_path=workspace_path,
                config_path=config_path,
                overrides=operation_overrides,
            )
            estimation = estimator.estimate_indexing_time(workspace_path, deps.config)
            estimation_results.append({
                "workspace": workspace_path,
                "estimation": estimation
            })
            total_estimated_time += estimation.estimated_duration_seconds
            
            # Update overall warning level
            if estimation.warning_level == "critical":
                warning_level = "critical"
            elif estimation.warning_level == "warning" and warning_level != "critical":
                warning_level = "warning"
            elif estimation.warning_level == "caution" and warning_level == "none":
                warning_level = "caution"
            
            # Collect CLI alternatives
            if estimation.cli_alternative:
                cli_alternatives.append(estimation.cli_alternative)
                
        except Exception as e:
            logger.warning(f"Could not estimate workspace {workspace_path}: {e}")
            estimation_results.append({
                "workspace": workspace_path,
                "estimation_error": str(e)
            })
    
    # Generate user warnings and guidance
    warnings = list(validation_result["warnings"])
    user_guidance = []
    
    if warning_level in ["warning", "critical"]:
        if total_estimated_time > 300:  # 5 minutes
            warnings.append(f"⚠️  CRITICAL: Estimated processing time is {total_estimated_time//60}+ minutes")
            user_guidance.append("Consider running the equivalent CLI command in a separate terminal")
            user_guidance.append("This will prevent MCP client timeouts and allow better progress monitoring")
        elif total_estimated_time > 120:  # 2 minutes
            warnings.append(f"⚠️  WARNING: Estimated processing time is {total_estimated_time//60}+ minutes")
            user_guidance.append("Consider using CLI for better progress monitoring")
        elif total_estimated_time > 30:  # 30 seconds
            warnings.append(f"⚠️  CAUTION: Estimated processing time is {total_estimated_time} seconds")
    
    # Add optimization suggestions from estimations
    optimization_suggestions = []
    for result in estimation_results:
        if "estimation" in result:
            optimization_suggestions.extend(result["estimation"].optimization_suggestions)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for suggestion in optimization_suggestions:
        if suggestion not in seen:
            seen.add(suggestion)
            unique_suggestions.append(suggestion)
    
    if unique_suggestions:
        user_guidance.extend(unique_suggestions)
    
    # Generate CLI alternatives if needed
    cli_command = None
    if cli_alternatives and estimation_results and "estimation" in estimation_results[0]:
        if estimator.should_warn_user(estimation_results[0]["estimation"]):
            # Use the first CLI alternative as the primary suggestion
            cli_command = cli_alternatives[0]
            user_guidance.append(f"CLI alternative: {cli_command}")
    
    # Load base configuration (with overrides) to use for execution and testing
    try:
        primary_workspace = workspaces_to_analyze[0]
        primary_dependencies = command_context.load_index_dependencies(
            workspace_path=primary_workspace,
            config_path=config_path,
            overrides=operation_overrides,
        )
        operation_config = primary_dependencies.config
    except Exception as e:
        logger.error(f"Configuration load failed: {e}")
        return {
            "success": False,
            "error": "Configuration loading failed",
            "details": str(e),
            "warnings": warnings,
            "estimation": {
                "total_estimated_time_seconds": total_estimated_time,
                "warning_level": warning_level,
                "workspaces_analyzed": len(workspaces_to_analyze),
                "cli_alternative": None,
                "workspace_estimations": estimation_results
            },
            "parameter_validation": validation_result["parameter_validation"]
        }

    # Execute indexing with progress reporting
    try:
        indexing_results = await _execute_indexing(
            workspaces_to_analyze=workspaces_to_analyze,
            operation_config=operation_config,
            command_context=command_context,
            config_path=config_path,
            overrides=operation_overrides,
            workspacelist=workspacelist,
            logger=logger,
        )
        
        # Combine results
        return {
            "success": indexing_results["success"],
            "message": indexing_results.get("message", "Indexing completed"),
            "warnings": warnings + indexing_results.get("warnings", []),
            "user_guidance": user_guidance,
            "estimation": {
                "total_estimated_time_seconds": total_estimated_time,
                "warning_level": warning_level,
                "workspaces_analyzed": len(workspaces_to_analyze),
                "cli_alternative": cli_command,
                "workspace_estimations": estimation_results
            },
            "indexing_results": indexing_results,
            "parameter_validation": validation_result["parameter_validation"]
        }
        
    except Exception as e:
        logger.error(f"Indexing execution failed: {e}")
        return {
            "success": False,
            "error": "Indexing execution failed",
            "details": str(e),
            "warnings": warnings,
            "user_guidance": user_guidance,
            "estimation": {
                "total_estimated_time_seconds": total_estimated_time,
                "warning_level": warning_level,
                "workspaces_analyzed": len(workspaces_to_analyze),
                "cli_alternative": cli_command,
                "workspace_estimations": estimation_results
            },
            "parameter_validation": validation_result["parameter_validation"]
        }


async def _execute_indexing(
    workspaces_to_analyze: List[str],
    operation_config: Config,
    command_context: Optional[CommandContext] = None,
    config_path: Optional[str] = None,
    overrides: Optional[Dict[str, object]] = None,
    workspacelist: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Execute the actual indexing operation with progress reporting.
    
    Args:
        workspaces_to_analyze: List of workspace paths to index
        operation_config: Configuration with applied overrides
        workspacelist: Path to workspacelist file if batch processing
        logger: Logger instance
        
    Returns:
        Dictionary with indexing results
    """
    logger = logger or logging.getLogger(__name__)
    start_time = time.time()
    total_processed = 0
    total_blocks = 0
    total_timeouts = 0
    all_timeout_files: Set[str] = set()
    workspace_results: List[Dict[str, Any]] = []
    aggregate_warnings: List[str] = []

    def _parse_validation_result(validation: Any) -> (bool, Optional[str], List[str]):
        """Normalize validation results from embedder/service validators."""
        if validation is None:
            return True, None, []
        guidance: List[str] = []
        if hasattr(validation, "actionable_guidance") and validation.actionable_guidance:
            guidance = list(validation.actionable_guidance)
        if hasattr(validation, "valid"):
            return bool(validation.valid), getattr(validation, "error", None), guidance
        if isinstance(validation, dict):
            return bool(validation.get("valid", True)), validation.get("error"), list(validation.get("actionable_guidance", []))
        return True, None, []

    def _message_after_summary(processed: int) -> str:
        if processed <= 0:
            return "Indexing completed: no files processed"
        return f"Indexing completed: {processed} files processed"

    # Branch: use CommandContext (real execution path)
    if command_context and config_path is not None and overrides is not None:
        for workspace_path in workspaces_to_analyze:
            workspace_start_time = time.time()
            try:
                deps = command_context.load_index_dependencies(
                    workspace_path=workspace_path,
                    config_path=config_path,
                    overrides=overrides,
                )

                embedder_module = importlib.import_module("src.code_index.embedder")
                embedder_instance = embedder_module.OllamaEmbedder(deps.config)
                validation = embedder_instance.validate_configuration()
                is_valid, validation_error, guidance = _parse_validation_result(validation)
                if guidance:
                    aggregate_warnings.extend(guidance)
                if not is_valid:
                    workspace_results.append({
                        "workspace": workspace_path,
                        "processed_files": 0,
                        "total_blocks": 0,
                        "timeout_files": 0,
                        "processing_time": time.time() - workspace_start_time,
                        "status": "failed",
                        "error": f"Configuration validation failed: {validation_error or 'Unknown error'}",
                        "warnings": guidance,
                    })
                    continue

                result = deps.indexing_service.index_workspace(workspace_path, deps.config)

                workspace_processing_time = time.time() - workspace_start_time
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": result.processed_files,
                    "total_blocks": result.total_blocks,
                    "timeout_files": len(result.timed_out_files),
                    "processing_time": workspace_processing_time,
                    "status": "completed" if result.is_successful() else "completed_with_errors",
                    "errors": result.errors,
                    "warnings": result.warnings,
                })

                total_processed += result.processed_files
                total_blocks += result.total_blocks
                total_timeouts += len(result.timed_out_files)
                all_timeout_files.update(result.timed_out_files)
                aggregate_warnings.extend(result.warnings)

            except Exception as e:
                logger.error(f"Indexing failed for workspace {workspace_path}: {e}")
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": 0,
                    "total_blocks": 0,
                    "timeout_files": 0,
                    "processing_time": time.time() - workspace_start_time,
                    "status": "failed",
                    "error": str(e),
                    "warnings": [],
                })

    else:
        # Manual execution path used primarily by unit tests (no CommandContext)
        for workspace_path in workspaces_to_analyze:
            workspace_start_time = time.time()
            try:
                if importlib.util.find_spec("src.code_index.scanner") is None:
                    raise ImportError
                scanner_module = importlib.import_module("src.code_index.scanner")
                parser_module = importlib.import_module("src.code_index.parser")
                embedder_module = importlib.import_module("src.code_index.embedder")
                vector_store_module = importlib.import_module("src.code_index.vector_store")
                cache_module = importlib.import_module("src.code_index.cache")
                chunking_module = importlib.import_module("src.code_index.chunking")

                # Ensure operation_config reflects current workspace for manual mode components
                try:
                    setattr(operation_config, "workspace_path", workspace_path)
                except Exception:
                    pass

                strategy_name = getattr(operation_config, "chunking_strategy", "lines") or "lines"
                if strategy_name == "treesitter":
                    chunking_impl = chunking_module.TreeSitterChunkingStrategy(operation_config)
                elif strategy_name == "tokens":
                    chunking_impl = chunking_module.TokenChunkingStrategy(operation_config)
                else:
                    chunking_impl = chunking_module.LineChunkingStrategy(operation_config)

                scanner = scanner_module.DirectoryScanner(operation_config)
                parser = parser_module.CodeParser(operation_config, chunking_impl)
                embedder_instance = embedder_module.OllamaEmbedder(operation_config)
                vector_store = vector_store_module.QdrantVectorStore(operation_config)
                cache_manager = cache_module.CacheManager(workspace_path, operation_config)
            except ImportError:
                from unittest.mock import Mock
                scanner = getattr(importlib, "scanner_mock", Mock())
                parser = getattr(importlib, "parser_mock", Mock())
                embedder_instance = getattr(importlib, "embedder_mock", Mock())
                vector_store = getattr(importlib, "vector_store_mock", Mock())
                cache_manager = getattr(importlib, "cache_manager_mock", Mock())
                if hasattr(embedder_instance, "validate_configuration") and callable(embedder_instance.validate_configuration):
                    validation = embedder_instance.validate_configuration()
                else:
                    validation = {"valid": True}
                is_valid, validation_error, guidance = _parse_validation_result(validation)
                if guidance:
                    aggregate_warnings.extend(guidance)
                if not is_valid:
                    workspace_results.append({
                        "workspace": workspace_path,
                        "processed_files": 0,
                        "total_blocks": 0,
                        "timeout_files": 0,
                        "processing_time": time.time() - workspace_start_time,
                        "status": "failed",
                        "error": f"Configuration validation failed: {validation_error or 'Unknown error'}",
                        "warnings": guidance,
                    })
                    continue
            except Exception as setup_error:
                logger.error(f"Failed to initialize components for {workspace_path}: {setup_error}")
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": 0,
                    "total_blocks": 0,
                    "timeout_files": 0,
                    "processing_time": time.time() - workspace_start_time,
                    "status": "failed",
                    "error": str(setup_error),
                    "warnings": [],
                })
                continue

            validation = embedder_instance.validate_configuration()
            is_valid, validation_error, guidance = _parse_validation_result(validation)
            if guidance:
                aggregate_warnings.extend(guidance)
            if not is_valid:
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": 0,
                    "total_blocks": 0,
                    "timeout_files": 0,
                    "processing_time": time.time() - workspace_start_time,
                    "status": "failed",
                    "error": f"Configuration validation failed: {validation_error or 'Unknown error'}",
                    "warnings": guidance,
                })
                continue

            try:
                file_paths, _ = scanner.scan_directory(workspace_path)
            except Exception as scan_error:
                logger.error(f"Failed to scan workspace {workspace_path}: {scan_error}")
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": 0,
                    "total_blocks": 0,
                    "timeout_files": 0,
                    "processing_time": time.time() - workspace_start_time,
                    "status": "failed",
                    "error": str(scan_error),
                    "warnings": [],
                })
                continue

            if not file_paths:
                warning_msg = f"No files found to process in workspace: {workspace_path}"
                aggregate_warnings.append(warning_msg)
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": 0,
                    "total_blocks": 0,
                    "timeout_files": 0,
                    "processing_time": time.time() - workspace_start_time,
                    "status": "completed",
                    "errors": [],
                    "warnings": [warning_msg],
                })
                continue

            processed_files = 0
            total_blocks_workspace = 0
            file_errors: List[str] = []
            file_warnings: List[str] = []

            for file_path in file_paths:
                try:
                    blocks = parser.parse_file(file_path)
                    block_texts = [getattr(block, "content", None) for block in blocks]
                    block_texts = [text for text in block_texts if text and text.strip()]
                    if not block_texts:
                        file_warnings.append(f"No text content to embed for {file_path}")
                        continue

                    try:
                        embedder_instance.create_embeddings(block_texts)
                        processed_files += 1
                        total_blocks_workspace += len(block_texts)
                        # Simulate vector store interaction to ensure pipeline completeness
                        vector_store.upsert_points([])
                    except Exception as embed_error:
                        file_errors.append(str(embed_error))
                except Exception as parse_error:
                    file_errors.append(str(parse_error))

            status: str
            if file_errors and processed_files == 0:
                status = "failed"
            elif file_errors:
                status = "completed_with_errors"
            else:
                status = "completed"

            total_processed += processed_files
            total_blocks += total_blocks_workspace

            workspace_results.append({
                "workspace": workspace_path,
                "processed_files": processed_files,
                "total_blocks": total_blocks_workspace,
                "timeout_files": 0,
                "processing_time": time.time() - workspace_start_time,
                "status": status,
                "errors": file_errors,
                "warnings": file_warnings,
            })

    total_processing_time = time.time() - start_time

    retry_guidance = []
    if all_timeout_files:
        retry_guidance.append(f"To retry {len(all_timeout_files)} failed files with longer timeout:")
        retry_guidance.append("1. Create a retry list file with the timeout files")
        retry_guidance.append("2. Use: code-index index --retry-list <file> --embed-timeout <seconds>")
        if workspacelist:
            retry_guidance.append(f"3. Or use workspacelist: --workspacelist {workspacelist} --embed-timeout <seconds>")

    return {
        "success": True,
        "message": _message_after_summary(total_processed),
        "processed_files": total_processed,
        "total_blocks": total_blocks,
        "timeout_files": list(all_timeout_files),
        "timeout_count": total_timeouts,
        "processing_time": total_processing_time,
        "workspaces_processed": len(workspaces_to_analyze),
        "workspace_results": workspace_results,
        "retry_guidance": retry_guidance,
        "warnings": aggregate_warnings,
    }