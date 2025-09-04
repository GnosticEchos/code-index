"""
Collections Tool for MCP Server

MCP wrapper for collection management with safety confirmations
and comprehensive collection operations.
"""

import os
import logging
from typing import Dict, Any, Optional, List

# Robust import of Context to tolerate environments where fastmcp may be missing or incomplete.
try:
    from fastmcp import Context  # type: ignore
except Exception:  # Fallback stub to avoid import-time failures in tests
    class Context:  # Minimal stub; only used for typing in this module
        async def elicit(self, *args, **kwargs):
            raise RuntimeError("fastmcp.Context is unavailable in this environment")
from ...config import Config
from ...collections import CollectionManager
from ..core.config_manager import MCPConfigurationManager

# Compatibility shim to ensure fastmcp exposes elicitation classes during tests/runtime.
# This augments the installed fastmcp (if present) or provides a minimal stub.
try:  # pragma: no cover - import-time compat code
    import importlib as _importlib
    import sys as _sys
    import types as _types

    try:
        _fm = _importlib.import_module("fastmcp")
    except Exception:
        _fm = _types.ModuleType("fastmcp")
        _sys.modules["fastmcp"] = _fm  # Ensure 'import fastmcp' succeeds

    if not hasattr(_fm, "AcceptedElicitation"):
        class AcceptedElicitation:  # tests use .value attribute
            def __init__(self, value=None):
                self.value = value
        _fm.AcceptedElicitation = AcceptedElicitation  # type: ignore[attr-defined]

    if not hasattr(_fm, "DeclinedElicitation"):
        class DeclinedElicitation:
            pass
        _fm.DeclinedElicitation = DeclinedElicitation  # type: ignore[attr-defined]

    if not hasattr(_fm, "CancelledElicitation"):
        class CancelledElicitation:
            pass
        _fm.CancelledElicitation = CancelledElicitation  # type: ignore[attr-defined]
except Exception:
    # Never fail import of this module due to shim problems
    pass

logger = logging.getLogger(__name__)


def create_collections_tool_description() -> str:
    """
    Create comprehensive tool description for the collections tool.
    
    Returns:
        Detailed tool description with usage examples and parameter documentation
    """
    return """Manages indexed code collections with comprehensive operations and safety confirmations.

This tool provides collection management operations for viewing, maintaining, and cleaning up 
indexed code repositories. All destructive operations require explicit confirmation for safety.

⚠️  SAFETY WARNING: Delete, prune, and clear-all operations permanently remove indexed data.
    These operations cannot be undone. Use with caution.

Usage Examples:
  collections(subcommand="list")                                    # List all collections
  collections(subcommand="list", detailed=True)                    # List with full details
  collections(subcommand="info", collection_name="ws-abc123def456") # Get collection details
  collections(subcommand="delete", collection_name="ws-abc123def456", yes=True) # Delete with confirmation bypass
  collections(subcommand="prune", older_than_days=30)              # Prune old collections (with confirmation)
  collections(subcommand="clear-all", yes=True)                    # Delete all collections (with confirmation bypass)

Subcommands:
  list: List all available collections with workspace mappings and metadata
  info: Get detailed information about a specific collection including dimensions and model
  delete: Delete a specific collection and its associated cache files (DESTRUCTIVE)
  prune: Delete collections older than specified days (DESTRUCTIVE - NOT YET IMPLEMENTED)
  clear-all: Delete all collections and clear local cache files (DESTRUCTIVE)

Parameters:
  subcommand (str, required): The operation to perform (list, info, delete, prune, clear-all)
  collection_name (str): Name of the collection (required for 'info' and 'delete' subcommands)
  older_than_days (int): Age threshold in days for 'prune' operation (default: 30)
  yes (bool): Skip confirmation prompts for destructive operations (default: false)
  detailed (bool): Include detailed information in 'list' results (default: false)

Safety Measures:
  • Destructive operations (delete, prune, clear-all) require explicit confirmation
  • Use yes=true parameter to bypass confirmation prompts for automation
  • Failed confirmations abort operations with clear messaging
  • Cache cleanup is performed automatically after successful deletions
  • Operations are logged for audit purposes

Collection Information:
  Each collection contains:
  • Workspace path mapping (where the code was indexed from)
  • Point count (number of indexed code chunks)
  • Vector dimensions (embedding model configuration)
  • Model identifier (which embedding model was used)
  • Creation metadata and status information

Common Error Solutions:
  • "Collection not found": Verify collection name with 'list' subcommand first
  • "Service connection failed": Ensure Qdrant service is running and accessible
  • "Permission denied": Check file system permissions for cache cleanup operations
  • "Operation cancelled": User denied confirmation for destructive operation

Returns:
  Dictionary containing:
  - success: Boolean indicating operation success
  - message: Human-readable status message
  - data: Operation-specific results (collections list, collection info, etc.)
  - warnings: Any warnings or important notices
"""


