"""
Tests for IndexingService CQRS implementation.

This module tests the IndexingService and related result types to ensure
proper separation of command operations from CLI concerns.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

from code_index.config import Config
from code_index.services import IndexingService
from code_index.services import _create_test_dependencies
from code_index.models import IndexingResult, ProcessingResult, ValidationResult
from code_index.errors import ErrorHandler


@pytest.fixture
def error_handler():
    """Provide ErrorHandler instance for testing."""
    return ErrorHandler()


@pytest.fixture
def sample_config():
    """Provide sample configuration for testing."""
    config = Config()
    config.workspace_path = "/test/workspace"
    config.ollama_base_url = "http://localhost:11434"
    config.ollama_model = "test-model"
    config.qdrant_url = "http://localhost:6333"
    config.embedding_length = 384
    config.chunking_strategy = "lines"
    config.use_tree_sitter = False
    config.embed_timeout_seconds = 30
    config.search_min_score = 0.1
    config.search_max_results = 10
    config.max_file_size_bytes = 1024 * 1024  # 1MB
    return config


@pytest.fixture
def indexing_service(error_handler):
    """Provide IndexingService instance for testing."""
    return IndexingService(error_handler)


@pytest.fixture
def mock_dependencies(error_handler):
    """Provide mock dependencies for testing."""
    return _create_test_dependencies(error_handler=error_handler)


class TestIndexingResult:
    """Test IndexingResult data model."""

    def test_indexing_result_creation(self):
        """Test creating IndexingResult with all fields."""
        result = IndexingResult(
            processed_files=10,
            total_blocks=50,
            errors=["error1", "error2"],
            warnings=["warning1"],
            timed_out_files=["file1.py"],
            processing_time_seconds=15.5,
            timestamp=datetime.now(),
            workspace_path="/test/workspace",
            config_summary={"test": "value"}
        )

        assert result.processed_files == 10
        assert result.total_blocks == 50
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.timed_out_files) == 1
        assert result.processing_time_seconds == 15.5
        assert result.workspace_path == "/test/workspace"
        assert result.config_summary == {"test": "value"}

    def test_indexing_result_post_init(self):
        """Test IndexingResult timestamp initialization."""
        result = IndexingResult(
            processed_files=5,
            total_blocks=25,
            errors=[],
            warnings=[],
            timed_out_files=[],
            processing_time_seconds=10.0,
            timestamp=None,  # Should be auto-initialized
            workspace_path="/test",
            config_summary={}
        )

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    def test_is_successful(self):
        """Test successful indexing detection."""
        # Successful result
        success_result = IndexingResult(
            processed_files=10,
            total_blocks=50,
            errors=[],
            warnings=[],
            timed_out_files=[],
            processing_time_seconds=10.0,
            timestamp=datetime.now(),
            workspace_path="/test",
            config_summary={}
        )
        assert success_result.is_successful() is True

        # Failed result
        failed_result = IndexingResult(
            processed_files=5,
            total_blocks=25,
            errors=["error1"],
            warnings=[],
            timed_out_files=[],
            processing_time_seconds=10.0,
            timestamp=datetime.now(),
            workspace_path="/test",
            config_summary={}
        )
        assert failed_result.is_successful() is False

    def test_has_warnings(self):
        """Test warning detection."""
        # Result with warnings
        result_with_warnings = IndexingResult(
            processed_files=10,
            total_blocks=50,
            errors=[],
            warnings=["warning1", "warning2"],
            timed_out_files=[],
            processing_time_seconds=10.0,
            timestamp=datetime.now(),
            workspace_path="/test",
            config_summary={}
        )
        assert result_with_warnings.has_warnings() is True

        # Result without warnings
        result_without_warnings = IndexingResult(
            processed_files=10,
            total_blocks=50,
            errors=[],
            warnings=[],
            timed_out_files=[],
            processing_time_seconds=10.0,
            timestamp=datetime.now(),
            workspace_path="/test",
            config_summary={}
        )
        assert result_without_warnings.has_warnings() is False

    def test_get_summary(self):
        """Test summary generation."""
        result = IndexingResult(
            processed_files=10,
            total_blocks=50,
            errors=["error1"],
            warnings=["warning1"],
            timed_out_files=["file1.py"],
            processing_time_seconds=15.5,
            timestamp=datetime.now(),
            workspace_path="/test",
            config_summary={"test": "value"}
        )

        summary = result.get_summary()

        assert summary["processed_files"] == 10
        assert summary["total_blocks"] == 50
        assert summary["errors"] == 1
        assert summary["warnings"] == 1
        assert summary["timed_out_files"] == 1
        assert summary["processing_time_seconds"] == 15.5
        assert summary["successful"] is False
        assert "timestamp" in summary


class TestProcessingResult:
    """Test ProcessingResult data model."""

    def test_processing_result_creation(self):
        """Test creating ProcessingResult with all fields."""
        result = ProcessingResult(
            file_path="/test/file.py",
            success=True,
            blocks_processed=5,
            error=None,
            processing_time_seconds=2.5,
            metadata={"test": "value"}
        )

        assert result.file_path == "/test/file.py"
        assert result.success is True
        assert result.blocks_processed == 5
        assert result.error is None
        assert result.processing_time_seconds == 2.5
        assert result.metadata == {"test": "value"}

    def test_processing_result_post_init(self):
        """Test ProcessingResult metadata initialization."""
        result = ProcessingResult(
            file_path="/test/file.py",
            success=False,
            blocks_processed=0,
            error="Test error"
        )

        assert result.metadata == {}

    def test_is_successful(self):
        """Test successful processing detection."""
        success_result = ProcessingResult(
            file_path="/test/file.py",
            success=True,
            blocks_processed=5
        )
        assert success_result.is_successful() is True

        failed_result = ProcessingResult(
            file_path="/test/file.py",
            success=False,
            blocks_processed=0,
            error="Test error"
        )
        assert failed_result.is_successful() is False

    def test_has_error(self):
        """Test error detection."""
        result_with_error = ProcessingResult(
            file_path="/test/file.py",
            success=False,
            blocks_processed=0,
            error="Test error"
        )
        assert result_with_error.has_error() is True

        result_without_error = ProcessingResult(
            file_path="/test/file.py",
            success=True,
            blocks_processed=5
        )
        assert result_without_error.has_error() is False


class TestValidationResult:
    """Test ValidationResult data model."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult with all fields."""
        result = ValidationResult(
            workspace_path="/test/workspace",
            valid=True,
            errors=[],
            warnings=["warning1"],
            metadata={"test": "value"},
            validation_time_seconds=1.5
        )

        assert result.workspace_path == "/test/workspace"
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == ["warning1"]
        assert result.metadata == {"test": "value"}
        assert result.validation_time_seconds == 1.5

    def test_validation_result_post_init(self):
        """Test ValidationResult metadata initialization."""
        result = ValidationResult(
            workspace_path="/test/workspace",
            valid=False,
            errors=["error1"],
            warnings=[],
            metadata=None,  # Should be auto-initialized
            validation_time_seconds=1.0
        )

        assert result.metadata == {}

    def test_is_valid(self):
        """Test validation status detection."""
        valid_result = ValidationResult(
            workspace_path="/test/workspace",
            valid=True,
            errors=[],
            warnings=[],
            metadata={},
            validation_time_seconds=1.0
        )
        assert valid_result.is_valid() is True

        invalid_result = ValidationResult(
            workspace_path="/test/workspace",
            valid=False,
            errors=["error1"],
            warnings=[],
            metadata={},
            validation_time_seconds=1.0
        )
        assert invalid_result.is_valid() is False

    def test_has_issues(self):
        """Test issue detection."""
        result_with_issues = ValidationResult(
            workspace_path="/test/workspace",
            valid=False,
            errors=["error1"],
            warnings=["warning1"],
            metadata={},
            validation_time_seconds=1.0
        )
        assert result_with_issues.has_issues() is True

        result_without_issues = ValidationResult(
            workspace_path="/test/workspace",
            valid=True,
            errors=[],
            warnings=[],
            metadata={},
            validation_time_seconds=1.0
        )
        assert result_without_issues.has_issues() is False

    def test_get_summary(self):
        """Test summary generation."""
        result = ValidationResult(
            workspace_path="/test/workspace",
            valid=False,
            errors=["error1", "error2"],
            warnings=["warning1"],
            metadata={"test": "value"},
            validation_time_seconds=2.5
        )

        summary = result.get_summary()

        assert summary["workspace_path"] == "/test/workspace"
        assert summary["valid"] is False
        assert summary["errors"] == 2
        assert summary["warnings"] == 1
        assert summary["validation_time_seconds"] == 2.5


