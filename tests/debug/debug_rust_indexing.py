import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.parser import CodeParser
from code_index.vector_store import QdrantVectorStore

def debug_rust_indexing():
    """Debug the Rust indexing process."""
    print("=== Debugging Rust Indexing Process ===")
    
    # Load the batch configuration which uses Tree-sitter
    config = Config.from_file("batch_config.json")
    print(f"Configuration: chunking_strategy={config.chunking_strategy}, use_tree_sitter={getattr(config, 'use_tree_sitter', False)}")
    print(f"Workspace path: {config.workspace_path}")
    
    # Create a parser
    parser = CodeParser(config)
    
    # Test with a Rust file from the auth module
    rust_file_path = "/home/james/kanban_frontend/kanban_api/src/auth/handlers/login.rs"
    
    if not os.path.exists(rust_file_path):
        print(f"Error: File not found: {rust_file_path}")
        return
    
    print(f"\nParsing file: {rust_file_path}")
    
    # Parse the file
    blocks = parser.parse_file(rust_file_path)
    
    print(f"Found {len(blocks)} code blocks:")
    
    # Show all blocks with more content
    for i, block in enumerate(blocks):
        print(f"\nBlock {i+1}:")
        print(f"  Type: {block.type}")
        print(f"  Lines: {block.start_line}-{block.end_line}")
        print(f"  Identifier: {block.identifier}")
        # Show more content - first 300 characters
        content_preview = block.content[:300].replace('\n', '\\n')
        print(f"  Content preview: {content_preview}{'...' if len(block.content) > 300 else ''}")
        
    # Now let's check what would be indexed
    print("\n=== Simulating Indexing Process ===")
    
    # Set the workspace path to the kanban_api directory
    config.workspace_path = "/home/james/kanban_frontend/kanban_api"
    print(f"Updated workspace path: {config.workspace_path}")
    
    # Initialize vector store
    vector_store = QdrantVectorStore(config)
    
    # Check if collection exists
    print(f"Collection name: {vector_store.collection_name}")
    print(f"Collection exists: {vector_store.collection_exists()}")
    
    if vector_store.collection_exists():
        # Try to get some points from the collection
        try:
            # Search for points with a simple query vector (all zeros)
            query_vector = [0.0] * config.embedding_length
            results = vector_store.search(query_vector, min_score=0.0, max_results=5)
            
            print(f"Found {len(results)} points in collection:")
            
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
    debug_rust_indexing()