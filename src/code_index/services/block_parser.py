"""
Block parser module for Tree-sitter block extraction.

This module handles the actual parsing of code into semantic blocks using Tree-sitter.
"""

import logging
from typing import List, Optional, Dict, Any
from ..models import CodeBlock
from ..utils import split_content


def compile_treesitter_query(language, query_text: str):
    """Compile a Tree-sitter query."""
    try:
        from tree_sitter import Query
        return Query(language, query_text)
    except Exception as e:
        return None


def execute_treesitter_query(query, root_node) -> List[Dict[str, Any]]:
    """Execute a Tree-sitter query and return captures with metadata."""
    captures: List[Dict[str, Any]] = []
    try:
        from tree_sitter import QueryCursor
        cursor = QueryCursor(query)

        for match in cursor.matches(root_node):
            pattern_index, captures_dict = match
            for capture_name, nodes in captures_dict.items():
                for node in nodes:
                    captures.append({
                        "node": node,
                        "capture_name": capture_name,
                    })

    except Exception:
        pass

    return captures


def basic_line_chunking(
    content: str,
    file_path: str,
    file_hash: str,
    max_block_chars: int = 6000,
    fallback_chunk_size: int = 5
) -> List[CodeBlock]:
    """Fallback strategy: split plain text into fixed-size line chunks."""
    if not content:
        return []

    lines = content.splitlines()
    chunk_size = max(1, int(fallback_chunk_size))

    blocks: List[CodeBlock] = []
    for start in range(0, len(lines), chunk_size):
        chunk_lines = lines[start:start + chunk_size]
        if not chunk_lines:
            continue

        start_line = start + 1
        end_line = start + len(chunk_lines)
        chunk_text = "\n".join(chunk_lines)
        
        # Split oversized chunks to preserve all data
        if len(chunk_text) > max_block_chars:
            content_chunks = split_content(chunk_text, max_block_chars)
            
            parent_id = f"text_chunk_{start_line}_{end_line}"
            
            for chunk_idx, chunk_content in enumerate(content_chunks):
                chunk_identifier = f"text_chunk_{start_line}_{end_line}_part{chunk_idx + 1}"
                
                blocks.append(CodeBlock(
                    file_path=file_path,
                    identifier=chunk_identifier,
                    type="text_chunk",
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    file_hash=file_hash,
                    segment_hash=f"{file_hash}:{start_line}:{end_line}:part{chunk_idx + 1}",
                    split_index=chunk_idx + 1,
                    split_total=len(content_chunks),
                    parent_block_id=parent_id,
                ))
        else:
            identifier = f"text_chunk_{start_line}_{end_line}"

            blocks.append(CodeBlock(
                file_path=file_path,
                identifier=identifier,
                type="text_chunk",
                start_line=start_line,
                end_line=end_line,
                content=chunk_text,
                file_hash=file_hash,
                segment_hash=f"{file_hash}:{start_line}:{end_line}"
            ))

    return blocks


def extract_blocks_with_treesitter(
    root_node,
    text: str,
    file_path: str,
    file_hash: str,
    language_key: str,
    parser_manager,
    config,
    debug_enabled: bool = False
) -> List[CodeBlock]:
    """
    Extract semantic blocks using actual Tree-sitter parsing.
    
    Args:
        root_node: Tree-sitter root node
        text: Source code text
        file_path: Path to the source file
        file_hash: Hash of the file
        language_key: Language identifier
        parser_manager: Parser manager instance
        config: Configuration object
        debug_enabled: Enable debug logging
        
    Returns:
        List of extracted code blocks
    """
    _logger = logging.getLogger("code_index.block_parser")
    blocks = []
    
    try:
        # Get Tree-sitter queries for the language
        from ..treesitter_queries import get_queries_for_language
        query_text = get_queries_for_language(language_key)
        
        if not query_text:
            return basic_line_chunking(text, file_path, file_hash)
        
        # Compile and execute the query
        parser = parser_manager.get_parser(language_key)
        if not parser:
            return basic_line_chunking(text, file_path, file_hash)
            
        query = compile_treesitter_query(parser.language, query_text)
        if not query:
            return []
            
        # Get thresholds from config
        min_block_chars = getattr(config, "tree_sitter_min_block_chars", 30)
        max_block_chars = getattr(config, "tree_sitter_max_block_chars", 6000)
        
        # Execute query
        captures = execute_treesitter_query(query, root_node)
        
        # Define structural captures
        structural_captures = {
            "module", "component", "function", "function_definition",
            "function_declaration", "method_definition", "method_declaration",
            "class", "class_definition", "class_declaration", "impl",
            "impl_item", "struct", "struct_item", "enum", "enum_item",
            "trait", "trait_item", "template", "template_element",
        }
        
        # Process captures into blocks
        for capture in captures:
            node = capture["node"]
            block_type = capture["capture_name"]
            
            start_line, start_col = node.start_point
            end_line, end_col = node.end_point
            
            # Convert to 1-based indexing
            start_line += 1
            end_line += 1
            
            # Extract content
            block_content = text[node.start_byte:node.end_byte]
            
            content_length = len(block_content.strip())
            threshold = min_block_chars
            
            # Skip blocks that are too short
            if block_type in structural_captures:
                if content_length < threshold:
                    continue
            elif content_length < threshold:
                continue
            
            # Split oversized blocks
            if len(block_content) > max_block_chars:
                content_chunks = split_content(block_content, max_block_chars)
                total_lines = end_line - start_line + 1
                lines_per_chunk = max(1, total_lines // len(content_chunks))
                parent_id = f"{block_type}_{start_line}_{end_line}"
                
                for chunk_idx, chunk_content in enumerate(content_chunks):
                    chunk_start_line = start_line + (chunk_idx * lines_per_chunk)
                    chunk_end_line = min(chunk_start_line + lines_per_chunk - 1, end_line)
                    identifier = f"{block_type}_{chunk_start_line}_{chunk_end_line}_part{chunk_idx + 1}"
                    
                    block = CodeBlock(
                        file_path=file_path,
                        identifier=identifier,
                        type=block_type,
                        start_line=chunk_start_line,
                        end_line=chunk_end_line,
                        content=chunk_content,
                        file_hash=file_hash,
                        segment_hash=f"{file_hash}:{chunk_start_line}:{chunk_end_line}:part{chunk_idx + 1}",
                        split_index=chunk_idx + 1,
                        split_total=len(content_chunks),
                        parent_block_id=parent_id,
                    )
                    blocks.append(block)
            else:
                identifier = f"{block_type}_{start_line}_{end_line}"
                block = CodeBlock(
                    file_path=file_path,
                    identifier=identifier,
                    type=block_type,
                    start_line=start_line,
                    end_line=end_line,
                    content=block_content,
                    file_hash=file_hash,
                    segment_hash=f"{file_hash}:{start_line}:{end_line}"
                )
                blocks.append(block)

    except Exception:
        return basic_line_chunking(text, file_path, file_hash)

    return blocks
