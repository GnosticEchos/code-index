import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder

def test_embedding():
    """Test if the embedding service is working."""
    print("=== Testing Embedding Service ===")
    
    # Load the current configuration
    config = Config.from_file("current_config.json")
    print(f"Using Ollama model: {config.ollama_model}")
    print(f"Ollama base URL: {config.ollama_base_url}")
    
    # Initialize embedder
    embedder = OllamaEmbedder(config)
    
    # Validate configuration
    print("Validating configuration...")
    validation_result = embedder.validate_configuration()
    if not validation_result["valid"]:
        print(f"Error: {validation_result['error']}")
        return
    
    print("Configuration is valid.")
    
    # Test embedding generation
    test_texts = [
        "vector store implementation",
        "code indexing tool",
        "Qdrant database client"
    ]
    
    for text in test_texts:
        print(f"\n--- Testing embedding for: '{text}' ---")
        
        try:
            embedding_response = embedder.create_embeddings([text])
            print(f"Embedding generated successfully")
            print(f"Vector length: {len(embedding_response['embeddings'][0])}")
            print(f"Response keys: {list(embedding_response.keys())}")
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_embedding()