import os
import tempfile

import pytest

from code_index.config import Config
from code_index.config_service import ConfigurationService
from code_index.errors import ErrorHandler
from code_index.file_processing import FileProcessingService


@pytest.fixture
def workspace_dir(tmp_path, register_workspace_for_cleanup):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    register_workspace_for_cleanup(str(workspace))
    return workspace


def create_file(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def test_load_path_list_filters_outside_entries(workspace_dir):
    list_file = workspace_dir / "paths.txt"
    create_file(
        list_file,
        """
        src/allowed.py
        /tmp/escape.py
        ../outside/file.py
        *.py
        """.strip()
    )

    service = FileProcessingService(ErrorHandler())
    results = service.load_path_list(str(list_file), str(workspace_dir), "test_load_path_list")

    assert "src/allowed.py" in results
    assert ".py" in results
    assert not any("tmp" in entry for entry in results)
    assert not any(entry.startswith("..") for entry in results)


def test_load_exclude_list_filters_outside_entries(workspace_dir):
    exclude_file = workspace_dir / "exclude.txt"
    create_file(
        exclude_file,
        """
        logs/
        ../outside
        *.log
        /tmp/escape.txt
        """.strip()
    )

    service = FileProcessingService(ErrorHandler())
    results = service.load_exclude_list(str(workspace_dir), str(exclude_file), "test_load_exclude_list")

    assert "logs/" in results
    assert ".log" in results
    assert not any(entry.startswith("..") for entry in results)
    assert not any("tmp" in entry for entry in results)


def test_cli_override_rejects_outside_timeout_log(workspace_dir):
    config = Config()
    config.workspace_path = str(workspace_dir)

    service = ConfigurationService(test_mode=True)
    updated = service.apply_cli_overrides(config, {"timeout_log_path": "../escape.log"})

    assert updated.timeout_log_path == "timeout_files.txt"


def test_cli_override_accepts_workspace_timeout_log(workspace_dir):
    config = Config()
    config.workspace_path = str(workspace_dir)

    service = ConfigurationService(test_mode=True)
    updated = service.apply_cli_overrides(config, {"timeout_log_path": "logs/timeouts.log"})

    assert updated.timeout_log_path == "logs/timeouts.log"
