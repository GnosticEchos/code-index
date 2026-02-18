"""
Search strategy selector module for choosing search strategies.

This module handles selection and initialization of search strategies
based on configuration and query types.
"""

import logging
from typing import Tuple, Any, Optional, Dict

logger = logging.getLogger('code_index.search_strategy_selector')


class SearchStrategySelector:
    """
    Selects and configures search strategies based on query and configuration.
    """
    
    def __init__(self, config):
        self.config = config
    
    def select_strategy(self, query: str) -> str:
        """
        Select the appropriate search strategy based on query.
        
        Args:
            query: Search query string
            
        Returns:
            Strategy name ('embedding', 'text', 'similarity', 'hybrid')
        """
        # Check if query is a special type
        if query.startswith('similar:'):
            return 'similarity'
        elif query.startswith('hybrid:'):
            return 'hybrid'
        
        # Default to embedding-based search
        return getattr(self.config, 'search_strategy', 'embedding')
    
    def initialize_components(self, config) -> Tuple[Any, Any]:
        """
        Initialize search components (embedder and vector store).
        
        Args:
            config: Configuration object
            
        Returns:
            Tuple of (embedder, vector_store)
        """
        from ...embedder import OllamaEmbedder
        from ...vector_store import QdrantVectorStore
        
        embedder = OllamaEmbedder(config)
        vector_store = QdrantVectorStore(config)
        return embedder, vector_store
    
    def get_search_params(self, config) -> Dict[str, Any]:
        """
        Get search parameters from configuration.
        
        Args:
            config: Configuration object
            
        Returns:
            Dictionary of search parameters
        """
        return {
            'min_score': getattr(config, 'search_min_score', 0.4),
            'max_results': getattr(config, 'search_max_results', 50),
            'strategy': getattr(config, 'search_strategy', 'similarity'),
            'cache_enabled': getattr(config, 'search_cache_enabled', False)
        }
    
    def should_use_cache(self, config) -> bool:
        """Check if caching should be enabled."""
        return getattr(self.config, 'search_cache_enabled', False)
    
    def get_cache_key_components(self, query: str, config) -> Dict[str, Any]:
        """
        Get components for building cache key.
        
        Args:
            query: Search query
            config: Configuration object
            
        Returns:
            Dictionary of cache key components
        """
        return {
            'query': query,
            'workspace': getattr(config, 'workspace_path', ''),
            'min_score': getattr(config, 'search_min_score', 0.4),
            'max_results': getattr(config, 'search_max_results', 50),
            'weights': getattr(config, 'search_file_type_weights', {}),
            'path_boosts': getattr(config, 'search_path_boosts', []),
            'lang_boosts': getattr(config, 'search_language_boosts', {}),
            'exclude_patterns': getattr(config, 'search_exclude_patterns', []),
            'model': getattr(config, 'ollama_model', ''),
            'qdrant_url': getattr(config, 'qdrant_url', '')
        }


def create_strategy_selector(config) -> SearchStrategySelector:
    """Factory function to create a SearchStrategySelector."""
    return SearchStrategySelector(config)
