"""
Dimension validation service to prevent model/dimension corruption.

This service ensures users search with correct model/dimensions
and provides clear guidance for mismatches.
"""

from typing import Dict, Any, Optional, List

from ...config import Config
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ...service_validation import ValidationResult
from ...constants import HTTP_TIMEOUT_DEFAULT


class DimensionValidator:
    """
    Service to validate embedding model/dimension compatibility.
    
    Prevents the bug where searching with wrong dimensions
    corrupts collection metadata.
    """
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the dimension validator."""
        self.error_handler = error_handler or ErrorHandler()
    
    def validate_model_compatibility(self, config: Config, collection_path: Optional[str] = None) -> ValidationResult:
        """
        Validate that the current model/dimensions match the collection.
        
        Args:
            config: Current configuration
            collection_path: Optional path to check collection metadata
            
        Returns:
            ValidationResult with compatibility status
        """
        try:
            errors = []
            warnings = []
            metadata = {}
            
            # Get expected dimensions from current config
            expected_dims = config.embedding_length
            current_model = config.ollama_model
            
            metadata.update({
                "current_model": current_model,
                "expected_dimensions": expected_dims,
                "chunking_strategy": config.chunking_strategy
            })
            
            # Dynamic dimension detection via Ollama API
            actual_dims = self._get_model_dimensions(current_model, config.ollama_base_url)
            
            if actual_dims is None:
                warnings.append(
                    f"Could not determine dimensions for '{current_model}'. "
                    f"Using configured dimension: {expected_dims}. "
                    f"Consider validating with: ollama show {current_model}"
                )
            elif actual_dims != expected_dims:
                warnings.append(
                    f"Dimension mismatch: config specifies {expected_dims} but model '{current_model}' "
                    f"has {actual_dims} dimensions"
                )
                metadata["actual_dimensions"] = actual_dims
                
            # Add guidance based on model name patterns
                if "qwen" in current_model.lower():
                    warnings.append("Qwen models typically use 1024 dimensions")
                elif "nomic" in current_model.lower():
                    warnings.append("Nomic models typically use 768 dimensions")
                elif "large" in current_model.lower():
                    warnings.append("Large embedding models typically use 3584+ dimensions")
            
            # Validate dimension consistency (only warn for known models)
            guide = self.get_model_dimension_guide()
            supported_models = {k: v["dimensions"] for k, v in guide["supported_models"].items()}
            
            if current_model in supported_models and expected_dims != supported_models[current_model]:
                errors.append(
                    f"Dimension mismatch: config specifies {expected_dims} but model '{current_model}' "
                    f"uses {supported_models[current_model]} dimensions"
                )
            
            return ValidationResult(
                service="dimension_validator",
                valid=len(errors) == 0,
                error="; ".join(errors) if errors else None,
                warnings=warnings,
                details=metadata,
                actionable_guidance=[
                    "Check your configuration file for correct model/dimension settings",
                    "Ensure you use the same model for indexing and searching",
                    "Re-index if you need to change models"
                ]
            )
            
        except Exception as e:
            error_context = ErrorContext(
                component="dimension_validator",
                operation="validate_model_compatibility"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            
            return ValidationResult(
                service="dimension_validator",
                valid=False,
                error=f"Validation failed: {error_response.message}",
                details={"validation_error": str(e)}
            )
    
    def get_model_dimension_guide(self) -> Dict[str, Any]:
        """Get a guide for model/dimension mappings."""
        return {
            "supported_models": {
                "nomic-embed-text:latest": {
                    "dimensions": 768,
                    "description": "General purpose embedding model",
                    "recommended_for": ["general_code", "documentation"]
                },
                "dengcao/Qwen3-Embedding-0.6B:F16": {
                    "dimensions": 1024,
                    "description": "High-quality embeddings for code analysis",
                    "recommended_for": ["code_search", "semantic_analysis"]
                },
                "text-embedding-3-large": {
                    "dimensions": 3584,
                    "description": "Large embeddings for complex queries",
                    "recommended_for": ["complex_search", "advanced_analysis"]
                }
            },
            "troubleshooting": {
                "dimension_mismatch": "Re-index with correct model",
                "model_change": "Update config and re-index entire workspace",
                "mixed_models": "Use separate collections for different models"
            }
        }
    
    def _get_model_dimensions(self, model_name: str, base_url: str = "http://localhost:11434") -> Optional[int]:
        """
        Get actual embedding dimensions from Ollama API.
        
        Args:
            model_name: Name of the model to check
            base_url: Ollama API base URL
            
        Returns:
            Integer dimensions or None if unavailable
        """
        try:
            import requests
            
            # Query Ollama API for model details
            response = requests.post(
                f"{base_url}/api/show",
                json={"model": model_name},
                timeout=HTTP_TIMEOUT_DEFAULT
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract embedding dimensions from model_info
                model_info = data.get("model_info", {})
                dimensions = model_info.get("llama.embedding_length")
                
                if dimensions:
                    return int(dimensions)
                    
            return None
            
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                ErrorContext(
                    component="dimension_validator",
                    operation="get_model_dimensions",
                    additional_data={"model": model_name, "url": base_url}
                ),
                ErrorCategory.NETWORK, ErrorSeverity.LOW
            )
            return None

    def create_dimension_checklist(self, config: Config) -> List[str]:
        """Create a checklist for dimension validation."""
        actual_dims = self._get_model_dimensions(config.ollama_model, config.ollama_base_url)
        
        checklist = [
            f"✓ Current model: {config.ollama_model}",
            f"✓ Configured dimensions: {config.embedding_length}",
            f"✓ Chunking strategy: {config.chunking_strategy}",
        ]
        
        if actual_dims:
            checklist.append(f"✓ Actual model dimensions: {actual_dims}")
            if actual_dims != config.embedding_length:
                checklist.append(f"⚠️  MISMATCH: Update config.embedding_length to {actual_dims}")
        else:
            checklist.append("⚠️  Could not verify model dimensions via Ollama API")
            
        checklist.extend([
            f"✓ Ollama base URL: {config.ollama_base_url}",
            "✓ Use same config for indexing and searching",
            f"✓ Verify via: ollama show {config.ollama_model}"
        ])
        
        return checklist


def validate_search_configuration(config: Config, collection_path: Optional[str] = None) -> ValidationResult:
    """
    Convenience function to validate search configuration.
    
    Args:
        config: Configuration to validate
        collection_path: Optional collection path
        
    Returns:
        ValidationResult with detailed guidance
    """
    validator = DimensionValidator()
    return validator.validate_model_compatibility(config, collection_path)
