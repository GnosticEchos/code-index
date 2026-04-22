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
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from .config import Config
from .models import CodeBlock
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from .utils import split_content


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
                    # Split oversized chunks to preserve all data
                    if len(chunk_content) > self.max_block_chars:
                        content_chunks = split_content(chunk_content, self.max_block_chars)
                        end_line = chunk_start_line + len(current_chunk_lines) - 1
                        
                        # Generate parent block ID for linking split parts
                        parent_id = f"chunk_{chunk_start_line}_{end_line}"
                        
                        for chunk_idx, chunk_part in enumerate(content_chunks):
                            segment_hash = file_hash + str(chunk_start_line) + f"_part{chunk_idx + 1}"
                            block = CodeBlock(
                                file_path=file_path,
                                identifier=None,
                                type="chunk",
                                start_line=chunk_start_line,
                                end_line=end_line,
                                content=chunk_part,
                                file_hash=file_hash,
                                segment_hash=segment_hash,
                                split_index=chunk_idx + 1,  # 1-based
                                split_total=len(content_chunks),
                                parent_block_id=parent_id,
                            )
                            blocks.append(block)
                    else:
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
        self.max_block_chars = 6000  # Default max chars for token chunks

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
                # Split oversized chunks to preserve all data
                if len(chunk) > self.max_block_chars:
                    content_chunks = split_content(chunk, self.max_block_chars)
                    
                    # Generate parent block ID for linking split parts
                    parent_id = f"token_chunk_{start_line}_{end_line}"
                    
                    for chunk_idx, chunk_part in enumerate(content_chunks):
                        segment_hash = file_hash + f"{start_line}_part{chunk_idx + 1}"
                        blocks.append(
                            CodeBlock(
                                file_path=file_path,
                                identifier=None,
                                type="chunk",
                                start_line=start_line,
                                end_line=end_line,
                                content=chunk_part,
                                file_hash=file_hash,
                                segment_hash=segment_hash,
                                split_index=chunk_idx + 1,  # 1-based
                                split_total=len(content_chunks),
                                parent_block_id=parent_id,
                            )
                        )
                else:
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

# Remove the standalone function as it's causing circular imports
# This function is not used and creates circular dependency issues

class TreeSitterChunkingStrategy(ChunkingStrategy):
    """Tree-sitter chunking strategy backed by `TreeSitterChunkCoordinator`."""

    def __init__(
        self,
        config: Config,
        file_processor=None,
        resource_manager=None,
        block_extractor=None,
        query_executor=None,
        config_manager=None,
        batch_processor=None,
        error_handler=None,
    ):
        super().__init__(config)
        self.error_handler = error_handler or ErrorHandler()
        self.min_block_chars = getattr(config, "tree_sitter_min_block_chars", 50)

        from .services.treesitter.tree_sitter_coordinator import TreeSitterChunkCoordinator

        self._coordinator = TreeSitterChunkCoordinator(
            config,
            error_handler=self.error_handler,
            file_processor=file_processor,
            resource_manager=resource_manager,
            block_extractor=block_extractor,
            query_executor=query_executor,
            config_manager=config_manager,
            batch_processor=batch_processor,
            fallback_callable=self._line_fallback,
        )

        self._config = config
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

    def _debug(self, msg: str) -> None:
        """Conditional Tree-sitter debug logging."""
        if self._debug_enabled:
            import logging

            logging.getLogger("code_index.treesitter").debug(msg)

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks using Tree-sitter with composition pattern."""
        return self._coordinator.chunk_text(text, file_path, file_hash)

    def chunk_batch(self, files: List[Dict[str, Any]]) -> Dict[str, List[CodeBlock]]:
        """Process multiple files efficiently using batch processor."""
        batch_processor = self._coordinator.batch_processor
        return batch_processor.process_batch(files).results

    def cleanup_resources(self):
        """Clean up all resources using resource manager."""
        return self._coordinator.cleanup_resources()

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            self.cleanup_resources()
        except Exception:
            pass  # Ignore errors during destruction

    def _line_fallback(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

    @property
    def coordinator(self):
        """Access the underlying Tree-sitter coordinator."""
        return self._coordinator
