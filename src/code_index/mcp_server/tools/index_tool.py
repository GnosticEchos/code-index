"""
Index Tool for MCP Server

MCP wrapper for indexing functionality with parameter validation,
operation estimation, and progress reporting.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastmcp import Context
from ...config import Config
from ..core.config_manager import MCPConfigurationManager
from ..core.operation_estimator import OperationEstimator
from ..core.progress_reporter import ProgressReporter
from ...file_processing import FileProcessingService
from ...errors import ErrorHandler


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
    
    # Load configuration for operation estimation
    try:
        config_manager = MCPConfigurationManager(config or "code_index.json")
        base_config = config_manager.load_config()
        
        # Apply parameter overrides to create operation-specific config
        operation_overrides = {}
        if embed_timeout is not None:
            operation_overrides["embed_timeout_seconds"] = embed_timeout
        if chunking_strategy is not None:
            operation_overrides["chunking_strategy"] = chunking_strategy
        if use_tree_sitter is not None:
            operation_overrides["use_tree_sitter"] = use_tree_sitter
        
        # Config overrides removed due to FastMCP limitations
        
        # Apply overrides if any
        if operation_overrides:
            operation_config = config_manager.apply_overrides(base_config, operation_overrides)
        else:
            operation_config = base_config
            
    except Exception as e:
        return {
            "success": False,
            "error": "Configuration loading failed",
            "details": str(e),
            "warnings": validation_result["warnings"]
        }
    
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
            estimation = estimator.estimate_indexing_time(workspace_path, operation_config)
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
    
    # Execute indexing with progress reporting
    try:
        indexing_results = await _execute_indexing(
            workspaces_to_analyze=workspaces_to_analyze,
            operation_config=operation_config,
            workspacelist=workspacelist,
            logger=logger
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
    workspacelist: Optional[str],
    logger: logging.Logger
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
    import time
    from ...scanner import DirectoryScanner
    from ...parser import CodeParser
    from ...embedder import OllamaEmbedder
    from ...vector_store import QdrantVectorStore
    from ...cache import CacheManager
    from ...file_processing import FileProcessingService
    from ...errors import ErrorHandler
    from ...chunking import (
        LineChunkingStrategy,
        TokenChunkingStrategy,
        TreeSitterChunkingStrategy,
    )
    from requests.exceptions import ReadTimeout
    import uuid
    
    start_time = time.time()
    total_processed = 0
    total_blocks = 0
    total_timeouts = 0
    all_timeout_files = set()
    workspace_results = []
    
    # Initialize progress reporter for overall operation
    total_estimated_files = sum(len(list(Path(ws).rglob("*"))) for ws in workspaces_to_analyze if Path(ws).exists())
    progress_reporter = ProgressReporter(
        total_items=total_estimated_files,
        operation_type="indexing",
        update_interval=max(1, total_estimated_files // 100)  # Update every 1% or at least every file
    )
    
    # Process each workspace
    for workspace_idx, workspace_path in enumerate(workspaces_to_analyze):
        workspace_start_time = time.time()
        logger.info(f"Processing workspace {workspace_idx + 1}/{len(workspaces_to_analyze)}: {workspace_path}")
        
        try:
            # Update configuration for this workspace
            workspace_config = Config()
            for key, value in vars(operation_config).items():
                setattr(workspace_config, key, value)
            workspace_config.workspace_path = workspace_path
            
            # Determine chunking strategy
            strategy_name = getattr(workspace_config, "chunking_strategy", "lines")
            if getattr(workspace_config, "use_tree_sitter", False):
                strategy_name = "treesitter"
            
            if strategy_name == "treesitter":
                chunking_strategy_impl = TreeSitterChunkingStrategy(workspace_config)
            elif strategy_name == "tokens":
                chunking_strategy_impl = TokenChunkingStrategy(workspace_config)
            else:
                chunking_strategy_impl = LineChunkingStrategy(workspace_config)
            
            # Initialize components
            scanner = DirectoryScanner(workspace_config)
            parser = CodeParser(workspace_config, chunking_strategy_impl)
            embedder = OllamaEmbedder(workspace_config)
            vector_store = QdrantVectorStore(workspace_config)
            cache_manager = CacheManager(workspace_config.workspace_path, workspace_config)
            
            # Validate configuration
            logger.info("Validating configuration...")
            validation_result = embedder.validate_configuration()
            if not validation_result["valid"]:
                raise ValueError(f"Configuration validation failed: {validation_result['error']}")
            
            # Initialize vector store
            logger.info("Initializing vector store...")
            vector_store.initialize()
            
            # Scan directory for files
            logger.info(f"Scanning directory: {workspace_config.workspace_path}")
            scanned_paths, skipped_count = scanner.scan_directory()
            file_paths = scanned_paths
            logger.info(f"Found {len(file_paths)} files to process ({skipped_count} skipped)")
            
            if not file_paths:
                logger.warning(f"No files found to process in workspace: {workspace_path}")
                workspace_results.append({
                    "workspace": workspace_path,
                    "processed_files": 0,
                    "total_blocks": 0,
                    "timeout_files": 0,
                    "processing_time": time.time() - workspace_start_time,
                    "status": "completed_empty"
                })
                continue
            
            # Process files with progress reporting
            processed_count = 0
            blocks_count = 0
            timeout_files = set()
            
            for file_idx, file_path in enumerate(file_paths):
                rel_path = os.path.normpath(os.path.relpath(file_path, workspace_config.workspace_path))
                
                # Update progress
                await progress_reporter.update_progress(
                    completed_items=total_processed + processed_count,
                    current_item=f"Processing {rel_path}"
                )
                
                try:
                    # Check if file has changed
                    file_processor = FileProcessingService(ErrorHandler("mcp_index"))
                    current_hash = file_processor.get_file_hash(file_path)
                    cached_hash = cache_manager.get_hash(file_path)
                    if current_hash == cached_hash:
                        # File hasn't changed, skip processing
                        continue
                    
                    # Parse file into blocks
                    blocks = parser.parse_file(file_path)
                    if not blocks:
                        cache_manager.update_hash(file_path, current_hash)
                        continue
                    
                    # Generate embeddings
                    texts = [block.content for block in blocks if block.content.strip()]
                    if not texts:
                        cache_manager.update_hash(file_path, current_hash)
                        continue
                    
                    # Batch embeddings for efficiency
                    batch_size = workspace_config.batch_segment_threshold
                    all_embeddings = []
                    embedding_failed = False
                    
                    for i in range(0, len(texts), batch_size):
                        batch_texts = texts[i:i + batch_size]
                        try:
                            embedding_response = embedder.create_embeddings(batch_texts)
                            all_embeddings.extend(embedding_response["embeddings"])
                        except ReadTimeout:
                            timeout_files.add(rel_path)
                            embedding_failed = True
                            logger.warning(f"Timeout: Embedding request timed out for {rel_path}")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to embed batch for {rel_path}: {e}")
                            embedding_failed = True
                            break
                    
                    if embedding_failed or (len(all_embeddings) < len(texts) and len(all_embeddings) == 0):
                        # Do not cache as processed to allow retry
                        continue
                    
                    # Prepare points for vector store
                    points = []
                    for i, block in enumerate(blocks):
                        if i >= len(all_embeddings):
                            break
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
                            timeout_files.add(rel_path)
                            logger.warning(f"Timeout: Upsert timed out for {rel_path}")
                            continue
                        else:
                            logger.warning(f"Failed to upsert points for {rel_path}: {e}")
                            continue
                    
                    # Update cache and counters
                    cache_manager.update_hash(file_path, current_hash)
                    processed_count += 1
                    blocks_count += len(blocks)
                    
                except Exception as e:
                    logger.warning(f"Failed to process file {rel_path}: {e}")
                    continue
            
            # Write timeout log if any
            if timeout_files and hasattr(workspace_config, 'timeout_log_path') and workspace_config.timeout_log_path:
                timeout_log_path = workspace_config.timeout_log_path
                if not os.path.isabs(timeout_log_path):
                    timeout_log_path = os.path.join(workspace_config.workspace_path, timeout_log_path)
                
                try:
                    with open(timeout_log_path, 'w') as f:
                        for timeout_file in sorted(timeout_files):
                            f.write(f"{timeout_file}\n")
                    logger.info(f"Wrote timeout log to: {timeout_log_path}")
                except Exception as e:
                    logger.warning(f"Failed to write timeout log: {e}")
            
            # Record workspace results
            workspace_processing_time = time.time() - workspace_start_time
            workspace_results.append({
                "workspace": workspace_path,
                "processed_files": processed_count,
                "total_blocks": blocks_count,
                "timeout_files": len(timeout_files),
                "processing_time": workspace_processing_time,
                "status": "completed"
            })
            
            # Update totals
            total_processed += processed_count
            total_blocks += blocks_count
            total_timeouts += len(timeout_files)
            all_timeout_files.update(timeout_files)
            
            logger.info(f"Workspace {workspace_path} completed: {processed_count} files, {blocks_count} blocks, {len(timeout_files)} timeouts")
            
        except Exception as e:
            logger.error(f"Failed to process workspace {workspace_path}: {e}")
            workspace_results.append({
                "workspace": workspace_path,
                "processed_files": 0,
                "total_blocks": 0,
                "timeout_files": 0,
                "processing_time": time.time() - workspace_start_time,
                "status": "failed",
                "error": str(e)
            })
    
    # Calculate final results
    total_processing_time = time.time() - start_time
    
    # Generate retry guidance if there were timeouts
    retry_guidance = []
    if all_timeout_files:
        retry_guidance.append(f"To retry {len(all_timeout_files)} failed files with longer timeout:")
        retry_guidance.append("1. Create a retry list file with the timeout files")
        retry_guidance.append("2. Use: code-index index --retry-list <file> --embed-timeout <seconds>")
        if workspacelist:
            retry_guidance.append(f"3. Or use workspacelist: --workspacelist {workspacelist} --embed-timeout <seconds>")
    
    return {
        "success": True,
        "message": f"Indexing completed: {total_processed} files processed",
        "processed_files": total_processed,
        "total_blocks": total_blocks,
        "timeout_files": list(all_timeout_files),
        "timeout_count": total_timeouts,
        "processing_time": total_processing_time,
        "workspaces_processed": len(workspaces_to_analyze),
        "workspace_results": workspace_results,
        "retry_guidance": retry_guidance,
        "warnings": []
    }