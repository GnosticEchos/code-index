from click.testing import CliRunner
import json
from code_index.cli import cli
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore


def test_cli_json_schema_includes_adjusted_score(monkeypatch):
    # Hermetic: stub embedder and vector store to avoid external services
    monkeypatch.setattr(OllamaEmbedder, "validate_configuration", lambda self: {"valid": True})
    monkeypatch.setattr(OllamaEmbedder, "create_embeddings", lambda self, texts: {"embeddings": [[0.0, 0.1, 0.2]]})

    # Deterministic QdrantVectorStore.search returning adjustedScore values
    def fake_search(self, query_vector, directory_prefix=None, min_score=0.1, max_results=10):
        return [
            {
                "score": 0.42,
                "adjustedScore": 0.63,
                "payload": {
                    "filePath": "src/components/A.vue",
                    "startLine": 1,
                    "endLine": 10,
                    "type": ".vue",
                    "codeChunk": "..."
                }
            },
            {
                "score": 0.50,
                "adjustedScore": 0.50,
                "payload": {
                    "filePath": "docs/readme.md",
                    "startLine": 5,
                    "endLine": 20,
                    "type": ".md",
                    "codeChunk": "..."
                }
            }
        ]

    monkeypatch.setattr(QdrantVectorStore, "search", fake_search)

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