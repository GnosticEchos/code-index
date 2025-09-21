# Iterative Refactoring Sprints

## Overview

This document outlines a systematic, sprint-based approach to refactoring the code indexing system based on the Code Skeptic analysis. Each sprint focuses on specific, tightly-scoped improvements that build upon previous work, allowing for incremental testing and validation while minimizing risk.

**Total Sprints**: 5
**Estimated Timeline**: 4-6 weeks
**Risk Level**: Low to Medium (incremental approach)
**Focus**: Maintainability, testability, and code quality improvements

## Sprint 1: DRY Violation Fixes (Week 1)

### 1.1 Consolidate Error Handling Strategy

**Goal**: Eliminate duplicated error handling patterns across modules and implement centralized, structured error management.

**Affected Code Sections**:
- `src/code_index/cli.py` (Lines 468-471, 300-301, 423-424, 433-434)
- `src/code_index/chunking.py` (Lines 121-124, 206-207, 218-219)
- `src/code_index/vector_store.py` (Lines 300-301, 423-424, 433-434)
- `src/code_index/mcp_server/server.py` (Lines 78-80, 138-144, 195-200)

**Rationale**: The code review identified 15+ instances of identical error handling patterns with inconsistent formats and no centralized strategy, making debugging difficult and maintenance challenging.

**Implementation Steps**:

1. **Create Error Handler Module** (`src/code_index/errors.py`):
   ```python
   class ErrorHandler:
       @staticmethod
       def handle_file_processing_error(error: Exception, context: Dict) -> ErrorResult:
           # Centralized file processing error handling
           pass

       @staticmethod
       def handle_service_connection_error(service: str, error: Exception, context: Dict) -> ErrorResult:
           # Centralized service connection error handling
           pass

       @staticmethod
       def handle_configuration_error(error: Exception, context: Dict) -> ErrorResult:
           # Centralized configuration error handling
           pass

   class ErrorResult:
       def __init__(self, error_type: str, message: str, actionable_guidance: List[str]):
           self.error_type = error_type
           self.message = message
           self.actionable_guidance = actionable_guidance
   ```

2. **Replace CLI Error Handling**:
   - Replace scattered try-catch blocks in `_process_single_workspace()`
   - Update error handling in `index()` and `search()` methods
   - Implement consistent error logging with context

3. **Replace Chunking Error Handling**:
   - Update `TreeSitterChunkingStrategy.chunk()` method
   - Replace fallback error handling in `TokenChunkingStrategy`
   - Standardize Tree-sitter specific error handling

4. **Replace Vector Store Error Handling**:
   - Update `upsert_points()` error handling
   - Replace `delete_points_by_file_path()` error handling
   - Standardize `clear_collection()` error handling

5. **Replace MCP Server Error Handling**:
   - Update service validation error handling
   - Replace configuration loading error handling
   - Implement structured error responses

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_cli_error_handling.py` (if exists) - Redundant error handling tests
- `tests/test_mcp_error_handling.py` (if exists) - Redundant error handling tests
- Error handling test methods in `tests/test_cli.py` that test scattered error patterns
- Error handling test methods in `tests/test_mcp_server.py` that test old error patterns

**Existing Tests to Update**:
- `tests/test_mcp_server.py` - Update error handling assertions to use new ErrorHandler
- `tests/test_cli.py` - Update CLI error scenario tests to use centralized error handling
- `tests/test_treesitter.py` - Update Tree-sitter error handling tests to use ErrorHandler

**New Tests to Add**:
```python
def test_centralized_error_handling():
    """Test centralized error handling with different error types."""
    handler = ErrorHandler()

    # Test file processing error
    error_result = handler.handle_file_processing_error(
        FileNotFoundError("File not found"),
        {"file_path": "test.py", "operation": "read"}
    )
    assert error_result.error_type == "file_processing_error"
    assert "File not found" in error_result.message
    assert len(error_result.actionable_guidance) > 0

def test_service_connection_error_handling():
    """Test service connection error handling."""
    error_result = ErrorHandler.handle_service_connection_error(
        "Ollama",
        ConnectionError("Connection refused"),
        {"url": "http://localhost:11434", "timeout": 30}
    )
    assert error_result.error_type == "service_connection_error"
    assert "Ollama" in error_result.message
    assert "Connection refused" in error_result.message

