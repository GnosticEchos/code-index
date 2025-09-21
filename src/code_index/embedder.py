"""
Ollama embedder for the code index tool.
"""
import requests
from typing import List, Dict, Any, Optional
from code_index.config import Config
from code_index.service_validation import ValidationResult


class OllamaEmbedder:
    """Interface with Ollama API for generating embeddings."""
    
    def __init__(self, config: Config):
        """Initialize Ollama embedder with configuration."""
        self.base_url = config.ollama_base_url.rstrip("/")
        self.model = config.ollama_model
        # Timeout is configurable via config (and may be overridden by CLI/env before construction)
        self.timeout = int(getattr(config, "embed_timeout_seconds", 60) or 60)

    @property
    def model_identifier(self) -> str:
        """
        Canonical embedding model identifier for payload/metadata.
        - If configured model ends with ':latest', return without the suffix.
        - Otherwise return configured value as-is (including explicit tags like ':v1.5').
        """
        try:
            m = self.model or ""
        except AttributeError:
            m = ""
        return m[:-7] if m.endswith(":latest") else m
    def create_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        """
        Generate embeddings for texts using Ollama API.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Dictionary with embeddings and usage data
        """
        if not texts:
            return {"embeddings": []}
        
        url = f"{self.base_url}/api/embed"
        
        try:
            response = requests.post(
                url,
                json={
                    "model": self.model,
                    "input": texts
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            embeddings = data.get("embeddings", [])
            
            if not isinstance(embeddings, list):
                raise ValueError("Invalid response structure from Ollama API")
            
            return {
                "embeddings": embeddings
            }
        except requests.exceptions.ReadTimeout as e:
            # Bubble up read timeouts so the caller can treat them as retriable and log file in timeout list
            raise e
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to generate embeddings: {e}")
        except ValueError as e:
            raise Exception(f"Invalid response from Ollama API: {e}")
    
    def validate_configuration(self) -> ValidationResult:
        """
        Validate Ollama configuration.

        Returns:
            ValidationResult with detailed validation status
        """
        import time
        start_time = time.time()

        try:
            # Check if Ollama service is running
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=30
            )
            response.raise_for_status()

            # Check if the specific model exists
            models_data = response.json()
            models = models_data.get("models", [])

            model_exists = any(
                model.get("name") == self.model or
                model.get("name") == f"{self.model}:latest" or
                model.get("name") == self.model.replace(":latest", "")
                for model in models
            )

            if not model_exists:
                available_models = [model.get("name", "") for model in models]
                error_msg = f"Model '{self.model}' not found"
                guidance = [
                    f"Available models: {', '.join(available_models[:5])}",
                    "Pull the required model using: ollama pull <model_name>",
                    "Check model name spelling and version tag",
                    "Verify model is compatible with embedding tasks"
                ]

                return ValidationResult(
                    service="ollama",
                    valid=False,
                    error=error_msg,
                    details={
                        "available_models": available_models,
                        "requested_model": self.model,
                        "base_url": self.base_url
                    },
                    response_time_ms=int((time.time() - start_time) * 1000),
                    actionable_guidance=guidance
                )

            # Test embedding generation
            test_response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": ["test"]
                },
                timeout=30
            )
            test_response.raise_for_status()

            # Test successful
            return ValidationResult(
                service="ollama",
                valid=True,
                details={
                    "base_url": self.base_url,
                    "model": self.model,
                    "available_models_count": len(models),
                    "response_time_ms": int((time.time() - start_time) * 1000)
                },
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to Ollama service at {self.base_url}"
            guidance = [
                "Start Ollama service: ollama serve",
                "Verify service is running on the specified URL",
                "Check firewall and network connectivity",
                "Ensure Ollama is installed and accessible"
            ]

            return ValidationResult(
                service="ollama",
                valid=False,
                error=error_msg,
                details={
                    "base_url": self.base_url,
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
                service="ollama",
                valid=False,
                error=error_msg,
                details={
                    "base_url": self.base_url,
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
                service="ollama",
                valid=False,
                error=error_msg,
                details={
                    "base_url": self.base_url,
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
                service="ollama",
                valid=False,
                error=error_msg,
                details={
                    "base_url": self.base_url,
                    "error_type": "validation_error"
                },
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=guidance
            )

    def validate_configuration_dict(self) -> Dict[str, Any]:
        """
        Validate Ollama configuration (legacy method for backward compatibility).

        Returns:
            Dictionary with validation result (for backward compatibility)
        """
        result = self.validate_configuration()
        return {
            "valid": result.valid,
            "error": result.error,
            "details": result.details
        }

    def validate_configuration_and_raise(self) -> None:
        """
        Validate Ollama configuration and raise exception if invalid.

        This method maintains backward compatibility with code that expects
        exceptions to be raised on validation failures.
        """
        result = self.validate_configuration()
        result.raise_for_errors()