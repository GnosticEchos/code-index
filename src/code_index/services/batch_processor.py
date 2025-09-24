"""
TreeSitterBatchProcessor service for batch processing operations.

This service handles batch processing logic extracted from
TreeSitterChunkingStrategy, including language grouping and optimization.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..config import Config
from ..models import CodeBlock
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


@dataclass
class BatchProcessingResult:
    """Result of batch processing operation."""
    results: Dict[str, List[CodeBlock]]
    success: bool
    processed_files: int
    failed_files: int
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TreeSitterBatchProcessor:
    """
    Service for processing multiple files efficiently in batches.

    Handles:
    - Language-based file grouping
    - Batch optimization and resource management
    - Parallel processing coordination
    - Error handling and recovery
    """

    def __init__(
        self,
        config: Config,
        error_handler: Optional[ErrorHandler] = None,
        file_processor=None,
        resource_manager=None,
        block_extractor=None
    ):
        """
        Initialize the TreeSitterBatchProcessor.

        Args:
            config: Configuration object
            error_handler: Optional error handler instance
            file_processor: Optional TreeSitterFileProcessor service instance
            resource_manager: Optional TreeSitterResourceManager service instance
            block_extractor: Optional TreeSitterBlockExtractor service instance
        """
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        self.debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

        # Use dependency injection for services (for test compatibility)
        from ..services.file_processor import TreeSitterFileProcessor
        from ..services.resource_manager import TreeSitterResourceManager
        from ..services.block_extractor import TreeSitterBlockExtractor

        self.file_processor = file_processor or TreeSitterFileProcessor(config, error_handler=error_handler)
        self.resource_manager = resource_manager or TreeSitterResourceManager(config, error_handler)
        self.block_extractor = block_extractor or TreeSitterBlockExtractor(config, error_handler)

    def process_batch(self, files: List[Dict[str, Any]]) -> BatchProcessingResult:
        """
        Process multiple files efficiently by grouping by language.

        Args:
            files: List of file dictionaries with 'file_path', 'text', 'file_hash' keys

        Returns:
            BatchProcessingResult with processing results
        """
        try:
            results = {}
            processed_files = 0
            failed_files = 0

            # Group files by language for efficient processing
            language_groups = self.group_by_language(files)

            # Process each language group
            for language_key, language_files in language_groups.items():
                try:
                    group_result = self._process_language_group(language_key, language_files)
                    results.update(group_result.results)
                    processed_files += group_result.processed_files
                    failed_files += group_result.failed_files
                except Exception as e:
                    error_context = ErrorContext(
                        component="batch_processor",
                        operation="process_language_group",
                        additional_data={"language": language_key}
                    )
                    error_response = self.error_handler.handle_error(
                        e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
                    )
                    if self.debug_enabled:
                        print(f"Warning: {error_response.message}")

                    # Fallback to individual processing
                    fallback_result = self._process_individual_files(language_files)
                    results.update(fallback_result.results)
                    processed_files += fallback_result.processed_files
                    failed_files += fallback_result.failed_files

            return BatchProcessingResult(
                results=results,
                success=True,
                processed_files=processed_files,
                failed_files=failed_files,
                metadata={
                    "language_groups": len(language_groups),
                    "total_files": len(files),
                    "grouping_method": "language_based"
                }
            )

        except Exception as e:
            error_context = ErrorContext(
                component="batch_processor",
                operation="process_batch"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.HIGH
            )
            if self.debug_enabled:
                print(f"Warning: {error_response.message}")

            return BatchProcessingResult(
                results={},
                success=False,
                processed_files=0,
                failed_files=len(files),
                error_message=error_response.message,
                metadata={"batch_error": str(e)}
            )

    def group_by_language(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group files by language for efficient processing.

        Args:
            files: List of file dictionaries

        Returns:
            Dictionary mapping language keys to file lists
        """
        try:
            language_groups = {}

            for file_info in files:
                file_path = file_info['file_path']
                language_key = self._get_language_key_for_path(file_path)

                if language_key:
                    if language_key not in language_groups:
                        language_groups[language_key] = []
                    language_groups[language_key].append(file_info)
                else:
                    # Handle files with unknown language
                    if "unknown" not in language_groups:
                        language_groups["unknown"] = []
                    language_groups["unknown"].append(file_info)

            return language_groups

        except Exception as e:
            error_context = ErrorContext(
                component="batch_processor",
                operation="group_by_language"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.LOW
            )
            if self.debug_enabled:
                print(f"Warning: {error_response.message}")

            # Fallback to single-file groups
            return {f"file_{i}": [file_info] for i, file_info in enumerate(files)}

    def optimize_batch_config(self, language_key: str, file_count: int) -> Dict[str, Any]:
        """
        Optimize configuration for batch processing.

        Args:
            language_key: Language identifier
            file_count: Number of files in batch

        Returns:
            Dictionary with optimized configuration
        """
        try:
            base_config = {
                "max_blocks_per_file": getattr(self.config, "tree_sitter_max_blocks_per_file", 100),
                "timeout_multiplier": 1.0,
                "resource_sharing": True,
                "parallel_processing": False
            }

            # Language-specific optimizations
            if language_key == 'rust':
                # More conservative settings for Rust
                base_config.update({
                    "max_blocks_per_file": 30,
                    "timeout_multiplier": 0.8,
                    "resource_sharing": True
                })

            # Batch size optimizations
            if file_count > 10:
                base_config.update({
                    "parallel_processing": True,
                    "timeout_multiplier": 1.2  # Allow more time for large batches
                })

            return base_config

        except Exception as e:
            if self.debug_enabled:
                print(f"Error optimizing batch config: {e}")
            return {
                "max_blocks_per_file": getattr(self.config, "tree_sitter_max_blocks_per_file", 100),
                "timeout_multiplier": 1.0,
                "resource_sharing": True,
                "parallel_processing": False
            }

    def _process_language_group(
        self,
        language_key: str,
        language_files: List[Dict[str, Any]]
    ) -> BatchProcessingResult:
        """Process all files in a language group efficiently."""
        try:
            results = {}
            processed_files = 0
            failed_files = 0

            # Optimize configuration for this batch
            batch_config = self.optimize_batch_config(language_key, len(language_files))

            # Get shared resources for this language
            resources = self._acquire_shared_resources(language_key)

            # Process each file in the group
            for file_info in language_files:
                try:
                    blocks = self._process_single_file_with_resources(
                        file_info, language_key, resources, batch_config
                    )

                    if blocks:
                        results[file_info['file_path']] = blocks
                        processed_files += 1
                    else:
                        # Fallback to individual processing
                        fallback_blocks = self._process_file_individually(file_info)
                        results[file_info['file_path']] = fallback_blocks
                        processed_files += 1

                except Exception as e:
                    error_context = ErrorContext(
                        component="batch_processor",
                        operation="process_language_group_file",
                        file_path=file_info['file_path'],
                        metadata={"language": language_key}
                    )
                    error_response = self.error_handler.handle_error(
                        e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
                    )
                    if self.debug_enabled:
                        print(f"Warning: {error_response.message}")

                    failed_files += 1

                    # Fallback to line-based chunking
                    from ..chunking import LineChunkingStrategy
                    fallback_blocks = LineChunkingStrategy(self.config).chunk(
                        file_info['text'], file_info['file_path'], file_info['file_hash']
                    )
                    results[file_info['file_path']] = fallback_blocks

            return BatchProcessingResult(
                results=results,
                success=True,
                processed_files=processed_files,
                failed_files=failed_files,
                metadata={
                    "language": language_key,
                    "files_processed": len(language_files),
                    "batch_config": batch_config
                }
            )

        except Exception as e:
            if self.debug_enabled:
                print(f"Error processing language group {language_key}: {e}")
            raise

    def _process_individual_files(self, files: List[Dict[str, Any]]) -> BatchProcessingResult:
        """Process files individually as fallback."""
        try:
            results = {}
            processed_files = 0
            failed_files = 0

            for file_info in files:
                try:
                    blocks = self._process_file_individually(file_info)
                    results[file_info['file_path']] = blocks
                    processed_files += 1
                except Exception as e:
                    failed_files += 1
                    # Final fallback to line-based chunking
                    from ..chunking import LineChunkingStrategy
                    results[file_info['file_path']] = LineChunkingStrategy(self.config).chunk(
                        file_info['text'], file_info['file_path'], file_info['file_hash']
                    )

            return BatchProcessingResult(
                results=results,
                success=True,
                processed_files=processed_files,
                failed_files=failed_files,
                metadata={"processing_method": "individual"}
            )

        except Exception as e:
            raise

    def _process_file_individually(self, file_info: Dict[str, Any]) -> List[CodeBlock]:
        """Process a single file using Tree-sitter."""
        from ..chunking import TreeSitterChunkingStrategy
        strategy = TreeSitterChunkingStrategy(
            self.config,
            error_handler=self.error_handler,
            file_processor=self.file_processor,
            resource_manager=self.resource_manager,
            block_extractor=self.block_extractor
        )
        return strategy.chunk(file_info['text'], file_info['file_path'], file_info['file_hash'])

    def _process_single_file_with_resources(
        self,
        file_info: Dict[str, Any],
        language_key: str,
        resources: Dict[str, Any],
        batch_config: Dict[str, Any]
    ) -> List[CodeBlock]:
        """Process a single file using shared resources."""
        try:
            # Use the TreeSitterChunkingStrategy with shared resources
            from ..chunking import TreeSitterChunkingStrategy
            strategy = TreeSitterChunkingStrategy(
                self.config,
                error_handler=self.error_handler,
                file_processor=self.file_processor,
                resource_manager=self.resource_manager,
                block_extractor=self.block_extractor
            )

            # Temporarily adjust configuration for batch processing
            original_max_blocks = getattr(self.config, "tree_sitter_max_blocks_per_file", 100)
            setattr(self.config, "tree_sitter_max_blocks_per_file", batch_config["max_blocks_per_file"])

            try:
                blocks = strategy.chunk(file_info['text'], file_info['file_path'], file_info['file_hash'])
                return blocks
            finally:
                # Restore original configuration
                setattr(self.config, "tree_sitter_max_blocks_per_file", original_max_blocks)

        except Exception as e:
            if self.debug_enabled:
                print(f"Error processing file with shared resources: {e}")
            raise

    def _acquire_shared_resources(self, language_key: str) -> Dict[str, Any]:
        """Acquire shared resources for a language group."""
        try:
            resources = {}

            # Get parser for language
            from ..parser_manager import TreeSitterParserManager
            parser_manager = TreeSitterParserManager(self.config, self.error_handler)
            parser = parser_manager.get_parser(language_key)
            if parser:
                resources["parser"] = parser

            # Get query for language
            from ..query_manager import TreeSitterQueryManager
            query_manager = TreeSitterQueryManager(self.config, self.error_handler)
            query = query_manager.get_compiled_query(language_key)
            if query:
                resources["query"] = query

            return resources

        except Exception as e:
            if self.debug_enabled:
                print(f"Error acquiring shared resources for {language_key}: {e}")
            return {}

    def _get_language_key_for_path(self, file_path: str) -> Optional[str]:
        """Map file extension to Tree-sitter language key."""
        try:
            from ..language_detection import LanguageDetector
            language_detector = LanguageDetector(self.config, self.error_handler)
            return language_detector.detect_language(file_path)
        except Exception:
            return None

    # Missing methods for test compatibility
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
                "max_blocks_per_file": min(optimized.get("max_blocks_per_file", 100), 50),
                "timeout_multiplier": 0.8,
                "resource_sharing": True
            })
        elif strategy == "speed":
            optimized.update({
                "max_blocks_per_file": min(optimized.get("max_blocks_per_file", 100), 30),
                "timeout_multiplier": 1.2,
                "parallel_processing": True
            })

        return optimized

    def process_files(self, file_paths: List[str]) -> BatchProcessingResult:
        """
        Process multiple files by reading their content and converting to batch format.

        Args:
            file_paths: List of file paths to process

        Returns:
            BatchProcessingResult with processing results
        """
        try:
            files = []

            for file_path in file_paths:
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Generate simple hash based on content
                    import hashlib
                    file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

                    files.append({
                        'text': content,
                        'file_path': file_path,
                        'file_hash': file_hash
                    })

                except Exception as e:
                    error_context = ErrorContext(
                        component="batch_processor",
                        operation="process_files",
                        file_path=file_path
                    )
                    error_response = self.error_handler.handle_error(
                        e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW
                    )
                    if self.debug_enabled:
                        print(f"Warning: Could not read file {file_path}: {error_response.message}")

            # Process the files using the batch processor
            return self.process_batch(files)

        except Exception as e:
            error_context = ErrorContext(
                component="batch_processor",
                operation="process_files"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.HIGH
            )
            if self.debug_enabled:
                print(f"Warning: {error_response.message}")

            return BatchProcessingResult(
                results={},
                success=False,
                processed_files=0,
                failed_files=len(file_paths),
                error_message=error_response.message,
                metadata={"files_error": str(e)}
            )