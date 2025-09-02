# Collection Management

## Overview

The enhanced collection management system provides improved organization and identification of indexed codebases through persistent metadata storage and human-readable workspace path mapping.

## Features

### Automatic Collection Naming
- Generates consistent collection names based on workspace paths
- Uses SHA-256 hashing for deterministic naming
- Follows Kilo Code extension conventions with `ws-` prefix

### Persistent Metadata Storage
- Stores workspace path information with each collection
- Maintains indexing dates and file counts
- Enables collection identification without manual tracking

### Human-Readable Collection Listing
- Displays actual filesystem paths instead of hash-based names
- Shows point counts and collection status
- Provides detailed collection information on demand

### Collection Management Commands
- `collections list`: List all collections with workspace paths
- `collections info`: Show detailed information about a collection
- `collections delete`: Delete a collection
- `collections prune`: Remove old or unused collections

## Implementation Details

### Collection Metadata Storage
- Uses dedicated `code_index_metadata` collection for metadata storage
- Stores workspace paths, creation dates, and indexing information
- Implements UUID-based point IDs for Qdrant compliance

### Workspace Path Mapping
- Automatically maps collection names to filesystem paths
- Retrieves metadata during collection listing operations
- Falls back to hash-based naming for collections without metadata

### Collection Commands
- Integrated with main CLI as `code-index collections` subcommands
- Provides detailed collection information including status and statistics
- Supports collection deletion and pruning operations

## Usage

### Listing Collections
```bash
code-index collections list
```

Shows all collections with their associated workspace paths:
```
Name                           Points     Workspace Path
------------------------------------------------------------
ws-491a59846b84697a            124        /home/user/my-project
ws-a85371ec34f43f08            1271       /home/user/another-project
```

### Collection Information
```bash
code-index collections info ws-491a59846b84697a
```

Shows detailed information about a specific collection:
```
Collection: ws-491a59846b84697a
Status: green
Points: 124
Vectors: None
Workspace Path: /home/user/my-project
```

### Deleting Collections
```bash
code-index collections delete ws-491a59846b84697a
```

Deletes a specific collection after confirmation.

### Pruning Collections
```bash
code-index collections prune --older-than 30
```

Removes collections older than the specified number of days.

## Future Enhancements

### Collection Analytics
- Store language distribution and file type statistics
- Track indexing performance and timing information
- Maintain historical indexing data for trend analysis

### Advanced Pruning
- Automatic pruning based on usage patterns
- Space-based collection cleanup
- Smart collection archiving for infrequently accessed projects

### Collection Sharing
- Export/import collection metadata
- Share collections between team members
- Collection synchronization across multiple machines