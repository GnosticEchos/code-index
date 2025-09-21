"""
Tests for IndexingService CQRS implementation.

This module tests the IndexingService and related result types to ensure
proper separation of command operations from CLI concerns.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from code_index.config import Config
from code_index.services.indexing_service import IndexingService
from code_index.models import IndexingResult, ProcessingResult, ValidationResult
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


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

    def test_service_initialization(self, error_handler):
        """Test IndexingService initialization."""
        service = IndexingService(error_handler)

        assert service.error_handler == error_handler
        assert service.config_service is not None
        assert service.file_processor is not None
        assert service.service_validator is not None

    @patch('code_index.services.indexing_service.PathUtils')
    @patch('code_index.services.indexing_service.CacheManager')
    @patch('code_index.services.indexing_service.QdrantVectorStore')
    @patch('code_index.services.indexing_service.OllamaEmbedder')
    @patch('code_index.services.indexing_service.CodeParser')
    @patch('code_index.services.indexing_service.DirectoryScanner')
    def test_initialize_components(self, mock_scanner, mock_parser, mock_embedder, mock_vector_store, mock_cache_manager, mock_path_utils, indexing_service, sample_config):
        """Test component initialization."""
        mock_scanner = Mock()
        mock_parser = Mock()
        mock_embedder = Mock()
        mock_vector_store = Mock()
        mock_cache_manager = Mock()
        mock_path_utils = Mock()

        with patch('code_index.services.indexing_service.DirectoryScanner', return_value=mock_scanner), \
             patch('code_index.services.indexing_service.CodeParser', return_value=mock_parser), \
             patch('code_index.services.indexing_service.OllamaEmbedder', return_value=mock_embedder), \
             patch('code_index.services.indexing_service.QdrantVectorStore', return_value=mock_vector_store), \
             patch('code_index.services.indexing_service.CacheManager', return_value=mock_cache_manager), \
             patch('code_index.services.indexing_service.PathUtils', return_value=mock_path_utils):

            scanner, parser, embedder, vector_store, cache_manager, path_utils = \
                indexing_service._initialize_components(sample_config)

            assert scanner == mock_scanner
            assert parser == mock_parser
            assert embedder == mock_embedder
            assert vector_store == mock_vector_store
            assert cache_manager == mock_cache_manager
            assert path_utils == mock_path_utils

    def test_detect_project_type(self, indexing_service):
        """Test project type detection."""
        # Test Node.js project
        nodejs_markers = ['package.json']
        assert indexing_service._detect_project_type(nodejs_markers) == 'nodejs'

        # Test Python project
        python_markers = ['requirements.txt']
        assert indexing_service._detect_project_type(python_markers) == 'python'

        # Test Rust project
        rust_markers = ['Cargo.toml']
        assert indexing_service._detect_project_type(rust_markers) == 'rust'

        # Test Git repository
        git_markers = ['.git']
        assert indexing_service._detect_project_type(git_markers) == 'git_repository'

        # Test unknown project
        unknown_markers = ['unknown.txt']
        assert indexing_service._detect_project_type(unknown_markers) == 'unknown'

    @patch('code_index.services.indexing_service.ServiceValidator')
    def test_validate_workspace_success(self, mock_validator, indexing_service, sample_config):
        """Test successful workspace validation."""
        # Mock service validator
        mock_validator = Mock()
        mock_validator.validate_all_services.return_value = [
            Mock(service="ollama", valid=True, error=None, details={}),
            Mock(service="qdrant", valid=True, error=None, details={})
        ]
        indexing_service.service_validator = mock_validator

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_config.workspace_path = temp_dir

            result = indexing_service.validate_workspace(temp_dir, sample_config)

            assert result.is_valid() is True
            assert len(result.errors) == 0
            assert result.workspace_path == temp_dir
            assert result.validation_time_seconds >= 0

    @patch('code_index.services.indexing_service.ServiceValidator')
    def test_validate_workspace_failure(self, mock_validator, indexing_service, sample_config):
        """Test failed workspace validation."""
        # Mock service validator to return failures
        mock_validator = Mock()
        mock_validator.validate_all_services.return_value = [
            Mock(service="ollama", valid=False, error="Connection failed", details={}),
            Mock(service="qdrant", valid=True, error=None, details={})
        ]
        indexing_service.service_validator = mock_validator

        # Create a temporary file (not directory) to test validation failure
        with tempfile.NamedTemporaryFile() as temp_file:
            result = indexing_service.validate_workspace(temp_file.name, sample_config)

            assert result.is_valid() is False
            assert len(result.errors) > 0
            assert "not a directory" in result.errors[0]

    def test_process_files_empty_list(self, indexing_service, sample_config):
        """Test processing empty file list."""
        results = indexing_service.process_files([], sample_config)

        assert results == []

    @patch('code_index.services.indexing_service.PathUtils')
    @patch('code_index.services.indexing_service.QdrantVectorStore')
    @patch('code_index.services.indexing_service.OllamaEmbedder')
    @patch('code_index.services.indexing_service.CodeParser')
    def test_process_files_success(self, mock_parser, mock_embedder, mock_vector_store, mock_path_utils, indexing_service, sample_config):
        """Test successful file processing."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('print("Hello, World!")')
            temp_file_path = f.name

        try:
            # Mock components
            mock_parser = Mock()
            mock_parser.parse_file.return_value = [
                Mock(content='print("Hello, World!")', start_line=1, end_line=1, type="function")
            ]

            mock_embedder = Mock()
            mock_embedder.create_embeddings.return_value = {
                "embeddings": [[0.1, 0.2, 0.3]],
                "model": "test-model"
            }

            mock_vector_store = Mock()
            mock_path_utils = Mock()
            mock_path_utils.get_workspace_relative_path.return_value = "test.py"

            with patch('code_index.services.indexing_service.CodeParser', return_value=mock_parser), \
                 patch('code_index.services.indexing_service.OllamaEmbedder', return_value=mock_embedder), \
                 patch('code_index.services.indexing_service.QdrantVectorStore', return_value=mock_vector_store), \
                 patch('code_index.services.indexing_service.PathUtils', return_value=mock_path_utils):

                results = indexing_service.process_files([temp_file_path], sample_config)

                assert len(results) == 1
                assert results[0].is_successful() is True
                assert results[0].blocks_processed == 1
                assert results[0].file_path == temp_file_path

        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

    @patch('code_index.services.indexing_service.IndexingService._process_files')
    @patch('code_index.services.indexing_service.IndexingService._get_file_paths')
    @patch('code_index.services.indexing_service.IndexingService._initialize_components')
    @patch('code_index.services.indexing_service.IndexingService.validate_workspace')
    def test_index_workspace_integration(self, mock_validate, mock_initialize, mock_get_files, mock_process_files, indexing_service, sample_config):
        """Test full workspace indexing integration."""
        # Mock workspace validation to pass
        mock_validate.return_value = ValidationResult(
            workspace_path="/test/workspace",
            valid=True,
            errors=[],
            warnings=[],
            metadata={},
            validation_time_seconds=0.1
        )

        # Mock all internal methods
        mock_components = (Mock(), Mock(), Mock(), Mock(), Mock(), Mock())
        mock_initialize.return_value = mock_components

        mock_get_files.return_value = ["/test/file1.py", "/test/file2.py"]

        mock_process_files.return_value = (2, 10)

        result = indexing_service.index_workspace("/test/workspace", sample_config)

        assert result.processed_files == 2
        assert result.total_blocks == 10
        assert result.workspace_path == "/test/workspace"
        assert result.processing_time_seconds >= 0

    def test_index_workspace_error_handling(self, indexing_service, sample_config):
        """Test error handling in workspace indexing."""
        # Test with invalid workspace path
        result = indexing_service.index_workspace("/nonexistent/path", sample_config)

        assert result.processed_files == 0
        assert result.total_blocks == 0
        assert len(result.errors) > 0
        assert result.workspace_path == "/nonexistent/path"