# Code Index - Complete Logic Flow Documentation

## Overview
This document describes the complete flow from initial file scanning through query execution and result processing.

## Architecture Components

### 1. File Scanning & Discovery Layer
- **DirectoryScanner** (`src/code_index/scanner.py`)
- **SmartIgnoreManager** (`src/code_index/smart_ignore_manager.py`)
- **PathUtils** (`src/code_index/path_utils.py`)
- **FileProcessingService** (`src/code_index/services/core/file_processing_service.py`)

### 2. Language Detection & Parsing
- **LanguageDetector** (`src/code_index/indexing/language_detector.py`)
- **TreeSitterFileProcessor** (`src/code_index/services/treesitter/file_processor.py`)
- **CodeParser** (`src/code_index/parser.py`)
- **HybridParsers** (`src/code_index/hybrid_parsers.py`)

### 3. Query Management
- **QueryManager** (`src/code_index/query_manager.py`)
- **QueryService** (`src/code_index/services/core/query_service.py`)
- **QueryCache** (`src/code_index/services/query/query_cache.py`)
- **tree_sitter_queries.py** (`src/code_index/treesitter_queries.py`) - Language-specific query strings
- **universal_schema_service.py** (`src/code_index/services/query/universal_schema_service.py`) - 908-record relationship schema

### 4. Relationship Extraction
- **TreeSitterBlockExtractor** (`src/code_index/services/treesitter/block_extractor.py`)
- **RelationshipBlockExtractor** (`src/code_index/services/treesitter/relationship_extractor.py`)
- **TreeSitterQueryManager** (`src/code_index/services/treesitter/query_manager.py`)

### 5. Indexing & Storage
- **IndexOrchestrator** (`src/code_index/indexing/orchestrator.py`)
- **BatchManager** (`src/code_index/indexing/batch_manager.py`)
- **FileProcessor** (`src/code_index/indexing/file_processor.py`)
- **QdrantVectorStore** (`src/code_index/vector_store.py`)
- **IndexingDependencies** (`src/code_index/services/shared/indexing_dependencies.py`)

### 6. Search & Results
- **SearchService** (`src/code_index/services/core/search_service.py`)
- **EmbeddingGenerator** (`src/code_index/services/embedding/embedding_generator.py`)
- **ResultProcessor** (`src/code_index/search/result_processor.py`)
- **SimilaritySearchStrategy** (`src/code_index/search/similarity_search_strategy.py`)
- **EmbeddingSearchStrategy** (`src/code_index/search/embedding_search_strategy.py`)

### 7. Chunking Strategies
- **ChunkingStrategy** (base, `src/code_index/chunking.py`)
- **LineChunkingStrategy** (`src/code_index/chunking.py`)
- **TreeSitterChunkingStrategy** (`src/code_index/chunking.py`)

---

## Complete Flow: File Scan → Query → Results

