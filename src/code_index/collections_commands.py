"""
Collection management commands for the code index tool.
"""
import sys
import re
import logging
from typing import Optional

import click
from qdrant_client.models import Filter, FieldCondition, MatchValue
from code_index.config import Config
from code_index.collections import CollectionManager
from code_index.cache import delete_collection_cache, clear_all_caches

logger = logging.getLogger(__name__)

# Precompiled regex for 16 lowercase hex chars
HEX16 = re.compile(r"^[0-9a-f]{16}$")

def _resolve_canonical_id_for_delete(collection_manager: CollectionManager, collection_name: str) -> Optional[str]:
    """
    Resolve the canonical collection id (16 hex chars) used in cache filenames.

    Resolution order:
      1) Probe per-point payload for a known id (e.g., 'collection_id') via O(1) scroll(limit=1).
      2) If name matches 'ws-<hex16>', derive suffix.
      3) Otherwise, return None.

    This function must be resilient to backend errors and never raise.
    """
    # Using precompiled HEX16 at module scope

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
                    if isinstance(val, str) and HEX16.match(val):
                        return val
    except Exception:
        # Ignore probe failures; continue with name-based derivation
        pass

    # 2) Derive from naming pattern 'ws-<id>'
    try:
        if isinstance(collection_name, str) and collection_name.startswith("ws-"):
            suffix = collection_name[3:]
            if HEX16.match(suffix):
                return suffix
    except Exception:
        pass

    # 3) Unresolved
    return None


@click.command()
@click.option('--detailed', is_flag=True, help='Show detailed information')
def list_collections(detailed: bool):
    """List all collections."""
    try:
        # Use default config to connect to Qdrant
        cfg = Config()
        collection_manager = CollectionManager(cfg)
        
        collections = collection_manager.list_collections()
        
        if not collections:
            print("No collections found.")
            return
        
        print(f"{'Name':<30} {'Points':<8} {'Dim':<18} {'Model':<24} {'Workspace Path'}")
        print("-" * 100)
        
        for collection in collections:
            name = collection.get("name", "")
            points = collection.get("points_count", 0)
            workspace = collection.get("workspace_path", "Unknown")
            dims = collection.get("dimensions", {}) or {}
            model = collection.get("model_identifier", "unknown") or "unknown"

            # Dimension formatting:
            # - default only: show just the size (e.g., "768")
            # - named vectors: "name:size" pairs, comma-separated (e.g., "text:768,img:512")
            if len(dims) == 1 and "default" in dims:
                dim_display = str(dims.get("default"))
            else:
                pairs = [f"{k}:{v}" for k, v in dims.items()]
                dim_display = ",".join(pairs) if pairs else ""

            if detailed:
                print(f"{name:<30} {points:<8} {dim_display:<18} {model:<24} {workspace}")
            else:
                # Truncate long workspace paths
                ws = workspace
                if len(ws) > 50:
                    ws = ws[:47] + "..."
                print(f"{name:<30} {points:<8} {dim_display:<18} {model:<24} {ws}")
                
    except Exception as e:
        print(f"Error listing collections: {e}")
        sys.exit(1)


@click.command()
@click.argument('collection_name')
def collection_info(collection_name: str):
    """Show detailed information about a collection."""
    try:
        cfg = Config()
        collection_manager = CollectionManager(cfg)
        
        info = collection_manager.get_collection_info(collection_name)
        
        print(f"Collection: {info['name']}")
        print(f"Status: {info['status']}")
        print(f"Points: {info['points_count']}")
        print(f"Vectors: {info['vectors_count']}")
        #print(f"Config: {info['config']}")
        
        # Try to get workspace path from metadata (preserve existing behavior)
        try:
            points = []
            scroll_res = collection_manager.client.scroll(
                collection_name="code_index_metadata",
                limit=1,
                with_payload=True,
                with_vectors=False,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="collection_name",
                            match=MatchValue(value=collection_name),
                        )
                    ]
                ),
            )
            points = scroll_res[0] if isinstance(scroll_res, tuple) else getattr(scroll_res, "points", [])
            if points:
                payload = getattr(points[0], "payload", None) or (points[0].get("payload") if isinstance(points[0], dict) else None)
                if isinstance(payload, dict) and "workspace_path" in payload:
                    print(f"Workspace Path: {payload['workspace_path']}")
        except Exception:
            pass

        # Print dimensions
        dims = info.get("dimensions", {}) or {}
        if len(dims) == 1 and "default" in dims:
            print(f"Dimension: {dims.get('default')}")
        else:
            for name, size in dims.items():
                print(f"Vector {name}: {size}")

        # Print model identifier
        print(f"Model: {info.get('model_identifier', 'unknown') or 'unknown'}")
        
    except Exception as e:
        print(f"Error getting collection info: {e}")
        sys.exit(1)


