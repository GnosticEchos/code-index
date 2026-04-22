"""
Search result processor module for handling search result conversion.

This module provides a clean interface for converting raw search results
to SearchMatch objects, delegating to ResultRanker for ranking logic.
"""

from typing import List, Dict, Any, Optional
from ...models import SearchMatch
from ..shared.result_ranker import ResultRanker


class SearchResultProcessor:
    """
    Processes raw search results into SearchMatch objects.
    
    This class provides a simplified interface for result conversion,
    delegating to ResultRanker for the actual ranking logic.
    """
    
    def __init__(self, config) -> None:
        self.config = config
        self._ranker = ResultRanker(config)
    
    def process_results(
        self,
        search_results: List[Dict[str, Any]],
        query: str,
        warnings: Optional[List[str]] = None
    ) -> List[SearchMatch]:
        """
        Process raw search results into SearchMatch objects.
        
        Args:
            search_results: Raw results from vector store
            query: Original search query
            warnings: Optional list to collect warnings
            
        Returns:
            List of SearchMatch objects
        """
        return self._ranker.rank_results(search_results, query)
    
    def process_similarity_results(
        self,
        search_results: List[Dict[str, Any]],
        source_file: str,
        query: str
    ) -> List[SearchMatch]:
        """
        Process similarity search results, filtering out the source file.
        
        Args:
            search_results: Raw results from vector store
            source_file: File to exclude from results
            query: Original search query
            
        Returns:
            List of SearchMatch objects
        """
        matches = []
        for result in search_results:
            try:
                # Skip the original file if it appears in results
                if result["payload"]["filePath"] == source_file:
                    continue
                    
                match = SearchMatch(
                    file_path=result["payload"]["filePath"],
                    start_line=result["payload"]["startLine"],
                    end_line=result["payload"]["endLine"],
                    code_chunk=result["payload"]["codeChunk"],
                    match_type=result["payload"].get("type", "text"),
                    score=result["score"],
                    adjusted_score=result.get("adjustedScore", result["score"]),
                    metadata={
                        "embedding_model": result["payload"].get("embedding_model", ""),
                        "similarity_file": source_file
                    }
                )
                matches.append(match)
            except Exception:
                continue
        return matches
    
    def process_embedding_results(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[SearchMatch]:
        """
        Process embedding-based search results.
        
        Args:
            search_results: Raw results from vector store
            
        Returns:
            List of SearchMatch objects
        """
        matches = []
        for result in search_results:
            try:
                match = SearchMatch(
                    file_path=result["payload"]["filePath"],
                    start_line=result["payload"]["startLine"],
                    end_line=result["payload"]["endLine"],
                    code_chunk=result["payload"]["codeChunk"],
                    match_type=result["payload"].get("type", "text"),
                    score=result["score"],
                    adjusted_score=result.get("adjustedScore", result["score"]),
                    metadata={
                        "embedding_model": result["payload"].get("embedding_model", ""),
                        "search_method": "embedding"
                    }
                )
                matches.append(match)
            except Exception:
                continue
        return matches
    
    def adjust_scores(
        self,
        matches: List[SearchMatch],
        file_weights: Optional[Dict[str, float]] = None,
        path_boosts: Optional[List[Dict[str, Any]]] = None,
        language_boosts: Optional[Dict[str, float]] = None
    ) -> List[SearchMatch]:
        """Adjust scores on matches using configured weights and boosts."""
        return self._ranker.adjust_scores(matches, file_weights, path_boosts, language_boosts)


def create_result_processor(config) -> SearchResultProcessor:
    """Factory function to create a SearchResultProcessor."""
    return SearchResultProcessor(config)