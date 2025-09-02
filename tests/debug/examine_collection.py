import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.vector_store import QdrantVectorStore

def examine_collection():
    """Examine the contents of the collection directly."""
    print("=== Examining Collection Contents ===")
    
    # Load the batch configuration
    config = Config.from_file("batch_config.json")
    config.workspace_path = "/home/james/kanban_frontend/kanban_api"
    
    # Initialize vector store
    vector_store = QdrantVectorStore(config)
    
    # Check if collection exists
    print(f"Collection name: {vector_store.collection_name}")
    print(f"Collection exists: {vector_store.collection_exists()}")
    
    if not vector_store.collection_exists():
        print("Collection does not exist!")
        return
    
    # Try to get some points from the collection using scroll
    try:
        print("Scrolling through collection...")
        results = vector_store.client.scroll(
            collection_name=vector_store.collection_name,
            limit=20,
            with_payload=True,
            with_vectors=False
        )
        
        points, next_page = results
        print(f"Found {len(points)} points in collection:")
        
        # Count different file types
        file_types = {}
        auth_files = []
        
        for i, point in enumerate(points):
            payload = point.payload
            file_path = payload.get("filePath", "Unknown")
            start_line = payload.get("startLine", 0)
            end_line = payload.get("endLine", 0)
            content = payload.get("codeChunk", "").strip()
            block_type = payload.get("type", "Unknown")
            
            # Get file extension
            if '.' in file_path:
                ext = file_path.split('.')[-1]
            else:
                ext = "no_ext"
                
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Check if it's an auth file
            if "auth" in file_path.lower():
                auth_files.append((file_path, start_line, end_line, block_type))
            
            print(f"\nPoint {i+1}:")
            print(f"  File: {file_path}")
            print(f"  Lines: {start_line}-{end_line}")
            print(f"  Type: {block_type}")
            print(f"  Content preview: {content[:200]}{'...' if len(content) > 200 else ''}")
            
        print(f"\nFile type distribution:")
        for ext, count in sorted(file_types.items()):
            print(f"  {ext}: {count}")
            
        print(f"\nAuth-related files found: {len(auth_files)}")
        for file_path, start_line, end_line, block_type in auth_files[:10]:  # Show first 10
            print(f"  {file_path}:{start_line}-{end_line} ({block_type})")
            
    except Exception as e:
        print(f"Error examining collection: {e}")

if __name__ == "__main__":
    examine_collection()