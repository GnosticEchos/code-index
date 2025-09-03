"""
Unit tests for MCP Configuration Manager.

Tests configuration loading, validation, override application,
and documentation generation.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch
from pathlib import Path

from src.code_index.mcp_server.core.config_manager import (
    MCPConfigurationManager,
    ConfigurationOverride
)
from src.code_index.config import Config


class TestConfigurationOverride:
    """Test cases for ConfigurationOverride dataclass."""
    
    def test_configuration_override_creation(self):
        """Test creating ConfigurationOverride with various parameters."""
        override = ConfigurationOverride(
            embedding_length=1024,
            chunking_strategy="treesitter",
            use_tree_sitter=True,
            batch_segment_threshold=100
        )
        
        assert override.embedding_length == 1024
        assert override.chunking_strategy == "treesitter"
        assert override.use_tree_sitter is True
        assert override.batch_segment_threshold == 100
    
    def test_configuration_override_defaults(self):
        """Test ConfigurationOverride with default values."""
        override = ConfigurationOverride()
        
        assert override.embedding_length is None
        assert override.chunking_strategy is None
        assert override.use_tree_sitter is None
        assert override.batch_segment_threshold is None
    
    def test_validate_success(self):
        """Test successful validation of override parameters."""
        override = ConfigurationOverride(
            chunking_strategy="treesitter",
            use_tree_sitter=True,
            search_min_score=0.5,
            search_max_results=100,
            batch_segment_threshold=50,
            embed_timeout_seconds=120,
            embedding_length=768
        )
        
        errors = override.validate()
        assert len(errors) == 0
    
    def test_validate_invalid_chunking_strategy(self):
        """Test validation with invalid chunking strategy."""
        override = ConfigurationOverride(chunking_strategy="invalid")
        
        errors = override.validate()
        assert len(errors) == 1
        assert "chunking_strategy must be one of" in errors[0]
    
    def test_validate_invalid_search_score(self):
        """Test validation with invalid search score."""
        override = ConfigurationOverride(search_min_score=1.5)
        
        errors = override.validate()
        assert len(errors) == 1
        assert "search_min_score must be a number between 0 and 1" in errors[0]
    
    def test_validate_negative_values(self):
        """Test validation with negative values."""
        override = ConfigurationOverride(
            search_max_results=-1,
            batch_segment_threshold=0,
            embed_timeout_seconds=-10
        )
        
        errors = override.validate()
        assert len(errors) == 3
        assert any("search_max_results must be a positive integer" in error for error in errors)
        assert any("batch_segment_threshold must be a positive integer" in error for error in errors)
        assert any("embed_timeout_seconds must be a positive integer" in error for error in errors)
    
    def test_validate_compatibility_treesitter_lines(self):
        """Test validation of treesitter with lines strategy."""
        override = ConfigurationOverride(
            chunking_strategy="treesitter",
            use_tree_sitter=False
        )
        
        errors = override.validate()
        assert len(errors) == 1
        assert "chunking_strategy='treesitter' requires use_tree_sitter=true" in errors[0]
    
    def test_validate_tree_sitter_params_without_flag(self):
        """Test validation of tree-sitter parameters without use_tree_sitter=True."""
        override = ConfigurationOverride(
            use_tree_sitter=False,
            tree_sitter_max_file_size_bytes=1024,
            tree_sitter_skip_test_files=True
        )
        
        errors = override.validate()
        assert len(errors) == 1
        assert "Tree-sitter parameters" in errors[0]
        assert "require use_tree_sitter=true" in errors[0]
    
    def test_validate_token_params_without_strategy(self):
        """Test validation of token parameters without token strategy."""
        override = ConfigurationOverride(
            chunking_strategy="lines",
            token_chunk_size=500
        )
        
        errors = override.validate()
        assert len(errors) == 1
        assert "token_chunk_* parameters require chunking_strategy='tokens'" in errors[0]
    
    def test_validate_mmap_params_without_flag(self):
        """Test validation of mmap parameters without mmap flag."""
        override = ConfigurationOverride(
            use_mmap_file_reading=False,
            mmap_min_file_size_bytes=1024
        )
        
        errors = override.validate()
        assert len(errors) == 1
        assert "mmap_min_file_size_bytes requires use_mmap_file_reading=true" in errors[0]
    
    def test_get_non_none_fields(self):
        """Test getting non-None fields from override."""
        override = ConfigurationOverride(
            embedding_length=768,
            chunking_strategy=None,
            use_tree_sitter=True,
            batch_segment_threshold=None
        )
        
        fields = override.get_non_none_fields()
        
        assert fields == {
            "embedding_length": 768,
            "use_tree_sitter": True
        }


class TestMCPConfigurationManager:
    """Test cases for MCPConfigurationManager."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "chunking_strategy": "lines",
                "use_tree_sitter": False,
                "search_min_score": 0.4,
                "search_max_results": 50,
                "batch_segment_threshold": 60
            }
            json.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def invalid_config_file(self):
        """Create an invalid configuration file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                # Missing embedding_length
                "chunking_strategy": "invalid_strategy",
                "search_min_score": 1.5,  # Invalid range
                "search_max_results": -10  # Invalid value
            }
            json.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_initialization(self, temp_config_file):
        """Test configuration manager initialization."""
        manager = MCPConfigurationManager(temp_config_file)
        
        assert manager.config_path == temp_config_file
        assert manager._base_config is None
    
    def test_initialization_default_path(self):
        """Test configuration manager with default path."""
        manager = MCPConfigurationManager()
        
        assert manager.config_path == "code_index.json"
    
    def test_load_config_existing_file(self, temp_config_file):
        """Test loading configuration from existing file."""
        manager = MCPConfigurationManager(temp_config_file)
        
        config = manager.load_config()
        
        assert config is not None
        assert config.embedding_length == 768
        assert config.chunking_strategy == "lines"
        assert config.search_min_score == 0.4
        assert manager._base_config is config
    
    def test_load_config_nonexistent_file(self):
        """Test loading configuration from non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "new_config.json")
            manager = MCPConfigurationManager(config_path)
            
            config = manager.load_config()
            
            assert config is not None
            assert os.path.exists(config_path)  # Should create default config
            assert manager._base_config is config
    
    def test_load_config_invalid_file(self, invalid_config_file):
        """Test loading invalid configuration file."""
        manager = MCPConfigurationManager(invalid_config_file)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            manager.load_config()
    
    def test_validate_config_success(self, temp_config_file):
        """Test successful configuration validation."""
        manager = MCPConfigurationManager(temp_config_file)
        config = Config.from_file(temp_config_file)
        
        # Should not raise any exceptions
        manager._validate_config(config)
    
    def test_validate_config_missing_embedding_length(self):
        """Test configuration validation with missing embedding_length."""
        manager = MCPConfigurationManager()
        config = Config()
        config.embedding_length = None
        
        with pytest.raises(ValueError, match="embedding_length must be set"):
            manager._validate_config(config)
    
    def test_validate_config_invalid_chunking_strategy(self):
        """Test configuration validation with invalid chunking strategy."""
        manager = MCPConfigurationManager()
        config = Config()
        config.embedding_length = 768
        config.chunking_strategy = "invalid"
        
        with pytest.raises(ValueError, match="chunking_strategy must be one of"):
            manager._validate_config(config)
    
    def test_apply_overrides_success(self, temp_config_file):
        """Test successful override application."""
        manager = MCPConfigurationManager(temp_config_file)
        base_config = manager.load_config()
        
        overrides = {
            "embedding_length": 1024,
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True,
            "batch_segment_threshold": 100
        }
        
        new_config = manager.apply_overrides(base_config, overrides)
        
        assert new_config.embedding_length == 1024
        assert new_config.chunking_strategy == "treesitter"
        assert new_config.use_tree_sitter is True
        assert new_config.batch_segment_threshold == 100
        
        # Original config should be unchanged
        assert base_config.embedding_length == 768
        assert base_config.chunking_strategy == "lines"
    
    def test_apply_overrides_invalid_parameters(self, temp_config_file):
        """Test override application with invalid parameters."""
        manager = MCPConfigurationManager(temp_config_file)
        base_config = manager.load_config()
        
        overrides = {
            "chunking_strategy": "invalid",
            "search_min_score": 1.5
        }
        
        with pytest.raises(ValueError, match="Configuration override validation failed"):
            manager.apply_overrides(base_config, overrides)
    
    def test_apply_overrides_compatibility_error(self, temp_config_file):
        """Test override application with compatibility errors."""
        manager = MCPConfigurationManager(temp_config_file)
        base_config = manager.load_config()
        
        overrides = {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": False  # Incompatible
        }
        
        with pytest.raises(ValueError, match="Configuration override validation failed"):
            manager.apply_overrides(base_config, overrides)
    
    def test_apply_overrides_unknown_parameters(self, temp_config_file):
        """Test override application with unknown parameters."""
        manager = MCPConfigurationManager(temp_config_file)
        base_config = manager.load_config()
        
        overrides = {
            "embedding_length": 1024,
            "unknown_parameter": "value",  # Should be ignored
            "another_unknown": 123
        }
        
        new_config = manager.apply_overrides(base_config, overrides)
        
        assert new_config.embedding_length == 1024
        assert not hasattr(new_config, "unknown_parameter")
        assert not hasattr(new_config, "another_unknown")
    
    def test_create_override_object_success(self):
        """Test creating override object from dictionary."""
        manager = MCPConfigurationManager()
        
        overrides = {
            "embedding_length": 768,
            "chunking_strategy": "tokens",
            "use_tree_sitter": False
        }
        
        override_obj = manager._create_override_object(overrides)
        
        assert isinstance(override_obj, ConfigurationOverride)
        assert override_obj.embedding_length == 768
        assert override_obj.chunking_strategy == "tokens"
        assert override_obj.use_tree_sitter is False
    
    def test_create_override_object_invalid_types(self):
        """Test creating override object with invalid types."""
        manager = MCPConfigurationManager()
        
        overrides = {
            "embedding_length": "not_an_int",  # Should be int
        }
        
        with pytest.raises(ValueError, match="Invalid override parameters"):
            manager._create_override_object(overrides)
    
    def test_get_available_overrides(self):
        """Test getting list of available override parameters."""
        manager = MCPConfigurationManager()
        
        overrides = manager.get_available_overrides()
        
        assert isinstance(overrides, list)
        assert "embedding_length" in overrides
        assert "chunking_strategy" in overrides
        assert "use_tree_sitter" in overrides
        assert "search_min_score" in overrides
        assert len(overrides) > 10  # Should have many parameters
    
    def test_check_override_compatibility_success(self):
        """Test compatibility checking with valid overrides."""
        manager = MCPConfigurationManager()
        
        overrides = {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True,
            "batch_segment_threshold": 50
        }
        
        result = manager.check_override_compatibility(overrides)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_check_override_compatibility_errors(self):
        """Test compatibility checking with invalid overrides."""
        manager = MCPConfigurationManager()
        
        overrides = {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": False,  # Incompatible
            "search_min_score": 1.5  # Invalid range
        }
        
        result = manager.check_override_compatibility(overrides)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_check_override_compatibility_warnings(self):
        """Test compatibility checking with warnings."""
        manager = MCPConfigurationManager()
        
        overrides = {
            "use_tree_sitter": True,
            "chunking_strategy": "lines",  # Suboptimal combination
            "batch_segment_threshold": 150,  # Large value
            "embed_timeout_seconds": 15  # Short timeout
        }
        
        result = manager.check_override_compatibility(overrides)
        
        assert result["valid"] is True
        assert len(result["warnings"]) > 0
    
    def test_check_override_compatibility_suggestions(self):
        """Test compatibility checking with suggestions."""
        manager = MCPConfigurationManager()
        
        overrides = {
            "chunking_strategy": "treesitter"
            # Missing use_tree_sitter=True
        }
        
        result = manager.check_override_compatibility(overrides)
        
        assert result["valid"] is True
        assert len(result["suggestions"]) > 0
        assert any("use_tree_sitter=true" in suggestion for suggestion in result["suggestions"])
    
    def test_get_config_documentation(self):
        """Test getting configuration documentation."""
        manager = MCPConfigurationManager()
        
        docs = manager.get_config_documentation()
        
        assert isinstance(docs, dict)
        assert "categories" in docs
        assert "examples" in docs
        assert "optimization_strategies" in docs
        assert "parameter_compatibility" in docs
        assert "troubleshooting" in docs
        
        # Check categories structure
        categories = docs["categories"]
        assert "core" in categories
        assert "performance" in categories
        assert "chunking" in categories
        assert "search" in categories
        assert "advanced" in categories
    
    def test_get_optimization_examples(self):
        """Test getting optimization examples."""
        manager = MCPConfigurationManager()
        
        examples = manager.get_optimization_examples()
        
        assert isinstance(examples, dict)
        assert len(examples) > 0
        
        # Should have different optimization strategies
        example_keys = list(examples.keys())
        assert any("fast" in key.lower() for key in example_keys)
        assert any("accuracy" in key.lower() or "semantic" in key.lower() for key in example_keys)


