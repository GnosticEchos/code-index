"""
Tree-sitter queries for various programming languages.
"""

from typing import Dict, Optional


def get_queries_for_language(language_key: str) -> Optional[str]:
    """Get Tree-sitter queries for a specific language."""
    queries: Dict[str, str] = {
        # Core languages with detailed queries
        'python': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
            (module) @module
        ''',
        'javascript': '''
            (function_declaration name: (identifier) @name) @function
            (method_definition name: (property_identifier) @name) @method
            (class_declaration name: (identifier) @name) @class
            (arrow_function) @function
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
        'rust': '''
            (function_item name: (identifier) @name) @function
            (struct_item name: (type_identifier) @name) @struct
            (enum_item name: (type_identifier) @name) @enum
            (trait_item name: (type_identifier) @name) @trait
            (impl_item) @impl
        ''',
        'go': '''
            (function_declaration name: (identifier) @name) @function
            (method_declaration name: (field_identifier) @name) @method
            (type_declaration) @type
        ''',
        'bash': '''
            (function_definition name: (word) @name) @function
            (command name: (command_name (word)) @name) @command
        ''',
        'scala': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
            (object_definition name: (identifier) @name) @object
        ''',
        'matlab': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
        ''',
        'julia': '''
            (function_definition name: (identifier) @name) @function
            (module_definition name: (identifier) @name) @module
        ''',
        'dockerfile': '''
            (from_instruction) @from
            (run_instruction) @run
            (cmd_instruction) @cmd
        ''',
        'markdown': '''
            (atx_heading) @heading
            (setext_heading) @heading
            (fenced_code_block) @code_block
            (html_block) @html_block
        ''',
        'java': '''
            (class_declaration name: (identifier) @name) @class
            (method_declaration name: (identifier) @name) @method
            (constructor_declaration name: (identifier) @name) @constructor
        ''',
        'cpp': '''
            (class_specifier name: (type_identifier) @name) @class
            (struct_specifier name: (type_identifier) @name) @struct
            (function_definition declarator: (identifier) @name) @function
        ''',
        'c': '''
            (function_definition declarator: (identifier) @name) @function
            (struct_specifier name: (type_identifier) @name) @struct
        ''',
        'csharp': '''
            (class_declaration name: (identifier) @name) @class
            (method_declaration name: (identifier) @name) @method
            (constructor_declaration name: (identifier) @name) @constructor
        ''',
        'ruby': '''
            (class name: (constant) @name) @class
            (method name: (identifier) @name) @method
            (singleton_method name: (identifier) @name) @method
        ''',
        'php': '''
            (class_declaration name: (name) @name) @class
            (function_definition name: (name) @name) @function
            (method_declaration name: (name) @name) @method
        ''',
        'kotlin': '''
            (class_declaration) @class
            (function_declaration) @function
        ''',
        'swift': '''
            (class_declaration name: (type_identifier) @name) @class
            (function_declaration name: (simple_identifier) @name) @function
        ''',
        'lua': '''
            (function_declaration) @function
            (table_constructor) @table
        ''',
        'json': '''
            (object) @object
            (array) @array
            (pair) @pair
        ''',
        'yaml': '''
            (block_mapping_pair) @pair
            (block_sequence_item) @item
            (block_scalar) @scalar
        ''',
        'html': '''
            (element) @element
            (script_element) @script
            (style_element) @style
        ''',
        'css': '''
            (rule_set) @rule
            (media_statement) @media
            (keyframes_statement) @keyframes
        ''',
        'scss': '''
            (rule_set) @rule
            (media_statement) @media
            (keyframes_statement) @keyframes
            (mixin_statement) @mixin
            (function_statement) @function
        ''',
        'sql': '''
            (statement (select)) @select
            (statement (insert)) @insert
            (statement (update)) @update
            (statement (delete)) @delete
        ''',
        'dart': '''
            (class_definition) @class
            (function_signature) @function
            (method_signature) @method
        ''',
        'perl': '''
            (package_statement) @package
            (subroutine_declaration_statement) @subroutine
        ''',
        'haskell': '''
            (module) @module
            (function_declaration) @function
            (type_declaration) @type
        ''',
        'elixir': '''
            (call (identifier) @module_def (#eq? @module_def "defmodule")) @module
            (call (identifier) @function_def (#eq? @function_def "def")) @function
            (call (identifier) @private_function_def (#eq? @private_function_def "defp")) @function
        ''',
        'clojure': '''
            (list_lit (sym_lit (sym_name) @ns_def) (#eq? @ns_def "ns")) @namespace
            (list_lit (sym_lit (sym_name) @defn_def) (#eq? @defn_def "defn")) @function
        ''',
        'erlang': '''
            (module_attribute) @module
            (fun_decl (function_clause (atom) @function_name)) @function
        ''',
        'ocaml': '''
            (module_definition) @module
            (value_definition (let_binding (value_name) @function_name)) @function
        ''',
        'r': '''
            (function_definition) @function
        ''',
        
        # Web frameworks and markup languages
        'vue': '''
            (component) @component
            (template_element) @template
            (script_element) @script
            (element) @element
        ''',
        'svelte': '''
            (document) @document
            (element) @element
            (script_element) @script
            (style_element) @style
        ''',
        'astro': '''
            (document) @document
            (frontmatter) @frontmatter
            (element) @element
            (style_element) @style
        ''',
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
        'elm': '''
            (value_declaration) @function
            (type_declaration) @type
            (type_alias_declaration) @type_alias
        ''',
        'elm_function': '''
            (function_declaration_left) @function
        ''',
        'embeddedtemplate': '''
            (template) @template
            (block) @block
            (partial) @partial
        ''',
        'heex': '''
            (element) @element
            (component) @component
        ''',
        
        # Configuration and data formats
        'toml': '''
            (table) @table
            (table_array_element) @table_array
            (pair) @pair
        ''',
        'xml': None,
        'ini': None,
        'csv': None,
        'tsv': None,
        'jsonnet': '''
            (function) @function
            (local_bind) @local_bind
            (object) @object
        ''',
        'yaml': '''
            (block_mapping_pair) @pair
            (block_sequence_item) @item
            (block_scalar) @scalar
        ''',
        
        # System and infrastructure languages
        'dockerfile': '''
            (from_instruction) @from
            (run_instruction) @run
            (cmd_instruction) @cmd
            (copy_instruction) @copy
            (env_instruction) @env
        ''',
        'make': '''
            (rule) @rule
            (variable_assignment) @variable
        ''',
        'cmake': '''
            (function_def) @function
            (macro_def) @macro
            (normal_command) @command
        ''',
        'ninja': '''
            (rule) @rule
            (build) @build
            (variable) @variable
        ''',
        'meson': '''
            (function_definition) @function
            (method_call) @method
        ''',
        'bazel': '''
            (function_definition) @function
            (rule_definition) @rule
        ''',
        
        # Query and template languages
        'graphql': '''
            (type_definition) @type
            (field_definition) @field
            (operation_definition) @operation
        ''',
        'sparql': '''
            (select_query) @select
            (ask_query) @ask
            (construct_query) @construct
            (describe_query) @describe
        ''',
        'prisma': '''
            (model_declaration) @model
            (enum_declaration) @enum
            (field_declaration) @field
        ''',
        'rego': '''
            (package) @package
            (rule) @rule
            (function) @function
        ''',
        'jq': '''
            (function_definition) @function
            (query) @query
        ''',
        
        # Functional and academic languages
        'haskell': '''
            (header) @module
            (function) @function
            (signature) @signature
        ''',
        'ocaml': '''
            (module_definition) @module
            (value_definition) @value
            (type_definition) @type
        ''',
        'ocaml_interface': '''
            (module_definition) @module
            (value_definition) @value
            (type_definition) @type
        ''',
        'fennel': '''
            (function_definition) @function
            (let_expression) @let
        ''',
        'janet': '''
            (def) @def
            (var) @var
            (fn) @function
        ''',
        'scheme': None,
        'commonlisp': None,
        'racket': None,
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
        
        # Shell and scripting languages
        'bash': '''
            (function_definition name: (word) @name) @function
            (command name: (command_name (word)) @name) @command
        ''',
        'fish': '''
            (function_definition) @function
            (command) @command
        ''',
        'powershell': None,
        'zsh': None,
        
        # Markup and documentation languages
        'markdown': '''
            (atx_heading) @heading
            (setext_heading) @heading
            (fenced_code_block) @code_block
            (html_block) @html_block
        ''',
        'rst': '''
            (section) @section
            (directive) @directive
            (field) @field
        ''',
        'org': '''
            (section) @section
            (headline) @headline
            (block) @block
        ''',
        'latex': '''
            (chapter) @chapter
            (section) @section
            (subsection) @subsection
            (subsubsection) @subsubsection
        ''',
        'tex': '''
            (chapter) @chapter
            (section) @section
            (subsection) @subsection
            (subsubsection) @subsubsection
        ''',
        
        # Database query languages
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
        'mysql': None,
        'postgresql': None,
        
        # Smart contract languages
        'solidity': '''
            (contract_declaration) @contract
            (function_definition) @function
            (modifier_definition) @modifier
            (event_definition) @event
        ''',
        'vyper': '''
            (function_definition) @function
            (event_definition) @event
            (struct_definition) @struct
        ''',
        
        # Hardware description languages
        'verilog': '''
            (module_declaration) @module
            (function_declaration) @function
            (task_declaration) @task
        ''',
        'systemverilog': '''
            (module_declaration) @module
            (function_declaration) @function
            (task_declaration) @task
        ''',
        'vhdl': None,
        
        # Other programming languages
        'swift': '''
            (class_declaration name: (type_identifier) @name) @class
            (function_declaration name: (simple_identifier) @name) @function
        ''',
        'kotlin': '''
            (class_declaration) @class
            (function_declaration) @function
            (property_declaration) @property
        ''',
        'scala': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
            (object_definition name: (identifier) @name) @object
            (trait_definition name: (identifier) @name) @trait
        ''',
        'dart': '''
            (class_definition) @class
            (function_signature) @function
            (method_signature) @method
            (getter_signature) @getter
            (setter_signature) @setter
        ''',
        'go': '''
            (function_declaration name: (identifier) @name) @function
            (method_declaration name: (field_identifier) @name) @method
            (type_declaration) @type
        ''',
        'rust': '''
            (function_item name: (identifier) @name) @function
            (struct_item name: (type_identifier) @name) @struct
            (enum_item name: (type_identifier) @name) @enum
            (trait_item name: (type_identifier) @name) @trait
            (impl_item) @impl
        ''',
        'zig': None,
        'v': None,
        'nim': None,
        'julia': '''
            (function_definition name: (identifier) @name) @function
            (module_definition name: (identifier) @name) @module
            (struct_definition) @struct
        ''',
        'matlab': '''
            (function_definition name: (identifier) @name) @function
            (class_definition name: (identifier) @name) @class
        ''',
        'r': '''
            (function_definition) @function
            (call function: (identifier) @function_call)
        ''',
        'perl': '''
            (package_statement) @package
            (subroutine_declaration_statement) @subroutine
        ''',
        'tcl': None,
        'lua': '''
            (function_declaration) @function
            (table_constructor) @table
        ''',
        'ruby': '''
            (class name: (constant) @name) @class
            (method name: (identifier) @name) @method
            (singleton_method name: (identifier) @name) @method
        ''',
        'php': '''
            (class_declaration name: (name) @name) @class
            (function_definition name: (name) @name) @function
            (method_declaration name: (name) @name) @method
        ''',
        'java': '''
            (class_declaration name: (identifier) @name) @class
            (method_declaration name: (identifier) @name) @method
            (constructor_declaration name: (identifier) @name) @constructor
        ''',
        'csharp': '''
            (class_declaration name: (identifier) @name) @class
            (method_declaration name: (identifier) @name) @method
            (constructor_declaration name: (identifier) @name) @constructor
        ''',
        'cpp': '''
            (class_specifier name: (type_identifier) @name) @class
            (struct_specifier name: (type_identifier) @name) @struct
            (function_definition declarator: (identifier) @name) @function
        ''',
        'c': '''
            (function_definition declarator: (identifier) @name) @function
            (struct_specifier name: (type_identifier) @name) @struct
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
        
        # Markup and template languages
        'html': '''
            (element) @element
            (script_element) @script
            (style_element) @style
        ''',
        'css': '''
            (rule_set) @rule
            (media_statement) @media
            (keyframes_statement) @keyframes
        ''',
        'scss': '''
            (rule_set) @rule
            (media_statement) @media
            (keyframes_statement) @keyframes
            (mixin_statement) @mixin
            (function_statement) @function
        ''',
        'sass': '''
            (rule_set) @rule
            (mixin) @mixin
            (function) @function
        ''',
        'less': '''
            (rule_set) @rule
            (mixin_definition) @mixin
            (function_definition) @function
        ''',
        
        # Configuration languages
        'hcl': '''
            (block) @block
            (attribute) @attribute
            (object) @object
        ''',
        'terraform': '''
            (block) @block
            (attribute) @attribute
            (object) @object
        ''',
        'puppet': None,
        'ansible': '''
            (block_mapping_pair) @pair
            (block_sequence_item) @item
        ''',
        
        # Domain-specific languages
        'thrift': None,
        'proto': '''
            (message) @message
            (service) @service
            (rpc) @rpc
        ''',
        'capnp': '''
            (struct) @struct
            (interface) @interface
            (method) @method
        ''',
        'smithy': '''
            (shape_statement) @shape
            (service_statement) @service
            (operation_statement) @operation
        ''',
        
        # Text processing languages
        'awk': '''
            (function_definition) @function
            (pattern) @pattern
        ''',
        'sed': '''
            (command) @command
        ''',
        
        # Languages with fallback (not supported by tree_sitter_language_pack)
        'fsharp': None,
        'vb': None,
        'makefile': None,
        'protobuf': None,
        
        # Additional languages
        'groovy': None,
    }
    return queries.get(language_key)