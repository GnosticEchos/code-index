"""
Utility functions and classes for generating test data.
"""
import pytest
from typing import Dict, List, Any

class TestDataGenerator:
    """Class for generating test data."""
    
    # Remove __init__ to avoid pytest collection issues
    # Use class methods instead
    
    def generate_config(self) -> Dict[str, Any]:
        """Generate a sample configuration dictionary."""
        return {
            "api_key": "test_key_123",
            "timeout": 30,
            "max_retries": 3,
            "endpoint": "https://api.example.com/v1"
        }
    
    def generate_error_responses(self) -> List[Dict[str, Any]]:
        """Generate a list of error response examples."""
        return [
            {
                "status_code": 404,
                "message": "Resource not found",
                "details": "The requested resource could not be found."
            },
            {
                "status_code": 500,
                "message": "Internal server error",
                "details": "Something went wrong on our end."
            }
        ]

# Keep the original functions for backward compatibility
def generate_config() -> Dict[str, Any]:
    """Generate a sample configuration dictionary."""
    generator = TestDataGenerator()
    return generator.generate_config()

def generate_error_responses() -> List[Dict[str, Any]]:
    """Generate a list of error response examples."""
    generator = TestDataGenerator()
    return generator.generate_error_responses()