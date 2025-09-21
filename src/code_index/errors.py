"""
Centralized error handling system for the code index tool.

This module provides a comprehensive error handling framework with:
- Error categorization and severity levels
- Context collection and reporting
- Recovery suggestions and fallbacks
- Structured error responses
- Integration with logging systems
"""

import logging
import traceback
import sys
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Minor issues, operation can continue
    MEDIUM = "medium"     # Important issues, but operation can continue
    HIGH = "high"         # Critical issues, operation should stop
    CRITICAL = "critical" # System-level failures, immediate shutdown required


class ErrorCategory(Enum):
    """Error categories for better organization and handling."""
    VALIDATION = "validation"      # Configuration or input validation errors
    FILE_SYSTEM = "file_system"    # File/directory operation errors
    NETWORK = "network"           # Network/API connectivity errors
    PARSING = "parsing"           # Code parsing or chunking errors
    DATABASE = "database"         # Vector store/database errors
    CONFIGURATION = "configuration" # Configuration loading/processing errors
    SERVICE = "service"           # External service connectivity errors
    UNKNOWN = "unknown"           # Unclassified errors


@dataclass
class ErrorContext:
    """Context information for error reporting."""
    component: str                    # Component where error occurred
    operation: str                   # Operation being performed
    file_path: Optional[str] = None  # File path if applicable
    line_number: Optional[int] = None # Line number if applicable
    additional_data: Optional[Dict[str, Any]] = None  # Additional context data

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "component": self.component,
            "operation": self.operation,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "additional_data": self.additional_data or {}
        }


