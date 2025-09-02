"""
Qdrant vector store for the code index tool.
"""
import hashlib
import os
import time
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from code_index.config import Config


class QdrantVectorStore:
    """Interface with Qdrant vector database."""

    def __init__(self, config: Config):
        """Initialize Qdrant client with configuration."""
        self.workspace_path = os.path.abspath(config.workspace_path)
        self.collection_name = self._generate_collection_name()

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

        # Persist connection parameters for fallback strategies
        self._host = host
        self._https = https
        self._http_port = port
        self._api_key = config.qdrant_api_key
        self._url = url
        self._config = config

        # Prefer using the consolidated URL form first (more robust in newer clients)
        # We'll fall back to explicit host/port with gRPC if needed during initialize()
        self.client = QdrantClient(
            url=url,
            api_key=config.qdrant_api_key
        )

        # Vector size comes from configuration (config-first).
        # It will be validated during initialize(); must be a positive integer.
        self.vector_size: Optional[int] = config.embedding_length

    def _generate_collection_name(self) -> str:
        """Generate collection name based on workspace path.

        Aligns with Kilo Code extension convention:
        - Prefix: "ws-"
        - Hash: sha256(workspace_path) first 16 hex chars
        """
        workspace_hash = hashlib.sha256(self.workspace_path.encode()).hexdigest()
        return f"ws-{workspace_hash[:16]}"

    def _init_metadata_collection(self):
        """Initialize metadata collection for storing workspace information."""
        try:
            metadata_collection = "code_index_metadata"
            collections = self.client.get_collections()
            collection_names = [
                collection.name for collection in collections.collections]

            if metadata_collection not in collection_names:
                self.client.create_collection(
                    collection_name=metadata_collection,
                    vectors_config=VectorParams(
                        size=1,  # Minimal vector size for metadata
                        distance=Distance.COSINE
                    )
                )
        except Exception:
            # If we can't create metadata collection, continue without it
            pass

    def _store_collection_metadata(self):
        """Store metadata about this collection."""
        try:
            # Ensure metadata collection exists first
            self._init_metadata_collection()
            
            metadata_collection = "code_index_metadata"
            # Store workspace path mapping
            metadata = {
                "collection_name": self.collection_name,
                "workspace_path": self.workspace_path,
                "created_date": time.time(),
                "indexed_date": time.time()
            }

            # Create a simple vector for storage (all zeros)
            vector = [0.0] * 1

            # Create point with metadata using a proper UUID
            import uuid
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, self.collection_name))
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=metadata
            )

            self.client.upsert(
                collection_name=metadata_collection,
                points=[point]
            )
        except Exception as e:
            # If we can't store metadata, continue without it
            print(f"Warning: Could not store collection metadata: {e}")
            pass

    def initialize(self) -> bool:
        """
        Initialize Qdrant collection.

        Returns:
            True if a new collection was created, False if it already existed
        """
        try:
            # First attempt using current client (URL-based)
            collections = self.client.get_collections()
        except Exception as e1:
            # Fallback: try gRPC on typical port (http_port + 1)
            grpc_port = (self._http_port
                         + 1) if isinstance(self._http_port, int) else 6334
            try:
                self.client = QdrantClient(
                    host=self._host,
                    port=grpc_port,
                    https=self._https,
                    api_key=self._api_key,
                    prefer_grpc=True,
                )
                collections = self.client.get_collections()
            except Exception as e2:
                raise Exception(
                    f"Failed to initialize Qdrant collection: primary HTTP failed: {e1}; "
                    f"fallback gRPC failed: {e2}"
                )

        collection_names = [collection.name for collection in collections.collections]

        if self.collection_name not in collection_names:
            # Require embedding_length set via configuration
            if (
                self.vector_size is None
                or not isinstance(self.vector_size, int)
                or self.vector_size <= 0
            ):
                raise Exception(
                    "Config error: Please set 'embedding_length' in code_index.json to match the Ollama model (e.g., 1024 for Qwen, 768 for nomic)."
                )

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            # Create payload indexes
            self._create_payload_indexes()
            
            # Store metadata about this collection
            self._store_collection_metadata()
            return True
        else:
            # Collection already exists, but ensure metadata is stored
            self._store_collection_metadata()
            return False

    def _create_payload_indexes(self) -> None:
        """Create payload indexes for efficient filtering."""
        try:
            # Create indexes for path segments (up to 5 levels deep)
            for i in range(5):
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=f"pathSegments.{i}",
                    field_schema="keyword"
                )
            # Optional: index for embedding model identifier to enable future filtering
            # This is additive and should not interfere with existing payload schema.
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="embedding_model",
                    field_schema="keyword"
                )
            except Exception:
                # If the backend/version does not support this or index already exists, ignore.
                pass
        except Exception:
            # Ignore errors if indexes already exist
            pass

    # ------------------------------
    # Post-retrieval weighting helpers
    # ------------------------------
    def _filetype_weight(self, file_path: str) -> float:
        """Weight by file extension using config.search_file_type_weights."""
        try:
            ext = os.path.splitext(file_path.lower())[1]
            return float(getattr(self._config, "search_file_type_weights", {}).get(ext, 1.0))
        except Exception:
            return 1.0

    def _path_weight(self, file_path: str) -> float:
        """Aggregate multiplicative boosts for any matching path pattern rules."""
        try:
            p = file_path.lower()
            weight = 1.0
            for rule in getattr(self._config, "search_path_boosts", []):
                try:
                    pat = str(rule.get("pattern", "")).lower()
                    w = float(rule.get("weight", 1.0))
                except Exception:
                    continue
                if pat and pat in p:
                    weight *= w
            return weight
        except Exception:
            return 1.0

    def _language_weight(self, lang: str) -> float:
        """Optional language multiplier from config.search_language_boosts."""
        try:
            if not lang:
                return 1.0
            return float(getattr(self._config, "search_language_boosts", {}).get(lang.lower(), 1.0))
        except Exception:
            return 1.0

    def _exclude_match(self, file_path: str) -> bool:
        """Return True if file_path matches any configured exclude pattern (substring)."""
        try:
            p = file_path.lower()
            for pat in getattr(self._config, "search_exclude_patterns", []):
                try:
                    if str(pat).lower() in p:
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def upsert_points(self, points: List[Dict[str, Any]]) -> None:
        """
        Upsert points into Qdrant collection.

        Args:
            points: List of point dictionaries with id, vector, and payload
        """
        if not points:
            return

        try:
            # Convert to PointStruct objects and add path segments
            point_structs = []
            for point in points:
                payload = point.get("payload", {})
                if payload and "filePath" in payload:
                    # Add path segments for efficient filtering
                    file_path = payload["filePath"]
                    path_segments = file_path.split(os.sep)
                    payload["pathSegments"] = {
                        str(i): segment for i, segment in enumerate(path_segments)
                    }

                point_structs.append(
                    PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=payload
                    )
                )

            self.client.upsert(
                collection_name=self.collection_name,
                points=point_structs
            )
        except Exception as e:
            raise Exception(f"Failed to upsert points: {e}")

    def _is_payload_valid(self, payload: Dict[str, Any]) -> bool:
        """Check if payload is valid (KiloCode-compatible)."""
        if not payload:
            return False
        # Match KiloCode's expected fields
        required_fields = ["filePath", "codeChunk", "startLine", "endLine"]
        return all(field in payload for field in required_fields)

    def search(self, query_vector: List[float], directory_prefix: Optional[str] = None,
               min_score: float = 0.4, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Vector to search for
            directory_prefix: Optional directory prefix to filter results
            min_score: Minimum score threshold
            max_results: Maximum number of results to return

        Returns:
            List of search results
        """
        try:
            # Build filter if directory prefix is specified
            search_filter = None
            if directory_prefix:
                # Normalize the directory prefix
                normalized_prefix = os.path.normpath(directory_prefix).strip(os.sep)
                if normalized_prefix:
                    # Split into path segments
                    segments = normalized_prefix.split(os.sep)
                    if segments:
                        # Create filter conditions for each segment
                        must_conditions = [
                            FieldCondition(
                                key=f"pathSegments.{i}",
                                match=MatchValue(value=segment)
                            )
                            for i, segment in enumerate(segments)
                        ]
                        search_filter = Filter(must=must_conditions)

            # Perform search
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=search_filter,
                limit=max_results,
                score_threshold=min_score,
                with_payload=True
            )

            if not results or not results.points:
                return []

            # Convert results to dictionary format (KiloCode-compatible)
            hits = [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": {
                        "filePath": result.payload.get("filePath", ""),
                        "codeChunk": result.payload.get("codeChunk", ""),
                        "startLine": result.payload.get("startLine", 0),
                        "endLine": result.payload.get("endLine", 0),
                        "type": result.payload.get("type", "")
                    }
                }
                for result in results.points if self._is_payload_valid(result.payload)
            ]

            # Apply excludes and compute adjusted scores using config weights
            filtered_hits = []
            for h in hits:
                fp = h["payload"].get("filePath", "")
                if self._exclude_match(fp):
                    continue
                file_w = self._filetype_weight(fp)
                path_w = self._path_weight(fp)
                lang_w = self._language_weight(h["payload"].get("type", ""))
                base = h.get("score", 0.0) or 0.0
                adjusted = base * file_w * path_w * lang_w
                h["adjustedScore"] = adjusted
                filtered_hits.append(h)

            # Stable sort: primarily by adjustedScore, fallback by base score
            filtered_hits.sort(
                key=lambda x: (x.get("adjustedScore", x.get("score", 0.0)), x.get("score", 0.0)),
                reverse=True
            )

            return filtered_hits
        except Exception as e:
            raise Exception(f"Failed to search: {e}")

    def delete_points_by_file_path(self, file_path: str) -> None:
        """
        Delete points by file path.

        Args:
            file_path: Path of the file to delete points for
        """
        try:
            # Split file path into segments
            path_segments = file_path.split(os.sep)

            # Create filter conditions for each segment
            must_conditions = [
                FieldCondition(
                    key=f"pathSegments.{i}",
                    match=MatchValue(value=segment)
                )
                for i, segment in enumerate(path_segments)
            ]

            # Delete points matching the filter
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=must_conditions)
            )
        except Exception as e:
            raise Exception(f"Failed to delete points by file path: {e}")

    def clear_collection(self) -> None:
        """Clear all points from collection."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter()
            )
        except Exception as e:
            raise Exception(f"Failed to clear collection: {e}")

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
        except Exception as e:
            raise Exception(f"Failed to delete collection: {e}")

    def collection_exists(self) -> bool:
        """Check if the collection exists."""
        try:
            collections = self.client.get_collections()
            return self.collection_name in [collection.name for collection in collections.collections]
        except Exception:
            return False

