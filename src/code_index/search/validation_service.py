"""
Search validation service for validating search configuration and operations.
"""
import time
from typing import List, Dict, Any, Optional

from ..config import Config
from ..models import ValidationResult
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class SearchValidationService:
    """Service for validating search configuration and operations."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize validation service."""
        self.error_handler = error_handler or ErrorHandler()
    
    def validate_search_config(self, config: Config) -> ValidationResult:
        """Validate search configuration."""
        start_time = time.time()
        errors: List[str] = []
        metadata: Dict[str, Any] = {}
        
        try:
            # Validate search configuration
            if not getattr(config, "search_min_score"):
                errors.append("No minimum score configured")
            elif getattr(config, "search_min_score") < 0 or getattr(config, "search_min_score") > 1:
                errors.append("search_min_score must be between 0 and 1")
            elif getattr(config, "search_max_results") <= 0:
                errors.append("Max results must be positive")
            elif getattr(config, "search_strategy") not in ["text", "similarity", "embedding"]:
                errors.append("Invalid search strategy")
            
            combined_error = "; ".join(errors) if errors else None
            return ValidationResult(
                service="search_validation_service",
                valid=len(errors) == 0,
                error=combined_error,
                details=metadata,
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check search configuration"]
            )
        except Exception as e:
            error_context = ErrorContext(
                component="search_validation_service",
                operation="validate_search_config"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="search_validation_service",
                valid=False,
                error=error_response.message,
                details={},
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check search configuration"]
            )
    
    def validate_query(self, query: str) -> bool:
        """Validate search query."""
        try:
            if not query or not query.strip():
                return False
            
            # Check for minimum length
            query = query.strip()
            if len(query) < 2:
                return False
            
            # Check for valid characters
            import re
            if not re.match(r'^[a-zA-Z0-9_\-\s]+$', query):
                return False
            
            return True
        except Exception as e:
            return False
    
    def get_validation_info(self) -> Dict[str, Any]:
        """Get validation information."""
        return {
            "min_query_length": 2,
            "allowed_characters": "letters, numbers, spaces, underscores, hyphens",
            "disallowed_characters": "special characters, symbols, punctuation"
        }