def test_error_result_structure():
    """Test ErrorResult structure and serialization."""
    result = ErrorResult(
        "test_error",
        "Test error message",
        ["Action 1", "Action 2"]
    )
    assert result.error_type == "test_error"
    assert result.message == "Test error message"
    assert len(result.actionable_guidance) == 2
```

**Integration Tests Required**:
- Test error handling in full indexing workflow
- Test error propagation through MCP server tools
- Test error logging and reporting consistency

**Success Criteria**:
- **Code Quality Metrics**:
  - Reduce error handling code duplication by 80%
  - Achieve 100% test coverage for error handling utilities
  - Consistent error message format across all modules
- **Functional Validation**:
  - All existing functionality preserved
  - Error messages provide actionable guidance
  - No performance degradation in error paths
- **Rollback Procedure**:
  - Keep backup of original error handling code
  - Implement feature flag to revert to old error handling
  - Database backup before deployment

### 1.2 Extract File Processing Utilities

**Goal**: Consolidate duplicated file processing logic and create reusable utilities for path handling, file loading, and processing operations.

**Affected Code Sections**:
- `src/code_index/cli.py` (Lines 80-98, 140-163)
- `src/code_index/scanner.py` (file discovery logic)
- `src/code_index/utils.py` (existing utilities)

**Rationale**: The code review identified 5+ instances of duplicated file path processing, list loading, and file filtering logic across different modules.

**Implementation Steps**:

1. **Create File Processing Service** (`src/code_index/file_processing.py`):
   ```python
   class FileProcessingService:
       def load_path_list(self, path_file: str, workspace: str) -> List[str]:
           """Load newline-separated paths with comment filtering."""
           pass

       def load_workspace_list(self, workspace_list_file: str) -> List[str]:
           """Load workspace list with validation."""
           pass

       def load_exclude_list(self, workspace_path: str, exclude_files_path: str) -> Set[str]:
           """Load exclude patterns as normalized relative paths."""
           pass

       def filter_files_by_criteria(self, files: List[str], criteria: Dict) -> List[str]:
           """Filter files by size, extension, and exclude patterns."""
           pass
   ```

2. **Create Path Utilities** (`src/code_index/path_utils.py`):
   ```python
   class PathUtils:
       @staticmethod
       def normalize_relative_path(path: str, workspace: str) -> str:
           """Normalize path to relative path from workspace."""
           pass

       @staticmethod
       def is_path_excluded(path: str, exclude_patterns: List[str]) -> bool:
           """Check if path matches any exclude pattern."""
           pass

       @staticmethod
       def get_path_segments(path: str) -> List[str]:
           """Split path into segments for indexing."""
           pass
   ```

3. **Replace CLI File Processing**:
   - Replace `_load_path_list()` function
   - Replace `_load_workspace_list()` function
   - Replace `_load_exclude_list()` function
   - Update file filtering logic

4. **Update Scanner Integration**:
   - Use centralized file processing utilities
   - Implement consistent path handling
   - Add file criteria filtering

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_cli_file_processing.py` (if exists) - Redundant file processing tests
- `tests/test_scanner_file_processing.py` (if exists) - Redundant file processing tests
- File processing test methods in `tests/test_cli.py` that duplicate scanner functionality
- Path processing test methods in `tests/test_ignore_patterns.py` that test internal logic

**Existing Tests to Update**:
- `tests/test_cli.py` - Update file loading test cases to use FileProcessingService
- `tests/test_ignore_patterns.py` - Update path processing tests to use PathUtils
- `tests/test_scanner.py` - Update file discovery tests to use centralized services

**New Tests to Add**:
```python
def test_path_list_loading():
    """Test loading of path lists with various formats."""
    service = FileProcessingService()

    # Test with comments and empty lines
    path_list = service.load_path_list("test_paths.txt", "/workspace")
    assert len(path_list) == 3
    assert "src/main.py" in path_list
    assert "tests/" not in path_list  # Should be filtered

def test_workspace_list_validation():
    """Test workspace list loading with validation."""
    service = FileProcessingService()

    # Test with invalid directories
    workspaces = service.load_workspace_list("invalid_workspaces.txt")
    assert len(workspaces) == 1  # Only valid directories included
    assert "/valid/workspace" in workspaces

def test_exclude_list_normalization():
    """Test exclude list loading and normalization."""
    service = FileProcessingService()

    excludes = service.load_exclude_list("/workspace", "exclude.txt")
    assert "node_modules/" in excludes
    assert ".git/" in excludes
    assert len(excludes) == 5
```

