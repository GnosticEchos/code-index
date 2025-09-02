#!/usr/bin/env python3
"""
Script to identify workspace paths associated with Qdrant collections.
"""
import hashlib
import os

# Common workspace paths to check
common_paths = [
    "/home/james/kanban_frontend/code_index",
    "/home/james/kanban_frontend/RESEARCH/kilocode-main",
    "/home/james/kanban_frontend",
    "/home/james",
    "/home/james/code",
    "/home/james/projects",
    "/home/james/kanban_frontend/code_index/src",
    "/home/james/kanban_frontend/code_index/src/code_index"
]

# Collection names from Qdrant
collections = [
    "code_index_922a3c8225ae94a8",
    "ws-3a53e730d1e351ba",
    "ws-6218cfe5b35e611e",
    "ws-0399fa2b02a056d1",
    "code_index_28c224411e907efc",
    "ws-47cb73481c0f8f9b",
    "ws-a6447323e6024049",  # This is the one from code_index.json
    "ws-491a59846b84697a",  # This is the one for current directory
    "ws-28c224411e907efc",
    "code_index_49df9a81dfd66579",
    "code_index_a85371ec34f43f08",
    "ws-a85371ec34f43f08",
    "ws-922a3c8225ae94a8",
    "ws-28c3774e0c54b916"
]

def generate_collection_name(workspace_path):
    """Generate collection name based on workspace path."""
    workspace_hash = hashlib.sha256(os.path.abspath(workspace_path).encode()).hexdigest()
    return f"ws-{workspace_hash[:16]}"

print("Matching collections to workspace paths:")
print("=" * 50)

for path in common_paths:
    collection_name = generate_collection_name(path)
    if collection_name in collections:
        print(f"✓ {collection_name} <- {path}")
    else:
        print(f"  {collection_name} <- {path} (not found)")

print("\nUnmatched collections:")
print("=" * 50)
matched_collections = {generate_collection_name(path) for path in common_paths}
for collection in collections:
    if collection not in matched_collections:
        print(f"  {collection}")