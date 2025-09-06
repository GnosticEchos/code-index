"""
Test runner for MCP Server tests.

Provides utilities for running MCP server tests with proper setup and teardown,
including mock service management and test environment configuration.
"""

import pytest
import sys
import os
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class MCPTestEnvironment:
    """Test environment manager for MCP server tests."""
    
    def __init__(self):
        self.temp_dirs: List[str] = []
        self.mock_patches: List[Any] = []
        
    def create_test_workspace(self, files: Optional[Dict[str, str]] = None) -> str:
        """
        Create a temporary workspace with test files.
        
        Args:
            files: Dictionary of filename -> content mappings
            
        Returns:
            Path to temporary workspace
        """
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        if files is None:
            files = {
                "main.py": "def main():\n    print('Hello, World!')\n",
                "utils.py": "def helper():\n    return True\n",
                "README.md": "# Test Project\n"
            }
        
        for filename, content in files.items():
            file_path = Path(temp_dir) / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        
        return temp_dir
    
    def create_test_config(self, workspace_path: str, **overrides) -> str:
        """
        Create a test configuration file.
        
        Args:
            workspace_path: Path to workspace
            **overrides: Configuration overrides
            
        Returns:
            Path to configuration file
        """
        config_data = {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "nomic-embed-text:latest",
            "qdrant_url": "http://localhost:6333",
            "embedding_length": 768,
            "workspace_path": workspace_path,
            "chunking_strategy": "lines",
            "use_tree_sitter": False,
            "search_min_score": 0.4,
            "search_max_results": 50,
            "batch_segment_threshold": 60
        }
        
        config_data.update(overrides)
        
        config_file = Path(workspace_path) / "code_index.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        
        return str(config_file)
    
    def setup_mock_services(self) -> Dict[str, Mock]:
        """
        Set up mock services for testing.
        
        Returns:
            Dictionary of mock services
        """
        # Mock Ollama embedder
        embedder_patch = patch('src.code_index.embedder.OllamaEmbedder')
        mock_embedder_class = embedder_patch.start()
        self.mock_patches.append(embedder_patch)
        
        mock_embedder = Mock()
        mock_embedder.validate_configuration.return_value = {"valid": True}
        mock_embedder.create_embeddings.return_value = {
            "embeddings": [[0.1] * 768]
        }
        mock_embedder_class.return_value = mock_embedder
        
        # Mock Qdrant vector store
        vector_store_patch = patch('src.code_index.vector_store.QdrantVectorStore')
        mock_vector_store_class = vector_store_patch.start()
        self.mock_patches.append(vector_store_patch)
        
        mock_vector_store = Mock()
        mock_collection = Mock()
        mock_collection.name = "ws-test123456789"
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_vector_store.client.get_collections.return_value = mock_collections
        mock_vector_store.collection_name = "ws-test123456789"
        mock_vector_store.initialize = Mock()
        mock_vector_store.search.return_value = []
        mock_vector_store_class.return_value = mock_vector_store
        
        # Mock collection manager
        collection_manager_patch = patch('src.code_index.collections.CollectionManager')
        mock_collection_manager_class = collection_manager_patch.start()
        self.mock_patches.append(collection_manager_patch)
        
        mock_collection_manager = Mock()
        mock_collection_manager.list_collections.return_value = []
        mock_collection_manager_class.return_value = mock_collection_manager
        
        return {
            "embedder": mock_embedder,
            "vector_store": mock_vector_store,
            "collection_manager": mock_collection_manager,
            "embedder_class": mock_embedder_class,
            "vector_store_class": mock_vector_store_class,
            "collection_manager_class": mock_collection_manager_class
        }
    
    def cleanup(self):
        """Clean up test environment."""
        # Stop all patches
        for patch_obj in self.mock_patches:
            patch_obj.stop()
        self.mock_patches.clear()
        
        # Clean up temporary directories
        import shutil
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        self.temp_dirs.clear()


def run_mcp_tests(test_pattern: str = "test_mcp_*.py", verbose: bool = True) -> int:
    """
    Run MCP server tests with proper environment setup.
    
    Args:
        test_pattern: Pattern for test files to run
        verbose: Whether to run in verbose mode
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Configure pytest arguments
    pytest_args = [
        "-v" if verbose else "-q",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings",
        f"tests/{test_pattern}"
    ]
    
    # Add coverage if available
    try:
        import pytest_cov
        pytest_args.extend([
            "--cov=src.code_index.mcp_server",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    except ImportError:
        pass
    
    # Run tests
    return pytest.main(pytest_args)


def run_unit_tests() -> int:
    """Run unit tests only."""
    return run_mcp_tests("test_mcp_[!i]*.py")  # Exclude integration tests


def run_integration_tests() -> int:
    """Run integration tests only."""
    return run_mcp_tests("test_mcp_integration.py")


def run_all_tests() -> int:
    """Run all MCP tests."""
    return run_mcp_tests("test_mcp_*.py")


def run_specific_test(test_name: str) -> int:
    """
    Run a specific test.
    
    Args:
        test_name: Name of the test file or test function
        
    Returns:
        Exit code
    """
    pytest_args = [
        "-v",
        "--tb=short",
        f"tests/{test_name}" if not test_name.startswith("tests/") else test_name
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MCP Server tests")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "specific"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--test-name",
        help="Specific test name (for test_type='specific')"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run in quiet mode"
    )
    
    args = parser.parse_args()
    
    if args.test_type == "unit":
        exit_code = run_unit_tests()
    elif args.test_type == "integration":
        exit_code = run_integration_tests()
    elif args.test_type == "all":
        exit_code = run_all_tests()
    elif args.test_type == "specific":
        if not args.test_name:
            print("Error: --test-name is required for specific tests")
            sys.exit(1)
        exit_code = run_specific_test(args.test_name)
    else:
        print(f"Unknown test type: {args.test_type}")
        sys.exit(1)
    
    sys.exit(exit_code)