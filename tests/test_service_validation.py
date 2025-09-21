"""
Tests for the Service Validation Framework.

This module contains comprehensive tests for the ServiceValidator class
and ValidationResult dataclass, ensuring proper validation of external services.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from code_index.service_validation import ServiceValidator, ValidationResult
from code_index.config import Config
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation with all fields."""
        result = ValidationResult(
            service="test_service",
            valid=True,
            error="Test error",
            details={"key": "value"},
            timestamp=datetime.now(),
            response_time_ms=100,
            actionable_guidance=["Action 1", "Action 2"]
        )

        assert result.service == "test_service"
        assert result.valid is True
        assert result.error == "Test error"
        assert result.details == {"key": "value"}
        assert result.response_time_ms == 100
        assert len(result.actionable_guidance) == 2

    def test_validation_result_minimal_creation(self):
        """Test ValidationResult creation with minimal fields."""
        result = ValidationResult(service="test_service", valid=True)

        assert result.service == "test_service"
        assert result.valid is True
        assert result.error is None
        assert result.details is None
        assert result.timestamp is not None  # Should be auto-set
        assert result.response_time_ms is None
        assert result.actionable_guidance == []

    def test_validation_result_to_dict(self):
        """Test ValidationResult.to_dict() method."""
        result = ValidationResult(
            service="test_service",
            valid=False,
            error="Test error",
            details={"key": "value"},
            response_time_ms=100,
            actionable_guidance=["Action 1"]
        )

        result_dict = result.to_dict()

        assert result_dict["service"] == "test_service"
        assert result_dict["valid"] is False
        assert result_dict["error"] == "Test error"
        assert result_dict["details"] == {"key": "value"}
        assert result_dict["response_time_ms"] == 100
        assert result_dict["actionable_guidance"] == ["Action 1"]
        assert "timestamp" in result_dict


