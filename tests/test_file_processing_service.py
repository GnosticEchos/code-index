"""
Test module for the FileProcessingService class.
"""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from code_index.file_processing import FileProcessingService
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


def test_file_processing_service_initialization():
    """Test FileProcessingService initialization."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    assert service.error_handler == error_handler


def test_get_file_hash():
    """Test file hash calculation."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        # Calculate hash
        file_hash = service.get_file_hash(temp_file)
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64  # SHA256 hash length
    finally:
        # Clean up
        os.unlink(temp_file)


def test_get_file_hash_nonexistent_file():
    """Test file hash calculation with nonexistent file."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Try to calculate hash of nonexistent file
    with pytest.raises(FileNotFoundError):
        service.get_file_hash("/nonexistent/file.txt")


def test_load_file_with_encoding_utf8():
    """Test loading file with UTF-8 encoding."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a UTF-8 encoded file
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        f.write("test content with unicode: café")
        temp_file = f.name
    
    try:
        content = service.load_file_with_encoding(temp_file, "utf-8")
        assert content == "test content with unicode: café"
    finally:
        os.unlink(temp_file)


def test_load_file_with_encoding_fallback():
    """Test loading file with encoding fallback."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a file with content that might need encoding detection
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write("test content with unicode: café".encode("utf-8"))
        temp_file = f.name
    
    try:
        content = service.load_file_with_encoding(temp_file)
        assert "test content" in content
    finally:
        os.unlink(temp_file)


def test_load_file_with_encoding_detection_failure():
    """Test loading file when encoding detection fails."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a file that will cause encoding detection to fail
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        # Write binary data that isn't valid text
        f.write(b"\x00\x01\x02\x03\x04\x05")
        temp_file = f.name
    
    try:
        # Should fall back to latin-1
        content = service.load_file_with_encoding(temp_file)
        assert isinstance(content, str)
    finally:
        os.unlink(temp_file)


def test_load_file_with_encoding_file_not_found():
    """Test loading file with encoding when file doesn't exist."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    with pytest.raises(FileNotFoundError):
        service.load_file_with_encoding("/nonexistent/file.txt")


def test_is_binary_file_text():
    """Test binary file detection with text file."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a text file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("This is a text file with some content.")
        text_file = f.name
    
    try:
        # Text file should not be detected as binary
        assert not service.is_binary_file(text_file)
    finally:
        os.unlink(text_file)


def test_is_binary_file_binary():
    """Test binary file detection with binary file."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a "binary" file (with null bytes)
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
        f.write(b"\x00\x01\x02\x03\x04\x05")
        binary_file = f.name
    
    try:
        # Binary file should be detected as binary
        assert service.is_binary_file(binary_file)
    finally:
        os.unlink(binary_file)


def test_is_binary_file_file_not_found():
    """Test binary file detection with nonexistent file."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Nonexistent file should be considered binary (safe default)
    assert service.is_binary_file("/nonexistent/file.bin")


