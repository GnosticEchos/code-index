"""
Search Tool for MCP Server

MCP wrapper for search functionality with parameter validation,
configuration overrides, and result formatting.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from fastmcp import Context
from ...config import Config
from ...embedder import OllamaEmbedder
from ...vector_store import QdrantVectorStore
from ..core.config_manager import MCPConfigurationManager
from ..core.error_handler import error_handler
from ..core.resource_manager import resource_manager


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
  search(query="database connection", search_file_type_weights={".ts": 1.5, ".js": 1.2})

Parameters:
  query (str, required): Natural language search query describing what you're looking for
  workspace (str): Path to the workspace to search. Defaults to current directory.
  min_score (float): Minimum similarity score threshold (0.0-1.0). Lower = more results.
  max_results (int): Maximum number of results to return (1-500). Higher may be slower.

# Configuration overrides removed due to FastMCP limitations

Search Optimization Tips:
  • Use specific technical terms for better matches
  • Try different min_score values: 0.2 (broad), 0.4 (balanced), 0.6 (precise)
  • Boost file types relevant to your search with search_file_type_weights
  • Use path boosts to prioritize source code over tests/examples

Common Error Solutions:
  • "No collections found": Run the 'index' tool first to index your workspace
  • "No results found": Try lowering min_score or using broader search terms
  • "Service connection failed": Ensure Ollama and Qdrant services are running

Returns:
  List of search results, each containing:
  - filePath: Relative path to the file
  - startLine/endLine: Line numbers of the code snippet
  - type: Code element type (function, class, etc.)
  - score: Raw similarity score (0.0-1.0)
  - adjustedScore: Score after applying file type and path boosts
  - snippet: Preview of the matching code (truncated to preview length)
"""


async def search(
    ctx: Context,
    query: str,
    workspace: str = ".",
    min_score: Optional[float] = None,
    max_results: Optional[int] = None
) -> List[Dict[str, Any]]:
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
        List of search results with file paths, scores, and code snippets
        
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
        
        logger.info(f"Starting search for query: '{query}' in workspace: {workspace_path}")
        
        # Load configuration
        config_path = os.path.join(workspace_path, "code_index.json")
        config_manager = MCPConfigurationManager(config_path)
        
        try:
            base_config = config_manager.load_config()
        except ValueError as e:
            raise ValueError(f"Configuration error: {e}")
        
        # Update workspace path in config
        base_config.workspace_path = workspace_path
        
        # Configuration overrides removed due to FastMCP limitations
        config = base_config
        
        # Apply CLI parameter overrides
        if min_score is not None:
            config.search_min_score = min_score
        if max_results is not None:
            config.search_max_results = max_results
        
        # Initialize components
        try:
            embedder = OllamaEmbedder(config)
            vector_store = QdrantVectorStore(config)
        except Exception as e:
            raise Exception(f"Failed to initialize search components: {e}")
        
        # Validate service connectivity
        validation_result = embedder.validate_configuration()
        if not validation_result.get("valid", False):
            error_msg = validation_result.get("error", "Unknown validation error")
            raise Exception(f"Ollama service validation failed: {error_msg}")
        
        # Check if workspace has been indexed (collection exists)
        try:
            collections = vector_store.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if vector_store.collection_name not in collection_names:
                raise ValueError(
                    f"Workspace has not been indexed yet. Collection '{vector_store.collection_name}' not found. "
                    f"Please run the 'index' tool first to index this workspace."
                )
        except Exception as e:
            if "not been indexed" in str(e):
                raise
            raise Exception(f"Failed to check collection existence: {e}")
        
        # Generate query embedding
        try:
            embedding_response = embedder.create_embeddings([query])
            query_vector = embedding_response["embeddings"][0]
            logger.debug(f"Generated embedding for query (dimension: {len(query_vector)})")
        except Exception as e:
            raise Exception(f"Failed to generate embedding for query: {e}")
        
        # Perform search
        try:
            results = vector_store.search(
                query_vector=query_vector,
                min_score=config.search_min_score,
                max_results=config.search_max_results
            )
            logger.info(f"Search completed: found {len(results)} results")
        except Exception as e:
            raise Exception(f"Search operation failed: {e}")
        
        # Handle empty results with helpful guidance
        if not results:
            logger.info(f"No results found for query: '{query}' with min_score={config.search_min_score}")
            return _create_empty_results_response(query, config.search_min_score, workspace_path)
        
        # Format results for MCP consumption
        formatted_results = _format_search_results(results, config)
        
        return formatted_results
        
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
    logger.info(f"Search suggestions for empty results:")
    logger.info(f"  • Try lowering min_score (current: {min_score}, try: {max(0.1, min_score - 0.2)})")
    logger.info(f"  • Use broader search terms or synonyms")
    logger.info(f"  • Check if the relevant files were indexed in workspace: {workspace_path}")
    logger.info(f"  • Consider using different technical terminology")
    
    # Return empty array as per requirement 3.4
    return []


def _format_search_results(results: List[Dict[str, Any]], config: Config) -> List[Dict[str, Any]]:
    """
    Format search results for MCP client consumption with enhanced ranking and snippets.
    
    Args:
        results: Raw search results from vector store (already ranked by adjustedScore)
        config: Configuration for formatting options
        
    Returns:
        Formatted results with consistent structure, ranked by adjustedScore, with code snippets
    """
    if not results:
        return []
    
    preview_length = getattr(config, "search_snippet_preview_chars", 160)
    formatted_results = []
    
    for result in results:
        payload = result.get("payload", {}) or {}
        
        # Extract and clean code snippet with better formatting
        code_chunk = payload.get("codeChunk", "") or ""
        snippet = _create_code_snippet(code_chunk, preview_length)
        
        # Ensure scores are properly formatted
        raw_score = float(result.get("score", 0.0) or 0.0)
        adjusted_score = float(result.get("adjustedScore", raw_score) or raw_score)
        
        # Create formatted result with all required fields
        formatted_result = {
            "filePath": payload.get("filePath", ""),
            "startLine": int(payload.get("startLine", 0) or 0),
            "endLine": int(payload.get("endLine", 0) or 0),
            "type": payload.get("type", ""),
            "score": round(raw_score, 4),
            "adjustedScore": round(adjusted_score, 4),
            "snippet": snippet
        }
        
        formatted_results.append(formatted_result)
    
    # Results should already be ranked by adjustedScore from vector store,
    # but ensure consistent ordering for any edge cases
    formatted_results.sort(
        key=lambda x: (x["adjustedScore"], x["score"]), 
        reverse=True
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