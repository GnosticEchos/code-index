"""
Utility mocks for services.
"""
from unittest.mock import MagicMock, patch

class ServiceMocks:
    """Collection of service mocks for testing."""
    
    @staticmethod
    def mock_api_call():
        """Mock an API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        return mock_response

    @staticmethod
    def mock_database_connection():
        """Mock a database connection."""
        mock_db = MagicMock()
        mock_db.cursor.return_value = MagicMock()
        return mock_db

    @staticmethod
    def mock_auth_service():
        """Mock authentication service."""
        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = True
        return mock_auth

# Keep original functions for backward compatibility
def mock_api_call():
    """Mock an API call."""
    return ServiceMocks.mock_api_call()

def mock_database_connection():
    """Mock a database connection."""
    return ServiceMocks.mock_database_connection()

def mock_auth_service():
    """Mock authentication service."""
    return ServiceMocks.mock_auth_service()