**Integration Tests Required**:
- Test file processing in full indexing workflow
- Test path handling with various file structures
- Test integration with scanner and ignore systems

**Success Criteria**:
- **Code Quality Metrics**:
  - Reduce file processing code duplication by 75%
  - Achieve 95% test coverage for file processing utilities
  - Consistent path handling across all modules
- **Functional Validation**:
  - All existing file processing functionality preserved
  - No performance impact on file operations
  - Consistent behavior across different modules
- **Rollback Procedure**:
  - Keep backup of original file processing functions
  - Implement gradual migration with feature flags
  - Test file processing independently before integration

**Dependencies**: None (can be implemented independently)
**Prerequisites for Sprint 2**: Centralized file processing utilities available for configuration consolidation

## Sprint 2: Service Validation and Configuration Consolidation (Week 2)

### 2.1 Implement Service Validation Framework

**Goal**: Create a centralized service validation system to eliminate duplicated validation logic and provide consistent service health checking.

**Affected Code Sections**:
- `src/code_index/cli.py` (Lines 285-301)
- `src/code_index/mcp_server/server.py` (Lines 172-248)
- `src/code_index/embedder.py` (validation logic)
- `src/code_index/vector_store.py` (connection validation)

**Rationale**: Service validation logic is duplicated between CLI and MCP server with different error handling approaches, making it difficult to maintain consistent validation behavior.

**Implementation Steps**:

1. **Create Service Validation Framework** (`src/code_index/service_validation.py`):
   ```python
   class ServiceValidator:
       def validate_ollama_service(self, config: Config) -> ValidationResult:
           """Validate Ollama service connectivity and configuration."""
           pass

       def validate_qdrant_service(self, config: Config) -> ValidationResult:
           """Validate Qdrant service connectivity and configuration."""
           pass

       def validate_all_services(self, config: Config) -> List[ValidationResult]:
           """Validate all required services."""
           pass

   class ValidationResult:
       def __init__(self, service: str, valid: bool, error: str = None, details: Dict = None):
           self.service = service
           self.valid = valid
           self.error = error
           self.details = details
   ```

2. **Replace CLI Service Validation**:
   - Replace validation logic in `_process_single_workspace()`
   - Update `index()` and `search()` command validation
   - Implement consistent validation error handling

3. **Replace MCP Server Service Validation**:
   - Replace validation logic in `_validate_services()`
   - Update service connection error handling
   - Implement structured validation reporting

4. **Update Embedder and Vector Store**:
   - Add validation methods to existing classes
   - Implement consistent validation interfaces
   - Add validation metadata and reporting

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_cli_validation.py` (if exists) - Redundant CLI validation tests
- `tests/test_mcp_validation.py` (if exists) - Redundant MCP validation tests
- Service validation test methods in `tests/test_cli.py` that duplicate MCP tests
- Service validation test methods in `tests/test_mcp_server.py` that test scattered validation logic

**Existing Tests to Update**:
- `tests/test_mcp_server.py` - Update service validation tests to use ServiceValidator
- `tests/test_cli.py` - Update CLI validation tests to use centralized validation
- `tests/test_embedding.py` - Update embedder validation tests to use ValidationResult

**New Tests to Add**:
```python
def test_ollama_service_validation():
    """Test Ollama service validation with different scenarios."""
    validator = ServiceValidator()
    config = create_test_config()

    # Test successful validation
    result = validator.validate_ollama_service(config)
    assert result.valid == True
    assert result.service == "ollama"
    assert result.error is None

def test_qdrant_service_validation():
    """Test Qdrant service validation."""
    validator = ServiceValidator()
    config = create_test_config()

    # Test connection failure
    config.qdrant_url = "http://invalid:9999"
    result = validator.validate_qdrant_service(config)
    assert result.valid == False
    assert result.service == "qdrant"
    assert "connection" in result.error.lower()

