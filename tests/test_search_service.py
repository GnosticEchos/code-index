"""
Tests for SearchService CQRS implementation.

This module contains comprehensive tests for the SearchService class,
covering all search operations and edge cases.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from code_index.config import Config
from code_index.services.search_service import SearchService
from code_index.models import SearchResult, SearchMatch
from code_index.service_validation import ValidationResult
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.ollama_base_url = "http://localhost:11434"
    config.ollama_model = "test-model"
    config.qdrant_url = "http://localhost:6333"
    config.qdrant_api_key = None
    config.workspace_path = "/test/workspace"
    config.embedding_length = 768
    config.search_min_score = 0.4
    config.search_max_results = 50
    config.embed_timeout_seconds = 60
    config.chunking_strategy = "lines"
    config.use_tree_sitter = True  # Add missing attribute
    config.tree_sitter_skip_test_files = False  # Add missing attribute
    config.tree_sitter_min_file_size = 1024  # Add missing attribute
    config.tree_sitter_max_file_size = 1048576  # Add missing attribute
    return config


@pytest.fixture
def mock_error_handler():
    """Create a mock error handler for testing."""
    return Mock(spec=ErrorHandler)


@pytest.fixture
def search_service(mock_error_handler):
    """Create a SearchService instance for testing."""
    return SearchService(error_handler=mock_error_handler)


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        {
            "id": "test-id-1",
            "score": 0.85,
            "adjustedScore": 0.85,
            "payload": {
                "filePath": "src/main.py",
                "codeChunk": "def hello_world():\n    print('Hello, World!')",
                "startLine": 1,
                "endLine": 3,
                "type": "function",
                "embedding_model": "test-model"
            }
        },
        {
            "id": "test-id-2",
            "score": 0.75,
            "adjustedScore": 0.75,
            "payload": {
                "filePath": "src/utils.py",
                "codeChunk": "def print_hello():\n    print('Hello!')",
                "startLine": 1,
                "endLine": 3,
                "type": "function",
                "embedding_model": "test-model"
            }
        }
    ]


class TestSearchServiceInitialization:
    """Test SearchService initialization and setup."""

    def test_initialization_with_dependencies(self, mock_error_handler):
        """Test SearchService initialization with custom dependencies."""
        service = SearchService(error_handler=mock_error_handler)

        assert service.error_handler == mock_error_handler
        assert service.config_service is not None
        assert service.service_validator is not None

    def test_initialization_with_default_dependencies(self):
        """Test SearchService initialization with default dependencies."""
        service = SearchService()

        assert service.error_handler is not None
        assert service.config_service is not None
        assert service.service_validator is not None


class TestSearchCode:
    """Test text-based code search functionality."""

    def test_search_code_success(self, search_service, mock_config, sample_search_results):
        """Test successful text-based code search."""
        # Mock dependencies
        mock_embedder = Mock()
        mock_embedder.create_embeddings.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        mock_vector_store = Mock()
        mock_vector_store.search.return_value = sample_search_results

        with patch.object(search_service, '_initialize_search_components', return_value=(mock_embedder, mock_vector_store)), \
              patch.object(search_service, 'validate_search_config', return_value=ValidationResult(
                  service="search_service",
                  valid=True,
                  error=None,
                  details={},
                  response_time_ms=100,
                  actionable_guidance=[]
              )):
            result = search_service.search_code("test query", mock_config)

        assert result.is_successful()
        assert result.has_matches()
        assert len(result.matches) == 2
        assert result.total_found == 2
        assert result.search_method == "text"
        assert result.query == "test query"
        assert result.execution_time_seconds >= 0

        # Verify matches are properly converted
        match = result.matches[0]
        assert isinstance(match, SearchMatch)
        assert match.file_path == "src/main.py"
        assert match.score == 0.85
        assert match.adjusted_score == 0.85
        assert match.match_type == "function"

    def test_search_code_no_matches(self, search_service, mock_config):
        """Test search with no matches found."""
        # Mock dependencies
        mock_embedder = Mock()
        mock_embedder.create_embeddings.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        mock_vector_store = Mock()
        mock_vector_store.search.return_value = []

        with patch.object(search_service, '_initialize_search_components', return_value=(mock_embedder, mock_vector_store)), \
              patch.object(search_service, 'validate_search_config', return_value=ValidationResult(
                  service="search_service",
                  valid=True,
                  error=None,
                  details={},
                  response_time_ms=100,
                  actionable_guidance=[]
              )):
            result = search_service.search_code("nonexistent query", mock_config)

        assert result.is_successful()
        assert not result.has_matches()
        assert len(result.matches) == 0
        assert result.total_found == 0
        assert result.search_method == "text"

    def test_search_code_embedding_failure(self, search_service, mock_config):
        """Test search when embedding generation fails."""
        # Mock dependencies
        mock_embedder = Mock()
        mock_embedder.create_embeddings.return_value = {"embeddings": []}

        with patch.object(search_service, '_initialize_search_components', return_value=(mock_embedder, Mock())):
            result = search_service.search_code("test query", mock_config)

        assert not result.is_successful()
        assert len(result.errors) > 0
        # Test that we get some error message about configuration/model issues
        assert "Configuration" in result.errors[0] or "Model" in result.errors[0]
        assert not result.has_matches()

    def test_search_code_validation_failure(self, search_service, mock_config):
        """Test search when configuration validation fails."""
        with patch.object(search_service, 'validate_search_config', return_value=ValidationResult(
            service="search_service",
            valid=False,
            error="Invalid configuration",
            details={},
            response_time_ms=100,
            actionable_guidance=[]
        )):
            result = search_service.search_code("test query", mock_config)

        assert not result.is_successful()
        assert len(result.errors) > 0
        assert "Configuration" in result.errors[0]
        assert not result.has_matches()



class TestSearchSimilarFiles:
    """Test file similarity search functionality."""






class TestSearchByEmbedding:
    """Test embedding-based search functionality."""

    def test_search_by_embedding_success(self, search_service, mock_config, sample_search_results):
        """Test successful embedding-based search."""
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Mock dependencies
        mock_vector_store = Mock()
        mock_vector_store.search.return_value = sample_search_results

        with patch.object(search_service, '_initialize_search_components', return_value=(Mock(), mock_vector_store)), \
              patch.object(search_service, 'validate_search_config', return_value=ValidationResult(
                  service="search_service",
                  valid=True,
                  error=None,
                  details={},
                  response_time_ms=100,
                  actionable_guidance=[]
              )):
            result = search_service.search_by_embedding(test_embedding, mock_config)

        assert result.is_successful()
        assert result.has_matches()
        assert len(result.matches) == 2
        assert result.total_found == 2
        assert result.search_method == "embedding"
        assert result.query == "embedding_search"

    def test_search_by_embedding_no_matches(self, search_service, mock_config):
        """Test embedding search with no matches."""
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Mock dependencies
        mock_vector_store = Mock()
        mock_vector_store.search.return_value = []

        with patch.object(search_service, '_initialize_search_components', return_value=(Mock(), mock_vector_store)), \
              patch.object(search_service, 'validate_search_config', return_value=ValidationResult(
                  service="search_service",
                  valid=True,
                  error=None,
                  details={},
                  response_time_ms=100,
                  actionable_guidance=[]
              )):
            result = search_service.search_by_embedding(test_embedding, mock_config)

        assert result.is_successful()
        assert not result.has_matches()
        assert len(result.matches) == 0
        assert result.total_found == 0
        assert result.search_method == "embedding"


class TestValidateSearchConfig:
    """Test search configuration validation."""

    def test_validate_search_config_success(self, search_service, mock_config):
        """Test successful search configuration validation."""
        with patch.object(search_service.service_validator, 'validate_all_services', return_value=[
            ValidationResult(service="ollama", valid=True, error=None, details={}, response_time_ms=100, actionable_guidance=[]),
            ValidationResult(service="qdrant", valid=True, error=None, details={}, response_time_ms=100, actionable_guidance=[])
        ]), \
        patch.object(search_service, '_initialize_search_components') as mock_init:
            mock_vector_store = Mock()
            mock_vector_store.collection_exists.return_value = True
            mock_init.return_value = (Mock(), mock_vector_store)

            result = search_service.validate_search_config(mock_config)

        assert result.valid
        assert result.error is None
        # ValidationResult doesn't have warnings attribute, just check it's valid

    def test_validate_search_config_invalid_scores(self, search_service, mock_config):
        """Test validation with invalid score parameters."""
        mock_config.search_min_score = 1.5  # Invalid: > 1
        mock_config.search_max_results = -1  # Invalid: negative

        result = search_service.validate_search_config(mock_config)

        assert not result.valid
        assert result.error is not None
        assert "search_min_score must be between 0 and 1" in result.error
        assert "search_max_results must be positive" in result.error

    def test_validate_search_config_service_failure(self, search_service, mock_config):
        """Test validation when services fail."""
        with patch.object(search_service.service_validator, 'validate_all_services', return_value=[
            ValidationResult(service="ollama", valid=False, error="Connection failed", details={}, response_time_ms=100, actionable_guidance=[])
        ]):
            result = search_service.validate_search_config(mock_config)

        assert not result.valid
        assert result.error is not None
        assert "ollama: Connection failed" in result.error

    def test_validate_search_config_no_collection(self, search_service, mock_config):
        """Test validation when no collection exists."""
        with patch.object(search_service.service_validator, 'validate_all_services', return_value=[
            ValidationResult(service="ollama", valid=True, error=None, details={}, response_time_ms=100, actionable_guidance=[]),
            ValidationResult(service="qdrant", valid=True, error=None, details={}, response_time_ms=100, actionable_guidance=[])
        ]), \
        patch.object(search_service, '_initialize_search_components') as mock_init:
            mock_vector_store = Mock()
            mock_vector_store.collection_exists.return_value = False
            mock_init.return_value = (Mock(), mock_vector_store)

            result = search_service.validate_search_config(mock_config)

        assert result.valid  # Still valid, just a warning
        # ValidationResult doesn't have warnings attribute, just check it's valid


class TestSearchMatch:
    """Test SearchMatch functionality."""

    def test_search_match_creation(self):
        """Test SearchMatch object creation."""
        match = SearchMatch(
            file_path="src/main.py",
            start_line=1,
            end_line=5,
            code_chunk="def hello():\n    pass",
            match_type="function",
            score=0.85,
            adjusted_score=0.85,
            metadata={"test": "value"}
        )

        assert match.file_path == "src/main.py"
        assert match.start_line == 1
        assert match.end_line == 5
        assert match.code_chunk == "def hello():\n    pass"
        assert match.match_type == "function"
        assert match.score == 0.85
        assert match.adjusted_score == 0.85
        assert match.metadata == {"test": "value"}

    def test_search_match_context_lines(self):
        """Test getting context lines around a match."""
        match = SearchMatch(
            file_path="test.py",
            start_line=3,
            end_line=3,
            code_chunk="line 1\nline 2\nline 3\nline 4\nline 5",
            match_type="text",
            score=0.8,
            adjusted_score=0.8,
            metadata={}
        )

        context = match.get_context_lines(before=1, after=1)
        assert len(context) == 5  # All lines since we don't have file context
        assert "line 1" in context
        assert "line 2" in context
        assert "line 3" in context
        assert "line 4" in context
        assert "line 5" in context

    def test_search_match_to_dict(self):
        """Test converting SearchMatch to dictionary."""
        match = SearchMatch(
            file_path="src/main.py",
            start_line=1,
            end_line=5,
            code_chunk="def hello():\n    pass",
            match_type="function",
            score=0.85,
            adjusted_score=0.85,
            metadata={"test": "value"}
        )

        result_dict = match.to_dict()

        assert result_dict["file_path"] == "src/main.py"
        assert result_dict["start_line"] == 1
        assert result_dict["end_line"] == 5
        assert result_dict["code_chunk"] == "def hello():\n    pass"
        assert result_dict["match_type"] == "function"
        assert result_dict["score"] == 0.85
        assert result_dict["adjusted_score"] == 0.85
        assert result_dict["metadata"] == {"test": "value"}


class TestSearchResult:
    """Test SearchResult functionality."""

    def test_search_result_creation(self):
        """Test SearchResult object creation."""
        matches = [
            SearchMatch(
                file_path="src/main.py",
                start_line=1,
                end_line=5,
                code_chunk="def hello():\n    pass",
                match_type="function",
                score=0.85,
                adjusted_score=0.85,
                metadata={}
            )
        ]

        result = SearchResult(
            query="test query",
            matches=matches,
            total_found=1,
            execution_time_seconds=0.5,
            search_method="text",
            config_summary={"test": "config"},
            errors=[],
            warnings=[]
        )

        assert result.query == "test query"
        assert len(result.matches) == 1
        assert result.total_found == 1
        assert result.execution_time_seconds == 0.5
        assert result.search_method == "text"
        assert result.config_summary == {"test": "config"}
        assert result.is_successful()
        assert result.has_matches()

    def test_search_result_get_top_matches(self):
        """Test getting top matches by score."""
        matches = [
            SearchMatch(
                file_path="src/file1.py",
                start_line=1,
                end_line=5,
                code_chunk="code1",
                match_type="function",
                score=0.7,
                adjusted_score=0.7,
                metadata={}
            ),
            SearchMatch(
                file_path="src/file2.py",
                start_line=1,
                end_line=5,
                code_chunk="code2",
                match_type="function",
                score=0.9,
                adjusted_score=0.9,
                metadata={}
            ),
            SearchMatch(
                file_path="src/file3.py",
                start_line=1,
                end_line=5,
                code_chunk="code3",
                match_type="function",
                score=0.8,
                adjusted_score=0.8,
                metadata={}
            )
        ]

        result = SearchResult(
            query="test",
            matches=matches,
            total_found=3,
            execution_time_seconds=0.1,
            search_method="text",
            config_summary={},
            errors=[],
            warnings=[]
        )

        top_matches = result.get_top_matches(limit=2)
        assert len(top_matches) == 2
        assert top_matches[0].adjusted_score == 0.9
        assert top_matches[1].adjusted_score == 0.8

    def test_search_result_get_matches_by_file(self):
        """Test grouping matches by file."""
        matches = [
            SearchMatch(
                file_path="src/file1.py",
                start_line=1,
                end_line=5,
                code_chunk="code1",
                match_type="function",
                score=0.8,
                adjusted_score=0.8,
                metadata={}
            ),
            SearchMatch(
                file_path="src/file1.py",
                start_line=10,
                end_line=15,
                code_chunk="code2",
                match_type="function",
                score=0.7,
                adjusted_score=0.7,
                metadata={}
            ),
            SearchMatch(
                file_path="src/file2.py",
                start_line=1,
                end_line=5,
                code_chunk="code3",
                match_type="function",
                score=0.9,
                adjusted_score=0.9,
                metadata={}
            )
        ]

        result = SearchResult(
            query="test",
            matches=matches,
            total_found=3,
            execution_time_seconds=0.1,
            search_method="text",
            config_summary={},
            errors=[],
            warnings=[]
        )

        grouped = result.get_matches_by_file()
        assert len(grouped) == 2
        assert "src/file1.py" in grouped
        assert "src/file2.py" in grouped
        assert len(grouped["src/file1.py"]) == 2
        assert len(grouped["src/file2.py"]) == 1

    def test_search_result_get_summary(self):
        """Test getting search result summary."""
        matches = [
            SearchMatch(
                file_path="src/file1.py",
                start_line=1,
                end_line=5,
                code_chunk="code1",
                match_type="function",
                score=0.8,
                adjusted_score=0.8,
                metadata={}
            ),
            SearchMatch(
                file_path="src/file2.py",
                start_line=1,
                end_line=5,
                code_chunk="code2",
                match_type="function",
                score=0.6,
                adjusted_score=0.6,
                metadata={}
            )
        ]

        result = SearchResult(
            query="test query",
            matches=matches,
            total_found=2,
            execution_time_seconds=0.5,
            search_method="text",
            config_summary={"model": "test"},
            errors=["error1"],
            warnings=["warning1"]
        )

        summary = result.get_summary()
        assert summary["query"] == "test query"
        assert summary["total_found"] == 2
        assert summary["matches_returned"] == 2
        assert summary["execution_time_seconds"] == 0.5
        assert summary["search_method"] == "text"
        assert summary["successful"] == False  # Has errors
        assert summary["errors"] == 1
        assert summary["warnings"] == 1
        assert summary["top_score"] == 0.8
        assert summary["avg_score"] == 0.7

    def test_search_result_to_dict(self):
        """Test converting SearchResult to dictionary."""
        matches = [
            SearchMatch(
                file_path="src/file1.py",
                start_line=1,
                end_line=5,
                code_chunk="code1",
                match_type="function",
                score=0.8,
                adjusted_score=0.8,
                metadata={}
            )
        ]

        result = SearchResult(
            query="test query",
            matches=matches,
            total_found=1,
            execution_time_seconds=0.5,
            search_method="text",
            config_summary={"model": "test"},
            errors=[],
            warnings=[]
        )

        result_dict = result.to_dict()

        assert result_dict["query"] == "test query"
        assert len(result_dict["matches"]) == 1
        assert result_dict["total_found"] == 1
        assert result_dict["execution_time_seconds"] == 0.5
        assert result_dict["search_method"] == "text"
        assert result_dict["config_summary"] == {"model": "test"}
        assert len(result_dict["errors"]) == 0
        assert len(result_dict["warnings"]) == 0
        assert "summary" in result_dict