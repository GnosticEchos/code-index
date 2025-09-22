from click.testing import CliRunner
import json
from code_index.cli import cli
from code_index.services import SearchService
from code_index.models import SearchMatch
from code_index.config_service import ConfigurationService


def test_cli_json_schema_includes_adjusted_score(monkeypatch):
    """Test CLI JSON output schema with service integration."""

    # Mock the SearchService to return test data
    def fake_search_code(self, query, config):
        matches = [
            SearchMatch(
                file_path="src/components/A.vue",
                start_line=1,
                end_line=10,
                code_chunk="<template>...</template>",
                match_type="vue",
                score=0.42,
                adjusted_score=0.63,
                metadata={}
            ),
            SearchMatch(
                file_path="docs/readme.md",
                start_line=5,
                end_line=20,
                code_chunk="# Documentation...",
                match_type="markdown",
                score=0.50,
                adjusted_score=0.50,
                metadata={}
            )
        ]

        from code_index.models import SearchResult
        return SearchResult(
            query=query,
            matches=matches,
            total_found=len(matches),
            execution_time_seconds=0.1,
            search_method="text",
            config_summary={},
            errors=[],
            warnings=[]
        )

    monkeypatch.setattr(SearchService, "search_code", fake_search_code)

    # Mock the ConfigurationService to return a valid config
    def fake_load_with_fallback(self, config_path, workspace_path, overrides=None):
        from code_index.config import Config
        config = Config()
        config.workspace_path = workspace_path
        config.ollama_base_url = "http://localhost:11434"
        config.qdrant_url = "http://localhost:6333"
        config.embedding_model = "nomic-embed-text"
        config.embedding_length = 768
        config.chunking_strategy = "lines"
        config.search_min_score = 0.4
        config.search_max_results = 50
        return config

    # Mock the ConfigurationService that the CLI uses (the config loader service)
    monkeypatch.setattr(ConfigurationService, "load_with_fallback", fake_load_with_fallback)

    # Invoke CLI in an isolated filesystem so no real configs are mutated
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["search", "--json", "dummy query"])

        # CLI should succeed and produce valid JSON list
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list) and len(data) >= 2

        # Schema assertions
        required = {"filePath", "startLine", "endLine", "type", "score", "adjustedScore", "snippet"}
        for item in data:
            assert required.issubset(item.keys())

        # Ensure at least one item has adjustedScore != score
        assert any(it["adjustedScore"] != it["score"] for it in data)