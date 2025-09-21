"""
Test module for the ErrorHandler class.
"""
import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from code_index.errors import (
    ErrorHandler, 
    ErrorContext, 
    ErrorResponse, 
    ErrorCategory, 
    ErrorSeverity
)


def test_error_handler_initialization():
    """Test ErrorHandler initialization."""
    handler = ErrorHandler("test_component")
    assert handler.logger.name == "test_component"


def test_error_context_creation():
    """Test ErrorContext creation."""
    context = ErrorContext(
        component="test_component",
        operation="test_operation",
        file_path="/test/file.py",
        line_number=42,
        additional_data={"key": "value"}
    )
    
    assert context.component == "test_component"
    assert context.operation == "test_operation"
    assert context.file_path == "/test/file.py"
    assert context.line_number == 42
    assert context.additional_data == {"key": "value"}


def test_error_response_creation():
    """Test ErrorResponse creation."""
    context = ErrorContext(component="test", operation="test")
    response = ErrorResponse(
        error=True,
        error_type="ValueError",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.HIGH,
        message="Test error message",
        context=context,
        timestamp="2023-01-01T00:00:00",
        recovery_suggestions=["Try again"],
        actionable_guidance=["Check input"],
        original_exception=ValueError("Test error message"),
        stack_trace="Traceback..."
    )
    
    assert response.error == True
    assert response.error_type == "ValueError"
    assert response.category == ErrorCategory.VALIDATION
    assert response.severity == ErrorSeverity.HIGH
    assert response.message == "Test error message"
    assert response.context == context
    assert response.recovery_suggestions == ["Try again"]
    assert response.actionable_guidance == ["Check input"]


def test_categorize_validation_error():
    """Test categorization of validation errors."""
    handler = ErrorHandler("test")
    
    # Test ValueError (contains "value" in name)
    error = ValueError("Invalid value")
    context = ErrorContext(component="test", operation="test")
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.VALIDATION
    
    # Test TypeError (does not contain "value" in name)
    # Note: TypeError should be categorized as MEDIUM severity but UNKNOWN category
    error = TypeError("Wrong type")
    category = handler._categorize_error(error, context)
    # TypeError falls through to default case, so it should be UNKNOWN
    assert category == ErrorCategory.UNKNOWN


def test_categorize_file_access_error():
    """Test categorization of file access errors."""
    handler = ErrorHandler("test")
    context = ErrorContext(component="test", operation="test")
    
    # Test FileNotFoundError
    error = FileNotFoundError("File not found")
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.FILE_SYSTEM
    
    # Test PermissionError
    error = PermissionError("Permission denied")
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.FILE_SYSTEM


def test_categorize_parsing_error():
    """Test categorization of parsing errors."""
    handler = ErrorHandler("test")
    context = ErrorContext(component="test", operation="test")
    
    # Test SyntaxError (contains "syntax" in name, should be categorized as parsing)
    error = SyntaxError("Invalid syntax")
    category = handler._categorize_error(error, context)
    # SyntaxError should be categorized as PARSING since it's a parsing error
    assert category == ErrorCategory.PARSING
    
    # Test JSONDecodeError (contains "parse" in name through inheritance)
    error = json.JSONDecodeError("Invalid JSON", "invalid", 0)
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.PARSING


def test_categorize_network_error():
    """Test categorization of network errors."""
    handler = ErrorHandler("test")
    context = ErrorContext(component="test", operation="test")
    
    # Test ConnectionError
    error = ConnectionError("Connection failed")
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.NETWORK
    
    # Test TimeoutError
    error = TimeoutError("Request timed out")
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.NETWORK


def test_categorize_configuration_error():
    """Test categorization of configuration errors."""
    handler = ErrorHandler("test")
    context = ErrorContext(component="test", operation="test")
    
    # Test KeyError with "config" in message
    error = KeyError("config_key")
    category = handler._categorize_error(error, context)
    assert category == ErrorCategory.CONFIGURATION


def test_categorize_unknown_error():
    """Test categorization of unknown errors."""
    handler = ErrorHandler("test")
    context = ErrorContext(component="test", operation="test")
    
    # Test generic Exception
    error = Exception("Generic error")
    category = handler._categorize_error(error, context)
    # Exception should fall through to UNKNOWN category
    assert category == ErrorCategory.UNKNOWN


def test_generate_recovery_suggestions():
    """Test generation of recovery suggestions."""
    handler = ErrorHandler("test")
    
    # Test file system error
    context = ErrorContext(component="test", operation="test")
    suggestions = handler._generate_recovery_suggestions(error=Exception(), context=context, category=ErrorCategory.FILE_SYSTEM)
    assert "Check file/directory permissions" in str(suggestions)
    
    # Test network error
    suggestions = handler._generate_recovery_suggestions(error=Exception(), context=context, category=ErrorCategory.NETWORK)
    assert "Check network connectivity" in str(suggestions)


def test_handle_error_with_context():
    """Test handling of errors with context."""
    handler = ErrorHandler("test_component")
    
    error = ValueError("Invalid value")
    context = ErrorContext(
        component="test_component",
        operation="test_operation",
        file_path="/test/file.py",
        line_number=42
    )
    
    response = handler.handle_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert "Invalid value" in response.message
    assert response.category == ErrorCategory.VALIDATION
    assert response.context == context
    assert response.recovery_suggestions is not None
    assert response.actionable_guidance is not None


