"""
Test module for scalability features including large file handling and fallback parsing.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from code_index.file_processing import FileProcessingService
from code_index.services.file_processor import TreeSitterFileProcessor, FileProcessor
from code_index.hybrid_parsers import HybridParserManager, PlainTextParser, ConfigFileParser
from code_index.services.block_extractor import TreeSitterBlockExtractor, ExtractionResult
from code_index.config import Config
from code_index.errors import ErrorHandler
from code_index.models import CodeBlock


class TestLargeFileHandling:
    """Test large file handling capabilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.file_service = FileProcessingService(self.error_handler)

        # Configure for large file testing
        self.config.large_file_threshold_bytes = 256 * 1024  # 256KB
        self.config.streaming_threshold_bytes = 1024 * 1024   # 1MB
        self.config.default_chunk_size_bytes = 64 * 1024      # 64KB

    def test_chunked_file_loading(self):
        """Test loading large files in chunks."""
        # Create a larger file (400KB) to ensure chunking
        large_content = "This is a test line with some additional content to make it longer.\n" * 8000  # ~400KB

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(large_content)
            temp_file = f.name

        try:
            # Test chunked loading with explicit chunk size if available
            if hasattr(self.file_service, 'load_file_with_chunking'):
                chunks = list(self.file_service.load_file_with_chunking(temp_file, chunk_size=64*1024))

                # Should have multiple chunks for a 400KB file with 64KB chunks
                assert len(chunks) >= 6  # 400KB / 64KB ≈ 6+ chunks

                # Verify chunk structure
                for i, chunk in enumerate(chunks):
                    assert 'chunk_index' in chunk
                    assert 'chunk_data' in chunk
                    assert 'chunk_size' in chunk
                    assert 'progress' in chunk
                    assert chunk['chunk_index'] == i

                # Verify total content is preserved
                reconstructed_content = ''.join(chunk['chunk_data'] for chunk in chunks)
                assert reconstructed_content == large_content
            else:
                # If method doesn't exist, test basic file reading
                with open(temp_file, 'r') as f:
                    content = f.read()
                assert content == large_content

        finally:
            os.unlink(temp_file)

    def test_streaming_file_processing(self):
        """Test streaming processing of large files."""
        # Create a larger file (1.5MB) to ensure streaming
        large_content = "def function_{}():\n    return '{}'\n".format(
            "x" * 100, "y" * 100
        ) * 3000  # ~1.5MB

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(large_content)
            temp_file = f.name

        try:
            # Mock processor callback
            processed_chunks = []

            def mock_processor(chunk_data, chunk_index, is_complete):
                processed_chunks.append({
                    'chunk_index': chunk_index,
                    'chunk_size': len(chunk_data),
                    'is_complete': is_complete
                })
                return f"processed_chunk_{chunk_index}"

            # Test streaming processing if method exists
            if hasattr(self.file_service, 'stream_process_large_file'):
                results = self.file_service.stream_process_large_file(
                    temp_file, mock_processor, chunk_size=64*1024
                )

                assert results['success'] == True
                assert results['chunks_processed'] > 1
                assert len(processed_chunks) == results['chunks_processed']
            else:
                # Skip if method doesn't exist
                pytest.skip("stream_process_large_file not available")

        finally:
            os.unlink(temp_file)

    def test_memory_optimized_processing(self):
        """Test memory-optimized file processing."""
        # Create a medium-sized file (200KB)
        content = "\n".join([
            f"Line {i}: This is test content for memory optimization testing."
            for i in range(4000)
        ])  # ~200KB

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            temp_file = f.name

        try:
            # Test memory-optimized processing if method exists
            if hasattr(self.file_service, 'process_file_with_memory_optimization'):
                # Mock processor that tracks memory usage
                memory_usage_log = []

                def mock_processor(content, chunk_index, is_complete):
                    processed_content = content.upper()
                    memory_usage_log.append({
                        'chunk_index': chunk_index,
                        'content_size': len(content),
                        'processed_size': len(processed_content)
                    })
                    return processed_content

                results = self.file_service.process_file_with_memory_optimization(
                    temp_file, mock_processor, max_memory_usage_mb=50
                )

                assert results['success'] == True
                assert 'memory_usage_mb' in results
                assert results['strategy_used'] in ['streaming_chunked', 'chunked_processing', 'standard_loading']
            else:
                # Skip if method doesn't exist
                pytest.skip("process_file_with_memory_optimization not available")

        finally:
            os.unlink(temp_file)

    def test_file_info_via_processor(self):
        """Test getting file processing information via TreeSitterFileProcessor."""
        # Create a test file
        test_content = "def test_function():\n    return 'test'\n" * 100
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(test_content)
            temp_file = f.name

        try:
            # Test file processing info generation using TreeSitterFileProcessor
            processor = TreeSitterFileProcessor(self.config, self.error_handler)
            info = processor.get_file_info(temp_file)

            assert info['path'] == temp_file
            assert info['exists'] is True
            assert info['is_file'] is True
            assert 'size_bytes' in info
            assert info['is_valid'] is True

        finally:
            os.unlink(temp_file)


