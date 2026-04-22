"""
Search result processor for formatting and ranking search results.
"""
from typing import List, Dict, Any, Optional

from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class SearchResultProcessor:
    """Process and format search results for presentation."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize result processor."""
        self.error_handler = error_handler or ErrorHandler()
    
    def process_results(self, raw_results: List[Dict[str, Any]], config: Config) -> List[Dict[str, Any]]:
        """Process raw search results into formatted results."""
        try:
            if not raw_results:
                return []
            
            # Apply minimum score filtering
            min_score = getattr(config, "search_min_score", 0.4)
            filtered_results = [result for result in raw_results if result.get("similarity_score", 0) >= min_score]
            
            # Sort by similarity score (descending)
            filtered_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            
            # Limit results
            max_results = getattr(config, "search_max_results", 50)
            final_results = filtered_results[:max_results]
            
            # Format results for presentation
            formatted_results = []
            for i, result in enumerate(final_results):
                formatted_results.append({
                    "rank": i + 1,
                    "score": result.get("similarity_score", 0),
                    "snippet": result.get("snippet", "No snippet available"),
                    "file_path": result.get("file_path", "Unknown file"),
                    "start_line": result.get("start_line", 1),
                    "end_line": result.get("end_line", 1),
                    "type": result.get("type", "unknown"),
                    "similarity_score": result.get("similarity_score", 0)
                })
            
            return formatted_results
        except Exception as e:
            error_context = ErrorContext(
                component="result_processor",
                operation="process_results"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
            )
            return []
    
    def format_for_tui(self, results: List[Dict[str, Any]]) -> str:
        """Format results for TUI display."""
        try:
            if not results:
                return "No results found"
            
            formatted = []
            for result in results:
                formatted.append(f"Rank: {result['rank']} | Score: {result['score']:.3f} | File: {result['file_path']}:{result['start_line']}-{result['end_line']} | Type: {result['type']}")
            
            return "\n".join(formatted)
        except Exception as e:
            error_context = ErrorContext(
                component="result_processor",
                operation="format_for_tui"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )
            return "Error formatting results"