"""
Service Validation Framework for centralized service health checking.

This module provides a comprehensive service validation system that eliminates
duplicated validation logic across CLI and MCP server components.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

import requests

# Conditional import for Qdrant client
try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None

from .config import Config
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


@dataclass
class ValidationResult:
    """
    Structured validation result for service health checks.

    Provides detailed information about service validation status,
    including error details and actionable guidance.
    """
    service: str
    valid: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    response_time_ms: Optional[int] = None
    actionable_guidance: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize timestamp and actionable_guidance if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.actionable_guidance is None:
            self.actionable_guidance = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "service": self.service,
            "valid": self.valid,
            "error": self.error,
            "details": self.details or {},
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "actionable_guidance": self.actionable_guidance or []
        }

    def __getitem__(self, key: str) -> Any:
        """Enable dict-like access for backward compatibility."""
        if key == "service":
            return self.service
        elif key == "valid":
            return self.valid
        elif key == "error":
            return self.error
        elif key == "details":
            return self.details or {}
        elif key == "timestamp":
            return self.timestamp.isoformat()
        elif key == "response_time_ms":
            return self.response_time_ms
        elif key == "actionable_guidance":
            return self.actionable_guidance or []
        else:
            raise KeyError(f"'{key}' not found in ValidationResult")

    def get(self, key: str, default: Any = None) -> Any:
        """Enable dict-like get method for backward compatibility."""
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        """Enable 'in' operator for backward compatibility."""
        return key in ["service", "valid", "error", "details", "timestamp", "response_time_ms", "actionable_guidance"]

    def keys(self):
        """Return dict-like keys for backward compatibility."""
        return ["service", "valid", "error", "details", "timestamp", "response_time_ms", "actionable_guidance"]

    def __bool__(self) -> bool:
        """Enable boolean evaluation based on valid field."""
        return self.valid

    def raise_for_errors(self) -> None:
        """Raise appropriate exception if validation failed.

        This method maintains backward compatibility with code that expects
        exceptions to be raised on validation failures.
        """
        if not self.valid:
            if self.error:
                # Categorize error types and raise appropriate exceptions
                error_lower = self.error.lower()
                if "connection" in error_lower or "timeout" in error_lower:
                    raise ConnectionError(self.error)
                elif "model" in error_lower and "not found" in error_lower:
                    raise ValueError(self.error)
                elif "invalid" in error_lower or "structure" in error_lower:
                    raise ValueError(self.error)
                else:
                    raise RuntimeError(self.error)
            else:
                raise RuntimeError("Validation failed with no error message")


class ServiceValidator:
    """
    Centralized service validation system.

    Provides consistent validation logic for all external services
    (Ollama, Qdrant) with structured error handling and recovery guidance.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the service validator."""
        self.error_handler = error_handler or ErrorHandler()
        self._validation_cache: Dict[str, Dict[str, Any]] = {}

    def validate_ollama_service(self, config: Config) -> ValidationResult:
        """
        Validate Ollama service connectivity and configuration.

        Args:
            config: Configuration object with Ollama settings

        Returns:
            ValidationResult with detailed status information
        """
        start_time = time.time()
        service_name = "ollama"

        # Check cache first
        cached = self.get_cached_validation(service_name)
        if cached and cached.get("valid"):
            # Return cached result with updated timestamp
            return ValidationResult(
                service=service_name,
                valid=True,
                details={
                    "base_url": config.ollama_base_url,
                    "model": config.ollama_model,
                    "cached": True,
                    "original_timestamp": cached.get("timestamp"),
                    "embedding_dimension": cached.get("embedding_dimension"),
                    "available_models": cached.get("available_models", [])
                },
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        try:
            base_url = config.ollama_base_url.rstrip("/")
            model = config.ollama_model
            timeout = int(getattr(config, "embed_timeout_seconds", 60) or 60)

            # Step 1: Check basic connectivity
            tags_url = f"{base_url}/api/tags"
            response = requests.get(tags_url, timeout=30)
            response.raise_for_status()

            # Step 2: Validate model availability
            models_data = response.json()
            models = models_data.get("models", [])

            # Check for model variations
            model_name = str(model)  # Ensure model is a string
            model_exists = any(
                model.get("name") == model_name or
                model.get("name") == f"{model_name}:latest" or
                model.get("name") == model_name.replace(":latest", "")
                for model in models
            )

            if not model_exists:
                available_models = [model.get("name", "") for model in models]
                error_msg = f"Model '{model}' not found"
                guidance = [
                    f"Available models: {', '.join(available_models[:5])}",
                    "Pull the required model using: ollama pull <model_name>",
                    "Check model name spelling and version tag",
                    "Verify model is compatible with embedding tasks"
                ]

                return ValidationResult(
                    service=service_name,
                    valid=False,
                    error=error_msg,
                    details={
                        "available_models": available_models,
                        "requested_model": model,
                        "base_url": base_url
                    },
                    response_time_ms=int((time.time() - start_time) * 1000),
                    actionable_guidance=guidance
                )

            # Step 3: Test embedding generation
            embed_url = f"{base_url}/api/embed"
            test_response = requests.post(
                embed_url,
                json={"model": model, "input": ["test"]},
                timeout=30
            )
            test_response.raise_for_status()

            # Step 4: Validate embedding dimensions
            test_data = test_response.json()
            embeddings = test_data.get("embeddings", [])
            if not embeddings or not isinstance(embeddings[0], list):
                raise ValueError("Invalid embedding response structure")

            embedding_dim = len(embeddings[0])
            if embedding_dim <= 0:
                raise ValueError(f"Invalid embedding dimension: {embedding_dim}")

            # Cache successful validation
            self._validation_cache[service_name] = {
                "valid": True,
                "timestamp": datetime.now(),
                "embedding_dimension": embedding_dim,
                "available_models": [m.get("name", "") for m in models]
            }

            return ValidationResult(
                service=service_name,
                valid=True,
                details={
                    "base_url": base_url,
                    "model": model,
                    "embedding_dimension": embedding_dim,
                    "available_models_count": len(models),
                    "response_time_ms": int((time.time() - start_time) * 1000)
                },
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to Ollama service at {config.ollama_base_url}"
            guidance = [
                "Start Ollama service: ollama serve",
                "Verify service is running on the specified URL",
                "Check firewall and network connectivity",
                "Ensure Ollama is installed and accessible"
            ]

            return ValidationResult(
                service=service_name,
                valid=False,
                error=error_msg,
                details={
                    "base_url": config.ollama_base_url,
                    "error_type": "connection_error"
                },
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

        except requests.exceptions.Timeout as e:
            error_msg = f"Ollama service timeout after {int((time.time() - start_time) * 1000)}ms"
            guidance = [
                "Increase timeout settings in configuration",
                "Check Ollama service performance",
                "Verify system resources (CPU, memory)",
                "Consider using a smaller model for testing"
            ]

            return ValidationResult(
                service=service_name,
                valid=False,
                error=error_msg,
                details={
                    "base_url": config.ollama_base_url,
                    "timeout_ms": int((time.time() - start_time) * 1000)
                },
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama service error: {str(e)}"
            guidance = [
                "Check Ollama service logs for detailed errors",
                "Verify API endpoint compatibility",
                "Test with curl: curl http://localhost:11434/api/tags",
                "Restart Ollama service if necessary"
            ]

            return ValidationResult(
                service=service_name,
                valid=False,
                error=error_msg,
                details={
                    "base_url": config.ollama_base_url,
                    "error_type": "request_error"
                },
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

        except Exception as e:
            error_msg = f"Ollama validation failed: {str(e)}"
            guidance = [
                "Check configuration settings",
                "Verify Ollama installation",
                "Review service logs",
                "Test connectivity manually"
            ]

            return ValidationResult(
                service=service_name,
                valid=False,
                error=error_msg,
                details={
                    "base_url": config.ollama_base_url,
                    "error_type": "validation_error"
                },
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

    def validate_qdrant_service(self, config: Config) -> ValidationResult:
        """
        Validate Qdrant service connectivity and configuration.

        Args:
            config: Configuration object with Qdrant settings

        Returns:
            ValidationResult with detailed status information
        """
        start_time = time.time()
        service_name = "qdrant"

        # Check if Qdrant client is available
        if not QDRANT_AVAILABLE:
            error_msg = "Qdrant client not available - please install qdrant-client package"
            guidance = [
                "Install Qdrant client: pip install qdrant-client",
                "Verify Qdrant service installation",
                "Check Python environment and dependencies"
            ]

            return ValidationResult(
                service=service_name,
                valid=False,
                error=error_msg,
                details={"error_type": "missing_dependency"},
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

        try:
            # Parse Qdrant URL
            url = config.qdrant_url
            api_key = config.qdrant_api_key

            # Step 1: Test basic connectivity
            client = QdrantClient(url=url, api_key=api_key)

            # Step 2: Get collections to verify service is responsive
            collections = client.get_collections()

            # Step 3: Validate collection operations
            collection_count = len(collections.collections)
            collection_names = [col.name for col in collections.collections]

            # Step 4: Test collection creation capability
            test_collection_name = "code_index_validation_test"
            test_created = False

            try:
                # Try to create a test collection
                if test_collection_name not in collection_names:
                    client.create_collection(
                        collection_name=test_collection_name,
                        vectors_config={
                            "size": 1,
                            "distance": "Cosine"
                        }
                    )
                    test_created = True

                # Clean up test collection
                if test_created:
                    client.delete_collection(test_collection_name)

            except Exception as e:
                # Test collection operations might fail due to permissions
                # This is not necessarily a critical error
                pass

            # Cache successful validation
            self._validation_cache[service_name] = {
                "valid": True,
                "timestamp": datetime.now(),
                "collection_count": collection_count,
                "collection_names": collection_names
            }

            return ValidationResult(
                service=service_name,
                valid=True,
                details={
                    "url": url,
                    "collection_count": collection_count,
                    "collection_names": collection_names,
                    "response_time_ms": int((time.time() - start_time) * 1000)
                },
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            error_msg = f"Qdrant service error: {str(e)}"
            guidance = [
                "Verify Qdrant service is running",
                "Check Qdrant URL and API key configuration",
                "Test connection: docker ps | grep qdrant",
                "Check Qdrant service logs for errors"
            ]

            # Categorize the error for better guidance
            error_str = str(e).lower()
            if "connection" in error_str or "timeout" in error_str:
                guidance.insert(0, "Check network connectivity to Qdrant service")
            elif "unauthorized" in error_str or "forbidden" in error_str:
                guidance.insert(0, "Verify API key permissions")
            elif "not found" in error_str:
                guidance.insert(0, "Check Qdrant service URL and port")

            return ValidationResult(
                service=service_name,
                valid=False,
                error=error_msg,
                details={
                    "url": config.qdrant_url,
                    "error_type": "connection_error"
                },
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

    def validate_all_services(self, config: Config) -> List[ValidationResult]:
        """
        Validate all required services.

        Args:
            config: Configuration object with service settings

        Returns:
            List of validation results for all services
        """
        results = []

        # Validate Ollama service
        ollama_result = self.validate_ollama_service(config)
        results.append(ollama_result)

        # Validate Qdrant service
        qdrant_result = self.validate_qdrant_service(config)
        results.append(qdrant_result)

        return results

    def get_service_status(self, config: Config) -> Dict[str, Any]:
        """
        Get current status of all services.

        Args:
            config: Configuration object with service settings

        Returns:
            Dictionary with service status information
        """
        results = self.validate_all_services(config)

        status = {
            "all_healthy": all(result.valid for result in results),
            "services": {},
            "timestamp": datetime.now().isoformat(),
            "total_response_time_ms": sum(r.response_time_ms or 0 for r in results)
        }

        for result in results:
            status["services"][result.service] = {
                "healthy": result.valid,
                "error": result.error,
                "details": result.details,
                "response_time_ms": result.response_time_ms,
                "actionable_guidance": result.actionable_guidance
            }

        return status

    def clear_validation_cache(self) -> None:
        """Clear the validation cache."""
        self._validation_cache.clear()

    def get_cached_validation(self, service: str) -> Optional[Dict[str, Any]]:
        """
        Get cached validation result for a service.

        Args:
            service: Service name

        Returns:
            Cached validation data or None if not available
        """
        return self._validation_cache.get(service)