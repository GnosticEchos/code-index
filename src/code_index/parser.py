"""
Code parser for the code index tool.
"""
import os
import mmap
import time
import logging
from typing import List, Dict, Any, Optional
from code_index.config import Config
from code_index.chunking import ChunkingStrategy
from code_index.models import CodeBlock
from code_index.file_processing import FileProcessingService
from code_index.errors import ErrorHandler

# Set up logging for mmap operations
mmap_logger = logging.getLogger('code_index.mmap')

class CodeParser:
    """Parses code files into blocks."""
    
    def __init__(self, config: Config, chunking_strategy: ChunkingStrategy):
        """Initialize code parser with configuration and a chunking strategy."""
        self.config = config
        self.chunking_strategy = chunking_strategy
        # Initialize mmap metrics tracking
        self.mmap_metrics = {
            'total_uses': 0,
            'successful_uses': 0,
            'failed_uses': 0,
            'fallback_uses': 0,
            'total_bytes_read': 0,
            'average_read_time_ms': 0,
            'cross_platform_compatibility': {}
        }
    
    def parse_file(self, file_path: str) -> List[CodeBlock]:
        """
        Parse a file into code blocks.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            List of CodeBlock objects
        """
        try:
            # Read file content using configured method
            content = self._read_file_content(file_path)
            
            # Calculate file hash
            file_processor = FileProcessingService(ErrorHandler("parser"))
            file_hash = file_processor.get_file_hash(file_path)
            
            # Choose chunking strategy
            return self.chunking_strategy.chunk(text=content, file_path=file_path, file_hash=file_hash)
        except Exception as e:
            print(f"Warning: Failed to parse file {file_path}: {e}")
            return []
    
    def _read_file_content(self, file_path: str) -> str:
        """
        Read file content using optimal method based on configuration and file size.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content as string
        """
        use_mmap = getattr(self.config, "use_mmap_file_reading", False)
        mmap_min_size = getattr(self.config, "mmap_min_file_size_bytes", 64 * 1024)
        
        if not use_mmap:
            return self._read_file_traditional(file_path)
        
        try:
            # Check file size to determine if mmap is beneficial
            file_size = os.path.getsize(file_path)
            if file_size < mmap_min_size:
                # For small files, traditional reading is more efficient
                return self._read_file_traditional(file_path)
            
            return self._read_file_with_mmap(file_path)
        except (OSError, ValueError) as e:
            # Fall back to traditional reading if file operations fail
            print(f"Warning: File size check failed for {file_path}, falling back to traditional reading: {e}")
            return self._read_file_traditional(file_path)
    
    def _read_file_traditional(self, file_path: str) -> str:
        """Read file content using traditional file reading."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"Warning: Traditional reading failed for {file_path}: {e}")
            return ""
    
    def _read_file_with_mmap(self, file_path: str) -> str:
        """
        Read file content using memory-mapped file reading with comprehensive validation and logging.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content as string
            
        Raises:
            OSError: If file cannot be opened or mapped
            ValueError: If file is empty
        """
        start_time = time.time()
        self.mmap_metrics['total_uses'] += 1
        
        try:
            # Cross-platform validation
            if not self._validate_mmap_compatibility():
                mmap_logger.warning(f"MMAP not compatible on this platform, falling back to traditional reading for {file_path}")
                self.mmap_metrics['failed_uses'] += 1
                self.mmap_metrics['fallback_uses'] += 1
                return self._read_file_traditional(file_path)
            
            with open(file_path, "rb") as f:
                # Get file size
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    return ""
                
                # Validate file size for mmap
                if file_size > 1024 * 1024 * 1024:  # 1GB limit for safety
                    mmap_logger.warning(f"File {file_path} too large for mmap ({file_size} bytes), using traditional reading")
                    self.mmap_metrics['fallback_uses'] += 1
                    return self._read_file_traditional(file_path)
                
                # Create memory map with proper error handling and validation
                try:
                    with mmap.mmap(f.fileno(), file_size, access=mmap.ACCESS_READ) as mm:
                        # Validate mmap creation
                        if mm.size() != file_size:
                            raise ValueError(f"Mmap size mismatch: expected {file_size}, got {mm.size()}")
                        
                        # Decode bytes to string with comprehensive error handling
                        try:
                            content = mm.read(file_size).decode('utf-8', errors='ignore')
                            
                            # Update metrics
                            read_time = (time.time() - start_time) * 1000
                            self.mmap_metrics['successful_uses'] += 1
                            self.mmap_metrics['total_bytes_read'] += file_size
                            
                            # Update average read time
                            if self.mmap_metrics['successful_uses'] == 1:
                                self.mmap_metrics['average_read_time_ms'] = read_time
                            else:
                                self.mmap_metrics['average_read_time_ms'] = (
                                    (self.mmap_metrics['average_read_time_ms'] * (self.mmap_metrics['successful_uses'] - 1) + read_time) 
                                    / self.mmap_metrics['successful_uses']
                                )
                            
                            # Log successful mmap operation
                            mmap_logger.info(
                                f"MMAP successful: {file_path} ({file_size} bytes, {read_time:.2f}ms, "
                                f"success rate: {self.get_mmap_success_rate():.1f}%)"
                            )
                            
                            return content
                            
                        except UnicodeDecodeError as decode_error:
                            mmap_logger.warning(f"Unicode decode error in mmap for {file_path}: {decode_error}")
                            self.mmap_metrics['failed_uses'] += 1
                            self.mmap_metrics['fallback_uses'] += 1
                            # Fall back to traditional reading with different encoding
                            return self._read_file_traditional(file_path)
                            
                except (mmap.error, OSError, ValueError) as mmap_error:
                    # mmap-specific errors with detailed logging
                    mmap_logger.error(f"MMAP failed for {file_path}: {mmap_error}")
                    self.mmap_metrics['failed_uses'] += 1
                    self.mmap_metrics['fallback_uses'] += 1
                    
                    # Track cross-platform compatibility issues
                    import platform
                    platform_key = f"{platform.system()}_{platform.machine()}"
                    if platform_key not in self.mmap_metrics['cross_platform_compatibility']:
                        self.mmap_metrics['cross_platform_compatibility'][platform_key] = {
                            'successes': 0, 'failures': 0, 'fallbacks': 0
                        }
                    self.mmap_metrics['cross_platform_compatibility'][platform_key]['failures'] += 1
                    self.mmap_metrics['cross_platform_compatibility'][platform_key]['fallbacks'] += 1
                    
                    return self._read_file_traditional(file_path)
                    
        except (OSError, ValueError) as file_error:
            # File opening errors
            mmap_logger.error(f"File open failed for {file_path}: {file_error}")
            self.mmap_metrics['failed_uses'] += 1
            return ""
    
    def _validate_mmap_compatibility(self) -> bool:
        """
        Validate mmap compatibility across different platforms and environments.
        
        Returns:
            True if mmap is compatible, False otherwise
        """
        try:
            import platform
            import sys
            
            # Check platform compatibility
            system = platform.system()
            machine = platform.machine()
            
            # Known problematic combinations
            incompatible_platforms = [
                ("Windows", "ARM"),  # Windows ARM has known mmap issues
                ("Linux", "armv6"),  # Some ARMv6 systems have mmap limitations
            ]
            
            for incompatible_system, incompatible_machine in incompatible_platforms:
                if system == incompatible_system and incompatible_machine in machine:
                    return False
            
            # Check Python version compatibility
            if sys.version_info < (3, 6):
                return False
            
            # Test mmap functionality with a small temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as tmp_file:
                tmp_file.write(b"test mmap compatibility")
                tmp_file.flush()
                
                try:
                    with mmap.mmap(tmp_file.fileno(), 0, access=mmap.ACCESS_READ) as test_mm:
                        # Test basic operations
                        if len(test_mm.read()) != 23:  # "test mmap compatibility" is 23 bytes
                            return False
                except (mmap.error, OSError):
                    return False
                finally:
                    import os
                    try:
                        os.unlink(tmp_file.name)
                    except OSError:
                        pass
            
            return True
            
        except Exception as e:
            mmap_logger.warning(f"MMAP compatibility check failed: {e}")
            return False
    
    def get_mmap_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive mmap usage metrics and performance statistics.
        
        Returns:
            Dictionary with mmap metrics
        """
        return {
            'usage_stats': {
                'total_uses': self.mmap_metrics['total_uses'],
                'successful_uses': self.mmap_metrics['successful_uses'],
                'failed_uses': self.mmap_metrics['failed_uses'],
                'fallback_uses': self.mmap_metrics['fallback_uses'],
                'success_rate': self.get_mmap_success_rate()
            },
            'performance_stats': {
                'total_bytes_read': self.mmap_metrics['total_bytes_read'],
                'average_read_time_ms': self.mmap_metrics['average_read_time_ms']
            },
            'compatibility': self.mmap_metrics['cross_platform_compatibility'],
            'enabled': getattr(self.config, "use_mmap_file_reading", False)
        }
    
    def get_mmap_success_rate(self) -> float:
        """
        Calculate mmap success rate as a percentage.
        
        Returns:
            Success rate as percentage (0-100)
        """
        if self.mmap_metrics['total_uses'] == 0:
            return 0.0
        return (self.mmap_metrics['successful_uses'] / self.mmap_metrics['total_uses']) * 100
