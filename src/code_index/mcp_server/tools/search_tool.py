"""MCP search tool leveraging shared services."""

import os
import logging
from typing import List, Dict, Any, Optional, Callable

from fastmcp import Context
from ...services.shared.command_context import CommandContext
from ...services.command.config_overrides import build_search_overrides
_command_context_factory: Optional[Callable[[], CommandContext]] = None
_default_config_path: Optional[str] = None


def set_command_context_factory(factory: Optional[Callable[[], CommandContext]]) -> None:
    """Register factory for creating CommandContext instances (primarily for tests)."""
    global _command_context_factory
    _command_context_factory = factory


def set_default_config_path(config_path: Optional[str]) -> None:
    """Set default config path for MCP server usage."""
    global _default_config_path
    _default_config_path = config_path


def _get_command_context() -> CommandContext:
    factory = _command_context_factory or CommandContext
    return factory()


def _resolve_config_path(workspace_path: str) -> str:
    if _default_config_path:
        return _default_config_path
    return os.path.join(workspace_path, "code_index.json")


logger = logging.getLogger(__name__)


def create_search_tool_description() -> str:
    """
    Create comprehensive tool description for the search tool.
    
    Returns:
        Detailed tool description with usage examples and parameter documentation
    """
    return """Performs semantic searches on indexed code repositories using natural language queries.

This tool searches through previously indexed code using vector similarity to find relevant 
code snippets, functions, and files based on your query. Results are ranked by relevance 
with configurable scoring and filtering options.

⚠️  PREREQUISITE: The workspace must be indexed first using the 'index' tool.

Usage Examples:
  search(query="authentication middleware", workspace="/path/to/project")
  search(query="error handling", min_score=0.6, max_results=20)
  search(query="database connection", min_score=0.4)

Parameters:
  query (str, required): Natural language search query describing what you're looking for
  workspace (str): Path to the workspace to search. Defaults to current directory.
  min_score (float): Minimum similarity score threshold (0.0-1.0). Lower = more results.
  max_results (int): Maximum number of results to return (1-500). Higher may be slower.
  filetype (str, optional): Filter by file type/language (e.g. "go", "py", "rs"). Skips language weight boosting.
  collection_name (str, optional): Search a specific collection by name instead of workspace path.

Search Optimization Tips:
  • Use specific technical terms for better matches
  • Try different min_score values: 0.2 (broad), 0.4 (balanced), 0.6 (precise)
  • Use path boosts to prioritize source code over tests/examples

Common Error Solutions:
  • "No collections found": Run the 'index' tool first to index your workspace
  • "No results found": Try lowering min_score or using broader search terms
  • "Service connection failed": Ensure Ollama and Qdrant services are running

Returns:
  Search response with status and results:
  
  1. **Successful search**:
     ```python
     {
         "results": [
             {
                 "filePath": "relative/path/to/file.py",
                 "startLine": 10,
                 "endLine": 20,
                 "type": "function",
                 "score": 0.85,
                 "adjustedScore": 0.9,
                 "snippet": "def my_function(): ..."
             }
         ],
         "status": "success",
         "result_count": 1
     }
     ```

  2. **No results matched query**:
     ```python
     {
         "results": [],
         "status": "no_results",
         "message": "Search completed but no results matched the query.",
         "query": "your search query"
     }
     ```

  3. **Workspace not indexed**:
     ```python
     {
         "results": [],
         "status": "not_indexed",
         "message": "Workspace is not indexed. Call the index tool first with this workspace path.",
         "workspace": "/path/to/workspace"
     }
     ```
"""


