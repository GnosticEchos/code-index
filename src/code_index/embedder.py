"""
Ollama embedder for the code index tool.
"""
import requests
from typing import List, Dict, Any, Optional
from code_index.config import Config


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
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate Ollama configuration.
        
        Returns:
            Dictionary with validation result
        """
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
                available_models = [model.get("name") for model in models]
                return {
                    "valid": False,
                    "error": f"Model '{self.model}' not found. Available models: {', '.join(available_models)}"
                }
            
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
            
            return {"valid": True}
        except requests.exceptions.ConnectionError:
            return {
                "valid": False,
                "error": f"Cannot connect to Ollama service at {self.base_url}"
            }
        except requests.exceptions.RequestException as e:
            return {
                "valid": False,
                "error": f"Ollama service error: {e}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Configuration validation failed: {e}"
            }