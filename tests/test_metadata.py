#!/usr/bin/env python3
"""
Test script to verify metadata storage functionality.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.vector_store import QdrantVectorStore


def test_metadata_storage():
    """Test that metadata storage works correctly."""
    print("=== Testing Metadata Storage ===")
    
    # Load config
    config = Config.from_file("current_config.json")
    print(f"Workspace path: {config.workspace_path}")
    
    # Initialize vector store
    vector_store = QdrantVectorStore(config)
    print(f"Collection name: {vector_store.collection_name}")
    
    # Test initialization (should create metadata collection)
    print("Initializing vector store...")
    created = vector_store.initialize()
    print(f"Collection created: {created}")
    
    # Check if metadata collection exists
    try:
        collections = vector_store.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        has_metadata_collection = "code_index_metadata" in collection_names
        print(f"Metadata collection exists: {has_metadata_collection}")
        
        if has_metadata_collection:
            print("✓ Metadata collection created successfully")
        else:
            print("❌ Metadata collection was not created")
            
        # Check if current collection exists
        has_main_collection = vector_store.collection_name in collection_names
        print(f"Main collection exists: {has_main_collection}")
        
        if has_main_collection:
            print("✓ Main collection exists")
        else:
            print("❌ Main collection does not exist")
            
        assert has_metadata_collection and has_main_collection
        
    except Exception as e:
        print(f"Error checking collections: {e}")
        assert False


if __name__ == "__main__":
    success = test_metadata_storage()
    sys.exit(0 if success else 1)