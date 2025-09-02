"""
Code parser for the code index tool.
"""
import os
import mmap
from typing import List, Dict, Any, Optional
from code_index.config import Config
from code_index.utils import get_file_hash
from code_index.chunking import ChunkingStrategy
from code_index.models import CodeBlock


class CodeParser:
    """Parses code files into blocks."""
    
    def __init__(self, config: Config, chunking_strategy: ChunkingStrategy):
        """Initialize code parser with configuration and a chunking strategy."""
        self.config = config
        self.chunking_strategy = chunking_strategy
    
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
            file_hash = get_file_hash(file_path)
            
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
        Read file content using memory-mapped file reading.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content as string
            
        Raises:
            OSError: If file cannot be opened or mapped
            ValueError: If file is empty
        """
        try:
            with open(file_path, "rb") as f:
                # Get file size
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    return ""
                
                # Create memory map with proper error handling
                try:
                    with mmap.mmap(f.fileno(), file_size, access=mmap.ACCESS_READ) as mm:
                        # Decode bytes to string
                        try:
                            content = mm.read(file_size).decode('utf-8', errors='ignore')
                            return content
                        except UnicodeDecodeError as decode_error:
                            print(f"Warning: Unicode decode error in mmap for {file_path}: {decode_error}")
                            # Fall back to traditional reading with different encoding
                            return self._read_file_traditional(file_path)
                except (mmap.error, OSError, ValueError) as mmap_error:
                    # mmap-specific errors
                    print(f"Warning: mmap failed for {file_path}, falling back to traditional reading: {mmap_error}")
                    return self._read_file_traditional(file_path)
        except (OSError, ValueError) as file_error:
            # File opening errors
            print(f"Warning: File open failed for {file_path}: {file_error}")
            return ""