class TestIndexingService:
    """Test IndexingService functionality."""

    def test_service_initialization_with_dependencies(self, error_handler, mock_dependencies):
        """Test IndexingService initialization with dependency injection."""
        service = IndexingService(error_handler, dependencies=mock_dependencies)

        assert service.error_handler == error_handler
        assert service.config_service is not None
        assert service.service_validator is not None
        assert service._dependencies is not None

    def test_service_initialization_without_dependencies(self, error_handler):
        """Test IndexingService initialization without dependencies."""
        service = IndexingService(error_handler)

        assert service.error_handler == error_handler
        assert service.config_service is not None
        assert service.service_validator is not None

    def test_orchestrator_property_lazy_initialization(self, error_handler, mock_dependencies):
        """Test that orchestrator is lazily initialized."""
        service = IndexingService(error_handler, dependencies=mock_dependencies)

        # Orchestrator should be None initially
        assert service._orchestrator is None

        # Accessing orchestrator property should create it
        orchestrator = service.orchestrator
        assert orchestrator is not None
        assert service._orchestrator is not None

    def test_file_processor_property_lazy_initialization(self, error_handler, mock_dependencies):
        """Test that file_processor is lazily initialized."""
        service = IndexingService(error_handler, dependencies=mock_dependencies)

        # File processor should be None initially
        assert service._file_processor is None

        # Accessing file_processor property should create it
        processor = service.file_processor
        assert processor is not None
        assert service._file_processor is not None

    def test_batch_manager_property_lazy_initialization(self, error_handler, mock_dependencies):
        """Test that batch_manager is lazily initialized."""
        service = IndexingService(error_handler, dependencies=mock_dependencies)

        # Batch manager should be None initially
        assert service._batch_manager is None

        # Accessing batch_manager property should create it
        manager = service.batch_manager
        assert manager is not None
        assert service._batch_manager is not None

    def test_validate_workspace_delegates_to_orchestrator(self, error_handler, sample_config):
        """Test that validate_workspace delegates to orchestrator."""
        service = IndexingService(error_handler)

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_config.workspace_path = temp_dir

            # Mock the orchestrator's validate_workspace method
            expected_result = ValidationResult(
                workspace_path=temp_dir,
                valid=True,
                errors=[],
                warnings=[],
                metadata={},
                validation_time_seconds=0.1
            )

            with patch.object(service.orchestrator, 'validate_workspace', return_value=expected_result):
                result = service.validate_workspace(temp_dir, sample_config)

                assert result.is_valid() is True
                assert result.workspace_path == temp_dir

    def test_index_workspace_delegates_to_orchestrator(self, error_handler, sample_config):
        """Test that index_workspace delegates to orchestrator."""
        service = IndexingService(error_handler)

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_config.workspace_path = temp_dir

            # Mock the orchestrator's index_workspace method
            expected_result = IndexingResult(
                processed_files=5,
                total_blocks=25,
                errors=[],
                warnings=[],
                timed_out_files=[],
                processing_time_seconds=1.0,
                timestamp=datetime.now(),
                workspace_path=temp_dir,
                config_summary={}
            )

            with patch.object(service.orchestrator, 'index_workspace', return_value=expected_result):
                result = service.index_workspace(temp_dir, sample_config)

                assert result.processed_files == 5
                assert result.total_blocks == 25
                assert result.workspace_path == temp_dir

    def test_process_files_empty_list(self, error_handler, sample_config):
        """Test processing empty file list."""
        service = IndexingService(error_handler)
        results = service.process_files([], sample_config)

        assert results == []

    def test_process_files_with_mock_dependencies(self, error_handler, sample_config):
        """Test process_files with mocked dependencies."""
        # Create test dependencies with mocks
        mock_parser = Mock()
        mock_embedder = Mock()
        mock_vector_store = Mock()
        mock_cache_manager = Mock()
        mock_path_utils = Mock()

        mock_embedder.create_embeddings.return_value = {
            "embeddings": [[0.1, 0.2, 0.3]],
            "model": "test-model"
        }
        mock_path_utils.get_workspace_relative_path.return_value = "test.py"

        deps = _create_test_dependencies(
            error_handler=error_handler,
            mock_parser=mock_parser,
            mock_embedder=mock_embedder,
            mock_vector_store=mock_vector_store,
            mock_cache_manager=mock_cache_manager,
            mock_path_utils=mock_path_utils
        )

        service = IndexingService(error_handler, dependencies=deps)

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('print("Hello, World!")')
            temp_file_path = f.name

        try:
            # Mock the orchestrator's initialize_components to return our mocks
            with patch.object(service.orchestrator, 'initialize_components', return_value=(
                mock_parser, mock_embedder, mock_vector_store, mock_cache_manager, mock_path_utils
            )):
                results = service.process_files([temp_file_path], sample_config)

                # Results should be a list of ProcessingResult objects
                assert isinstance(results, list)
                assert len(results) == 1

        finally:
            os.unlink(temp_file_path)

    def test_index_workspace_error_handling(self, error_handler, sample_config):
        """Test error handling in workspace indexing."""
        service = IndexingService(error_handler)

        # Test with invalid workspace path - should return result with errors
        result = service.index_workspace("/nonexistent/path/that/does/not/exist", sample_config)

        assert result.processed_files == 0
        assert result.total_blocks == 0
        assert len(result.errors) > 0
        assert result.workspace_path == "/nonexistent/path/that/does/not/exist"

    def test_dependencies_property_creates_default_when_none(self, error_handler):
        """Test that dependencies property creates default when None."""
        service = IndexingService(error_handler)
        service._dependencies = None

        deps = service.dependencies
        assert deps is not None
        assert deps.error_handler == error_handler

    def test_dependencies_setter_resets_lazy_services(self, error_handler, mock_dependencies):
        """Test that setting dependencies resets lazy services."""
        service = IndexingService(error_handler)

        # Initialize lazy services
        _ = service.orchestrator
        _ = service.file_processor
        _ = service.batch_manager

        # Set new dependencies
        new_deps = _create_test_dependencies(error_handler=error_handler)
        service.dependencies = new_deps

        # Lazy services should be reset
        assert service._orchestrator is None
        assert service._file_processor is None
        assert service._batch_manager is None
        assert service._dependencies == new_deps