@click.command()
@click.argument('collection_name')
@click.option('--yes', '-y', is_flag=True, help='Confirm deletion non-interactively; skip confirmation prompt')
def delete_collection(collection_name: str, yes: bool = False):
    """Delete a collection.

    Note: Also removes the local cache entry (cache_{canonical-id}.json) when the canonical id can be resolved.
    """
    try:
        cfg = Config()
        collection_manager = CollectionManager(cfg)

        # Resolve canonical id before deletion to avoid relying on post-delete state
        canonical_id = _resolve_canonical_id_for_delete(collection_manager, collection_name)

        # Confirm deletion (interactive unless --yes/-y provided)
        if not yes:
            try:
                # Preferred interactive confirmation with automatic abort on "no"
                click.confirm(
                    f"Are you sure you want to delete collection '{collection_name}'?",
                    default=False,
                    abort=True,
                )
            except click.Abort:
                # User explicitly chose "no" or aborted
                print("Deletion cancelled.")
                return
            except Exception:
                # Non-interactive environments (e.g., pytest capture) — fall back to raw input
                try:
                    resp = input(f"Are you sure you want to delete collection '{collection_name}'? (y/N): ")
                except Exception:
                    print("Deletion cancelled.")
                    return
                if (resp or "").lower() != 'y':
                    print("Deletion cancelled.")
                    return

        collection_manager.delete_collection(collection_name)
        print(f"Collection '{collection_name}' deleted successfully.")

        # Cache cleanup (best-effort)
        if canonical_id:
            try:
                removed = delete_collection_cache(canonical_id, cfg)
            except Exception:
                removed = 0
            print(f"Cache: removed {removed} file(s) for canonical id {canonical_id}.")
        else:
            print(f"Cache: skipped cleanup; canonical id for '{collection_name}' could not be resolved.")
        
    except Exception as e:
        print(f"Error deleting collection: {e}")
        sys.exit(1)


@click.command()
@click.option('--older-than', type=int, default=30, help='Prune collections older than specified days')
def prune_collections(older_than: int):
    """Prune old collections."""
    try:
        cfg = Config()
        collection_manager = CollectionManager(cfg)
        
        deleted_collections = collection_manager.prune_old_collections(older_than)
        
        if deleted_collections:
            print(f"Pruned {len(deleted_collections)} collections:")
            for collection in deleted_collections:
                print(f"  - {collection}")
        else:
            print("No collections to prune.")
            
    except Exception as e:
        print(f"Error pruning collections: {e}")
        sys.exit(1)


def _extract_collection_names(obj) -> list[str]:
    """
    Best-effort extraction of collection names from Qdrant client get_collections() result.
    Supports common shapes:
      - Response with '.collections' attribute (list of objects with '.name')
      - Dict with 'collections' key -> list of dicts/objects
      - List[str] of names
      - List[dict] with 'name' or 'collection_name'
      - List[object] with '.name' or '.collection_name'
    """
    names: set[str] = set()
    try:
        iterable = None
        if hasattr(obj, "collections"):
            iterable = getattr(obj, "collections", None)
        elif isinstance(obj, dict):
            iterable = obj.get("collections", obj)
        else:
            iterable = obj

        if not iterable:
            return []

        for item in iterable:
            name = None
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                name = item.get("name") or item.get("collection_name")
            else:
                name = getattr(item, "name", None) or getattr(item, "collection_name", None)
            if isinstance(name, str) and name:
                names.add(name)
    except Exception:
        # Be resilient; return what we have
        pass
    return sorted(names)


