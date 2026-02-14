import json

from src.code_index.config import Config


def _build_sample_config() -> Config:
    config = Config()
    config.workspace_path = "/sample/workspace"
    config.use_tree_sitter = True
    config.tree_sitter_max_blocks_per_file = 42
    config.search_min_score = 0.55
    config.streaming_threshold_bytes = 2 * 1024 * 1024
    config.logging_component_levels = {"code_index": "DEBUG"}
    return config


def test_config_round_trip_flattened() -> None:
    original = _build_sample_config()

    serialized = original.to_dict()

    restored = Config()
    restored.update_from_dict(serialized)

    assert restored.workspace_path == original.workspace_path
    assert restored.use_tree_sitter is True
    assert restored.tree_sitter_max_blocks_per_file == 42
    assert restored.search_min_score == 0.55
    assert restored.streaming_threshold_bytes == 2 * 1024 * 1024
    assert restored.logging_component_levels == {"code_index": "DEBUG"}


def test_config_round_trip_nested_dict() -> None:
    original = _build_sample_config()

    nested = original.to_nested_dict()
    nested["tree_sitter"]["tree_sitter_max_blocks_per_file"] = 99
    nested["performance"]["streaming_threshold_bytes"] = 3 * 1024 * 1024

    restored = Config()
    restored.update_from_dict(nested)

    assert restored.use_tree_sitter is True
    assert restored.tree_sitter_max_blocks_per_file == 99
    assert restored.streaming_threshold_bytes == 3 * 1024 * 1024


def test_config_save_and_from_file(tmp_path) -> None:
    original = _build_sample_config()
    original.tree_sitter_debug_logging = True

    config_path = tmp_path / "code_index.json"
    original.save(config_path.as_posix())

    loaded = Config.from_file(config_path.as_posix())

    assert loaded.workspace_path == original.workspace_path
    assert loaded.tree_sitter_debug_logging is True
    assert loaded.logging_component_levels == {"code_index": "DEBUG"}


def test_config_to_json_formats() -> None:
    original = _build_sample_config()

    flat_json = original.to_json()
    nested_json = original.to_json(nested=True)

    assert json.loads(flat_json)["workspace_path"] == "/sample/workspace"
    assert json.loads(nested_json)["tree_sitter"]["tree_sitter_max_blocks_per_file"] == 42
