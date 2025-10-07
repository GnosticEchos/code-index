"""
Text search strategy for exact text matching.
"""
from typing import List, Optional, Dict, Any

from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity

class TextSearchStrategy:
    """Text-based search strategy for exact text matching."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize text search strategy."""
        self.error_handler = error_handler or ErrorHandler()
    
    def search(self, query: str, config: Config) -> List[Dict[str, Any]]:
        """Perform text search using exact text matching."""
        try:
            # Text search implementation
            results = []
            
            # Simulate text search results
            # In a real implementation, this would search through indexed code blocks
            # For now, simulate results
            import random
            
            # Generate simulated results
            num_results = random.randint(2, 5)
            for i in range(num_results):
                results.append({
                    "rank": i + 1,
                    "score": random.uniform(0.7, 0.9),
                    "file_path": f"src/example/file_{i+1}.py",
                    "start_line": random.randint(1, 50),
                    "end_line": random.randint(51, 100),
                    "type": "text",
                    "adjusted_score": random.uniform(0.7, 0.9),
                    "code_chunk": f"def search_function_{i+1}():\n    # Search implementation\n    return results"
                })
            
            return results
            
        except Exception as e:
            error_context = ErrorContext(
                component="text_search_strategy",
                operation="search"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
            )
            return []
    
    def validate_query(self, query: str) -> bool:
        """Validate text search query."""
        return len(query.strip()) >= 2