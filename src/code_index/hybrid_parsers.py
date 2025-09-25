"""
Hybrid Parser System for handling unsupported file types.

This module provides fallback parsing strategies for files that don't have
Tree-sitter support, including plain text, configuration files, and other
unsupported formats.
"""

import re
import os
import time
from typing import List, Dict, Any, Optional, Callable, Pattern
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .config import Config
from .models import CodeBlock
from .errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


@dataclass
class ParserResult:
    """Result of parsing operation."""
    blocks: List[CodeBlock]
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    processing_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseFallbackParser(ABC):
    """Base class for fallback parsers."""
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        self.name = self.__class__.__name__
        
    @abstractmethod
    def can_parse(self, file_path: str, content: str) -> bool:
        """Check if this parser can handle the given file."""
        pass
        
    @abstractmethod
    def parse(self, content: str, file_path: str, file_hash: str) -> ParserResult:
        """Parse the content and return blocks."""
        pass
        
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about this parser."""
        return {
            "name": self.name,
            "type": "fallback",
            "supported_extensions": getattr(self, "supported_extensions", []),
            "description": getattr(self, "description", "Fallback parser")
        }


class PlainTextParser(BaseFallbackParser):
    """Parser for plain text files."""
    
    supported_extensions = [".txt", ".log", ".out", ".err"]
    description = "Parser for plain text files with line-based chunking"
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        super().__init__(config, error_handler)
        self.chunk_size = getattr(config, "text_chunk_size", 1000)  # characters per chunk
        self.min_chunk_lines = getattr(config, "text_min_chunk_lines", 10)
        
    def can_parse(self, file_path: str, content: str) -> bool:
        """Check if this is a plain text file."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions or self._is_plain_text(content)
        
    def _is_plain_text(self, content: str) -> bool:
        """Check if content appears to be plain text."""
        if not content:
            return False
            
        # Check for high percentage of printable characters
        printable_count = sum(1 for char in content[:1000] if char.isprintable() or char in '\n\r\t')
        printable_ratio = printable_count / min(len(content), 1000)
        
        # Check for reasonable line length distribution
        lines = content.split('\n')
        if len(lines) > 100:
            long_lines = sum(1 for line in lines if len(line) > 200)
            if long_lines / len(lines) > 0.5:  # Too many very long lines
                return False
                
        return printable_ratio > 0.95
        
    def parse(self, content: str, file_path: str, file_hash: str) -> ParserResult:
        """Parse plain text content into chunks."""
        start_time = time.time()
        
        try:
            blocks = []
            lines = content.split('\n')
            
            if len(lines) < self.min_chunk_lines:
                # Small file - create single block
                block = CodeBlock(
                    file_path=file_path,
                    identifier="content",
                    type="text_chunk",
                    start_line=1,
                    end_line=len(lines),
                    content=content,
                    file_hash=file_hash,
                    segment_hash=f"{file_hash}:1:{len(lines)}"
                )
                blocks.append(block)
            else:
                # Create chunks based on line count
                chunk_start = 1
                current_chunk_lines = []
                
                for i, line in enumerate(lines):
                    current_chunk_lines.append(line)
                    
                    # Create chunk when we have enough lines or at end of file
                    if (len(current_chunk_lines) >= self.min_chunk_lines and 
                        (i == len(lines) - 1 or len('\n'.join(current_chunk_lines)) >= self.chunk_size)):
                        
                        chunk_content = '\n'.join(current_chunk_lines)
                        block = CodeBlock(
                            file_path=file_path,
                            identifier=f"chunk_{chunk_start}",
                            type="text_chunk",
                            start_line=chunk_start,
                            end_line=chunk_start + len(current_chunk_lines) - 1,
                            content=chunk_content,
                            file_hash=file_hash,
                            segment_hash=f"{file_hash}:{chunk_start}:{chunk_start + len(current_chunk_lines) - 1}"
                        )
                        blocks.append(block)
                        
                        chunk_start = i + 2  # Next line (1-indexed)
                        current_chunk_lines = []
                        
            return ParserResult(
                blocks=blocks,
                success=True,
                metadata={
                    "parser": "PlainTextParser",
                    "chunks_created": len(blocks),
                    "total_lines": len(lines)
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ParserResult(
                blocks=[],
                success=False,
                error_message=str(e),
                metadata={"parser": "PlainTextParser"},
                processing_time_ms=(time.time() - start_time) * 1000
            )


class ConfigFileParser(BaseFallbackParser):
    """Parser for configuration files."""
    
    supported_extensions = [".ini", ".cfg", ".conf", ".properties", ".env"]
    description = "Parser for configuration files with section-based chunking"
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        super().__init__(config, error_handler)
        self.section_patterns = [
            re.compile(r'^\[([^\]]+)\]'),  # INI-style sections
            re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*='),  # Key-value pairs
            re.compile(r'^#.*$'),  # Comments
            re.compile(r'^;.*$'),  # Comments
        ]
        
    def can_parse(self, file_path: str, content: str) -> bool:
        """Check if this is a configuration file."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.supported_extensions:
            return True
            
        # Check content patterns for files without known extensions
        lines = content.split('\n')[:50]  # Check first 50 lines
        section_count = 0
        key_value_count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
                
            if self.section_patterns[0].match(line):  # Section header
                section_count += 1
            elif '=' in line and not line.startswith(' '):  # Key-value pair
                key_value_count += 1
                
        # Heuristic: config files usually have sections or key-value pairs
        return section_count > 0 or (key_value_count > len([l for l in lines if l.strip() and not l.startswith('#') and not l.startswith(';')]) * 0.3)
        
    def parse(self, content: str, file_path: str, file_hash: str) -> ParserResult:
        """Parse configuration file content."""
        start_time = time.time()
        
        try:
            blocks = []
            lines = content.split('\n')
            current_section = None
            section_content = []
            section_start_line = 1
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for section header
                section_match = self.section_patterns[0].match(line)
                if section_match:
                    # Save previous section if exists
                    if current_section and section_content:
                        block = CodeBlock(
                            file_path=file_path,
                            identifier=current_section,
                            type="config_section",
                            start_line=section_start_line,
                            end_line=i - 1,
                            content='\n'.join(section_content),
                            file_hash=file_hash,
                            segment_hash=f"{file_hash}:{section_start_line}:{i-1}"
                        )
                        blocks.append(block)
                        
                    # Start new section
                    current_section = section_match.group(1)
                    section_content = [line]
                    section_start_line = i
                elif current_section:
                    section_content.append(line)
                    
            # Add final section
            if current_section and section_content:
                block = CodeBlock(
                    file_path=file_path,
                    identifier=current_section,
                    type="config_section",
                    start_line=section_start_line,
                    end_line=len(lines),
                    content='\n'.join(section_content),
                    file_hash=file_hash,
                    segment_hash=f"{file_hash}:{section_start_line}:{len(lines)}"
                )
                blocks.append(block)
                
            # If no sections found, treat as key-value pairs
            if not blocks:
                blocks = self._parse_key_value_pairs(content, file_path, file_hash)
                
            return ParserResult(
                blocks=blocks,
                success=True,
                metadata={
                    "parser": "ConfigFileParser",
                    "sections_found": len(blocks),
                    "has_sections": any(block.type == "config_section" for block in blocks)
                },
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ParserResult(
                blocks=[],
                success=False,
                error_message=str(e),
                metadata={"parser": "ConfigFileParser"},
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
    def _parse_key_value_pairs(self, content: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Parse content as key-value pairs."""
        blocks = []
        lines = content.split('\n')
        
        # Group consecutive key-value pairs
        current_group = []
        group_start_line = 1
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if '=' in line and not line.startswith('#') and not line.startswith(';'):
                if not current_group:
                    group_start_line = i
                current_group.append(line)
            elif current_group:
                # End of key-value group
                block = CodeBlock(
                    file_path=file_path,
                    identifier=f"config_group_{group_start_line}",
                    type="config_key_values",
                    start_line=group_start_line,
                    end_line=i - 1,
                    content='\n'.join(current_group),
                    file_hash=file_hash,
                    segment_hash=f"{file_hash}:{group_start_line}:{i-1}"
                )
                blocks.append(block)
                current_group = []
                
        # Add final group
        if current_group:
            block = CodeBlock(
                file_path=file_path,
                identifier=f"config_group_{group_start_line}",
                type="config_key_values",
                start_line=group_start_line,
                end_line=len(lines),
                content='\n'.join(current_group),
                file_hash=file_hash,
                segment_hash=f"{file_hash}:{group_start_line}:{len(lines)}"
            )
            blocks.append(block)
            
        return blocks


class HybridParserManager:
    """Manager for hybrid parsing strategies."""
    
    def __init__(self, config: Config, error_handler: Optional[ErrorHandler] = None):
        self.config = config
        self.error_handler = error_handler or ErrorHandler()
        self.parsers = []
        self._debug_enabled = getattr(config, "tree_sitter_debug_logging", False)
        
        # Initialize fallback parsers
        self._initialize_parsers()
        
    def _initialize_parsers(self):
        """Initialize all available fallback parsers."""
        self.parsers = [
            ConfigFileParser(self.config, self.error_handler),
            PlainTextParser(self.config, self.error_handler),
        ]
        
    def parse_with_fallback(self, content: str, file_path: str, file_hash: str) -> ParserResult:
        """
        Parse content using appropriate fallback parser.
        
        Args:
            content: File content
            file_path: Path to the file
            file_hash: Hash of the file content
            
        Returns:
            ParserResult with parsed blocks
        """
        start_time = time.time()
        
        try:
            # Try each parser in order
            for parser in self.parsers:
                if parser.can_parse(file_path, content):
                    if self._debug_enabled:
                        print(f"[DEBUG] Using fallback parser: {parser.name} for {file_path}")
                        
                    result = parser.parse(content, file_path, file_hash)
                    result.metadata["fallback_parser_used"] = parser.name
                    result.metadata["processing_time_ms"] = (time.time() - start_time) * 1000
                    return result
                    
            # No suitable parser found
            if self._debug_enabled:
                print(f"[DEBUG] No suitable fallback parser found for {file_path}")
                
            return ParserResult(
                blocks=[],
                success=False,
                error_message="No suitable fallback parser found",
                metadata={"fallback_parsers_tried": [p.name for p in self.parsers]},
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            error_context = ErrorContext(
                component="hybrid_parser_manager",
                operation="parse_with_fallback",
                file_path=file_path
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.PARSING, ErrorSeverity.MEDIUM
            )
            
            return ParserResult(
                blocks=[],
                success=False,
                error_message=str(e),
                metadata={"error": str(e)},
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
    def get_available_parsers(self) -> List[Dict[str, Any]]:
        """Get information about all available parsers."""
        return [parser.get_parser_info() for parser in self.parsers]
        
    def add_custom_parser(self, parser: BaseFallbackParser):
        """Add a custom fallback parser."""
        self.parsers.append(parser)
        
    def get_parser_stats(self) -> Dict[str, Any]:
        """Get statistics about parser usage."""
        return {
            "total_parsers": len(self.parsers),
            "parser_types": [parser.name for parser in self.parsers],
            "available_extensions": list(set(
                ext for parser in self.parsers 
                for ext in getattr(parser, "supported_extensions", [])
            ))
        }