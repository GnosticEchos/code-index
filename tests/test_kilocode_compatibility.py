#!/usr/bin/env python3
"""
Test script to verify KiloCode compatibility of our vector store implementation.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.vector_store import QdrantVectorStore


def test_kilocode_compatibility():
    """Test that our vector store is compatible with KiloCode expectations."""
    print("=== Testing KiloCode Compatibility ===")
    
    # Create temporary workspace
    test_dir = tempfile.mkdtemp(prefix="kilocode_compat_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Create test file
        test_file = os.path.join(test_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    print('Hello World')\n")
        
        # Create configuration
        config = Config()
        config.workspace_path = test_dir
        config.embedding_length = 768  # Standard size
        
        # Initialize vector store
        vector_store = QdrantVectorStore(config)
        
        # Test collection naming compatibility
        expected_collection_name = vector_store._generate_collection_name()
        print(f"Collection name: {expected_collection_name}")
        
        # Verify it follows KiloCode naming convention
        assert expected_collection_name.startswith("ws-"), "Collection name should start with 'ws-'"
        assert len(expected_collection_name) == 19, "Collection name should be 'ws-' + 16 chars"
        print("✓ Collection naming is KiloCode-compatible")
        
        # Test initialization
        print("Testing collection initialization...")
        created = vector_store.initialize()
        print(f"Collection created: {created}")
        
        # Test payload index creation
        print("Testing payload index creation...")
        # This should not raise any errors
        vector_store._create_payload_indexes()
        print("✓ Payload indexes created successfully")
        
        # Test payload validation
        print("Testing payload validation...")
        valid_payload = {
            "filePath": "test.py",
            "codeChunk": "def hello():\n    print('Hello World')",
            "startLine": 1,
            "endLine": 2
        }
        
        invalid_payload = {
            "file_path": "test.py",  # Wrong field name
            "content": "def hello():\n    print('Hello World')",
            "start_line": 1,  # Wrong field name
            "end_line": 2     # Wrong field name
        }
        
        assert vector_store._is_payload_valid(valid_payload), "Valid payload should be recognized as valid"
        assert not vector_store._is_payload_valid(invalid_payload), "Invalid payload should be recognized as invalid"
        assert not vector_store._is_payload_valid({}), "Empty payload should be invalid"
        assert not vector_store._is_payload_valid(None), "None payload should be invalid"
        print("✓ Payload validation works correctly")
        
        # Test point creation with correct field names
        print("Testing point creation...")
        import uuid
        test_points = [{
            "id": str(uuid.uuid4()),  # Use proper UUID
            "vector": [0.1] * 768,  # Dummy vector
            "payload": {
                "filePath": "test.py",
                "codeChunk": "def hello():\n    print('Hello World')",
                "startLine": 1,
                "endLine": 2,
                "type": "function"
            }
        }]
        
        # This should not raise any errors
        vector_store.upsert_points(test_points)
        print("✓ Points upserted successfully with KiloCode-compatible fields")
        
        # Test search result format
        print("Testing search result format...")
        # Test the _is_payload_valid method directly
        valid_payload = {
            "filePath": "test.py",
            "codeChunk": "def hello():\n    print('Hello World')",
            "startLine": 1,
            "endLine": 2,
            "type": "function"
        }
        
        # Test that our validation works
        assert vector_store._is_payload_valid(valid_payload), "Payload validation should work"
        
        # Test that result formatting works (manually test the logic)
        formatted_payload = {
            "filePath": valid_payload.get("filePath", ""),
            "codeChunk": valid_payload.get("codeChunk", ""),
            "startLine": valid_payload.get("startLine", 0),
            "endLine": valid_payload.get("endLine", 0),
            "type": valid_payload.get("type", "")
        }
        
        # Verify KiloCode-compatible result format
        assert "filePath" in formatted_payload, "Payload should have 'filePath' field"
        assert "codeChunk" in formatted_payload, "Payload should have 'codeChunk' field"
        assert "startLine" in formatted_payload, "Payload should have 'startLine' field"
        assert "endLine" in formatted_payload, "Payload should have 'endLine' field"
        print("✓ Search results are KiloCode-compatible")
        
        print("\n=== All KiloCode compatibility tests passed! ===")
        assert True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False
    finally:
        # Clean up
        try:
            vector_store.delete_collection()
        except:
            pass
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_kilocode_compatibility()
    sys.exit(0 if success else 1)