#!/usr/bin/env python3
"""
Test script to verify metadata storage is working correctly.
"""
import os
import sys
import tempfile
import shutil
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.vector_store import QdrantVectorStore


def test_metadata_storage():
    """Test that metadata storage works correctly."""
    print("=== Testing Metadata Storage ===")
    
    # Create temporary workspace
    test_dir = tempfile.mkdtemp(prefix="metadata_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Create test file
        test_file = os.path.join(test_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    print('Hello World')\n")
        
        # Create configuration
        config_file = os.path.join(test_dir, "code_index.json")
        config_data = {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "nomic-embed-text:latest",
            "qdrant_url": "http://localhost:6333",
            "workspace_path": test_dir,
            "extensions": [".py"],
            "embedding_length": 768,
            "max_file_size_bytes": 1048576,
            "batch_segment_threshold": 60,
            "search_min_score": 0.4,
            "search_max_results": 50
        }
        
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        
        config = Config.from_file(config_file)
        
        # Initialize vector store
        vector_store = QdrantVectorStore(config)
        
        # Test initialization (should create metadata collection)
        print("Initializing vector store...")
        created = vector_store.initialize()
        print(f"Collection created: {created}")
        
        # Check if metadata collection exists
        try:
            import requests
            response = requests.get("http://localhost:6333/collections/code_index_metadata")
            if response.status_code == 200:
                print("✓ Metadata collection exists")
            else:
                print("❌ Metadata collection does not exist")
        except Exception as e:
            print(f"Error checking metadata collection: {e}")
        
        # Check if our collection exists with correct name
        collection_name = vector_store._generate_collection_name()
        print(f"Collection name: {collection_name}")
        
        try:
            response = requests.get(f"http://localhost:6333/collections/{collection_name}")
            if response.status_code == 200:
                print("✓ Test collection exists")
            else:
                print("❌ Test collection does not exist")
        except Exception as e:
            print(f"Error checking test collection: {e}")
        
        # Test collections list command
        print("\nTesting collections list...")
        result = os.system(f"cd {os.getcwd()} && source .venv/bin/activate && python -m code_index.cli collections list > /tmp/test_collections.txt 2>&1")
        
        with open("/tmp/test_collections.txt", "r") as f:
            output = f.read()
            print("Collections list output:")
            print(output)
        
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            vector_store.delete_collection()
        except:
            pass
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_metadata_storage()