@click.command()
@click.option('--yes', '-y', 'yes', is_flag=True, help='Skip confirmation prompt')
@click.option('--dry-run', is_flag=True, help='Show intended collections to delete, then exit without deleting or clearing cache')
@click.option('--keep-metadata', is_flag=True, help='Do not delete code_index_metadata (default is to delete it)')
def clear_all_collections(yes: bool, dry_run: bool, keep_metadata: bool):
    """
    Delete all Qdrant collections and clear local cache files.

    Behavior:
    - Discovers collections via CollectionManager(...).client.get_collections()
    - Deletes all collections returned, including 'code_index_metadata' by default
      unless --keep-metadata is provided
    - Per-collection failures are logged and do not abort the run
    - 404 / "not found" errors are treated as already absent
    - After deletions (unless --dry-run), clears all cache_*.json files from the application cache directory
    """
    try:
        cfg = Config()
        collection_manager = CollectionManager(cfg)
        client = collection_manager.client
    except Exception as e:
        print(f"Error initializing collection manager: {e}")
        sys.exit(1)

    # Discover collections
    try:
        discovered = client.get_collections()
    except Exception as e:
        print(f"Error retrieving collections list: {e}")
        sys.exit(1)

    all_names = _extract_collection_names(discovered)
    total_found = len(all_names)

    # Determine targets
    targets = [n for n in all_names if (n != "code_index_metadata" or not keep_metadata)]
    
    if not dry_run and len(targets) == 0:
        print("No collections targeted for deletion (respecting flags). Proceeding to cache cleanup.")
    
    if dry_run:
        print(f"Dry run: would delete {len(targets)} collection(s):")
        for n in targets:
            print(f"  - {n}")
        if not keep_metadata and "code_index_metadata" in all_names:
            print("Note: 'code_index_metadata' is included by default. Use --keep-metadata to preserve it.")
        print("No deletions performed. Cache not cleared.")
        return

    # Confirmation, unless --yes
    if not yes:
        try:
            target_list_preview = ", ".join(targets) if targets else "(none)"
            click.confirm(
                f"This will delete {len(targets)} collection(s): {target_list_preview}\n"
                f"It will also clear local cache files (cache_*.json). Continue?",
                default=False,
                abort=True,
            )
        except click.Abort:
            print("Deletion cancelled.")
            return
        except Exception:
            # Non-interactive fallback
            try:
                resp = input(
                    f"This will delete {len(targets)} collection(s): {target_list_preview}. "
                    f"Also clears local cache files. Proceed? (y/N): "
                )
            except Exception:
                print("Deletion cancelled.")
                return
            if (resp or "").lower() != "y":
                print("Deletion cancelled.")
                return

    # Perform deletions (best-effort)
    deleted = 0
    already_absent = 0
    failed = 0

    for name in targets:
        try:
            client.delete_collection(name)
            deleted += 1
        except Exception as e:
            msg = str(e).lower()
            if "not found" in msg or "doesn't exist" in msg or "404" in msg:
                already_absent += 1
                logger.info(f"Collection '{name}' already absent; continuing.")
            else:
                failed += 1
                logger.error(f"Failed to delete collection '{name}': {e}")

    # Clear cache artifacts
    removed_cache = 0
    try:
        removed_cache = clear_all_caches(cfg)
    except Exception:
        removed_cache = 0  # helper is resilient; continue

    # User-facing summaries
    print(f"Collections: found {total_found}, deleted {deleted}, already absent {already_absent}, failed {failed}.")
    print(f"Cache: removed {removed_cache} file(s) from application cache directory.")
    # Log summaries respecting global logging level
    logger.info(
        f"Collections summary — found={total_found} deleted={deleted} already_absent={already_absent} failed={failed}"
    )
    logger.info(f"Cache cleanup summary — removed={removed_cache} file(s)")