```mermaid
graph TD
    Start([Start Indexing]) --> Scanner[DirectoryScanner.scan_directory]
    
    subgraph "1. File Discovery"
        Scanner -->|Enumerate files| Ignore[SmartIgnoreManager]
        Ignore -->|Apply .gitignore patterns| Filter[PathUtils.validate_file_path]
        Filter -->|Check extensions| LangDet[LanguageDetector]
    end
    
    subgraph "2. Language Detection"
        LangDet -->|File extension| DetectExt[Detect by extension]
        LangDet -->|File content| DetectContent[Detect by content heuristics]
        LangDet -->|Shebang| DetectShebang[Detect by shebang]
        LangDet -->|Tree-sitter| DetectTS[Tree-sitter parser detection]
        LangDet -->|Return| LangKey[language_key: str]
    end
    
    subgraph "3. File Processing"
        LangKey -->|language_key| Proc[FileProcessingService.process_files]
        Proc -->|Load encoding| Encode[load_file_with_encoding]
        Encode -->|file content| Chunk[ChunkingStrategy]
    end
    
    subgraph "4. Chunking Strategies"
        Chunk -->|strategy=lines| Line[LineChunkingStrategy]
        Chunk -->|strategy=treesitter| TSChunk[TreeSitterChunkingStrategy]
        
        Line -->|Split by lines| LineBlocks[Create line-based blocks]
        
        TSChunk -->|Parse AST| TSParse[TreeSitter parse]
        TSParse -->|Get queries| GetQ[get_queries_for_language]
        GetQ -->|language_key| TQ[tree_sitter_queries.py]
        TQ -->|Return query string| TSExec[Execute tree-sitter query]
        TSExec -->|Captures| TSBlocks[Semantic code blocks]
    end
    
    subgraph "5. Block Processing"
        LineBlocks -->|blocks| ProcBlocks
        TSBlocks -->|blocks| ProcBlocks
        
        subgraph "5a. Relationship Extraction (Optional)"
            ProcBlocks -->|Extract relationships| RExtract[RelationshipBlockExtractor]
            RExtract -->|Use schema| US[UniversalSchemaService]
            US -->|Load 908 queries| QL[queries_minimal.jsonl]
            QL -->|Query patterns| RExtract
            RExtract -->|Extract| Rels[Code relationships]
            Rels -->|class, function, import, call| StoreRels[Store in DB]
        end
        
        ProcBlocks -->|Each block| Embed[EmbeddingGenerator]
    end
    
    subgraph "6. Embedding Generation"
        Embed -->|Text block| CheckCache[Check embedding cache]
        CheckCache -->|Cache miss| Ollama[OllamaEmbedder.create_embeddings]
        Ollama -->|API call| OllamaAPI[Ollama API: /api/embeddings]
        OllamaAPI -->|Generate| Vector[768-dim vector]
        Vector -->|Store| Cache[Update cache]
        Cache -->|Return| Vectors[Embedding vectors]
    end
    
    subgraph "7. Vector Storage"
        Vectors -->|Upsert| Qdrant[QdrantVectorStore]
        Qdrant -->|Collection| Points[Vector points + metadata]
        Points -->|Metadata| Meta[file_path, line_start, line_end, language, etc.]
    end
    
    EndIndex([Indexing Complete])
    
    Scanner -->|Progress| Progress[ProgressManager]
    Proc -->|Progress| Progress
    Qdrant -->|Progress| Progress
    
    style Start fill:#90EE90,stroke:#006400
    style EndIndex fill:#90EE90,stroke:#006400
    style TQ fill:#FFE4B5,stroke:#DAA520
    style QL fill:#FFE4B5,stroke:#DAA520
    style US fill:#FFE4B5,stroke:#DAA520
```

---

## Query Execution Flow

```mermaid
graph TD
    Start([User Query]) --> Search[SearchService.search]
    
    subgraph "Query Input Processing"
        Search -->|Parse| Normalize[QueryNormalizer]
        Normalize -->|Clean/normalize| QCache[QueryCache.check]
    end
    
    subgraph "Cache Check"
        QCache -->|Cache hit| ReturnCached[Return cached results]
        QCache -->|Cache miss| EmbedQ[Generate query embedding]
    end
    
    subgraph "Query Embedding"
        EmbedQ -->|Text query| QEmbed[EmbeddingGenerator]
        QEmbed -->|Ollama| QVector[Query vector]
    end
    
    subgraph "Vector Search"
        QVector -->|Search| QDrant[QdrantVectorStore.search]
        QDrant -->|ANN search| Scored[Scored results]
        Scored -->|Filter| Filtered[Min score threshold]
    end
    
    subgraph "Result Processing"
        Filtered -->|Re-rank| ReRank[ResultRanker]
        ReRank -->|Boost by| Boost[Relevance heuristics]
        Boost -->|File type| TypeBoost[Language weights]
        Boost -->|Recency| TimeBoost[Recent files]
        Boost -->|Popularity| PopBoost[Access frequency]
        Boost -->|Final results| Formatted[Format results]
    end
    
    subgraph "Response Format"
        Formatted -->|JSON| APIResp[API response]
        Formatted -->|Text| CLIResp[CLI display]
    end
    
    ReturnCached -->|Results| APIResp
    APIResp --> End([End])
    CLIResp --> End
    
    style Start fill:#87CEEB,stroke:#191970
    style End fill:#87CEEB,stroke:#191970
    style QDrant fill:#DDA0DD,stroke:#8B008B
```