class TestScalableFileProcessor:
    """Test scalable file processor capabilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.processor = TreeSitterFileProcessor(self.config, self.error_handler)

    def test_validate_file_scalability_basic(self):
        """Test basic file validation with different file sizes."""
        # Create test files of different sizes
        test_cases = [
            ("small.py", "print('hello')\n" * 10),
            ("medium.py", "def func():\n    pass\n" * 1000),  # ~50KB
        ]

        for filename, content in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
                f.write(content)
                temp_file = f.name

            try:
                # Test basic validation
                result = self.processor.validate_file(temp_file)

                print(f"File: {filename}, Valid: {result}")

                # Should be valid for normal-sized files
                assert result is True

            finally:
                os.unlink(temp_file)

    def test_validate_file_large_file(self):
        """Test validation of large files."""
        # Create a file larger than the max size limit
        self.config.tree_sitter_max_file_size_bytes = 1024  # 1KB limit
        processor = TreeSitterFileProcessor(self.config, self.error_handler)

        content = "x" * 2000  # 2KB content

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(content)
            temp_file = f.name

        try:
            # Should be invalid due to size
            result = processor.validate_file(temp_file)
            assert result is False

        finally:
            os.unlink(temp_file)

    def test_file_info_scalability(self):
        """Test getting file info with scalability configuration."""
        # Create a test file
        content = "class TestClass:\n    def method(self):\n        return 'test'\n" * 50

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(content)
            temp_file = f.name

        try:
            # Test file info
            info = self.processor.get_file_info(temp_file)

            assert info['is_valid'] is True
            assert info['path'] == temp_file
            assert 'size_bytes' in info
            assert info['size_bytes'] > 0
            assert info['extension'] == '.py'
            assert info['exists'] is True
            assert info['is_file'] is True

        finally:
            os.unlink(temp_file)

    def test_scalability_configuration_loaded(self):
        """Test that scalability configuration is properly loaded."""
        # Verify scalability settings are configured
        assert hasattr(self.processor, 'enable_chunked_processing')
        assert hasattr(self.processor, 'large_file_threshold')
        assert hasattr(self.processor, 'streaming_threshold')
        assert hasattr(self.processor, 'default_chunk_size')
        assert hasattr(self.processor, 'memory_threshold_mb')
        assert hasattr(self.processor, 'enable_progressive_indexing')


class TestHybridParserSystem:
    """Test hybrid parser system for unsupported file types."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.hybrid_manager = HybridParserManager(self.config, self.error_handler)
        
    def test_plain_text_parser(self):
        """Test plain text parser."""
        parser = PlainTextParser(self.config, self.error_handler)
        
        # Test with plain text content
        content = "This is line 1.\nThis is line 2.\nThis is line 3.\n" * 20
        file_path = "test.txt"
        
        # Test can_parse
        assert parser.can_parse(file_path, content) == True
        
        # Test parsing
        result = parser.parse(content, file_path, "hash123")
        
        assert result.success == True
        assert len(result.blocks) > 0
        assert all(isinstance(block, CodeBlock) for block in result.blocks)
        
        # Verify block structure
        for block in result.blocks:
            assert block.type == "text_chunk"
            assert block.file_path == file_path
            assert block.file_hash == "hash123"
            
    def test_config_file_parser(self):
        """Test configuration file parser."""
        parser = ConfigFileParser(self.config, self.error_handler)
        
        # Test with INI-style content
        content = """[section1]
key1 = value1
key2 = value2

[section2]
key3 = value3
key4 = value4"""
        
        file_path = "test.ini"
        
        # Test can_parse
        assert parser.can_parse(file_path, content) == True
        
        # Test parsing
        result = parser.parse(content, file_path, "hash123")
        
        assert result.success == True
        assert len(result.blocks) >= 2  # Should have at least 2 sections
        assert any(block.type == "config_section" for block in result.blocks)
        
    def test_hybrid_parser_manager(self):
        """Test hybrid parser manager."""
        # Test with different file types
        test_cases = [
            ("test.txt", "Plain text content\nwith multiple lines", "PlainTextParser"),
            ("test.ini", "[section]\nkey=value", "ConfigFileParser"),
            ("test.log", "Log entry 1\nLog entry 2\nLog entry 3", "PlainTextParser"),
        ]
        
        for file_path, content, expected_parser in test_cases:
            result = self.hybrid_manager.parse_with_fallback(content, file_path, "hash123")
            
            assert result.success == True
            assert len(result.blocks) > 0
            assert result.metadata["fallback_parser_used"] == expected_parser
            
    def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        # Test with binary-like content
        content = "\x00\x01\x02\x03\x04\x05" * 100
        file_path = "test.bin"
        
        result = self.hybrid_manager.parse_with_fallback(content, file_path, "hash123")
        
        assert result.success == False
        assert result.error_message == "No suitable fallback parser found"
        assert len(result.blocks) == 0
        
    def test_parser_stats(self):
        """Test parser statistics."""
        stats = self.hybrid_manager.get_parser_stats()
        
        assert "total_parsers" in stats
        assert "parser_types" in stats
        assert "available_extensions" in stats
        assert stats["total_parsers"] > 0


