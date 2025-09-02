import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.vector_store import QdrantVectorStore

def examine_indexed_points():
    """Examine what was actually indexed in the Qdrant collection."""
    print("=== Examining Indexed Points in Qdrant Collection ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    config.workspace_path = "/home/james/kanban_frontend/kanban_api"
    
    # Initialize vector store
    vector_store = QdrantVectorStore(config)
    
    print(f"Collection name: {vector_store.collection_name}")
    print(f"Collection exists: {vector_store.collection_exists()}")
    
    if not vector_store.collection_exists():
        print("Collection does not exist!")
        return
    
    # Try to get some points from the collection
    try:
        # Search for points with a simple query vector (all zeros)
        query_vector = [0.0] * config.embedding_length
        results = vector_store.search(query_vector, min_score=0.0, max_results=5)
        
        print(f"\nFound {len(results)} points in collection:")
        
        for i, result in enumerate(results):
            payload = result.get("payload", {})
            file_path = payload.get("filePath", "Unknown")
            start_line = payload.get("startLine", 0)
            end_line = payload.get("endLine", 0)
            content = payload.get("codeChunk", "").strip()
            block_type = payload.get("type", "Unknown")
            score = result.get("score", 0)
            
            print(f"\nPoint {i+1}:")
            print(f"  File: {file_path}")
            print(f"  Lines: {start_line}-{end_line}")
            print(f"  Type: {block_type}")
            print(f"  Score: {score}")
            print(f"  Content preview: {content[:200]}{'...' if len(content) > 200 else ''}")
            
    except Exception as e:
        print(f"Error examining points: {e}")

if __name__ == "__main__":
    examine_indexed_points()