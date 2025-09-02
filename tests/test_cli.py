"""
Test module for CLI commands.
"""
import os
import tempfile
import pytest
from click.testing import CliRunner
from code_index.cli import cli


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