async def collections(
    ctx: Context,
    subcommand: str,
    collection_name: Optional[str] = None,
    older_than_days: Optional[int] = None,
    yes: bool = False,
    detailed: bool = False
) -> Dict[str, Any]:
    """
    Collections management tool for MCP server.
    
    Manages indexed collections with safety confirmations for destructive operations.
    
    Args:
        subcommand: The operation to perform (list, info, delete, prune, clear-all)
        collection_name: Name of the collection (required for info/delete)
        older_than_days: Age threshold for prune operation (default: 30)
        yes: Skip confirmation prompts for destructive operations
        detailed: Include detailed information in results
        # Options removed due to FastMCP limitations
        
    Returns:
        Dictionary with operation results
        
    Raises:
        ValueError: If parameters are invalid or required parameters are missing
        Exception: If collection operation fails
    """
    try:
        # Validate subcommand parameter
        valid_subcommands = ["list", "info", "delete", "prune", "clear-all"]
        if not subcommand or not isinstance(subcommand, str):
            raise ValueError("subcommand parameter is required and must be a non-empty string")
        
        if subcommand not in valid_subcommands:
            raise ValueError(f"Invalid subcommand '{subcommand}'. Must be one of: {', '.join(valid_subcommands)}")
        
        # Validate subcommand-specific parameters
        if subcommand in ["info", "delete"]:
            if not collection_name or not isinstance(collection_name, str):
                raise ValueError(f"collection_name parameter is required for '{subcommand}' subcommand")
        
        if subcommand == "prune":
            if older_than_days is not None:
                if not isinstance(older_than_days, int) or older_than_days <= 0:
                    raise ValueError("older_than_days must be a positive integer")
            else:
                older_than_days = 30  # Default value
        
        # Validate boolean parameters
        if not isinstance(yes, bool):
            raise ValueError("yes parameter must be a boolean")
        
        if not isinstance(detailed, bool):
            raise ValueError("detailed parameter must be a boolean")
        
        logger.info(f"Starting collections operation: {subcommand}")
        
        # Load configuration
        config_manager = MCPConfigurationManager("code_index.json")
        
        try:
            config = config_manager.load_config()
        except ValueError as e:
            raise ValueError(f"Configuration error: {e}")
        
        # Initialize collection manager
        try:
            collection_manager = CollectionManager(config)
        except Exception as e:
            raise Exception(f"Failed to initialize collection manager: {e}")
        
        # Route to appropriate subcommand handler
        if subcommand == "list":
            return await _handle_list_collections(collection_manager, detailed)
        elif subcommand == "info":
            return await _handle_collection_info(collection_manager, collection_name)
        elif subcommand == "delete":
            return await _handle_delete_collection(ctx, collection_manager, collection_name, yes, config)
        elif subcommand == "prune":
            return await _handle_prune_collections(ctx, collection_manager, older_than_days, yes)
        elif subcommand == "clear-all":
            return await _handle_clear_all_collections(ctx, collection_manager, yes, config)
        else:
            # This should never happen due to validation above, but included for completeness
            raise ValueError(f"Unhandled subcommand: {subcommand}")
        
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        logger.error(f"Collections tool error: {e}")
        raise Exception(f"Collections operation failed: {e}")


