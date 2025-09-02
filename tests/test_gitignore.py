import os
import pytest
from pathlib import Path

from code_index.config import Config
from code_index.scanner import DirectoryScanner


@pytest.fixture
def config(tmp_path):
    """Provides a default Config object for tests."""
    cfg = Config()
    cfg.workspace_path = str(tmp_path)
    cfg.auto_ignore_detection = True
    cfg.extensions = [".js", ".rs", ".py"]
    return cfg


def test_ignore_node_modules(tmp_path, config):
    """Test that node_modules is ignored in a Node.js project."""
    # Create a dummy Node.js project
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "some_dependency.js").write_text("console.log('hello');")
    (tmp_path / ".gitignore").write_text("node_modules/")

    scanner = DirectoryScanner(config)
    scanned_files, _ = scanner.scan_directory()

    assert not any("node_modules" in f for f in scanned_files)


def test_ignore_rust_target(tmp_path, config):
    """Test that target is ignored in a Rust project."""
    # Create a dummy Rust project
    (tmp_path / "Cargo.toml").write_text("[package]")
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "debug").mkdir()
    (tmp_path / "target" / "debug" / "some_binary.rs").write_text("fn main() {}")

    scanner = DirectoryScanner(config)
    scanned_files, _ = scanner.scan_directory()

    assert not any("target" in f for f in scanned_files)


def test_ignore_python_pycache(tmp_path, config):
    """Test that __pycache__ is ignored in a Python project."""
    # Create a dummy Python project
    (tmp_path / "requirements.txt").write_text("pytest")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "some_module.cpython-39.pyc").write_text("")

    scanner = DirectoryScanner(config)
    scanned_files, _ = scanner.scan_directory()

    assert not any("__pycache__" in f for f in scanned_files)
