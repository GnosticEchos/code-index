"""Constants for code_index application."""

# =============================================================================
# Timeout constants (in seconds)
# =============================================================================

# HTTP request timeouts
HTTP_TIMEOUT_DEFAULT = 10  # Default timeout for HTTP requests
HTTP_TIMEOUT_LONG = 30  # Longer timeout for operations that may take longer

# Batch processing timeouts
BATCH_TIMEOUT = 300  # 5 minutes timeout per batch
BATCH_TIMEOUT_MINUTES = 5  # BATCH_TIMEOUT in minutes

# Cleanup intervals
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes between cleanup operations
MEMORY_CHECK_INTERVAL_SECONDS = 60  # 1 minute between memory checks

# =============================================================================
# Memory thresholds (in bytes or MB)
# =============================================================================

# Memory usage thresholds (in percent)
MEMORY_THRESHOLD_DEFAULT = 70.0  # Default threshold for memory cleanup (percent)
MEMORY_THRESHOLD_HIGH = 80.0  # High memory warning threshold (percent)
MEMORY_THRESHOLD_CRITICAL = 90.0  # Critical memory threshold (percent)

# Memory limits (in MB)
MEMORY_LIMIT_DEFAULT = 500  # Default memory limit in MB
MEMORY_TARGET_EMBEDDING = 50  # Target memory for embedding operations (MB)
MEMORY_TARGET_BATCH = 10  # Target memory per batch (MB)

# =============================================================================
# Buffer sizes (in bytes)
# =============================================================================

# File reading buffers
FILE_READ_BUFFER_SMALL = 4096  # 4KB - small file reads (hashing, etc.)
FILE_READ_BUFFER_MEDIUM = 8192  # 8KB - medium buffer
FILE_READ_BUFFER_LARGE = 65536  # 64KB - large buffer (default)
FILE_READ_BUFFER_XLARGE = 16384  # 16KB - extra large

# Chunk sizes for processing
CHUNK_SIZE_DEFAULT = 64 * 1024  # 64KB default chunk size
CHUNK_SIZE_LARGE = 256 * 1024  # 256KB for large files
CHUNK_SIZE_STREAMING = 1024 * 1024  # 1MB for streaming operations

# Memory mapping thresholds
MMAP_MIN_SIZE_DEFAULT = 64 * 1024  # 64KB minimum file size for mmap
MMAP_MIN_SIZE_SMALL = 32 * 1024  # 32KB minimum for optimized mmap

# =============================================================================
# Batch processing constants
# =============================================================================

# Batch sizes
BATCH_SIZE_SMALL = 10  # Small batch size for parallel processing
BATCH_SIZE_DEFAULT = 32  # Default batch size for embedding
BATCH_SIZE_MEDIUM = 50  # Medium batch size
BATCH_SIZE_LARGE = 100  # Large batch size
BATCH_SIZE_XLARGE = 1000  # Extra large batch size

# Batch limits
MAX_BATCH_SIZE = 1000  # Maximum allowed batch size
MIN_BATCH_SIZE = 1  # Minimum batch size

# Batch segment threshold
BATCH_SEGMENT_THRESHOLD = 32  # Threshold for segmenting batches

# =============================================================================
# Parallel processing constants
# =============================================================================

# Worker counts
MAX_WORKERS_DEFAULT = 4  # Default number of worker threads
MAX_WORKERS_MULTIPLIER = 2  # Multiplier for CPU count
MAX_PARALLEL_BATCHES = 4  # Maximum parallel embedding batches

# Concurrent processing
MAX_CONCURRENT_BATCHES = 3  # Maximum concurrent batch operations

# =============================================================================
# Retry constants
# =============================================================================

# Retry configuration
MAX_RETRIES = 3  # Maximum number of retry attempts
RETRY_DELAY_DEFAULT = 1.0  # Default delay between retries (seconds)
RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base

# Retry batch size reduction
RETRY_BATCH_DIVISOR = 2  # Divide batch size by this for retries

# =============================================================================
# Search and query limits
# =============================================================================

# Search limits
MAX_SEARCH_RESULTS = 100  # Maximum number of search results
MAX_QUERY_LENGTH = 1000  # Maximum query string length

# =============================================================================
# File size limits (in bytes)
# =============================================================================