async def _handle_list_collections(collection_manager: CollectionManager, detailed: bool) -> Dict[str, Any]:
    """
    Handle the 'list' subcommand to list all collections.
    
    Args:
        collection_manager: Initialized collection manager
        detailed: Whether to include detailed information
        
    Returns:
        Dictionary with collections list and metadata
    """
    try:
        collections_list = collection_manager.list_collections()
        
        if not collections_list:
            return {
                "success": True,
                "message": "No collections found.",
                "data": {
                    "collections": [],
                    "total_count": 0
                }
            }
        
        # Format collections data
        formatted_collections = []
        for collection in collections_list:
            formatted_collection = {
                "name": collection.get("name", ""),
                "points_count": collection.get("points_count", 0),
                "workspace_path": collection.get("workspace_path", "Unknown"),
                "dimensions": collection.get("dimensions", {}),
                "model_identifier": collection.get("model_identifier", "unknown")
            }
            
            # Add detailed information if requested
            if detailed:
                formatted_collection.update({
                    "vectors_count": collection.get("vectors_count", 0),
                    "status": collection.get("status", "unknown")
                })
            
            formatted_collections.append(formatted_collection)
        
        # Sort collections by name for consistent output
        formatted_collections.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "message": f"Found {len(formatted_collections)} collection(s).",
            "data": {
                "collections": formatted_collections,
                "total_count": len(formatted_collections),
                "detailed": detailed
            }
        }
        
    except Exception as e:
        raise Exception(f"Failed to list collections: {e}")


async def _handle_collection_info(collection_manager: CollectionManager, collection_name: str) -> Dict[str, Any]:
    """
    Handle the 'info' subcommand to get detailed collection information.
    
    Args:
        collection_manager: Initialized collection manager
        collection_name: Name of the collection to get info for
        
    Returns:
        Dictionary with detailed collection information
    """
    try:
        collection_info = collection_manager.get_collection_info(collection_name)
        
        return {
            "success": True,
            "message": f"Retrieved information for collection '{collection_name}'.",
            "data": {
                "collection": {
                    "name": collection_info.get("name", ""),
                    "status": collection_info.get("status", "unknown"),
                    "points_count": collection_info.get("points_count", 0),
                    "vectors_count": collection_info.get("vectors_count", 0),
                    "workspace_path": collection_info.get("workspace_path", "Unknown"),
                    "dimensions": collection_info.get("dimensions", {}),
                    "model_identifier": collection_info.get("model_identifier", "unknown"),
                    "config": collection_info.get("config", "")
                }
            }
        }
        
    except Exception as e:
        if "not found" in str(e).lower() or "doesn't exist" in str(e).lower():
            raise ValueError(f"Collection '{collection_name}' not found. Use 'list' subcommand to see available collections.")
        raise Exception(f"Failed to get collection info: {e}")


