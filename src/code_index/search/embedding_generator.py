"""
Search embedding generator for generating vector embeddings for search operations.
"""
import time
from typing import List, Dict, Any, Optional

from ..config import Config
from ..errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


class EmbeddingGenerator:
    """Generate embeddings for search operations."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize embedding generator."""
        self.error_handler = error_handler or ErrorHandler()
    
    def generate_embedding(self, text: str, config: Config) -> Optional[List[float]]:
        """Generate embedding for a text."""
        try:
            if not text or not text.strip():
                return None
            
            # Simulate embedding generation
            import random
            import numpy as np
            
            # Generate random embedding vector
            embedding = [random.random() for _ in range(getattr(config, "embedding_dimensions", 384))]
            
            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = [e / norm for e in embedding]
            
            return embedding
        except Exception as e:
            error_context = ErrorContext(
                component="embedding_generator",
                operation="generate_embedding"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
            )
            return None
    
    def generate_batch_embeddings(self, texts: List[str], config: Config) -> Dict[str, Any]:
        """Generate embeddings for multiple texts."""
        try:
            embeddings = {}
            for text in texts:
                embedding = self.generate_embedding(text, config)
                if embedding:
                    embeddings[text] = {
                        "embedding": embedding,
                        "original_text": text,
                        "config_info": {
                            "model_used": getattr(config, "ollama_model", "llama3.2:3b"),
                            "config_hash": getattr(config, "config_hash", "unknown"),
                            "timestamp": time.time()
                        }
                    }
            
            return {
                "embeddings": embeddings,
            }
        except Exception as e:
            error_context = ErrorContext(
                component="embedding_generator",
                operation="generate_batch_embeddings"
            )
            error_response = self.error_handler.handle_error(
                e, error_context, ErrorCategory.SEARCH, ErrorSeverity.MEDIUM
            )
            return {
                "error": error_response.message
            }