class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "code_index.json"
            config_data = {
                "ollama_base_url": "http://localhost:11434",
                "ollama_model": "nomic-embed-text:latest",
                "qdrant_url": "http://localhost:6333",
                "embedding_length": 768,
                "workspace_path": temp_dir,
                "chunking_strategy": "lines",
                "use_tree_sitter": False
            }
            config_file.write_text(json.dumps(config_data, indent=2))
            
            yield temp_dir
    
    def test_end_to_end_configuration_workflow(self, temp_workspace):
        """Test complete configuration workflow."""
        config_path = os.path.join(temp_workspace, "code_index.json")
        manager = MCPConfigurationManager(config_path)
        
        # Load base configuration
        base_config = manager.load_config()
        assert base_config.embedding_length == 768
        assert base_config.chunking_strategy == "lines"
        
        # Apply overrides
        overrides = {
            "chunking_strategy": "treesitter",
            "use_tree_sitter": True,
            "tree_sitter_skip_test_files": True,
            "batch_segment_threshold": 100
        }
        
        new_config = manager.apply_overrides(base_config, overrides)
        
        # Verify overrides applied
        assert new_config.chunking_strategy == "treesitter"
        assert new_config.use_tree_sitter is True
        assert new_config.tree_sitter_skip_test_files is True
        assert new_config.batch_segment_threshold == 100
        
        # Original config unchanged
        assert base_config.chunking_strategy == "lines"
        assert base_config.use_tree_sitter is False


if __name__ == "__main__":
    pytest.main([__file__])