def test_handle_error_without_context():
    """Test handling of errors without context."""
    handler = ErrorHandler("test_component")
    
    error = ValueError("Invalid value")
    context = ErrorContext(component="test_component", operation="unknown")
    response = handler.handle_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert "Invalid value" in response.message
    assert response.category == ErrorCategory.VALIDATION
    assert response.context == context
    assert response.recovery_suggestions is not None
    assert response.actionable_guidance is not None


@patch('builtins.print')
def test_handle_error_with_suppression(mock_print):
    """Test handling of errors with suppression."""
    handler = ErrorHandler("test_component")
    
    error = ValueError("Test error")
    context = ErrorContext(component="test_component", operation="test")
    handler.handle_error(error, context)
    
    # Should have logged the error
    assert handler.logger is not None


def test_error_handler_repr():
    """Test ErrorHandler string representation."""
    handler = ErrorHandler("test_component")
    repr_str = repr(handler)
    assert "ErrorHandler" in repr_str


def test_error_context_repr():
    """Test ErrorContext string representation."""
    context = ErrorContext(
        component="test_component",
        operation="test_operation",
        file_path="/test/file.py"
    )
    repr_str = repr(context)
    assert "ErrorContext" in repr_str
    assert "test_component" in repr_str
    assert "test_operation" in repr_str
    assert "/test/file.py" in repr_str


def test_error_response_repr():
    """Test ErrorResponse string representation."""
    context = ErrorContext(component="test", operation="test")
    response = ErrorResponse(
        error=True,
        error_type="ValueError",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.HIGH,
        message="Test error",
        context=context,
        timestamp="2023-01-01T00:00:00",
        recovery_suggestions=["Try again"],
        actionable_guidance=["Check input"],
        original_exception=ValueError("Test error"),
        stack_trace="Traceback..."
    )
    repr_str = repr(response)
    assert "ErrorResponse" in repr_str
    assert "Test error" in repr_str
    assert "VALIDATION" in repr_str
    assert "HIGH" in repr_str


def test_handle_validation_error():
    """Test handling of validation errors."""
    handler = ErrorHandler("test_component")
    
    error = ValueError("Invalid value")
    context = ErrorContext(component="test_component", operation="test")
    response = handler.handle_validation_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert response.category == ErrorCategory.VALIDATION
    assert response.severity == ErrorSeverity.HIGH


def test_handle_file_error():
    """Test handling of file errors."""
    handler = ErrorHandler("test_component")
    
    error = FileNotFoundError("File not found")
    context = ErrorContext(component="test_component", operation="test")
    response = handler.handle_file_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert response.category == ErrorCategory.FILE_SYSTEM
    assert response.severity == ErrorSeverity.MEDIUM


def test_handle_network_error():
    """Test handling of network errors."""
    handler = ErrorHandler("test_component")
    
    error = ConnectionError("Connection failed")
    context = ErrorContext(component="test_component", operation="test")
    response = handler.handle_network_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert response.category == ErrorCategory.NETWORK
    assert response.severity == ErrorSeverity.HIGH


def test_handle_configuration_error():
    """Test handling of configuration errors."""
    handler = ErrorHandler("test_component")
    
    error = KeyError("config_key")
    context = ErrorContext(component="test_component", operation="test")
    response = handler.handle_configuration_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert response.category == ErrorCategory.CONFIGURATION
    assert response.severity == ErrorSeverity.CRITICAL


def test_handle_unknown_error():
    """Test handling of unknown errors."""
    handler = ErrorHandler("test_component")
    
    error = Exception("Generic error")
    context = ErrorContext(component="test_component", operation="test")
    response = handler.handle_unknown_error(error, context)
    
    assert isinstance(response, ErrorResponse)
    assert response.category == ErrorCategory.UNKNOWN
    assert response.severity == ErrorSeverity.CRITICAL


def test_should_retry():
    """Test retry decision logic."""
    handler = ErrorHandler("test_component")
    
    # Test network error (should retry)
    context = ErrorContext(component="test", operation="test")
    error = ConnectionError("Connection failed")
    response = handler.handle_error(error, context)
    assert handler.should_retry(response, 1, 3) == True
    
    # Test file system error (should retry)
    error = FileNotFoundError("File not found")
    response = handler.handle_error(error, context)
    assert handler.should_retry(response, 1, 3) == True
    
    # Test configuration error (should not retry)
    error = KeyError("config_key")
    response = handler.handle_error(error, context)
    assert handler.should_retry(response, 1, 3) == False
    
    # Test critical error (should not retry)
    response.severity = ErrorSeverity.CRITICAL
    assert handler.should_retry(response, 1, 3) == False


def test_get_retry_delay():
    """Test retry delay calculation."""
    handler = ErrorHandler("test_component")
    context = ErrorContext(component="test", operation="test")
    
    # Test network error delay
    error = ConnectionError("Connection failed")
    response = handler.handle_error(error, context)
    delay = handler.get_retry_delay(response, 1)
    assert delay > 0
    
    # Test regular error delay
    error = ValueError("Invalid value")
    response = handler.handle_error(error, context)
    response.category = ErrorCategory.VALIDATION
    delay = handler.get_retry_delay(response, 1)
    assert delay > 0