def test_comprehensive_service_validation():
    """Test validation of all services together."""
    validator = ServiceValidator()
    config = create_test_config()

    results = validator.validate_all_services(config)
    assert len(results) == 2  # Ollama and Qdrant

    # Both services should be valid
    assert all(result.valid for result in results)
```

**Integration Tests Required**:
- Test service validation in MCP server startup
- Test validation during CLI command execution
- Test validation error propagation and reporting

**Success Criteria**:
- **Code Quality Metrics**:
  - Reduce service validation code duplication by 85%
  - Achieve 100% test coverage for validation framework
  - Consistent validation behavior across all modules
- **Functional Validation**:
  - All existing validation functionality preserved
  - Better error messages and actionable guidance
  - No impact on service connection performance
- **Rollback Procedure**:
  - Keep backup of original validation logic
  - Implement validation bypass mechanism
  - Gradual rollout with monitoring

### 2.2 Consolidate Configuration Loading

**Goal**: Create a centralized configuration management system to eliminate duplicated loading logic and provide consistent configuration handling.

**Affected Code Sections**:
- `src/code_index/cli.py` (Lines 238-270)
- `src/code_index/mcp_server/server.py` (Lines 132-144)
- `src/code_index/mcp_server/tools/index_tool.py` (similar pattern)
- `src/code_index/config.py` (existing configuration)

**Rationale**: Configuration loading logic is repeated across CLI, MCP server, and tools with different error handling and override mechanisms.

**Implementation Steps**:

1. **Create Configuration Service** (`src/code_index/config_service.py`):
   ```python
   class ConfigurationService:
       def load_with_fallback(self, config_path: str, workspace: str) -> Config:
           """Load configuration with fallback to defaults."""
           pass

       def apply_cli_overrides(self, config: Config, overrides: Dict) -> Config:
           """Apply CLI-specific overrides to configuration."""
           pass

       def validate_and_initialize(self, config: Config) -> ValidationResult:
           """Validate configuration and initialize services."""
           pass

       def create_workspace_config(self, workspace: str, overrides: Dict = None) -> Config:
           """Create configuration for specific workspace."""
           pass
   ```

2. **Replace CLI Configuration Loading**:
   - Replace configuration loading in `_process_single_workspace()`
   - Update `index()` and `search()` command configuration
   - Implement centralized override handling

3. **Replace MCP Server Configuration Loading**:
   - Replace configuration loading in `_load_configuration()`
   - Update configuration validation and error handling
   - Implement consistent configuration initialization

4. **Update Tool Configuration**:
   - Replace configuration loading in MCP tools
   - Implement consistent configuration access patterns
   - Add configuration validation for tools

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_cli_config_loading.py` (if exists) - Redundant CLI config tests
- `tests/test_mcp_config_loading.py` (if exists) - Redundant MCP config tests
- Configuration loading test methods in `tests/test_cli.py` that duplicate MCP tests
- Configuration loading test methods in `tests/test_mcp_server.py` that test scattered loading logic

**Existing Tests to Update**:
- `tests/test_mcp_config_manager.py` - Update configuration tests to use ConfigurationService
- `tests/test_cli.py` - Update CLI configuration tests to use centralized service
- `tests/test_config.py` - Update configuration loading tests to use new service

**New Tests to Add**:
```python
def test_configuration_service_loading():
    """Test centralized configuration loading."""
    service = ConfigurationService()

    # Test loading with fallback
    config = service.load_with_fallback("nonexistent.json", "/workspace")
    assert config.workspace_path == "/workspace"
    assert config.ollama_base_url == "http://localhost:11434"  # Default

def test_cli_overrides_application():
    """Test CLI overrides application."""
    service = ConfigurationService()
    config = create_test_config()

    overrides = {
        "embed_timeout": 120,
        "chunking_strategy": "treesitter"
    }

    updated_config = service.apply_cli_overrides(config, overrides)
    assert updated_config.embed_timeout_seconds == 120
    assert updated_config.chunking_strategy == "treesitter"

def test_configuration_validation():
    """Test configuration validation and initialization."""
    service = ConfigurationService()
    config = create_test_config()

    # Test valid configuration
    result = service.validate_and_initialize(config)
    assert result.valid == True
    assert len(result.warnings) == 0
```

