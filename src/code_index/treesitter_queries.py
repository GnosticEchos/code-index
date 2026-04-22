"""
Tree-sitter queries for various programming languages.
"""

from typing import Dict, Optional


def get_queries_for_language(language_key: str) -> Optional[str]:
    """Get Tree-sitter queries for a specific language."""
    queries: Dict[str, str] = {
        'ansible': '''
            (block_mapping_pair) @pair
            (block_sequence_item) @item
        ''',
        'astro': '''
            (document) @document
            (frontmatter) @frontmatter
            (element) @element
            (style_element) @style
        ''',
        'awk': '''
            (function_definition) @function
            (pattern) @pattern
        ''',
        'bash': '''
            (function_definition name: (word) @name) @function
            (command name: (command_name (word)) @name) @command
        ''',
        'bazel': '''
            (function_definition) @function
            (rule_definition) @rule
        ''',
        'c': '''
            (function_definition declarator: (identifier) @name) @function
            (struct_specifier name: (type_identifier) @name) @struct
        ''',
        'capnp': '''
            (struct) @struct
            (interface) @interface
            (method) @method
        ''',
        'clojure': '''
            (list_lit (sym_lit (sym_name) @ns_def) (#eq? @ns_def "ns")) @namespace
            (list_lit (sym_lit (sym_name) @defn_def) (#eq? @defn_def "defn")) @function
            (list_lit (sym_lit (sym_name) @def_def) (#eq? @def_def "def")) @definition
        ''',
        'clojurescript': '''
            (list_lit (sym_lit (sym_name) @ns_def) (#eq? @ns_def "ns")) @namespace
            (list_lit (sym_lit (sym_name) @defn_def) (#eq? @defn_def "defn")) @function
            (list_lit (sym_lit (sym_name) @def_def) (#eq? @def_def "def")) @definition
        ''',
        'cmake': '''
            (function_def) @function
            (macro_def) @macro
            (normal_command) @command
        ''',
        'commonlisp': None,
        'cpp': '''
            (class_specifier name: (type_identifier) @name) @class
            (struct_specifier name: (type_identifier) @name) @struct
            (function_definition declarator: (identifier) @name) @function
        ''',
        'csharp': '''
            (class_declaration name: (identifier) @name) @class
            (method_declaration name: (identifier) @name) @method
            (constructor_declaration name: (identifier) @name) @constructor
            (property_declaration name: (identifier) @name) @property
            (field_declaration name: (identifier) @name) @field
            (interface_declaration name: (identifier) @name) @interface
            (struct_declaration name: (identifier) @name) @struct
            (enum_declaration name: (identifier) @name) @enum
            (namespace_declaration name: (identifier) @name) @namespace
        ''',
        'css': '''
            (rule_set) @rule
            (media_statement) @media
            (keyframes_statement) @keyframes
        ''',
        'csv': None,
        'dart': '''
            (class_definition) @class
            (function_signature) @function
            (method_signature) @method
            (getter_signature) @getter
            (setter_signature) @setter
        ''',
        'dockerfile': '''
            (from_instruction) @from
            (run_instruction) @run
            (cmd_instruction) @cmd
            (copy_instruction) @copy
            (env_instruction) @env
        ''',
        'elixir': '''
            (call (identifier) @module_def (#eq? @module_def "defmodule")) @module
            (call (identifier) @function_def (#eq? @function_def "def")) @function
            (call (identifier) @private_function_def (#eq? @private_function_def "defp")) @function
        ''',
        'elm': '''
            (value_declaration) @function
            (type_declaration) @type
            (type_alias_declaration) @type_alias
        ''',
        'elm_function': '''
            (function_declaration_left) @function
        ''',
        'embeddedtemplate': '''
            (comment_directive) @comment
            (content) @content
            (code) @code
        ''',
        'erlang': '''
            (module_attribute) @module
            (fun_decl (function_clause (atom) @function_name)) @function
        ''',
        'fennel': '''
            (function_definition) @function
            (let_expression) @let
        ''',
        'fish': '''
            (function_definition) @function
            (command) @command
        ''',
        'fsharp': None,
        'go': '''
            (function_declaration name: (identifier) @name) @function
            (method_declaration name: (field_identifier) @name) @method
            (type_declaration) @type
        ''',
        'graphql': '''
            (type_definition) @type
            (field_definition) @field
            (operation_definition) @operation
        ''',
        'groovy': None,
        'haskell': '''
            (function) @function
            (function_declaration) @function
            (header) @module
            (module) @module
            (signature) @signature
            (type_declaration) @type
        ''',
        'hcl': '''
            (block) @block
            (attribute) @attribute
            (object) @object
        ''',
        'heex': '''
            (element) @element
            (component) @component
        ''',
        'html': '''
            (element) @element
            (script_element) @script
            (style_element) @style
        ''',
        'ini': None,
        'janet': '''
            (def) @def
            (var) @var
            (fn) @function
        ''',
        'java': '''
            (class_declaration name: (identifier) @name) @class
            (method_declaration name: (identifier) @name) @method
            (constructor_declaration name: (identifier) @name) @constructor
        ''',
        'javascript': '''
            (function_declaration name: (identifier) @name) @function
            (method_definition name: (property_identifier) @name) @method
            (class_declaration name: (identifier) @name) @class
            (arrow_function) @function
        ''',
        'jq': '''
            (function_definition) @function
            (query) @query
        ''',
        'json': '''
            (object) @object
            (array) @array
            (pair) @pair
        ''',
        'jsonnet': '''
            (function) @function
            (local_bind) @local_bind
            (object) @object
        ''',
        'julia': '''
            (function_definition name: (identifier) @name) @function
            (module_definition name: (identifier) @name) @module
            (struct_definition) @struct
        ''',
        'kotlin': '''
            (class_declaration) @class
            (function_declaration) @function
            (property_declaration) @property
        ''',
        'latex': '''
            (chapter) @chapter
            (section) @section
            (subsection) @subsection
            (subsubsection) @subsubsection
        ''',
        'less': '''
            (rule_set) @rule
            (mixin_definition) @mixin
            (function_definition) @function
        ''',
        'lua': '''
            (function_declaration) @function
            (table_constructor) @table
        ''',
        'make': '''
            (rule) @rule
            (variable_assignment) @variable
        ''',
        'makefile': None,
        'markdown': '''
            (atx_heading) @heading
            (setext_heading) @heading
            (fenced_code_block) @code_block
            (html_block) @html_block
        ''',
        'matlab': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
        ''',
        'meson': '''
            (function_definition) @function
            (method_call) @method
        ''',
        'mysql': None,
        'nim': None,
        'ninja': '''
            (rule) @rule
            (build) @build
            (variable) @variable
        ''',
        'objc': '''
            (class_interface) @class
            (class_implementation) @class
            (method_definition) @method
        ''',
        'objcpp': '''
            (class_specifier name: (type_identifier) @name) @class
            (struct_specifier name: (type_identifier) @name) @struct
            (function_definition declarator: (identifier) @name) @function
        ''',
        'ocaml': '''
            (module_definition) @module
            (type_definition) @type
            (value_definition (let_binding (value_name) @function_name)) @function
            (value_definition) @value
        ''',
        'ocaml_interface': '''
            (module_definition) @module
            (value_definition) @value
            (type_definition) @type
        ''',
        'org': '''
            (section) @section
            (headline) @headline
            (block) @block
        ''',
        'perl': '''
            (package_statement) @package
            (subroutine_declaration_statement) @subroutine
        ''',
        'php': '''
            (class_declaration name: (name) @name) @class
            (function_definition name: (name) @name) @function
            (method_declaration name: (name) @name) @method
        ''',
        'postgresql': None,
        'powershell': None,
        'prisma': '''
            (model_declaration) @model
            (enum_declaration) @enum
            (field_declaration) @field
        ''',
        'proto': '''
            (message) @message
            (service) @service
            (rpc) @rpc
        ''',
        'protobuf': None,
        'puppet': None,
        'python': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
            (module) @module
        ''',
        'r': '''
            (function_definition) @function
            (call function: (identifier) @function_call)
        ''',
        'racket': None,
        'rego': '''
            (package) @package
            (rule) @rule
            (function) @function
        ''',
        'rst': '''
            (section) @section
            (directive) @directive
            (field) @field
        ''',
        'ruby': '''
            (class name: (constant) @name) @class
            (method name: (identifier) @name) @method
            (singleton_method name: (identifier) @name) @method
        ''',
        'rust': '''
            (function_item name: (identifier) @name) @function
            (struct_item name: (type_identifier) @name) @struct
            (enum_item name: (type_identifier) @name) @enum
            (trait_item name: (type_identifier) @name) @trait
            (impl_item) @impl
        ''',
        'sass': '''
            (rule_set) @rule
            (mixin) @mixin
            (function) @function
        ''',
        'scala': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
            (object_definition name: (identifier) @name) @object
            (trait_definition name: (identifier) @name) @trait
        ''',
        'scheme': None,
        'scss': '''
            (rule_set) @rule
            (media_statement) @media
            (keyframes_statement) @keyframes
            (mixin_statement) @mixin
            (function_statement) @function
        ''',
        'sed': '''
            (command) @command
        ''',
        'smithy': '''
            (shape_statement) @shape
            (service_statement) @service
            (operation_statement) @operation
        ''',
        'solidity': '''
            (contract_declaration) @contract
            (function_definition) @function
            (modifier_definition) @modifier
            (event_definition) @event
        ''',
        'sparql': '''
            (select_query) @select
            (ask_query) @ask
            (construct_query) @construct
            (describe_query) @describe
        ''',
        'sql': '''
            (statement (select)) @select
            (statement (insert)) @insert
            (statement (update)) @update
            (statement (delete)) @delete
            (create_table) @create_table
            (drop_table) @drop_table
            (alter_table) @alter_table
        ''',
        'sqlite': None,
        'svelte': '''
            (document) @document
            (element) @element
            (script_element) @script
            (style_element) @style
        ''',
        'swift': '''
            (class_declaration name: (type_identifier) @name) @class
            (function_declaration name: (simple_identifier) @name) @function
        ''',
        'systemverilog': '''
            (module_declaration) @module
            (function_declaration) @function
            (task_declaration) @task
        ''',
        'tcl': None,
        'terraform': '''
            (block) @block
            (attribute) @attribute
            (object) @object
        ''',
        'tex': '''
            (chapter) @chapter
            (section) @section
            (subsection) @subsection
            (subsubsection) @subsubsection
        ''',
        'thrift': None,
        'toml': '''
            (table) @table
            (table_array_element) @table_array
            (pair) @pair
        ''',
        'tsv': None,
        'tsx': '''
            ; Core declarations
            (function_declaration) @function
            (method_definition) @method
            (class_declaration) @class
            (interface_declaration) @interface
            (type_alias_declaration) @type

            ; Function-like expressions
            (arrow_function) @function
            (function_expression) @function

            ; Variable initializer patterns
            (lexical_declaration
              (variable_declarator
                name: (identifier) @name
                value: (arrow_function))) @function

            (lexical_declaration
              (variable_declarator
                name: (identifier) @name
                value: (function_expression))) @function

            ; JSX
            (jsx_element) @jsx_element
            (jsx_self_closing_element) @jsx_element
        ''',
        'typescript': '''
            ; Core declarations
            (function_declaration) @function
            (method_definition) @method
            (class_declaration) @class
            (interface_declaration) @interface
            (type_alias_declaration) @type

            ; Function-like expressions frequently used in TS codebases
            (arrow_function) @function
            (function_expression) @function

            ; Common variable initializer patterns for function-like constructs
            (lexical_declaration
              (variable_declarator
                name: (identifier) @name
                value: (arrow_function))) @function

            (lexical_declaration
              (variable_declarator
                name: (identifier) @name
                value: (function_expression))) @function
        ''',
        'v': None,
        'vb': None,
        'verilog': '''
            (module_declaration) @module
            (function_declaration) @function
            (task_declaration) @task
        ''',
        'vhdl': None,
        'vue': '''
            (component) @component
            (template_element) @template
            (script_element) @script
            (element) @element
        ''',
        'vyper': '''
            (function_definition) @function
            (event_definition) @event
            (struct_definition) @struct
        ''',
        'xml': None,
        'yaml': '''
            (block_mapping_pair) @pair
            (block_sequence_item) @item
            (block_scalar) @scalar
        ''',
        'zig': None,
        'zsh': None,
    }
    return queries.get(language_key)
def validate_queries_for_language(language_key: str) -> dict:
    """Validate tree-sitter queries for a specific language."""
    try:
        queries = get_queries_for_language(language_key)
        
        if not queries:
            return {
                "language_key": language_key,
                "valid": False,
                "reason": "No queries available for language",
                "query_count": 0,
                "syntax_check": False
            }
        
        # Basic syntax validation
        syntax_valid = True
        syntax_errors = []
        
        # Check for basic syntax issues
        if not isinstance(queries, str):
            syntax_valid = False
            syntax_errors.append("Queries must be a string")
        elif len(queries.strip()) == 0:
            syntax_valid = False
            syntax_errors.append("Queries cannot be empty")
        else:
            # Check for unbalanced parentheses/brackets
            parens = queries.count("(") - queries.count(")")
            brackets = queries.count("[") - queries.count("]")
            braces = queries.count("{") - queries.count("}")
            
            if parens != 0:
                syntax_valid = False
                syntax_errors.append(f"Unbalanced parentheses: {parens}")
            if brackets != 0:
                syntax_valid = False
                syntax_errors.append(f"Unbalanced brackets: {brackets}")
            if braces != 0:
                syntax_valid = False
                syntax_errors.append(f"Unbalanced braces: {braces}")
            
            # Check for common syntax issues
            if "@" in queries and not any(f"@{token}" in queries for token in ["function", "class", "method", "variable", "identifier"]):
                syntax_errors.append("Queries contain @ symbols but no valid capture names")
            
        # Count query patterns (rough estimate)
        pattern_count = queries.count("@")
        
        return {
            "language_key": language_key,
            "valid": syntax_valid,
            "reason": "; ".join(syntax_errors) if syntax_errors else "Valid",
            "query_count": pattern_count,
            "syntax_check": syntax_valid,
            "query_length": len(queries),
            "has_captures": "@" in queries,
            "estimated_complexity": "high" if pattern_count > 5 else "medium" if pattern_count > 2 else "low"
        }
        
    except Exception as e:
        return {
            "language_key": language_key,
            "valid": False,
            "reason": f"Validation error: {str(e)}",
            "query_count": 0,
            "syntax_check": False
        }

def validate_all_queries() -> dict:
    """Validate queries for all supported languages."""
    # Get all language keys from the queries dict
    
    # Extract language keys from the queries dictionary
    # This is a bit hacky but works with the current structure
    import inspect
    source = inspect.getsource(get_queries_for_language)
    
    # Parse the dictionary keys from the source
    languages = []
    in_dict = False
    for line in source.split("\n"):
        line = line.strip()
        if line.startswith("queries: Dict[str, str] = {"):
            in_dict = True
            continue
        elif in_dict and line.startswith("}"):
            break
        elif in_dict and line.strip().startswith('"'):
            # Extract language key
            key = line.split(":")[0].strip().strip('"\'')
            if key:
                languages.append(key)
    
    # Fallback: manually list common languages if parsing fails
    if not languages:
        languages = [
            "python", "javascript", "typescript", "rust", "go", "java", "cpp", "c",
            "csharp", "ruby", "php", "kotlin", "swift", "lua", "dart", "scala",
            "perl", "haskell", "elixir", "clojure", "erlang", "ocaml", "r", "matlab",
            "julia", "groovy", "dockerfile", "makefile", "cmake", "protobuf", "graphql",
            "vue", "svelte", "astro", "elm", "toml", "html", "css", "scss", "sql",
            "bash", "json", "yaml", "markdown", "xml", "ini", "csv", "tsv", "terraform",
            "hcl", "solidity", "verilog", "vhdl", "zig", "v", "nim", "tcl", "scheme",
            "commonlisp", "racket", "clojurescript", "fish", "powershell", "zsh", "rst",
            "org", "latex", "tex", "sqlite", "mysql", "postgresql", "puppet", "thrift",
            "proto", "capnp", "smithy", "fsharp", "vb", "makefile", "protobuf", "groovy"
        ]
    
    results = {}
    valid_count = 0
    total_count = len(languages)
    
    for lang in languages:
        validation = validate_queries_for_language(lang)
        results[lang] = validation
        if validation["valid"]:
            valid_count += 1
    
    summary = {
        "total_languages": total_count,
        "valid_languages": valid_count,
        "invalid_languages": total_count - valid_count,
        "validation_rate": valid_count / total_count if total_count > 0 else 0,
        "results": results
    }
    
    return summary

def test_query_compilation(language_key: str) -> dict:
    """Test if queries for a language can be compiled by tree-sitter."""
    try:
        queries = get_queries_for_language(language_key)
        
        if not queries:
            return {
                "language_key": language_key,
                "compilable": False,
                "reason": "No queries available",
                "compilation_time_ms": 0
            }
        
        # Try to load the language and compile queries
        import time
        start_time = time.time()
        
        try:
            # Try to get language object
            from tree_sitter_language_pack import get_language
            language_obj = get_language(language_key)
            
            if not language_obj:
                return {
                    "language_key": language_key,
                    "compilable": False,
                    "reason": "Language not available in tree_sitter_language_pack",
                    "compilation_time_ms": 0
                }
            
            # Try to compile query
            from tree_sitter import Query
            compiled_query = Query(language_obj, queries)
            
            compilation_time = (time.time() - start_time) * 1000
            
            return {
                "language_key": language_key,
                "compilable": True,
                "reason": "Successfully compiled",
                "compilation_time_ms": compilation_time,
                "query_object": str(type(compiled_query))
            }
            
        except ImportError:
            return {
                "language_key": language_key,
                "compilable": False,
                "reason": "tree_sitter_language_pack not available",
                "compilation_time_ms": 0
            }
        except Exception as e:
            compilation_time = (time.time() - start_time) * 1000
            return {
                "language_key": language_key,
                "compilable": False,
                "reason": f"Compilation failed: {str(e)}",
                "compilation_time_ms": compilation_time
            }
            
    except Exception as e:
        return {
            "language_key": language_key,
            "compilable": False,
            "reason": f"Test setup failed: {str(e)}",
            "compilation_time_ms": 0
        }

def test_all_query_compilations() -> dict:
    """Test query compilation for all supported languages."""
    # Get languages the same way as validate_all_queries
    import inspect
    source = inspect.getsource(get_queries_for_language)
    
    languages = []
    in_dict = False
    for line in source.split("\n"):
        line = line.strip()
        if line.startswith("queries: Dict[str, str] = {"):
            in_dict = True
            continue
        elif in_dict and line.startswith("}"):
            break
        elif in_dict and line.strip().startswith('"'):
            key = line.split(":")[0].strip().strip('"\'')
            if key:
                languages.append(key)
    
    # Fallback languages
    if not languages:
        languages = [
            "python", "javascript", "typescript", "rust", "go", "java", "cpp", "c",
            "csharp", "ruby", "php", "kotlin", "swift", "lua", "dart", "scala"
        ]
    
    results = {}
    compilable_count = 0
    total_count = len(languages)
    total_time = 0
    
    for lang in languages:
        test_result = test_query_compilation(lang)
        results[lang] = test_result
        if test_result["compilable"]:
            compilable_count += 1
        total_time += test_result["compilation_time_ms"]
    
    summary = {
        "total_languages": total_count,
        "compilable_languages": compilable_count,
        "non_compilable_languages": total_count - compilable_count,
        "compilation_rate": compilable_count / total_count if total_count > 0 else 0,
        "total_compilation_time_ms": total_time,
        "average_compilation_time_ms": total_time / total_count if total_count > 0 else 0,
        "results": results
    }
    
    return summary