async def _handle_delete_collection(
    ctx: Context,
    collection_manager: CollectionManager, 
    collection_name: str, 
    yes: bool,
    config: Config
) -> Dict[str, Any]:
    """
    Handle the 'delete' subcommand to delete a specific collection.
    
    This is a DESTRUCTIVE operation that requires confirmation unless yes=True.
    
    Args:
        ctx: MCP context for user interactions
        collection_manager: Initialized collection manager
        collection_name: Name of the collection to delete
        yes: Whether to skip confirmation prompt
        config: Configuration for cache cleanup
        
    Returns:
        Dictionary with deletion results
    """
    try:
        # Verify collection exists before attempting deletion
        try:
            collection_info = collection_manager.get_collection_info(collection_name)
        except Exception as e:
            if "not found" in str(e).lower() or "doesn't exist" in str(e).lower():
                raise ValueError(f"Collection '{collection_name}' not found. Use 'list' subcommand to see available collections.")
            raise Exception(f"Failed to verify collection existence: {e}")
        
        # Get confirmation unless bypassed with yes=True
        if not yes:
            confirmation_result = await _request_confirmation(
                ctx,
                f"Are you sure you want to delete collection '{collection_name}'?",
                f"This will permanently remove {collection_info.get('points_count', 0)} indexed code chunks "
                f"from workspace: {collection_info.get('workspace_path', 'Unknown')}. "
                f"This action cannot be undone."
            )
            
            if not confirmation_result["confirmed"]:
                return {
                    "success": False,
                    "message": f"Collection deletion cancelled by user: {confirmation_result['reason']}",
                    "data": {
                        "collection_name": collection_name,
                        "operation": "delete",
                        "cancelled": True
                    }
                }
        
        # Resolve canonical ID for cache cleanup before deletion
        canonical_id = _resolve_canonical_id_for_delete(collection_manager, collection_name)
        
        # Perform the deletion
        try:
            success = collection_manager.delete_collection(collection_name)
            if not success:
                raise Exception("Collection deletion returned False")
        except Exception as e:
            raise Exception(f"Failed to delete collection from Qdrant: {e}")
        
        # Clean up cache files
        cache_files_removed = 0
        if canonical_id:
            try:
                from ...cache import delete_collection_cache
                cache_files_removed = delete_collection_cache(canonical_id, config)
            except Exception as e:
                logger.warning(f"Cache cleanup failed for collection {collection_name}: {e}")
        
        logger.info(f"Successfully deleted collection '{collection_name}' and cleaned up {cache_files_removed} cache files")
        
        return {
            "success": True,
            "message": f"Collection '{collection_name}' deleted successfully.",
            "data": {
                "collection_name": collection_name,
                "points_deleted": collection_info.get("points_count", 0),
                "workspace_path": collection_info.get("workspace_path", "Unknown"),
                "cache_files_removed": cache_files_removed,
                "canonical_id": canonical_id or "unknown"
            }
        }
        
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        raise Exception(f"Failed to delete collection: {e}")


async def _handle_prune_collections(
    ctx: Context,
    collection_manager: CollectionManager, 
    older_than_days: int, 
    yes: bool
) -> Dict[str, Any]:
    """
    Handle the 'prune' subcommand to delete collections older than specified days.
    
    This is a DESTRUCTIVE operation that requires confirmation unless yes=True.
    
    Args:
        ctx: MCP context for user interactions
        collection_manager: Initialized collection manager
        older_than_days: Age threshold in days
        yes: Whether to skip confirmation prompt
        
    Returns:
        Dictionary with pruning results
    """
    try:
        # Get confirmation unless bypassed with yes=True
        if not yes:
            confirmation_result = await _request_confirmation(
                ctx,
                f"Are you sure you want to prune collections older than {older_than_days} days?",
                f"This will permanently delete all collections that are older than {older_than_days} days, "
                f"including all their indexed code chunks and associated cache files. "
                f"This action cannot be undone."
            )
            
            if not confirmation_result["confirmed"]:
                return {
                    "success": False,
                    "message": f"Collection pruning cancelled by user: {confirmation_result['reason']}",
                    "data": {
                        "older_than_days": older_than_days,
                        "operation": "prune",
                        "cancelled": True
                    }
                }
        
        # Perform the pruning
        try:
            pruned_collections = collection_manager.prune_old_collections(older_than_days)
            
            if not pruned_collections:
                return {
                    "success": True,
                    "message": f"No collections found older than {older_than_days} days to prune.",
                    "data": {
                        "older_than_days": older_than_days,
                        "collections_pruned": [],
                        "total_pruned": 0
                    }
                }
            
            # Note: The current implementation of prune_old_collections returns an empty list
            # This is a placeholder for when timestamp tracking is implemented
            return {
                "success": True,
                "message": f"Pruning operation completed. {len(pruned_collections)} collections were removed.",
                "data": {
                    "older_than_days": older_than_days,
                    "collections_pruned": pruned_collections,
                    "total_pruned": len(pruned_collections)
                },
                "warnings": [
                    "Note: Collection age tracking is not yet fully implemented. "
                    "This operation currently returns no collections to prune."
                ]
            }
            
        except Exception as e:
            raise Exception(f"Failed to prune collections: {e}")
        
    except Exception as e:
        raise Exception(f"Failed to prune collections: {e}")


