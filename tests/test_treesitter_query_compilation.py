"""
Test script to validate Tree-sitter query compilation for all supported languages.
This test ensures that all Tree-sitter queries are syntactically correct and can be compiled.
"""

import pytest
from code_index.chunking import TreeSitterChunkingStrategy
from code_index.config import Config


class TestTreeSitterQueryCompilation:
    """Test suite for Tree-sitter query compilation."""
    
    def setup_method(self):
        """Set up test configuration."""
        self.config = Config()
        self.config.use_tree_sitter = True
        self.strategy = TreeSitterChunkingStrategy(self.config)
    
    def test_all_supported_languages_have_valid_queries(self):
        """Test that all supported languages have valid Tree-sitter queries."""
        # List of all languages supported by the system
        supported_languages = [
            'typescript', 'markdown', 'python', 'javascript', 'rust', 'go', 'java',
            'cpp', 'c', 'csharp', 'ruby', 'php', 'kotlin', 'swift', 'lua', 'json',
            'yaml', 'html', 'css', 'scss', 'sql', 'bash', 'dart', 'scala', 'perl',
            'haskell', 'elixir', 'clojure', 'erlang', 'ocaml', 'fsharp', 'vb', 'r',
            'matlab', 'julia', 'groovy', 'dockerfile', 'makefile', 'cmake', 'protobuf',
            'graphql', 'vue', 'svelte', 'astro', 'tsx', 'elm', 'toml', 'xml', 'ini',
            'csv', 'tsv', 'terraform', 'solidity', 'verilog', 'vhdl', 'zig', 'nim',
            'v', 'tcl', 'scheme', 'commonlisp', 'racket', 'fish', 'powershell', 'zsh',
            'rst', 'org', 'latex', 'sqlite', 'mysql', 'postgresql', 'hcl', 'puppet',
            'thrift', 'proto', 'capnp', 'smithy'
        ]
        
        compilation_errors = []
        missing_queries = []
        successful_compilations = []
        
        print("\nTesting Tree-sitter query compilation for all supported languages...")
        
        for lang in supported_languages:
            query = self.strategy._get_queries_for_language(lang)
            if query:
                try:
                    # Try to compile the query using the config manager
                    compiled_query = self.strategy.config_manager._compile_query(lang, query)
                    if compiled_query:
                        successful_compilations.append(lang)
                        print(f"✅ {lang}: Query compiled successfully")
                    else:
                        compilation_errors.append(f"{lang}: Failed to compile query (returned None)")
                        print(f"❌ {lang}: Failed to compile query")
                except Exception as e:
                    compilation_errors.append(f"{lang}: Error compiling query - {e}")
                    print(f"❌ {lang}: Error compiling query - {e}")
            else:
                missing_queries.append(lang)
                print(f"⚠️  {lang}: No query defined (will use fallback)")
        
        # Report results
        print(f"\n=== COMPILATION RESULTS ===")
        print(f"Successful: {len(successful_compilations)} languages")
        print(f"Errors: {len(compilation_errors)} languages")
        print(f"Missing queries: {len(missing_queries)} languages")
        
        if compilation_errors:
            print("\n=== COMPILATION ERRORS ===")
            for error in compilation_errors:
                print(f"  {error}")
        
        if missing_queries:
            print("\n=== MISSING QUERIES ===")
            for lang in missing_queries:
                print(f"  {lang}")
        
        # Assert that there are no compilation errors
        assert len(compilation_errors) == 0, f"Found {len(compilation_errors)} query compilation errors: {compilation_errors}"
        
        # For languages without queries, ensure they have fallback node types defined
        for lang in missing_queries:
            node_types = self.strategy._get_node_types_for_language(lang)
            assert node_types, f"Language {lang} has no query and no fallback node types defined"
            print(f"✅ {lang}: Has fallback node types: {node_types}")
    
    def test_typescript_query_specific_fix(self):
        """Test that TypeScript query specifically compiles without syntax errors."""
        # This test specifically targets the TypeScript query that was causing issues
        typescript_query = self.strategy._get_queries_for_language('typescript')
        assert typescript_query is not None, "TypeScript query should be defined"
        
        # Try to compile the query using the config manager
        compiled_query = self.strategy.config_manager._compile_query('typescript', typescript_query)
        assert compiled_query is not None, "TypeScript query should compile successfully"
        
        print("✅ TypeScript query compiled successfully after fix")
    
    def test_markdown_query_specific(self):
        """Test that Markdown query is properly defined and compiles."""
        markdown_query = self.strategy._get_queries_for_language('markdown')
        assert markdown_query is not None, "Markdown query should be defined after fix"
        
        # Try to compile the query using the config manager
        compiled_query = self.strategy.config_manager._compile_query('markdown', markdown_query)
        assert compiled_query is not None, "Markdown query should compile successfully"
        
        print("✅ Markdown query compiled successfully")


def run_comprehensive_query_test():
    """Run the comprehensive query test and return results."""
    tester = TestTreeSitterQueryCompilation()
    tester.setup_method()
    
    print("=" * 60)
    print("COMPREHENSIVE TREE-SITTER QUERY COMPILATION TEST")
    print("=" * 60)
    
    try:
        tester.test_all_supported_languages_have_valid_queries()
        tester.test_typescript_query_specific_fix()
        tester.test_markdown_query_specific()
        print("\n🎉 ALL TESTS PASSED! Tree-sitter queries are properly configured.")
        return True
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = run_comprehensive_query_test()
    exit(0 if success else 1)