def test_process_files_batch_success():
    """Test batch file processing with success."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create temporary files
    files = []
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f".py") as f:
            f.write(f"test content {i}")
            temp_files.append(f.name)
            files.append({
                'file_path': f.name,
                'abs_path': f.name,
                'rel_path': os.path.basename(f.name)
            })
    
    try:
        # Mock the load_file_with_encoding method to return predictable content
        with patch.object(service, 'load_file_with_encoding', side_effect=lambda path, encoding=None: f"content of {path}") as mock_load:
            results = service.process_files_batch(files)
            
            # Check that all files were processed
            assert len(results) == 3
            for file_info in files:
                assert file_info['file_path'] in results
                assert results[file_info['file_path']]['content'] == f"content of {file_info['file_path']}"
                assert results[file_info['file_path']]['status'] == 'success'
            
            # Check that load_file_with_encoding was called for each file
            assert mock_load.call_count == 3
    finally:
        for temp_file in temp_files:
            os.unlink(temp_file)


def test_process_files_batch_with_errors():
    """Test batch file processing with some errors."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create temporary files
    files = []
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f".py") as f:
            f.write(f"test content {i}")
            temp_files.append(f.name)
            files.append({
                'file_path': f.name,
                'abs_path': f.name,
                'rel_path': os.path.basename(f.name)
            })
    
    try:
        # Mock the load_file_with_encoding method to raise an error for one file
        def mock_load_file(path, encoding=None):
            if files[1]['file_path'] == path:  # Fail for the second file
                raise IOError("Permission denied")
            return f"content of {path}"
        
        with patch.object(service, 'load_file_with_encoding', side_effect=mock_load_file):
            results = service.process_files_batch(files)
            
            # Check that all files were processed
            assert len(results) == 3
            
            # First file should be successful
            assert results[files[0]['file_path']]['status'] == 'success'
            assert results[files[0]['file_path']]['content'] == f"content of {files[0]['file_path']}"
            
            # Second file should have an error
            assert results[files[1]['file_path']]['status'] == 'error'
            assert "Permission denied" in results[files[1]['file_path']]['error']
            
            # Third file should be successful
            assert results[files[2]['file_path']]['status'] == 'success'
            assert results[files[2]['file_path']]['content'] == f"content of {files[2]['file_path']}"
    finally:
        for temp_file in temp_files:
            os.unlink(temp_file)


def test_process_files_batch_empty_list():
    """Test batch file processing with empty list."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    results = service.process_files_batch([])
    assert results == {}


def test_process_files_batch_with_progress_callback():
    """Test batch file processing with progress callback."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create temporary files
    files = []
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f".py") as f:
            f.write(f"test content {i}")
            temp_files.append(f.name)
            files.append({
                'file_path': f.name,
                'abs_path': f.name,
                'rel_path': os.path.basename(f.name)
            })
    
    try:
        # Mock the progress callback
        progress_callback = Mock()
        
        with patch.object(service, 'load_file_with_encoding', return_value="test content"):
            results = service.process_files_batch(files, progress_callback=progress_callback)
            
            # Check that progress callback was called
            assert progress_callback.call_count == 3
    finally:
        for temp_file in temp_files:
            os.unlink(temp_file)


@patch('code_index.file_processing.os.path.getsize')
def test_get_file_size(mock_getsize):
    """Test getting file size."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)

    # Mock os.path.getsize to return a specific file size
    mock_getsize.return_value = 1024

    size = service.get_file_size("/test/file.txt")
    assert size == 1024
    mock_getsize.assert_called_once_with("/test/file.txt")


@patch('code_index.file_processing.os.path.getsize')
def test_get_file_size_error(mock_getsize):
    """Test getting file size when an error occurs."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)

    # Mock os.path.getsize to raise an exception
    mock_getsize.side_effect = OSError("Permission denied")

    size = service.get_file_size("/test/file.txt")
    assert size == 0


def test_validate_file_path_valid():
    """Test validating a valid file path."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Create a temporary file with some content
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        # Valid file path should return True
        assert service.validate_file_path(temp_file) == True
    finally:
        os.unlink(temp_file)


def test_validate_file_path_invalid():
    """Test validating an invalid file path."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    # Invalid file path should return False
    assert service.validate_file_path("/nonexistent/file.txt") == False


def test_validate_file_path_permission_error():
    """Test validating a file path with permission error."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    
    with patch.object(service, 'error_handler') as mock_error_handler:
        # Mock os.path.exists to raise PermissionError
        with patch('code_index.file_processing.os.path.exists', side_effect=PermissionError("Permission denied")):
            result = service.validate_file_path("/restricted/file.txt")
            assert result == False


def test_file_processing_service_repr():
    """Test FileProcessingService string representation."""
    error_handler = ErrorHandler("test")
    service = FileProcessingService(error_handler)
    repr_str = repr(service)
    assert "FileProcessingService" in repr_str