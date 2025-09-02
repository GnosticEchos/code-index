#!/usr/bin/env python3
"""
Script to get detailed information about all Qdrant collections using the CollectionManager directly.
This script dynamically discovers collections instead of using hardcoded names.
"""
import sys
import os

# Add src to path so we can import code_index modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from code_index.config import Config
from code_index.collections import CollectionManager


def main():
    """Main function to summarize all collections."""
    print("=== Code Index Collection Summary ===")
    print()
    
    try:
        # Create config and collection manager
        cfg = Config()
        collection_manager = CollectionManager(cfg)
        
        # Get list of all collections
        print("Discovering collections...")
        collections = collection_manager.list_collections()
        
        if not collections:
            print("No collections found.")
            return
        
        print(f"Found {len(collections)} collections:")
        print("-" * 60)
        
        # Display collection information
        for collection in collections:
            name = collection["name"]
            points = collection["points_count"]
            workspace = collection["workspace_path"]
            
            print(f"Collection: {name}")
            print(f"  Points: {points}")
            print(f"  Workspace: {workspace}")
            
            # Get additional detailed info using collection info
            try:
                info = collection_manager.get_collection_info(name)
                if info and "status" in info:
                    print(f"  Status: {info['status']}")
                else:
                    print("  Status: Unknown")
            except Exception as e:
                print(f"  Status: Error getting details ({e})")
            
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()