async def _handle_clear_all_collections(
    ctx: Context,
    collection_manager: CollectionManager, 
    yes: bool,
    config: Config
) -> Dict[str, Any]:
    """
    Handle the 'clear-all' subcommand to delete all collections.
    
    This is a DESTRUCTIVE operation that requires confirmation unless yes=True.
    
    Args:
        ctx: MCP context for user interactions
        collection_manager: Initialized collection manager
        yes: Whether to skip confirmation prompt
        config: Configuration for cache cleanup
        
    Returns:
        Dictionary with clear-all results
    """
    try:
        # Get list of collections to show user what will be deleted
        collections_list = collection_manager.list_collections()
        total_collections = len(collections_list)
        total_points = sum(col.get("points_count", 0) for col in collections_list)
        
        # Get confirmation unless bypassed with yes=True
        if not yes:
            confirmation_result = await _request_confirmation(
                ctx,
                f"Are you sure you want to delete ALL {total_collections} collections?",
                f"This will permanently delete ALL {total_collections} collections containing "
                f"{total_points} total indexed code chunks, plus all associated cache files. "
                f"This action cannot be undone and will require re-indexing all workspaces."
            )
            
            if not confirmation_result["confirmed"]:
                return {
                    "success": False,
                    "message": f"Clear-all operation cancelled by user: {confirmation_result['reason']}",
                    "data": {
                        "total_collections": total_collections,
                        "total_points": total_points,
                        "operation": "clear-all",
                        "cancelled": True
                    }
                }
        
        # Perform the clear-all operation
        deleted_collections = []
        failed_deletions = []
        
        # Delete each collection individually
        for collection in collections_list:
            collection_name = collection.get("name", "")
            if not collection_name:
                continue
                
            try:
                success = collection_manager.delete_collection(collection_name)
                if success:
                    deleted_collections.append(collection_name)
                else:
                    failed_deletions.append({"name": collection_name, "error": "Deletion returned False"})
            except Exception as e:
                failed_deletions.append({"name": collection_name, "error": str(e)})
                logger.warning(f"Failed to delete collection '{collection_name}': {e}")
        
        # Clear all cache files
        cache_files_removed = 0
        try:
            from ...cache import clear_all_caches
            cache_files_removed = clear_all_caches(config)
        except Exception as e:
            logger.warning(f"Cache cleanup failed during clear-all operation: {e}")
        
        # Prepare result
        success_count = len(deleted_collections)
        failure_count = len(failed_deletions)
        
        if failure_count == 0:
            message = f"Successfully deleted all {success_count} collections and cleared {cache_files_removed} cache files."
            success = True
        elif success_count == 0:
            message = f"Failed to delete any collections. {failure_count} failures occurred."
            success = False
        else:
            message = f"Partially completed: {success_count} collections deleted, {failure_count} failed. Cleared {cache_files_removed} cache files."
            success = True  # Partial success is still considered success
        
        logger.info(f"Clear-all operation completed: {success_count} deleted, {failure_count} failed, {cache_files_removed} cache files removed")
        
        result_data = {
            "total_collections": total_collections,
            "total_points": total_points,
            "deleted_collections": deleted_collections,
            "success_count": success_count,
            "failure_count": failure_count,
            "cache_files_removed": cache_files_removed
        }
        
        if failed_deletions:
            result_data["failed_deletions"] = failed_deletions
        
        return {
            "success": success,
            "message": message,
            "data": result_data
        }
        
    except Exception as e:
        raise Exception(f"Failed to clear all collections: {e}")


