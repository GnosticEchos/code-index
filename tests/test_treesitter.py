import pytest
import tree_sitter_language_pack as tsl
from tree_sitter import Parser
import os

def test_treesitter_basic_parsing():
    """Test basic Tree-sitter parsing functionality."""
    # Skip if the test file doesn't exist
    file_path = "/home/james/kanban_frontend/kanban_api/src/auth/handlers/login.rs"
    if not os.path.exists(file_path):
        pytest.skip("Test file not found")
    
    with open(file_path, "r") as f:
        content = f.read()

    # Get Rust language
    language = tsl.get_language('rust')
    parser = Parser()
    parser.language = language

    # Parse the content
    tree = parser.parse(bytes(content, "utf8"))
    root_node = tree.root_node

    # Basic assertions - just test that parsing works
    assert root_node.type == "source_file"
    assert len(root_node.children) > 0
    
    # Test that we can iterate through children (basic Tree-sitter functionality)
    child_count = 0
    for child in root_node.children:
        child_count += 1
        assert hasattr(child, 'type')
        assert hasattr(child, 'start_point')
        assert hasattr(child, 'end_point')
    
    assert child_count > 0