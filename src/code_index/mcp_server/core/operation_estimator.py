"""
Operation Estimator for MCP Server

Provides workspace analysis, complexity estimation, and optimization recommendations
for code indexing operations.
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from ...config import Config
from ...scanner import DirectoryScanner


@dataclass
class WorkspaceAnalysis:
    """Analysis results for a workspace"""
    total_files: int
    total_size_bytes: int
    file_type_distribution: Dict[str, int]
    largest_files: List[Tuple[str, int]]  # (path, size) pairs
    directory_depth: int
    has_large_files: bool
    has_many_files: bool
    estimated_tree_sitter_files: int
    complexity_factors: List[str]


@dataclass
class EstimationResult:
    """Results from operation complexity estimation"""
    estimated_duration_seconds: int
    file_count: int
    total_size_bytes: int
    complexity_factors: List[str]
    optimization_suggestions: List[str]
    warning_level: str  # "none", "caution", "warning", "critical"
    cli_alternative: Optional[str] = None
    confidence_level: str = "medium"  # "low", "medium", "high"


@dataclass
class Recommendation:
    """Optimization recommendation"""
    category: str  # "performance", "accuracy", "memory"
    priority: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    config_changes: Dict[str, Any]
    expected_impact: str


class OperationEstimator:
    """
    Estimates operation complexity and provides optimization recommendations
    for code indexing operations.
    """
    
    def __init__(self):
        """Initialize the operation estimator."""
        self.logger = logging.getLogger(__name__)
        
        # Estimation constants based on empirical testing
        self.BASE_FILE_PROCESSING_TIME = 0.05  # seconds per file (baseline)
        self.TREE_SITTER_OVERHEAD = 2.0  # multiplier for tree-sitter processing
        self.EMBEDDING_TIME_PER_CHUNK = 0.1  # seconds per chunk for embedding
        self.LARGE_FILE_THRESHOLD = 100 * 1024  # 100KB
        self.MANY_FILES_THRESHOLD = 1000
        self.CRITICAL_FILES_THRESHOLD = 5000
        
        # File type complexity multipliers
        self.FILE_TYPE_COMPLEXITY = {
            '.rs': 1.3,    # Rust files tend to be complex
            '.ts': 1.2,    # TypeScript complexity
            '.tsx': 1.2,   # TypeScript JSX
            '.vue': 1.4,   # Vue single-file components
            '.cpp': 1.3,   # C++ complexity
            '.hpp': 1.2,   # C++ headers
            '.java': 1.1,  # Java verbosity
            '.py': 1.0,    # Python baseline
            '.js': 0.9,    # JavaScript simpler
            '.jsx': 1.0,   # React JSX
            '.go': 0.9,    # Go simplicity
            '.md': 0.3,    # Markdown is simple
            '.txt': 0.2,   # Plain text
            '.json': 0.1,  # JSON is structured
            '.yaml': 0.2,  # YAML is simple
            '.yml': 0.2,   # YAML is simple
        }
    
    def analyze_workspace_complexity(self, workspace: str) -> WorkspaceAnalysis:
        """
        Analyze workspace to understand its complexity characteristics.
        
        Args:
            workspace: Path to workspace directory
            
        Returns:
            WorkspaceAnalysis with detailed workspace characteristics
        """
        workspace_path = Path(workspace).resolve()

        # Check if path exists first
        if not workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {workspace}")

        if not workspace_path.is_dir():
            raise ValueError(f"Workspace path is not a directory: {workspace}")
        
        # Initialize analysis
        total_files = 0
        total_size = 0
        file_type_dist = {}
        largest_files = []
        max_depth = 0
        tree_sitter_files = 0
        complexity_factors = []
        
        # Walk through workspace
        for root, dirs, files in os.walk(workspace_path):
            # Calculate directory depth
            depth = len(Path(root).relative_to(workspace_path).parts)
            max_depth = max(max_depth, depth)
            
            for file in files:
                file_path = Path(root) / file
                
                try:
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    total_files += 1
                    
                    # Track file type distribution
                    ext = file_path.suffix.lower()
                    file_type_dist[ext] = file_type_dist.get(ext, 0) + 1
                    
                    # Track largest files
                    largest_files.append((str(file_path.relative_to(workspace_path)), file_size))
                    
                    # Estimate tree-sitter eligible files
                    if self._is_tree_sitter_eligible(ext):
                        tree_sitter_files += 1
                        
                except (OSError, IOError):
                    # Skip files we can't access
                    continue
        
        # Sort largest files by size
        largest_files.sort(key=lambda x: x[1], reverse=True)
        largest_files = largest_files[:10]  # Keep top 10
        
        # Determine complexity factors
        if total_files > self.MANY_FILES_THRESHOLD:
            complexity_factors.append(f"Large number of files ({total_files:,})")
        
        if total_files > self.CRITICAL_FILES_THRESHOLD:
            complexity_factors.append(f"Very large repository ({total_files:,} files)")
        
        if total_size > 100 * 1024 * 1024:  # 100MB
            complexity_factors.append(f"Large total size ({total_size / (1024*1024):.1f}MB)")
        
        if max_depth > 10:
            complexity_factors.append(f"Deep directory structure ({max_depth} levels)")
        
        if tree_sitter_files > total_files * 0.8:
            complexity_factors.append("High proportion of complex code files")
        
        # Check for specific patterns that increase complexity
        if any(ext in file_type_dist for ext in ['.vue', '.tsx', '.rs']):
            complexity_factors.append("Contains complex file types (Vue/TSX/Rust)")
        
        return WorkspaceAnalysis(
            total_files=total_files,
            total_size_bytes=total_size,
            file_type_distribution=file_type_dist,
            largest_files=largest_files,
            directory_depth=max_depth,
            has_large_files=any(size > self.LARGE_FILE_THRESHOLD for _, size in largest_files[:5]),
            has_many_files=total_files > self.MANY_FILES_THRESHOLD,
            estimated_tree_sitter_files=tree_sitter_files,
            complexity_factors=complexity_factors
        )
    
    def estimate_indexing_time(self, workspace: str, config: Config) -> EstimationResult:
        """
        Estimate indexing time based on workspace analysis and configuration.
        
        Args:
            workspace: Path to workspace directory
            config: Configuration object
            
        Returns:
            EstimationResult with time estimates and recommendations
        """
        # Analyze workspace
        analysis = self.analyze_workspace_complexity(workspace)
        
        # Base time calculation
        base_time = analysis.total_files * self.BASE_FILE_PROCESSING_TIME
        
        # Apply configuration-based multipliers
        multiplier = 1.0
        complexity_factors = list(analysis.complexity_factors)
        optimization_suggestions = []
        
        # Tree-sitter overhead
        if config.use_tree_sitter or config.chunking_strategy == "treesitter":
            multiplier *= self.TREE_SITTER_OVERHEAD
            complexity_factors.append("Tree-sitter semantic analysis enabled")
            if analysis.estimated_tree_sitter_files > 500:
                optimization_suggestions.append(
                    "Consider disabling tree_sitter_skip_test_files=false for faster processing"
                )
        
        # File type complexity
        type_complexity = 1.0
        for ext, count in analysis.file_type_distribution.items():
            if ext in self.FILE_TYPE_COMPLEXITY:
                weight = count / analysis.total_files
                type_complexity += (self.FILE_TYPE_COMPLEXITY[ext] - 1.0) * weight
        
        multiplier *= type_complexity
        
        # Batch size impact
        if config.batch_segment_threshold < 30:
            multiplier *= 1.2
            complexity_factors.append("Small batch size increases overhead")
            optimization_suggestions.append("Increase batch_segment_threshold to 60+ for better performance")
        elif config.batch_segment_threshold > 100:
            multiplier *= 0.9
            complexity_factors.append("Large batch size improves efficiency")
        
        # Timeout configuration impact
        if config.embed_timeout_seconds < 60:
            complexity_factors.append("Short timeout may cause failures")
            optimization_suggestions.append("Consider increasing embed_timeout_seconds to 120+ for large files")
        
        # Memory mapping benefits
        if not config.use_mmap_file_reading and analysis.has_large_files:
            optimization_suggestions.append("Enable use_mmap_file_reading for better memory efficiency with large files")
        
        # Calculate final estimate
        estimated_seconds = int(base_time * multiplier)
        
        # Add embedding time estimate (rough approximation)
        estimated_chunks = analysis.total_files * 5  # Rough estimate of chunks per file
        embedding_time = estimated_chunks * self.EMBEDDING_TIME_PER_CHUNK
        estimated_seconds += int(embedding_time)
        
        # Determine warning level and CLI alternative
        warning_level = self._determine_warning_level(estimated_seconds, analysis)
        cli_alternative = self._generate_cli_alternative(workspace, config) if warning_level in ["warning", "critical"] else None
        
        # Add size-based suggestions
        if analysis.total_files > self.CRITICAL_FILES_THRESHOLD:
            optimization_suggestions.extend([
                "Consider using workspacelist to process in smaller batches",
                "Use exclude_files_path to skip generated/vendor files",
                "Enable tree_sitter_skip_examples and tree_sitter_skip_test_files"
            ])
        
        # Confidence level based on analysis quality
        confidence = "high" if analysis.total_files > 10 else "medium" if analysis.total_files > 0 else "low"
        
        return EstimationResult(
            estimated_duration_seconds=estimated_seconds,
            file_count=analysis.total_files,
            total_size_bytes=analysis.total_size_bytes,
            complexity_factors=complexity_factors,
            optimization_suggestions=optimization_suggestions,
            warning_level=warning_level,
            cli_alternative=cli_alternative,
            confidence_level=confidence
        )
    
    def recommend_optimizations(self, analysis: WorkspaceAnalysis, config: Config) -> List[Recommendation]:
        """
        Generate optimization recommendations based on workspace analysis.
        
        Args:
            analysis: Workspace analysis results
            config: Current configuration
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Performance recommendations
        if analysis.has_many_files:
            recommendations.append(Recommendation(
                category="performance",
                priority="high",
                title="Optimize batch processing for large repository",
                description="Large repositories benefit from optimized batch sizes and timeouts",
                config_changes={
                    "batch_segment_threshold": 30,
                    "embed_timeout_seconds": 120,
                    "use_mmap_file_reading": True
                },
                expected_impact="20-30% faster processing"
            ))
        
        # Memory recommendations
        if analysis.has_large_files:
            recommendations.append(Recommendation(
                category="memory",
                priority="medium",
                title="Enable memory-mapped file reading",
                description="Large files benefit from memory-mapped reading to reduce memory usage",
                config_changes={
                    "use_mmap_file_reading": True,
                    "mmap_min_file_size_bytes": 32 * 1024
                },
                expected_impact="Reduced memory usage for large files"
            ))
        
        # Accuracy vs performance trade-offs
        if analysis.estimated_tree_sitter_files > 10 and not config.use_tree_sitter:
            recommendations.append(Recommendation(
                category="accuracy",
                priority="medium",
                title="Enable semantic chunking for better search accuracy",
                description="Your codebase has many files that would benefit from semantic analysis",
                config_changes={
                    "use_tree_sitter": True,
                    "chunking_strategy": "treesitter",
                    "tree_sitter_skip_test_files": True
                },
                expected_impact="Better search accuracy, 2x processing time"
            ))
        
        # File type specific optimizations
        dominant_types = sorted(analysis.file_type_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if dominant_types and dominant_types[0][0] in ['.rs', '.ts', '.vue']:
            file_type = dominant_types[0][0]
            recommendations.append(Recommendation(
                category="accuracy",
                priority="low",
                title=f"Optimize search ranking for {file_type} files",
                description=f"Your codebase is primarily {file_type} files - optimize search weights",
                config_changes={
                    "search_file_type_weights": {file_type: 1.3}
                },
                expected_impact="Better search result ranking"
            ))
        
        return recommendations
    
    def should_warn_user(self, estimation: EstimationResult) -> bool:
        """
        Determine if user should be warned about operation duration.
        
        Args:
            estimation: Estimation results
            
        Returns:
            True if user should be warned
        """
        return estimation.warning_level in ["warning", "critical"]
    
    def _is_tree_sitter_eligible(self, extension: str) -> bool:
        """Check if file extension is eligible for tree-sitter processing."""
        tree_sitter_extensions = {
            '.rs', '.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.java',
            '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
            '.kt', '.scala', '.vue'
        }
        return extension in tree_sitter_extensions
    
    def _determine_warning_level(self, estimated_seconds: int, analysis: WorkspaceAnalysis) -> str:
        """Determine appropriate warning level based on estimation."""
        if estimated_seconds > 300:  # 5 minutes
            return "critical"
        elif estimated_seconds > 120:  # 2 minutes
            return "warning"
        elif estimated_seconds > 30:  # 30 seconds
            return "caution"
        else:
            return "none"
    
    def _generate_cli_alternative(self, workspace: str, config: Config) -> str:
        """Generate CLI command alternative for long-running operations."""
        cmd_parts = ["code-index", "index"]
        
        if workspace != ".":
            cmd_parts.extend(["--workspace", f'"{workspace}"'])
        
        if config.use_tree_sitter:
            cmd_parts.append("--use-tree-sitter")
        
        if config.chunking_strategy != "lines":
            cmd_parts.extend(["--chunking-strategy", config.chunking_strategy])
        
        if config.embed_timeout_seconds != 60:
            cmd_parts.extend(["--embed-timeout", str(config.embed_timeout_seconds)])
        
        return " ".join(cmd_parts)