**Integration Tests Required**:
- Test configuration loading in full system startup
- Test configuration overrides in CLI workflows
- Test configuration validation error handling

**Success Criteria**:
- **Code Quality Metrics**:
  - Reduce configuration loading code duplication by 90%
  - Achieve 95% test coverage for configuration service
  - Consistent configuration behavior across all modules
- **Functional Validation**:
  - All existing configuration functionality preserved
  - Better configuration validation and error messages
  - No impact on configuration loading performance
- **Rollback Procedure**:
  - Keep backup of original configuration loading logic
  - Implement configuration service bypass
  - Gradual migration with compatibility layer

**Dependencies**: Sprint 1 (file processing utilities available)
**Prerequisites for Sprint 3**: Centralized configuration service for CQRS implementation

## Sprint 3: CQRS Pattern Implementation (Week 3)

### 3.1 Implement CQRS for CLI Operations

**Goal**: Separate command operations from query operations in the CLI layer to improve testability and maintainability.

**Affected Code Sections**:
- `src/code_index/cli.py` (Lines 166-486, 489-582)
- `src/code_index/mcp_server/tools/` (command/query mixing)

**Rationale**: CLI methods mix command execution with queries, making them difficult to test and maintain. CQRS separation will improve code organization and testability.

**Implementation Steps**:

1. **Create Command Services** (`src/code_index/services/`):
   ```python
   class IndexingService:
       def index_workspace(self, workspace: str, config: Config) -> IndexingResult:
           """Execute indexing command."""
           pass

       def process_files(self, files: List[str], config: Config) -> ProcessingResult:
           """Process files for indexing."""
           pass

   class SearchService:
       def search_code(self, query: str, config: Config) -> SearchResult:
           """Execute search command."""
           pass

   class ConfigurationService:
       def get_file_status(self, file_path: str, config: Config) -> FileStatus:
           """Query file processing status."""
           pass

       def get_processing_stats(self, config: Config) -> ProcessingStats:
           """Query processing statistics."""
           pass
   ```

2. **Create Result Types** (`src/code_index/models.py`):
   ```python
   class IndexingResult:
       def __init__(self, processed_files: int, total_blocks: int, errors: List[str]):
           self.processed_files = processed_files
           self.total_blocks = total_blocks
           self.errors = errors

   class SearchResult:
       def __init__(self, results: List[Dict], total_found: int, execution_time: float):
           self.results = results
           self.total_found = total_found
           self.execution_time = execution_time

   class FileStatus:
       def __init__(self, file_path: str, is_processed: bool, last_modified: datetime):
           self.file_path = file_path
           self.is_processed = is_processed
           self.last_modified = last_modified
   ```

3. **Refactor CLI Index Command**:
   - Extract indexing logic into `IndexingService`
   - Separate file status queries into `ConfigurationService`
   - Update `index()` method to use services

4. **Refactor CLI Search Command**:
   - Extract search logic into `SearchService`
   - Separate configuration queries
   - Update `search()` method to use services

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_cli_internal_state.py` (if exists) - Tests internal CLI state rather than behavior
- `tests/test_cli_implementation.py` (if exists) - Tests implementation details
- Test methods in `tests/test_cli.py` that test internal state rather than public behavior
- Test methods in `tests/test_mcp_server.py` that test command/query mixing

**Existing Tests to Update**:
- `tests/test_cli.py` - Update CLI integration tests to use service composition
- `tests/test_mcp_server.py` - Update MCP tool tests to use CQRS services
- `tests/test_search.py` - Update search functionality tests to use SearchService

**New Tests to Add**:
```python
def test_indexing_service():
    """Test indexing service command operations."""
    service = IndexingService()
    config = create_test_config()

    result = service.index_workspace("/test/workspace", config)
    assert result.processed_files > 0
    assert result.total_blocks > 0
    assert len(result.errors) == 0

def test_search_service():
    """Test search service command operations."""
    service = SearchService()
    config = create_test_config()

    result = service.search_code("test query", config)
    assert len(result.results) >= 0
    assert result.total_found >= 0
    assert result.execution_time > 0

