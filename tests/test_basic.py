"""
Test module for the code index tool.
"""
import os
import tempfile
import pytest
from code_index.config import Config
from code_index.utils import get_file_hash, is_binary_file, is_supported_file
from code_index.cache import CacheManager


def test_config():
    """Test configuration management."""
    config = Config()
    assert config.ollama_base_url == "http://localhost:11434"
    assert config.ollama_model == "nomic-embed-text:latest"
    assert config.qdrant_url == "http://localhost:6333"
    assert isinstance(config.extensions, list)
    assert ".py" in config.extensions


def test_file_hash():
    """Test file hash calculation."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        # Calculate hash
        file_hash = get_file_hash(temp_file)
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64  # SHA256 hash length
    finally:
        # Clean up
        os.unlink(temp_file)


def test_binary_file_detection():
    """Test binary file detection."""
    # Create a text file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("This is a text file with some content.")
        text_file = f.name
    
    # Create a "binary" file (with null bytes)
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
        f.write(b"\x00\x01\x02\x03\x04\x05")
        binary_file = f.name
    
    try:
        # Text file should not be detected as binary
        assert not is_binary_file(text_file)
        
        # Binary file should be detected as binary
        assert is_binary_file(binary_file)
    finally:
        # Clean up
        os.unlink(text_file)
        os.unlink(binary_file)


def test_supported_files():
    """Test supported file detection."""
    # Test supported files
    assert is_supported_file("test.py")
    assert is_supported_file("test.js")
    assert is_supported_file("test.rs")
    assert is_supported_file("test.vue")
    assert is_supported_file("test.surql")
    
    # Test unsupported files
    assert not is_supported_file("test.exe")
    assert not is_supported_file("test.dll")
    assert not is_supported_file("test.bin")


def test_cache_manager():
    """Test cache manager functionality."""
    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize cache manager
        cache_manager = CacheManager(temp_dir)
        
        # Test cache operations
        test_file = os.path.join(temp_dir, "test.py")
        test_hash = "abcdef1234567890"
        
        # Test get_hash on non-existent file
        assert cache_manager.get_hash(test_file) is None
        
        # Test update_hash
        cache_manager.update_hash(test_file, test_hash)
        assert cache_manager.get_hash(test_file) == test_hash
        
        # Test delete_hash
        cache_manager.delete_hash(test_file)
        assert cache_manager.get_hash(test_file) is None
        
        # Test get_all_hashes
        cache_manager.update_hash(test_file, test_hash)
        all_hashes = cache_manager.get_all_hashes()
        assert isinstance(all_hashes, dict)
        assert test_file in all_hashes
        assert all_hashes[test_file] == test_hash