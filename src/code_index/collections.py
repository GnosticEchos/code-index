"""
Collection management for the code index tool.
"""
import os
import time
import hashlib
import json
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from code_index.config import Config


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
        
        # Split host and port
        if ":" in host:
            host, port_str = host.split(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 6333 if not https else 443
        else:
            port = 6333 if not https else 443
        
        # Initialize client
        self.client = QdrantClient(
            url=url,
            api_key=config.qdrant_api_key
        )
    
    def generate_collection_name(self, workspace_path: str) -> str:
        """Generate collection name based on workspace path."""
        workspace_hash = hashlib.sha256(os.path.abspath(workspace_path).encode()).hexdigest()
        return f"ws-{workspace_hash[:16]}"

    @staticmethod
    def _canonicalize_model(model: Optional[str]) -> str:
        """Return canonical model identifier (trim ':latest' suffix only)."""
        m = (model or "").strip()
        return m[:-7] if m.endswith(":latest") else m
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections with their workspace information, dimensions, and model identifier."""
        try:
            collections = self.client.get_collections()
            collection_info_list: List[Dict[str, Any]] = []

            # Build metadata map once (O(1) total outside per-collection ops)
            metadata_collection = "code_index_metadata"
            metadata_map: Dict[str, str] = {}
            try:
                metadata_results = self.client.query_points(
                    collection_name=metadata_collection,
                    query=[0.0] * 1,  # Zero vector for search all
                    limit=1000,
                    with_payload=True
                ).points
                for result in metadata_results:
                    payload = result.payload or {}
                    cn = payload.get("collection_name")
                    wp = payload.get("workspace_path")
                    if cn and wp:
                        metadata_map[str(cn)] = str(wp)
            except Exception:
                # Proceed without metadata if unavailable
                pass

            for collection in collections.collections:
                collection_name = collection.name
                info: Dict[str, Any] = {
                    "name": collection_name,
                    "workspace_path": metadata_map.get(collection_name, "Unknown"),
                    "points_count": 0,
                    "dimensions": {},
                    "model_identifier": "unknown",
                }

                # Per-collection: get_collection (for points and dimensions)
                try:
                    col_info = self.client.get_collection(collection_name)
                    info["points_count"] = getattr(col_info, "points_count", 0)

                    # Derive dimensions (robust across default and named vectors)
                    dim_map: Dict[str, int] = {}
                    cfg = getattr(col_info, "config", None)

                    # Prefer vectors attribute when present
                    vectors_attr = getattr(cfg, "vectors", None) if cfg is not None else None
                    size_val = None

                    # Default vector: vectors is a VectorParams-like object
                    if vectors_attr is not None and hasattr(vectors_attr, "size"):
                        try:
                            size_val = getattr(vectors_attr, "size", None)
                            if isinstance(size_val, int) and size_val > 0:
                                dim_map = {"default": int(size_val)}
                        except Exception:
                            pass

                    # Some client versions expose a 'default' VectorParams
                    if not dim_map and vectors_attr is not None and hasattr(vectors_attr, "default"):
                        try:
                            d = getattr(vectors_attr, "default", None)
                            dsz = getattr(d, "size", None)
                            if isinstance(dsz, int) and dsz > 0:
                                dim_map = {"default": int(dsz)}
                        except Exception:
                            pass

                    # Try serializing vectors_attr to dict (pydantic models often support .to_dict())
                    if not dim_map and vectors_attr is not None and hasattr(vectors_attr, "to_dict"):
                        try:
                            vd = vectors_attr.to_dict()
                            if isinstance(vd, dict):
                                if isinstance(vd.get("size"), int):
                                    dim_map = {"default": int(vd["size"])}
                                else:
                                    tmp: Dict[str, int] = {}
                                    for name, vp in vd.items():
                                        if isinstance(vp, dict) and isinstance(vp.get("size"), int):
                                            tmp[str(name)] = int(vp["size"])
                                    if tmp:
                                        dim_map = tmp
                        except Exception:
                            pass

                    # Named vectors: vectors is a dict of name -> VectorParams/dict
                    if not dim_map and isinstance(vectors_attr, dict):
                        tmp: Dict[str, int] = {}
                        for name, vp in vectors_attr.items():
                            sz = getattr(vp, "size", None)
                            if sz is None and isinstance(vp, dict):
                                sz = vp.get("size")
                            if isinstance(sz, int) and sz > 0:
                                tmp[str(name)] = int(sz)
                        if tmp:
                            dim_map = tmp

                    # Fallback to params attribute for default vector size
                    if not dim_map and cfg is not None and hasattr(cfg, "params"):
                        try:
                            params_attr = getattr(cfg, "params", None)
                            psz = getattr(params_attr, "size", None)
                            if isinstance(psz, int) and psz > 0:
                                dim_map = {"default": int(psz)}
                            elif hasattr(params_attr, "to_dict"):
                                pd = params_attr.to_dict()
                                if isinstance(pd, dict) and isinstance(pd.get("size"), int):
                                    dim_map = {"default": int(pd["size"])}
                        except Exception:
                            pass

                    # Dict-style config fallback
                    if not dim_map and isinstance(cfg, dict):
                        vecs = cfg.get("vectors")
                        if isinstance(vecs, dict):
                            tmp: Dict[str, int] = {}
                            for n, vp in vecs.items():
                                sz = None
                                if isinstance(vp, dict):
                                    sz = vp.get("size")
                                if isinstance(sz, int) and sz > 0:
                                    tmp[str(n)] = int(sz)
                            if tmp:
                                dim_map = tmp
                        else:
                            # Some older shapes may store default size at config['params']['size']
                            params = cfg.get("params")
                            if isinstance(params, dict) and isinstance(params.get("size"), int):
                                dim_map = {"default": int(params["size"])}

                    info["dimensions"] = dim_map if dim_map else {}

                    # If we don't have metadata and it's our naming convention, indicate it
                    if info["workspace_path"] == "Unknown" and collection_name.startswith("ws-"):
                        info["workspace_path"] = f"Hash-based collection: {collection_name}"

                except Exception:
                    # Keep defaults if collection info fails
                    pass

                # Per-collection: scroll one point to probe payload for model identifier
                model_identifier = "unknown"
                try:
                    scroll_res = self.client.scroll(
                        collection_name=collection_name,
                        limit=1,
                        with_payload=True,
                        with_vectors=True,
                    )
                    if isinstance(scroll_res, tuple):
                        pts = scroll_res[0]
                    else:
                        pts = getattr(scroll_res, "points", scroll_res)
                    payload = None
                    first = None
                    if pts:
                        first = pts[0]
                        payload = getattr(first, "payload", None)
                        if payload is None and isinstance(first, dict):
                            payload = first.get("payload")

                    if isinstance(payload, dict):
                        for key in ["embedding_model", "model", "embedder", "embedding_model_name"]:
                            val = payload.get(key)
                            if val:
                                model_identifier = self._canonicalize_model(str(val))
                                break

                    # If dimensions are still empty, attempt to infer from the scrolled point vectors
                    if not info.get("dimensions"):
                        dim_from_scroll: Dict[str, int] = {}
                        # Default vector
                        try:
                            vec_single = getattr(first, "vector", None)
                            if isinstance(vec_single, list) and vec_single:
                                dim_from_scroll = {"default": len(vec_single)}
                        except Exception:
                            pass
                        # Named vectors
                        if not dim_from_scroll:
                            try:
                                vecs_named = getattr(first, "vectors", None)
                                if isinstance(vecs_named, dict):
                                    tmp: Dict[str, int] = {}
                                    for n, v in vecs_named.items():
                                        if isinstance(v, list):
                                            tmp[str(n)] = len(v)
                                    if tmp:
                                        dim_from_scroll = tmp
                            except Exception:
                                pass
                        # Dict-style fallback
                        if not dim_from_scroll and isinstance(first, dict):
                            v_single = first.get("vector")
                            v_named = first.get("vectors")
                            if isinstance(v_single, list) and v_single:
                                dim_from_scroll = {"default": len(v_single)}
                            elif isinstance(v_named, dict):
                                tmp: Dict[str, int] = {}
                                for n, v in v_named.items():
                                    if isinstance(v, list):
                                        tmp[str(n)] = len(v)
                                if tmp:
                                    dim_from_scroll = tmp
                        if dim_from_scroll:
                            info["dimensions"] = dim_from_scroll
                except Exception:
                    # Ignore scroll errors; will fallback to metadata/config lookup
                    pass

                # No local config fallback; keep 'unknown' when payload lacks model info

                info["model_identifier"] = model_identifier or "unknown"
                collection_info_list.append(info)

            return collection_info_list
        except Exception as e:
            raise Exception(f"Failed to list collections: {e}")
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific collection, including dimensions and model identifier."""
        try:
            col_info = self.client.get_collection(collection_name)
            status = getattr(col_info, "status", "unknown")
            points_count = getattr(col_info, "points_count", 0)
            vectors_count = getattr(col_info, "vectors_count", 0)
            cfg_obj = getattr(col_info, "config", None)

            # Dimensions discovery (same logic as list_collections)
            dim_map: Dict[str, int] = {}
            cfg = cfg_obj

            vectors_attr = getattr(cfg, "vectors", None) if cfg is not None else None
            size_val = None

            # Default vector via VectorParams-like object
            if vectors_attr is not None and hasattr(vectors_attr, "size"):
                try:
                    size_val = getattr(vectors_attr, "size", None)
                    if isinstance(size_val, int) and size_val > 0:
                        dim_map = {"default": int(size_val)}
                except Exception:
                    pass

            # Some client versions expose a 'default' VectorParams
            if not dim_map and vectors_attr is not None and hasattr(vectors_attr, "default"):
                try:
                    d = getattr(vectors_attr, "default", None)
                    dsz = getattr(d, "size", None)
                    if isinstance(dsz, int) and dsz > 0:
                        dim_map = {"default": int(dsz)}
                except Exception:
                    pass

            # Try serializing vectors_attr to dict
            if not dim_map and vectors_attr is not None and hasattr(vectors_attr, "to_dict"):
                try:
                    vd = vectors_attr.to_dict()
                    if isinstance(vd, dict):
                        if isinstance(vd.get("size"), int):
                            dim_map = {"default": int(vd["size"])}
                        else:
                            tmp: Dict[str, int] = {}
                            for name, vp in vd.items():
                                if isinstance(vp, dict) and isinstance(vp.get("size"), int):
                                    tmp[str(name)] = int(vp["size"])
                            if tmp:
                                dim_map = tmp
                except Exception:
                    pass

            # Named vectors via dict mapping
            if not dim_map and isinstance(vectors_attr, dict):
                tmp: Dict[str, int] = {}
                for name, vp in vectors_attr.items():
                    sz = getattr(vp, "size", None)
                    if sz is None and isinstance(vp, dict):
                        sz = vp.get("size")
                    if isinstance(sz, int) and sz > 0:
                        tmp[str(name)] = int(sz)
                if tmp:
                    dim_map = tmp

            # Fallback to params attribute
            if not dim_map and cfg is not None and hasattr(cfg, "params"):
                try:
                    params_attr = getattr(cfg, "params", None)
                    psz = getattr(params_attr, "size", None)
                    if isinstance(psz, int) and psz > 0:
                        dim_map = {"default": int(psz)}
                    elif hasattr(params_attr, "to_dict"):
                        pd = params_attr.to_dict()
                        if isinstance(pd, dict) and isinstance(pd.get("size"), int):
                            dim_map = {"default": int(pd["size"])}
                except Exception:
                    pass

            # Dict-style config fallback
            if not dim_map and isinstance(cfg, dict):
                vecs = cfg.get("vectors")
                if isinstance(vecs, dict):
                    tmp: Dict[str, int] = {}
                    for n, vp in vecs.items():
                        sz = None
                        if isinstance(vp, dict):
                            sz = vp.get("size")
                        if isinstance(sz, int) and sz > 0:
                            tmp[str(n)] = int(sz)
                    if tmp:
                        dim_map = tmp
                else:
                    params = cfg.get("params")
                    if isinstance(params, dict) and isinstance(params.get("size"), int):
                        dim_map = {"default": int(params["size"])}

            # Workspace path via metadata map (single filtered query)
            workspace_path = "Unknown"
            try:
                metadata_results = self.client.query_points(
                    collection_name="code_index_metadata",
                    query=[0.0] * 1,
                    limit=1,
                    with_payload=True,
                    query_filter=Filter(
                        must=[FieldCondition(key="collection_name", match=MatchValue(value=collection_name))]
                    ),
                ).points
                if metadata_results:
                    payload = metadata_results[0].payload or {}
                    wp = payload.get("workspace_path")
                    if wp:
                        workspace_path = str(wp)
            except Exception:
                pass

            # Scroll one point for model identifier
            model_identifier = "unknown"
            try:
                scroll_res = self.client.scroll(
                    collection_name=collection_name,
                    limit=1,
                    with_payload=True,
                    with_vectors=True,
                )
                if isinstance(scroll_res, tuple):
                    pts = scroll_res[0]
                else:
                    pts = getattr(scroll_res, "points", scroll_res)
                payload = None
                first = None
                if pts:
                    first = pts[0]
                    payload = getattr(first, "payload", None)
                    if payload is None and isinstance(first, dict):
                        payload = first.get("payload")
                if isinstance(payload, dict):
                    for key in ["embedding_model", "model", "embedder", "embedding_model_name"]:
                        val = payload.get(key)
                        if val:
                            model_identifier = self._canonicalize_model(str(val))
                            break

                # If dimensions could not be derived from get_collection, infer from scrolled point vectors
                if not dim_map:
                    dim_from_scroll: Dict[str, int] = {}
                    # Default vector
                    try:
                        vec_single = getattr(first, "vector", None)
                        if isinstance(vec_single, list) and vec_single:
                            dim_from_scroll = {"default": len(vec_single)}
                    except Exception:
                        pass
                    # Named vectors
                    if not dim_from_scroll:
                        try:
                            vecs_named = getattr(first, "vectors", None)
                            if isinstance(vecs_named, dict):
                                tmp: Dict[str, int] = {}
                                for n, v in vecs_named.items():
                                    if isinstance(v, list):
                                        tmp[str(n)] = len(v)
                                if tmp:
                                    dim_from_scroll = tmp
                        except Exception:
                            pass
                    # Dict-style fallback
                    if not dim_from_scroll and isinstance(first, dict):
                        v_single = first.get("vector")
                        v_named = first.get("vectors")
                        if isinstance(v_single, list) and v_single:
                            dim_from_scroll = {"default": len(v_single)}
                        elif isinstance(v_named, dict):
                            tmp: Dict[str, int] = {}
                            for n, v in v_named.items():
                                if isinstance(v, list):
                                    tmp[str(n)] = len(v)
                            if tmp:
                                dim_from_scroll = tmp
                    if dim_from_scroll:
                        dim_map = dim_from_scroll
            except Exception:
                pass

            # No local config fallback; keep 'unknown' when payload lacks model info

            return {
                "name": collection_name,
                "status": status,
                "points_count": points_count,
                "vectors_count": vectors_count,
                "config": str(cfg_obj),
                "workspace_path": workspace_path,
                "dimensions": dim_map if dim_map else {},
                "model_identifier": model_identifier or "unknown",
            }
        except Exception as e:
            raise Exception(f"Failed to get collection info: {e}")
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            raise Exception(f"Failed to delete collection: {e}")
    
    def prune_old_collections(self, older_than_days: int = 30) -> List[str]:
        """Prune collections older than specified days."""
        # This would require storing timestamps in collections
        # For now, we'll just return an empty list
        return []