async def _request_confirmation(ctx: Context, question: str, consequences: str) -> Dict[str, Any]:
    """
    Request user confirmation for destructive operations using MCP elicit mechanism.
    
    Args:
        ctx: MCP context for user interactions
        question: The confirmation question to ask the user
        consequences: Detailed explanation of what will happen
        
    Returns:
        Dictionary with confirmation result:
        - confirmed: Boolean indicating if user confirmed
        - reason: String explaining the result (confirmed/declined/cancelled)
    """
    try:
        # Create a clear confirmation message
        confirmation_message = f"{question}\n\n{consequences}\n\nType 'yes' to confirm or 'no' to cancel:"
        
        # Request confirmation from user using MCP elicit
        # We expect a simple string response
        elicit_result = await ctx.elicit(confirmation_message, str)
        
        # Check the type of response; import defensively in case fastmcp lacks these in this environment
        try:
            from fastmcp import AcceptedElicitation, DeclinedElicitation, CancelledElicitation  # type: ignore
        except Exception:
            # Define minimal stand-ins so tests and runtime can proceed
            class AcceptedElicitation:  # type: ignore
                def __init__(self, value=None):
                    self.value = value
            class DeclinedElicitation:  # type: ignore
                pass
            class CancelledElicitation:  # type: ignore
                pass
        
        if isinstance(elicit_result, AcceptedElicitation):
            # User provided a response
            response = elicit_result.value.strip().lower()
            
            if response in ["yes", "y", "confirm", "true"]:
                logger.info(f"User confirmed destructive operation with response: '{response}'")
                return {
                    "confirmed": True,
                    "reason": "User confirmed the operation"
                }
            else:
                logger.info(f"User declined destructive operation with response: '{response}'")
                return {
                    "confirmed": False,
                    "reason": f"User declined with response: '{response}'"
                }
        
        elif isinstance(elicit_result, DeclinedElicitation):
            # User explicitly declined to provide input
            logger.info("User declined to provide confirmation")
            return {
                "confirmed": False,
                "reason": "User declined to provide confirmation"
            }
        
        elif isinstance(elicit_result, CancelledElicitation):
            # Operation was cancelled
            logger.info("Confirmation request was cancelled")
            return {
                "confirmed": False,
                "reason": "Confirmation request was cancelled"
            }
        
        else:
            # Unexpected response type
            logger.warning(f"Unexpected elicit result type: {type(elicit_result)}")
            return {
                "confirmed": False,
                "reason": "Unexpected response from confirmation request"
            }
    
    except Exception as e:
        logger.error(f"Failed to request confirmation: {e}")
        # In case of error, default to not confirmed for safety
        return {
            "confirmed": False,
            "reason": f"Confirmation request failed: {e}"
        }


def _resolve_canonical_id_for_delete(collection_manager: CollectionManager, collection_name: str) -> Optional[str]:
    """
    Resolve the canonical collection id used in cache filenames.

    Resolution order:
      1) Probe a single point's payload for a known id (via scroll(limit=1)).
      2) If name starts with 'ws-', strip the prefix and use the suffix.
      3) Otherwise, return None.

    This function must be resilient to backend errors and never raise.
    """
    # 1) Try O(1) scroll probe for payload metadata
    try:
        scroll_res = collection_manager.client.scroll(
            collection_name=collection_name,
            limit=1,
            with_payload=True,
            with_vectors=False,
        )
        points = scroll_res[0] if isinstance(scroll_res, tuple) else getattr(scroll_res, "points", [])
        if points:
            first = points[0]
            payload = getattr(first, "payload", None)
            if payload is None and isinstance(first, dict):
                payload = first.get("payload")
            if isinstance(payload, dict):
                for key in ("collection_id", "collectionId", "ws_id", "workspace_id"):
                    val = payload.get(key)
                    if isinstance(val, str) and val:
                        return val
    except Exception:
        # Ignore probe failures; continue with name-based derivation
        pass

    # 2) Derive from naming pattern 'ws-<id>'
    try:
        if isinstance(collection_name, str) and collection_name.startswith("ws-"):
            suffix = collection_name[3:]
            if suffix:
                return suffix
    except Exception:
        pass

    # 3) Unresolved
    return None