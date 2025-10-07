"""
Test module for new CLI commands and enhanced functionality.
"""
import os
import tempfile
import pytest
from click.testing import CliRunner
from code_index.cli_new import cli
from code_index.services import HealthService, WorkspaceService
from code_index.search import SearchValidationService, SearchStrategyFactory, SearchResultProcessor
from code_index.errors import ErrorHandler


def test_new_health_command():
    """Test the new health command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['health', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'Check system health and configuration status' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output


def test_new_workspace_command():
    """Test the new workspace command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['workspace', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'Validate workspace configuration and display workspace information' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output


def test_new_validate_config_command():
    """Test the new validate-config command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['validate-config', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'Validate search configuration' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output


def test_new_search_strategies_command():
    """Test the new search-strategies command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['search-strategies'])
    assert result.exit_code == 0
    assert 'Available Search Strategies' in result.output
    assert 'Available strategies:' in result.output


def test_new_search_info_command():
    """Test the new search-info command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['search-info'])
    assert result.exit_code == 0
    assert 'Search Result Processing Info' in result.output
    assert 'Validation rules:' in result.output


def test_enhanced_index_with_health_check():
    """Test enhanced index command with health checks."""
    runner = CliRunner()
    result = runner.invoke(cli, ['index', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--health-check' in result.output
    assert 'Perform health checks before indexing' in result.output


def test_enhanced_index_with_workspace_validation():
    """Test enhanced index command with workspace validation."""
    runner = CliRunner()
    result = runner.invoke(cli, ['index', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--workspace-check' in result.output
    assert 'Validate workspace configuration' in result.output


def test_enhanced_search_with_strategy_selection():
    """Test enhanced search command with strategy selection."""
    runner = CliRunner()
    result = runner.invoke(cli, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--search-strategy' in result.output
    assert 'Search strategy for search operations' in result.output


def test_service_integration_new_services():
    """Test service integration with new services."""
    # Test HealthService initialization
    error_handler = ErrorHandler()
    health_service = HealthService(error_handler)
    assert health_service is not None
    assert hasattr(health_service, 'check_health')
    
    # Test WorkspaceService initialization
    workspace_service = WorkspaceService(error_handler)
    assert workspace_service is not None
    assert hasattr(workspace_service, 'validate_workspace')
    
    # Test SearchValidationService initialization
    search_validation_service = SearchValidationService(error_handler)
    assert search_validation_service is not None
    assert hasattr(search_validation_service, 'validate_search_config')
    
    # Test SearchStrategyFactory initialization
    strategy_factory = SearchStrategyFactory()
    assert strategy_factory is not None
    assert hasattr(strategy_factory, 'get_available_strategies')


def test_service_dependency_injection_new_services():
    """Test that new services properly use dependency injection."""
    # Test with custom error handler
    custom_error_handler = ErrorHandler()
    
    health_service = HealthService(custom_error_handler)
    assert health_service.error_handler is custom_error_handler
    
    workspace_service = WorkspaceService(custom_error_handler)
    assert workspace_service.error_handler is custom_error_handler
    
    search_validation_service = SearchValidationService(custom_error_handler)
    assert search_validation_service.error_handler is custom_error_handler