---

## Tree-Sitter Query System Details

```mermaid
graph TD
    subgraph "tree_sitter_queries.py"
        TQDict[queries dictionary]
        TQDict -->|Key| Python["python": {...}]
        TQDict -->|Key| Java["java": {...}]
        TQDict -->|Key| JS["javascript": {...}]
        TQDict -->|Key| Rust["rust": {...}]
        TQDict -->|20+ languages| Other[other languages]
        
        Python -->|Query| PyFunc[function_definition]
        Python -->|Query| PyClass[class_definition]
        Python -->|Query| PyImport[import_statement]
        
        Java -->|Query| JavaClass[class_declaration]
        Java -->|Query| JavaMethod[method_declaration]
        
        style TQDict fill:#FFE4B5,stroke:#DAA520
    end
    
    subgraph "universal_schema_service.py"
        US[UniversalSchemaService]
        US -->|Load| QL[queries_minimal.jsonl]
        QL -->|908 records| Schema[Relationship schema]
        
        Schema -->|Type| Class[class]
        Schema -->|Type| Func[function]
        Schema -->|Type| Imp[import]
        Schema -->|Type| Call[call]
        Schema -->|Type| Var[variable]
        Schema -->|5 types| OtherTypes[other]
    end
    
    subgraph "relationship_extractor.py"
        RE[RelationshipBlockExtractor]
        RE -->|Uses| US
        RE -->|Matches| TQDict
        RE -->|Extracts| Rel[Relationships]
        
        Rel -->|Output format| JSON[JSON-LD format]
        JSON -->|Stores| Graph[Knowledge graph]
    end
    
    TreeSitter[TreeSitter parser] -->|Parse code| AST[AST]
    AST -->|Matches| TQDict
    AST -->|Capture nodes| RE
    
    style QL fill:#E6E6FA,stroke:#4B0082
    style TQDict fill:#FFE4B5,stroke:#DAA520
    style US fill:#E6E6FA,stroke:#4B0082
    style RE fill:#F0F8FF,stroke:#4682B4
```

---

## Key Data Flow Paths

### Path A: Standard Indexing (Line-based chunking)
```
File → Scanner → LanguageDetector → LineChunking → Embedding → Qdrant
```

### Path B: Semantic Indexing (Tree-sitter chunking)
```
File → Scanner → LanguageDetector → TreeSitter → GetQueries → ExecuteQuery → 
SemanticBlocks → Embedding → Qdrant
```

### Path C: Relationship Extraction (Advanced)
```
File → Scanner → LanguageDetector → TreeSitter → GetQueries → ExecuteQuery →
UniversalSchema → RelationshipExtractor → KnowledgeGraph → Qdrant
```

### Path D: Search Query
```
Query → Normalize → Cache → Embedding → Qdrant ANN → Re-rank → Results
```

---

## Component Interactions Matrix

| Component | Depends On | Used By | Data Flow |
|-----------|-----------|---------|-----------|
| **DirectoryScanner** | PathUtils | FileProcessingService | File paths |
| **LanguageDetector** | TreeSitter | Scanner, Parser | language_key |
| **tree_sitter_queries.py** | - | TreeSitter, BlockExtractor | Query strings |
| **UniversalSchemaService** | queries_minimal.jsonl | RelationshipExtractor | 908 relationship rules |
| **RelationshipExtractor** | TreeSitter, US | FileProcessor | Relationship JSON |
| **EmbeddingGenerator** | Ollama API | Indexing, Search | 768-dim vectors |
| **QdrantVectorStore** | Qdrant server | Indexing, Search | Vector + metadata |
| **QueryManager** | QueryCache, Embedder | SearchService | Query results |
| **ResultRanker** | - | SearchService | Re-ranked results |

