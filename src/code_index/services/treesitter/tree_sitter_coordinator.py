"""Tree-sitter chunking coordinator.

This module centralizes the orchestration logic that wires together
Tree-sitter services for chunking operations. It was extracted from
`TreeSitterChunkingStrategy` to reduce class responsibilities and make
composition patterns clearer.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...config import Config
from ...errors import (
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
)

from ..._exceptions import (
    TreeSitterError,
    TreeSitterFileTooLargeError,
    TreeSitterLanguageError,
)
from ...models import CodeBlock


class TreeSitterChunkCoordinator:
    """Coordinate Tree-sitter services to produce code blocks."""

    def __init__(
        self,
        config: Config,
        error_handler: Optional[ErrorHandler] = None,
        *,
        file_processor=None,
        resource_manager=None,
        block_extractor=None,
        query_executor=None,
        config_manager=None,
        batch_processor=None,
        fallback_callable=None,
    ) -> None:
        self._config = config
        self._error_handler = error_handler or ErrorHandler()

        # Dependencies are injected lazily to preserve existing behaviour and
        # avoid circular import issues.
        self._file_processor = file_processor
        self._resource_manager = resource_manager
        self._block_extractor = block_extractor
        self._query_executor = query_executor
        self._config_manager = config_manager
        self._batch_processor = batch_processor
        self._fallback_callable = fallback_callable

        self._services_initialized = False
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

    # Public API ---------------------------------------------------------
    def chunk_text(
        self,
        text: str,
        file_path: str,
        file_hash: str,
    ) -> List[CodeBlock]:
        """Chunk text into Tree-sitter blocks using tree-sitter-language-pack."""

        try:
            self._ensure_services()
            assert self._block_extractor is not None

            if self._file_processor and not self._file_processor.validate_file(file_path):
                return self._fallback(text, file_path, file_hash)

            language_key = self.get_language_key(file_path)
            if not language_key:
                return self._fallback(text, file_path, file_hash)

            from tree_sitter_language_pack import get_language
            from tree_sitter import Parser

            ts_lang = get_language(language_key)
            parser = Parser()
            parser.language = ts_lang
            tree = parser.parse(text.encode("utf8"))

            extraction_result = self._block_extractor.extract_blocks_from_root_node(
                tree.root_node,
                text,
                file_path,
                file_hash,
                language_key,
                ts_lang=ts_lang,
            )
            extraction_result = self._normalize_result(extraction_result)

            if extraction_result.success and extraction_result.blocks:
                return extraction_result.blocks

            return self._fallback(text, file_path, file_hash)

        except TreeSitterLanguageError:
            return self._fallback(text, file_path, file_hash)
        except TreeSitterFileTooLargeError:
            return self._fallback(text, file_path, file_hash)
        except TreeSitterError as exc:
            error_context = ErrorContext(
                component="tree_sitter_coordinator",
                operation="chunk_text",
                file_path=file_path,
            )
            self._error_handler.handle_error(
                exc, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM,
            )
            return self._fallback(text, file_path, file_hash)
        except Exception as exc:  # noqa: BLE001
            error_context = ErrorContext(
                component="tree_sitter_coordinator",
                operation="chunk_text",
                file_path=file_path,
            )
            self._error_handler.handle_error(
                exc, error_context, ErrorCategory.PARSING, ErrorSeverity.HIGH,
            )
            return self._fallback(text, file_path, file_hash)

    # Helpers ------------------------------------------------------------
    def _ensure_services(self) -> None:
        if self._services_initialized:
            return

        from .treesitter_file_processor import TreeSitterFileProcessor
        from .resource_manager import TreeSitterResourceManager
        from .block_extractor import TreeSitterBlockExtractor
        from ..query.query_executor import TreeSitterQueryExecutor
        from ..command.config_manager import TreeSitterConfigurationManager
        from ..batch.batch_processor import TreeSitterBatchProcessor

        if self._file_processor is None:
            self._file_processor = TreeSitterFileProcessor(
                self._config, error_handler=self._error_handler
            )
        if self._resource_manager is None:
            self._resource_manager = TreeSitterResourceManager(
                self._config, self._error_handler
            )
        if self._block_extractor is None:
            self._block_extractor = TreeSitterBlockExtractor(
                self._config, self._error_handler
            )
        if self._query_executor is None:
            self._query_executor = TreeSitterQueryExecutor(
                self._config, self._error_handler
            )
        if self._config_manager is None:
            self._config_manager = TreeSitterConfigurationManager(
                self._config, self._error_handler
            )
        if self._batch_processor is None:
            self._batch_processor = TreeSitterBatchProcessor(
                self._config, self._error_handler
            )

        self._services_initialized = True

    def get_language_key(self, file_path: str) -> Optional[str]:
        try:
            from ...language_detection import LanguageDetector

            detector = LanguageDetector(self._config, self._error_handler)
            return detector.detect_language(file_path)
        except Exception:  # noqa: BLE001
            return None

    def get_queries_for_language(self, language_key: str):
        self._ensure_services()
        if hasattr(self._config_manager, "get_query_for_language"):
            return self._config_manager.get_query_for_language(language_key)
        return None

    def get_node_types_for_language(self, language_key: str) -> Optional[List[str]]:
        self._ensure_services()
        getter = getattr(self._config_manager, "_get_node_types_for_language", None)
        if callable(getter):
            return getter(language_key)
        return None

    def ensure_tree_sitter_version(self) -> Optional[Any]:
        self._ensure_services()
        if hasattr(self._resource_manager, "ensure_tree_sitter_version"):
            return self._resource_manager.ensure_tree_sitter_version()
        return None

    def _fallback(
        self,
        text: str,
        file_path: str,
        file_hash: str,
    ) -> List[CodeBlock]:
        if self._fallback_callable is not None:
            return self._fallback_callable(text, file_path, file_hash)
        from ...chunking import LineChunkingStrategy  # Local import to avoid circular dependency

        return LineChunkingStrategy(self._config).chunk(text, file_path, file_hash)

    @staticmethod
    def _normalize_result(result: Any) -> Any:
        """Ensure any legacy return types behave like ExtractionResult."""
        from .block_extractor import ExtractionResult

        if isinstance(result, list):
            return ExtractionResult(
                blocks=result,
                success=bool(result),
                metadata={"converted_from_list": True},
            )
        if not hasattr(result, "success"):
            return ExtractionResult(
                blocks=getattr(result, "blocks", []),
                success=bool(getattr(result, "blocks", [])),
                metadata={"fallback_conversion": True},
            )
        return result

    # Exposed for batch operations (TreeSitterChunkingStrategy compatibility)
    @property
    def batch_processor(self):
        self._ensure_services()
        return self._batch_processor

    def cleanup_resources(self) -> Optional[Dict[str, Any]]:
        if self._services_initialized and self._resource_manager:
            return self._resource_manager.cleanup_all()
        return None

    def should_process_file(self, file_path: str) -> bool:
        """Determine if Tree-sitter should process the given file."""
        self._ensure_services()
        processor = self._file_processor

        if hasattr(processor, "_should_process_file_for_treesitter"):
            return processor._should_process_file_for_treesitter(file_path)  # type: ignore[attr-defined]

        return processor.validate_file(file_path)
