"""
Configuration persistence module for MCP server.

This module handles configuration documentation, templates, and optimization examples.
"""

from typing import Dict, Any, Optional, List


class ConfigPersistence:
    """
    Handles configuration documentation, templates, and optimization examples.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def get_config_documentation(self) -> Dict[str, Any]:
        """Get comprehensive configuration documentation."""
        return {
            "categories": self._get_configuration_categories(),
            "examples": self.get_optimization_examples(),
            "optimization_strategies": self._get_optimization_strategies(),
            "parameter_compatibility": self._get_parameter_compatibility_matrix(),
            "troubleshooting": self._get_troubleshooting_guide()
        }
    
    def _get_configuration_categories(self) -> Dict[str, Any]:
        """Get detailed configuration categories."""
        return {
            "core": {
                "description": "Core service endpoints and workspace configuration",
                "priority": "required",
                "parameters": {
                    "embedding_length": {
                        "type": "integer",
                        "required": True,
                        "description": "Vector dimension for embeddings"
                    },
                    "ollama_base_url": {
                        "type": "string",
                        "default": "http://localhost:11434",
                        "description": "Base URL for Ollama API service"
                    },
                    "ollama_model": {
                        "type": "string", 
                        "default": "nomic-embed-text:latest",
                        "description": "Ollama model for generating embeddings"
                    },
                    "qdrant_url": {
                        "type": "string",
                        "default": "http://localhost:6333",
                        "description": "Qdrant vector database connection URL"
                    },
                    "workspace_path": {
                        "type": "string",
                        "default": ".",
                        "description": "Default workspace path for indexing operations"
                    }
                }
            },
            "performance": {
                "description": "Performance tuning and resource management settings",
                "priority": "optimization",
                "parameters": {
                    "batch_segment_threshold": {
                        "type": "integer",
                        "default": 60,
                        "description": "Number of code segments to batch together for embedding"
                    },
                    "embed_timeout_seconds": {
                        "type": "integer",
                        "default": 60,
                        "description": "Timeout for individual embedding operations"
                    },
                    "max_file_size_bytes": {
                        "type": "integer",
                        "default": 1048576,
                        "description": "Maximum file size to process (bytes)"
                    },
                    "use_mmap_file_reading": {
                        "type": "boolean",
                        "default": False,
                        "description": "Use memory-mapped file reading for large files"
                    }
                }
            },
            "chunking": {
                "description": "Text chunking strategy and semantic analysis configuration",
                "priority": "core",
                "parameters": {
                    "chunking_strategy": {
                        "type": "string",
                        "default": "lines",
                        "options": ["lines", "tokens", "treesitter"],
                        "description": "Strategy for splitting code into searchable chunks"
                    },
                    "use_tree_sitter": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable semantic code structure analysis"
                    },
                    "tree_sitter_max_blocks_per_file": {
                        "type": "integer",
                        "default": 100,
                        "description": "Maximum code blocks to extract per file"
                    }
                }
            },
            "search": {
                "description": "Search ranking, filtering, and result formatting configuration",
                "priority": "optimization",
                "parameters": {
                    "search_min_score": {
                        "type": "float",
                        "default": 0.4,
                        "description": "Minimum similarity score threshold for search results"
                    },
                    "search_max_results": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum number of search results to return"
                    }
                }
            },
            "advanced": {
                "description": "Advanced features and debugging configuration",
                "priority": "optional",
                "parameters": {
                    "extensions": {
                        "type": "array",
                        "default": [".rs", ".ts", ".vue", ".js", ".py"],
                        "description": "File extensions to index"
                    },
                    "auto_extensions": {
                        "type": "boolean",
                        "default": False,
                        "description": "Automatically detect additional file extensions using Pygments"
                    },
                    "skip_dot_files": {
                        "type": "boolean",
                        "default": True,
                        "description": "Skip hidden files and directories (starting with .)"
                    },
                    "auto_ignore_detection": {
                        "type": "boolean",
                        "default": True,
                        "description": "Automatically apply .gitignore and similar ignore patterns"
                    },
                    "timeout_log_path": {
                        "type": "string",
                        "default": "timeout_files.txt",
                        "description": "File to log embedding timeouts for retry processing"
                    },
                    "tree_sitter_debug_logging": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable detailed Tree-sitter processing logs"
                    }
                }
            }
        }
    
    def _get_optimization_strategies(self) -> Dict[str, Any]:
        """Get optimization strategies."""
        return {
            "speed_optimized": {
                "name": "Speed Optimized",
                "description": "Fastest indexing with minimal accuracy trade-offs",
                "config_changes": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 100
                }
            },
            "accuracy_optimized": {
                "name": "Accuracy Optimized", 
                "description": "Maximum semantic accuracy with Tree-sitter analysis",
                "config_changes": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_max_blocks_per_file": 150
                }
            },
            "balanced": {
                "name": "Balanced",
                "description": "Good balance of speed and accuracy for most use cases",
                "config_changes": {
                    "chunking_strategy": "tokens",
                    "batch_segment_threshold": 60
                }
            },
            "memory_optimized": {
                "name": "Memory Optimized",
                "description": "Minimal memory usage for resource-constrained environments",
                "config_changes": {
                    "batch_segment_threshold": 20,
                    "max_file_size_bytes": 256000,
                    "use_mmap_file_reading": True
                }
            }
        }
    
    def _get_parameter_compatibility_matrix(self) -> Dict[str, Any]:
        """Get parameter compatibility information."""
        return {
            "dependencies": {
                "tree_sitter_*": {
                    "requires": "use_tree_sitter=true",
                    "description": "All tree_sitter_* parameters require Tree-sitter to be enabled"
                },
                "token_chunk_*": {
                    "requires": "chunking_strategy='tokens'",
                    "description": "Token chunking parameters only apply with token strategy"
                }
            },
            "conflicts": {
                "chunking_strategy='treesitter' + use_tree_sitter=false": {
                    "description": "Tree-sitter chunking requires use_tree_sitter=true"
                }
            }
        }
    
    def _get_troubleshooting_guide(self) -> Dict[str, Any]:
        """Get troubleshooting guide."""
        return {
            "common_errors": {
                "embedding_length_mismatch": {
                    "symptoms": ["Vector dimension errors", "Qdrant insertion failures"],
                    "solutions": [
                        "Check your Ollama model's embedding dimension",
                        "Update embedding_length in configuration"
                    ]
                },
                "service_connectivity": {
                    "symptoms": ["Connection refused", "Timeout errors"],
                    "solutions": [
                        "Verify services are running",
                        "Check URLs are accessible"
                    ]
                }
            }
        }
    
    def get_optimization_examples(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive example configurations."""
        return {
            "fast_indexing": {
                "name": "Fast Indexing",
                "description": "Optimized for speed",
                "config": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 100,
                    "search_min_score": 0.3
                }
            },
            "semantic_accuracy": {
                "name": "Semantic Accuracy",
                "description": "Maximum semantic understanding",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_max_blocks_per_file": 150
                }
            },
            "balanced": {
                "name": "Balanced Performance",
                "description": "Good balance of speed and accuracy",
                "config": {
                    "chunking_strategy": "tokens",
                    "batch_segment_threshold": 60,
                    "search_min_score": 0.4
                }
            },
            "memory_optimized": {
                "name": "Memory Optimized",
                "description": "Minimal memory usage",
                "config": {
                    "batch_segment_threshold": 20,
                    "max_file_size_bytes": 256000,
                    "use_mmap_file_reading": True
                }
            },
            "rust_project": {
                "name": "Rust Project Optimization",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_languages": ["rust"],
                    "search_file_type_weights": {".rs": 1.4, ".toml": 1.1}
                }
            },
            "typescript_vue_project": {
                "name": "TypeScript/Vue Project",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_languages": ["typescript", "vue", "javascript"],
                    "search_file_type_weights": {".vue": 1.4, ".ts": 1.3}
                }
            },
            "python_project": {
                "name": "Python Project",
                "config": {
                    "chunking_strategy": "treesitter",
                    "use_tree_sitter": True,
                    "tree_sitter_languages": ["python"],
                    "search_file_type_weights": {".py": 1.3}
                }
            },
            "large_monorepo": {
                "name": "Large Monorepo",
                "config": {
                    "chunking_strategy": "tokens",
                    "use_tree_sitter": True,
                    "batch_segment_threshold": 80,
                    "use_mmap_file_reading": True,
                    "search_max_results": 100
                }
            },
            "ci_cd_optimized": {
                "name": "CI/CD Pipeline",
                "config": {
                    "chunking_strategy": "lines",
                    "use_tree_sitter": False,
                    "batch_segment_threshold": 120,
                    "embed_timeout_seconds": 20
                }
            }
        }
    
    def generate_config_template(self, template_name: str, base_config: Optional[Any] = None) -> Dict[str, Any]:
        """Generate a configuration template."""
        examples = self.get_optimization_examples()
        
        if template_name not in examples:
            available = list(examples.keys())
            raise ValueError(f"Unknown template '{template_name}'. Available: {available}")
        
        template = examples[template_name]
        
        # Start with default configuration
        if base_config:
            config_dict = {}.copy()
        else:
            from ...config import Config
            default_config = Config()
            config_dict = {}.copy()
        
        # Apply template overrides
        template_config = template["config"]
        for key, value in template_config.items():
            config_dict[key] = value
        
        # Add template metadata
        config_dict["_template_info"] = {
            "name": template["name"],
            "description": template["description"]
        }
        
        return config_dict
    
    def get_override_documentation(self) -> Dict[str, Any]:
        """Get documentation for configuration override parameters."""
        return {
            "index_tool_overrides": {
                "description": "Configuration parameters for index operations",
                "parameters": {
                    "embedding_length": {"type": "integer", "description": "Vector dimension"},
                    "chunking_strategy": {"type": "string", "options": ["lines", "tokens", "treesitter"]},
                    "use_tree_sitter": {"type": "boolean"},
                    "batch_segment_threshold": {"type": "integer"}
                }
            },
            "search_tool_overrides": {
                "description": "Configuration parameters for search operations",
                "parameters": {
                    "search_min_score": {"type": "float", "range": "0.0-1.0"},
                    "search_max_results": {"type": "integer"},
                    "search_file_type_weights": {"type": "object"}
                }
            }
        }


def create_persistence(logger=None) -> ConfigPersistence:
    """Factory function to create a ConfigPersistence."""
    return ConfigPersistence(logger)
