"""
IndexingService for CQRS pattern implementation.

This service handles workspace indexing commands, separating business logic
from CLI concerns and providing a clean interface for indexing operations.
"""

import time
import uuid
from typing import List, Set, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..config import Config
from ..config_service import ConfigurationService
from ..file_processing import FileProcessingService
from ..service_validation import ServiceValidator
from ..scanner import DirectoryScanner
from ..parser import CodeParser
from ..embedder import OllamaEmbedder
from ..vector_store import QdrantVectorStore
from ..cache import CacheManager
from ..chunking import (
    ChunkingStrategy,
    LineChunkingStrategy,
    TokenChunkingStrategy,
    TreeSitterChunkingStrategy,
)
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..path_utils import PathUtils
from ..models import IndexingResult, ProcessingResult, ValidationResult


class IndexingService:
    """
    Service for handling workspace indexing operations.

    This service encapsulates the business logic for indexing code files,
    separating command operations from query operations and CLI concerns.
    """

    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the IndexingService with required dependencies."""
        self.error_handler = error_handler or ErrorHandler()
        self.config_service = ConfigurationService(self.error_handler)
        self.file_processor = FileProcessingService(self.error_handler)
        self.service_validator = ServiceValidator(self.error_handler)

    def index_workspace(self, workspace: str, config: Config) -> IndexingResult:
        """
        Execute indexing command for a workspace.

        Args:
            workspace: Path to the workspace to index
            config: Configuration object with indexing parameters

        Returns:
            IndexingResult with detailed operation results
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        timed_out_files: List[str] = []

        try:
            # Validate workspace before processing
            validation_result = self.validate_workspace(workspace, config)
            if not validation_result.valid:
                errors.extend(validation_result.errors)
                return IndexingResult(
                    processed_files=0,
                    total_blocks=0,
                    errors=errors,
                    warnings=warnings,
                    timed_out_files=timed_out_files,
                    processing_time_seconds=time.time() - start_time,
                    timestamp=datetime.now(),
                    workspace_path=workspace,
                    config_summary=self.config_service.get_config_summary(config)
                )

            # Initialize components
            scanner, parser, embedder, vector_store, cache_manager, path_utils = self._initialize_components(config)

            # Get file paths to process
            file_paths = self._get_file_paths(workspace, config, path_utils)

            if not file_paths:
                warnings.append("No files found to process after filtering")
                return IndexingResult(
                    processed_files=0,
                    total_blocks=0,
                    errors=errors,
                    warnings=warnings,
                    timed_out_files=timed_out_files,
                    processing_time_seconds=time.time() - start_time,
                    timestamp=datetime.now(),
                    workspace_path=workspace,
                    config_summary=self.config_service.get_config_summary(config)
                )

            vector_store.initialize()

            # Process files
            processed_count, total_blocks = self._process_files(
                file_paths, parser, embedder, vector_store, cache_manager,
                path_utils, config, timed_out_files, errors, warnings
            )

            return IndexingResult(
                processed_files=processed_count,
                total_blocks=total_blocks,
                errors=errors,
                warnings=warnings,
                timed_out_files=timed_out_files,
                processing_time_seconds=time.time() - start_time,
                timestamp=datetime.now(),
                workspace_path=workspace,
                config_summary=self.config_service.get_config_summary(config)
            )

        except Exception as e:
            error_context = ErrorContext(
                component="indexing_service",
                operation="index_workspace",
                additional_data={"workspace": workspace}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.CRITICAL
            )
            errors.append(error_response.message)

            return IndexingResult(
                processed_files=0,
                total_blocks=0,
                errors=errors,
                warnings=warnings,
                timed_out_files=timed_out_files,
                processing_time_seconds=time.time() - start_time,
                timestamp=datetime.now(),
                workspace_path=workspace,
                config_summary=self.config_service.get_config_summary(config)
            )

    def process_files(self, files: List[str], config: Config) -> List[ProcessingResult]:
        """
        Process a list of files for indexing.

        Args:
            files: List of file paths to process
            config: Configuration object with processing parameters

        Returns:
            List of ProcessingResult objects for each file
        """
        results: List[ProcessingResult] = []

        try:
            # Initialize components
            _, parser, embedder, vector_store, _, path_utils = self._initialize_components(config)

            for file_path in files:
                start_time = time.time()
                try:
                    # Parse file into blocks
                    blocks = parser.parse_file(file_path)
                    if not blocks:
                        results.append(ProcessingResult(
                            file_path=file_path,
                            success=False,
                            blocks_processed=0,
                            error="No code blocks generated",
                            processing_time_seconds=time.time() - start_time
                        ))
                        continue

                    # Generate embeddings
                    texts = [block.content for block in blocks if block.content.strip()]
                    if not texts:
                        results.append(ProcessingResult(
                            file_path=file_path,
                            success=False,
                            blocks_processed=0,
                            error="No text content to embed",
                            processing_time_seconds=time.time() - start_time
                        ))
                        continue

                    # Create embeddings
                    embedding_response = embedder.create_embeddings(texts)

                    # Prepare and upsert points
                    points = []
                    for i, block in enumerate(blocks):
                        if i >= len(embedding_response["embeddings"]):
                            break
                        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                                f"{file_path}:{block.start_line}:{block.end_line}"))
                        rel_path = path_utils.get_workspace_relative_path(file_path) or path_utils.normalize_path(file_path)
                        point = {
                            "id": point_id,
                            "vector": embedding_response["embeddings"][i],
                            "payload": {
                                "filePath": rel_path,
                                "codeChunk": block.content,
                                "startLine": block.start_line,
                                "endLine": block.end_line,
                                "type": block.type,
                                "embedding_model": embedder.model_identifier
                            }
                        }
                        points.append(point)

                    # Delete existing points and upsert new ones
                    rel_path = path_utils.get_workspace_relative_path(file_path) or path_utils.normalize_path(file_path)
                    vector_store.delete_points_by_file_path(rel_path)
                    vector_store.upsert_points(points)

                    results.append(ProcessingResult(
                        file_path=file_path,
                        success=True,
                        blocks_processed=len(blocks),
                        processing_time_seconds=time.time() - start_time
                    ))

                except Exception as e:
                    error_context = ErrorContext(
                        component="indexing_service",
                        operation="process_files",
                        file_path=file_path
                    )
                    error_response = self.error_handler.handle_file_error(
                        e, error_context, "file_processing"
                    )
                    results.append(ProcessingResult(
                        file_path=file_path,
                        success=False,
                        blocks_processed=0,
                        error=error_response.message,
                        processing_time_seconds=time.time() - start_time
                    ))

        except Exception as e:
            error_context = ErrorContext(
                component="indexing_service",
                operation="process_files"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.HIGH
            )

            # Mark remaining files as failed
            for file_path in files[len(results):]:
                results.append(ProcessingResult(
                    file_path=file_path,
                    success=False,
                    blocks_processed=0,
                    error=error_response.message
                ))

        return results

    def validate_workspace(self, workspace: str, config: Config) -> ValidationResult:
        """
        Validate workspace before indexing.

        Args:
            workspace: Path to the workspace to validate
            config: Configuration object with validation parameters

        Returns:
            ValidationResult with validation status and details
        """
        start_time = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        metadata: Dict[str, Any] = {}

        try:
            # Check if workspace path exists
            if not Path(workspace).exists():
                errors.append(f"Workspace path does not exist: {workspace}")
            elif not Path(workspace).is_dir():
                errors.append(f"Workspace path is not a directory: {workspace}")
            else:
                metadata["workspace_exists"] = True

                # Check workspace permissions
                if not Path(workspace).is_absolute():
                    abs_workspace = str(Path(workspace).resolve())
                    metadata["absolute_path"] = abs_workspace
                else:
                    abs_workspace = workspace

                # Check read access
                try:
                    test_file = Path(abs_workspace) / ".git" / "config"
                    if test_file.exists():
                        test_file.read_text()
                    else:
                        # Try to list directory contents
                        list(Path(abs_workspace).iterdir())
                    metadata["read_access"] = True
                except PermissionError:
                    errors.append(f"No read access to workspace: {abs_workspace}")
                except Exception:
                    # Other errors are acceptable for validation
                    metadata["read_access"] = True

                # Check for common project markers
                project_markers = ['.git', 'package.json', 'requirements.txt', 'Cargo.toml', 'pyproject.toml']
                found_markers = []
                for marker in project_markers:
                    if (Path(abs_workspace) / marker).exists():
                        found_markers.append(marker)

                if found_markers:
                    metadata["project_markers"] = found_markers
                    metadata["project_type"] = self._detect_project_type(found_markers)
                else:
                    warnings.append("No common project markers found - this may not be a code project")

                # Validate services
                service_results = self.service_validator.validate_all_services(config)
                failed_services = [result for result in service_results if not result.valid]

                if failed_services:
                    errors.extend([f"{result.service}: {result.error}" for result in failed_services])
                    metadata["service_validation"] = [result.to_dict() for result in service_results]
                else:
                    metadata["service_validation"] = [result.to_dict() for result in service_results]

            return ValidationResult(
                workspace_path=workspace,
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                validation_time_seconds=time.time() - start_time
            )

        except Exception as e:
            error_context = ErrorContext(
                component="indexing_service",
                operation="validate_workspace",
                additional_data={"workspace": workspace}
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM
            )
            errors.append(error_response.message)

            return ValidationResult(
                workspace_path=workspace,
                valid=False,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                validation_time_seconds=time.time() - start_time
            )

    def _initialize_components(self, config: Config):
        """Initialize all required components for indexing."""
        # Determine chunking strategy
        strategy_name = getattr(config, "chunking_strategy", "lines")
        if strategy_name == "treesitter":
            chunking_strategy_impl = TreeSitterChunkingStrategy(config)
        elif strategy_name == "tokens":
            chunking_strategy_impl = TokenChunkingStrategy(config)
        else:
            chunking_strategy_impl = LineChunkingStrategy(config)

        # Initialize components
        scanner = DirectoryScanner(config)
        parser = CodeParser(config, chunking_strategy_impl)
        embedder = OllamaEmbedder(config)
        vector_store = QdrantVectorStore(config)
        cache_manager = CacheManager(config.workspace_path, config)
        path_utils = PathUtils(self.error_handler, config.workspace_path)

        return scanner, parser, embedder, vector_store, cache_manager, path_utils

    def _get_file_paths(self, workspace: str, config: Config, path_utils: PathUtils) -> List[str]:
        """Get list of file paths to process."""
        # Scan directory to get set of valid files
        scanner = DirectoryScanner(config)
        scanned_paths, skipped_count = scanner.scan_directory()
        return scanned_paths

    def _process_files(self, file_paths: List[str], parser: CodeParser, embedder: OllamaEmbedder,
                      vector_store: QdrantVectorStore, cache_manager: CacheManager,
                      path_utils: PathUtils, config: Config, timed_out_files: List[str],
                      errors: List[str], warnings: List[str]) -> tuple[int, int]:
        """Process files and return (processed_count, total_blocks)."""
        processed_count = 0
        total_blocks = 0

        for file_path in file_paths:
            try:
                rel_path = path_utils.get_workspace_relative_path(file_path) or path_utils.normalize_path(file_path)

                # Check if file has changed
                current_hash = self.file_processor.get_file_hash(file_path)
                cached_hash = cache_manager.get_hash(file_path)
                if current_hash == cached_hash:
                    continue  # File hasn't changed, skip processing

                # Parse file into blocks
                blocks = parser.parse_file(file_path)
                if not blocks:
                    cache_manager.update_hash(file_path, current_hash)
                    continue

                # Generate embeddings
                texts = [block.content for block in blocks if block.content.strip()]
                if not texts:
                    cache_manager.update_hash(file_path, current_hash)
                    continue

                # Batch embeddings for efficiency
                batch_size = getattr(config, "batch_segment_threshold", 10)
                all_embeddings: List[List[float]] = []

                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    try:
                        embedding_response = embedder.create_embeddings(batch_texts)
                        all_embeddings.extend(embedding_response["embeddings"])
                    except Exception as e:
                        error_context = ErrorContext(
                            component="indexing_service",
                            operation="embed_batch",
                            file_path=rel_path
                        )
                        error_response = self.error_handler.handle_network_error(e, error_context, "Ollama")
                        warnings.append(f"Embedding failed for {rel_path}: {error_response.message}")
                        break

                if len(all_embeddings) < len(texts) and len(all_embeddings) == 0:
                    continue  # No embeddings generated

                # Prepare points for vector store
                points = []
                for i, block in enumerate(blocks):
                    if i >= len(all_embeddings):
                        break
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{file_path}:{block.start_line}:{block.end_line}"))
                    point = {
                        "id": point_id,
                        "vector": all_embeddings[i],
                        "payload": {
                            "filePath": rel_path,
                            "codeChunk": block.content,
                            "startLine": block.start_line,
                            "endLine": block.end_line,
                            "type": block.type,
                            "embedding_model": embedder.model_identifier
                        }
                    }
                    points.append(point)

                # Delete existing points for this file and upsert new ones
                try:
                    vector_store.delete_points_by_file_path(rel_path)
                except Exception:
                    pass  # Ignore errors if file wasn't previously indexed

                try:
                    vector_store.upsert_points(points)
                except Exception as e:
                    error_context = ErrorContext(
                        component="indexing_service",
                        operation="upsert_points",
                        file_path=rel_path
                    )
                    error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.DATABASE, ErrorSeverity.MEDIUM)
                    errors.append(f"Failed to store vectors for {rel_path}: {error_response.message}")
                    continue

                # Update cache
                cache_manager.update_hash(file_path, current_hash)

                processed_count += 1
                total_blocks += len(blocks)

            except Exception as e:
                error_context = ErrorContext(
                    component="indexing_service",
                    operation="process_file",
                    file_path=file_path
                )
                error_response = self.error_handler.handle_file_error(e, error_context, "file_processing")
                errors.append(f"Failed to process {file_path}: {error_response.message}")

        return processed_count, total_blocks

    def _detect_project_type(self, markers: List[str]) -> str:
        """Detect project type based on found markers."""
        if 'package.json' in markers:
            return 'nodejs'
        elif 'requirements.txt' in markers or 'pyproject.toml' in markers:
            return 'python'
        elif 'Cargo.toml' in markers:
            return 'rust'
        elif '.git' in markers:
            return 'git_repository'
        else:
            return 'unknown'