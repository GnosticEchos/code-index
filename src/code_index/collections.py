"""
Collection management for the code index tool.
"""
import os
import hashlib
import logging
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from code_index.config import Config

logger = logging.getLogger(__name__)


class CollectionManager:
    """Manage Qdrant collections for code indexing."""
    
    def __init__(self, config: Config):
        """Initialize collection manager with configuration."""
        self.config = config
        self.workspace_path = os.path.abspath(config.workspace_path)
        
        # Parse Qdrant URL
        url = config.qdrant_url
        if url.startswith("http://"):
            host = url[7:]
            https = False
        elif url.startswith("https://"):
            host = url[8:]
            https = True
        else:
            host = url
            https = False
        
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 6333
            
        self.client = QdrantClient(host=host, port=port, https=https)
        self.collection_name = self.generate_collection_name(self.workspace_path)

    def generate_collection_name(self, workspace_path: str) -> str:
        """Generate a unique collection name based on the workspace path."""
        # Use first 16 chars of SHA-256 hash of absolute path
        path_hash = hashlib.sha256(os.path.abspath(workspace_path).encode()).hexdigest()[:16]
        return f"ws-{path_hash}"

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections in Qdrant with basic metadata."""
        try:
            collections = self.client.get_collections().collections
            result = []
            for c in collections:
                c_name = c.name if hasattr(c, 'name') else str(c)
                info = self.get_collection_info(c_name)
                result.append(info)
            return result
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a specific collection."""
        name = collection_name or self.collection_name
        try:
            # Handle info which might be a mock object or dict
            info = self.client.get_collection(collection_name=name)
            
            # Extract basic metrics with fallback for dicts
            points_count = getattr(info, 'points_count', 0)
            if points_count == 0 and isinstance(info, dict):
                points_count = info.get('points_count', 0)
                
            status = getattr(info, 'status', 'unknown')
            if status == 'unknown' and isinstance(info, dict):
                status = info.get('status', 'unknown')

            vectors_count = getattr(info, 'vectors_count', 0)
            if vectors_count == 0 and isinstance(info, dict):
                vectors_count = info.get('vectors_count', 0)

            # Extract dimensionality and model
            dimensions = {}
            dimension = 0
            model = "unknown"
            
            try:
                # Probe first point for metadata
                scroll_result = self.client.scroll(
                    collection_name=name,
                    limit=1,
                    with_payload=True,
                    with_vectors=True
                )
                points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result.points
                if points:
                    p = points[0]
                    payload = p.payload if hasattr(p, 'payload') else p.get('payload', {})
                    model = payload.get("model") or payload.get("embedding_model") or "unknown"
                    
                    vec_data = p.vector if hasattr(p, 'vector') else p.get('vector')
                    if isinstance(vec_data, dict):
                        for k, v in vec_data.items():
                            dimensions[k] = len(v)
                        if 'text' in dimensions:
                            dimension = dimensions['text']
                        elif dimensions:
                            dimension = next(iter(dimensions.values()))
                    elif isinstance(vec_data, list):
                        dimension = len(vec_data)
                        dimensions["default"] = dimension
            except Exception:
                pass

            # Fallback to config extraction
            if not dimensions:
                try:
                    def _try_get(obj, key):
                        if hasattr(obj, key): return getattr(obj, key)
                        if isinstance(obj, dict): return obj.get(key)
                        return None

                    # 1) Search for 'vectors' or 'size' at all potential levels (root, config, config.params)
                    candidates = [info]
                    config = _try_get(info, 'config')
                    if config: candidates.append(config)
                    params = _try_get(config, 'params') if config else None
                    if params: candidates.append(params)
                    
                    # Also handle dict-style access for the col2 mock
                    if isinstance(info, dict) and 'config' in info:
                        cfg = info['config']
                        if 'params' in cfg: candidates.append(cfg['params'])
                        if 'vectors' in cfg: candidates.append(cfg['vectors'])
                    if isinstance(info, dict) and 'vectors' in info:
                        candidates.append(info['vectors'])

                    for cand in candidates:
                        if dimension and dimensions: break
                        
                        # Check for 'size' directly
                        s = _try_get(cand, 'size')
                        if s:
                            dimension = s
                            dimensions["default"] = s
                        
                        # Check for 'vectors' map
                        v_data = _try_get(cand, 'vectors')
                        if v_data and isinstance(v_data, dict) and 'size' not in v_data:
                            # It's a map of vector configs (e.g., {'text': {'size': 768}})
                            for vk, vv in v_data.items():
                                vs = _try_get(vv, 'size')
                                if vs:
                                    dimensions[vk] = vs
                                    if not dimension or vk == 'text': dimension = vs
                        elif v_data and _try_get(v_data, 'size'):
                            # It's a single vector config object
                            vs = _try_get(v_data, 'size')
                            dimension = vs
                            dimensions["default"] = vs
                except Exception:
                    pass
            
            return {
                "name": name,
                "status": status,
                "points_count": points_count,
                "vectors_count": vectors_count,
                "dimension": dimension,
                "dimensions": dimensions,
                "model": model,
                "model_identifier": model,
                "indexing_status": getattr(info, 'optimizer_status', 'unknown'),
                "workspace_path": "Unknown" 
            }
        except Exception as e:
            logger.error(f"Error getting collection info for {name}: {e}")
            return {"error": str(e)}

    def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """Delete a collection from Qdrant."""
        name = collection_name or self.collection_name
        try:
            self.client.delete_collection(collection_name=name)
            return True
        except Exception as e:
            logger.error(f"Error deleting collection {name}: {e}")
            return False

    def prune_old_collections(self, older_than_days: int) -> List[str]:
        """Prune collections older than specified days (placeholder)."""
        return []

    def clear_all_collections(self) -> Dict[str, int]:
        """Delete all collections managed by this tool."""
        collections = self.list_collections()
        targets = [c["name"] for c in collections if c["name"].startswith("ws-")]
        
        deleted = 0
        failed = 0
        for name in targets:
            if self.delete_collection(name):
                deleted += 1
            else:
                failed += 1
        return {"found": len(targets), "deleted": deleted, "failed": failed}

    def canonicalize_model(self, model_name: str) -> str:
        """Standardize model names for consistent identification."""
        if not model_name: return "unknown"
        m = model_name.lower()
        if "nomic" in m: return "nomic-embed-text"
        if "qwen" in m: return "qwen-embeddings"
        if "llama" in m: return "llama-embeddings"
        if "bge" in m: return "bge-embeddings"
        return model_name.split(":")[0] if ":" in model_name else model_name

    def get_collections_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all managed collections."""
        collections = self.list_collections()
        targets = [c for c in collections if c["name"].startswith("ws-")]
        return targets

    def find_collection_by_path(self, workspace_path: str) -> Optional[str]:
        """Find if a collection exists for a given workspace path."""
        target_name = self.generate_collection_name(workspace_path)
        collections = self.list_collections()
        for c in collections:
            if c["name"] == target_name:
                return target_name
        return None

    def get_metadata_for_path(self, file_path: str, collection_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific file path from the collection."""
        name = collection_name or self.collection_name
        try:
            scroll_result = self.client.scroll(
                collection_name=name,
                scroll_filter=Filter(must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))]),
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result.points
            if points:
                p = points[0]
                return p.payload if hasattr(p, 'payload') else p.get('payload', {})
            return None
        except Exception as e:
            logger.error(f"Error getting metadata for {file_path} from {name}: {e}")
            return None
