"""
Chunking strategies for the code index tool.
"""
import os
import traceback
import weakref
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from weakref import WeakValueDictionary

from code_index.config import Config
from code_index.models import CodeBlock
from code_index.utils import get_file_hash
from code_index.treesitter_queries import get_queries_for_language as get_ts_queries

class TreeSitterError(Exception):
    """Base exception for Tree-sitter related errors."""
    pass


class TreeSitterParserError(TreeSitterError):
    """Exception raised when Tree-sitter parser fails to load."""
    pass


class TreeSitterQueryError(TreeSitterError):
    """Exception raised when Tree-sitter query execution fails."""
    pass


class TreeSitterLanguageError(TreeSitterError):
    """Exception raised when language is not supported by Tree-sitter."""
    pass


class TreeSitterFileTooLargeError(TreeSitterError):
    """Exception raised when file is too large for Tree-sitter parsing."""
    pass


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into a list of CodeBlock objects."""
        pass


class LineChunkingStrategy(ChunkingStrategy):
    """Chunking strategy based on lines."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.min_block_chars = 50
        self.max_block_chars = 1000
        self.max_chars_tolerance_factor = 1.15

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks based on lines."""
        lines = text.split("\n")
        blocks: List[CodeBlock] = []
        current_chunk_lines: List[str] = []
        current_chunk_length = 0
        chunk_start_line = 1

        for i, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for newline
            current_chunk_length += line_length
            current_chunk_lines.append(line)

            if (
                current_chunk_length >= self.max_block_chars * self.max_chars_tolerance_factor
                or i == len(lines) - 1
            ):
                chunk_content = "\n".join(current_chunk_lines)
                if len(chunk_content.strip()) >= self.min_block_chars:
                    segment_hash = file_hash + str(chunk_start_line)
                    block = CodeBlock(
                        file_path=file_path,
                        identifier=None,
                        type="chunk",
                        start_line=chunk_start_line,
                        end_line=chunk_start_line + len(current_chunk_lines) - 1,
                        content=chunk_content,
                        file_hash=file_hash,
                        segment_hash=segment_hash,
                    )
                    blocks.append(block)

                current_chunk_lines = []
                current_chunk_length = 0
                chunk_start_line = i + 2  # Next line (1-indexed)

        return blocks


class TokenChunkingStrategy(ChunkingStrategy):
    """Chunking strategy based on tokens."""

    def __init__(self, config: Config):
        super().__init__(config)
        self.min_block_chars = 50

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks based on tokens."""
        try:
            from langchain_text_splitters import TokenTextSplitter  # type: ignore

            chunk_size = int(getattr(self.config, "token_chunk_size", 1000) or 1000)
            chunk_overlap = int(getattr(self.config, "token_chunk_overlap", 200) or 200)
            splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            chunks: List[str] = splitter.split_text(text)
            if not chunks:
                return []
            return self._map_chunks_with_lines(text, chunks, file_path, file_hash)
        except Exception:
            print(
                "Warning: Token-based chunking requested but 'langchain-text-splitters' is not available; falling back to line-based splitting."
            )
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

    def _map_chunks_with_lines(
        self, original_text: str, chunks: List[str], file_path: str, file_hash: str
    ) -> List[CodeBlock]:
        """Approximate start_line/end_line mapping for token chunks."""
        blocks: List[CodeBlock] = []
        pos = 0
        consumed_lines = 1  # 1-indexed line counter when search fails
        for chunk in chunks:
            found_index = original_text.find(chunk, pos)
            if found_index != -1:
                start_line = original_text.count("\n", 0, found_index) + 1
                add_one = 0 if chunk.endswith("\n") else 1
                end_line = start_line + chunk.count("\n") + add_one - 1
                pos = found_index + max(1, len(chunk) - 1)
            else:
                start_line = consumed_lines
                add_one = 0 if chunk.endswith("\n") else 1
                end_line = start_line + chunk.count("\n") + add_one - 1
                consumed_lines = end_line + 1

            if len(chunk.strip()) >= self.min_block_chars:
                segment_hash = file_hash + f"{start_line}"
                blocks.append(
                    CodeBlock(
                        file_path=file_path,
                        identifier=None,
                        type="chunk",
                        start_line=start_line,
                        end_line=end_line,
                        content=chunk,
                        file_hash=file_hash,
                        segment_hash=segment_hash,
                    )
                )
        return blocks


