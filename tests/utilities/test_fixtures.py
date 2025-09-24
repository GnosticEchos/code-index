"""
Test fixtures utilities.
"""
import pytest

@pytest.fixture
def mock_config():
    """Fixture for a mock configuration."""
    return {
        "api_key": "test_key",
        "debug": True,
        "timeout": 30
    }

@pytest.fixture
def mock_error_handler():
    """Fixture for a mock error handler."""
    class MockErrorHandler:
        def __init__(self, name):
            self.name = name
            
        def handle_error(self, error_type, error_message, error_traceback):
            """Mock error handling method."""
            print(f"Error handled by {self.name}: {error_type}")
            return True
    
    return MockErrorHandler("test_handler")

@pytest.fixture
def mock_query_executor():
    """Fixture for a mock query executor."""
    class MockQueryExecutor:
        def __init__(self, config, error_handler):
            self.config = config
            self.error_handler = error_handler
            
        def execute_with_fallbacks(self, code, query, parser, language):
            """Mock execute_with_fallbacks method."""
            return {
                "success": True,
                "result": "mocked_result"
            }
    
    return MockQueryExecutor({}, mock_error_handler())