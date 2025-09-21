"""
Test module for the code index tool.
"""
import os
import tempfile
import pytest
from code_index.config import Config
from code_index.file_processing import FileProcessingService
from code_index.errors import ErrorHandler
from code_index.cache import CacheManager


def test_config():
    """Test configuration management."""
    from code_index.config_service import ConfigurationService

    # Test using ConfigurationService with test mode to avoid actual service calls
    config_service = ConfigurationService(test_mode=True)
    config = config_service.load_with_fallback(config_path="/tmp/nonexistent_config_12345.json")

    # Test that configuration loads successfully and has expected structure
    assert config.ollama_base_url is not None
    assert config.ollama_model is not None
    assert config.qdrant_url is not None
    assert isinstance(config.extensions, list)
    assert ".py" in config.extensions

    # Test that we can access configuration values
    assert config_service.get_config_value(config, "ollama_base_url", str) is not None
    assert config_service.get_config_value(config, "ollama_model", str) is not None
    assert config_service.get_config_value(config, "qdrant_url", str) is not None


def test_file_hash():
    """Test file hash calculation."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        # Initialize file processing service with error handler
        file_processor = FileProcessingService(ErrorHandler("test"))
        # Calculate hash
        file_hash = file_processor.get_file_hash(temp_file)
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
        # Initialize file processing service with error handler
        file_processor = FileProcessingService(ErrorHandler("test"))
        # Text file should not be detected as binary
        assert not file_processor.is_binary_file(text_file)
        
        # Binary file should be detected as binary
        assert file_processor.is_binary_file(binary_file)
    finally:
        # Clean up
        os.unlink(text_file)
        os.unlink(binary_file)


def test_supported_files():
    """Test supported file detection."""
    # Initialize file processing service with error handler
    file_processor = FileProcessingService(ErrorHandler("test"))
    # Test supported files
    assert file_processor.is_supported_file("test.py")
    assert file_processor.is_supported_file("test.js")
    assert file_processor.is_supported_file("test.rs")
    assert file_processor.is_supported_file("test.vue")
    assert file_processor.is_supported_file("test.surql")
    
    # Test unsupported files
    assert not file_processor.is_supported_file("test.exe")
    assert not file_processor.is_supported_file("test.dll")
    assert not file_processor.is_supported_file("test.bin")


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