import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore

def test_simple_search():
    """Test search with a simple query that should match the indexed content."""
    print("=== Testing Simple Search ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    print(f"Using workspace path: {config.workspace_path}")
    
    # Initialize components
    embedder = OllamaEmbedder(config)
    vector_store = QdrantVectorStore(config)
    
    print(f"Collection name: {vector_store.collection_name}")
    print(f"Collection exists: {vector_store.collection_exists()}")
    
    if not vector_store.collection_exists():
        print("Collection does not exist!")
        return
    
    # Test queries that should match the indexed content
    queries = [
        "vector store",
        "code indexing",
        "configuration class",
        "Qdrant client",
        "Ollama embeddings"
    ]
    
    for query in queries:
        print(f"\n--- Searching for: '{query}' ---")
        
        try:
            embedding_response = embedder.create_embeddings([query])
            query_vector = embedding_response["embeddings"][0]
            
            results = vector_store.search(
                query_vector=query_vector,
                min_score=0.3,
                max_results=5
            )
            
            print(f"Found {len(results)} results:")
            
            for i, result in enumerate(results):
                payload = result.get("payload", {})
                file_path = payload.get("filePath", "Unknown")
                start_line = payload.get("startLine", 0)
                end_line = payload.get("endLine", 0)
                content = payload.get("codeChunk", "").strip()
                score = result.get("score", 0)
                
                print(f"{i+1}. {file_path}:{start_line}-{end_line} (score: {score:.3f})")
                content_preview = content[:100].replace('\n', '\\n')
                print(f"   {content_preview}{'...' if len(content) > 100 else ''}")
                
        except Exception as e:
            print(f"Error searching: {e}")

if __name__ == "__main__":
    test_simple_search()