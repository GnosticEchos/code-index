from typing import List, Optional, Callable, Iterator, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

from ...errors import ErrorHandler, ErrorContext, ErrorCategory, ErrorSeverity


logger = logging.getLogger("code_index.streaming_embedder")

class StreamingEmbedder:

    def __init__(
            self,
            embedder,
            batch_size: int = 32,
            parallel_batches: int = 1,
            progress_callback: Optional[Callable[[float], None]] = None,
            error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize the streaming embedder.

        Args:
            embedder: The underlying embedder instance (e.g., OllamaEmbedder)
            batch_size: Number of texts to process in each batch (default: 32)
            parallel_batches: Number of parallel batch processing threads (default: 1)
            progress_callback: Optional callback for progress reporting (receives percentage)
            error_handler: Optional error handler instance
        """
        self._embedder = embedder
        self._batch_size = max(1, batch_size)
        self._parallel_batches = max(1, parallel_batches)
        self._progress_callback = progress_callback
        self._error_handler = error_handler or ErrorHandler()
        self._lock = threading.Lock()
        self._logger = logger

    @property
    def batch_size(self) -> int:
        """
        Get the current batch size.
        """
        return self._batch_size

    @property
    def parallel_batches(self) -> int:
        """
        Get the number of parallel batches.
        """
        return self._parallel_batches

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts using the underlying embedder.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            response = self._embedder.create_embeddings(texts)
            embeddings = response.get("embeddings", [])
            if not isinstance(embeddings, list):
                raise ValueError("Invalid response structure from embedder")

            return embeddings
        except Exception as e:
            error_context = ErrorContext(
                component="streaming_embedder",
                operation="embed_batch"
            )
            error_response = self._error_handler.handle_error(
                e, error_context, ErrorCategory.EMBEDDING, ErrorSeverity.HIGH
            )
            self._logger.error(f"Failed to embed batch: {error_response.message}")
            raise

    def embed_stream(
        self,
        texts: List[str],
        on_embedding: Optional[Callable[[List[List[float]], int, int], None]] = None
    ) -> Iterator[List[List[float]]]:
        """
        Stream embeddings one batch at a time.

        This method processes texts in batches and yields embeddings as they are
        computed, rather than accumulating all embeddings in memory.

        Args:
            texts: List of texts to embed
            on_embedding: Optional callback for each embedding batch.
                         Receives (embeddings, batch_index, total_texts)

        Yields:
            List of embedding vectors for each batch

        Example:
            >>> embedder = StreamingEmbedder(ollama_embedder, batch_size=32)
            >>> for embedding_batch in embedder.embed_stream(texts):
            ...     # Process embeddings immediately
            ...     process_embeddings(embedding_batch)
        """
        total_texts = len(texts)
        if total_texts == 0:
            if self._progress_callback:
                self._progress_callback(100.0)
            return

        for i in range(0, total_texts, self._batch_size):
            batch = texts[i:i + self._batch_size]
            embeddings = self.embed_batch(batch)

            if on_embedding:
                on_embedding(embeddings, i, total_texts)

            # Report progress
            if self._progress_callback:
                progress = min(100.0, (i + len(batch)) / total_texts * 100.0)
                self._progress_callback(progress)

            yield embeddings

        # Report completion
        if self._progress_callback:
            self._progress_callback(100.0)

    def embed_stream_parallel(
        self,
        texts: List[str],
        on_embedding: Optional[Callable[[List[List[float]], int, int], None]] = None
    ) -> Iterator[List[List[float]]]:
        """
        Stream embeddings with parallel batch processing.

        This method processes multiple batches in parallel using thread pools,
        which can improve throughput for large text collections.

        Args:
            texts: List of texts to embed
            on_embedding: Optional callback for each embedding batch.
                         Receives (embeddings, batch_index, total_texts)

        Yields:
            List of embedding vectors for each batch (in order)

        Note:
            Results are yielded in the original order, even though processing
            may happen in parallel.
        """
        total_texts = len(texts)
        if total_texts == 0:
            if self._progress_callback:
                self._progress_callback(100.0)
            return

        # Create batches
        batches = []
        for i in range(0, total_texts, self._batch_size):
            batches.append((i, texts[i:i + self._batch_size]))

        # Process batches in parallel
        results = [None] * len(batches)
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self._parallel_batches) as executor:
            # Submit all batch tasks
            future_to_index = {
                executor.submit(self.embed_batch, batch): idx
                for idx, (_, batch) in enumerate(batches)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                batch_index = future_to_index[future]
                try:
                    embeddings = future.result()
                    results[batch_index] = embeddings

                    # Report progress
                    completed_count += 1
                    if self._progress_callback:
                        progress = completed_count / len(batches) * 100.0
                        self._progress_callback(progress)

                except Exception as e:
                    self._logger.error(f"Failed to process batch {batch_index}: {e}")
                    results[batch_index] = []

        # Yield results in order
        for i, embeddings in enumerate(results):
            if embeddings:
                batch_start = batches[i][0]
                if on_embedding:
                    on_embedding(embeddings, batch_start, total_texts)
                yield embeddings

        # Report completion
        if self._progress_callback:
            self._progress_callback(100.0)

    def embed_all(
        self,
        texts: List[str],
        on_embedding: Optional[Callable[[List[List[float]], int, int], None]] = None
    ) -> List[List[float]]:
        """
        Embed all texts and return as a single list (non-streaming).

        This method provides backward compatibility for code that expects
        all embeddings to be returned at once.

        Args:
            texts: List of texts to embed
            on_embedding: Optional callback for each embedding batch

        Returns:
            List of all embedding vectors
        """
        all_embeddings = []
        for embedding_batch in self.embed_stream(texts, on_embedding):
            all_embeddings.extend(embedding_batch)
        return all_embeddings

    def estimate_memory_usage(self, num_texts: int, embedding_dim: int = 768) -> int:
        """
        Estimate memory usage for embedding a given number of texts.

        Args:
            num_texts: Number of texts to embed
            embedding_dim: Dimension of each embedding vector (default: 768)

        Returns:
            Estimated memory usage in bytes
        """
        # Each float is 8 bytes (double precision)
        bytes_per_embedding = embedding_dim * 8
        total_bytes = num_texts * bytes_per_embedding

        # Add overhead for Python objects (rough estimate)
        overhead = num_texts * 100  # ~100 bytes per embedding object

        return total_bytes + overhead

    def get_optimal_batch_size(
        self,
        num_texts: int,
        embedding_dim: int = 768,
        target_memory_mb: int = 50
    ) -> int:
        """
        Calculate optimal batch size based on memory constraints.

        Args:
            num_texts: Total number of texts to embed
            embedding_dim: Dimension of each embedding vector
            target_memory_mb: Target memory usage per batch in MB

        Returns:
            Optimal batch size
        """
        if num_texts == 0:
            return self._batch_size

        # Calculate memory per text
        bytes_per_text = self.estimate_memory_usage(1, embedding_dim)
        target_bytes = target_memory_mb * 1024 * 1024

        # Calculate optimal batch size
        optimal_size = max(1, int(target_bytes / bytes_per_text))

        # Respect configured batch size as upper bound
        return min(optimal_size, self._batch_size)

    def set_progress_callback(self, callback: Optional[Callable[[float], None]]) -> None:
        """
        Set or update the progress callback.

        Args:
            callback: New progress callback function
        """
        self._progress_callback = callback


class BatchResult:

    def __init__(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        batch_index: int = 0,
        total_batches: int = 1
    ):
        """
        Initialize a batch result.

        Args:
            chunks: List of text chunks in this batch
            embeddings: List of embedding vectors for this batch
            batch_index: Index of this batch in the overall processing
            total_batches: Total number of batches
        """
        self.chunks = chunks
        self.embeddings = embeddings
        self.batch_index = batch_index
        self.total_batches = total_batches

    @property
    def size(self) -> int:
        """
        Get the number of items in this batch.
        """
        return len(self.chunks)

    @property
    def progress(self) -> float:
        """
        Get progress percentage for this batch.
        """
        if self.total_batches == 0:
            return 100.0
        return (self.batch_index + 1) / self.total_batches * 100.0