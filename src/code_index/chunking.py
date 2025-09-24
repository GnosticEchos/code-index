"""
Tree-sitter based chunking strategy for code indexing.
"""

# Tree-sitter Error Classes
class TreeSitterError(Exception):
    """Base exception for Tree-sitter related errors."""
    pass

class TreeSitterParserError(TreeSitterError):
    """Exception raised when Tree-sitter parser encounters an error."""
    pass

class TreeSitterQueryError(TreeSitterError):
    """Exception raised when Tree-sitter query compilation or execution fails."""
    pass

class TreeSitterLanguageError(TreeSitterError):
    """Exception raised when Tree-sitter language loading fails."""
    pass

class TreeSitterFileTooLargeError(TreeSitterError):
    """Exception raised when a file exceeds the maximum size for Tree-sitter processing."""
    pass
"""
Chunking strategies for the code index tool.
"""
import os
import traceback
import weakref
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from weakref import WeakValueDictionary

from code_index.config import Config
from code_index.models import CodeBlock
from code_index.treesitter_queries import get_queries_for_language as get_ts_queries
from code_index.errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity, error_handler

class TreeSitterError(Exception):
    """Base exception for Tree-sitter related errors."""
    pass


class TreeSitterParserError(TreeSitterError):
    """Exception raised when Tree-sitter parser fails to load."""
    pass


class TreeSitterQueryError(TreeSitterError):
    """Exception raised when Tree-sitter query execution fails."""
    pass


class TreeSitterLanguageError(TreeSitterError):
    """Exception raised when language is not supported by Tree-sitter."""
    pass


