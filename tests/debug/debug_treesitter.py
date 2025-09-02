import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.parser import CodeParser

def debug_rust_parsing():
    """Debug Tree-sitter parsing for Rust files."""
    print("=== Debugging Tree-sitter Parsing for Rust Files ===")
    
    # Load the batch configuration which uses Tree-sitter
    config = Config.from_file("batch_config.json")
    print(f"Configuration loaded: chunking_strategy={config.chunking_strategy}, use_tree_sitter={getattr(config, 'use_tree_sitter', False)}")
    
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
        # Show more content - first 200 characters
        content_preview = block.content[:300].replace('\n', '\\n')
        print(f"  Content preview: {content_preview}{'...' if len(block.content) > 300 else ''}")

if __name__ == "__main__":
    debug_rust_parsing()