def test_configuration_service_queries():
    """Test configuration service query operations."""
    service = ConfigurationService()
    config = create_test_config()

    # Test file status query
    status = service.get_file_status("src/main.py", config)
    assert status.file_path == "src/main.py"
    assert isinstance(status.is_processed, bool)

    # Test processing stats query
    stats = service.get_processing_stats(config)
    assert isinstance(stats.total_files, int)
    assert isinstance(stats.processed_files, int)
```

**Integration Tests Required**:
- Test CQRS pattern in full CLI workflows
- Test command/query separation in MCP tools
- Test service composition and dependency injection

**Success Criteria**:
- **Code Quality Metrics**:
  - Reduce CLI method complexity by 60%
  - Achieve 90% test coverage for service classes
  - Clear separation between command and query operations
- **Functional Validation**:
  - All existing CLI functionality preserved
  - Better error isolation and handling
  - Improved testability of individual operations
- **Rollback Procedure**:
  - Keep backup of original CLI implementation
  - Implement service compatibility layer
  - Gradual migration with feature flags

**Dependencies**: Sprint 2 (configuration service available)
**Prerequisites for Sprint 4**: CQRS services for chunking strategy refactoring

## Sprint 4: Chunking Strategy Refactoring (Week 4)

### 4.1 Extract Chunking Strategy Components

**Goal**: Break down the complex TreeSitterChunkingStrategy class into focused, single-responsibility components to improve maintainability and testability.

**Affected Code Sections**:
- `src/code_index/chunking.py` (Lines 163-1388)
- `src/code_index/treesitter_queries.py` (query management)

**Rationale**: The TreeSitterChunkingStrategy class is 1,225 lines with multiple responsibilities, making it difficult to maintain and test.

**Implementation Steps**:

1. **Create Language Detection Service** (`src/code_index/language_detection.py`):
   ```python
   class LanguageDetector:
       def detect_language(self, file_path: str) -> Optional[str]:
           """Detect programming language from file path."""
           pass

       def get_supported_languages(self) -> List[str]:
           """Get list of supported languages."""
           pass

       def is_language_supported(self, language: str) -> bool:
           """Check if language is supported."""
           pass
   ```

2. **Create Query Management Service** (`src/code_index/query_manager.py`):
   ```python
   class TreeSitterQueryManager:
       def get_queries_for_language(self, language: str) -> Optional[str]:
           """Get Tree-sitter queries for language."""
           pass

       def compile_query(self, language: str, query_text: str) -> Any:
           """Compile Tree-sitter query."""
           pass

       def validate_query(self, language: str, query_text: str) -> bool:
           """Validate query syntax."""
           pass
   ```

3. **Create Parser Management Service** (`src/code_index/parser_manager.py`):
   ```python
   class TreeSitterParserManager:
       def get_parser(self, language: str) -> Optional[Any]:
           """Get Tree-sitter parser for language."""
           pass

       def cleanup_resources(self) -> None:
           """Clean up parser resources."""
           pass

       def validate_parser(self, language: str) -> bool:
           """Validate parser availability."""
           pass
   ```

4. **Refactor TreeSitterChunkingStrategy**:
   - Use composition with new service classes
   - Reduce class to core chunking logic only
   - Implement dependency injection pattern

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_treesitter_internal.py` (if exists) - Tests internal Tree-sitter implementation
- `tests/test_treesitter_caching.py` (if exists) - Tests internal caching mechanisms
- Test methods in `tests/test_treesitter.py` that test private methods or internal state
- Test methods in `tests/test_chunking.py` that test implementation details rather than behavior

**Existing Tests to Update**:
- `tests/test_treesitter.py` - Update Tree-sitter tests to use new service composition
- `tests/test_treesitter_integration.py` - Update integration tests to use LanguageDetector
- `tests/test_modern_treesitter.py` - Update modern Tree-sitter tests to use new services

