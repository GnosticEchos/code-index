"""
Tests for ConfigurationService class.

This module contains comprehensive tests for the ConfigurationService class,
including tests for configuration loading, validation, CLI overrides,
workspace-specific configuration, and type-safe configuration access.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from code_index.config import Config
from code_index.config_service import ConfigurationService, ConfigurationSource
from code_index.service_validation import ValidationResult
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class TestConfigurationService:
    """Test suite for ConfigurationService class."""

    @pytest.fixture
    def config_service(self):
        """Create a ConfigurationService instance for testing."""
        return ConfigurationService(test_mode=True)

    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        config = Config()
        config.workspace_path = "/test/workspace"
        config.ollama_base_url = "http://localhost:11434"
        config.ollama_model = "test-model"
        config.qdrant_url = "http://localhost:6333"
        config.embedding_length = 768
        config.chunking_strategy = "lines"
        config.use_tree_sitter = False
        config.embed_timeout_seconds = 60
        config.search_min_score = 0.4
        config.search_max_results = 50
        return config

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file for testing."""
        config_data = {
            "ollama_base_url": "http://test:11434",
            "ollama_model": "test-model:latest",
            "qdrant_url": "http://test:6333",
            "embedding_length": 1024,
            "chunking_strategy": "tokens",
            "use_tree_sitter": True,
            "embed_timeout_seconds": 120,
            "search_min_score": 0.3,
            "search_max_results": 100
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)

    @pytest.fixture
    def temp_workspace_config(self):
        """Create a temporary workspace-specific configuration file."""
        config_data = {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True,
            "tree_sitter_max_blocks_per_file": 50
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, ".code_index.json")
            with open(config_path, 'w') as f:
                json.dump(config_data, f)

            yield temp_dir, config_path

    def test_configuration_service_initialization(self, config_service):
        """Test ConfigurationService initialization."""
        assert config_service is not None
        assert config_service.logger is not None
        assert config_service.error_handler is not None
        assert len(config_service._config_cache) == 0
        assert len(config_service._validation_cache) == 0

        sources = config_service.get_configuration_sources()
        assert len(sources) == 5
        assert all(isinstance(source, ConfigurationSource) for source in sources)

        # Check source priorities
        priorities = [source.priority for source in sources]
        assert priorities == [100, 90, 80, 70, 10]  # CLI, workspace, env, file, default

    def test_load_with_fallback_no_config_file(self, config_service):
        """Test loading configuration when no config file exists."""
        config = config_service.load_with_fallback(
            config_path="nonexistent.json",
            workspace_path="/test/workspace"
        )

        assert isinstance(config, Config)
        assert config.workspace_path == "/test/workspace"
        assert config.ollama_base_url == "http://localhost:11434"  # Default
        assert config.ollama_model == "nomic-embed-text:latest"  # Default

    def test_load_with_fallback_with_config_file(self, config_service, temp_config_file):
        """Test loading configuration from existing config file."""
        config = config_service.load_with_fallback(
            config_path=temp_config_file,
            workspace_path="/test/workspace"
        )

        assert isinstance(config, Config)
        assert config.workspace_path == "/test/workspace"
        assert config.ollama_base_url == "http://test:11434"
        assert config.ollama_model == "test-model:latest"
        assert config.qdrant_url == "http://test:6333"
        assert config.embedding_length == 1024
        assert config.chunking_strategy == "tokens"
        assert config.use_tree_sitter is True
        assert config.embed_timeout_seconds == 120
        assert config.search_min_score == 0.3
        assert config.search_max_results == 100

    def test_load_with_fallback_with_environment_overrides(self, config_service):
        """Test loading configuration with environment variable overrides."""
        with patch.dict(os.environ, {
            'OLLAMA_BASE_URL': 'http://env:11434',
            'OLLAMA_MODEL': 'env-model',
            'QDRANT_URL': 'http://env:6333',
            'CODE_INDEX_EMBED_TIMEOUT': '90',
            'CODE_INDEX_USE_TREE_SITTER': 'true'
        }):
            config = config_service.load_with_fallback(
                config_path="nonexistent.json",
                workspace_path="/test/workspace"
            )

            assert config.ollama_base_url == "http://env:11434"
            assert config.ollama_model == "env-model"
            assert config.qdrant_url == "http://env:6333"
            assert config.embed_timeout_seconds == 90
            assert config.use_tree_sitter is True

    def test_load_with_fallback_with_workspace_config(self, config_service, temp_workspace_config):
        """Test loading configuration with workspace-specific config."""
        temp_dir, config_path = temp_workspace_config

        config = config_service.load_with_fallback(
            config_path="nonexistent.json",
            workspace_path=temp_dir
        )

        assert isinstance(config, Config)
        assert config.workspace_path == temp_dir
        assert config.chunking_strategy == "treesitter"
        assert config.use_tree_sitter is True
        assert config.tree_sitter_max_blocks_per_file == 50

    def test_load_with_fallback_with_cli_overrides(self, config_service):
        """Test loading configuration with CLI overrides."""
        overrides = {
            'chunking_strategy': 'treesitter',
            'use_tree_sitter': True,
            'embed_timeout_seconds': 180,
            'search_min_score': 0.5
        }

        config = config_service.load_with_fallback(
            config_path="nonexistent.json",
            workspace_path="/test/workspace",
            overrides=overrides
        )

        assert config.chunking_strategy == "treesitter"
        assert config.use_tree_sitter is True
        assert config.embed_timeout_seconds == 180
        assert config.search_min_score == 0.5

    def test_apply_cli_overrides(self, config_service, sample_config):
        """Test applying CLI overrides to configuration."""
        overrides = {
            'chunking_strategy': 'treesitter',
            'use_tree_sitter': True,
            'embed_timeout_seconds': 180,
            'search_min_score': 0.5
        }

        updated_config = config_service.apply_cli_overrides(sample_config, overrides)

        assert updated_config.chunking_strategy == "treesitter"
        assert updated_config.use_tree_sitter is True
        assert updated_config.embed_timeout_seconds == 180
        assert updated_config.search_min_score == 0.5

        # Original config should be unchanged
        assert sample_config.chunking_strategy == "lines"
        assert sample_config.use_tree_sitter is False
        assert sample_config.embed_timeout_seconds == 60
        assert sample_config.search_min_score == 0.4

    def test_apply_cli_overrides_invalid_parameter(self, config_service, sample_config):
        """Test applying CLI overrides with invalid parameters."""
        overrides = {
            'invalid_parameter': 'invalid_value',
            'chunking_strategy': 'treesitter',
            'use_tree_sitter': True  # Fix the validation error
        }

        updated_config = config_service.apply_cli_overrides(sample_config, overrides)

        # Verify the valid overrides were applied
        assert updated_config.chunking_strategy == 'treesitter'
        assert updated_config.use_tree_sitter is True

        # Valid override should be applied
        assert updated_config.chunking_strategy == "treesitter"

        # Invalid parameter should be ignored
        assert not hasattr(updated_config, 'invalid_parameter')

    def test_validate_and_initialize_valid_config(self, config_service, sample_config):
        """Test validation and initialization with valid configuration."""
        result = config_service.validate_and_initialize(sample_config)

        assert result.valid is True
        assert result.service == "configuration"
        assert result.error is None

    def test_validate_and_initialize_invalid_config(self, config_service):
        """Test validation and initialization with invalid configuration."""
        config = Config()
        config.embedding_length = None  # Invalid: must be positive integer

        result = config_service.validate_and_initialize(config)

        assert result.valid is False
        assert result.service == "configuration"
        assert "embedding_length" in result.error

    def test_validate_and_initialize_service_validation_failure(self, config_service):
        """Test validation and initialization when service validation fails."""
        # Create a config service without test mode to test actual service validation
        real_config_service = ConfigurationService(test_mode=False)
        config = Config()
        config.ollama_base_url = "http://invalid:9999"  # Invalid service URL

        result = real_config_service.validate_and_initialize(config)

        assert result.valid is False
        assert result.service == "configuration"
        assert "Service validation failed" in result.error

    def test_create_workspace_config(self, config_service):
        """Test creating workspace-specific configuration."""
        workspace_path = "/test/workspace"
        base_config_path = None
        overrides = {
            'chunking_strategy': 'treesitter',
            'use_tree_sitter': True
        }

        config = config_service.create_workspace_config(
            workspace_path=workspace_path,
            base_config_path=base_config_path,
            overrides=overrides
        )

        assert isinstance(config, Config)
        assert config.workspace_path == workspace_path
        assert config.chunking_strategy == "treesitter"
        assert config.use_tree_sitter is True

    def test_get_config_value_valid(self, config_service, sample_config):
        """Test getting configuration value with valid type."""
        # Test string value
        value = config_service.get_config_value(sample_config, 'ollama_base_url', str)
        assert value == "http://localhost:11434"
        assert isinstance(value, str)

        # Test integer value
        value = config_service.get_config_value(sample_config, 'embedding_length', int)
        assert value == 768
        assert isinstance(value, int)

        # Test boolean value
        value = config_service.get_config_value(sample_config, 'use_tree_sitter', bool)
        assert value is False
        assert isinstance(value, bool)

    def test_get_config_value_with_default(self, config_service, sample_config):
        """Test getting configuration value with default fallback."""
        # Test non-existent key with default
        value = config_service.get_config_value(sample_config, 'non_existent_key', str, "default_value")
        assert value == "default_value"

        # Test None value with default
        sample_config.ollama_base_url = None
        value = config_service.get_config_value(sample_config, 'ollama_base_url', str, "default_url")
        assert value == "default_url"

    def test_get_config_value_type_mismatch(self, config_service, sample_config):
        """Test getting configuration value with type mismatch."""
        # Test type mismatch with default
        value = config_service.get_config_value(sample_config, 'embedding_length', str, "768")
        assert value == "768"

        # Test type mismatch without default (should raise error)
        with pytest.raises(ValueError, match="Configuration key 'embedding_length' has type"):
            config_service.get_config_value(sample_config, 'embedding_length', str)

    def test_get_config_value_nonexistent_key(self, config_service, sample_config):
        """Test getting configuration value for non-existent key."""
        # Test non-existent key with default
        value = config_service.get_config_value(sample_config, 'non_existent_key', str, "default")
        assert value == "default"

        # Test non-existent key without default (should raise error)
        with pytest.raises(ValueError, match="Configuration key 'non_existent_key' not found"):
            config_service.get_config_value(sample_config, 'non_existent_key', str)

    def test_clear_cache(self, config_service):
        """Test clearing configuration and validation caches."""
        # Add some items to cache
        config_service._config_cache['test1'] = Config()
        config_service._validation_cache['test2'] = []

        # Clear cache
        config_service.clear_cache()

        # Verify cache is empty
        assert len(config_service._config_cache) == 0
        assert len(config_service._validation_cache) == 0

    def test_get_configuration_sources(self, config_service):
        """Test getting configuration sources."""
        sources = config_service.get_configuration_sources()

        assert len(sources) == 5
        assert all(isinstance(source, ConfigurationSource) for source in sources)

        # Check source types
        source_types = [source.source_type for source in sources]
        assert "cli" in source_types
        assert "workspace" in source_types
        assert "env" in source_types
        assert "file" in source_types
        assert "default" in source_types

    def test_get_config_summary(self, config_service, sample_config):
        """Test getting configuration summary."""
        summary = config_service.get_config_summary(sample_config)

        assert isinstance(summary, dict)
        assert "workspace_path" in summary
        assert "ollama_base_url" in summary
        assert "ollama_model" in summary
        assert "qdrant_url" in summary
        assert "embedding_length" in summary
        assert "chunking_strategy" in summary
        assert "use_tree_sitter" in summary
        assert "embed_timeout_seconds" in summary
        assert "search_min_score" in summary
        assert "search_max_results" in summary

    def test_configuration_service_with_error_handler(self):
        """Test ConfigurationService with custom error handler."""
        error_handler = ErrorHandler()
        config_service = ConfigurationService(error_handler)

        assert config_service.error_handler is error_handler

    def test_configuration_service_caching(self, config_service):
        """Test configuration caching functionality."""
        # Load configuration twice with same parameters
        config1 = config_service.load_with_fallback(
            config_path="nonexistent.json",
            workspace_path="/test/workspace"
        )

        config2 = config_service.load_with_fallback(
            config_path="nonexistent.json",
            workspace_path="/test/workspace"
        )

        # Should return cached configuration
        assert config1 is config2
        assert len(config_service._config_cache) == 1

    def test_validation_caching(self, config_service, sample_config):
        """Test validation result caching."""
        # Validate configuration twice
        result1 = config_service.validate_and_initialize(sample_config)
        result2 = config_service.validate_and_initialize(sample_config)

        # Should return cached validation result (same content, may be different objects)
        assert result1.valid == result2.valid
        assert result1.service == result2.service
        assert result1.error == result2.error
        assert len(config_service._validation_cache) == 1


class TestConfigurationSource:
    """Test suite for ConfigurationSource class."""

    def test_configuration_source_creation(self):
        """Test ConfigurationSource creation and properties."""
        source = ConfigurationSource(
            name="test_source",
            priority=50,
            path="/test/path",
            source_type="test"
        )

        assert source.name == "test_source"
        assert source.priority == 50
        assert source.path == "/test/path"
        assert source.source_type == "test"

    def test_configuration_source_defaults(self):
        """Test ConfigurationSource default values."""
        source = ConfigurationSource(name="test_source", priority=50)

        assert source.name == "test_source"
        assert source.priority == 50
        assert source.path is None
        assert source.source_type == "default"