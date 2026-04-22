"""
Batch scheduler module for coordinating batch processing operations.

This module handles language-based grouping and scheduling of batch operations.
"""

import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from ...constants import BATCH_TIMEOUT, MAX_WORKERS_DEFAULT, CHUNK_SIZE_DEFAULT


batch_logger = logging.getLogger('code_index.batch_scheduler')


class BatchScheduler:
    """
    Schedules and coordinates batch processing operations.
    
    Handles:
    - Language-based file grouping
    - Batch optimization
    - Parallel vs sequential processing decisions
    """
    
    def __init__(
        self,
        config,
        parallel_processing_enabled: bool = True,
        max_workers: int = MAX_WORKERS_DEFAULT,
        chunk_size: int = CHUNK_SIZE_DEFAULT
    ):
        self.config = config
        self.parallel_processing_enabled = parallel_processing_enabled
        self.max_workers = max_workers
        self.chunk_size = chunk_size
    
    def group_by_language(self, files: List[Dict[str, Any]], get_language_key_func) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group files by language for efficient processing.

        Args:
            files: List of file dictionaries
            get_language_key_func: Function to get language key for a file

        Returns:
            Dictionary mapping language keys to file lists
        """
        try:
            language_groups = {}

            for file_info in files:
                file_path = file_info['file_path']
                language_key = get_language_key_func(file_path)

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

        except Exception:
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
                "parallel_processing": self.parallel_processing_enabled,
                "memory_optimization": True,
                "chunk_size": self.chunk_size
            }

            # Language-specific optimizations
            if language_key == 'rust':
                base_config.update({
                    "max_blocks_per_file": 30,
                    "timeout_multiplier": 0.8,
                    "resource_sharing": True,
                    "memory_optimization": True
                })
            elif language_key in ['javascript', 'typescript']:
                base_config.update({
                    "max_blocks_per_file": 50,
                    "timeout_multiplier": 1.1,
                    "memory_optimization": True
                })
            elif language_key == 'python':
                base_config.update({
                    "max_blocks_per_file": 40,
                    "timeout_multiplier": 1.0,
                    "memory_optimization": True
                })

            # Batch size optimizations
            if file_count > 10:
                base_config.update({
                    "parallel_processing": True,
                    "timeout_multiplier": 1.2,
                    "memory_optimization": True
                })
            
            if file_count > 50:
                base_config.update({
                    "max_blocks_per_file": min(base_config["max_blocks_per_file"], 25),
                    "chunk_size": min(self.chunk_size, 32768)
                })

            return base_config

        except Exception:
            return {
                "max_blocks_per_file": getattr(self.config, "tree_sitter_max_blocks_per_file", 100),
                "timeout_multiplier": 1.0,
                "resource_sharing": True,
                "parallel_processing": self.parallel_processing_enabled,
                "memory_optimization": True,
                "chunk_size": self.chunk_size
            }
    
    def should_use_parallel(self, file_count: int) -> bool:
        """Determine if parallel processing should be used."""
        return self.parallel_processing_enabled and file_count > 5
    
    def create_thread_pool(self) -> ThreadPoolExecutor:
        """Create a thread pool executor for parallel processing."""
        return ThreadPoolExecutor(max_workers=self.max_workers)
    
    def process_groups_parallel(
        self,
        language_groups: Dict[str, List[Dict[str, Any]]],
        process_group_func,
        error_handler=None
    ) -> List:
        """
        Process language groups in parallel.
        
        Args:
            language_groups: Dictionary mapping language keys to file lists
            process_group_func: Function to process each language group
            error_handler: Optional error handler
            
        Returns:
            List of processing results
        """
        results = []
        
        with self.create_thread_pool() as executor:
            future_to_language = {
                executor.submit(process_group_func, language_key, language_files): language_key
                for language_key, language_files in language_groups.items()
            }
            
            for future in as_completed(future_to_language):
                language_key = future_to_language[future]
                try:
                    result = future.result(timeout=BATCH_TIMEOUT)
                    results.append(result)
                    batch_logger.info(f"Parallel processing completed for {language_key}: {result.processed_files}")
                except Exception as e:
                    from ...errors import ErrorContext, ErrorCategory, ErrorSeverity
                    if error_handler:
                        error_context = ErrorContext(
                            component="batch_scheduler",
                            operation="parallel_language_group_processing",
                            additional_data={"language": language_key}
                        )
                        error_handler.handle_error(
                            e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
                        )
                    
                    # Fallback to individual processing
                    fallback_result = process_group_func(language_key, language_groups[language_key])
                    results.append(fallback_result)
        
        return results
    
    def process_groups_sequential(
        self,
        language_groups: Dict[str, List[Dict[str, Any]]],
        process_group_func,
        error_handler=None
    ) -> List:
        """
        Process language groups sequentially.
        
        Args:
            language_groups: Dictionary mapping language keys to file lists
            process_group_func: Function to process each language group
            error_handler: Optional error handler
            
        Returns:
            List of processing results
        """
        results = []
        
        for language_key, language_files in language_groups.items():
            try:
                result = process_group_func(language_key, language_files)
                results.append(result)
            except Exception as e:
                from ...errors import ErrorContext, ErrorCategory, ErrorSeverity
                if error_handler:
                    error_context = ErrorContext(
                        component="batch_scheduler",
                        operation="sequential_language_group_processing",
                        additional_data={"language": language_key}
                    )
                    error_handler.handle_error(
                        e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
                    )
                
                fallback_result = process_group_func(language_key, language_files)
                results.append(fallback_result)
        
        return results
