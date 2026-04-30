"""
Helper functions for FileProcessor to reduce file size.
"""
import os
import uuid
from typing import Dict, Any, List, Optional, Callable
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


def compute_file_hash(file_path: str, logger) -> str:
    """Compute hash of file content for change detection."""
    try:
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to compute hash for {file_path}: {e}")
        return ""


def check_file_changed(file_path: str, cache_manager, current_hash: str) -> bool:
    """Check if file has changed since last processing."""
    cached_hash = cache_manager.get_hash(file_path) if cache_manager else None
    return current_hash == cached_hash


def get_file_blocks(parser, file_path: str) -> List:
    """Parse file into blocks."""
    return parser.parse_file(file_path) if parser else []


def extract_texts_from_blocks(blocks: List) -> List[str]:
    """Extract text content from blocks."""
    return [block.content for block in blocks if block.content.strip()]


def prepare_vector_points(
    file_path: str,
    blocks: List,
    embeddings: List[List[float]],
    rel_path: str,
    embedder
) -> List[Dict[str, Any]]:
    """Prepare vector points for storage."""
    points = []
    for i, block in enumerate(blocks):
        if i >= len(embeddings):
            break
        
        point_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{file_path}:{block.start_line}:{block.end_line}:{getattr(block, 'split_index', '')}"
        ))
        
        _, ext = os.path.splitext(rel_path)
        filetype = ext.lstrip('.').lower() if ext else ""

        payload = {
            "filePath": rel_path,
            "filetype": filetype,
            "codeChunk": block.content,
            "startLine": block.start_line,
            "endLine": block.end_line,
            "type": block.type,
            "embedding_model": getattr(embedder, 'model_identifier', 'unknown')
        }
        
        if hasattr(block, 'split_index') and block.split_index is not None:
            payload["splitIndex"] = block.split_index
            payload["splitTotal"] = block.split_total
            payload["parentBlockId"] = block.parent_block_id
        
        point = {
            "id": point_id,
            "vector": embeddings[i],
            "payload": payload
        }
        points.append(point)
    
    return points


def store_vectors(vector_store, rel_path: str, points: List[Dict], errors: List[str], 
                 error_handler: ErrorHandler = None, file_path: str = "") -> bool:
    """Store vectors in the database, return True on success."""
    try:
        vector_store.delete_points_by_file_path(rel_path)
    except Exception:
        pass
    
    try:
        vector_store.upsert_points(points)
        return True
    except Exception as e:
        if error_handler:
            error_context = ErrorContext(
                component="file_processor",
                operation="upsert_points",
                file_path=rel_path
            )
            error_response = error_handler.handle_error(
                e, error_context, ErrorCategory.DATABASE, ErrorSeverity.MEDIUM
            )
            errors.append(f"Failed to store vectors for {rel_path}: {error_response.message}")
        else:
            errors.append(f"Failed to store vectors for {rel_path}: {str(e)}")
        return False


def update_cache(cache_manager, file_path: str, current_hash: str) -> None:
    """Update cache with new file hash."""
    if cache_manager:
        cache_manager.update_hash(file_path, current_hash)


def get_relative_path(file_path: str, workspace_path: str, path_utils) -> str:
    """Get workspace-relative path or normalized path."""
    from pathlib import Path
    if path_utils:
        return path_utils.get_workspace_relative_path(file_path) or \
               path_utils.normalize_path(file_path)
    
    try:
        file_p = Path(file_path)
        workspace_p = Path(workspace_path)
        if file_p.is_absolute() and workspace_p.is_absolute():
            rel_path = file_p.relative_to(workspace_p)
            return str(rel_path)
    except (ValueError, TypeError):
        pass
    
    return str(Path(file_path).name)


def init_result(file_path: str) -> Dict[str, Any]:
    """Initialize standard result dictionary."""
    return {'success': False, 'file_path': file_path, 'blocks_processed': 0, 'error': None}


def handle_skip(file_path: str, current_hash: str, cache_manager, 
                progress_callback: Optional[Callable], completed_count: int, total_files: int,
                reason: str = None) -> Dict[str, Any]:
    """Handle skipped file processing."""
    result = init_result(file_path)
    result['skipped'] = True
    if reason:
        result['reason'] = reason
    if cache_manager:
        update_cache(cache_manager, file_path, current_hash)
    if progress_callback:
        progress_callback(file_path, completed_count, total_files, "skipped", 0)
    return result