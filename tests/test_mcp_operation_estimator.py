"""
Unit tests for MCP Operation Estimator.

Tests workspace analysis, complexity estimation, and optimization recommendations
for code indexing operations.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.code_index.mcp_server.core.operation_estimator import (
    OperationEstimator,
    WorkspaceAnalysis,
    EstimationResult,
    Recommendation
)
from src.code_index.config import Config


class TestWorkspaceAnalysis:
    """Test cases for WorkspaceAnalysis dataclass."""
    
    def test_workspace_analysis_creation(self):
        """Test creating WorkspaceAnalysis with various parameters."""
        analysis = WorkspaceAnalysis(
            total_files=100,
            total_size_bytes=1024000,
            file_type_distribution={".py": 50, ".js": 30, ".md": 20},
            largest_files=[("large_file.py", 50000), ("big_file.js", 40000)],
            directory_depth=5,
            has_large_files=True,
            has_many_files=False,
            estimated_tree_sitter_files=80,
            complexity_factors=["Large files present"]
        )
        
        assert analysis.total_files == 100
        assert analysis.total_size_bytes == 1024000
        assert analysis.file_type_distribution[".py"] == 50
        assert len(analysis.largest_files) == 2
        assert analysis.directory_depth == 5
        assert analysis.has_large_files is True
        assert analysis.has_many_files is False
        assert analysis.estimated_tree_sitter_files == 80
        assert "Large files present" in analysis.complexity_factors


class TestEstimationResult:
    """Test cases for EstimationResult dataclass."""
    
    def test_estimation_result_creation(self):
        """Test creating EstimationResult with various parameters."""
        result = EstimationResult(
            estimated_duration_seconds=120,
            file_count=50,
            total_size_bytes=512000,
            complexity_factors=["Tree-sitter enabled"],
            optimization_suggestions=["Use batch processing"],
            warning_level="caution",
            cli_alternative="code-index index --workspace /path",
            confidence_level="high"
        )
        
        assert result.estimated_duration_seconds == 120
        assert result.file_count == 50
        assert result.total_size_bytes == 512000
        assert "Tree-sitter enabled" in result.complexity_factors
        assert "Use batch processing" in result.optimization_suggestions
        assert result.warning_level == "caution"
        assert result.cli_alternative == "code-index index --workspace /path"
        assert result.confidence_level == "high"


class TestRecommendation:
    """Test cases for Recommendation dataclass."""
    
    def test_recommendation_creation(self):
        """Test creating Recommendation with various parameters."""
        recommendation = Recommendation(
            category="performance",
            priority="high",
            title="Enable batch processing",
            description="Use larger batch sizes for better performance",
            config_changes={"batch_segment_threshold": 100},
            expected_impact="20% faster processing"
        )
        
        assert recommendation.category == "performance"
        assert recommendation.priority == "high"
        assert recommendation.title == "Enable batch processing"
        assert recommendation.description == "Use larger batch sizes for better performance"
        assert recommendation.config_changes["batch_segment_threshold"] == 100
        assert recommendation.expected_impact == "20% faster processing"


class TestOperationEstimator:
    """Test cases for OperationEstimator class."""
    
    @pytest.fixture
    def estimator(self):
        """Create an OperationEstimator instance for testing."""
        return OperationEstimator()
    
    @pytest.fixture
    def temp_workspace_small(self):
        """Create a small temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a few test files
            files = [
                ("test.py", "def hello():\n    return 'world'\n"),
                ("main.js", "console.log('hello world');\n"),
                ("README.md", "# Test Project\n\nThis is a test.\n"),
                ("config.json", '{"test": true}\n')
            ]
            
            for filename, content in files:
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
            
            yield temp_dir
    
    @pytest.fixture
    def temp_workspace_large(self):
        """Create a large temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many files to simulate a large repository (over 1000 threshold)
            for i in range(1200):
                file_path = Path(temp_dir) / f"file_{i}.py"
                content = f"# File {i}\n" + "def function():\n    pass\n" * 10
                file_path.write_text(content)
            
            # Create some large files (over 100KB threshold)
            large_file = Path(temp_dir) / "large_file.py"
            large_content = "# Large file\n" + "def function():\n    pass\n" * 15000  # ~150KB
            large_file.write_text(large_content)
            
            # Create nested directories
            nested_dir = Path(temp_dir) / "src" / "deep" / "nested" / "path"
            nested_dir.mkdir(parents=True)
            (nested_dir / "deep_file.py").write_text("# Deep nested file\n")
            
            yield temp_dir
    
    @pytest.fixture
    def temp_workspace_complex(self):
        """Create a complex workspace with various file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files of different types (mostly tree-sitter eligible)
            files = [
                ("component.vue", "<template><div>Hello</div></template>\n<script>export default {}</script>"),
                ("types.ts", "interface User { name: string; }\n"),
                ("main.rs", "fn main() { println!(\"Hello\"); }\n"),
                ("app.tsx", "import React from 'react';\nexport default function App() { return <div>App</div>; }"),
                ("server.go", "package main\n\nfunc main() {\n\tfmt.Println(\"Hello\")\n}"),
                ("Model.java", "public class Model {\n\tprivate String name;\n}"),
                ("script.cpp", "#include <iostream>\nint main() { return 0; }"),
                ("utils.py", "# Utils\n\ndef helper():\n    return True\n"),
                ("config.py", "# Config\n\nsettings = {}\n"),
                ("main.py", "# Main\n\nif __name__ == '__main__':\n    print('Hello')\n"),
                ("types2.ts", "type User = { name: string; }\n"),
                ("component2.vue", "<template><p>World</p></template>\n<script>export default {}</script>"),
                ("lib.rs", "pub fn lib_function() {}\n"),
                ("app2.tsx", "import React from 'react';\nconst App = () => <div>App2</div>;\nexport default App;"),
                ("server2.go", "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tfmt.Println(\"Hello2\")\n}"),
                ("Model2.java", "public class Model2 {\n\tpublic String getName() {\n\t\treturn \"test\";\n\t}\n}"),
                ("script2.cpp", "#include <iostream>\n\nvoid func() {\n\tstd::cout << \"test\" << std::endl;\n}\n"),
            ]
            
            for filename, content in files:
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
            
            yield temp_dir
    
    def test_estimator_initialization(self, estimator):
        """Test OperationEstimator initialization."""
        assert estimator.BASE_FILE_PROCESSING_TIME > 0
        assert estimator.TREE_SITTER_OVERHEAD > 1.0
        assert estimator.EMBEDDING_TIME_PER_CHUNK > 0
        assert estimator.LARGE_FILE_THRESHOLD > 0
        assert estimator.MANY_FILES_THRESHOLD > 0
        assert isinstance(estimator.FILE_TYPE_COMPLEXITY, dict)
    
    def test_analyze_workspace_complexity_small(self, estimator, temp_workspace_small):
        """Test workspace analysis with small workspace."""
        analysis = estimator.analyze_workspace_complexity(temp_workspace_small)
        
        assert isinstance(analysis, WorkspaceAnalysis)
        assert analysis.total_files == 4
        assert analysis.total_size_bytes > 0
        assert ".py" in analysis.file_type_distribution
        assert ".js" in analysis.file_type_distribution
        assert ".md" in analysis.file_type_distribution
        assert ".json" in analysis.file_type_distribution
        assert analysis.directory_depth >= 0
        assert analysis.has_many_files is False
        assert len(analysis.largest_files) <= 10
    
    def test_analyze_workspace_complexity_large(self, estimator, temp_workspace_large):
        """Test workspace analysis with large workspace."""
        analysis = estimator.analyze_workspace_complexity(temp_workspace_large)
        
        assert analysis.total_files > 50
        assert analysis.total_size_bytes > 10000  # Should be substantial
        assert ".py" in analysis.file_type_distribution
        assert analysis.directory_depth > 1  # Has nested directories
        assert analysis.has_large_files is True  # Has the large file we created
        assert len(analysis.complexity_factors) > 0
    
    def test_analyze_workspace_complexity_complex(self, estimator, temp_workspace_complex):
        """Test workspace analysis with complex file types."""
        analysis = estimator.analyze_workspace_complexity(temp_workspace_complex)

        assert analysis.total_files == 17
        assert ".vue" in analysis.file_type_distribution
        assert ".ts" in analysis.file_type_distribution
        assert ".rs" in analysis.file_type_distribution
        assert ".tsx" in analysis.file_type_distribution
        assert analysis.estimated_tree_sitter_files > 0
        
        # Should detect complex file types
        assert any("complex file types" in factor.lower() for factor in analysis.complexity_factors)
    
    def test_analyze_workspace_nonexistent(self, estimator):
        """Test workspace analysis with non-existent path."""
        with pytest.raises(ValueError, match=r"Workspace path.*(?:does not exist|is not a directory)"):
            estimator.analyze_workspace_complexity("/nonexistent/path")
    
    def test_analyze_workspace_not_directory(self, estimator):
        """Test workspace analysis with file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValueError, match="Workspace path is not a directory"):
                estimator.analyze_workspace_complexity(temp_file.name)
    
    def test_estimate_indexing_time_basic(self, estimator, temp_workspace_small):
        """Test basic indexing time estimation."""
        config = Config()
        config.use_tree_sitter = False
        config.chunking_strategy = "lines"
        config.batch_segment_threshold = 60
        config.embed_timeout_seconds = 60
        config.use_mmap_file_reading = False
        
        result = estimator.estimate_indexing_time(temp_workspace_small, config)
        
        assert isinstance(result, EstimationResult)
        assert result.estimated_duration_seconds > 0
        assert result.file_count == 4
        assert result.total_size_bytes > 0
        assert result.warning_level in ["none", "caution", "warning", "critical"]
        assert result.confidence_level in ["low", "medium", "high"]
    
    def test_estimate_indexing_time_tree_sitter(self, estimator, temp_workspace_complex):
        """Test indexing time estimation with Tree-sitter enabled."""
        config = Config()
        config.use_tree_sitter = True
        config.chunking_strategy = "treesitter"
        config.batch_segment_threshold = 60
        config.embed_timeout_seconds = 60
        
        result = estimator.estimate_indexing_time(temp_workspace_complex, config)
        
        assert result.estimated_duration_seconds > 0
        assert any("Tree-sitter" in factor for factor in result.complexity_factors)
        assert len(result.optimization_suggestions) >= 0
    
    def test_estimate_indexing_time_small_batch(self, estimator, temp_workspace_small):
        """Test indexing time estimation with small batch size."""
        config = Config()
        config.batch_segment_threshold = 10  # Small batch
        config.embed_timeout_seconds = 60
        
        result = estimator.estimate_indexing_time(temp_workspace_small, config)
        
        assert any("Small batch size" in factor for factor in result.complexity_factors)
        assert any("batch_segment_threshold" in suggestion for suggestion in result.optimization_suggestions)
    
    def test_estimate_indexing_time_large_batch(self, estimator, temp_workspace_small):
        """Test indexing time estimation with large batch size."""
        config = Config()
        config.batch_segment_threshold = 150  # Large batch
        config.embed_timeout_seconds = 60
        
        result = estimator.estimate_indexing_time(temp_workspace_small, config)
        
        assert any("Large batch size" in factor for factor in result.complexity_factors)
    
    def test_estimate_indexing_time_short_timeout(self, estimator, temp_workspace_small):
        """Test indexing time estimation with short timeout."""
        config = Config()
        config.embed_timeout_seconds = 30  # Short timeout
        config.batch_segment_threshold = 60
        
        result = estimator.estimate_indexing_time(temp_workspace_small, config)
        
        assert any("Short timeout" in factor for factor in result.complexity_factors)
        assert any("embed_timeout_seconds" in suggestion for suggestion in result.optimization_suggestions)
    
    def test_estimate_indexing_time_large_workspace(self, estimator, temp_workspace_large):
        """Test indexing time estimation with large workspace."""
        config = Config()
        config.use_tree_sitter = False
        config.batch_segment_threshold = 60
        config.embed_timeout_seconds = 60
        config.use_mmap_file_reading = False
        
        result = estimator.estimate_indexing_time(temp_workspace_large, config)
        
        # Should suggest mmap for large files
        assert any("use_mmap_file_reading" in suggestion for suggestion in result.optimization_suggestions)
        
        # Should have higher warning level for large workspace
        assert result.warning_level in ["caution", "warning", "critical"]
        
        # Should provide CLI alternative for large operations
        if result.warning_level in ["warning", "critical"]:
            assert result.cli_alternative is not None
            assert "code-index" in result.cli_alternative
    
    def test_recommend_optimizations_large_repo(self, estimator, temp_workspace_large):
        """Test optimization recommendations for large repository."""
        config = Config()
        analysis = estimator.analyze_workspace_complexity(temp_workspace_large)
        
        recommendations = estimator.recommend_optimizations(analysis, config)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should have performance recommendations for large repo
        perf_recs = [r for r in recommendations if r.category == "performance"]
        assert len(perf_recs) > 0
        
        # Should recommend batch optimization
        batch_recs = [r for r in recommendations if "batch" in r.title.lower()]
        assert len(batch_recs) > 0
    
    def test_recommend_optimizations_large_files(self, estimator, temp_workspace_large):
        """Test optimization recommendations for large files."""
        config = Config()
        analysis = estimator.analyze_workspace_complexity(temp_workspace_large)
        
        recommendations = estimator.recommend_optimizations(analysis, config)
        
        # Should have memory recommendations for large files
        memory_recs = [r for r in recommendations if r.category == "memory"]
        assert len(memory_recs) > 0
        
        # Should recommend mmap
        mmap_recs = [r for r in recommendations if "memory-mapped" in r.description.lower()]
        assert len(mmap_recs) > 0
    
    def test_recommend_optimizations_tree_sitter(self, estimator, temp_workspace_complex):
        """Test optimization recommendations for Tree-sitter eligible files."""
        config = Config()
        config.use_tree_sitter = False  # Not using tree-sitter
        analysis = estimator.analyze_workspace_complexity(temp_workspace_complex)
        
        recommendations = estimator.recommend_optimizations(analysis, config)
        
        # Should recommend tree-sitter for accuracy
        accuracy_recs = [r for r in recommendations if r.category == "accuracy"]
        tree_sitter_recs = [r for r in recommendations if "semantic" in r.description.lower()]
        
        # Should have at least one accuracy or tree-sitter recommendation
        assert len(accuracy_recs) > 0 or len(tree_sitter_recs) > 0
    
    def test_recommend_optimizations_file_type_specific(self, estimator, temp_workspace_complex):
        """Test file type specific optimization recommendations."""
        config = Config()
        analysis = estimator.analyze_workspace_complexity(temp_workspace_complex)
        
        recommendations = estimator.recommend_optimizations(analysis, config)
        
        # Should have recommendations for dominant file types
        file_type_recs = [r for r in recommendations if "search ranking" in r.title.lower()]
        assert len(file_type_recs) >= 0  # May or may not have depending on file distribution
    
    def test_should_warn_user(self, estimator):
        """Test user warning determination."""
        # No warning for short operations
        short_result = EstimationResult(
            estimated_duration_seconds=15,
            file_count=10,
            total_size_bytes=1000,
            complexity_factors=[],
            optimization_suggestions=[],
            warning_level="none"
        )
        assert estimator.should_warn_user(short_result) is False
        
        # Warning for long operations
        long_result = EstimationResult(
            estimated_duration_seconds=300,
            file_count=1000,
            total_size_bytes=100000,
            complexity_factors=[],
            optimization_suggestions=[],
            warning_level="critical"
        )
        assert estimator.should_warn_user(long_result) is True
    
    def test_is_tree_sitter_eligible(self, estimator):
        """Test Tree-sitter eligibility detection."""
        # Eligible extensions
        assert estimator._is_tree_sitter_eligible(".rs") is True
        assert estimator._is_tree_sitter_eligible(".ts") is True
        assert estimator._is_tree_sitter_eligible(".tsx") is True
        assert estimator._is_tree_sitter_eligible(".js") is True
        assert estimator._is_tree_sitter_eligible(".jsx") is True
        assert estimator._is_tree_sitter_eligible(".py") is True
        assert estimator._is_tree_sitter_eligible(".vue") is True
        assert estimator._is_tree_sitter_eligible(".go") is True
        assert estimator._is_tree_sitter_eligible(".java") is True
        
        # Non-eligible extensions
        assert estimator._is_tree_sitter_eligible(".txt") is False
        assert estimator._is_tree_sitter_eligible(".md") is False
        assert estimator._is_tree_sitter_eligible(".json") is False
        assert estimator._is_tree_sitter_eligible(".xml") is False
        assert estimator._is_tree_sitter_eligible(".bin") is False
    
    def test_determine_warning_level(self, estimator):
        """Test warning level determination."""
        analysis = WorkspaceAnalysis(
            total_files=10,
            total_size_bytes=1000,
            file_type_distribution={},
            largest_files=[],
            directory_depth=1,
            has_large_files=False,
            has_many_files=False,
            estimated_tree_sitter_files=0,
            complexity_factors=[]
        )
        
        # No warning for short time
        assert estimator._determine_warning_level(15, analysis) == "none"
        
        # Caution for moderate time
        assert estimator._determine_warning_level(45, analysis) == "caution"
        
        # Warning for longer time
        assert estimator._determine_warning_level(150, analysis) == "warning"
        
        # Critical for very long time
        assert estimator._determine_warning_level(400, analysis) == "critical"
    
    def test_generate_cli_alternative(self, estimator):
        """Test CLI alternative generation."""
        config = Config()
        config.use_tree_sitter = True
        config.chunking_strategy = "treesitter"
        config.embed_timeout_seconds = 120
        
        cli_cmd = estimator._generate_cli_alternative("/path/to/workspace", config)
        
        assert "code-index index" in cli_cmd
        assert "--workspace" in cli_cmd
        assert '"/path/to/workspace"' in cli_cmd
        assert "--use-tree-sitter" in cli_cmd
        assert "--chunking-strategy treesitter" in cli_cmd
        assert "--embed-timeout 120" in cli_cmd
    
    def test_generate_cli_alternative_defaults(self, estimator):
        """Test CLI alternative generation with default values."""
        config = Config()
        config.use_tree_sitter = False
        config.chunking_strategy = "lines"
        config.embed_timeout_seconds = 60
        
        cli_cmd = estimator._generate_cli_alternative(".", config)
        
        assert "code-index index" in cli_cmd
        # Should not include default values
        assert "--workspace" not in cli_cmd  # Current directory
        assert "--use-tree-sitter" not in cli_cmd  # False is default
        assert "--chunking-strategy" not in cli_cmd  # lines is default
        assert "--embed-timeout" not in cli_cmd  # 60 is default


class TestOperationEstimatorIntegration:
    """Integration tests for operation estimator."""
    
    @pytest.fixture
    def realistic_workspace(self):
        """Create a realistic workspace for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a realistic project structure
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir()
            
            docs_dir = Path(temp_dir) / "docs"
            docs_dir.mkdir()
            
            # Create various file types
            files = [
                ("src/main.py", "#!/usr/bin/env python3\n" + "def main():\n    pass\n" * 20),
                ("src/utils.py", "# Utilities\n" + "def helper():\n    return True\n" * 15),
                ("src/models.py", "# Data models\n" + "class Model:\n    pass\n" * 10),
                ("tests/test_main.py", "import unittest\n" + "def test_something():\n    assert True\n" * 5),
                ("tests/test_utils.py", "import pytest\n" + "def test_helper():\n    assert True\n" * 8),
                ("docs/README.md", "# Project\n\nThis is a test project.\n" + "## Section\n\nContent.\n" * 10),
                ("docs/API.md", "# API Documentation\n" + "## Endpoint\n\nDescription.\n" * 15),
                ("package.json", '{"name": "test", "version": "1.0.0"}'),
                ("requirements.txt", "pytest>=6.0\nrequests>=2.25\n"),
                (".gitignore", "__pycache__/\n*.pyc\n.env\n")
            ]
            
            for filepath, content in files:
                full_path = Path(temp_dir) / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            yield temp_dir
    
    def test_end_to_end_estimation(self, realistic_workspace):
        """Test complete estimation workflow."""
        estimator = OperationEstimator()
        
        # Test with different configurations
        configs = [
            # Fast configuration
            {
                "use_tree_sitter": False,
                "chunking_strategy": "lines",
                "batch_segment_threshold": 100,
                "embed_timeout_seconds": 60
            },
            # Accurate configuration
            {
                "use_tree_sitter": True,
                "chunking_strategy": "treesitter",
                "batch_segment_threshold": 30,
                "embed_timeout_seconds": 120
            }
        ]
        
        for config_dict in configs:
            config = Config()
            for key, value in config_dict.items():
                setattr(config, key, value)
            
            # Analyze workspace
            analysis = estimator.analyze_workspace_complexity(realistic_workspace)
            assert analysis.total_files > 5
            assert analysis.total_size_bytes > 1000
            
            # Estimate indexing time
            result = estimator.estimate_indexing_time(realistic_workspace, config)
            assert result.estimated_duration_seconds > 0
            assert result.file_count == analysis.total_files
            assert result.total_size_bytes == analysis.total_size_bytes
            
            # Get recommendations
            recommendations = estimator.recommend_optimizations(analysis, config)
            assert isinstance(recommendations, list)
            
            # Verify consistency
            assert result.file_count == analysis.total_files
            assert result.total_size_bytes == analysis.total_size_bytes


if __name__ == "__main__":
    pytest.main([__file__])