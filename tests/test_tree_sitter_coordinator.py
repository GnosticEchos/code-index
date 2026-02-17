import types
from unittest.mock import Mock

import pytest

from code_index.chunking import TreeSitterError
from code_index.config import Config
from code_index.models import CodeBlock
from code_index.services import TreeSitterChunkCoordinator


class _StubTree:
    def __init__(self, root_node=None):
        self.root_node = root_node or object()


class _StubParser:
    def parse(self, data: bytes):
        return _StubTree()


class _StubExtractionResult:
    def __init__(self, blocks, success=True):
        self.blocks = blocks
        self.success = success
        self.metadata = {}


class _StubBlockExtractor:
    def __init__(self, result):
        self._result = result

    def extract_blocks_from_root_node(self, *args, **kwargs):
        return self._result


class _StubResourceManager:
    def __init__(self, parser):
        self._parser = parser

    def acquire_resources(self, language_key, resource_type):
        return {"parser": self._parser}

    def cleanup_all(self):
        return {"cleaned": True}


class _StubConfigManager:
    def apply_language_optimizations(self, file_path, language_key):
        return {"max_blocks": 100}

    def get_query_for_language(self, language_key):
        return f"query::{language_key}"

    def _get_node_types_for_language(self, language_key):
        return ["function", "class"]


class _StubBatchProcessor:
    def __init__(self):
        self.calls = []

    def process_batch(self, files):
        self.calls.append(files)
        return Mock(results={})


@pytest.fixture()
def config():
    cfg = Config()
    cfg.use_tree_sitter = True
    return cfg


@pytest.fixture()
def fallback():
    def _fallback(text, file_path, file_hash):
        return [CodeBlock(file_path, "fallback", "fallback", 1, 1, text, file_hash, file_hash)]

    return _fallback


def _create_coordinator(config, *, file_validator=True, extraction_result=None, error_handler=None, fallback_callable=None):
    error_handler = error_handler or Mock()

    file_processor = Mock()
    file_processor.validate_file.return_value = file_validator

    resource_manager = _StubResourceManager(_StubParser())
    result = extraction_result or _StubExtractionResult([
        CodeBlock("test.py", "fn", "function", 1, 3, "content", "hash", "segment")
    ])
    block_extractor = _StubBlockExtractor(result)

    coordinator = TreeSitterChunkCoordinator(
        config,
        error_handler=error_handler,
        file_processor=file_processor,
        resource_manager=resource_manager,
        block_extractor=block_extractor,
        config_manager=_StubConfigManager(),
        batch_processor=_StubBatchProcessor(),
        fallback_callable=fallback_callable,
    )

    coordinator.get_language_key = types.MethodType(lambda self, path: "python", coordinator)
    return coordinator, file_processor, error_handler, block_extractor


def test_chunk_text_returns_extraction_blocks(config, fallback):
    coordinator, file_processor, error_handler, block_extractor = _create_coordinator(
        config,
        fallback_callable=fallback,
    )

    blocks = coordinator.chunk_text("print('hello')", "test.py", "hash")

    assert blocks == block_extractor._result.blocks
    file_processor.validate_file.assert_called_once_with("test.py")
    error_handler.handle_error.assert_not_called()


def test_chunk_text_invalid_file_triggers_fallback(config, fallback):
    coordinator, file_processor, error_handler, _ = _create_coordinator(
        config,
        file_validator=False,
        fallback_callable=fallback,
    )

    blocks = coordinator.chunk_text("text", "filtered.py", "hash")

    assert len(blocks) == 1
    assert blocks[0].type == "fallback"
    file_processor.validate_file.assert_called_once()
    error_handler.handle_error.assert_not_called()


def test_chunk_text_extraction_failure_uses_fallback(config, fallback):
    extraction_result = _StubExtractionResult([], success=False)
    error_handler = Mock()
    coordinator, file_processor, _, _ = _create_coordinator(
        config,
        extraction_result=extraction_result,
        error_handler=error_handler,
        fallback_callable=fallback,
    )

    blocks = coordinator.chunk_text("text", "file.py", "hash")

    assert blocks[0].type == "fallback"
    file_processor.validate_file.assert_called_once()
    error_handler.handle_error.assert_not_called()


def test_chunk_text_exception_is_reported(config, fallback):
    class _FailingExtractor:
        def extract_blocks_from_root_node(self, *args, **kwargs):
            raise TreeSitterError("boom")

    error_handler = Mock()
    coordinator, file_processor, _, _ = _create_coordinator(
        config,
        extraction_result=None,
        error_handler=error_handler,
        fallback_callable=fallback,
    )
    coordinator._block_extractor = _FailingExtractor()

    blocks = coordinator.chunk_text("text", "file.py", "hash")

    assert blocks[0].type == "fallback"
    error_handler.handle_error.assert_called_once()
    args, kwargs = error_handler.handle_error.call_args
    assert "tree_sitter_coordinator" in args[1].component
    file_processor.validate_file.assert_called_once()