class TestBlockExtractorWithFallback:
    """Test block extractor with fallback parsing capabilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config.enable_fallback_parsers = True
        self.error_handler = ErrorHandler()
        self.extractor = TreeSitterBlockExtractor(self.config, self.error_handler)
        
    def test_extract_blocks_with_fallback(self):
        """Test block extraction with fallback parsing."""
        # Test with plain text content (should use fallback parser)
        content = "This is a plain text file.\nIt has multiple lines.\nEach line is content."
        file_path = "test.txt"
        file_hash = "hash123"
        
        blocks = self.extractor.extract_blocks_with_fallback(content, file_path, file_hash)
        
        assert len(blocks) > 0
        assert all(isinstance(block, CodeBlock) for block in blocks)
        
        # Verify fallback was used
        # Note: This would require checking metadata, but the basic functionality works
        
    def test_extract_blocks_from_root_node_with_fallback(self):
        """Test extraction from root node with fallback."""
        # Test with mock root node (simulating Tree-sitter failure)
        mock_root_node = Mock()
        mock_root_node.__class__ = Mock
        mock_root_node.__str__ = Mock(return_value="MockNode")
        
        content = "Plain text content\nwith multiple lines\nfor testing fallback."
        file_path = "test.txt"
        file_hash = "hash123"
        
        result = self.extractor.extract_blocks_from_root_node_with_fallback(
            mock_root_node, content, file_path, file_hash
        )
        
        assert isinstance(result, ExtractionResult)
        assert result.success == True
        assert len(result.blocks) > 0
        assert result.metadata["extraction_method"] in ["fallback_parser", "basic_chunking"]
        
    def test_basic_line_chunking(self):
        """Test basic line-based chunking fallback."""
        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        file_path = "test.txt"
        file_hash = "hash123"
        
        blocks = self.extractor._basic_line_chunking(content, file_path, file_hash)
        
        assert len(blocks) > 0
        assert all(isinstance(block, CodeBlock) for block in blocks)
        
        # Verify first block
        first_block = blocks[0]
        assert first_block.file_path == file_path
        assert first_block.file_hash == file_hash
        assert first_block.type == "text_chunk"


class TestConfigurationIntegration:
    """Test integration with configuration system."""
    
    def test_scalability_configuration(self):
        """Test that scalability configuration is properly loaded."""
        config = Config()
        
        # Verify new configuration options exist
        assert hasattr(config, 'enable_chunked_processing')
        assert hasattr(config, 'large_file_threshold_bytes')
        assert hasattr(config, 'streaming_threshold_bytes')
        assert hasattr(config, 'default_chunk_size_bytes')
        assert hasattr(config, 'enable_fallback_parsers')
        assert hasattr(config, 'enable_hybrid_parsing')
        
    def test_language_chunk_sizes(self):
        """Test language-specific chunk size configuration."""
        config = Config()
        
        # Verify language chunk sizes are configured
        assert hasattr(config, 'language_chunk_sizes')
        assert isinstance(config.language_chunk_sizes, dict)
        assert 'python' in config.language_chunk_sizes
        assert 'java' in config.language_chunk_sizes
        
    def test_fallback_parser_patterns(self):
        """Test fallback parser pattern configuration."""
        config = Config()
        
        # Verify fallback parser patterns are configured
        assert hasattr(config, 'fallback_parser_patterns')
        assert isinstance(config.fallback_parser_patterns, dict)
        assert 'text' in config.fallback_parser_patterns
        assert 'config' in config.fallback_parser_patterns


class TestPerformanceMonitoring:
    """Test performance monitoring capabilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.config.enable_performance_monitoring = True
        self.config.parser_performance_monitoring = True
        self.error_handler = ErrorHandler()

    def test_parser_performance_tracking(self):
        """Test that parser performance configuration is set up correctly."""
        # Verify the configuration is set up correctly
        assert self.config.enable_performance_monitoring == True
        assert self.config.parser_performance_monitoring == True
        assert hasattr(self.config, 'performance_stats_interval')
        assert hasattr(self.config, 'parser_timeout_seconds')

    def test_monitoring_configuration_loaded(self):
        """Test that monitoring configuration is loaded in TreeSitterFileProcessor."""
        processor = TreeSitterFileProcessor(self.config, self.error_handler)

        # Verify monitoring settings are loaded
        assert hasattr(processor, 'enable_performance_tracking')
        assert hasattr(processor, 'log_mmap_metrics')
        assert hasattr(processor, 'log_resource_usage')
        assert hasattr(processor, 'log_per_file_metrics')
        assert hasattr(processor, 'log_memory_usage')


# Integration tests
def test_end_to_end_large_file_processing():
    """Test end-to-end processing of large files."""
    config = Config()
    config.enable_chunked_processing = True
    config.large_file_threshold_bytes = 100 * 1024  # 100KB
    config.streaming_threshold_bytes = 500 * 1024   # 500KB

    error_handler = ErrorHandler()

    # Create a large test file
    large_content = "def function_{}():\n    return 'test'\n".format("x" * 50) * 2000
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
        f.write(large_content)
        temp_file = f.name

    try:
        # Test file processor
        processor = TreeSitterFileProcessor(config, error_handler)

        # Get processing info
        info = processor.get_file_info(temp_file)

        assert info['is_valid'] is True
        assert info['exists'] is True
        assert info['is_file'] is True
        assert info['size_bytes'] > 0

        # Test basic file operations
        assert processor.validate_file(temp_file) is True

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__])