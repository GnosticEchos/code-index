# Getting Started with Code Index Tool

This guide will help you get started with the code index tool.

## Prerequisites

1. **Python 3.13+**: The tool requires Python 3.13 or later
2. **Ollama**: For generating embeddings
3. **Qdrant**: For vector storage
4. **uv**: For environment management (recommended)

## Installation

### 1. Install Python 3.13+

Make sure you have Python 3.13+ installed on your system.

### 2. Install uv (recommended)

```bash
# On Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
# Download the installer from https://github.com/astral-sh/uv/releases
```

### 3. Install Ollama

Download and install Ollama from https://ollama.com/

Pull an embedding model:
```bash
ollama pull nomic-embed-text:latest
```

### 4. Install Qdrant

You can run Qdrant in Docker:
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

Or download it from https://qdrant.tech/

### 5. Clone and Setup the Code Index Tool

```bash
# Clone the repository
git clone <repository-url>
cd code-index-tool

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install the tool
uv pip install -e .
```

## Configuration

The tool can be configured in several ways:

### Environment Variables

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=nomic-embed-text:latest
export QDRANT_URL=http://localhost:6333
export WORKSPACE_PATH=/path/to/your/project
```

### Configuration File

Create a `code_index.json` file:
```json
{
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "nomic-embed-text:latest",
    "qdrant_url": "http://localhost:6333",
    "workspace_path": ".",
    "extensions": [".py", ".js", ".ts", ".rs", ".vue"],
    "search_min_score": 0.4,
    "search_max_results": 50
}
```

## Usage

### Indexing Code

To index code in your workspace:
```bash
code-index index
```

To index with a specific configuration:
```bash
code-index index --config code_index.json
```

### Searching Code

To search indexed code:
```bash
code-index search "function to parse JSON"
```

To search with custom parameters:
```bash
code-index search "database connection" --min-score 0.5 --max-results 20
```

### Global Reset (Destructive)

To delete all Qdrant collections (including metadata by default) and clear local cache:
```bash
code-index collections clear-all --yes
```

Notes:
- Preview targets without deleting:
  - code-index collections clear-all --dry-run
- Keep metadata collection:
  - code-index collections clear-all --keep-metadata
- To delete a single collection:
  - code-index collections delete COLLECTION_NAME

## Supported File Types

The tool supports indexing the following file types:
- Programming languages: Python, JavaScript, TypeScript, Rust, Go, Java, C, C++, etc.
- Web technologies: HTML, CSS, Vue, React
- Data formats: JSON, YAML, XML
- Documentation: Markdown, reStructuredText
- Configuration: INI, TOML
- And many more...

## Performance Tips

1. **First Indexing**: The first indexing of a large project may take some time
2. **Incremental Updates**: Subsequent indexing only processes changed files
3. **File Filtering**: Use .gitignore to exclude unnecessary files
4. **Model Selection**: Choose an appropriate embedding model for your needs
5. **Batch Processing**: The tool processes files in batches for efficiency

## Troubleshooting

### Ollama Issues

- Make sure Ollama is running: `ollama serve`
- Check if the model is available: `ollama list`
- Pull the model if needed: `ollama pull nomic-embed-text:latest`

### Qdrant Issues

- Make sure Qdrant is running
- Check the Qdrant URL in your configuration
- Verify network connectivity to the Qdrant server

### Python Issues

- Make sure you're using Python 3.13+
- Ensure all dependencies are installed
- Check that the virtual environment is activated

## Extending the Tool

The tool is designed to be extensible:
- Add new file types by updating the supported extensions list
- Implement more sophisticated parsing by enhancing the parser module
- Add new embedding providers by creating new embedder classes
- Extend CLI functionality by adding new commands to cli.py

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT