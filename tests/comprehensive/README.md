# Comprehensive Search Tests

This directory contains comprehensive test suites for validating the code-index search functionality.

## Test Files

### [`comprehensive_search_test.py`](comprehensive_search_test.py:1)
Main comprehensive test suite implementing all 10 test requirements:
- Basic search queries
- Semantic code-specific queries  
- Score threshold variations
- Result limit variations
- File type filtering
- Performance measurement
- Result verification
- Error handling and edge cases

### [`test_treesitter_search.py`](test_treesitter_search.py:1)
Tree-sitter specific tests for semantic chunking validation:
- Language-aware parsing (Python, JavaScript, Rust)
- Semantic block extraction (functions, classes, methods)
- Search quality assessment
- Chunking strategy comparison

### [`run_comprehensive_search_tests.py`](run_comprehensive_search_tests.py:1)
Coordinated test runner that executes both test suites and generates comprehensive reports.

## Running the Tests

```bash
# Run comprehensive tests with original model configuration
python tests/comprehensive/run_comprehensive_search_tests.py --config ../search_with_original_model.json

# Run individual test suites
python -m pytest tests/comprehensive/comprehensive_search_test.py -v
python -m pytest tests/comprehensive/test_treesitter_search.py -v
```

## Reports

Test reports are generated in the [`tests/reports/`](../reports/) directory:
- `comprehensive_test_results.json` - Detailed JSON results
- `comprehensive_test_results.md` - Summary report
- `comprehensive_search_test_report.md` - Comprehensive documentation

## Test Requirements Covered

✅ **Basic Search Queries** - 10+ query types  
✅ **Semantic Code-Specific Queries** - 10 semantic categories  
✅ **Score Threshold Variation** - 5 threshold levels  
✅ **Result Limit Variation** - 5 result limits  
✅ **File Type Filtering** - 8 file types  
✅ **Performance Measurement** - 5 iterations with timing  
✅ **Result Verification** - Content validation  
✅ **Error Handling** - Edge case testing  
✅ **Detailed Reporting** - JSON and Markdown formats  
✅ **Tree-sitter Integration** - Semantic chunking validation