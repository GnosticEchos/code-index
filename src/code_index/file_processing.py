"""
File processing utilities for the code index tool.
"""
import os
import chardet
import psutil
import time
from typing import List, Dict, Any, Optional, Iterator, Set, Callable
from pathlib import Path
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class FileProcessingService:
    """
    Centralized service for file processing operations.

    This class consolidates file loading, validation, and processing logic
    that was previously scattered across multiple modules.
    """

    def __init__(self, error_handler: ErrorHandler):
        """
        Initialize the FileProcessingService.

        Args:
            error_handler: ErrorHandler instance for structured error handling
        """
        self.error_handler = error_handler
        # Add chunking configuration
        self.default_chunk_size = 64 * 1024  # 64KB default chunk size
        self.large_file_threshold = 256 * 1024  # 256KB threshold for large files
        self.streaming_threshold = 1024 * 1024  # 1MB threshold for streaming

    def load_file_with_encoding(self, file_path: str, encoding: Optional[str] = None) -> str:
        """
        Load a file with automatic encoding detection and fallback strategies.

        Args:
            file_path: Path to the file to load
            encoding: Optional specific encoding to use

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read due to permissions
            UnicodeDecodeError: If file cannot be decoded with any encoding
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="load_file_with_encoding",
            file_path=file_path
        )

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Get file size for optimization
            file_size = os.path.getsize(file_path)

            # Use memory mapping for large files
            if file_size > 1024 * 1024:  # 1MB threshold
                return self._read_large_file(file_path, encoding)
            else:
                return self._read_file_with_encoding_detection(file_path, encoding)

        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "file_loading")
            raise e
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            raise e

    def _read_file_with_encoding_detection(self, file_path: str, encoding: Optional[str] = None) -> str:
        """Read file with automatic encoding detection."""
        try:
            # Try specified encoding first
            if encoding:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()

            # Try UTF-8 first (most common)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                pass

            # Detect encoding using chardet if available
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected_encoding = None
                if chardet is not None:
                    detected = chardet.detect(raw_data)
                    detected_encoding = detected.get('encoding')
 
                if detected_encoding:
                    with open(file_path, 'r', encoding=detected_encoding) as f:
                        return f.read()
 
            # Final fallback to latin-1
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end,
                                   f"Failed to decode file {file_path} with any encoding")

    def _read_large_file(self, file_path: str, encoding: Optional[str] = None) -> str:
        """Read large files efficiently using memory mapping."""
        try:
            import mmap

            with open(file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    if encoding:
                        return mm.read().decode(encoding)
                    else:
                        # Try UTF-8 first
                        try:
                            return mm.read().decode('utf-8')
                        except UnicodeDecodeError:
                            # Detect encoding for large files (if chardet available)
                            sample = mm.read(1024)  # Read first 1KB for detection
                            detected_encoding = None
                            if chardet is not None:
                                detected = chardet.detect(sample)
                                detected_encoding = detected.get('encoding')
                            if not detected_encoding:
                                detected_encoding = 'utf-8'
                            mm.seek(0)  # Reset to beginning
                            return mm.read().decode(detected_encoding)

        except ImportError:
            # Fallback to traditional reading if mmap not available
            return self._read_file_with_encoding_detection(file_path, encoding)

    def load_file_with_chunking(self, file_path: str, chunk_size: Optional[int] = None, 
                              encoding: Optional[str] = None, progress_callback: Optional[Callable] = None) -> Iterator[Dict[str, Any]]:
        """
        Load a large file in chunks for progressive processing.
        
        Args:
            file_path: Path to the file to load
            chunk_size: Size of each chunk in bytes (default: 64KB)
            encoding: Optional specific encoding to use
            progress_callback: Optional callback for progress updates
            
        Yields:
            Dictionary with chunk data, metadata, and progress info
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="load_file_with_chunking",
            file_path=file_path
        )
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
                
            file_size = os.path.getsize(file_path)
            chunk_size = chunk_size or self.default_chunk_size
            
            # Use different strategies based on file size
            if file_size <= self.large_file_threshold:
                # Small file - load entirely
                content = self.load_file_with_encoding(file_path, encoding)
                yield {
                    "chunk_index": 0,
                    "chunk_data": content,
                    "chunk_size": len(content),
                    "total_size": file_size,
                    "is_complete": True,
                    "progress": 100.0
                }
            else:
                # Large file - process in chunks
                yield from self._process_file_in_chunks(file_path, file_size, chunk_size, encoding, progress_callback)
                
        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "chunked_loading")
            yield {
                "chunk_index": -1,
                "error": str(e),
                "error_response": error_response,
                "success": False
            }

    def _process_file_in_chunks(self, file_path: str, file_size: int, chunk_size: int, 
                               encoding: Optional[str], progress_callback: Optional[Callable]) -> Iterator[Dict[str, Any]]:
        """Process a large file in chunks with streaming."""
        try:
            # Detect encoding first if not provided
            if not encoding:
                encoding = self._detect_file_encoding(file_path)
            
            chunk_index = 0
            bytes_processed = 0
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                        
                    chunk_bytes = len(chunk_data.encode(encoding, errors='replace'))
                    bytes_processed += chunk_bytes
                    progress = (bytes_processed / file_size) * 100
                    
                    yield {
                        "chunk_index": chunk_index,
                        "chunk_data": chunk_data,
                        "chunk_size": len(chunk_data),
                        "total_size": file_size,
                        "is_complete": bytes_processed >= file_size,
                        "progress": progress,
                        "encoding": encoding
                    }
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(chunk_index, bytes_processed, file_size, progress)
                    
                    chunk_index += 1
                    
                    # Check for memory usage and yield control
                    if chunk_index % 10 == 0:  # Every 10 chunks
                        import gc
                        gc.collect()
                        
        except Exception as e:
            yield {
                "chunk_index": -1,
                "error": str(e),
                "success": False
            }

    def _detect_file_encoding(self, file_path: str) -> str:
        """Detect file encoding using chardet or fallback methods."""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)  # Read first 4KB for detection
                
            if chardet is not None:
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8')
                if encoding:
                    return encoding
                    
            # Fallback to UTF-8
            return 'utf-8'
            
        except Exception:
            return 'utf-8'

    def stream_process_large_file(self, file_path: str, processor_callback: Callable, 
                                 chunk_size: Optional[int] = None, encoding: Optional[str] = None) -> Dict[str, Any]:
        """
        Stream process a large file with custom processor callback.
        
        Args:
            file_path: Path to the file
            processor_callback: Function to process each chunk
            chunk_size: Size of each chunk
            encoding: File encoding
            
        Returns:
            Dictionary with processing results and statistics
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="stream_process_large_file",
            file_path=file_path
        )
        
        results = {
            "file_path": file_path,
            "chunks_processed": 0,
            "total_size": 0,
            "processing_time_ms": 0,
            "errors": [],
            "success": True
        }
        
        start_time = time.time()
        
        try:
            file_size = os.path.getsize(file_path)
            results["total_size"] = file_size
            
            # Process file in chunks
            for chunk_info in self.load_file_with_chunking(file_path, chunk_size, encoding):
                if "error" in chunk_info:
                    results["errors"].append(chunk_info["error"])
                    results["success"] = False
                    continue
                    
                if chunk_info["is_complete"] and chunk_info["chunk_index"] == 0:
                    # Small file processed entirely
                    chunk_result = processor_callback(chunk_info["chunk_data"], 0, True)
                    results["chunks_processed"] += 1
                    results["processing_results"] = chunk_result
                else:
                    # Large file chunk
                    chunk_result = processor_callback(
                        chunk_info["chunk_data"], 
                        chunk_info["chunk_index"], 
                        chunk_info["is_complete"]
                    )
                    results["chunks_processed"] += 1
                    
                    # Store chunk results
                    if "chunk_results" not in results:
                        results["chunk_results"] = []
                    results["chunk_results"].append({
                        "chunk_index": chunk_info["chunk_index"],
                        "result": chunk_result,
                        "chunk_size": chunk_info["chunk_size"]
                    })
                    
        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "stream_processing")
            results["errors"].append(str(e))
            results["success"] = False
            
        finally:
            results["processing_time_ms"] = (time.time() - start_time) * 1000
            
        return results

    def get_optimal_chunk_size(self, file_size: int, language: Optional[str] = None) -> int:
        """
        Get optimal chunk size based on file size and language.
        
        Args:
            file_size: Size of the file in bytes
            language: Optional language hint for optimization
            
        Returns:
            Optimal chunk size in bytes
        """
        # Base chunk sizes for different file size categories
        if file_size < 1024 * 1024:  # < 1MB
            return 64 * 1024  # 64KB
        elif file_size < 10 * 1024 * 1024:  # < 10MB
            return 128 * 1024  # 128KB
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            return 256 * 1024  # 256KB
        else:  # > 100MB
            return 512 * 1024  # 512KB
            
        # Language-specific optimizations
        if language:
            language_chunk_sizes = {
                'python': 64 * 1024,      # Python files tend to be smaller
                'javascript': 128 * 1024, # JS files can be larger
                'typescript': 128 * 1024,
                'java': 256 * 1024,       # Java files are often larger
                'cpp': 256 * 1024,
                'rust': 128 * 1024,
                'go': 128 * 1024,
                'text': 32 * 1024,        # Text files can use smaller chunks
                'markdown': 32 * 1024,
                'json': 64 * 1024,
                'xml': 128 * 1024,
                'yaml': 32 * 1024
            }
            return language_chunk_sizes.get(language, self.default_chunk_size)
            
        return self.default_chunk_size

    def process_file_with_memory_optimization(self, file_path: str, processor: Callable, 
                                            max_memory_usage_mb: int = 100) -> Dict[str, Any]:
        """
        Process a file with memory usage optimization.
        
        Args:
            file_path: Path to the file
            processor: Function to process the file content
            max_memory_usage_mb: Maximum memory usage in MB
            
        Returns:
            Dictionary with processing results and memory usage stats
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="process_file_with_memory_optimization",
            file_path=file_path
        )
        
        results = {
            "file_path": file_path,
            "success": False,
            "memory_usage_mb": 0,
            "peak_memory_mb": 0,
            "processing_time_ms": 0,
            "strategy_used": "unknown"
        }
        
        start_time = time.time()
        
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            file_size = os.path.getsize(file_path)
            
            # Choose processing strategy based on file size and memory constraints
            if file_size > max_memory_usage_mb * 1024 * 1024:  # File larger than memory limit
                results["strategy_used"] = "streaming_chunked"
                # Use streaming with very small chunks
                chunk_size = min(32 * 1024, self.get_optimal_chunk_size(file_size))
                stream_results = self.stream_process_large_file(
                    file_path, processor, chunk_size
                )
                results.update(stream_results)
            elif file_size > self.streaming_threshold:
                results["strategy_used"] = "chunked_processing"
                # Use normal chunked processing
                chunk_size = self.get_optimal_chunk_size(file_size)
                stream_results = self.stream_process_large_file(
                    file_path, processor, chunk_size
                )
                results.update(stream_results)
            else:
                results["strategy_used"] = "standard_loading"
                # Use standard loading for smaller files
                content = self.load_file_with_encoding(file_path)
                processing_result = processor(content, 0, True)
                results["processing_results"] = processing_result
                results["success"] = True
                
            # Measure final memory usage
            final_memory = process.memory_info().rss / (1024 * 1024)  # MB
            results["memory_usage_mb"] = final_memory - initial_memory
            results["peak_memory_mb"] = max(initial_memory, final_memory) - initial_memory
            
        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "memory_optimized_processing")
            results["error"] = str(e)
            results["error_response"] = error_response
            
        finally:
            results["processing_time_ms"] = (time.time() - start_time) * 1000
            
        return results

    def process_file_list(self, file_paths: List[str], operation: str = "processing") -> Iterator[Dict[str, Any]]:
        """
        Process a list of files with error handling and progress tracking.

        Args:
            file_paths: List of file paths to process
            operation: Description of the operation being performed

        Yields:
            Dictionary with file_path, success status, and result/error info
        """
        for file_path in file_paths:
            error_context = ErrorContext(
                component="file_processing",
                operation=operation,
                file_path=file_path
            )

            try:
                # Validate file path
                if not self.validate_file_path(file_path):
                    yield {
                        "file_path": file_path,
                        "success": False,
                        "error": "Invalid file path",
                        "error_type": "validation"
                    }
                    continue

                # Load file content
                content = self.load_file_with_encoding(file_path)

                yield {
                    "file_path": file_path,
                    "success": True,
                    "content": content,
                    "size": len(content),
                    "error": None
                }

            except Exception as e:
                error_response = self.error_handler.handle_file_error(e, error_context, operation)
                yield {
                    "file_path": file_path,
                    "success": False,
                    "error": str(e),
                    "error_response": error_response,
                    "error_type": "processing"
                }

    def process_files_batch(self, file_list: List[Dict[str, Any]], operation: str = "batch_processing",
                          progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Process a batch of files and return results as a dictionary.

        Args:
            file_list: List of file dictionaries with file_path, abs_path, and rel_path keys
            operation: Description of the operation being performed
            progress_callback: Optional callback function to track progress

        Returns:
            Dictionary mapping file paths to processing results
        """
        results = {}
        
        # Convert file list to simple file paths for processing
        file_paths = [file_info['file_path'] for file_info in file_list]
        
        # Process files using existing method
        for result in self.process_file_list(file_paths, operation):
            file_path = result['file_path']
            # Add status field for backward compatibility
            result['status'] = 'success' if result['success'] else 'error'
            results[file_path] = result

            # Call progress callback if provided
            if progress_callback:
                progress_callback(file_path, result)

        return results

    def validate_file_paths(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Validate a list of file paths.

        Args:
            file_paths: List of file paths to validate

        Returns:
            Dictionary with validation results and statistics
        """
        results = {
            "valid": [],
            "invalid": [],
            "errors": [],
            "total": len(file_paths),
            "valid_count": 0,
            "invalid_count": 0
        }

        for file_path in file_paths:
            error_context = ErrorContext(
                component="file_processing",
                operation="validate_file_paths",
                file_path=file_path
            )

            try:
                if self.validate_file_path(file_path):
                    results["valid"].append(file_path)
                    results["valid_count"] += 1
                else:
                    results["invalid"].append(file_path)
                    results["invalid_count"] += 1

            except Exception as e:
                error_response = self.error_handler.handle_file_error(e, error_context, "path_validation")
                results["errors"].append({
                    "file_path": file_path,
                    "error": str(e),
                    "error_response": error_response
                })
                results["invalid_count"] += 1

        return results

    def load_exclude_list(self, workspace_path: str, exclude_files_path: str | None, operation: str = "load_exclude_list") -> Set[str]:
        """
        Load exclude list as normalized relative paths from workspace root.

        Args:
            workspace_path: Root directory of the workspace
            exclude_files_path: Path to the exclude file (can be relative or absolute)
            operation: Description of the operation for error context

        Returns:
            Set of normalized relative paths to exclude
        """
        error_context = ErrorContext(
            component="file_processing",
            operation=operation,
            file_path=exclude_files_path,
            additional_data={"workspace_path": workspace_path}
        )

        try:
            excluded: Set[str] = set()
            if not exclude_files_path:
                return excluded

            # Resolve exclude file path
            exclude_file_path = exclude_files_path
            if not os.path.isabs(exclude_file_path):
                exclude_file_path = os.path.join(workspace_path, exclude_file_path)

            # Validate exclude file path
            if not self.validate_file_path(exclude_file_path):
                return excluded

            # Load file content
            content = self.load_file_with_encoding(exclude_file_path)

            # Process lines
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Normalize path relative to workspace
                if os.path.isabs(line):
                    rel = os.path.relpath(line, workspace_path)
                else:
                    rel = line

                # Normalize glob patterns and paths
                rel = os.path.normpath(rel)
                # Handle glob patterns by removing leading * from extensions
                if rel.startswith('*.'):
                    rel = rel[1:]
                # Add trailing slash for directory patterns (those ending with /)
                if line.endswith('/') or line.endswith('/*'):
                    rel = rel + '/'

                excluded.add(rel)

            return excluded

        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, operation)
            return set()

    def load_path_list(self, path_file: str, workspace: str, operation: str = "load_path_list") -> List[str]:
        """
        Load newline-separated paths from a file and normalize to relative paths from workspace.

        Args:
            path_file: Path to the file containing newline-separated paths
            workspace: Workspace root directory for path normalization
            operation: Description of the operation for error context

        Returns:
            List of normalized relative paths
        """
        error_context = ErrorContext(
            component="file_processing",
            operation=operation,
            file_path=path_file,
            additional_data={"workspace": workspace}
        )

        try:
            # Validate file path
            if not self.validate_file_path(path_file):
                return []

            # Load file content
            content = self.load_file_with_encoding(path_file)

            # Process lines
            results: List[str] = []
            for line in content.splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue

                # Normalize path relative to workspace
                if os.path.isabs(s):
                    rel = os.path.relpath(s, workspace)
                else:
                    rel = s
                results.append(os.path.normpath(rel))

            return results

        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, operation)
            return []

    def validate_file_path(self, file_path: str) -> bool:
        """
        Validate a single file path.

        Args:
            file_path: File path to validate

        Returns:
            True if path is valid and accessible
        """
        try:
            # Check if path is not empty
            if not file_path or not file_path.strip():
                return False

            # Normalize path
            normalized_path = os.path.normpath(file_path)

            # Check if file exists
            if not os.path.exists(normalized_path):
                return False

            # Check if it's actually a file (not a directory)
            if not os.path.isfile(normalized_path):
                return False

            # Check if file is readable
            if not os.access(normalized_path, os.R_OK):
                return False

            # Check file size (not empty)
            if os.path.getsize(normalized_path) == 0:
                return False

            return True

        except Exception:
            return False

    def batch_process_files(self, file_paths: List[str], batch_size: int = 10,
                          operation: str = "batch_processing") -> Dict[str, Any]:
        """
        Process files in batches with progress tracking and error aggregation.

        Args:
            file_paths: List of file paths to process
            batch_size: Number of files to process in each batch
            operation: Description of the operation being performed

        Returns:
            Dictionary with batch processing results and statistics
        """
        results = {
            "batches": [],
            "total_files": len(file_paths),
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "errors": []
        }

        # Process files in batches
        for i in range(0, len(file_paths), batch_size):
            batch_files = file_paths[i:i + batch_size]
            batch_number = i // batch_size + 1

            error_context = ErrorContext(
                component="file_processing",
                operation=operation,
                additional_data={"batch_number": batch_number, "batch_size": len(batch_files)}
            )

            try:
                batch_results = list(self.process_file_list(batch_files, operation))

                batch_summary = {
                    "batch_number": batch_number,
                    "files_processed": len(batch_results),
                    "successful": sum(1 for r in batch_results if r["success"]),
                    "failed": sum(1 for r in batch_results if not r["success"]),
                    "results": batch_results
                }

                results["batches"].append(batch_summary)
                results["processed_files"] += len(batch_results)
                results["successful_files"] += batch_summary["successful"]
                results["failed_files"] += batch_summary["failed"]

            except Exception as e:
                error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.HIGH)
                results["errors"].append({
                    "batch_number": batch_number,
                    "error": str(e),
                    "error_response": error_response,
                    "files": batch_files
                })

        return results

    def load_workspace_list(self, workspace_list_file: str, operation: str = "load_workspace_list") -> List[str]:
        """
        Load workspace list file containing directory paths. Skip empty lines and comments.

        Args:
            workspace_list_file: Path to the workspace list file
            operation: Description of the operation for error context

        Returns:
            List of valid workspace directory paths
        """
        error_context = ErrorContext(
            component="file_processing",
            operation=operation,
            file_path=workspace_list_file
        )

        workspaces: List[str] = []
        try:
            # Validate file path
            if not workspace_list_file or not self.validate_file_path(workspace_list_file):
                return workspaces

            # Load file content
            content = self.load_file_with_encoding(workspace_list_file)

            # Process lines
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Validate that the path exists and is a directory
                if os.path.exists(line) and os.path.isdir(line):
                    workspaces.append(os.path.normpath(line))
                else:
                    error_msg = f"Warning: Invalid directory path in workspace list: {line}"
                    error_response = self.error_handler.handle_file_error(
                        FileNotFoundError(error_msg),
                        error_context,
                        operation
                    )
                    print(error_msg)
        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, operation)
            print(f"Error reading workspace list file {workspace_list_file}: {e}")

        return workspaces

    def is_binary_file(self, file_path: str) -> bool:
        """
        Check if a file is binary by reading a sample of its content.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is binary, False otherwise
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="is_binary_file",
            file_path=file_path
        )

        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\x00" in chunk:
                    return True
                # Check if the chunk contains mostly printable characters
                printable_chars = sum(1 for byte in chunk if 32 <= byte <= 126 or byte in (9, 10, 13))
                return printable_chars / len(chunk) < 0.7 if chunk else False
        except (IOError, OSError) as e:
            # If we can't read the file, assume it's binary
            error_response = self.error_handler.handle_file_error(e, error_context, "binary_check")
            return True
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return True

    def augment_extensions_with_pygments(self, base_extensions: List[str]) -> List[str]:
        """
        Augment a list of extensions using Pygments lexers' filename patterns.

        If Pygments is unavailable, returns base_extensions and prints a warning.

        Args:
            base_extensions: List of base extensions to augment

        Returns:
            Augmented list of extensions
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="augment_extensions_with_pygments",
            additional_data={"base_extensions_count": len(base_extensions)}
        )

        try:
            from pygments.lexers import get_all_lexers  # type: ignore
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.DEPENDENCY, ErrorSeverity.LOW)
            print("Auto-extensions requested but 'pygments' is not installed; proceeding with configured extensions only.")
            return base_extensions

        discovered: Set[str] = set()
        try:
            for lex in get_all_lexers():
                # get_all_lexers() yields tuples: (name, aliases, filenames, mimetypes)
                filenames = []
                if len(lex) >= 3 and lex[2]:
                    filenames = lex[2]
                for pattern in filenames:
                    # Common patterns like "*.py", "*.rs", "*.vue"
                    if isinstance(pattern, str) and pattern.startswith("*."):
                        ext = pattern[1:].lower()  # ".*" -> ".ext"
                        discovered.add(ext)
        except Exception as e:
            # If anything goes wrong, don't fail hard; just return base list
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.DEPENDENCY, ErrorSeverity.LOW)
            return list(dict.fromkeys([e.lower() for e in base_extensions]))

        merged = list(dict.fromkeys([e.lower() for e in (list(base_extensions) + list(discovered))]))
        return merged

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file to hash

        Returns:
            SHA256 hash of the file as a hexadecimal string
        """
        import hashlib
        
        error_context = ErrorContext(
            component="file_processing",
            operation="get_file_hash",
            file_path=file_path
        )
        
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "hash_calculation")
            raise e

    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of supported file extensions
        """
        return [
            ".rs", ".ts", ".vue", ".surql", ".js", ".py", ".jsx", ".tsx",
            ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php",
            ".swift", ".kt", ".scala", ".dart", ".lua", ".pl", ".pm",
            ".t", ".r", ".sql", ".html", ".css", ".scss", ".sass", ".less",
            ".md", ".markdown", ".rst", ".txt", ".json", ".xml", ".yaml", ".yml"
        ]

    def is_supported_file(self, file_path: str) -> bool:
        """
        Check if a file is supported based on its extension.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is supported, False otherwise
        """
        import os
        
        error_context = ErrorContext(
            component="file_processing",
            operation="is_supported_file",
            file_path=file_path
        )
        
        try:
            _, ext = os.path.splitext(file_path.lower())
            return ext in self.get_supported_extensions()
        except Exception as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "file_type_check")
            return False

    def load_gitignore_patterns(self, directory: str) -> Set[str]:
        """
        Load .gitignore patterns from a directory.

        Args:
            directory: Directory to load .gitignore patterns from

        Returns:
            Set of .gitignore patterns
        """
        import os
        from typing import Set
        
        error_context = ErrorContext(
            component="file_processing",
            operation="load_gitignore_patterns",
            additional_data={"directory": directory}
        )
        
        patterns = set()
        gitignore_path = os.path.join(directory, ".gitignore")
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.add(line)
            except (IOError, OSError) as e:
                error_response = self.error_handler.handle_file_error(e, error_context, "gitignore_loading")
                pass
        return patterns

    def matches_pattern(self, file_path: str, patterns: Set[str], root_dir: str) -> bool:
        """
        Check if a file path matches any of the ignore patterns.

        Args:
            file_path: Path to the file to check
            patterns: Set of ignore patterns
            root_dir: Root directory for relative path calculation

        Returns:
            True if the file path matches any pattern, False otherwise
        """
        import os
        import fnmatch
        
        error_context = ErrorContext(
            component="file_processing",
            operation="matches_pattern",
            file_path=file_path,
            additional_data={"root_dir": root_dir, "pattern_count": len(patterns)}
        )
        
        try:
            relative_path = os.path.relpath(file_path, root_dir)
            
            for pattern in patterns:
                # Handle absolute patterns
                if pattern.startswith("/"):
                    if relative_path.startswith(pattern[1:]):
                        return True
                # Handle patterns with wildcards
                elif "*" in pattern or "?" in pattern:
                    if fnmatch.fnmatch(relative_path, pattern):
                        return True
                # Handle directory patterns
                elif pattern.endswith("/"):
                    if relative_path.startswith(pattern) or relative_path.startswith(pattern[:-1]):
                        return True
                # Handle exact matches
                else:
                    if relative_path == pattern:
                        return True
                    # Check if it's a directory match
                    if relative_path.startswith(pattern + os.sep):
                        return True
            return False
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return False

    def get_file_size(self, file_path: str) -> int:
        """
        Get the size of a file in bytes.

        Args:
            file_path: Path to the file

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be accessed
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="get_file_size",
            file_path=file_path
        )

        try:
            return os.path.getsize(file_path)
        except (FileNotFoundError, PermissionError, OSError) as e:
            error_response = self.error_handler.handle_file_error(e, error_context, "file_size_check")
            return 0
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return 0

    def filter_files_by_criteria(self, file_paths: List[str], criteria: Dict[str, Any]) -> List[str]:
        """
        Filter files based on various criteria (size, extension, exclude patterns, etc.).

        Args:
            file_paths: List of file paths to filter
            criteria: Dictionary containing filtering criteria:
                - workspace_path: Workspace root for relative path calculations
                - exclude_patterns: Set of patterns to exclude
                - extensions: Set of allowed extensions
                - max_file_size: Maximum file size in bytes
                - skip_binary: Whether to skip binary files

        Returns:
            List of filtered file paths
        """
        error_context = ErrorContext(
            component="file_processing",
            operation="filter_files_by_criteria",
            additional_data={"file_count": len(file_paths), "criteria": criteria}
        )

        try:
            filtered_files = []
            workspace_path = criteria.get("workspace_path", "")
            exclude_patterns = criteria.get("exclude_patterns", set())
            extensions = criteria.get("extensions", set())
            max_file_size = criteria.get("max_file_size", float('inf'))
            skip_binary = criteria.get("skip_binary", True)

            for file_path in file_paths:
                try:
                    # Convert to absolute path if relative
                    abs_path = file_path if os.path.isabs(file_path) else os.path.join(workspace_path, file_path)

                    # Check if file exists
                    if not os.path.exists(abs_path):
                        continue

                    # Normalize relative path for comparison
                    rel_path = os.path.normpath(os.path.relpath(abs_path, workspace_path))

                    # Check exclude patterns
                    if rel_path in exclude_patterns:
                        continue

                    # Check file size
                    try:
                        if os.path.getsize(abs_path) > max_file_size:
                            continue
                    except (OSError, IOError):
                        continue

                    # Check extension filtering
                    _, ext = os.path.splitext(abs_path.lower())
                    if extensions and ext not in extensions:
                        continue

                    # Check if binary file
                    if skip_binary and self.is_binary_file(abs_path):
                        continue

                    filtered_files.append(abs_path)

                except Exception as e:
                    # Log individual file errors but continue processing
                    error_response = self.error_handler.handle_file_error(e, error_context, "file_filtering")
                    continue

            return filtered_files

        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.MEDIUM)
            return []

    def normalize_path(self, path: str) -> str:
        """
        Normalize a path to use forward slashes.

        Args:
            path: Path to normalize

        Returns:
            Normalized path with forward slashes
        """
        from pathlib import Path

        error_context = ErrorContext(
            component="file_processing",
            operation="normalize_path",
            additional_data={"input_path": path}
        )

        try:
            return str(Path(path).as_posix())
        except Exception as e:
            error_response = self.error_handler.handle_error(e, error_context, ErrorCategory.FILE_SYSTEM, ErrorSeverity.LOW)
            return path