@dataclass
class ErrorResponse:
    """Structured error response."""
    error: bool
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: ErrorContext
    timestamp: datetime
    recovery_suggestions: List[str]
    actionable_guidance: List[str]
    original_exception: Optional[Exception] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary."""
        return {
            "error": self.error,
            "error_type": self.error_type,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "recovery_suggestions": self.recovery_suggestions,
            "actionable_guidance": self.actionable_guidance,
            "stack_trace": self.stack_trace
        }


class ErrorHandler:
    """
    Centralized error handling system.

    Provides structured error handling with categorization, context collection,
    recovery suggestions, and integration with logging systems.
    """

    def __init__(self, logger_name: str = "code_index"):
        """Initialize the error handler."""
        self.logger = logging.getLogger(logger_name)
        self._recovery_strategies: Dict[str, Callable] = {}

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        include_stack_trace: bool = True
    ) -> ErrorResponse:
        """
        Handle a general error with full context and structured response.

        Args:
            error: The exception that occurred
            context: Context information about where/why the error occurred
            category: Error category (auto-detected if not provided)
            severity: Error severity (auto-detected if not provided)
            include_stack_trace: Whether to include stack trace in response

        Returns:
            Structured error response
        """
        # Auto-detect category and severity if not provided
        if category is None:
            category = self._categorize_error(error, context)
        if severity is None:
            severity = self._determine_severity(error, context)

        # Collect error context
        error_context = self._collect_error_context(error, context)

        # Generate recovery suggestions
        recovery_suggestions = self._generate_recovery_suggestions(error, context, category)
        actionable_guidance = self._generate_actionable_guidance(error, context, category)

        # Create error response
        error_response = ErrorResponse(
            error=True,
            error_type=type(error).__name__,
            category=category,
            severity=severity,
            message=str(error),
            context=context,
            timestamp=datetime.now(),
            recovery_suggestions=recovery_suggestions,
            actionable_guidance=actionable_guidance,
            original_exception=error,
            stack_trace=traceback.format_exc() if include_stack_trace else None
        )

        # Add collected context to the response context
        if context.additional_data is None:
            context.additional_data = {}
        context.additional_data.update(error_context)

        # Log the error
        self._log_error(error_response)

        return error_response

    def handle_validation_error(
        self,
        error: Exception,
        context: ErrorContext,
        validation_field: Optional[str] = None
    ) -> ErrorResponse:
        """
        Handle validation errors specifically.

        Args:
            error: The validation exception
            context: Context information
            validation_field: The field that failed validation

        Returns:
            Structured error response for validation failures
        """
        if validation_field:
            context.additional_data = context.additional_data or {}
            context.additional_data["validation_field"] = validation_field

        return self.handle_error(
            error,
            context,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH
        )

    def handle_file_error(
        self,
        error: Exception,
        context: ErrorContext,
        file_operation: Optional[str] = None
    ) -> ErrorResponse:
        """
        Handle file system errors specifically.

        Args:
            error: The file system exception
            context: Context information
            file_operation: The file operation that failed

        Returns:
            Structured error response for file operation failures
        """
        if file_operation:
            context.additional_data = context.additional_data or {}
            context.additional_data["file_operation"] = file_operation

        return self.handle_error(
            error,
            context,
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM
        )

    def handle_network_error(
        self,
        error: Exception,
        context: ErrorContext,
        service_name: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> ErrorResponse:
        """
        Handle network/API errors specifically.

        Args:
            error: The network exception
            context: Context information
            service_name: Name of the service (e.g., "Ollama", "Qdrant")
            endpoint: The endpoint that failed

        Returns:
            Structured error response for network failures
        """
        context.additional_data = context.additional_data or {}
        if service_name:
            context.additional_data["service_name"] = service_name
        if endpoint:
            context.additional_data["endpoint"] = endpoint

        return self.handle_error(
            error,
            context,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH
        )

    def handle_service_connection_error(
        self,
        service_name: str,
        error: Exception,
        context: ErrorContext
    ) -> ErrorResponse:
        """
        Handle service connection errors with specific guidance.

        Args:
            service_name: Name of the service (e.g., "Ollama", "Qdrant")
            error: The connection exception
            context: Context information

        Returns:
            Structured error response for service connection failures
        """
        context.additional_data = context.additional_data or {}
        context.additional_data["service_name"] = service_name

        return self.handle_network_error(error, context, service_name)

    def handle_configuration_error(
        self,
        error: Exception,
        context: ErrorContext,
        config_file: Optional[str] = None
    ) -> ErrorResponse:
        """
        Handle configuration errors specifically.

        Args:
            error: The configuration exception
            context: Context information
            config_file: Path to the configuration file

        Returns:
            Structured error response for configuration failures
        """
        if config_file:
            context.additional_data = context.additional_data or {}
            context.additional_data["config_file"] = config_file

        return self.handle_error(
            error,
            context,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL
        )

    def handle_unknown_error(
        self,
        error: Exception,
        context: ErrorContext
    ) -> ErrorResponse:
        """
        Handle unknown/unexpected errors.

        Args:
            error: The unexpected exception
            context: Context information

        Returns:
            Structured error response for unknown errors
        """
        return self.handle_error(
            error,
            context,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.CRITICAL
        )

    def _categorize_error(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Auto-detect error category based on exception type and context."""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()

        # Network-related errors
        if any(keyword in error_type for keyword in ['connection', 'timeout', 'network', 'http']):
            return ErrorCategory.NETWORK
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'http']):
            return ErrorCategory.NETWORK

        # File system errors
        if any(keyword in error_type for keyword in ['filenotfound', 'permission', 'ioerror', 'oserror']):
            return ErrorCategory.FILE_SYSTEM
        if any(keyword in error_message for keyword in ['file not found', 'permission denied', 'no such file']):
            return ErrorCategory.FILE_SYSTEM

        # Parsing errors (check before validation to catch JSONDecodeError, etc.)
        if any(keyword in error_type for keyword in ['parse', 'syntax', 'chunk', 'decode']):
            return ErrorCategory.PARSING

        # Validation errors
        if any(keyword in error_type for keyword in ['value']):
            return ErrorCategory.VALIDATION
        if any(keyword in error_message for keyword in ['invalid', 'validation']):
            return ErrorCategory.VALIDATION

        # Configuration errors
        if any(keyword in error_type for keyword in ['config']):
            return ErrorCategory.CONFIGURATION
        if any(keyword in error_message for keyword in ['configuration', 'config']):
            return ErrorCategory.CONFIGURATION

        # Database/vector store errors
        if any(keyword in error_type for keyword in ['database', 'vector', 'qdrant']):
            return ErrorCategory.DATABASE

        # Default to unknown
        return ErrorCategory.UNKNOWN

    def _determine_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """Auto-detect error severity based on exception type and context."""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()

        # Critical errors - system cannot continue
        if any(keyword in error_type for keyword in ['systemexit', 'keyboardinterrupt']):
            return ErrorSeverity.CRITICAL

        # High severity errors - operation should stop
        if any(keyword in error_type for keyword in ['importerror', 'modulenotfound', 'runtime']):
            return ErrorSeverity.HIGH
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'cannot continue']):
            return ErrorSeverity.HIGH

        # Medium severity errors - operation can continue but with warnings
        if any(keyword in error_type for keyword in ['valueerror', 'typeerror', 'attributeerror']):
            return ErrorSeverity.MEDIUM
        if any(keyword in error_message for keyword in ['warning', 'deprecated', 'not found']):
            return ErrorSeverity.MEDIUM

        # Default to low severity
        return ErrorSeverity.LOW

    def _collect_error_context(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Collect additional context information for the error."""
        error_context = {
            "error_type": type(error).__name__,
            "error_module": type(error).__module__,
            "python_version": sys.version,
            "platform": sys.platform
        }

        # Add file context if available
        if context.file_path:
            try:
                import os
                error_context["file_exists"] = os.path.exists(context.file_path)
                error_context["file_size"] = os.path.getsize(context.file_path) if os.path.exists(context.file_path) else 0
            except Exception:
                pass

        return error_context

    def _generate_recovery_suggestions(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> List[str]:
        """Generate recovery suggestions based on error type and category."""
        suggestions = []

        if category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check network connectivity",
                "Verify service URLs and endpoints",
                "Check firewall and security settings",
                "Retry the operation with exponential backoff"
            ])

        elif category == ErrorCategory.FILE_SYSTEM:
            suggestions.extend([
                "Check file/directory permissions",
                "Verify file paths exist",
                "Check available disk space",
                "Ensure write permissions for target directories"
            ])

        elif category == ErrorCategory.CONFIGURATION:
            suggestions.extend([
                "Review configuration file syntax",
                "Check for missing required fields",
                "Verify configuration file paths",
                "Restore from backup configuration if available"
            ])

        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check input data format and types",
                "Verify required fields are present",
                "Review validation constraints",
                "Check for data type mismatches"
            ])

        # Add general suggestions
        suggestions.extend([
            "Check application logs for more details",
            "Review documentation for troubleshooting steps",
            "Consider restarting the application",
            "Contact support if issue persists"
        ])

        return suggestions

    def _generate_actionable_guidance(self, error: Exception, context: ErrorContext, category: ErrorCategory) -> List[str]:
        """Generate actionable guidance for resolving the error."""
        guidance = []

        if category == ErrorCategory.NETWORK:
            guidance.extend([
                "Verify the service is running and accessible",
                "Check network configuration and firewall rules",
                "Test connectivity using ping or telnet",
                "Review service logs for connection errors"
            ])

        elif category == ErrorCategory.FILE_SYSTEM:
            guidance.extend([
                "Run 'ls -la' to check file permissions",
                "Use 'chmod' to fix permission issues",
                "Check available disk space with 'df -h'",
                "Verify file paths are correct and accessible"
            ])

        elif category == ErrorCategory.CONFIGURATION:
            guidance.extend([
                "Open configuration file in editor",
                "Check JSON/YAML syntax with validation tools",
                "Compare with working configuration backup",
                "Review configuration documentation"
            ])

        elif category == ErrorCategory.VALIDATION:
            guidance.extend([
                "Check input data format and types",
                "Verify required fields are present",
                "Review validation constraints",
                "Check for data type mismatches"
            ])

        # Add general guidance if no specific guidance was added
        if not guidance:
            guidance.extend([
                "Check application logs for more details",
                "Review documentation for troubleshooting steps",
                "Consider restarting the application",
                "Contact support if issue persists"
            ])

        return guidance

    def _log_error(self, error_response: ErrorResponse) -> None:
        """Log the error using appropriate log level based on severity."""
        log_message = f"[{error_response.category.value.upper()}] {error_response.message}"
        log_context = f"Component: {error_response.context.component}, Operation: {error_response.context.operation}"

        if error_response.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"{log_message} | {log_context}")
        elif error_response.severity == ErrorSeverity.HIGH:
            self.logger.error(f"{log_message} | {log_context}")
        elif error_response.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"{log_message} | {log_context}")
        else:
            self.logger.info(f"{log_message} | {log_context}")

        # Log stack trace for high severity errors
        if error_response.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and error_response.stack_trace:
            self.logger.debug(f"Stack trace: {error_response.stack_trace}")

    def register_recovery_strategy(self, error_type: str, strategy: Callable) -> None:
        """
        Register a custom recovery strategy for specific error types.

        Args:
            error_type: Type of error to handle
            strategy: Callable that implements the recovery logic
        """
        self._recovery_strategies[error_type] = strategy

    def should_retry(self, error_response: ErrorResponse, attempt_count: int, max_attempts: int = 3) -> bool:
        """
        Determine if an operation should be retried based on error response.

        Args:
            error_response: The error response from the failed operation
            attempt_count: Current attempt number (1-based)
            max_attempts: Maximum number of retry attempts

        Returns:
            True if the operation should be retried
        """
        if attempt_count >= max_attempts:
            return False

        # Don't retry critical errors
        if error_response.severity == ErrorSeverity.CRITICAL:
            return False

        # Don't retry configuration errors
        if error_response.category == ErrorCategory.CONFIGURATION:
            return False

        # Retry network errors (with exponential backoff)
        if error_response.category == ErrorCategory.NETWORK:
            return True

        # Retry file system errors (might be temporary)
        if error_response.category == ErrorCategory.FILE_SYSTEM:
            return True

        return False

    def get_retry_delay(self, error_response: ErrorResponse, attempt_count: int) -> float:
        """
        Calculate retry delay in seconds using exponential backoff.

        Args:
            error_response: The error response
            attempt_count: Current attempt number

        Returns:
            Delay in seconds before next retry
        """
        base_delay = 1.0

        # Longer delays for network errors
        if error_response.category == ErrorCategory.NETWORK:
            base_delay = 2.0

        # Exponential backoff with jitter
        delay = base_delay * (2 ** (attempt_count - 1))
        jitter = delay * 0.1  # 10% jitter

        return delay + jitter


# Global error handler instance
error_handler = ErrorHandler()