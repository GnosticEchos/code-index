from types import SimpleNamespace as NS
import json
import os
from unittest.mock import patch, Mock

import code_index.cli as cli


def test_index_payload_model_key(monkeypatch, tmp_path):
    # Create a dummy workspace with one file
    ws = tmp_path
    fpath = ws / "example.py"
    fpath.write_text("# sample content\nprint('hello')\n", encoding="utf-8")

    # Create a minimal config file (values largely unused due to mocking)
    cfg_path = ws / "code_index.json"
    cfg_path.write_text(json.dumps({"embedding_length": 3, "workspace_path": str(ws)}), encoding="utf-8")

    # Capture container for points sent to upsert
    captured = {}

    # Dummy components to isolate index() pipeline up to payload creation
    class DummyEmbedder:
        def __init__(self, config):
            self.model = "bge-m3:latest"
            self.timeout = 1

        @property
        def model_identifier(self) -> str:
            # Canonicalized value (trim ':latest')
            return "bge-m3"

        def validate_configuration(self):
            return {"valid": True}

        def create_embeddings(self, texts):
            # Return one 3D vector per text
            return {"embeddings": [[0.1, 0.2, 0.3] for _ in texts]}

    class DummyVectorStore:
        def __init__(self, config):
            pass

        def initialize(self):
            return True

        def delete_points_by_file_path(self, rel_path: str):
            # no-op for test
            pass

        def upsert_points(self, points):
            captured["points"] = points

    class DummyScanner:
        def __init__(self, config):
            pass

        def scan_directory(self):
            # Return our one file, zero skipped
            return [str(fpath)], 0

    class DummyParser:
        def __init__(self, config, chunking_strategy):
            pass

        def parse_file(self, file_path: str):
            # Return one block; content must be non-empty/strip() to be embedded
            return [NS(content="hello world", start_line=1, end_line=2, type="py")]

    # Mock ConfigurationService to prevent service validation and real config loading
    with patch('src.code_index.cli.ConfigurationService') as mock_config_service_class:
        mock_config_service = Mock()
        mock_config = Mock()
        mock_config.embedding_length = 3
        mock_config.workspace_path = str(ws)
        mock_config.batch_segment_threshold = 60
        mock_config.max_file_size_bytes = 2097152
        mock_config.timeout_log_path = "timeout_files.txt"
        mock_config_service.load_with_fallback.return_value = mock_config
        mock_config_service_class.return_value = mock_config_service

        # Mock FileProcessingService to prevent undefined variable errors
        with patch('src.code_index.cli.FileProcessingService') as mock_file_processor_class:
            mock_file_processor = Mock()
            mock_file_processor.load_path_list.return_value = []
            mock_file_processor.load_workspace_list.return_value = []
            mock_file_processor.load_exclude_list.return_value = set()
            mock_file_processor.filter_files_by_criteria.return_value = [str(fpath)]
            mock_file_processor.get_file_hash.return_value = "mock_hash"
            mock_file_processor.augment_extensions_with_pygments.return_value = []
            mock_file_processor_class.return_value = mock_file_processor

            # Mock the functions that use file_processor
            monkeypatch.setattr(cli, "_load_path_list", lambda *args, **kwargs: [])
            monkeypatch.setattr(cli, "_load_workspace_list", lambda *args, **kwargs: [])
            monkeypatch.setattr(cli, "_load_exclude_list", lambda *args, **kwargs: set())
            monkeypatch.setattr(cli, "_write_timeout_log", lambda *args, **kwargs: None)

            # Mock the file_processor variable used in _process_single_workspace
            mock_file_processor = Mock()
            mock_file_processor.get_file_hash.return_value = "mock_hash"
            mock_file_processor.augment_extensions_with_pygments.return_value = []
            # Mock it at the function level where it's used
            original_process = cli._process_single_workspace
            def mock_process_single_workspace(*args, **kwargs):
                # Replace file_processor usage with our mock
                original_file_processor = getattr(cli, 'file_processor', None)
                cli.file_processor = mock_file_processor
                try:
                    return original_process(*args, **kwargs)
                finally:
                    if original_file_processor is not None:
                        cli.file_processor = original_file_processor
                    elif hasattr(cli, 'file_processor'):
                        delattr(cli, 'file_processor')
            monkeypatch.setattr(cli, "_process_single_workspace", mock_process_single_workspace)

            # Patch pipeline classes used by cli._process_single_workspace
            monkeypatch.setattr(cli, "OllamaEmbedder", DummyEmbedder)
            monkeypatch.setattr(cli, "QdrantVectorStore", DummyVectorStore)
            monkeypatch.setattr(cli, "DirectoryScanner", DummyScanner)
            monkeypatch.setattr(cli, "CodeParser", DummyParser)

    # Run the single-workspace processing path to trigger point creation
    cli._process_single_workspace(
        workspace=str(ws),
        config=str(cfg_path),
        embed_timeout=None,
        retry_list=None,
        timeout_log=None,
        ignore_config=None,
        ignore_override_pattern=None,
        auto_ignore_detection=False,
        use_tree_sitter=False,
        chunking_strategy=None,
    )

    # Assert that points were upserted and payload includes canonicalized embedding_model
    assert "points" in captured and captured["points"], "No points captured for upsert"
    payload = captured["points"][0].get("payload", {})
    assert payload.get("embedding_model") == "bge-m3"