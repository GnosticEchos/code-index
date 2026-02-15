"""
Result ranker module for ranking and processing search results.

This module handles ranking, filtering, and assembly of search results.
"""

from typing import List, Dict, Any, Optional
from ..models import SearchMatch


class ResultRanker:
    """
    Ranks and processes search results.
    
    Handles:
    - Result ranking by score
    - Split block reassembly
    - Score adjustment
    """
    
    def __init__(self, config):
        self.config = config
    
    def rank_results(
        self,
        search_results: List[Dict[str, Any]],
        query: str
    ) -> List[SearchMatch]:
        """
        Rank search results and convert to SearchMatch objects.
        
        Args:
            search_results: Raw search results from vector store
            query: Original search query
            
        Returns:
            List of SearchMatch objects
        """
        # First, group split parts by parentBlockId for reassembly
        split_groups: Dict[str, List[Dict[str, Any]]] = {}
        non_split_results: List[Dict[str, Any]] = []
        
        for result in search_results:
            payload = result["payload"]
            if "splitIndex" in payload and "parentBlockId" in payload:
                parent_id = payload["parentBlockId"]
                if parent_id not in split_groups:
                    split_groups[parent_id] = []
                split_groups[parent_id].append(result)
            else:
                non_split_results.append(result)
        
        # Process results
        matches = []
        warnings = []
        
        # Process non-split results
        for result in non_split_results:
            try:
                match = self._create_match(result, query)
                matches.append(match)
            except Exception:
                continue
        
        # Process and reassemble split parts
        for parent_id, parts in split_groups:
            try:
                assembled_match = self._reassemble_split_block(
                    parent_id, parts, query
                )
                if assembled_match:
                    matches.append(assembled_match)
            except Exception as e:
                # Add individual parts as fallback
                warnings.append(f"Failed to reassemble split block {parent_id}: {str(e)}")
                for part in parts:
                    try:
                        match = self._create_match(part, query, f"split_part")
                        matches.append(match)
                    except Exception:
                        continue
        
        return matches
    
    def _create_match(
        self,
        result: Dict[str, Any],
        query: str,
        split_info: Optional[str] = None
    ) -> SearchMatch:
        """Create a SearchMatch from a search result."""
        payload = result["payload"]
        
        metadata = {
            "embedding_model": payload.get("embedding_model", ""),
            "search_query": query
        }
        
        if split_info:
            metadata["split_part"] = split_info
        
        return SearchMatch(
            file_path=payload["filePath"],
            start_line=payload["startLine"],
            end_line=payload["endLine"],
            code_chunk=payload["codeChunk"],
            match_type=payload.get("type", "text"),
            score=result["score"],
            adjusted_score=result.get("adjustedScore", result["score"]),
            metadata=metadata
        )
    
    def _reassemble_split_block(
        self,
        parent_id: str,
        parts: List[Dict[str, Any]],
        query: str
    ) -> Optional[SearchMatch]:
        """Reassemble a split block from its parts."""
        # Sort parts by splitIndex
        sorted_parts = sorted(parts, key=lambda p: p["payload"]["splitIndex"])
        
        # Verify we have all parts
        total_expected = sorted_parts[0]["payload"]["splitTotal"]
        if len(sorted_parts) != total_expected:
            return None
        
        # Reassemble the complete block
        first_part = sorted_parts[0]
        last_part = sorted_parts[-1]
        
        # Concatenate all code chunks
        reassembled_code = "".join(
            p["payload"]["codeChunk"] for p in sorted_parts
        )
        
        # Use the best score from all parts
        best_score = max(p["score"] for p in sorted_parts)
        best_adjusted = max(p.get("adjustedScore", p["score"]) for p in sorted_parts)
        
        return SearchMatch(
            file_path=first_part["payload"]["filePath"],
            start_line=first_part["payload"]["startLine"],
            end_line=last_part["payload"]["endLine"],
            code_chunk=reassembled_code,
            match_type=first_part["payload"].get("type", "text"),
            score=best_score,
            adjusted_score=best_adjusted,
            metadata={
                "embedding_model": first_part["payload"].get("embedding_model", ""),
                "search_query": query,
                "reassembled_from": total_expected,
                "parent_block_id": parent_id
            }
        )
    
    def adjust_scores(
        self,
        matches: List[SearchMatch],
        file_weights: Optional[Dict[str, float]] = None,
        path_boosts: Optional[List[Dict[str, Any]]] = None,
        language_boosts: Optional[Dict[str, float]] = None
    ) -> List[SearchMatch]:
        """
        Adjust scores based on file type weights, path boosts, and language boosts.
        
        Args:
            matches: List of search matches
            file_weights: File extension weights
            path_boosts: Path pattern boosts
            language_boosts: Language-specific boosts
            
        Returns:
            List of matches with adjusted scores
        """
        if not matches:
            return matches
        
        # Apply file type weights
        if file_weights:
            for match in matches:
                ext = self._get_extension(match.file_path)
                if ext in file_weights:
                    match.adjusted_score = match.score * file_weights[ext]
        
        # Apply path boosts
        if path_boosts:
            for match in matches:
                for boost in path_boosts:
                    pattern = boost.get("pattern", "")
                    weight = boost.get("weight", 1.0)
                    if pattern in match.file_path:
                        match.adjusted_score *= weight
        
        return matches
    
    def _get_extension(self, file_path: str) -> str:
        """Get file extension from path."""
        import os
        return os.path.splitext(file_path)[1].lower()
    
    def filter_by_threshold(
        self,
        matches: List[SearchMatch],
        min_score: float = 0.0
    ) -> List[SearchMatch]:
        """Filter matches by minimum score threshold."""
        return [m for m in matches if m.adjusted_score >= min_score]
    
    def sort_by_score(self, matches: List[SearchMatch], descending: bool = True) -> List[SearchMatch]:
        """Sort matches by adjusted score."""
        return sorted(matches, key=lambda m: m.adjusted_score, reverse=descending)


def create_ranker(config) -> ResultRanker:
    """Factory function to create a ResultRanker."""
    return ResultRanker(config)
