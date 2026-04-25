# Code Index 🧠🔍

A fast, slightly-too-smart codebase indexing tool and semantic search engine. It reads your code, figures out what language it is (even if you forgot the extension), chops it up into meaningful pieces, and stuffs it into a vector database so your AI assistants can actually find things.

Under the hood, it combines **Google's Magika** for AI-driven file identification with **Tree-sitter** for surgical code parsing, all backed by **Ollama** and **Qdrant**.

It's available as a standalone CLI or as a full Model Context Protocol (MCP) server.

---

## 🌟 Why Code Index?

Because grepping through 10,000 files for "that one authentication middleware" is soul-crushing.

- **It Actually Understands Code**: Instead of blindly chopping files every 500 characters, it uses Tree-sitter (with 908 custom queries across 200+ languages) to extract complete `classes`, `functions`, `imports`, and `calls`.
- **AI Gatekeeper**: We integrated Google's Magika Deep Learning model. It looks at the first 2KB of a file and *knows* what language it is, even if it's named `Dockerfile.backup.old`.
- **Bring Your Own Models**: Uses your local Ollama instance for embeddings, keeping your codebase completely private.
- **Zero Dependencies (Mostly)**: We compile 37MB standalone binaries for Linux, macOS, and Windows. No fighting with Python virtual environments unless you really want to.
- **KiloCode Compatible**: Produces collections that KiloCode can use directly.

---

## 🛠️ Prerequisites

Before you start indexing the universe, you need two things running:
1. **[Ollama](https://ollama.com/)**: For generating embeddings (default expects `nomic-embed-text:latest` on `http://localhost:11434`).
2. **[Qdrant](https://qdrant.tech/)**: For storing the vectors (default expects `http://localhost:6333`).

---

## 🚀 Installation

### Option A: The Easy Way (Binaries)
Grab the standalone binary for your OS from the releases page (or build it yourself via `make build-all`). 
*It has Magika, Tree-sitter, and everything else jammed inside.*

```bash
chmod +x code-index
./code-index --help
```

### Option B: The Developer Way (From Source)
You'll need Python 3.13+ and `uv` (because pip is so 2023).

```bash
git clone <repository-url>
cd code_index
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## 💻 Usage: Command Line Interface

The CLI is perfect for scripting, CI/CD, or just aggressively re-indexing your project after a massive refactor.

### 1. Indexing
Point it at a directory and watch it go. We recommend always passing your config file explicitly.

```bash
# Basic line-by-line chunking (fastest)
code-index index --workspace ./my-project --config code_index.json

# Semantic chunking (smartest, highly recommended)
code-index index --workspace ~/kanban_frontend/clones/context-hub \
  --config rust_optimized_config.json \
  --use-tree-sitter --chunking-strategy treesitter

# Batch process a whole list of workspaces
code-index index --workspacelist ./repos.txt --config code_index.json
```

### 2. Searching
Find the code you wrote 6 months ago and completely forgot about. Always specify the workspace and config to ensure the embeddings map correctly.

```bash
# Natural language semantic search
code-index search "haskell signatures and data types in HelpTree.hs" \
  --workspace ~/Projects/HelpTree \
  --config rust_optimized_config.json

# Be picky (higher score = stricter match)
code-index search "database connection pool" \
  --workspace ./my-project \
  --config code_index.json \
  --min-score 0.7
```

### 3. Collection Management
Clean up your vector database before it consumes your entire hard drive.

```bash
# List everything we've indexed
code-index collections list

# Nuke a specific workspace's collection
code-index collections delete ws-abc123def456

# The Nuclear Option (deletes ALL collections, requires confirmation)
code-index collections clear-all
```

---

## 🌍 Supported Languages (200+)

Most indexing tools stop at Python, JavaScript, and maybe Rust. Code Index supports **over 200 programming languages** natively.

Because we use **Magika** for AI-driven detection and a 908-record **Universal Relationship Schema** for Tree-sitter parsing, Code Index can structurally map everything from `C++` and `Go` to obscure configuration formats, database schema dialects (like `Surql`), and functional languages like `Haskell` or `OCaml`.

**Missing a language?** Code Index can automatically augment its support using Pygments lexers, or you can manually define new rules.

👉 **[Read the full guide on extending language support](docs/language-support.md)**

---

## 🤖 Usage: MCP Server

Code Index includes a full **Model Context Protocol (MCP)** server. This allows AI assistants (like Claude Desktop or Cursor) to dynamically index and search your codebases themselves.

### Exposing the Server to your AI
Add this to your MCP client's configuration file.

**If using the compiled binary:**
```json
{
  "mcpServers": {
    "code_index": {
      "command": "/absolute/path/to/code-index-mcp",
      "args": []
    }
  }
}
```

**If running from source:**
```json
{
  "mcpServers": {
    "code_index": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/code_index",
        "run", "code-index-mcp"
      ]
    }
  }
}
```

Once connected, your AI gets three shiny new tools: `index`, `search`, and `collections`. You can literally say: *"Hey AI, please index the frontend folder using tree-sitter, then search it for the login component."*

---

## ⚙️ Configuration

By default, Code Index looks for a `code_index.json` file in your workspace or the current directory. If it doesn't find one, it uses sensible defaults.

Here is a fully loaded example configuration:

```json
{
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "nomic-embed-text:latest",
  "qdrant_url": "http://localhost:6333",
  
  "workspace_path": ".",
  "extensions": [".rs", ".ts", ".vue", ".surql", ".js", ".py"],
  
  "embedding_length": 768,
  "chunking_strategy": "treesitter",
  "use_tree_sitter": true,
  
  "search_min_score": 0.4,
  "search_max_results": 50,
  
  "tree_sitter_min_block_chars": 50,
  "tree_sitter_skip_test_files": true,
  
  "auto_ignore_detection": true,
  "skip_dot_files": true
}
```

> **Pro Tip**: Make sure `embedding_length` exactly matches the output dimension of your chosen `ollama_model`. If you switch from `nomic-embed-text` (768) to a massive Qwen model (e.g., 1024), you must update the length, or Qdrant will throw a tantrum.

---

## 🏗️ Building the Binaries

Want to compile the 37MB standalone executables yourself? We use Nuitka (v4.0.8+) for that. The build scripts aggressively prune bloat (like `torch` and `sympy`) to keep the binaries lean while retaining the ONNX-backed Magika AI.

```bash
# Build both CLI and MCP binaries (Linux, macOS, Windows compatible)
make build-all
```
The finished binaries will be waiting for you in the `dist/` directory.

---

## 📜 License

MIT License. Do whatever you want with it, just don't blame us if it achieves sentience.
