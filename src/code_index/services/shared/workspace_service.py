"""
Workspace service for workspace validation and configuration.

This service handles workspace validation and workspace-specific configuration.
"""
import time
from typing import List, Dict, Any, Optional

from pathlib import Path

from ...config import Config
from ...models import ValidationResult
from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class WorkspaceService:
    """Service for workspace validation and configuration."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize workspace service."""
        self.error_handler = error_handler or ErrorHandler()
    
    def validate_workspace(self, workspace: str, config: Config) -> ValidationResult:
        """Validate workspace configuration."""
        start_time = time.time()
        errors: List[str] = []
        metadata: Dict[str, Any] = {}
        
        try:
            # Validate workspace path
            workspace_path = Path(workspace)
            if not workspace_path.exists():
                errors.append(f"Workspace path does not exist: {workspace}")
            elif not workspace_path.is_dir():
                errors.append(f"Workspace is not a directory: {workspace}")
            
            # Validate configuration
            if not getattr(config, "workspace_path"):
                errors.append("No workspace path configured")
            elif Path(getattr(config, "workspace_path")).resolve() != workspace_path.resolve():
                errors.append("Workspace path mismatch")
            
            # Check for required files
            required_files = ["pyproject.toml", "README.md"]
            missing_files = []
            for file in required_files:
                if not (workspace_path / file).exists():
                    missing_files.append(file)
            
            if missing_files:
                metadata["missing_files"] = missing_files
                if len(missing_files) > 2:
                    errors.append(f"Missing required files: {', '.join(missing_files)}")
                else:
                    metadata["warnings"] = [f"Missing files: {', '.join(missing_files)}"]
            
            combined_error = "; ".join(errors) if errors else None
            return ValidationResult(
                service="workspace_service",
                valid=len(errors) == 0,
                error=combined_error,
                details=metadata,
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check workspace configuration"]
            )
        except Exception as e:
            error_context = ErrorContext(
                component="workspace_service",
                operation="validate_workspace"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )
            return ValidationResult(
                service="workspace_service",
                valid=False,
                error=error_response.message,
                details={},
                response_time_ms=int((time.time() - start_time) * 1000),
                actionable_guidance=["Check workspace configuration"]
            )
    
    def get_workspace_info(self, workspace: str) -> Dict[str, Any]:
        """Get workspace information."""
        try:
            workspace_path = Path(workspace)
            if not workspace_path.exists() or not workspace_path.is_dir():
                return {}
            
            # Get workspace metadata
            metadata = {
                "workspace_path": str(workspace_path.resolve()),
                "workspace_name": workspace_path.name,
                "workspace_size": self._get_directory_size(workspace_path),
                "file_count": self._count_files_in_directory(workspace_path),
            }
            
            # Add configuration files
            config_files = {}
            for config_file in workspace_path.glob("**/*.json"):
                config_files[str(config_file)] = "configuration file"
            
            metadata["config_files"] = config_files
            
            return metadata
        except Exception as e:
            error_context = ErrorContext(
                component="workspace_service",
                operation="get_workspace_info"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )
            return {}
    
    def _get_directory_size(self, path: Path) -> str:
        """Get directory size in human-readable format."""
        # Convert to human-readable format
        total_size = 0
        for file_path in path.rglob("**/*"):
            try:
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            except Exception:
                # Handle permission errors
                pass
        
        for unit in ["B", "KB", "MB", "GB"]:
            if total_size < 1024.0:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024.0
        
        return f"{total_size:.1f} TB"
    
    def _count_files_in_directory(self, path: Path) -> int:
        """Count files in directory."""
        try:
            return len([f for f in path.rglob("**/*") if f.is_file()])
        except Exception:
            return 0