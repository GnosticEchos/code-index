# 🌍 Extending Language Support

Code Index natively supports over **200 programming languages** out of the box. 

Unlike simplistic tools that rely solely on file extensions, Code Index employs a three-tier AI-first detection system to accurately identify languages and a Universal Structural Schema to extract meaningful chunks (`class`, `function`, `call`, `import`) regardless of the language syntax.

---

## 🔍 How Language Detection Works

When Code Index reads a file, it determines the language using this fallback chain:

1. **Google Magika (AI Gatekeeper)**: A deep learning model analyzes the first 2KB of the file's binary signature. It can identify the language based on structural patterns and syntax, even if the file lacks an extension (e.g., a file named `script` with a `#!/usr/bin/env python3` shebang).
2. **Internal Mapping Registry**: If Magika is unsure, the system falls back to a massive internal mapping of known extensions (e.g., `.rs` -> `rust`, `.surql` -> `surql`).
3. **Pygments Auto-Discovery**: If `auto_extensions` is enabled in your configuration, Code Index will query the Pygments library to dynamically register hundreds of niche extensions and lexers.
4. **Plain Text Fallback**: If all else fails, it defaults to basic line chunking.

---

## 🛠️ Adding Custom Extensions

If you're using a niche domain-specific language (DSL) or a custom file extension that Code Index doesn't recognize out of the box, you can force it to read those files by adding them to your `code_index.json`.

```json
{
  "extensions": [
    ".rs", ".ts", ".vue", ".surql", ".js", ".py",
    ".my_custom_ext"  // <-- Add your extension here
  ]
}
```

Once added, Code Index will automatically process `.my_custom_ext` files. If it doesn't have a specific Tree-sitter parser for that extension, it will smoothly fall back to our high-performance **line chunking** strategy, ensuring your custom files are still embedded and searchable.

---

## 🌳 The Universal Relationship Schema (Tree-sitter)

For structural intelligence, Code Index uses Tree-sitter v0.23.x bindings combined with a custom **908-record Universal Relationship Schema**.

We maintain specific S-expression queries (`src/code_index/queries/queries_minimal.jsonl`) for parsing the structural boundaries of over 200 languages. These queries are derived from the comprehensive [tree-sitter-language-pack](https://github.com/kreuzberg-dev/tree-sitter-language-pack) repository, which provides a unified grammar collection and query definitions across the entire Tree-sitter ecosystem.

When you run with `--use-tree-sitter --chunking-strategy treesitter`, the engine looks up the detected language in this schema and dynamically extracts:
*   `class` definitions (Structs, Enums, Traits, Interfaces)
*   `function` logic (Methods, Functions)
*   `call` invocations
*   `import` statements

### Modifying the Parser Behavior

If you need to tweak how a specific language is parsed (e.g., you want to extract a specific type of macro in Rust), you can extend the `queries_minimal.jsonl` file. 

Code Index uses a version-aware `QueryCursor` that supports both list-based and modern dictionary-based capture returns, meaning any standard Tree-sitter query will be evaluated correctly.
