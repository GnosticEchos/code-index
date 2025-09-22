"""
Test module for CLI commands.
"""
import os
import tempfile
import pytest
from click.testing import CliRunner
from code_index.cli import cli
from code_index.services import IndexingService, SearchService, ConfigurationService
from code_index.errors import ErrorHandler


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'index' in result.output
    assert 'search' in result.output
    assert 'collections' in result.output


def test_cli_index_help():
    """Test CLI index command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['index', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output


def test_cli_search_help():
    """Test CLI search command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output
    assert '--min-score' in result.output
    assert '--max-results' in result.output


def test_cli_clear_help():
    """Test collections clear-all command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['collections', 'clear-all', '--help'])
    assert result.exit_code == 0
    assert 'clear-all' in result.output
    assert 'Delete all Qdrant collections and clear local cache files.' in result.output


def test_cli_service_integration():
    """Test CLI integration with service composition pattern."""
    # Test that CLI can import and initialize all services
    error_handler = ErrorHandler()

    # Test IndexingService initialization
    indexing_service = IndexingService(error_handler)
    assert indexing_service is not None
    assert hasattr(indexing_service, 'index_workspace')

    # Test SearchService initialization
    search_service = SearchService(error_handler)
    assert search_service is not None
    assert hasattr(search_service, 'search_code')

    # Test ConfigurationService initialization
    config_service = ConfigurationService(error_handler)
    assert config_service is not None
    assert hasattr(config_service, 'get_file_status')
    assert hasattr(config_service, 'get_processing_stats')
    assert hasattr(config_service, 'get_workspace_status')


def test_cli_index_with_service_integration():
    """Test CLI index command with service integration."""
    runner = CliRunner()

    # Test index command help still works
    result = runner.invoke(cli, ['index', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output
    assert 'Index code files in workspace' in result.output


def test_cli_search_with_service_integration():
    """Test CLI search command with service integration."""
    runner = CliRunner()

    # Test search command help still works
    result = runner.invoke(cli, ['search', '--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert '--workspace' in result.output
    assert '--config' in result.output
    assert '--min-score' in result.output
    assert '--max-results' in result.output
    assert 'Search indexed code using semantic similarity' in result.output


def test_cli_collections_with_service_integration():
    """Test CLI collections commands with service integration."""
    runner = CliRunner()

    # Test collections list command help
    result = runner.invoke(cli, ['collections', 'list', '--help'])
    assert result.exit_code == 0
    assert 'list' in result.output
    assert 'List all collections' in result.output

    # Test collections info command help
    result = runner.invoke(cli, ['collections', 'info', '--help'])
    assert result.exit_code == 0
    assert 'info' in result.output
    assert 'Show detailed information about a collection' in result.output


def test_service_dependency_injection():
    """Test that services properly use dependency injection."""
    # Test with custom error handler
    custom_error_handler = ErrorHandler()

    indexing_service = IndexingService(custom_error_handler)
    assert indexing_service.error_handler is custom_error_handler

    search_service = SearchService(custom_error_handler)
    assert search_service.error_handler is custom_error_handler

    config_service = ConfigurationService(custom_error_handler)
    assert config_service.error_handler is custom_error_handler


def test_service_composition_pattern():
    """Test that CLI uses service composition rather than inheritance."""
    # Verify that CLI methods use service composition
    # This is tested by checking that the CLI imports and uses services
    # rather than inheriting behavior or mixing command/query logic

    # Import the CLI module to ensure it can be loaded with service dependencies
    from code_index.cli import cli

    # Verify the CLI module has the expected structure
    # CLI is a Click Group, so commands are stored in cli.commands
    assert hasattr(cli, 'commands')

    # Verify that the CLI commands are properly registered
    commands = [cmd.name for cmd in cli.commands.values()]
    assert 'index' in commands
    assert 'search' in commands
    assert 'collections' in commands

    # Verify that the CLI can import and initialize all services
    error_handler = ErrorHandler()

    # Test IndexingService initialization
    indexing_service = IndexingService(error_handler)
    assert indexing_service is not None
    assert hasattr(indexing_service, 'index_workspace')

    # Test SearchService initialization
    search_service = SearchService(error_handler)
    assert search_service is not None
    assert hasattr(search_service, 'search_code')

    # Test ConfigurationService initialization (the query service)
    config_service = ConfigurationService(error_handler)
    assert config_service is not None
    assert hasattr(config_service, 'get_file_status')
    assert hasattr(config_service, 'get_processing_stats')
    assert hasattr(config_service, 'get_workspace_status')