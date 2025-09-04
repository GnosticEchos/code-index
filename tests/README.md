# MCP Server Test Suite

This directory contains comprehensive tests for the MCP (Model Context Protocol) Server implementation. The test suite covers unit tests, integration tests, and end-to-end workflows to ensure the reliability and correctness of the MCP server functionality.

## Test Structure

### Unit Tests

- **`test_mcp_server.py`** - Tests for the main MCP server class, initialization, configuration loading, and tool registration
- **`test_mcp_config_manager.py`** - Tests for configuration management, validation, and override functionality
- **`test_mcp_operation_estimator.py`** - Tests for workspace analysis, complexity estimation, and optimization recommendations
- **`test_mcp_progress_reporter.py`** - Tests for progress reporting, ETA calculations, and batch operation tracking
- **`test_mcp_index_tool.py`** - Tests for the index tool including parameter validation and execution
- **`test_mcp_search_tool.py`** - Tests for the search tool including query processing and result formatting
- **`test_mcp_collections_tool.py`** - Tests for the collections tool including safety confirmations and management operations
- **`test_mcp_error_handler.py`** - Tests for error handling, structured responses, and actionable guidance

### Integration Tests

- **`test_mcp_integration.py`** - Integration tests for MCP protocol, service connectivity, and end-to-end workflows

### Test Configuration

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`test_mcp_runner.py`** - Test runner utilities and environment management
- **`pytest.ini`** - Pytest configuration file

## Running Tests

### Prerequisites

Ensure you have the required dependencies installed:

```bash
pip install pytest pytest-asyncio pytest-mock
```

Optional for coverage reporting:
```bash
pip install pytest-cov
```

### Running All Tests

```bash
# Run all MCP tests
python tests/test_mcp_runner.py all

# Or using pytest directly
pytest tests/test_mcp_*.py -v
```

### Running Specific Test Categories

```bash
# Unit tests only
python tests/test_mcp_runner.py unit

# Integration tests only
python tests/test_mcp_runner.py integration

# Specific test file
python tests/test_mcp_runner.py specific --test-name test_mcp_server.py
```

### Running Tests with Coverage

```bash
pytest tests/test_mcp_*.py --cov=src.code_index.mcp_server --cov-report=html --cov-report=term-missing
```

### Running Tests by Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

## Test Categories and Coverage

### Unit Test Coverage

#### MCP Server Core (`test_mcp_server.py`)
- ✅ Server initialization and configuration
- ✅ Service validation (Ollama, Qdrant)
- ✅ Tool registration and lifecycle management
- ✅ Error handling and resource cleanup

#### Configuration Management (`test_mcp_config_manager.py`)
- ✅ Configuration loading and validation
- ✅ Parameter override application
- ✅ Compatibility checking and suggestions
- ✅ Documentation generation

#### Operation Estimation (`test_mcp_operation_estimator.py`)
- ✅ Workspace complexity analysis
- ✅ Time estimation algorithms
- ✅ Optimization recommendations
- ✅ Warning level determination

#### Progress Reporting (`test_mcp_progress_reporter.py`)
- ✅ Progress tracking and ETA calculations
- ✅ Batch operation management
- ✅ MCP-compatible progress updates
- ✅ Error handling in callbacks

#### Index Tool (`test_mcp_index_tool.py`)
- ✅ Parameter validation (workspace, config, overrides)
- ✅ Operation estimation and warnings
- ✅ Indexing execution with mocked components
- ✅ Error scenarios and recovery

#### Search Tool (`test_mcp_search_tool.py`)
- ✅ Query validation and processing
- ✅ Service connectivity checks
- ✅ Result formatting and ranking
- ✅ Configuration override application

#### Collections Tool (`test_mcp_collections_tool.py`)
- ✅ Subcommand routing and validation
- ✅ Safety confirmations for destructive operations
- ✅ Collection management operations
- ✅ Error handling and user guidance

#### Error Handler (`test_mcp_error_handler.py`)
- ✅ Structured error response generation
- ✅ Actionable guidance creation
- ✅ Error categorization and formatting
- ✅ Service-specific error handling

### Integration Test Coverage

#### MCP Protocol Integration (`test_mcp_integration.py`)
- ✅ Server initialization with FastMCP
- ✅ Tool registration and MCP protocol compliance
- ✅ Service validation integration
- ✅ Lifespan management

#### Service Connectivity
- ✅ Ollama service integration and failure scenarios
- ✅ Qdrant service integration and error handling
- ✅ Service validation workflows

