#!/usr/bin/env python3
"""
Script to completely delete all Qdrant collections and cache files for fresh start with KiloCode compatibility.
"""
import os
import sys
import shutil
import glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.vector_store import QdrantVectorStore
from qdrant_client import QdrantClient


def delete_all_collections():
    """Delete all collections in Qdrant and clear cache files."""
    print("=== Deleting All Qdrant Collections ===")
    
    # Create a basic config to connect to Qdrant
    config = Config()
    config.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    
    # Create Qdrant client directly
    client = QdrantClient(url=config.qdrant_url)
    
    try:
        # Get list of all collections
        collections = client.get_collections()
        collection_names = [collection.name for collection in collections.collections]
        
        print(f"Found {len(collection_names)} collections:")
        for name in collection_names:
            print(f"  - {name}")
        
        # Delete each collection
        for collection_name in collection_names:
            if collection_name != "code_index_metadata":  # Keep metadata collection
                print(f"Deleting collection: {collection_name}")
                client.delete_collection(collection_name=collection_name)
        
        # Also delete metadata collection for clean slate
        try:
            print("Deleting metadata collection...")
            client.delete_collection(collection_name="code_index_metadata")
        except Exception as e:
            print(f"Could not delete metadata collection: {e}")
        
        print("✓ All collections deleted successfully!")
        
        # Verify no collections remain
        collections = client.get_collections()
        remaining = [collection.name for collection in collections.collections]
        if remaining:
            print(f"Remaining collections: {remaining}")
        else:
            print("✓ No collections remaining")
            
    except Exception as e:
        print(f"Error deleting collections: {e}")
        return False
    
    # Clear cache files
    print("\n=== Clearing Cache Files ===")
    cache_dir = os.path.expanduser("~/.cache/code_index")
    if os.path.exists(cache_dir):
        try:
            cache_files = glob.glob(os.path.join(cache_dir, "*.json"))
            print(f"Found {len(cache_files)} cache files to delete")
            for cache_file in cache_files:
                os.remove(cache_file)
                print(f"  Deleted: {os.path.basename(cache_file)}")
            print("✓ All cache files cleared!")
        except Exception as e:
            print(f"Warning: Could not clear all cache files: {e}")
    else:
        print("No cache directory found")
    
    return True


if __name__ == "__main__":
    success = delete_all_collections()
    sys.exit(0 if success else 1)