---

## Redundancy Analysis

### ✓ GOOD: No Critical Redundancies

### ⚠️ Potential Overlaps:

1. **Language Detection**
   - TreeSitter used for both: query execution AND language detection
   - Could cache detection results to avoid re-parsing

2. **Caching Layers**
   - File hash cache (cache.py)
   - Embedding cache (query_embedding_cache.py)
   - Query cache (query_cache.py)
   - Risk: Stale cache if file changes

3. **Chunking Strategies**
   - Line-based (simple, fast)
   - Tree-sitter based (semantic, slower)
   - Hybrid parser attempts both
   - ✅ Actually: Configurable, not redundant

4. **Query Systems** (⚠️ IMPORTANT)
   - `tree_sitter_queries.py`: Language-specific query strings
   - `universal_schema_service.py`: 908-record relationship schema
   - These serve DIFFERENT purposes:
     * Tree-sitter queries = "Find all function definitions" (syntax)
     * Universal schema = "Extract class/function/import/call relationships" (semantics)
   - ✅ Not redundant, complementary

### ✅ Well-Designed Separations:

1. **Indexing vs Search**: Clear separation, different code paths
2. **Parsing vs Embedding**: Modular, can swap components
3. **Storage vs Retrieval**: Qdrant handles both cleanly
4. **Sync vs Async**: Proper separation (mcp_server uses async)

---

## Critical Paths & Bottlenecks

### 🔴 High Latency:
1. **Ollama API calls** - Embedding generation (network + GPU)
   - Mitigation: Batch processing, caching
   
2. **Tree-sitter parsing** - Initial file analysis
   - Mitigation: Parallel processing, incremental updates

3. **Qdrant network calls** - Vector operations
   - Mitigation: Batch upserts, connection pooling

### 🟡 Medium Latency:
1. **File I/O** - Reading large codebases
   - Mitigation: Async I/O, parallel reads

2. **Tree-sitter query execution** - Complex semantic queries
   - Mitigation: Query optimization, limit depth

### 🟢 Low Latency:
1. **Cache lookups** - File hash, embeddings, queries
2. **Line-based chunking** - Simple text operations
3. **Local file scanning** - Fast with proper ignore patterns

---

## Recommendations

### 1. Performance
- ✅ Add query result pagination for large codebases
- ✅ Implement incremental indexing (watch for file changes)
- ✅ Parallel tree-sitter parsing (language-specific workers)

### 2. Reliability
- ✅ Better error handling for tree-sitter parse failures
- ✅ Retry logic for Ollama/Qdrant connection issues
- ✅ Graceful degradation (fallback to line-based if tree-sitter fails)

### 3. Scalability
- ✅ Distributed indexing (shard by language/module)
- ✅ Separate read/write Qdrant collections
- ✅ Async search endpoints

### 4. Maintainability
- ✅ Document the relationship between tree_sitter_queries.py and universal_schema_service.py
- ✅ Add type hints throughout (mypy is currently failing)
- ✅ Integration tests with mocked services

---

## Summary: Is There Redundant Logic?

**NO**: The architecture is well-structured with clear separations.

The two query systems serve different purposes:
- **tree_sitter_queries.py** = Syntax-level queries (find classes, functions)
- **universal_schema_service.py** = Semantic relationships (extract knowledge graph)

The flow from file scan to query is linear and efficient, with appropriate caching at each layer. The main areas for improvement are error handling, retry logic, and performance optimization - not structural redundancy.

**Grade: A-** (Excellent architecture, minor improvements needed in resilience)
