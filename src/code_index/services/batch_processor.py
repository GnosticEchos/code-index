"""
TreeSitterBatchProcessor service for batch processing operations.

This service handles batch processing logic extracted from
TreeSitterChunkingStrategy, including language grouping and optimization.
"""

import time
import logging
import threading
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..config import Config
from ..models import CodeBlock
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity

# Set up logging for batch processing
batch_logger = logging.getLogger('code_index.batch_processor')

@dataclass
class BatchProcessingResult:
    """Result of batch processing operation."""
    results: Dict[str, List[CodeBlock]]
    success: bool
    processed_files: int
    failed_files: int
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    performance_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}

class TreeSitterBatchProcessor:
    """
    Service for processing multiple files efficiently in batches.

    Handles:
    - Language-based file grouping
    - Batch optimization and resource management
    - Parallel processing coordination
    - Error handling and recovery
    - Performance monitoring and optimization
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
        self.error_handler =error_handler or ErrorHandler()
        self.debug_enabled = getattr(config, "tree_sitter_debug_logging", False)

        # Performance optimization settings
        self.parallel_processing_enabled = getattr(config, "parallel_processing", True)
        self.max_workers = getattr(config, "max_parallel_workers", min(4, (os.cpu_count() or 1) * 2))
        self.chunk_size = getattr(config, "chunk_size", 65536)
        self.memory_limit_mb = getattr(config, "memory_limit_mb", 500)
        
        # Read monitoring configuration settings
        monitoring_config = getattr(config, "monitoring", {})
        self.enable_performance_tracking = monitoring_config.get("enable_performance_tracking", False)
        self.log_mmap_metrics = monitoring_config.get("log_mmap_metrics", False)
        self.log_resource_usage = monitoring_config.get("log_resource_usage", False)
        self.log_per_file_metrics = monitoring_config.get("log_per_file_metrics", False)
        self.log_memory_usage = monitoring_config.get("log_memory_usage", False)
        self.log_mmap_statistics = monitoring_config.get("log_mmap_statistics", False)
        self.log_cache_performance = monitoring_config.get("log_cache_performance", False)
        self.log_cache_efficiency = monitoring_config.get("log_cache_efficiency", False)
        self.enable_detailed_logging = monitoring_config.get("enable_detailed_logging", False)
        self.performance_report_interval = monitoring_config.get("performance_report_interval", 30)
        self.log_file_processing_times = monitoring_config.get("log_file_processing_times", False)
        self.track_cross_platform_compatibility = monitoring_config.get("track_cross_platform_compatibility", False)
        
        # Performance metrics
        self.performance_metrics = {
            'total_batches_processed': 0,
            'total_files_processed': 0,
            'total_processing_time_ms': 0,
            'average_processing_time_per_file_ms': 0,
            'parallel_processing_efficiency': 0,
            'memory_usage_optimization': 0
        }

        # Use dependency injection for services (for test compatibility)
        from ..services.file_processor import TreeSitterFileProcessor
        from ..services.resource_manager import TreeSitterResourceManager
        from ..services.block_extractor import TreeSitterBlockExtractor

        self.file_processor = file_processor or TreeSitterFileProcessor(config, error_handler=error_handler)
        self.resource_manager = resource_manager or TreeSitterResourceManager(config, error_handler)
        self.block_extractor = block_extractor or TreeSitterBlockExtractor(config, error_handler)

    def process_batch(self, files: List[Dict[str, Any]]) -> BatchProcessingResult:
        """
        Process multiple files efficiently by grouping by language with parallel processing support.

        Args:
            files: List of file dictionaries with 'file_path', 'text', 'file_hash' keys

        Returns:
            BatchProcessingResult with processing results
        """
        start_time = time.time()
        start_memory = self._get_memory_usage_mb() if self.log_memory_usage else 0
        
        try:
            results = {}
            processed_files = 0
            failed_files = 0

            # Group files by language for efficient processing
            language_groups = self.group_by_language(files)
            
            batch_logger.info(f"Processing batch with {len(files)} files in {len(language_groups)} language groups")

            # Log initial memory usage if enabled
            if self.log_memory_usage:
                current_memory = self._get_memory_usage_mb()
                batch_logger.info(f"Initial memory usage: {current_memory:.2f} MB")

            # Process each language group with parallel processing if enabled
            if self.parallel_processing_enabled and len(files) > 5:
                group_results = self._process_language_groups_parallel(language_groups)
            else:
                group_results = self._process_language_groups_sequential(language_groups)

            # Aggregate results
            for group_result in group_results:
                results.update(group_result.results)
                processed_files += group_result.processed_files
                failed_files += group_result.failed_files

            # Update performance metrics
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(len(files), processing_time, len(language_groups))

            # Log final memory usage if enabled
            if self.log_memory_usage:
                end_memory = self._get_memory_usage_mb()
                memory_delta = end_memory - start_memory
                batch_logger.info(f"Memory usage - Start: {start_memory:.2f} MB, End: {end_memory:.2f} MB, Delta: {memory_delta:.2f} MB")

            batch_logger.info(
                f"Batch processing completed: {processed_files} files processed, "
                f"{failed_files} failed in {processing_time:.2f}ms "
                f"(avg: {processing_time/len(files):.2f}ms per file)"
            )

            return BatchProcessingResult(
                results=results,
                success=True,
                processed_files=processed_files,
                failed_files=failed_files,
                metadata={
                    "language_groups": len(language_groups),
                    "total_files": len(files),
                    "grouping_method": "language_based",
                    "parallel_processing": self.parallel_processing_enabled,
                    "processing_time_ms": processing_time,
                    "memory_usage_mb": end_memory if self.log_memory_usage else None,
                    "memory_delta_mb": memory_delta if self.log_memory_usage else None
                },
                performance_metrics=self._get_current_performance_metrics()
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
            
            batch_logger.error(f"Batch processing failed: {e}")

            return BatchProcessingResult(
                results={},
                success=False,
                processed_files=0,
                failed_files=len(files),
                error_message=error_response.message,
                metadata={"batch_error": str(e)},
                performance_metrics={"error": str(e)}
            )

    def _process_language_groups_parallel(self, language_groups: Dict[str, List[Dict[str, Any]]]) -> List[BatchProcessingResult]:
        """
        Process language groups in parallel using ThreadPoolExecutor.
        
        Args:
            language_groups: Dictionary mapping language keys to file lists
            
        Returns:
            List of BatchProcessingResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all language group processing tasks
            future_to_language = {
                executor.submit(self._process_language_group, language_key, language_files): language_key
                for language_key, language_files in language_groups.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_language):
                language_key = future_to_language[future]
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per group
                    results.append(result)
                    batch_logger.info(f"Parallel processing completed for {language_key}: {result.processed_files} files")
                except Exception as e:
                    error_context = ErrorContext(
                        component="batch_processor",
                        operation="parallel_language_group_processing",
                        additional_data={"language": language_key}
                    )
                    error_response = self.error_handler.handle_error(
                        e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
                    )
                    
                    # Fallback to individual processing for failed group
                    language_files = language_groups[language_key]
                    fallback_result = self._process_individual_files(language_files)
                    results.append(fallback_result)
                    
                    if self.debug_enabled:
                        print(f"Warning: Parallel processing failed for {language_key}: {error_response.message}")
        
        return results

    def _process_language_groups_sequential(self, language_groups: Dict[str, List[Dict[str, Any]]]) -> List[BatchProcessingResult]:
        """
        Process language groups sequentially (fallback for small batches or when parallel processing is disabled).
        
        Args:
            language_groups: Dictionary mapping language keys to file lists
            
        Returns:
            List of BatchProcessingResult objects
        """
        results = []
        
        for language_key, language_files in language_groups.items():
            try:
                result = self._process_language_group(language_key, language_files)
                results.append(result)
                batch_logger.info(f"Sequential processing completed for {language_key}: {result.processed_files} files")
            except Exception as e:
                error_context = ErrorContext(
                    component="batch_processor",
                    operation="sequential_language_group_processing",
                    additional_data={"language": language_key}
                )
                error_response = self.error_handler.handle_error(
                    e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
                )
                
                # Fallback to individual processing
                fallback_result = self._process_individual_files(language_files)
                results.append(fallback_result)
                
                if self.debug_enabled:
                    print(f"Warning: Sequential processing failed for {language_key}: {error_response.message}")
        
        return results

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

                # Handle files with unknown or text/plain language
                if language_key is None or language_key == 'text/plain':
                    if "unknown" not in language_groups:
                        language_groups["unknown"] = []
                    language_groups["unknown"].append(file_info)
                else:
                    if language_key not in language_groups:
                        language_groups[language_key] = []
                    language_groups[language_key].append(file_info)

            batch_logger.info(f"Grouped {len(files)} files into {len(language_groups)} language groups")
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
        Optimize configuration for batch processing with memory and performance considerations.

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
                "parallel_processing": self.parallel_processing_enabled,
                "memory_optimization": True,
                "chunk_size": self.chunk_size
            }

            # Language-specific optimizations
            if language_key == 'rust':
                # More conservative settings for Rust
                base_config.update({
                    "max_blocks_per_file": 30,
                    "timeout_multiplier": 0.8,
                    "resource_sharing": True,
                    "memory_optimization": True
                })
            elif language_key in ['javascript', 'typescript']:
                # Optimized settings for JS/TS
                base_config.update({
                    "max_blocks_per_file": 50,
                    "timeout_multiplier": 1.1,
                    "memory_optimization": True
                })
            elif language_key == 'python':
                # Balanced settings for Python
                base_config.update({
                    "max_blocks_per_file": 40,
                    "timeout_multiplier": 1.0,
                    "memory_optimization": True
                })

            # Batch size optimizations
            if file_count > 10:
                base_config.update({
                    "parallel_processing": True,
                    "timeout_multiplier": 1.2,  # Allow more time for large batches
                    "memory_optimization": True
                })
            
            if file_count > 50:
                base_config.update({
                    "max_blocks_per_file": min(base_config["max_blocks_per_file"], 25),
                    "chunk_size": min(self.chunk_size, 32768)  # Smaller chunks for memory efficiency
                })

            batch_logger.debug(f"Optimized config for {language_key} ({file_count} files): {base_config}")
            return base_config

        except Exception as e:
            if self.debug_enabled:
                print(f"Error optimizing batch config: {e}")
            return {
                "max_blocks_per_file": getattr(self.config, "tree_sitter_max_blocks_per_file", 100),
                "timeout_multiplier": 1.0,
                "resource_sharing": True,
                "parallel_processing": self.parallel_processing_enabled,
                "memory_optimization": True,
                "chunk_size": self.chunk_size
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
            file_metrics = []

            # Optimize configuration for this batch
            batch_config = self.optimize_batch_config(language_key, len(language_files))

            # Get shared resources for this language
            resources = self._acquire_shared_resources(language_key)

            # Process each file in the group with memory optimization
            for file_info in language_files:
                file_start_time = time.time()
                try:
                    # Log MMAP statistics if enabled
                    if self.log_mmap_statistics:
                        self._log_mmap_statistics(file_info['file_path'], len(file_info.get('text', '')))
                    
                    # Check memory usage before processing
                    if self._should_optimize_memory():
                        self.resource_manager.cleanup_all()
                    
                    blocks = self._process_single_file_with_resources(
                        file_info, language_key, resources, batch_config
                    )

                    if blocks:
                        results[file_info['file_path']] = blocks
                        processed_files += 1
                        
                        # Log per-file metrics if enabled
                        if self.log_per_file_metrics:
                            file_processing_time = (time.time() - file_start_time) * 1000
                            file_size = len(file_info.get('text', ''))
                            block_count = len(blocks)
                            batch_logger.info(
                                f"File processed: {file_info['file_path']} - "
                                f"Time: {file_processing_time:.2f}ms, "
                                f"Size: {file_size} chars, "
                                f"Blocks: {block_count}"
                            )
                            file_metrics.append({
                                'file_path': file_info['file_path'],
                                'processing_time_ms': file_processing_time,
                                'file_size_chars': file_size,
                                'block_count': block_count
                            })
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
                    "batch_config": batch_config,
                    "parallel_processing": self.parallel_processing_enabled,
                    "file_metrics": file_metrics if self.log_per_file_metrics else None
                }
            )

        except Exception as e:
            if self.debug_enabled:
                print(f"Error processing language group {language_key}: {e}")
            raise

    def _should_optimize_memory(self) -> bool:
        """
        Determine if memory optimization is needed based on current usage.
        
        Returns:
            True if memory optimization should be performed
        """
        try:
            import psutil
            process = psutil.Process()
            memory_percent = process.memory_percent()
            return memory_percent > 80.0  # Optimize if memory usage > 80%
        except Exception:
            return False

    def _update_performance_metrics(self, file_count: int, processing_time: float, language_groups: int):
        """
        Update performance metrics after batch processing.
        
        Args:
            file_count: Number of files processed
            processing_time: Total processing time in milliseconds
            language_groups: Number of language groups
        """
        self.performance_metrics['total_batches_processed'] += 1
        
        # Avoid division by zero
        if file_count > 0:
            self.performance_metrics['total_files_processed'] += file_count
            self.performance_metrics['total_processing_time_ms'] += processing_time
            
            # Calculate average processing time per file
            self.performance_metrics['average_processing_time_per_file_ms'] = (
                self.performance_metrics['total_processing_time_ms'] / self.performance_metrics['total_files_processed']
            )
        
        # Calculate parallel processing efficiency
        if self.parallel_processing_enabled and file_count > 5:
            # Estimate sequential processing time (rough approximation)
            estimated_sequential_time = processing_time * 1.5  # Assume 50% overhead for parallel processing
            if estimated_sequential_time > 0:
                efficiency = (estimated_sequential_time - processing_time) / estimated_sequential_time * 100
                self.performance_metrics['parallel_processing_efficiency'] = max(0, efficiency)
        
        batch_logger.info(
            f"Performance metrics updated: avg {self.performance_metrics['average_processing_time_per_file_ms']:.2f}ms/file, "
            f"parallel efficiency: {self.performance_metrics['parallel_processing_efficiency']:.1f}%"
        )

    def _get_current_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return dict(self.performance_metrics)

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

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert bytes to MB
        except Exception:
            return 0.0

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
                "resource_sharing": True,
                "memory_optimization": True
            })
        elif strategy == "speed":
            optimized.update({
                "max_blocks_per_file": min(optimized.get("max_blocks_per_file", 100), 30),
                "timeout_multiplier": 1.2,
                "parallel_processing": True,
                "memory_optimization": True
            })

        return optimized

    def _log_mmap_statistics(self, file_path: str, file_size: int):
        """Log MMAP statistics for file processing."""
        if self.log_mmap_statistics:
            batch_logger.info(
                f"MMAP Statistics for {file_path}: "
                f"File size: {file_size} bytes, "
                f"MMAP enabled: {getattr(self.config, 'use_mmap_file_reading', False)}, "
                f"Min size threshold: {getattr(self.config, 'mmap_min_file_size_bytes', 65536)} bytes"
            )

    def process_files(self, file_paths: List[str]) -> BatchProcessingResult:
        """
        Process multiple files by reading their content and converting to batch format.

        Args:
            file_paths: List of file paths to process

        Returns:
            BatchProcessingResult with processing results
        """
        start_time = time.time()
        
        try:
            files = []

            for file_path in file_paths:
                try:
                    # Use file processing service for memory-optimized file reading
                    from ..file_processing import FileProcessingService
                    file_service = FileProcessingService(self.error_handler)
                    
                    # Read file content using the file processing service
                    content = file_service.load_file_with_encoding(file_path)

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
                metadata={"files_error": str(e)},
                performance_metrics={"error": str(e)}
            )