**New Tests to Add**:
```python
def test_language_detector():
    """Test language detection service."""
    detector = LanguageDetector()

    # Test various file extensions
    assert detector.detect_language("src/main.py") == "python"
    assert detector.detect_language("src/app.js") == "javascript"
    assert detector.detect_language("src/style.css") == "css"
    assert detector.detect_language("unknown.xyz") is None

def test_query_manager():
    """Test query management service."""
    manager = TreeSitterQueryManager()

    # Test query retrieval
    python_queries = manager.get_queries_for_language("python")
    assert python_queries is not None
    assert "function_definition" in python_queries

    # Test query compilation
    query = manager.compile_query("python", python_queries)
    assert query is not None

def test_parser_manager():
    """Test parser management service."""
    manager = TreeSitterParserManager()

    # Test parser retrieval
    parser = manager.get_parser("python")
    assert parser is not None

    # Test parser validation
    assert manager.validate_parser("python") == True
    assert manager.validate_parser("unsupported") == False
```

**Integration Tests Required**:
- Test chunking strategy composition
- Test service integration in full parsing workflow
- Test resource cleanup and memory management

**Success Criteria**:
- **Code Quality Metrics**:
  - Reduce TreeSitterChunkingStrategy complexity by 70%
  - Achieve 95% test coverage for individual services
  - Clear separation of concerns between components
- **Functional Validation**:
  - All existing chunking functionality preserved
  - Better error isolation and handling
  - Improved resource management
- **Rollback Procedure**:
  - Keep backup of original chunking strategy
  - Implement service compatibility layer
  - Gradual migration with fallback mechanisms

**Dependencies**: Sprint 3 (CQRS services available)
**Prerequisites for Sprint 5**: Refactored chunking components for testing improvements

## Sprint 5: Testing Infrastructure Improvements (Week 5)

### 5.1 Create Comprehensive Testing Utilities

**Goal**: Develop comprehensive testing utilities and fixtures to improve test coverage and quality across the refactored codebase.

**Affected Code Sections**:
- `tests/conftest.py` (existing test configuration)
- `tests/` (all test files)

**Rationale**: The refactored codebase needs comprehensive testing utilities to ensure quality and maintainability of the new architecture.

**Implementation Steps**:

1. **Create Test Data Generator** (`tests/utilities/test_data_generator.py`):
   ```python
   class TestDataGenerator:
       def create_test_config(self, overrides: Dict = None) -> Config:
           """Create test configuration with overrides."""
           pass

       def create_test_files(self, file_specs: List[Dict]) -> List[str]:
           """Create test files with specified content."""
           pass

       def create_mock_services(self) -> Dict[str, Any]:
           """Create mock services for testing."""
           pass

       def create_test_workspace(self, structure: Dict) -> str:
           """Create test workspace with directory structure."""
           pass
   ```

2. **Create Service Mocks** (`tests/utilities/service_mocks.py`):
   ```python
   class MockOllamaEmbedder:
       def create_embeddings(self, texts: List[str]) -> Dict:
           """Mock embedding creation."""
           pass

       def validate_configuration(self) -> Dict:
           """Mock configuration validation."""
           pass

   class MockQdrantVectorStore:
       def upsert_points(self, points: List[Dict]) -> None:
           """Mock point upsertion."""
           pass

       def search(self, query_vector: List[float], **kwargs) -> List[Dict]:
           """Mock vector search."""
           pass
   ```

3. **Create Test Fixtures** (`tests/utilities/test_fixtures.py`):
   ```python
   class TestFixtures:
       @pytest.fixture
       def sample_config(self):
           """Provide sample configuration for tests."""
           pass

       @pytest.fixture
       def mock_services(self):
           """Provide mock services for testing."""
           pass

       @pytest.fixture
       def test_workspace(self):
           """Provide test workspace with sample files."""
           pass
   ```

4. **Update Test Configuration**:
   - Update `conftest.py` with new fixtures
   - Add test utilities to test configuration
   - Implement test data factories

**Impacted Test Cases**:

**Test Cases to Remove**:
- `tests/test_data_creation.py` (if exists) - Redundant test data creation utilities
- `tests/test_helpers.py` (if exists) - Redundant test helper functions
- `tests/test_mocks.py` (if exists) - Redundant mock implementations
- Duplicate test fixtures in individual test files
- Scattered test utility functions across test files

**Existing Tests to Update**:
- All existing test files to use new fixtures and utilities from TestDataGenerator
- Update test configuration to use centralized utilities and service mocks
- Migrate existing test data creation to use TestDataGenerator