class TestServiceValidator:
    """Test cases for ServiceValidator class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock(spec=Config)
        config.ollama_base_url = "http://localhost:11434"
        config.ollama_model = "test-model"
        config.qdrant_url = "http://localhost:6333"
        config.qdrant_api_key = "test-key"
        # Ensure model is a string, not a Mock object
        config.ollama_model = "test-model"
        return config

    @pytest.fixture
    def mock_error_handler(self):
        """Create a mock error handler."""
        return Mock(spec=ErrorHandler)

    @pytest.fixture
    def service_validator(self, mock_error_handler):
        """Create a ServiceValidator instance."""
        return ServiceValidator(mock_error_handler)

    def test_service_validator_initialization(self, mock_error_handler):
        """Test ServiceValidator initialization."""
        validator = ServiceValidator(mock_error_handler)

        assert validator.error_handler == mock_error_handler
        assert validator._validation_cache == {}

    def test_service_validator_default_error_handler(self):
        """Test ServiceValidator with default error handler."""
        validator = ServiceValidator()

        assert isinstance(validator.error_handler, ErrorHandler)

    @patch('code_index.service_validation.requests.get')
    def test_validate_ollama_service_success(self, mock_get, mock_config):
        """Test successful Ollama service validation."""
        validator = ServiceValidator()

        # Mock successful API responses
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "models": [{"name": "test-model"}]
        }
        mock_get.return_value = mock_response

        # Mock successful embedding test
        with patch('code_index.service_validation.requests.post') as mock_post:
            mock_embedding_response = Mock()
            mock_embedding_response.raise_for_status.return_value = None
            mock_embedding_response.json.return_value = {
                "embeddings": [[0.1, 0.2, 0.3]]  # Valid embedding structure
            }
            mock_post.return_value = mock_embedding_response

            result = validator.validate_ollama_service(mock_config)

            assert result.valid is True
            assert result.service == "ollama"
            assert result.error is None
            assert result.response_time_ms is not None
            assert "base_url" in result.details
            assert "model" in result.details

    @patch('code_index.service_validation.requests.get')
    def test_validate_ollama_service_connection_error(self, mock_get, mock_config):
        """Test Ollama service validation with connection error."""
        validator = ServiceValidator()

        # Mock connection error
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("Connection refused")

        result = validator.validate_ollama_service(mock_config)

        assert result.valid is False
        assert result.service == "ollama"
        assert "Cannot connect" in result.error
        assert result.response_time_ms is not None
        assert len(result.actionable_guidance) > 0
        assert "Start Ollama service" in result.actionable_guidance[0]

    @patch('code_index.service_validation.requests.get')
    def test_validate_ollama_service_model_not_found(self, mock_get, mock_config):
        """Test Ollama service validation with model not found."""
        validator = ServiceValidator()

        # Mock successful connection but model not found
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "models": [{"name": "other-model"}]
        }
        mock_get.return_value = mock_response

        result = validator.validate_ollama_service(mock_config)

        assert result.valid is False
        assert result.service == "ollama"
        assert "not found" in result.error.lower()
        assert len(result.actionable_guidance) > 0
        assert "Available models" in result.actionable_guidance[0]

    @patch('code_index.service_validation.requests.get')
    def test_validate_ollama_service_timeout(self, mock_get, mock_config):
        """Test Ollama service validation with timeout."""
        validator = ServiceValidator()

        # Mock timeout error
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Request timed out")

        result = validator.validate_ollama_service(mock_config)

        assert result.valid is False
        assert result.service == "ollama"
        assert "timeout" in result.error.lower()
        assert len(result.actionable_guidance) > 0
        assert "Increase timeout" in result.actionable_guidance[0]

    def test_validate_qdrant_service_success(self, mock_config):
        """Test successful Qdrant service validation."""
        # Skip test if Qdrant client is not available
        try:
            from qdrant_client import QdrantClient
            qdrant_available = True
        except ImportError:
            qdrant_available = False

        if not qdrant_available:
            pytest.skip("Qdrant client not available - skipping Qdrant tests")

        validator = ServiceValidator()

        with patch('code_index.service_validation.QdrantClient') as mock_client_class:
            # Mock Qdrant client and collections
            mock_client = Mock()
            mock_collections = Mock()
            mock_collections.collections = [Mock(name="test-collection")]
            mock_client.get_collections.return_value = mock_collections
            mock_client_class.return_value = mock_client

            result = validator.validate_qdrant_service(mock_config)

            assert result.valid is True
            assert result.service == "qdrant"
            assert result.error is None
            assert result.response_time_ms is not None
            assert "url" in result.details
            assert "collection_count" in result.details

    def test_validate_qdrant_service_connection_error(self, mock_config):
        """Test Qdrant service validation with connection error."""
        # Skip test if Qdrant client is not available
        try:
            from qdrant_client import QdrantClient
            qdrant_available = True
        except ImportError:
            qdrant_available = False

        if not qdrant_available:
            pytest.skip("Qdrant client not available - skipping Qdrant tests")

        validator = ServiceValidator()

        with patch('code_index.service_validation.QdrantClient') as mock_client_class:
            # Mock connection error
            mock_client_class.side_effect = Exception("Connection failed")

            result = validator.validate_qdrant_service(mock_config)

            assert result.valid is False
            assert result.service == "qdrant"
            assert "Connection failed" in result.error
            assert len(result.actionable_guidance) > 0
            assert "Check network connectivity to Qdrant service" in result.actionable_guidance[0]

    def test_validate_all_services(self, mock_config):
        """Test validation of all services."""
        validator = ServiceValidator()

        with patch.object(validator, 'validate_ollama_service') as mock_ollama, \
             patch.object(validator, 'validate_qdrant_service') as mock_qdrant:

            # Mock validation results
            mock_ollama.return_value = ValidationResult(service="ollama", valid=True)
            mock_qdrant.return_value = ValidationResult(service="qdrant", valid=False, error="Test error")

            results = validator.validate_all_services(mock_config)

            assert len(results) == 2
            assert results[0].service == "ollama"
            assert results[1].service == "qdrant"
            assert results[1].valid is False

    def test_get_service_status(self, mock_config):
        """Test getting service status."""
        validator = ServiceValidator()

        with patch.object(validator, 'validate_all_services') as mock_validate:
            mock_results = [
                ValidationResult(service="ollama", valid=True, response_time_ms=100),
                ValidationResult(service="qdrant", valid=True, response_time_ms=200)
            ]
            mock_validate.return_value = mock_results

            status = validator.get_service_status(mock_config)

            assert status["all_healthy"] is True
            assert "ollama" in status["services"]
            assert "qdrant" in status["services"]
            assert status["total_response_time_ms"] == 300

    def test_clear_validation_cache(self, service_validator):
        """Test clearing validation cache."""
        # Add some cache entries
        service_validator._validation_cache = {
            "ollama": {"valid": True, "timestamp": datetime.now()},
            "qdrant": {"valid": False, "timestamp": datetime.now()}
        }

        service_validator.clear_validation_cache()

        assert service_validator._validation_cache == {}

    def test_get_cached_validation(self, service_validator):
        """Test getting cached validation results."""
        # Add cache entry
        cached_data = {"valid": True, "timestamp": datetime.now()}
        service_validator._validation_cache["ollama"] = cached_data

        # Test getting cached data
        result = service_validator.get_cached_validation("ollama")
        assert result == cached_data

        # Test getting non-existent cache
        result = service_validator.get_cached_validation("nonexistent")
        assert result is None

    def test_validation_caching(self, mock_config):
        """Test that validation results are cached."""
        validator = ServiceValidator()

        with patch('code_index.service_validation.requests.get') as mock_get:
            # Mock successful response
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"models": [{"name": "test-model"}]}
            mock_get.return_value = mock_response

            with patch('code_index.service_validation.requests.post') as mock_post:
                mock_embedding_response = Mock()
                mock_embedding_response.raise_for_status.return_value = None
                mock_embedding_response.json.return_value = {
                    "embeddings": [[0.1, 0.2, 0.3]]  # Valid embedding structure
                }
                mock_post.return_value = mock_embedding_response

                # First call should make actual request
                result1 = validator.validate_ollama_service(mock_config)
                assert result1.valid is True

                # Second call should use cache
                result2 = validator.validate_ollama_service(mock_config)
                assert result2.valid is True

                # Verify cache was used (only one request made)
                assert mock_get.call_count == 1


class TestServiceValidatorIntegration:
    """Integration tests for ServiceValidator with real components."""

    def test_validation_result_serialization(self):
        """Test that ValidationResult can be serialized/deserialized."""
        import json

        result = ValidationResult(
            service="test",
            valid=False,
            error="Test error",
            details={"key": "value"},
            response_time_ms=100,
            actionable_guidance=["Action 1", "Action 2"]
        )

        # Test JSON serialization
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)
        json_dict = json.loads(json_str)

        assert json_dict["service"] == "test"
        assert json_dict["valid"] is False
        assert json_dict["error"] == "Test error"
        assert json_dict["details"]["key"] == "value"

    def test_service_validator_with_real_error_handler(self):
        """Test ServiceValidator with real ErrorHandler."""
        from code_index.errors import ErrorHandler

        error_handler = ErrorHandler()
        validator = ServiceValidator(error_handler)

        # Should not raise any exceptions
        assert validator.error_handler == error_handler
        assert isinstance(validator._validation_cache, dict)

    def test_validation_result_immutability(self):
        """Test that ValidationResult fields are properly set."""
        result = ValidationResult(service="test", valid=True)

        # Test that timestamp is automatically set
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

        # Test that actionable_guidance defaults to empty list
        assert result.actionable_guidance == []

        # Test that details defaults to None
        assert result.details is None