class TreeSitterFileTooLargeError(TreeSitterError):
    """Exception raised when file is too large for Tree-sitter parsing."""
    pass


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into a list of CodeBlock objects."""
        pass


class LineChunkingStrategy(ChunkingStrategy):
    """Chunking strategy based on lines."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.min_block_chars = 50
        self.max_block_chars = 1000
        self.max_chars_tolerance_factor = 1.15

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks based on lines."""
        lines = text.split("\n")
        blocks: List[CodeBlock] = []
        current_chunk_lines: List[str] = []
        current_chunk_length = 0
        chunk_start_line = 1

        for i, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for newline
            current_chunk_length += line_length
            current_chunk_lines.append(line)

            if (
                current_chunk_length >= self.max_block_chars * self.max_chars_tolerance_factor
                or i == len(lines) - 1
            ):
                chunk_content = "\n".join(current_chunk_lines)
                if len(chunk_content.strip()) >= self.min_block_chars:
                    segment_hash = file_hash + str(chunk_start_line)
                    block = CodeBlock(
                        file_path=file_path,
                        identifier=None,
                        type="chunk",
                        start_line=chunk_start_line,
                        end_line=chunk_start_line + len(current_chunk_lines) - 1,
                        content=chunk_content,
                        file_hash=file_hash,
                        segment_hash=segment_hash,
                    )
                    blocks.append(block)

                current_chunk_lines = []
                current_chunk_length = 0
                chunk_start_line = i + 2  # Next line (1-indexed)

        return blocks


class TokenChunkingStrategy(ChunkingStrategy):
    """Chunking strategy based on tokens."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.min_block_chars = 50

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks based on tokens."""
        try:
            from langchain_text_splitters import TokenTextSplitter  # type: ignore

            chunk_size = int(getattr(self.config, "token_chunk_size", 1000) or 1000)
            chunk_overlap = int(getattr(self.config, "token_chunk_overlap", 200) or 200)
            splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks: List[str] = splitter.split_text(text)
            if not chunks:
                return []
            return self._map_chunks_with_lines(text, chunks, file_path, file_hash)
        except Exception as e:
            error_context = ErrorContext(
                component="chunking",
                operation="token_chunking",
                file_path=file_path
            )
            error_response = error_handler.handle_error(e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM)
            print(f"Warning: {error_response.message}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

    def _map_chunks_with_lines(
        self, original_text: str, chunks: List[str], file_path: str, file_hash: str
    ) -> List[CodeBlock]:
        """Approximate start_line/end_line mapping for token chunks."""
        blocks: List[CodeBlock] = []
        pos = 0
        consumed_lines = 1  # 1-indexed line counter when search fails
        for chunk in chunks:
            found_index = original_text.find(chunk, pos)
            if found_index != -1:
                start_line = original_text.count("\n", 0, found_index) + 1
                add_one = 0 if chunk.endswith("\n") else 1
                end_line = start_line + chunk.count("\n") + add_one - 1
                pos = found_index + max(1, len(chunk) - 1)
            else:
                start_line = consumed_lines
                add_one = 0 if chunk.endswith("\n") else 1
                end_line = start_line + chunk.count("\n") + add_one - 1
                consumed_lines = end_line + 1

            if len(chunk.strip()) >= self.min_block_chars:
                segment_hash = file_hash + f"{start_line}"
                blocks.append(
                    CodeBlock(
                        file_path=file_path,
                        identifier=None,
                        type="chunk",
                        start_line=start_line,
                        end_line=end_line,
                        content=chunk,
                        file_hash=file_hash,
                        segment_hash=segment_hash,
                    )
                )
        return blocks


class TreeSitterChunkingStrategy(ChunkingStrategy):
    """
    Refactored Tree-sitter chunking strategy using composition pattern.

    This version uses specialized services for file processing, resource management,
    block extraction, query execution, configuration management, and batch processing
    to achieve better separation of concerns and maintainability.
    """

    def __init__(
        self,
        config: Config,
        file_processor=None,
        resource_manager=None,
        block_extractor=None,
        query_executor=None,
        config_manager=None,
        batch_processor=None,
        error_handler=None
    ):
        """
        Initialize the TreeSitterChunkingStrategy with dependency injection.

        Args:
            config: Configuration object
            file_processor: Optional TreeSitterFileProcessor service instance
            resource_manager: Optional TreeSitterResourceManager service instance
            block_extractor: Optional TreeSitterBlockExtractor service instance
            query_executor: Optional TreeSitterQueryExecutor service instance
            config_manager: Optional TreeSitterConfigurationManager service instance
            batch_processor: Optional TreeSitterBatchProcessor service instance
            error_handler: Optional ErrorHandler instance
        """
        super().__init__(config)
        self.min_block_chars = 50

        # Use dependency injection for services
        from .services.file_processor import TreeSitterFileProcessor
        from .services.resource_manager import TreeSitterResourceManager
        from .services.block_extractor import TreeSitterBlockExtractor
        from .services.query_executor import TreeSitterQueryExecutor
        from .services.config_manager import TreeSitterConfigurationManager
        from .services.batch_processor import TreeSitterBatchProcessor
        from .errors import ErrorHandler

        self.file_processor = file_processor or TreeSitterFileProcessor(config, error_handler=error_handler)
        self.resource_manager = resource_manager or TreeSitterResourceManager(config, error_handler)
        self.block_extractor = block_extractor or TreeSitterBlockExtractor(config, error_handler)
        self.query_executor = query_executor or TreeSitterQueryExecutor(config, error_handler)
        self.config_manager = config_manager or TreeSitterConfigurationManager(config, error_handler)
        self.batch_processor = batch_processor or TreeSitterBatchProcessor(config, error_handler)
        self.error_handler = error_handler or ErrorHandler()

        # Debug logging
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

    def _debug(self, msg: str) -> None:
        """Conditional Tree-sitter debug logging."""
        try:
            if self._debug_enabled:
                print(f"TS-DEBUG: {msg}")
        except Exception:
            pass

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks using Tree-sitter with composition pattern."""
        try:
            # Validate file first
            if not self.file_processor.validate_file(file_path):
                self._debug(f"File validation failed for {file_path}")
                return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

            # Get language key
            language_key = self._get_language_key_for_path(file_path)
            if not language_key:
                self._debug(f"No language detected for {file_path}")
                return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

            # Apply language optimizations
            optimizations = self.config_manager.apply_language_optimizations(file_path, language_key)

            # Acquire resources
            resources = self.resource_manager.acquire_resources(language_key, "parser")

            # Parse text
            parser = resources.get("parser")
            if not parser:
                self._debug(f"Parser not available for {language_key}")
                return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

            tree = parser.parse(bytes(text, "utf8"))
            root_node = tree.root_node

            # Extract blocks
            extraction_result = self.block_extractor.extract_blocks(
                root_node, text, file_path, file_hash, language_key
            )

            if extraction_result.success and extraction_result.blocks:
                # Apply limits
                max_blocks = optimizations.get("max_blocks", 100)
                if len(extraction_result.blocks) > max_blocks:
                    extraction_result.blocks = extraction_result.blocks[:max_blocks]

                return extraction_result.blocks

            # Fallback to line-based chunking
            self._debug(f"Block extraction failed for {file_path}, using fallback")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

        except TreeSitterLanguageError as e:
            print(f"Note: Tree-sitter not suitable for {file_path}: {e}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except TreeSitterFileTooLargeError as e:
            print(f"Note: {e}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except TreeSitterError as e:
            error_context = ErrorContext(
                component="chunking",
                operation="tree_sitter_chunking",
                file_path=file_path
            )
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM)
            print(f"Warning: {error_response.message}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except Exception as e:
            error_context = ErrorContext(
                component="chunking",
                operation="tree_sitter_chunking",
                file_path=file_path
            )
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.PARSING, ErrorSeverity.HIGH)
            print(f"Warning: {error_response.message}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

    def chunk_batch(self, files: List[Dict[str, Any]]) -> Dict[str, List[CodeBlock]]:
        """Process multiple files efficiently using batch processor."""
        return self.batch_processor.process_batch(files).results

    def _get_language_key_for_path(self, file_path: str) -> Optional[str]:
        """Map file extension to Tree-sitter language key."""
        try:
            from .language_detection import LanguageDetector
            language_detector = LanguageDetector(self.config, self.error_handler)
            return language_detector.detect_language(file_path)
        except Exception:
            return None

    def cleanup_resources(self):
        """Clean up all resources using resource manager."""
        return self.resource_manager.cleanup_all()

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            self.cleanup_resources()
        except:
            pass  # Ignore errors during destruction

    # Missing methods for test compatibility
    def _ensure(self, condition: bool, message: str = "") -> None:
        """Ensure a condition is true, raise error if not."""
        if not condition:
            raise AssertionError(message or "Condition failed")

    def _group_by(self, items: list, key_func) -> dict:
        """Group items by a key function."""
        result = {}
        for item in items:
            key = key_func(item)
            if key not in result:
                result[key] = []
            result[key].append(item)
        return result

    def _optimize(self, config: dict, strategy: str = "default") -> dict:
        """Optimize configuration based on strategy."""
        optimized = dict(config)

        # Apply optimization strategies
        if strategy == "memory":
            optimized.update({
                "max_blocks": min(optimized.get("max_blocks", 100), 50),
                "timeout_multiplier": 0.8
            })
        elif strategy == "speed":
            optimized.update({
                "max_blocks": min(optimized.get("max_blocks", 100), 30),
                "timeout_multiplier": 1.2
            })

        return optimized

    def _should(self, condition_func, *args, **kwargs) -> bool:
        """Evaluate a condition function."""
        try:
            return condition_func(*args, **kwargs)
        except Exception:
            return False

    def _get_query(self, language_key: str):
        """Get query for language."""
        try:
            from .query_manager import TreeSitterQueryManager
            query_manager = TreeSitterQueryManager(self.config, self.error_handler)
            return query_manager.get_compiled_query(language_key)
        except Exception:
            return None

    def _should_process_file_for_treesitter(self, file_path: str) -> bool:
        """Check if file should be processed by Tree-sitter."""
        return self.file_processor.validate_file(file_path)

    def _get_queries_for_language(self, language_key: str) -> Optional[str]:
        """Get queries for a specific language."""
        try:
            from .treesitter_queries import get_queries_for_language
            return get_queries_for_language(language_key)
        except Exception:
            return None

    def _ensure_tree_sitter_version(self) -> None:
        """Ensure Tree-sitter version compatibility."""
        try:
            import tree_sitter
            # Check if basic Tree-sitter functionality is available
            if not hasattr(tree_sitter, 'Parser'):
                raise TreeSitterError("Tree-sitter Parser not available")
        except ImportError:
            raise TreeSitterError("Tree-sitter package not installed")
        except Exception as e:
            raise TreeSitterError(f"Tree-sitter version check failed: {e}")

    def _get_node_types_for_language(self, language_key: str) -> Optional[list]:
        """Get node types for a specific language."""
        try:
            from .services.config_manager import TreeSitterConfigurationManager
            config_manager = TreeSitterConfigurationManager(self.config, self.error_handler)
            return config_manager._get_node_types_for_language(language_key)
        except Exception:
            return None

    def _get_cached_query(self, language_key: str, query_key: str):
        """Get a cached query for a language."""
        try:
            from .services.config_manager import TreeSitterConfigurationManager
            config_manager = TreeSitterConfigurationManager(self.config, self.error_handler)
            return config_manager._get_cached_query(language_key, query_key)
        except Exception:
            return None