**New Tests to Add**:
```python
def test_test_data_generator():
    """Test test data generator functionality."""
    generator = TestDataGenerator()

    # Test configuration generation
    config = generator.create_test_config({"embedding_length": 512})
    assert config.embedding_length == 512
    assert config.ollama_base_url == "http://localhost:11434"

    # Test file creation
    files = generator.create_test_files([
        {"name": "test.py", "content": "print('hello')"},
        {"name": "test.js", "content": "console.log('hello')"}
    ])
    assert len(files) == 2
    assert all(os.path.exists(f) for f in files)

def test_service_mocks():
    """Test service mock functionality."""
    embedder = MockOllamaEmbedder()
    vector_store = MockQdrantVectorStore()

    # Test mock embedding
    result = embedder.create_embeddings(["test"])
    assert "embeddings" in result
    assert len(result["embeddings"]) == 1

    # Test mock search
    results = vector_store.search([0.1, 0.2, 0.3])
    assert isinstance(results, list)

def test_integration_with_mocks():
    """Test integration using mock services."""
    config = create_test_config()
    embedder = MockOllamaEmbedder()
    vector_store = MockQdrantVectorStore()

    # Test full workflow with mocks
    embeddings = embedder.create_embeddings(["test code"])
    vector_store.upsert_points([{
        "id": "test",
        "vector": embeddings["embeddings"][0],
        "payload": {"filePath": "test.py", "codeChunk": "test code"}
    }])

    results = vector_store.search(embeddings["embeddings"][0])
    assert len(results) > 0
```

**Integration Tests Required**:
- Test full system workflows with mock services
- Test service integration and dependency injection
- Test error scenarios and edge cases

**Success Criteria**:
- **Code Quality Metrics**:
  - Achieve 90%+ test coverage across all modules
  - Reduce test setup code by 60%
  - Consistent test patterns across all modules
- **Functional Validation**:
  - All existing functionality thoroughly tested
  - Better test isolation and reliability
  - Faster test execution with mocks
- **Rollback Procedure**:
  - Keep backup of original test files
  - Implement test compatibility layer
  - Gradual migration of test suites

**Dependencies**: All previous sprints completed
**Prerequisites for Sprint 6**: None (final sprint)

## Implementation Guidelines

### Risk Mitigation Strategies

1. **Gradual Rollout**: Each sprint implements changes incrementally with feature flags
2. **Comprehensive Testing**: Every sprint includes extensive test coverage
3. **Rollback Procedures**: Each sprint has clear rollback mechanisms
4. **Monitoring**: Track system performance and error rates during rollout

### Code Quality Standards

1. **Single Responsibility**: Each class and method has one clear purpose
2. **Dependency Injection**: Services use dependency injection for testability
3. **Interface Segregation**: Clear interfaces between components
4. **Error Handling**: Consistent error handling across all components

### Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Ensure no performance degradation

This sprint-based approach ensures systematic improvement of the codebase while maintaining system stability and functionality throughout the refactoring process.

## Test Maintenance Summary

### Overall Test Impact
- **Total Test Files to Remove**: ~15-20 redundant or implementation-specific test files
- **Test Methods to Remove**: ~50-70 methods testing internal implementation details
- **New Test Files to Create**: 8-10 focused test files for new services
- **New Test Methods to Add**: ~100-120 methods testing behavior over implementation
- **Net Test Reduction**: 25-30% fewer tests with better coverage and maintainability

### Test Quality Improvements
- **Before Refactoring**: 200+ tests with duplication and brittleness
- **After Refactoring**: 150-160 focused tests with clear separation of concerns
- **Coverage Maintenance**: 95%+ of existing functionality covered by new tests
- **Test Execution Time**: 30-40% reduction due to better isolation and mocking

### Migration Strategy
1. **Sprint 1**: Remove ~20% of tests (error handling and file processing duplication)
2. **Sprint 2**: Remove ~15% of tests (service validation and configuration duplication)
3. **Sprint 3**: Remove ~25% of tests (CLI implementation coupling)
4. **Sprint 4**: Remove ~20% of tests (chunking strategy internal details)
5. **Sprint 5**: Remove ~20% of tests (redundant utilities and scattered fixtures)

This strategic test removal approach reduces maintenance burden while improving test quality and execution speed.