import logging
from typing import List, Optional, Dict, Any
from ...models import CodeBlock
from ..query.universal_schema_service import UniversalSchemaService

logger = logging.getLogger(__name__)

class RelationshipBlockExtractor:
    """
    Extracts high-precision relationship blocks (classes, functions, imports, calls)
    using the Relationship-Native Query Schema.
    """

    def __init__(self, schema_service: Optional[UniversalSchemaService] = None):
        self.schema_service = schema_service or UniversalSchemaService()
        self.schema_service.load_schema()

    def extract_relationship_blocks(
        self, 
        root_node, 
        text: str, 
        file_path: str, 
        file_hash: str, 
        language: str,
        ts_lang: Optional[Any] = None
    ) -> List[CodeBlock]:
        """
        Execute relationship queries for the given language and return CodeBlocks.
        """
        blocks = []
        lang_queries = self.schema_service.get_queries_for_language(language)
        
        if not lang_queries:
            logger.debug(f"No relationship queries found for language: {language}")
            return []

        # Determine the Language object
        active_lang = ts_lang
        if active_lang is None:
            try:
                # Common Tree-sitter binding patterns
                if hasattr(root_node, 'language'):
                    active_lang = root_node.language
                elif hasattr(root_node, 'tree') and root_node.tree:
                    active_lang = getattr(root_node.tree, 'language', None)
            except Exception:
                pass

        if active_lang is None:
             return []

        try:
            import tree_sitter
            # We execute queries by category to maintain precise identification
            for category, queries in lang_queries.items():
                for query_str in queries:
                    try:
                        # 2024-2025 Tree-sitter Pattern: Query + QueryCursor
                        q = tree_sitter.Query(active_lang, query_str)
                        cursor = tree_sitter.QueryCursor(q)
                        captures = cursor.captures(root_node)
                        
                        target_capture_name = self.schema_service.get_target_capture(language, query_str)
                        
                        # In this version, captures is a dict: { capture_name: [nodes] }
                        if isinstance(captures, dict):
                             nodes = captures.get(target_capture_name, [])
                             for node in nodes:
                                  blocks.append(self._node_to_block(
                                      node, category, text, file_path, file_hash
                                  ))
                        else:
                             # Fallback for older bindings returning list of (node, name)
                             for node, capture_name in captures:
                                 if capture_name == target_capture_name:
                                     blocks.append(self._node_to_block(
                                         node, category, text, file_path, file_hash
                                     ))
                                
                    except Exception as e:
                        logger.warning(f"Failed to execute relationship query for {language}.{category}: {e}")
                        continue
        except ImportError:
            logger.error("tree_sitter module not found")
            return []
        
        if blocks:
            logger.debug(f"Extracted {len(blocks)} relationship blocks for {file_path} ({language})")
        return blocks

    def _node_to_block(
        self, 
        node, 
        category: str, 
        text: str, 
        file_path: str, 
        file_hash: str
    ) -> CodeBlock:
        """Convert a Tree-sitter node to a domain CodeBlock."""
        # Standard tree-sitter start_point/end_point handling
        try:
             start_pt = node.start_point
             end_pt = node.end_point
             if isinstance(start_pt, (list, tuple)):
                  start_line = start_pt[0] + 1
                  end_line = end_pt[0] + 1
             else:
                  start_line = getattr(start_pt, 'row', 0) + 1
                  end_line = getattr(end_pt, 'row', 0) + 1
        except Exception:
             start_line = 1
             end_line = 1
        
        # Exact extraction of the symbol name from source text
        identifier = text[node.start_byte:node.end_byte]
        
        return CodeBlock(
            file_path=file_path,
            identifier=identifier,
            type=category, # e.g., 'class', 'function', 'import', 'call'
            start_line=start_line,
            end_line=end_line,
            content=text[node.start_byte:node.end_byte],
            file_hash=file_hash,
            segment_hash=f"{file_hash}:{start_line}:{end_line}",
            metadata={
                'relationship_type': category,
                'precision': 'high'
            }
        )
