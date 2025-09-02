# Indexing Status Tracking System Design

## Overview

This document describes the design for implementing indexing status tracking in the Code Index Tool, inspired by KiloCode's approach.

## KiloCode Implementation Analysis

### Key Components

1. **StateManager**: Tracks indexing state and progress
   - States: "Standby", "Indexing", "Indexed", "Error"
   - Progress tracking: processedItems, totalItems
   - Event-based progress updates

2. **Orchestrator**: Coordinates indexing workflow
   - Manages state transitions
   - Reports progress during scanning
   - Handles errors and completion

3. **Scanner**: Processes files and reports progress
   - Accepts progress callbacks
   - Reports file parsing and block indexing progress

### Progress Tracking Pattern

```typescript
// State transitions
stateManager.setSystemState("Indexing", "Initializing services...")
stateManager.setSystemState("Indexing", "Services ready. Starting workspace scan...")

// Progress reporting
stateManager.reportBlockIndexingProgress(processedItems, totalItems)

// Completion
stateManager.setSystemState("Indexed", "Index up-to-date.")
```

## Proposed Python Implementation

### 1. IndexingStateManager Class

```python
from enum import Enum
from typing import Optional, Callable
import threading

class IndexingState(Enum):
    STANDBY = "Standby"
    INDEXING = "Indexing"  
    INDEXED = "Indexed"
    ERROR = "Error"

class IndexingProgress:
    def __init__(self, processed: int = 0, total: int = 0, message: str = ""):
        self.processed = processed
        self.total = total
        self.message = message

class IndexingStateManager:
    def __init__(self):
        self._state = IndexingState.STANDBY
        self._message = "Ready."
        self._processed_items = 0
        self._total_items = 0
        self._progress_listeners = []
        self._lock = threading.Lock()
    
    @property
    def state(self) -> IndexingState:
        return self._state
    
    @property
    def message(self) -> str:
        return self._message
    
    @property
    def progress(self) -> IndexingProgress:
        return IndexingProgress(
            processed=self._processed_items,
            total=self._total_items,
            message=self._message
        )
    
    def add_progress_listener(self, listener: Callable[[IndexingProgress], None]):
        """Add a listener for progress updates."""
        with self._lock:
            self._progress_listeners.append(listener)
    
    def set_state(self, new_state: IndexingState, message: Optional[str] = None):
        """Set the indexing state and optionally update the message."""
        with self._lock:
            state_changed = new_state != self._state
            message_changed = message is not None and message != self._message
            
            if state_changed or message_changed:
                self._state = new_state
                if message is not None:
                    self._message = message
                
                # Reset progress counters when not indexing
                if new_state != IndexingState.INDEXING:
                    self._processed_items = 0
                    self._total_items = 0
                    if new_state == IndexingState.STANDBY and message is None:
                        self._message = "Ready."
                    elif new_state == IndexingState.INDEXED and message is None:
                        self._message = "Index up-to-date."
                
                # Notify listeners
                self._notify_progress_listeners()
    
    def report_file_progress(self, processed_files: int, total_files: int, current_file: Optional[str] = None):
        """Report progress for file processing."""
        with self._lock:
            progress_changed = (
                processed_files != self._processed_items or 
                total_files != self._total_items
            )
            
            if progress_changed:
                self._processed_items = processed_files
                self._total_items = total_files
                
                if current_file:
                    self._message = f"Processing {current_file} ({processed_files}/{total_files})"
                else:
                    self._message = f"Processed {processed_files}/{total_files} files"
                
                self._notify_progress_listeners()
    
    def report_block_progress(self, processed_blocks: int, total_blocks: int):
        """Report progress for block processing."""
        with self._lock:
            progress_changed = (
                processed_blocks != self._processed_items or 
                total_blocks != self._total_items
            )
            
            if progress_changed:
                self._processed_items = processed_blocks
                self._total_items = total_blocks
                self._message = f"Indexed {processed_blocks}/{total_blocks} blocks"
                self._notify_progress_listeners()
    
    def _notify_progress_listeners(self):
        """Notify all progress listeners."""
        progress = self.progress
        for listener in self._progress_listeners:
            try:
                listener(progress)
            except Exception:
                # Don't let listener errors break progress reporting
                pass
```

### 2. IndexingOrchestrator Class

