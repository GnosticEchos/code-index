"""
Search strategy pattern implementation for flexible search algorithms.
"""
from typing import List, Optional, Dict, Any

from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity
from ..search.text_search_strategy import TextSearchStrategy
from ..search.similarity_search_strategy import SimilaritySearchStrategy
from ..search.embedding_search_strategy import EmbeddingSearchStrategy

class SearchStrategyFactory:
    """Factory for creating search strategies based on configuration."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize strategy factory."""
        self.error_handler = error_handler or ErrorHandler()
    
    def create_strategy(self, config: Config) -> Optional[Any]:
        """Create search strategy based on configuration."""
        try:
            strategy_type = getattr(config, "search_strategy", "similarity")
            
            if strategy_type == "text":
                return TextSearchStrategy(self.error_handler)
            elif strategy_type == "similarity":
                return SimilaritySearchStrategy(self.error_handler)
            elif strategy_type == "embedding":
                return EmbeddingSearchStrategy(self.error_handler)
            else:
                error_context = ErrorContext(
                    component="search_strategy_factory",
                    operation="create_strategy"
                )
                error_response = self.error_handler.handle_error(
                    ValueError(f"Unknown search strategy: {strategy_type}"),
                    error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
                )
                return None
                
        except Exception as e:
            error_context = ErrorContext(
                component="search_strategy_factory",
                operation="create_strategy"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
            )
            return None
    
    def get_available_strategies(self) -> List[str]:
        """Get available search strategies."""
        return ["text", "similarity", "embedding"]
    
    def get_strategy_description(self, strategy_name: str) -> str:
        """Get description for a specific search strategy."""
        descriptions = {
            "text": "Text-based search using string matching and regex patterns",
            "similarity": "Vector similarity search using embeddings",
            "embedding": "Advanced embedding-based semantic search"
        }
        return descriptions.get(strategy_name, f"Unknown strategy: {strategy_name}")