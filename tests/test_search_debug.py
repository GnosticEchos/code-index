import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore

def test_search_debug():
    """Debug the search functionality."""
    print("=== Debugging Search Functionality ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    
    # Initialize components
    embedder = OllamaEmbedder(config)
    vector_store = QdrantVectorStore(config)
    
    print(f"Collection name: {vector_store.collection_name}")
    
    # Generate a query vector
    query_text = "vector store"
    print(f"\nQuery: '{query_text}'")
    
    try:
        embedding_response = embedder.create_embeddings([query_text])
        query_vector = embedding_response["embeddings"][0]
        
        # Test with different score thresholds
        thresholds = [0.4, 0.3, 0.2, 0.1, 0.05, 0.01, 0.0]
        
        for threshold in thresholds:
            print(f"\n--- Testing with threshold: {threshold} ---")
            
            try:
                # Use direct Qdrant query_points to bypass the validation
                from qdrant_client.models import Filter
                results = vector_store.client.query_points(
                    collection_name=vector_store.collection_name,
                    query=query_vector,
                    limit=5,
                    score_threshold=threshold,
                    with_payload=True
                )
                
                print(f"Raw Qdrant results: {len(results.points)}")
                
                for i, result in enumerate(results.points):
                    payload = result.payload
                    file_path = payload.get("filePath", "Unknown")
                    score = result.score
                    print(f"  {i+1}. {file_path} (score: {score:.3f})")
                    
                    # Check payload validity
                    is_valid = vector_store._is_payload_valid(payload)
                    print(f"     Payload valid: {is_valid}")
                    if not is_valid:
                        print(f"     Missing fields: {[field for field in ['filePath', 'codeChunk', 'startLine', 'endLine'] if field not in payload]}")
                
            except Exception as e:
                print(f"Error with threshold {threshold}: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_debug()