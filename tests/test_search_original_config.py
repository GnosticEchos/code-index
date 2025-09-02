#!/usr/bin/env python3
"""
Test search with the original configuration.
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore

def test_search():
    """Test search functionality with original configuration."""
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), 'code_index.json')
    if os.path.exists(config_path):
        config = Config.from_file(config_path)
    else:
        config = Config()
        config.workspace_path = "/home/james/kanban_frontend/RESEARCH/kilocode-main"
    
    print(f"Workspace path: {config.workspace_path}")
    print(f"Ollama model: {config.ollama_model}")
    print(f"Embedding length: {config.embedding_length}")
    
    # Initialize components
    embedder = OllamaEmbedder(config)
    vector_store = QdrantVectorStore(config)
    
    # Validate configuration
    print("Validating Ollama configuration...")
    validation_result = embedder.validate_configuration()
    if not validation_result["valid"]:
        print(f"Error: {validation_result['error']}")
        return
    
    print("✓ Ollama configuration is valid")
    
    # Check if collection exists
    print("Checking if collection exists...")
    if not vector_store.collection_exists():
        print("Error: No index found. Please run 'code-index index' first.")
        return
    
    print("✓ Collection exists")
    
    # Generate embedding for query
    query = "code indexing"
    print(f"Generating embedding for query: '{query}'")
    try:
        embedding_response = embedder.create_embeddings([query])
        query_vector = embedding_response["embeddings"][0]
        print(f"✓ Embedding generated successfully, dimensions: {len(query_vector)}")
    except Exception as e:
        print(f"Error generating embedding for query: {e}")
        return
    
    # Search vector store
    print("Searching vector store...")
    try:
        results = vector_store.search(
            query_vector=query_vector,
            min_score=0.1,  # Lower threshold to see if we get any results
            max_results=10
        )
        print(f"✓ Search completed, found {len(results)} results")
    except Exception as e:
        print(f"Error searching vector store: {e}")
        return
    
    # Display results
    if not results:
        print("No results found.")
        return
    
    print(f"Top 5 results:")
    print("-" * 80)
    
    for i, result in enumerate(results[:5], 1):
        payload = result.get("payload", {})
        file_path = payload.get("file_path", "Unknown")
        start_line = payload.get("start_line", 0)
        end_line = payload.get("end_line", 0)
        content = payload.get("content", "").strip()
        score = result.get("score", 0)
        
        print(f"{i}. {file_path}:{start_line}-{end_line} (score: {score:.3f})")
        # Show just the first line of content for brevity
        first_line = content.split('\n')[0] if content else ""
        print(f"   {first_line[:100]}{'...' if len(first_line) > 100 else ''}")
        print()

if __name__ == "__main__":
    test_search()