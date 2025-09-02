#!/usr/bin/env python3
"""
Migrate code_index collection to KiloCode-compatible collection.

- Source collection: code_index_{sha16(abs_workspace_path)}
- Target collection: ws-{sha16(abs_workspace_path)}  (KiloCode convention)
- Payload remap:
    file_path -> filePath
    content -> codeChunk
    start_line -> startLine
    end_line -> endLine
    + pathSegments.{i} derived from filePath
- Vector size: detected from first point in source; ensures target collection dimension matches
- Qdrant URL: from env QDRANT_URL or default http://localhost:6333
"""

import argparse
import hashlib
import os
import sys
import time
from typing import Dict, Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import VectorParams, Distance

DEFAULT_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

def sha16_path(path: str) -> str:
    return hashlib.sha256(os.path.abspath(path).encode()).hexdigest()[:16]

def source_collection(workspace_path: str) -> str:
    # code_index_<sha16>
    return f"code_index_{sha16_path(workspace_path)}"

def target_collection(workspace_path: str) -> str:
    # KiloCode convention: ws-<sha16>
    return f"ws-{sha16_path(workspace_path)}"

def ensure_collection(client: QdrantClient, name: str, vector_size: int) -> None:
    try:
        info = client.get_collection(name)
        # Attempt to read existing vector size
        existing_size = None
        try:
            vecs = info.config.params.vectors
            if isinstance(vecs, dict):
                existing_size = vecs.get("size")
            elif hasattr(vecs, "size"):
                existing_size = vecs.size
        except Exception:
            pass

        if existing_size is None or int(existing_size) != vector_size:
            # Recreate with proper dimension
            try:
                client.delete_collection(name)
            except Exception:
                # ignore if it doesn't exist
                pass
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
    except Exception:
        # Not existing; create
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # Create payload indexes for pathSegments.{i}
    for i in range(5):
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=f"pathSegments.{i}",
                field_schema="keyword",  # string keyword
            )
        except Exception:
            # ignore if already exists
            pass

def detect_vector_size(client: QdrantClient, collection: str) -> Optional[int]:
    """Scroll one point to read vector length."""
    try:
        points, _ = client.scroll(collection_name=collection, limit=1, with_vectors=True, with_payload=False)
        if points:
            vec = points[0].vector
            if isinstance(vec, list):
                return len(vec)
    except Exception:
        return None
    return None

def transform_payload(payload: Dict[str, Any], workspace_path: str) -> Dict[str, Any]:
    # Map code_index keys to KiloCode expected keys
    file_path = payload.get("file_path") or payload.get("filePath")
    content = payload.get("content") or payload.get("codeChunk")
    start_line = payload.get("start_line") or payload.get("startLine")
    end_line = payload.get("end_line") or payload.get("endLine")

    # Store relative path to workspace
    if file_path:
        try:
            rel = os.path.relpath(file_path, os.path.abspath(workspace_path))
        except Exception:
            rel = file_path
    else:
        rel = "unknown"

    # Build pathSegments.{i} from POSIX-like segments
    segments = rel.replace("\\", "/").split("/")
    path_segments = {str(i): seg for i, seg in enumerate([s for s in segments if s])}

    out = {
        "filePath": rel,
        "codeChunk": content if isinstance(content, str) else (content or ""),
        "startLine": int(start_line) if start_line is not None else 0,
        "endLine": int(end_line) if end_line is not None else 0,
        "pathSegments": path_segments,
    }
    return out

def migrate(client: QdrantClient, src: str, dst: str, workspace_path: str, batch: int = 200) -> None:
    # Detect vector size
    vec_size = detect_vector_size(client, src)
    if not vec_size:
        print(f"Error: Could not detect vector size from source collection '{src}'.")
        sys.exit(1)

    ensure_collection(client, dst, vec_size)

    # Scroll and upsert in batches
    scroll_filter = None  # all points
    next_page = None
    total = 0
    while True:
        points, next_page = client.scroll(
            collection_name=src,
            scroll_filter=scroll_filter,
            with_vectors=True,
            with_payload=True,
            limit=batch,
            offset=next_page,
        )
        if not points:
            break

        out_points = []
        for p in points:
            payload = p.payload or {}
            new_payload = transform_payload(payload, workspace_path)
            out_points.append(
                {
                    "id": p.id,
                    "vector": p.vector,
                    "payload": new_payload,
                }
            )

        # Upsert in sub-batches with retry/backoff to avoid HTTP write timeouts
        def upsert_with_retry(points_batch: List[Dict[str, Any]], max_retries: int = 5, base_sleep: float = 0.5):
            attempt = 0
            while True:
                try:
                    client.upsert(collection_name=dst, points=points_batch, wait=True)
                    return
                except ResponseHandlingException as e:
                    msg = str(e)
                    if "timed out" in msg or "Timeout" in msg or "connect" in msg:
                        if attempt < max_retries:
                            delay = base_sleep * (2 ** attempt)
                            time.sleep(delay)
                            attempt += 1
                            continue
                    raise
                except Exception as e:
                    # Retry a few times on generic transient errors
                    msg = str(e)
                    if ("timed out" in msg or "Timeout" in msg or "temporarily" in msg or "unavailable" in msg) and attempt < max_retries:
                        delay = base_sleep * (2 ** attempt)
                        time.sleep(delay)
                        attempt += 1
                        continue
                    raise

        if out_points:
            # sub-batch size
            chunk = 100
            for i in range(0, len(out_points), chunk):
                sub = out_points[i:i+chunk]
                upsert_with_retry(sub)
                total += len(sub)
                if total % 500 == 0:
                    # light pacing to reduce pressure
                    time.sleep(0.1)
            print(f"Migrated {total} points...", flush=True)

        if next_page is None:
            break

    print(f"Migration complete. Total points migrated: {total}")

def main():
    ap = argparse.ArgumentParser(description="Migrate code_index collection to KiloCode-compatible schema")
    ap.add_argument("--workspace", required=True, help="Absolute path to workspace (e.g., /home/james/kanban_frontend/kanban_api)")
    ap.add_argument("--qdrant", default=DEFAULT_QDRANT_URL, help=f"Qdrant URL (default: {DEFAULT_QDRANT_URL})")
    args = ap.parse_args()

    ws = os.path.abspath(args.workspace)
    src = source_collection(ws)
    dst = target_collection(ws)

    client = QdrantClient(url=args.qdrant, timeout=60.0)

    # Sanity check that source exists
    try:
        info = client.get_collection(src)
    except Exception as e:
        print(f"Error: Source collection '{src}' not found or not accessible at {args.qdrant}: {e}")
        sys.exit(1)

    print(f"Source: {src}")
    print(f"Target: {dst}")
    print(f"Qdrant: {args.qdrant}")
    migrate(client, src, dst, ws)

if __name__ == "__main__":
    main()