#### End-to-End Workflows
- ✅ Complete index → search → collections flow
- ✅ Configuration override workflows
- ✅ Error handling and recovery scenarios
- ✅ Configuration example validation

## Test Fixtures and Utilities

### Common Fixtures

- **`temp_workspace`** - Creates temporary workspace with test files
- **`temp_config_file`** - Creates test configuration file
- **`mock_context`** - Mock MCP context for tool calls
- **`mock_ollama_embedder`** - Mock Ollama embedder service
- **`mock_qdrant_vector_store`** - Mock Qdrant vector store
- **`mock_collection_manager`** - Mock collection manager
- **`mock_indexing_components`** - Mock indexing pipeline components
- **`sample_search_results`** - Sample search result data
- **`sample_collections_data`** - Sample collections data
- **`configuration_examples`** - Various configuration examples

### Custom Assertions

- **`assert_mcp_error_response`** - Validates MCP error response format
- **`assert_mcp_success_response`** - Validates MCP success response format
- **`assert_search_results_format`** - Validates search results structure

### Test Environment Management

The `MCPTestEnvironment` class provides utilities for:
- Creating test workspaces with custom files
- Setting up mock services consistently
- Managing temporary resources and cleanup

## Test Data and Scenarios

### Test Workspaces

Tests use realistic project structures including:
- Python source files with functions and classes
- Configuration files (JSON, requirements.txt)
- Documentation files (README.md)
- Nested directory structures

### Configuration Scenarios

Tests cover various configuration scenarios:
- **Fast Indexing** - Optimized for speed with basic chunking
- **Semantic Accuracy** - Tree-sitter with comprehensive analysis
- **Large Repository** - Memory-optimized for big codebases
- **Custom Overrides** - Parameter override combinations

### Error Scenarios

Comprehensive error testing includes:
- Service connectivity failures (Ollama, Qdrant)
- Invalid parameter combinations
- Missing or corrupted configuration files
- Workspace access and permission issues
- Resource exhaustion scenarios

## Best Practices

### Writing New Tests

1. **Use Descriptive Names** - Test names should clearly describe what is being tested
2. **Follow AAA Pattern** - Arrange, Act, Assert structure
3. **Use Appropriate Fixtures** - Leverage existing fixtures for consistency
4. **Mock External Dependencies** - Always mock Ollama, Qdrant, and file system operations
5. **Test Error Conditions** - Include both success and failure scenarios
6. **Validate Response Formats** - Use custom assertions for MCP response validation

### Test Organization

1. **Group Related Tests** - Use test classes to group related functionality
2. **Use Markers** - Apply appropriate pytest markers (unit, integration, slow)
3. **Document Complex Tests** - Add docstrings for complex test scenarios
4. **Keep Tests Independent** - Each test should be able to run in isolation

### Performance Considerations

1. **Mock Heavy Operations** - Mock file I/O, network calls, and embedding generation
2. **Use Appropriate Fixtures** - Choose session, module, or function scope appropriately
3. **Parallel Execution** - Ensure tests can run in parallel safely
4. **Resource Cleanup** - Always clean up temporary resources

## Continuous Integration

The test suite is designed to run in CI environments with:
- Consistent mock services (no external dependencies)
- Deterministic test data and results
- Comprehensive error reporting
- Coverage reporting integration

### CI Configuration Example

```yaml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/test_mcp_*.py --cov=src.code_index.mcp_server --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

1. **Import Errors** - Ensure `src` is in Python path (handled by conftest.py)
2. **Async Test Failures** - Use `pytest-asyncio` and `@pytest.mark.asyncio`
3. **Mock Conflicts** - Check for conflicting patches in different test files
4. **Temporary File Cleanup** - Use context managers and proper fixture cleanup

### Debugging Tests

1. **Verbose Output** - Use `-v` flag for detailed test output
2. **Show Locals** - Use `--showlocals` to see local variables on failure
3. **PDB Integration** - Use `--pdb` to drop into debugger on failure
4. **Log Output** - Enable logging with `--log-cli-level=DEBUG`

## Contributing

When adding new functionality to the MCP server:

1. **Write Tests First** - Follow TDD principles where possible
2. **Maintain Coverage** - Ensure new code is covered by tests
3. **Update Documentation** - Update this README for new test categories
4. **Run Full Suite** - Verify all tests pass before submitting changes

For questions or issues with the test suite, please refer to the main project documentation or open an issue.