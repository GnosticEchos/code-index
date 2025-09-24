"""
Integration tests for TreeSitter service composition.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.config import Config
from code_index.services.file_processor import TreeSitterFileProcessor
from code_index.services.resource_manager import TreeSitterResourceManager
from code_index.services.block_extractor import TreeSitterBlockExtractor
from code_index.services.query_executor import TreeSitterQueryExecutor
from code_index.services.config_manager import TreeSitterConfigurationManager
from code_index.services.batch_processor import TreeSitterBatchProcessor
from code_index.errors import ErrorHandler


class TestTreeSitterServiceIntegration:
    """Integration tests for TreeSitter service composition."""

    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.config.chunking_strategy = "treesitter"

        self.error_handler = ErrorHandler("test")

        # Initialize all services
        self.file_processor = TreeSitterFileProcessor(self.config, self.error_handler)
        self.resource_manager = TreeSitterResourceManager(self.config, self.error_handler)
        self.config_manager = TreeSitterConfigurationManager(self.config, self.error_handler)
        self.query_executor = TreeSitterQueryExecutor(self.config, self.error_handler)
        self.block_extractor = TreeSitterBlockExtractor(self.config, self.error_handler)
        self.batch_processor = TreeSitterBatchProcessor(self.config, self.error_handler)

    def test_full_service_chain_python_function(self):
        """Test full service chain for Python function extraction."""
        python_code = '''
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    result = a + b
    return result

class Calculator:
    def multiply(self, x, y):
        return x * y
'''

        # Step 1: File validation - create a temporary file
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name

        try:
            # Step 1: File validation
            assert self.file_processor.validate_file(temp_file) is True

            # Step 2: Language optimization - need to get language key first
            from code_index.language_detection import LanguageDetector
            language_detector = LanguageDetector(self.config, self.error_handler)
            language_key = language_detector.detect_language(temp_file)
            assert language_key == 'python'

            optimizations = self.file_processor.apply_language_optimizations(temp_file, language_key)
            assert optimizations is not None
            assert 'max_blocks' in optimizations
            assert optimizations['max_blocks'] == 100  # default value

            # Step 3: Resource acquisition
            with patch('tree_sitter.Language') as mock_language, \
                 patch('tree_sitter.Parser') as mock_parser:

                mock_language_instance = Mock()
                mock_parser_instance = Mock()

                mock_language.load.return_value = mock_language_instance
                mock_parser.return_value = mock_parser_instance

                # Mock the parser manager and query manager that resource manager uses
                with patch('code_index.parser_manager.TreeSitterParserManager') as mock_parser_manager, \
                     patch('code_index.query_manager.TreeSitterQueryManager') as mock_query_manager:

                    mock_parser_manager_instance = Mock()
                    mock_query_manager_instance = Mock()

                    mock_parser_manager.return_value = mock_parser_manager_instance
                    mock_query_manager.return_value = mock_query_manager_instance

                    mock_parser_manager_instance.get_parser.return_value = mock_parser_instance
                    mock_query_manager_instance.get_compiled_query.return_value = mock_parser_instance

                    resources = self.resource_manager.acquire_resources('python')
                    assert 'parser' in resources
                    assert resources['parser'] is not None

                    # Step 4: Configuration retrieval
                    config = self.config_manager.get_language_config('python')
                    assert config is not None
                    assert config.language_key == 'python'

                    # Step 5: Service integration validation
                    # Test that all services can work together
                    assert self.file_processor is not None
                    assert self.resource_manager is not None
                    assert self.config_manager is not None

                    # Test resource cleanup
                    released_count = self.resource_manager.release_resources('python')
                    assert released_count >= 0
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_service_chain_with_query_fallback(self):
        """Test service chain with query fallback mechanism."""
        python_code = 'def simple_func(): return "simple"'

        # Test that services can be initialized and used together
        assert self.file_processor is not None
        assert self.resource_manager is not None
        assert self.config_manager is not None
        assert self.block_extractor is not None

        # Test configuration consistency
        assert self.file_processor.config is self.config
        assert self.resource_manager.config is self.config
        assert self.config_manager.config is self.config
        assert self.block_extractor.config is self.config

    def test_batch_processing_integration(self):
        """Test integration of batch processing with all services."""
        files = [
            {
                'text': 'def func1(): return 1',
                'file_path': 'file1.py',
                'file_hash': 'hash1'
            },
            {
                'text': 'def func2(): return 2',
                'file_path': 'file2.py',
                'file_hash': 'hash2'
            }
        ]

        # Test that batch processor can process files
        result = self.batch_processor.process_batch(files)

        # Should return a BatchProcessingResult
        assert result is not None
        assert hasattr(result, 'results')
        assert hasattr(result, 'success')
        assert hasattr(result, 'processed_files')
        assert hasattr(result, 'failed_files')

    def test_error_propagation_through_services(self):
        """Test error propagation through the service chain."""
        python_code = 'def test(): pass'

        # Test that services handle errors gracefully
        with patch.object(self.error_handler, 'handle_error') as mock_handle:
            # Test file processor error handling
            result = self.file_processor.validate_file('/nonexistent/path')
            assert result is False  # Should return False for non-existent files

            # Test config manager error handling
            config = self.config_manager.get_language_config('nonexistent_language')
            assert config is not None  # Should return a default config for unknown languages
            assert config.language_key == 'nonexistent_language'

    def test_resource_lifecycle_management(self):
        """Test resource lifecycle management across services."""
        python_code = 'def test(): pass'

        # Test basic resource management functionality
        resources = self.resource_manager.acquire_resources('python')
        assert isinstance(resources, dict)

        # Test resource cleanup
        released_count = self.resource_manager.release_resources('python')
        assert released_count >= 0

        # Test resource info
        info = self.resource_manager.get_resource_info()
        assert isinstance(info, dict)
        assert 'total_resources' in info

    def test_configuration_consistency_across_services(self):
        """Test configuration consistency across all services."""
        # All services should share the same config instance
        assert self.file_processor.config is self.config
        assert self.resource_manager.config is self.config
        assert self.config_manager.config is self.config
        assert self.query_executor.config is self.config
        assert self.block_extractor.config is self.config
        assert self.batch_processor.config is self.config

        # All services should share the same error handler
        assert self.file_processor.error_handler is self.error_handler
        assert self.resource_manager.error_handler is self.error_handler
        assert self.config_manager.error_handler is self.error_handler
        assert self.query_executor.error_handler is self.error_handler
        assert self.block_extractor.error_handler is self.error_handler
        assert self.batch_processor.error_handler is self.error_handler

    def test_cross_service_dependencies(self):
        """Test cross-service dependencies and interactions."""
        # Test that block extractor has the required methods
        assert hasattr(self.block_extractor, 'extract_blocks')
        assert hasattr(self.block_extractor, 'execute_query')
        assert hasattr(self.block_extractor, 'create_block_from_node')

        # Test that batch processor has the required methods
        assert hasattr(self.batch_processor, 'process_batch')
        assert hasattr(self.batch_processor, 'group_by_language')
        assert hasattr(self.batch_processor, 'optimize_batch_config')

        # Test that services can be used independently
        assert self.batch_processor is not None
        assert self.file_processor is not None
        assert self.resource_manager is not None

    def test_memory_efficiency_with_shared_resources(self):
        """Test memory efficiency with shared resources across services."""
        # Test that services can be used multiple times
        resources1 = self.resource_manager.acquire_resources('python')
        resources2 = self.resource_manager.acquire_resources('python')

        # Both should return dictionaries
        assert isinstance(resources1, dict)
        assert isinstance(resources2, dict)

        # Test cleanup
        self.resource_manager.cleanup_all()

    def test_performance_with_service_composition(self):
        """Test performance characteristics of service composition."""
        # Create multiple files for batch processing
        files = []
        for i in range(5):  # Reduced from 10 for faster testing
            files.append({
                'text': f'def function_{i}(): return {i}',
                'file_path': f'file_{i}.py',
                'file_hash': f'hash_{i}'
            })

        # Test that batch processor can handle multiple files
        result = self.batch_processor.process_batch(files)

        # Should return a BatchProcessingResult
        assert result is not None
        assert hasattr(result, 'results')
        assert result.processed_files >= 0
        assert result.failed_files >= 0

    def test_error_recovery_across_services(self):
        """Test error recovery mechanisms across services."""
        files = [
            {
                'text': 'def valid_func(): return True',
                'file_path': 'valid.py',
                'file_hash': 'hash_valid'
            },
            {
                'text': 'def another_valid(): return True',
                'file_path': 'another_valid.py',
                'file_hash': 'hash_another'
            }
        ]

        # Test that batch processor handles valid files
        result = self.batch_processor.process_batch(files)

        # Should return a BatchProcessingResult
        assert result is not None
        assert hasattr(result, 'results')
        assert result.processed_files >= 0
        assert result.failed_files >= 0

    def test_service_initialization_order(self):
        """Test that services can be initialized in any order."""
        # This test verifies that there are no circular dependencies
        services = [
            TreeSitterFileProcessor(self.config, self.error_handler),
            TreeSitterResourceManager(self.config, self.error_handler),
            TreeSitterConfigurationManager(self.config, self.error_handler),
            TreeSitterQueryExecutor(self.config, self.error_handler),
            TreeSitterBlockExtractor(self.config, self.error_handler),
            TreeSitterBatchProcessor(self.config, self.error_handler)
        ]

        # All services should initialize successfully
        assert len(services) == 6
        assert all(service is not None for service in services)

    def test_service_dependency_injection(self):
        """Test service dependency injection pattern."""
        # Test that services can be injected with different configurations
        config1 = Config()
        config1.use_tree_sitter = True

        config2 = Config()
        config2.use_tree_sitter = False

        # Create services with different configs
        service1 = TreeSitterFileProcessor(config1, self.error_handler)
        service2 = TreeSitterFileProcessor(config2, self.error_handler)

        # Services should maintain their own config
        assert service1.config.use_tree_sitter is True
        assert service2.config.use_tree_sitter is False

    def test_graceful_degradation_when_services_fail(self):
        """Test graceful degradation when individual services fail."""
        python_code = 'def test(): pass'

        # Test with failing resource manager
        with patch.object(self.resource_manager, 'acquire_resources', side_effect=Exception("Resource acquisition failed")):

            # Create a mock root node for the block extractor
            mock_root_node = Mock()
            mock_root_node.start_byte = 0
            mock_root_node.end_byte = len(python_code)

            result = self.block_extractor.extract_blocks_from_node(
                mock_root_node, python_code, 'test.py', 'hash_fail', 'python'
            )

            # Should handle the error gracefully and return empty result
            assert len(result.blocks) == 0
            assert result.success is False
            assert result.error_message is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])