async def search(
    ctx: Context,
    query: str,
    workspace: str = ".",
    min_score: Optional[float] = None,
    max_results: Optional[int] = None,
    filetype: Optional[str] = None,
    collection_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search tool for MCP server.
    
    Performs semantic searches on indexed code repositories using natural language queries.
    
    Args:
        query: Search query string (required)
        workspace: Path to the workspace to search. Defaults to current dir.
        min_score: Minimum similarity score for results (0.0-1.0)
        max_results: Maximum number of results to return (1-500)
        # Search overrides removed due to FastMCP limitations
        
    Returns:
        Dict with search results and status information
        - For successful search: {"results": [...], "status": "success", "result_count": len(results)}
        - For no results: {"results": [], "status": "no_results", "message": "...", "query": query}
        - For not indexed: {"results": [], "status": "not_indexed", "message": "...", "workspace": workspace_path}
        
    Raises:
        ValueError: If parameters are invalid or workspace is not indexed
        Exception: If search operation fails
    """
    try:
        # Validate required parameters
        if not query or not isinstance(query, str):
            raise ValueError("query parameter is required and must be a non-empty string")
        
        if not isinstance(workspace, str):
            raise ValueError("workspace must be a string path")
        
        # Validate workspace exists and is accessible
        workspace_path = os.path.abspath(workspace)
        if not os.path.exists(workspace_path):
            raise ValueError(f"Workspace path does not exist: {workspace_path}")
        
        if not os.path.isdir(workspace_path):
            raise ValueError(f"Workspace path is not a directory: {workspace_path}")
        
        # Validate optional parameters
        if min_score is not None:
            if not isinstance(min_score, (int, float)) or min_score < 0 or min_score > 1:
                raise ValueError("min_score must be a number between 0.0 and 1.0")

        if max_results is not None:
            if not isinstance(max_results, int) or max_results <= 0 or max_results > 500:
                raise ValueError("max_results must be a positive integer between 1 and 500")

        if filetype is not None:
            if not isinstance(filetype, str) or len(filetype) < 1 or len(filetype) > 30:
                raise ValueError("filetype must be a non-empty string (e.g. 'go', 'py', 'rs')")
            filetype = filetype.lower()

        logger.info(f"Starting search for query: '{query}' in workspace: {workspace_path}")

        config_path = _resolve_config_path(workspace_path)
        overrides = build_search_overrides(min_score=min_score, max_results=max_results)

        command_context = _get_command_context()
        deps = command_context.load_search_dependencies(
            workspace_path=workspace_path,
            config_path=config_path,
            overrides=overrides,
        )

        collection_manager = deps.collection_manager
        
        # If collection_name is given, bypass workspace resolution
        if collection_name:
            deps.config.collection_name_override = collection_name
        else:
            workspace_collections = collection_manager.list_collections()
            matching_collections = [
                collection for collection in workspace_collections
                if collection.get("workspace_path") == workspace_path
            ]
            # Fallback: match by collection name (folder name)
            if not matching_collections:
                folder = os.path.basename(os.path.normpath(workspace_path))
                matching_collections = [
                    collection for collection in workspace_collections
                    if collection.get("name") == folder
                ]
            if not matching_collections:
                logger.warning(
                    "Workspace '%s' has not been indexed yet; returning empty search results",
                    workspace_path,
                )
                return {
                    "results": [],
                    "status": "not_indexed",
                    "message": "Workspace is not indexed. Call the index tool first with this workspace path.",
                    "workspace": workspace_path
                }

        # Perform search via shared service with validation
        result = deps.search_service.search_code(query, deps.config, filetype=filetype)

        if not result.is_successful():
            raise Exception(
                "Search execution reported errors: "
                + "; ".join(result.errors or ["unknown error"])
            )

        if result.warnings:
            logger.warning("Search completed with warnings: %s", result.warnings)

        if not result.has_matches():
            logger.info(
                "No results found for query: '%s' with min_score=%s",
                query,
                getattr(deps.config, "search_min_score", None),
            )
            return {
                "results": [],
                "status": "no_results",
                "message": "Search completed but no results matched the query.",
                "query": query
            }

        preview_chars = getattr(deps.config, "search_snippet_preview_chars", 160)
        results = _format_search_results(result.matches, preview_chars)
        return {
            "results": results,
            "status": "success",
            "result_count": len(results)
        }
        
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        logger.error(f"Search tool error: {e}")
        raise Exception(f"Search failed: {e}")


def _create_empty_results_response(query: str, min_score: float, workspace_path: str) -> List[Dict[str, Any]]:
    """
    Create helpful response for empty search results.
    
    Args:
        query: The search query that returned no results
        min_score: The minimum score threshold used
        workspace_path: Path to the workspace that was searched
        
    Returns:
        Empty list (as per requirement 3.4) - guidance is provided through logging
    """
    # Log helpful guidance for debugging
    logger.info("Search suggestions for empty results:")
    logger.info(f"  • Try lowering min_score (current: {min_score}, try: {max(0.1, min_score - 0.2)})")
    logger.info("  • Use broader search terms or synonyms")
    logger.info(f"  • Check if the relevant files were indexed in workspace: {workspace_path}")
    logger.info("  • Consider using different technical terminology")
    
    # Return empty array as per requirement 3.4
    return []


def _format_search_results(matches, preview_length: int) -> List[Dict[str, Any]]:
    """Format search matches into MCP search tool response shape."""
    formatted_results: List[Dict[str, Any]] = []

    if not matches:
        return formatted_results

    for match in matches:
        snippet = _create_code_snippet(getattr(match, "code_chunk", "") or "", preview_length)
        formatted_results.append(
            {
                "filePath": getattr(match, "file_path", ""),
                "startLine": getattr(match, "start_line", 0),
                "endLine": getattr(match, "end_line", 0),
                "type": getattr(match, "match_type", "text"),
                "score": round(getattr(match, "score", 0.0), 4),
                "adjustedScore": round(getattr(match, "adjusted_score", getattr(match, "score", 0.0)), 4),
                "snippet": snippet,
            }
        )

    return formatted_results


def _create_code_snippet(code_chunk: str, preview_length: int) -> str:
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