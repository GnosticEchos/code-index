"""
File processor for individual file handling.

Handles individual file processing with language detection, tree-sitter parsing,
and error recovery. Part of the decomposed indexing system.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import hashlib

from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from .language_detector import LanguageDetector


class FileProcessor:
    """Processes individual files with language detection and parsing."""
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        """Initialize file processor."""
        self.config = config
        self.error_handler = error_handler
        self.language_detector = LanguageDetector()
        
    async def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a single file with comprehensive language detection.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Processing result with language, blocks, and metadata
        """
        try:
            if not file_path.exists():
                return {
                    'filename': str(file_path),
                    'language': 'unknown',
                    'blocks': 0,
                    'size': 0,
                    'error': f"File not found: {file_path}",
                    'warnings': []
                }
                
            # Get file info
            stat = file_path.stat()
            if stat.st_size == 0:
                return {
                    'filename': str(file_path),
                    'language': 'unknown',
                    'blocks': 0,
                    'size': 0,
                    'error': None,
                    'warnings': ["Empty file"]
                }
                
            # Enhanced language detection
            language = self.language_detector.detect_language(str(file_path))
            tree_sitter_lang = self.language_detector.get_tree_sitter_language(language)
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with latin-1 encoding for binary files
                with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                    
            if not content.strip():
                return {
                    'filename': str(file_path),
                    'language': language,
                    'blocks': 0,
                    'size': stat.st_size,
                    'error': None,
                    'warnings': ["File contains only whitespace"]
                }
                
            # Process based on language
            if self.language_detector.is_supported_language(language):
                blocks = await self._process_with_tree_sitter(content, language, tree_sitter_lang)
            else:
                blocks = await self._process_fallback(content, language)
                
            return {
                'filename': str(file_path),
                'language': language,
                'blocks': blocks,
                'size': stat.st_size,
                'error': None,
                'warnings': []
            }
            
        except Exception as e:
            context = ErrorContext(
                component="file_processor",
                operation="process_file",
                file_path=str(file_path)
            )
            error_response = self.error_handler.handle_error(
                e, context, ErrorCategory.FILEPROCESSING, ErrorSeverity.MEDIUM
            )
            
            return {
                'filename': str(file_path),
                'language': 'unknown',
                'blocks': 0,
                'size': 0,
                'error': error_response.message,
                'warnings': []
            }
            
    async def _process_with_tree_sitter(self, content: str, language: str, 
                                      tree_sitter_lang: Optional[str]) -> int:
        """Process file with tree-sitter for supported languages."""
        try:
            # For now, estimate blocks based on content
            # This will be enhanced with actual tree-sitter parsing
            lines = content.split('\n')
            
            # Rough block estimation
            block_indicators = {
                'python': ['def ', 'class ', 'import ', 'if __name__'],
                'javascript': ['function ', 'class ', 'export ', 'import '],
                'typescript': ['function ', 'class ', 'export ', 'interface '],
                'vue': ['<template>', '<script>', '<style>'],
                'rust': ['fn ', 'struct ', 'impl ', 'mod '],
                'go': ['func ', 'type ', 'import ', 'package '],
                'java': ['public class', 'private class', 'interface '],
                'c': ['int ', 'void ', 'struct ', '#include'],
                'cpp': ['class ', 'namespace ', 'template<'],
                'csharp': ['public class', 'private class', 'interface '],
            }
            
            indicators = block_indicators.get(language, [])
            estimated_blocks = sum(1 for line in lines 
                                 if any(indicator in line for indicator in indicators))
            
            # Ensure at least 1 block for non-empty files
            return max(1, estimated_blocks)
            
        except Exception:
            # Fallback to line-based estimation
            return max(1, len(content.split('\n')) // 10)
            
    async def _process_fallback(self, content: str, language: str) -> int:
        """Fallback processing for unsupported languages."""
        # Simple line-based estimation
        lines = content.split('\n')
        return max(1, len(lines) // 15)
        
    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get basic file metadata."""
        try:
            stat = file_path.stat()
            language = self.language_detector.detect_language(str(file_path))
            
            return {
                'filename': str(file_path),
                'size': stat.st_size,
                'language': language,
                'extension': file_path.suffix,
                'last_modified': stat.st_mtime,
                'hash': self._calculate_hash(file_path)
            }
        except Exception as e:
            return {
                'filename': str(file_path),
                'size': 0,
                'language': 'unknown',
                'extension': '',
                'last_modified': 0,
                'hash': '',
                'error': str(e)
            }
            
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash for deduplication."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
            
    def should_process_file(self, file_path: Path) -> bool:
        """Determine if file should be processed."""
        if not file_path.exists():
            return False
            
        # Skip hidden files
        if any(part.startswith('.') for part in file_path.parts):
            return False
            
        # Skip common non-code files
        skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', '.dat'}
        if file_path.suffix.lower() in skip_extensions:
            return False
            
        # Skip large files (configurable)
        max_size = getattr(self.config, 'max_file_size_bytes', 1048576)  # 1MB default
        if file_path.stat().st_size > max_size:
            return False
            
        return True