class TreeSitterChunkingStrategy(ChunkingStrategy):
    """Chunking strategy based on Tree-sitter."""

    def _debug(self, msg: str) -> None:
        """Conditional Tree-sitter debug logging."""
        try:
            if getattr(self.config, "tree_sitter_debug_logging", False):
                print(f"TS-DEBUG: {msg}")
        except Exception:
            pass

    def __init__(self, config: Config):
        super().__init__(config)
        self.min_block_chars = 50
        # Cache parsers per language for better performance
        self._tree_sitter_parsers: Dict[str, Any] = {}
        # Cache queries per language for better performance
        self._query_cache: Dict[str, Any] = {}
        # Track processed languages for batch optimization
        self._processed_languages: Set[str] = set()
        # Cache languages and track parser-language identities to avoid mismatch
        self._ts_languages: Dict[str, Any] = {}
        self._parser_language_ids: Dict[str, int] = {}

    def chunk(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Chunk text into blocks using Tree-sitter."""
        try:
            # Rust-specific timeout optimization
            language_key = self._get_language_key_for_path(file_path)
            if language_key == 'rust':
                # For Rust files, use more conservative settings to avoid timeouts
                original_max_blocks = getattr(self.config, "tree_sitter_max_blocks_per_file", 100)
                setattr(self.config, "tree_sitter_max_blocks_per_file", 30)  # Temporary reduction

            blocks = self._chunk_text_treesitter(text, file_path, file_hash)

            if language_key == 'rust':
                # Restore original setting
                setattr(self.config, "tree_sitter_max_blocks_per_file", original_max_blocks)

            if blocks:
                return blocks
            self._debug(f"No Tree-sitter blocks for {file_path} (lang={language_key}); fallback to line-based.")
            print(f"Warning: Tree-sitter parsing failed for {file_path}, falling back to line-based splitting.")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except TreeSitterLanguageError as e:
            # Expected error for unsupported languages
            print(f"Note: Tree-sitter not suitable for {file_path}: {e}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except TreeSitterFileTooLargeError as e:
            # Expected error for large files
            print(f"Note: {e}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except TreeSitterError as e:
            # Other Tree-sitter specific errors
            print(f"Warning: Tree-sitter parsing error for {file_path}: {e}")
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)
        except Exception as e:
            # Unexpected errors
            print(f"Warning: Unexpected Tree-sitter parsing error for {file_path}: {e}")
            traceback.print_exc()
            return LineChunkingStrategy(self.config).chunk(text, file_path, file_hash)

    def chunk_batch(self, files: List[Dict[str, Any]]) -> Dict[str, List[CodeBlock]]:
        """Process multiple files efficiently by grouping by language."""
        results = {}
        
        # Group files by language for efficient processing
        language_groups = {}
        for file_info in files:
            file_path = file_info['file_path']
            language_key = self._get_language_key_for_path(file_path)
            if language_key:
                if language_key not in language_groups:
                    language_groups[language_key] = []
                language_groups[language_key].append(file_info)
        
        # Process each language group with optimized resource usage
        for language_key, language_files in language_groups.items():
            # Ensure parser and query are loaded for this language
            parser = self._get_tree_sitter_parser(language_key)
            queries = self._get_queries_for_language(language_key)
            
            if not parser or not queries:
                # Fallback to individual processing
                for file_info in language_files:
                    results[file_info['file_path']] = self.chunk(
                        file_info['text'], file_info['file_path'], file_info['file_hash']
                    )
                continue
            
            # Process all files in this language group
            for file_info in language_files:
                try:
                    blocks = self._chunk_text_treesitter(
                        file_info['text'], file_info['file_path'], file_info['file_hash']
                    )
                    if blocks:
                        results[file_info['file_path']] = blocks
                    else:
                        self._debug(f"No Tree-sitter blocks for {file_info['file_path']} (lang={language_key}); fallback to line-based.")
                        print(f"Warning: Tree-sitter parsing failed for {file_info['file_path']}, falling back to line-based splitting.")
                        results[file_info['file_path']] = LineChunkingStrategy(self.config).chunk(
                            file_info['text'], file_info['file_path'], file_info['file_hash']
                        )
                except TreeSitterError as e:
                    print(f"Warning: Tree-sitter batch processing failed for {file_info['file_path']}: {e}")
                    # Fallback to line-based in batch mode to avoid recursion
                    results[file_info['file_path']] = LineChunkingStrategy(self.config).chunk(
                        file_info['text'], file_info['file_path'], file_info['file_hash']
                    )
        
        return results

    def _chunk_text_treesitter(self, text: str, file_path: str, file_hash: str) -> List[CodeBlock]:
        """Extract semantic blocks using Tree-sitter with performance optimizations."""
        max_size = getattr(self.config, "tree_sitter_max_file_size_bytes", 512 * 1024)
        text_size = len(text.encode('utf-8'))
        if text_size > max_size:
            self._debug(f"Skipping {file_path}: size {text_size} > max {max_size}")
            raise TreeSitterFileTooLargeError(f"File {file_path} too large for Tree-sitter parsing ({text_size} > {max_size} bytes)")

        if not self._should_process_file_for_treesitter(file_path):
            self._debug(f"Filtered by config: {file_path}")
            raise TreeSitterError(f"File {file_path} filtered out by Tree-sitter configuration")

        language_key = self._get_language_key_for_path(file_path)
        if not language_key:
            self._debug(f"No language detected for {file_path}")
            raise TreeSitterLanguageError(f"Unsupported language for Tree-sitter parsing: {file_path}")

        parser = self._get_tree_sitter_parser(language_key)
        if not parser:
            self._debug(f"Parser load failed for lang={language_key}, file={file_path}")
            raise TreeSitterParserError(f"Failed to load Tree-sitter parser for {language_key}")

        try:
            self._debug(f"Parsing {file_path} as {language_key}")
            tree = parser.parse(bytes(text, "utf8"))
            root_node = tree.root_node

            blocks = self._extract_semantic_blocks_efficient(
                root_node, text, file_path, file_hash, language_key
            )
            self._debug(f"Extracted {len(blocks)} Tree-sitter blocks for {file_path} (lang={language_key})")

            max_blocks = getattr(self.config, "tree_sitter_max_blocks_per_file", 100)
            if len(blocks) > max_blocks:
                print(f"Warning: Limiting Tree-sitter blocks from {len(blocks)} to {max_blocks} for {file_path}")
                blocks = blocks[:max_blocks]

            return blocks
        except TreeSitterError:
            raise  # Re-raise Tree-sitter specific errors
        except Exception as e:
            raise TreeSitterError(f"Tree-sitter parsing failed for {file_path}: {e}")

    def _get_language_key_for_path(self, file_path: str) -> Optional[str]:
        """Map file extension to Tree-sitter language key using fast detection."""
        try:
            from whats_that_code.extension_based import guess_by_extension

            guesses = guess_by_extension(file_path)

            language_mapping = {
                'python': 'python',
                'javascript': 'javascript',
                'typescript': 'typescript',
                'tsx': 'tsx',
                'go': 'go',
                'java': 'java',
                'cpp': 'cpp',
                'c': 'c',
                'rust': 'rust',
                'csharp': 'csharp',
                'ruby': 'ruby',
                'php': 'php',
                'kotlin': 'kotlin',
                'swift': 'swift',
                'lua': 'lua',
                'json': 'json',
                'yaml': 'yaml',
                'markdown': 'markdown',
                'html': 'html',
                'css': 'css',
                'scss': 'scss',
                'bash': 'bash',
                'shell': 'bash',
                'dart': 'dart',
                'scala': 'scala',
                'perl': 'perl',
                'haskell': 'haskell',
                'elixir': 'elixir',
                'clojure': 'clojure',
                'clojurescript': 'clojure',  # Added for .cljs files
                'erlang': 'erlang',
                'ocaml': 'ocaml',
                'fsharp': 'fsharp',
                'docker': 'dockerfile',  # Added for Dockerfile
                'vb': 'vb',
                'vbnet': 'vb',  # Added for .vb files
                'r': 'r',
                'matlab': 'matlab',
                'julia': 'julia',
                'groovy': 'groovy',
                'dockerfile': 'dockerfile',
                'makefile': 'makefile',
                'graphql': 'graphql',  # Added for .graphql and .gql files
                'cmake': 'cmake',
                'protobuf': 'protobuf',
            }

            # Add support for additional languages
            language_mapping.update({
                # Web frameworks
                'vue': 'vue',
                'svelte': 'svelte',
                'astro': 'astro',
                # Configuration formats
                'toml': 'toml',
                'ini': 'ini',
                'xml': 'xml',
                # System and infrastructure
                'terraform': 'terraform',
                'thrift': 'thrift',
                'proto': 'proto',
                # Functional languages
                'elm': 'elm',
                'scheme': 'scheme',
                'commonlisp': 'commonlisp',
                'racket': 'racket',
                # Shell and scripting
                'fish': 'fish',
                'powershell': 'powershell',
                'zsh': 'zsh',
                # Markup and documentation
                'rst': 'rst',
                'org': 'org',
                'latex': 'latex',
                # Database query languages
                'sqlite': 'sqlite',
                'mysql': 'mysql',
                'postgresql': 'postgresql',
                # Smart contract languages
                'solidity': 'solidity',
                # Hardware description languages
                'verilog': 'verilog',
                'vhdl': 'vhdl',
                'systemverilog': 'systemverilog',
                # Other programming languages
                'zig': 'zig',
                'nim': 'nim',
                'v': 'v',
                'tcl': 'tcl',
                'clojurescript': 'clojurescript',
                'objc': 'objc',
                'objcpp': 'objcpp',
                'sass': 'sass',
                'less': 'less',
                'hcl': 'hcl',
                'puppet': 'puppet',
                'capnp': 'capnp',
                'smithy': 'smithy',
            })

            for guess in guesses:
                if guess in language_mapping:
                    return language_mapping[guess]

            # Fall back to manual extension mapping if whats_that_code returns empty
            return self._fallback_language_detection(file_path)
        except Exception:
            # Fall back to manual extension mapping if whats_that_code raises an exception
            return self._fallback_language_detection(file_path)
    
    def _fallback_language_detection(self, file_path: str) -> Optional[str]:
        """Fallback language detection using manual extension mapping."""
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path).lower()
        extension_to_language = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.jsx': 'javascript',
            '.go': 'go',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rs': 'rust',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.kt': 'kotlin',
            '.kts': 'kotlin',
            '.swift': 'swift',
            '.lua': 'lua',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sql': 'sql',
            '.surql': 'sql',
            # New language extensions
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.dart': 'dart',
            '.scala': 'scala',
            '.pl': 'perl',
            '.pm': 'perl',
            '.hs': 'haskell',
            '.ex': 'elixir',
            '.exs': 'elixir',
            '.clj': 'clojure',
            '.cljs': 'clojure',
            '.erl': 'erlang',
            '.hrl': 'erlang',
            '.ml': 'ocaml',
            '.mli': 'ocaml',
            '.fs': 'fsharp',
            '.fsx': 'fsharp',
            '.fsi': 'fsharp',
            '.vb': 'vb',
            '.r': 'r',
            '.m': 'matlab',
            '.jl': 'julia',
            '.groovy': 'groovy',
            '.cmake': 'cmake',
            '.proto': 'protobuf',
            '.graphql': 'graphql',
            '.gql': 'graphql',
            '.txt': None,  # Plain text files should use fallback
        }
        
        # Handle special filenames without extensions
        if filename == 'dockerfile':
            return 'dockerfile'
        elif filename == 'makefile':
            return 'makefile'
        elif filename.endswith('.cmake'):
            return 'cmake'
        
        # Additional language extensions
        additional_extensions = {
            # Web frameworks
            '.vue': 'vue',
            '.svelte': 'svelte',
            '.astro': 'astro',
            # Configuration formats
            '.toml': 'toml',
            '.ini': 'ini',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            # System and infrastructure
            '.tf': 'terraform',
            '.tfvars': 'terraform',
            '.proto': 'proto',
            '.thrift': 'thrift',
            # Functional languages
            '.elm': 'elm',
            '.hs': 'haskell',
            '.lhs': 'haskell',
            '.ml': 'ocaml',
            '.mli': 'ocaml_interface',
            # Shell and scripting
            '.fish': 'fish',
            '.ps1': 'powershell',
            '.zsh': 'zsh',
            # Markup and documentation
            '.rst': 'rst',
            '.org': 'org',
            '.tex': 'latex',
            # Database query languages
            '.sql': 'sql',
            # Smart contract languages
            '.sol': 'solidity',
            # Hardware description languages
            '.sv': 'systemverilog',
            '.svh': 'systemverilog',
            # Other programming languages
            '.zig': 'zig',
            '.nim': 'nim',
            '.v': 'v',
            '.tcl': 'tcl',
            '.swift': 'swift',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.dart': 'dart',
            '.jl': 'julia',
            '.r': 'r',
            '.pl': 'perl',
            '.pm': 'perl',
            '.lua': 'lua',
            '.rb': 'ruby',
            '.php': 'php',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.jsx': 'javascript',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.m': 'objc',
            '.mm': 'objcpp',
            # Markup and styling
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            # Data formats
            '.json': 'json',
            '.csv': 'csv',
            '.tsv': 'tsv',
        }
        
        # Check additional extensions
        if ext in additional_extensions:
            return additional_extensions[ext]
        
        return extension_to_language.get(ext)

    def _get_tree_sitter_language(self, language_key: str):
        """Get or cache a Tree-sitter Language object for a language key."""
        try:
            if language_key in self._ts_languages:
                return self._ts_languages[language_key]
            import tree_sitter_language_pack as tsl
            language = tsl.get_language(language_key)
            self._ts_languages[language_key] = language
            return language
        except Exception as e:
            self._debug(f"Failed to load Tree-sitter language for {language_key}: {e}")
            raise

    def _get_tree_sitter_parser(self, language_key: str):
        """Get or create a cached Tree-sitter parser for a language."""
        try:
            # Try to get from cache first
            if language_key in self._tree_sitter_parsers:
                return self._tree_sitter_parsers[language_key]

            from tree_sitter import Parser

            language = self._get_tree_sitter_language(language_key)
            parser = Parser()
            parser.language = language
            # Track language identity used by parser for this language_key
            self._parser_language_ids[language_key] = id(language)

            # Store in cache
            self._tree_sitter_parsers[language_key] = parser
            return parser
        except Exception as e:
            print(f"Warning: Failed to load Tree-sitter parser for {language_key}: {e}")
            return None

    def cleanup_resources(self):
        """Explicitly cleanup Tree-sitter resources."""
        # Clear parser cache (weak references will be collected automatically)
        try:
            self._tree_sitter_parsers.clear()
        except Exception:
            pass

        # Clear language cache and identity map
        try:
            self._ts_languages.clear()
        except Exception:
            pass
        try:
            self._parser_language_ids.clear()
        except Exception:
            pass

        # Clear query cache
        try:
            self._query_cache.clear()
        except Exception:
            pass

        # Clear processed languages tracking
        try:
            self._processed_languages.clear()
        except Exception:
            pass

        print("Tree-sitter resources cleaned up successfully")

    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        try:
            self.cleanup_resources()
        except:
            pass  # Ignore errors during destruction

    def _should_process_file_for_treesitter(self, file_path: str) -> bool:
        """Apply smart filtering like ignore patterns."""
        # First check if this is a source code file that Tree-sitter can handle
        language_key = self._get_language_key_for_path(file_path)
        if not language_key:
            return False  # Not a supported language

        # Rust-specific optimizations
        if language_key == 'rust':
            # Skip large Rust files if configured
            skip_large_rust_files = getattr(self.config, "rust_specific_optimizations", {}).get("skip_large_rust_files", False)
            if skip_large_rust_files:
                try:
                    file_size_kb = os.path.getsize(file_path) / 1024
                    max_size_kb = getattr(self.config, "rust_specific_optimizations", {}).get("max_rust_file_size_kb", 300)
                    if file_size_kb > max_size_kb:
                        print(f"Note: Skipping large Rust file {file_path} ({file_size_kb:.1f}KB > {max_size_kb}KB)")
                        return False
                except (OSError, IOError):
                    pass

            # Skip generated Rust files if configured
            skip_generated = getattr(self.config, "rust_specific_optimizations", {}).get("skip_generated_rust_files", True)
            if skip_generated:
                rust_target_dirs = getattr(self.config, "rust_specific_optimizations", {}).get("rust_target_directories", ["target/", "build/", "dist/"])
                if any(target_dir in file_path for target_dir in rust_target_dirs):
                    return False

        skip_test_files = getattr(self.config, "tree_sitter_skip_test_files", True)
        if skip_test_files:
            test_patterns = ['test', 'spec', '_test', 'tests']
            filename = os.path.basename(file_path).lower()
            # Only skip if the filename contains test patterns in a way that suggests it's a test file
            # but don't skip files that just have "test" as part of their normal name
            if any(
                filename == pattern or  # exact match
                filename.startswith(f"{pattern}_") or  # test_something.py
                filename.endswith(f"_{pattern}") or  # something_test.py
                f"_{pattern}_" in filename or  # something_test_something.py
                filename.endswith(f".{pattern}")  # something.test.py
                for pattern in test_patterns
            ):
                return False

        skip_examples = getattr(self.config, "tree_sitter_skip_examples", True)
        if skip_examples:
            example_patterns = ['example', 'sample', 'demo']
            filename = os.path.basename(file_path).lower()
            # Only skip if the entire filename suggests it's an example file
            if any(filename.startswith(pattern) or filename.endswith(pattern) or f"_{pattern}" in filename for pattern in example_patterns):
                return False

        skip_patterns = getattr(self.config, "tree_sitter_skip_patterns", [])
        for pattern in skip_patterns:
            if pattern in file_path or file_path.endswith(pattern.lstrip('*')):
                return False

        generated_dirs = ['target/', 'build/', 'dist/', 'node_modules/', '__pycache__/']
        if any(gen_dir in file_path for gen_dir in generated_dirs):
            return False

        return True

    def _extract_semantic_blocks_efficient(
        self, root_node, text: str, file_path: str, file_hash: str, language_key: str
    ) -> List[CodeBlock]:
        """Efficiently extract semantic blocks using Tree-sitter Query API with robust fallbacks."""
        blocks: List[CodeBlock] = []

        try:
            from tree_sitter import Query

            # Ensure we have modern Tree-sitter features
            self._ensure_tree_sitter_version()

            queries = self._get_queries_for_language(language_key)
            if not queries:
                self._debug(f"No query for lang={language_key}; using limited extraction for {file_path}")
                return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)

            # Get cached query or compile new one
            query = self._get_cached_query(language_key, queries)
            if not query:
                self._debug(f"Query compile failed for lang={language_key}; using limited extraction for {file_path}")
                return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)

            # Execute query using robust, multi-API compatibility path
            self._debug(f"Running query path for {file_path} (lang={language_key})")
            capture_results = None
            primary_error = None
            tried_any = False

            # 1) Preferred: Query.captures(root_node)
            try:
                tried_any = True
                capture_results = query.captures(root_node)  # typical API: List[Tuple[Node, str]]
                self._debug(f"Used Query.captures: {len(capture_results or [])} captures")
            except Exception as e_primary:
                primary_error = e_primary

            # 2) Fallback: Query.matches(root_node) -> reconstruct captures
            if capture_results is None:
                try:
                    tried_any = True
                    matches = query.matches(root_node)  # type: ignore[attr-defined]
                    tmp = []
                    for m in matches:
                        captures = getattr(m, "captures", [])
                        if captures:
                            for cap in captures:
                                if isinstance(cap, tuple) and len(cap) == 2:
                                    node, name = cap
                                    tmp.append((node, name))
                                else:
                                    node = getattr(cap, "node", None)
                                    idx = getattr(cap, "index", None)
                                    if node is not None and idx is not None:
                                        try:
                                            name = query.capture_names[idx]  # type: ignore[index]
                                        except Exception:
                                            name = str(idx)
                                        tmp.append((node, name))
                    self._debug(f"Used Query.matches: {len(tmp)} captures")
                    capture_results = tmp
                except Exception:
                    capture_results = None  # continue to next fallback

            # 3) QueryCursor compatibility variants
            if capture_results is None:
                try:
                    from tree_sitter import QueryCursor  # type: ignore
                except Exception:
                    QueryCursor = None  # type: ignore

                if QueryCursor is not None:
                    tmp_list_total = []

                    # 3a) Newer signature: cursor = QueryCursor(); cursor.exec(query, node); cursor.captures()
                    try:
                        cursor = QueryCursor()  # type: ignore[call-arg]
                        try:
                            tried_any = True
                            cursor.exec(query, root_node)  # type: ignore[attr-defined]
                            tmp_list = []
                            for cap in cursor.captures():  # type: ignore[attr-defined]
                                try:
                                    if isinstance(cap, (tuple, list)):
                                        if len(cap) >= 3:
                                            node, cap_idx = cap[0], cap[1]
                                        elif len(cap) >= 2:
                                            node, cap_idx = cap[0], cap[1]
                                        else:
                                            node = None
                                            cap_idx = None
                                    else:
                                        node = getattr(cap, "node", None)
                                        cap_idx = getattr(cap, "index", None)
                                    if node is not None and cap_idx is not None:
                                        try:
                                            name = self._get_capture_name(query, cap_idx, node)  # type: ignore[index]
                                        except Exception:
                                            name = str(cap_idx)
                                        tmp_list.append((node, name))
                                except Exception:
                                    continue
                            self._debug(f"QueryCursor.exec+captures produced {len(tmp_list)} captures")
                            tmp_list_total.extend(tmp_list)
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # 3b) Older signature: cursor.captures(node, query)
                    try:
                        cursor = QueryCursor()  # type: ignore[call-arg]
                        tried_any = True
                        items = cursor.captures(root_node, query)  # type: ignore[call-arg]
                        tmp_list = []
                        for cap in items:
                            try:
                                if isinstance(cap, (tuple, list)):
                                    if len(cap) >= 2:
                                        node, cap_idx = cap[0], cap[1]
                                    else:
                                        node = None
                                        cap_idx = None
                                else:
                                    node = getattr(cap, "node", None)
                                    cap_idx = getattr(cap, "index", None)
                                if node is not None and cap_idx is not None:
                                    try:
                                        name = self._get_capture_name(query, cap_idx, node)  # type: ignore[index]
                                    except Exception:
                                        name = str(cap_idx)
                                    tmp_list.append((node, name))
                            except Exception:
                                continue
                        self._debug(f"QueryCursor.captures(node,query) produced {len(tmp_list)} captures")
                        tmp_list_total.extend(tmp_list)
                    except Exception:
                        pass

                    # 3c) Constructor variant: QueryCursor(query, node)
                    if not tmp_list_total:
                        try:
                            tried_any = True
                            tried_any = True
                            cursor = QueryCursor(query, root_node)  # type: ignore[call-arg]
                            tmp_list = []
                            # Some bindings iterate directly yielding (node, cap_idx, match)
                            for cap in cursor:  # type: ignore[operator]
                                try:
                                    if isinstance(cap, (tuple, list)):
                                        if len(cap) >= 3:
                                            node, cap_idx = cap[0], cap[1]
                                        elif len(cap) >= 2:
                                            node, cap_idx = cap[0], cap[1]
                                        else:
                                            node = None
                                            cap_idx = None
                                    else:
                                        node = getattr(cap, "node", None)
                                        cap_idx = getattr(cap, "index", None)
                                    if node is not None and cap_idx is not None:
                                        try:
                                            name = self._get_capture_name(query, cap_idx, node)  # type: ignore[index]
                                        except Exception:
                                            # Fall back to node.type if capture_names not available
                                            name = getattr(node, "type", str(cap_idx))
                                        tmp_list.append((node, name))
                                except Exception:
                                    continue
                            self._debug(f"QueryCursor(iterator) produced {len(tmp_list)} captures")
                            tmp_list_total.extend(tmp_list)
                        except Exception:
                            pass

                    # 3d) Constructor requires query only: QueryCursor(query); then call captures(node) / matches(node)
                    if not tmp_list_total:
                        try:
                            cursor = QueryCursor(query)  # type: ignore[call-arg]
                            tried_any = True
                            tmp_list = []
                            # Try captures(node)
                            try:
                                items = cursor.captures(root_node)  # type: ignore[attr-defined]
                                # Some bindings return a dict {capture_name: [nodes...]}; handle that first
                                if hasattr(items, "items"):
                                    try:
                                        for cap_name, nodes in items.items():  # type: ignore[attr-defined]
                                            for node in (nodes or []):
                                                tmp_list.append((node, cap_name))
                                    except Exception:
                                        pass
                                else:
                                    for cap in items if isinstance(items, (list, tuple)) else items:  # handle iterators
                                        try:
                                            if isinstance(cap, (tuple, list)):
                                                if len(cap) >= 2:
                                                    node, cap_idx = cap[0], cap[1]
                                                else:
                                                    node = None
                                                    cap_idx = None
                                            else:
                                                node = getattr(cap, "node", None)
                                                cap_idx = getattr(cap, "index", None)
                                            if node is not None and cap_idx is not None:
                                                try:
                                                    name = self._get_capture_name(query, cap_idx, node)  # type: ignore[index]
                                                except Exception:
                                                    name = getattr(node, "type", str(cap_idx))
                                                tmp_list.append((node, name))
                                        except Exception:
                                            continue
                                if tmp_list:
                                    self._debug(f"QueryCursor(query).captures(node) produced {len(tmp_list)} captures")
                            except Exception:
                                pass

                            # If no captures, try matches(node) and reconstruct captures
                            if not tmp_list:
                                try:
                                    items = cursor.matches(root_node)  # type: ignore[attr-defined]
                                    if hasattr(items, "__iter__"):
                                        for m in items if isinstance(items, (list, tuple)) else items:
                                            # Some bindings yield (something, {capture_name: [nodes...]})
                                            try:
                                                if isinstance(m, (tuple, list)) and len(m) >= 2 and hasattr(m[1], "items"):
                                                    capmap = m[1]
                                                    for cap_name, nodes in capmap.items():
                                                        for node in (nodes or []):
                                                            tmp_list.append((node, cap_name))
                                                    continue
                                            except Exception:
                                                pass
                                            # Generic capture reconstruction path
                                            captures = getattr(m, "captures", [])
                                            if captures:
                                                for cap in captures:
                                                    try:
                                                        if isinstance(cap, (tuple, list)):
                                                            if len(cap) >= 2:
                                                                node, cap_idx = cap[0], cap[1]
                                                            else:
                                                                node = None
                                                                cap_idx = None
                                                        else:
                                                            node = getattr(cap, "node", None)
                                                            cap_idx = getattr(cap, "index", None)
                                                        if node is not None and cap_idx is not None:
                                                            try:
                                                                name = self._get_capture_name(query, cap_idx, node)  # type: ignore[index]
                                                            except Exception:
                                                                name = getattr(node, "type", str(cap_idx))
                                                            tmp_list.append((node, name))
                                                    except Exception:
                                                        continue
                                    if tmp_list:
                                        self._debug(f"QueryCursor(query).matches(node) produced {len(tmp_list)} captures")
                                except Exception:
                                    pass

                            tmp_list_total.extend(tmp_list)
                        except Exception:
                            pass

                    if tmp_list_total:
                        capture_results = tmp_list_total

            # 4) If still no captures, decide whether API was unavailable or executed with zero results
            if capture_results is None:
                if tried_any:
                    self._debug(f"Query executed but produced zero captures for {file_path}; switching to limited extraction")
                    return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)
                else:
                    self._debug(f"No capture API available for {file_path}; using limited extraction")
                    return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)

            processed_nodes = set()
            counters = {}

            self._debug(f"Query captures for {file_path}: {len(capture_results or [])}")
            for node, capture_name in (capture_results or []):
                # Skip duplicate nodes
                node_key = f"{node.start_byte}:{node.end_byte}"
                if node_key in processed_nodes:
                    continue
                processed_nodes.add(node_key)

                # Apply type limits
                type_limit = self._get_limit_for_node_type(capture_name, language_key)
                current_count = counters.get(capture_name, 0)
                if current_count >= type_limit:
                    continue
                counters[capture_name] = current_count + 1

                # Create block from node
                block = self._create_block_from_node(node, text, file_path, file_hash, capture_name)
                if block:
                    blocks.append(block)

            # If no blocks produced by query, fallback to limited extraction instead of returning empty
            if not blocks:
                self._debug(f"Zero blocks from query path for {file_path}, switching to limited extraction")
                return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)

            return blocks

        except TreeSitterQueryError as e:
            print(f"Warning: Tree-sitter query execution failed: {e}")
            self._debug(f"Query error; using limited extraction for {file_path}")
            return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)
        except Exception as e:
            print(f"Warning: Efficient Tree-sitter extraction failed, falling back to limited extraction: {e}")
            self._debug(f"Efficient extraction error; using limited extraction for {file_path}")
            return self._extract_with_limits(root_node, text, file_path, file_hash, language_key)

    def _get_cached_query(self, language_key: str, query_text: str) -> Optional[Any]:
        """Get cached query or compile and cache new query with compatibility fallbacks."""
        if language_key in self._query_cache:
            return self._query_cache[language_key]

        try:
            from tree_sitter import Query

            language = self._get_tree_sitter_language(language_key)

            # Try modern constructor first
            try:
                query = Query(language, query_text)
                self._debug(f"Compiled TS query using Query(language, text) for lang={language_key}")
            except Exception as e_primary:
                # Fallback to language.query if available on this binding
                try:
                    if hasattr(language, "query"):
                        query = language.query(query_text)  # type: ignore[attr-defined]
                        self._debug(f"Compiled TS query using language.query(text) for lang={language_key}")
                    else:
                        raise e_primary
                except Exception as e_fallback:
                    raise e_fallback

            # Debug: check Language object identity between parser and query for this language
            parser_lang_id = getattr(self, "_parser_language_ids", {}).get(language_key)
            lang_id = id(language)
            if parser_lang_id and parser_lang_id != lang_id:
                self._debug(f"Language identity mismatch for {language_key}: parser_lang_id={parser_lang_id} query_lang_id={lang_id}")

            self._query_cache[language_key] = query
            return query
        except Exception as e:
            print(f"Warning: Failed to compile Tree-sitter query for {language_key}: {e}")
            return None

    def _get_queries_for_language(self, language_key: str) -> Optional[str]:
        """Get Tree-sitter queries for a specific language."""
        return get_ts_queries(language_key)

    def _get_limit_for_node_type(self, node_type: str, language_key: str) -> int:
        """Get extraction limits for specific node types."""
        limits = {
            'function': getattr(self.config, "tree_sitter_max_functions_per_file", 50),
            'method': getattr(self.config, "tree_sitter_max_functions_per_file", 50),
            'class': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'struct': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'enum': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'interface': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'trait': getattr(self.config, "tree_sitter_max_classes_per_file", 20),
            'impl': getattr(self.config, "tree_sitter_max_impl_blocks_per_file", 30),
        }
        return limits.get(node_type, 20)

    def _get_capture_name(self, query: Any, cap_idx: int, node: Any) -> str:
        """Resolve a capture name across py-tree-sitter API variants.

        Resolution order:
        1) Query.capture_name(index) when available (py-tree-sitter >= 0.25.0)
        2) Query.capture_names list when present
        3) node.type as a best-effort fallback
        4) stringified index
        """
        try:
            # Preferred modern API
            if hasattr(query, "capture_name"):
                try:
                    return query.capture_name(cap_idx)  # type: ignore[attr-defined]
                except Exception:
                    pass
            # Legacy/common API
            names = getattr(query, "capture_names", None)
            if names:
                try:
                    return names[cap_idx]
                except Exception:
                    pass
        except Exception:
            # Ignore and use fallbacks
            pass

        # Final fallbacks
        try:
            return getattr(node, "type", str(cap_idx))
        except Exception:
            return str(cap_idx)

    def _extract_with_limits(
        self, root_node, text: str, file_path: str, file_hash: str, language_key: str
    ) -> List[CodeBlock]:
        """Extract blocks with limits when queries aren't available."""
        blocks: List[CodeBlock] = []
        self._debug(f"Limited extraction path for {file_path} (lang={language_key})")

        node_types = self._get_node_types_for_language(language_key)

        max_total_blocks = min(getattr(self.config, "tree_sitter_max_blocks_per_file", 100), 50)

        def traverse_node(node, depth=0):
            if depth > 7:
                return

            # Special handling for JS/TS/TSX to capture function-like initializers and callback args
            if language_key in ('javascript', 'typescript', 'tsx') and len(blocks) < max_total_blocks:
                try:
                    # Variable declarations with function/arrow initializers:
                    # const fn = () => {}; const fn = function() {};
                    if node.type in ('variable_declaration', 'lexical_declaration', 'variable_statement'):
                        for child in node.children:
                            if child.type == 'variable_declarator':
                                init = getattr(child, "child_by_field_name", lambda *_: None)('value') or \
                                       getattr(child, "child_by_field_name", lambda *_: None)('initializer')
                                if init is not None and init.type in ('arrow_function', 'function_expression'):
                                    blk = self._create_block_from_node(init, text, file_path, file_hash, init.type)
                                    if blk:
                                        blocks.append(blk)
                                        if len(blocks) >= max_total_blocks:
                                            return

                    # Callback functions passed to calls:
                    # app.get('/x', (req,res)=>{}), arr.map(x => x*x)
                    if node.type == 'call_expression':
                        args = getattr(node, "child_by_field_name", lambda *_: None)('arguments')
                        arg_nodes = []
                        if args is not None:
                            arg_nodes = list(getattr(args, 'children', []))
                        else:
                            # Fallback: scan direct children if 'arguments' field isn't available
                            arg_nodes = [c for c in getattr(node, 'children', []) if getattr(c, 'type', '') in ('arrow_function', 'function_expression')]
                        for arg in arg_nodes:
                            target = arg
                            if getattr(target, 'type', None) in ('arrow_function', 'function_expression'):
                                blk = self._create_block_from_node(target, text, file_path, file_hash, target.type)
                                if blk:
                                    blocks.append(blk)
                                    if len(blocks) >= max_total_blocks:
                                        return
                except Exception:
                    # Best-effort special handling; ignore failures and continue generic traversal
                    pass

            # Generic node-type-based extraction
            if node.type in node_types and len(blocks) < max_total_blocks:
                content = text[node.start_byte : node.end_byte]
                if len(content.strip()) >= self.min_block_chars:
                    identifier = f"{node.type}:{node.start_point[0] + 1}"
                    segment_hash = file_hash + f"{node.start_point[0] + 1}"
                    block = CodeBlock(
                        file_path=file_path,
                        identifier=identifier,
                        type=node.type,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        content=content,
                        file_hash=file_hash,
                        segment_hash=segment_hash,
                    )
                    blocks.append(block)

            if len(blocks) < max_total_blocks:
                for child in node.children:
                    traverse_node(child, depth + 1)

        traverse_node(root_node)
        # Deduplicate blocks by (start_line, end_line, type, identifier)
        seen = set()
        deduped = []
        for b in blocks:
            key = (b.start_line, b.end_line, b.type, b.identifier)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(b)
        if len(deduped) != len(blocks):
            self._debug(f"Limited extraction deduplicated {len(blocks) - len(deduped)} duplicate blocks for {file_path}")
        self._debug(f"Limited extraction produced {len(deduped[:max_total_blocks])} blocks for {file_path}")
        return deduped[:max_total_blocks]

    def _create_block_from_node(
        self, node, text: str, file_path: str, file_hash: str, node_type: str
    ) -> Optional[CodeBlock]:
        """Create a CodeBlock from a Tree-sitter node."""
        try:
            content = text[node.start_byte : node.end_byte]

            min_chars = getattr(self.config, "tree_sitter_min_block_chars", self.min_block_chars)
            if len(content.strip()) < (min_chars or self.min_block_chars):
                return None

            identifier = f"{node_type}:{node.start_point[0] + 1}"

            segment_hash = file_hash + f"{node.start_point[0] + 1}"

            return CodeBlock(
                file_path=file_path,
                identifier=identifier,
                type=node_type,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=content,
                file_hash=file_hash,
                segment_hash=segment_hash,
            )
        except Exception:
            return None

    def _get_node_types_for_language(self, language_key: str) -> List[str]:
        """Get node types to extract for a specific language."""
        language_node_types = {
            'python': ['function_definition', 'class_definition', 'module'],
            'javascript': ['function_declaration', 'method_definition', 'class_declaration', 'arrow_function'],
            'typescript': [
                'function_declaration',
                'arrow_function',
                'method_definition',
                'method_signature',
                'class_declaration',
                'interface_declaration',
                'function_signature',
                'type_alias_declaration',
            ],
            'tsx': [
                'function_declaration',
                'method_definition',
                'class_declaration',
                'interface_declaration',
                'type_alias_declaration',
            ],
            'go': ['function_declaration', 'method_declaration', 'type_declaration'],
            'java': ['class_declaration', 'method_declaration', 'interface_declaration'],
            'cpp': ['function_definition', 'class_specifier', 'struct_specifier'],
            'c': ['function_definition'],
            'rust': ['function_item', 'impl_item', 'struct_item', 'enum_item', 'trait_item'],
            'csharp': ['class_declaration', 'method_declaration', 'interface_declaration'],
            'ruby': ['method', 'class', 'module'],
            'php': ['function_definition', 'class_declaration'],
            'kotlin': ['class_declaration', 'function_declaration'],
            'swift': ['function_declaration', 'class_declaration'],
            'lua': ['function_declaration'],
            'json': ['pair'],
            'yaml': ['block_mapping_pair'],
            'markdown': ['atx_heading', 'setext_heading'],
            'html': ['element'],
            'css': ['rule_set'],
            'scss': ['rule_set'],
            'sql': ['statement', 'select_statement', 'insert_statement', 'update_statement', 'delete_statement'],
            # New language node types
            'bash': ['function_definition', 'command'],
            'dart': ['function_declaration', 'method_declaration', 'class_declaration'],
            'scala': ['function_definition', 'class_definition', 'object_definition'],
            'perl': ['subroutine_definition', 'package_statement'],
            'haskell': ['function', 'data_declaration', 'type_declaration'],
            'elixir': ['function_declaration', 'module_declaration'],
            'clojure': ['defn', 'def'],
            'erlang': ['function', 'module'],
            'ocaml': ['let_binding', 'module_definition'],
            'fsharp': ['let_binding', 'type_definition'],
            'vb': ['sub_declaration', 'function_declaration', 'class_declaration'],
            'r': ['function_definition', 'assignment'],
            'matlab': ['function_definition', 'class_definition'],
            'julia': ['function_definition', 'module_definition'],
            'groovy': ['method_declaration', 'class_declaration'],
            'dockerfile': ['from_instruction', 'run_instruction', 'cmd_instruction'],
            'makefile': ['rule', 'variable_assignment'],
            'cmake': ['function_call', 'macro_call'],
            'protobuf': ['message_declaration', 'service_declaration', 'rpc_declaration'],
            'graphql': ['type_definition', 'field_definition'],
            # Additional language node types
            'vue': ['component', 'template_element', 'script_element', 'style_element'],
            'svelte': ['document', 'element', 'script_element', 'style_element'],
            'astro': ['document', 'frontmatter', 'element', 'style_element'],
            'tsx': ['function_declaration', 'method_definition', 'class_declaration', 'interface_declaration', 'type_alias_declaration', 'jsx_element', 'jsx_self_closing_element'],
            'elm': ['value_declaration', 'type_declaration', 'type_alias_declaration'],
            'toml': ['table', 'table_array_element', 'pair'],
            'xml': ['element', 'script_element', 'style_element'],
            'ini': ['section', 'property'],
            'csv': ['record', 'field'],
            'tsv': ['record', 'field'],
            'terraform': ['block', 'attribute', 'object'],
            'solidity': ['contract_declaration', 'function_definition', 'modifier_definition', 'event_definition'],
            'verilog': ['module_declaration', 'function_declaration', 'task_declaration'],
            'vhdl': ['entity_declaration', 'architecture_body', 'function_specification'],
            'swift': ['class_declaration', 'function_declaration', 'enum_declaration', 'struct_declaration'],
            'zig': ['function_declaration', 'struct_declaration', 'enum_declaration'],
            'v': ['function_declaration', 'struct_declaration', 'enum_declaration'],
            'nim': ['function_declaration', 'type_declaration', 'variable_declaration'],
            'tcl': ['procedure_definition', 'command'],
            'scheme': ['function_definition', 'lambda_expression'],
            'commonlisp': ['defun', 'defvar', 'defclass'],
            'racket': ['function_definition', 'lambda_expression'],
            'clojurescript': ['defn', 'def'],
            'fish': ['function_definition', 'command'],
            'powershell': ['function_definition', 'command'],
            'zsh': ['function_definition', 'command'],
            'rst': ['section', 'directive', 'field'],
            'org': ['section', 'headline', 'block'],
            'latex': ['chapter', 'section', 'subsection', 'subsubsection'],
            'tex': ['chapter', 'section', 'subsection', 'subsubsection'],
            'sqlite': ['statement', 'select_statement', 'insert_statement', 'update_statement', 'delete_statement'],
            'mysql': ['statement', 'select_statement', 'insert_statement', 'update_statement', 'delete_statement'],
            'postgresql': ['statement', 'select_statement', 'insert_statement', 'update_statement', 'delete_statement'],
            'hcl': ['block', 'attribute', 'object'],
            'puppet': ['definition', 'class_definition', 'node_definition'],
            'thrift': ['struct', 'service', 'function'],
            'proto': ['message', 'service', 'rpc'],
            'capnp': ['struct', 'interface', 'method'],
            'smithy': ['shape_statement', 'service_statement', 'operation_statement'],
        }
        return language_node_types.get(language_key, ['function_definition', 'class_definition'])

    def _ensure_tree_sitter_version(self) -> None:
        """Ensure Tree-sitter Python bindings provide at least one usable query API."""
        try:
            from tree_sitter import Query  # type: ignore
            has_captures = hasattr(Query, "captures")
            has_matches = hasattr(Query, "matches")
            has_cursor = False
            try:
                # Older/newer bindings may provide QueryCursor; we won't rely on it here,
                # but its presence indicates usable bindings.
                from tree_sitter import QueryCursor  # type: ignore
                has_cursor = True
            except Exception:
                has_cursor = False

            if not (has_captures or has_matches or has_cursor):
                raise TreeSitterError(
                    "Tree-sitter bindings do not expose Query.captures, Query.matches, or QueryCursor"
                )
        except ImportError:
            raise TreeSitterError("Tree-sitter package not installed")
        except Exception as e:
            raise TreeSitterError(f"Tree-sitter version check failed: {e}")
