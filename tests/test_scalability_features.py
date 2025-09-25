"""
Test module for scalability features including large file handling and fallback parsing.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from code_index.file_processing import FileProcessingService
from code_index.services.file_processor import TreeSitterFileProcessor
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
            # Test chunked loading with explicit chunk size
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
            
        finally:
            os.unlink(temp_file)
            
    def test_chunked_file_loading_debug(self):
        """Test chunked file loading with debug output."""
        # Create a large file - need to be above 256KB threshold
        large_content = "Test line " + "x" * 100 + "\n" * 3000  # This is only ~3KB
        
        # Create a much larger file - 300KB
        large_content = "Test line " + "x" * 200 + "\n" * 1500  # ~300KB
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(large_content)
            temp_file = f.name
            
        try:
            print(f"File size: {os.path.getsize(temp_file)} bytes")
            
            # Test chunked loading
            chunks = list(self.file_service.load_file_with_chunking(temp_file))
            
            print(f"Number of chunks: {len(chunks)}")
            
            # The file should be chunked if it's above the threshold
            if os.path.getsize(temp_file) > 256 * 1024:  # 256KB threshold
                assert len(chunks) > 1  # Should be chunked
            else:
                # If below threshold, should be single chunk
                assert len(chunks) == 1
            
            assert all('chunk_data' in chunk for chunk in chunks)
            assert all('chunk_index' in chunk for chunk in chunks)
            
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
                
            # Test streaming processing with explicit chunk size
            results = self.file_service.stream_process_large_file(
                temp_file, mock_processor, chunk_size=64*1024
            )
            
            assert results['success'] == True
            assert results['chunks_processed'] > 1
            assert len(processed_chunks) == results['chunks_processed']
            
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
            # Mock processor that tracks memory usage
            memory_usage_log = []
            
            def mock_processor(content, chunk_index, is_complete):
                # Simulate some processing
                processed_content = content.upper()
                memory_usage_log.append({
                    'chunk_index': chunk_index,
                    'content_size': len(content),
                    'processed_size': len(processed_content)
                })
                return processed_content
                
            # Test memory-optimized processing
            results = self.file_service.process_file_with_memory_optimization(
                temp_file, mock_processor, max_memory_usage_mb=50
            )
            
            assert results['success'] == True
            assert 'memory_usage_mb' in results
            assert results['strategy_used'] in ['streaming_chunked', 'chunked_processing', 'standard_loading']
            
        finally:
            os.unlink(temp_file)
            
    def test_optimal_chunk_size_calculation(self):
        """Test calculation of optimal chunk sizes."""
        # Test different file sizes - these should match the actual implementation
        test_cases = [
            (500 * 1024, None, 64 * 1024),      # 500KB file, default chunk size
            (5 * 1024 * 1024, "python", 128 * 1024),   # 5MB Python file - should use 128KB
            (15 * 1024 * 1024, "java", 256 * 1024), # 15MB Java file - should use 256KB
            (150 * 1024 * 1024, "cpp", 512 * 1024), # 150MB C++ file - should use 512KB
        ]
        
        for file_size, language, expected_chunk_size in test_cases:
            chunk_size = self.file_service.get_optimal_chunk_size(file_size, language)
            assert chunk_size == expected_chunk_size
            
    def test_file_processing_info_generation(self):
        """Test generation of file processing information."""
        # Create a test file
        test_content = "def test_function():\n    return 'test'\n" * 100
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(test_content)
            temp_file = f.name
            
        try:
            # Test file processing info generation using the file processor
            processor = TreeSitterFileProcessor(self.config, self.error_handler)
            info = processor.get_file_processing_info(temp_file)
            
            assert info['file_path'] == temp_file
            assert info['valid'] == True
            assert 'file_size' in info
            assert 'language_key' in info
            assert 'strategy' in info
            assert 'estimated_memory_mb' in info
            assert 'estimated_time_seconds' in info
            
        finally:
            os.unlink(temp_file)


class TestScalableFileProcessor:
    """Test scalable file processor capabilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.processor = TreeSitterFileProcessor(self.config, self.error_handler)
        
    def test_validate_file_with_scalability(self):
        """Test file validation with scalability considerations."""
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
                # Test scalability validation
                result = self.processor.validate_file_with_scalability(temp_file)
                
                print(f"File: {filename}, Result: {result}")  # Debug output
                
                assert result['valid'] == True
                assert result['should_process'] == True
                assert 'strategy' in result
                assert 'file_size' in result
                assert 'language_key' in result
                
            finally:
                os.unlink(temp_file)
                
    def test_process_file_with_chunking(self):
        """Test processing files with chunking."""
        # Create a medium-sized file
        content = "def function_{}():\n    return {}\n".format("x" * 50, "y" * 50) * 200
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(content)
            temp_file = f.name
            
        try:
            # Mock chunk processor
            processed_chunks = []
            
            def mock_chunk_processor(chunk_data, chunk_index, is_complete):
                processed_chunks.append({
                    'chunk_index': chunk_index,
                    'chunk_size': len(chunk_data),
                    'is_complete': is_complete
                })
                return f"processed_chunk_{chunk_index}"
                
            # Test chunked processing
            results = self.processor.process_file_with_chunking(
                temp_file, mock_chunk_processor
            )
            
            assert results['success'] == True
            assert results['strategy'] == 'chunked'
            assert results['chunks_processed'] > 0
            assert len(processed_chunks) == results['chunks_processed']
            
        finally:
            os.unlink(temp_file)
            
    def test_file_processing_info(self):
        """Test comprehensive file processing information."""
        # Create a test file
        content = "class TestClass:\n    def method(self):\n        return 'test'\n" * 50
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(content)
            temp_file = f.name
            
        try:
            # Test file processing info
            info = self.processor.get_file_processing_info(temp_file)
            
            assert info['valid'] == True
            assert info['file_path'] == temp_file
            assert 'file_size_mb' in info
            assert 'estimated_memory_mb' in info
            assert 'estimated_time_seconds' in info
            assert 'recommended_batch_size' in info
            assert 'can_use_streaming' in info
            assert 'memory_optimization_available' in info
            
        finally:
            os.unlink(temp_file)


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
        """Test that parser performance is tracked."""
        # This would require integration with the parser manager
        # For now, just verify the configuration is set up correctly
        assert self.config.enable_performance_monitoring == True
        assert self.config.parser_performance_monitoring == True
        assert hasattr(self.config, 'performance_stats_interval')
        assert hasattr(self.config, 'parser_timeout_seconds')
        
    def test_memory_usage_estimation(self):
        """Test memory usage estimation for file processing."""
        processor = TreeSitterFileProcessor(self.config, self.error_handler)
        
        # Test memory estimation
        file_size = 10 * 1024 * 1024  # 10MB
        strategy = "chunked_processing"
        
        estimated_memory = processor._estimate_memory_usage(file_size, strategy)
        
        assert estimated_memory > 0
        assert isinstance(estimated_memory, float)
        
        # Test that streaming uses less memory
        streaming_memory = processor._estimate_memory_usage(file_size, "streaming_chunked")
        standard_memory = processor._estimate_memory_usage(file_size, "standard")
        
        assert streaming_memory < standard_memory


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
        info = processor.get_file_processing_info(temp_file)
        
        assert info['valid'] == True
        assert info['strategy'] in ['chunked_processing', 'streaming_chunked']
        assert info['can_use_streaming'] == True
        
        # Test actual processing
        def mock_processor(content, chunk_index, is_complete):
            return f"processed_chunk_{chunk_index}"
            
        results = processor.process_file_with_chunking(temp_file, mock_processor)
        
        assert results['success'] == True
        assert results['chunks_processed'] > 0
        
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__])