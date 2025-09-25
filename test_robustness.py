from code_index.services.block_extractor import TreeSitterBlockExtractor
from code_index.config import Config
from code_index.errors import ErrorHandler

# Test the robustness improvements
config = Config()
config.tree_sitter_debug_logging = True
error_handler = ErrorHandler('test')
extractor = TreeSitterBlockExtractor(config, error_handler)

# Test with a problematic file that would previously fail
test_code = '''
def problematic_function():
    # This has some edge cases that might cause tree-sitter issues
    x = "unclosed_string
    return x

class ProblematicClass:
    def __init__(self):
        self.value = 42
'''

print('Testing robustness improvements...')
blocks = extractor.extract_blocks(test_code, 'test.py', 'hash123', 'python')
print(f'Extracted {len(blocks)} blocks from problematic code')

# Check failure stats
stats = extractor.get_treesitter_failure_stats()
print(f'Total failures: {stats["total_failures"]}')
print(f'Failures by language: {stats["failures_by_language"]}')
print(f'Failures by operation: {stats["failures_by_operation"]}')
