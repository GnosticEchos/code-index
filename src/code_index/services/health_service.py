"""
Health service for monitoring service health and system status.

This service handles health checks for various services.
"""
import time
from typing import List, Dict, Any, Optional

from ..config import Config
from ..models import ValidationResult
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class HealthService:
    """Service for monitoring service health and system status."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize health service."""
        self.error_handler = error_handler or ErrorHandler()
    
    def check_health(self, config: Config) -> List[Dict[str, Any]]:
        """Check the health of various services."""
        try:
            from ..service_validation import ServiceValidator
            service_validator = ServiceValidator(self.error_handler)
            return service_validator.validate_all_services(config)
        except Exception as e:
            error_context = ErrorContext(
                component="health_service",
                operation="check_health"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )
            return [
                {
                    "service": "health_service",
                    "is_healthy": False,
                    "error": error_response.message,
                    "response_time_ms": 0,
                    "last_check_timestamp": None
                }
            ]
    
    def validate_health_config(self, config: Config) -> ValidationResult:
        """Validate health configuration."""
        start_time = time.time()
        errors: List[str] = []
        metadata: Dict[str, Any] = {}
        
        try:
            # Validate service URLs
            if not getattr(config, "ollama_base_url"):
                errors.append("No Ollama base URL configured")
            elif not getattr(config, "qdrant_url"):
                errors.append("No Qdrant URL configured")
            elif not getattr(config, "workspace_path"):
                errors.append("No workspace path configured")
            
            # Validate service configuration
            if getattr(config, "ollama_model") not in ["llama3.2:3b", "llama3:70b", "codellama:7b", "deepseek-r1:7b"]:
                warnings = metadata.get("warnings", [])
                metadata["warnings"] = warnings + [f"Unknown model: {getattr(config, 'ollama_model') if getattr(config, 'ollama_model') else 'unknown model not configured'}"]
            
            combined_error = "; ".join(errors) if errors else None
            return ValidationResult(
                service="health_service",
                valid=len(errors) == 0,
                error=combined_error,
                details=metadata,
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check configuration and service connectivity"]
            )
        except Exception as e:
            error_context = ErrorContext(
                component="health_service",
                operation="validate_health_config"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="health_service",
                valid=False,
                error=error_response.message,
                details={},
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check configuration and service connectivity"]
            )