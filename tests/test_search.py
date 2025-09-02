import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore

def test_search():
    """Test searching with different queries."""
    print("=== Testing Search with Different Queries ===")
    
    # Load the batch configuration
    config = Config.from_file("batch_config.json")
    config.workspace_path = "/home/james/kanban_frontend/kanban_api"
    
    print(f"Configuration: chunking_strategy={config.chunking_strategy}")
    print(f"Workspace path: {config.workspace_path}")
    
    # Initialize components
    embedder = OllamaEmbedder(config)
    vector_store = QdrantVectorStore(config)
    
    # Validate configuration
    print("Validating configuration...")
    validation_result = embedder.validate_configuration()
    if not validation_result["valid"]:
        print(f"Error: {validation_result['error']}")
        return
    
    print("Configuration is valid.")
    
    # Check if collection exists
    print(f"Collection name: {vector_store.collection_name}")
    print(f"Collection exists: {vector_store.collection_exists()}")
    
    if not vector_store.collection_exists():
        print("Collection does not exist!")
        return
    
    # Test different queries
    queries = [
        "how is auth implemented",
        "Rust authentication login function",
        "SurrealDB authentication in Rust",
        "login function implementation",
        "authentication flow in Rust code"
    ]
    
    for query in queries:
        print(f"\n--- Searching for: '{query}' ---")
        
        try:
            embedding_response = embedder.create_embeddings([query])
            query_vector = embedding_response["embeddings"][0]
            
            results = vector_store.search(
                query_vector=query_vector,
                min_score=0.4,
                max_results=5
            )
            
            print(f"Found {len(results)} results:")
            
            for i, result in enumerate(results, 1):
                payload = result.get("payload", {})
                file_path = payload.get("filePath", "Unknown")
                start_line = payload.get("startLine", 0)
                end_line = payload.get("endLine", 0)
                content = payload.get("codeChunk", "").strip()
                score = result.get("score", 0)
                
                print(f"{i}. {file_path}:{start_line}-{end_line} (score: {score:.3f})")
                # Show first 100 characters of content
                content_preview = content[:100].replace('\n', '\\n')
                print(f"   {content_preview}{'...' if len(content) > 100 else ''}")
                
        except Exception as e:
            print(f"Error searching: {e}")

if __name__ == "__main__":
    test_search()