# File size limits
MAX_FILE_SIZE_DEFAULT = 1 * 1024 * 1024  # 1MB default max file size
TREE_SITTER_MAX_FILE_SIZE = 512 * 1024  # 512KB max for tree-sitter parsing

# Large file thresholds
LARGE_FILE_THRESHOLD = 256 * 1024  # 256KB - threshold for "large" files
LARGE_FILE_THRESHOLD_XL = 10 * 1024 * 1024  # 10MB - extra large files
VERY_LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB - very large files

# Streaming thresholds
STREAMING_THRESHOLD = 1024 * 1024  # 1MB - start streaming above this

# =============================================================================
# Embedding dimensions
# =============================================================================

# Common embedding dimensions
EMBEDDING_DIMENSION_DEFAULT = 768  # Default (nomic-embed-text)
EMBEDDING_DIMENSION_QWEN = 1024  # Qwen models
EMBEDDING_DIMENSION_LARGE = 3584  # text-embedding-3-large

# =============================================================================
# Tree-sitter parsing limits
# =============================================================================

# Tree-sitter limits
TREE_SITTER_MAX_BLOCKS = 100  # Maximum blocks per file
TREE_SITTER_MAX_BLOCKS_REDUCED = 50  # Reduced limit for memory optimization
TREE_SITTER_MAX_BLOCKS_SMALL = 25  # Small limit for constrained environments

# Tree-sitter block size limits
TREE_SITTER_MIN_BLOCK_CHARS = 30  # Minimum characters per block
TREE_SITTER_MIN_BLOCK_CHARS_LARGE = 50  # Larger minimum for big files

# Resource age limits
TREE_SITTER_MAX_RESOURCE_AGE = 1800  # 30 minutes max resource age

# =============================================================================
# Configuration defaults
# =============================================================================

# Language-specific chunk sizes (in bytes)
CHUNK_SIZE_PYTHON = 64 * 1024  # Python files
CHUNK_SIZE_JAVASCRIPT = 128 * 1024  # JavaScript/TypeScript files
CHUNK_SIZE_JAVA = 256 * 1024  # Java files
CHUNK_SIZE_CPP = 256 * 1024  # C/C++ files
CHUNK_SIZE_RUST = 128 * 1024  # Rust files
CHUNK_SIZE_GO = 128 * 1024  # Go files
CHUNK_SIZE_TEXT = 32 * 1024  # Plain text files
CHUNK_SIZE_MARKDOWN = 32 * 1024  # Markdown files
CHUNK_SIZE_JSON = 64 * 1024  # JSON files
CHUNK_SIZE_XML = 128 * 1024  # XML files
CHUNK_SIZE_YAML = 32 * 1024  # YAML files

# =============================================================================
# Operation estimation constants
# =============================================================================

# Embedding time estimation
EMBEDDING_TIME_PER_CHUNK = 0.1  # seconds per chunk for embedding

# Complexity thresholds
LARGE_FILE_OPERATION_THRESHOLD = 100 * 1024  # 100KB - large file threshold
MANY_FILES_THRESHOLD = 1000  # Threshold for "many files" complexity
CRITICAL_FILES_THRESHOLD = 5000  # Threshold for critical file count

# File processing time estimation (seconds)
BASE_FILE_PROCESSING_TIME = 0.05  # seconds per file (baseline)
TREE_SITTER_OVERHEAD = 2.0  # multiplier for tree-sitter processing

# Warning levels (in seconds)
WARNING_LEVEL_CRITICAL = 300  # 5 minutes
WARNING_LEVEL_WARNING = 120  # 2 minutes
WARNING_LEVEL_CAUTION = 30  # 30 seconds

# MCP Server Resource Management
MEMORY_THRESHOLD_MCP = 1024  # 1GB default memory threshold for MCP
CLEANUP_INTERVAL_MCP = 300  # 5 minutes cleanup interval
OLD_RESOURCE_THRESHOLD = 3600  # 1 hour for old resource cleanup

# Memory pools
MEMORY_POOL_MAX_SIZE = 100  # Maximum objects in memory pool

# Shutdown timeout
SHUTDOWN_WAIT_TIMEOUT = 30.0  # seconds to wait for operations to complete