```python
import os
from typing import Optional, Callable
from code_index.config import Config
from code_index.scanner import DirectoryScanner
from code_index.parser import CodeParser
from code_index.embedder import OllamaEmbedder
from code_index.vector_store import QdrantVectorStore
from code_index.cache import CacheManager

class IndexingOrchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.state_manager = IndexingStateManager()
        self.scanner = DirectoryScanner(config)
        self.parser = CodeParser(config)
        self.embedder = OllamaEmbedder(config)
        self.vector_store = QdrantVectorStore(config)
        self.cache_manager = CacheManager(config.workspace_path)
        self._is_processing = False
    
    def start_indexing(self, progress_callback: Optional[Callable[[IndexingProgress], None]] = None):
        """Start the indexing process with progress tracking."""
        if progress_callback:
            self.state_manager.add_progress_listener(progress_callback)
        
        if self._is_processing:
            return
        
        self._is_processing = True
        try:
            # Initialize
            self.state_manager.set_state(IndexingState.INDEXING, "Initializing services...")
            
            collection_created = self.vector_store.initialize()
            if collection_created:
                self.cache_manager.clear_cache_file()
            
            self.state_manager.set_state(IndexingState.INDEXING, "Services ready. Starting workspace scan...")
            
            # Scan and process files
            cumulative_blocks_indexed = 0
            cumulative_blocks_found = 0
            
            def on_file_parsed(file_block_count: int):
                nonlocal cumulative_blocks_found
                cumulative_blocks_found += file_block_count
                self.state_manager.report_block_progress(cumulative_blocks_indexed, cumulative_blocks_found)
            
            def on_blocks_indexed(indexed_count: int):
                nonlocal cumulative_blocks_indexed
                cumulative_blocks_indexed += indexed_count
                self.state_manager.report_block_progress(cumulative_blocks_indexed, cumulative_blocks_found)
            
            # Perform the scan
            result = self.scanner.scan_directory(
                self.config.workspace_path,
                on_blocks_indexed=on_blocks_indexed,
                on_file_parsed=on_file_parsed
            )
            
            # Complete
            self.state_manager.set_state(IndexingState.INDEXED, "Index up-to-date.")
            
        except Exception as e:
            self.state_manager.set_state(IndexingState.ERROR, f"Indexing failed: {str(e)}")
            raise
        finally:
            self._is_processing = False
    
    def get_status(self) -> IndexingProgress:
        """Get current indexing status."""
        return self.state_manager.progress
```

### 3. Enhanced Scanner with Progress Reporting

```python
# In src/code_index/scanner.py
def scan_directory(self, directory: str = None, 
                  on_error: Optional[Callable[[Exception], None]] = None,
                  on_blocks_indexed: Optional[Callable[[int], None]] = None,
                  on_file_parsed: Optional[Callable[[int], None]] = None) -> Tuple[List[str], int]:
    """
    Recursively scan directory for supported files with progress reporting.
    
    Args:
        directory: Directory to scan (defaults to workspace path)
        on_error: Callback for handling errors
        on_blocks_indexed: Callback for block indexing progress
        on_file_parsed: Callback for file parsing progress
    """
    # ... existing scanning logic ...
    
    for root, dirs, files in os.walk(directory):
        # ... filtering logic ...
        
        for file in files:
            # ... file processing logic ...
            
            # Report file parsing progress
            if on_file_parsed:
                try:
                    # Parse file to get block count
                    blocks = self._parse_file_for_blocks(file_path)
                    on_file_parsed(len(blocks))
                except Exception as e:
                    if on_error:
                        on_error(e)
            
            # ... indexing logic ...
            
            # Report block indexing progress
            if on_blocks_indexed:
                on_blocks_indexed(1)  # or actual block count
    
    # ... return results ...
```

## CLI Integration

### Progress Display Options

```bash
# Basic progress display
code-index index --progress

# Detailed progress with file names
code-index index --progress --verbose

# JSON progress output for programmatic consumption
code-index index --progress --format json
```

### Progress Output Examples

```
[Indexing] Initializing services... 
[Indexing] Services ready. Starting workspace scan...
[Indexing] Processing main.py (12/156 files)
[Indexing] Indexed 45/234 blocks
[Indexing] Processing utils.py (45/156 files)
[Indexed] Index up-to-date.
```

## Implementation Roadmap

### Phase 1: Core State Management
- [ ] Implement IndexingStateManager
- [ ] Add state transition logic
- [ ] Implement progress reporting

### Phase 2: Orchestrator Integration
- [ ] Implement IndexingOrchestrator
- [ ] Integrate with existing components
- [ ] Add progress callback support

### Phase 3: Scanner Enhancement
- [ ] Modify scanner to report progress
- [ ] Add file parsing progress callbacks
- [ ] Add block indexing progress callbacks

### Phase 4: CLI Integration
- [ ] Add progress display options
- [ ] Implement progress output formatting
- [ ] Add real-time status commands

## Benefits

1. **Real-time Feedback**: Users can see exactly what's happening during indexing
2. **Progress Tracking**: Clear indication of how much work remains
3. **Error Handling**: Better error reporting and recovery
4. **User Experience**: Improved CLI experience with status updates
5. **Debugging**: Easier to diagnose issues with detailed progress information

## Future Enhancements

1. **ETA Calculation**: Estimate completion time based on progress rate
2. **Pause/Resume**: Allow interrupting and resuming indexing
3. **Web UI**: Progress display in a web interface
4. **Notifications**: System notifications for completion
5. **Historical Tracking**: Store indexing statistics for performance analysis