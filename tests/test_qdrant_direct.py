import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore

def test_qdrant_direct():
    """Test Qdrant search directly."""
    print("=== Testing Qdrant Direct Search ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    
    # Initialize components
    embedder = OllamaEmbedder(config)
    vector_store = QdrantVectorStore(config)
    
    print(f"Collection name: {vector_store.collection_name}")
    print(f"Collection exists: {vector_store.collection_exists()}")
    
    if not vector_store.collection_exists():
        print("Collection does not exist!")
        return
    
    # Generate a query vector
    query_text = "vector store"
    print(f"\nQuery: '{query_text}'")
    
    try:
        embedding_response = embedder.create_embeddings([query_text])
        query_vector = embedding_response["embeddings"][0]
        print(f"Query vector length: {len(query_vector)}")
        
        # Try direct Qdrant search
        print("\n--- Direct Qdrant Search ---")
        try:
            from qdrant_client.models import SearchRequest
            search_result = vector_store.client.query_points(
                collection_name=vector_store.collection_name,
                query=query_vector,
                limit=5,
                with_payload=True
            ).points
            
            print(f"Direct search found {len(search_result)} results:")
            for i, result in enumerate(search_result):
                payload = result.payload
                file_path = payload.get("filePath", "Unknown")
                score = result.score
                print(f"{i+1}. {file_path} (score: {score:.3f})")
                
        except Exception as e:
            print(f"Direct search error: {e}")
            import traceback
            traceback.print_exc()
        
        # Try using the vector store's search method
        print("\n--- Vector Store Search Method ---")
        try:
            results = vector_store.search(
                query_vector=query_vector,
                min_score=0.1,  # Very low threshold
                max_results=5
            )
            
            print(f"Vector store search found {len(results)} results:")
            for i, result in enumerate(results):
                payload = result.get("payload", {})
                file_path = payload.get("filePath", "Unknown")
                score = result.get("score", 0)
                print(f"{i+1}. {file_path} (score: {score:.3f})")
                
        except Exception as e:
            print(f"Vector store search error: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qdrant_direct()