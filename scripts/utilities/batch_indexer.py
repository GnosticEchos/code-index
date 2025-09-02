#!/usr/bin/env python3
"""
Enhanced batch indexer for multiple codebases with flexible workspace input options.
"""
import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path
import click


# Configuration template
CONFIG_TEMPLATE = {
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "nomic-embed-text:latest",
    "qdrant_url": "http://localhost:6333",
    "embedding_length": 768,
    "chunking_strategy": "lines",
    "token_chunk_size": 1000,
    "token_chunk_overlap": 200,
    "auto_extensions": False,
    "exclude_files_path": None,
    "timeout_log_path": "timeout_files.txt",
    "max_file_size_bytes": 1048576,
    "batch_segment_threshold": 60,
    "search_min_score": 0.4,
    "search_max_results": 50,
    "use_tree_sitter": False,
    "tree_sitter_max_file_size_bytes": 524288,
    "tree_sitter_skip_test_files": True,
    "tree_sitter_skip_examples": True
}


@click.command()
@click.option('--workspace-list', '-w', type=click.Path(exists=True), 
              help='Path to file containing newline-delimited workspace paths')
@click.option('--workspace', '-W', multiple=True, 
              help='Workspace paths (can be specified multiple times)')
@click.option('--config', '-c', type=click.Path(), default='code_index.json',
              help='Configuration file template')
@click.option('--embed-timeout', '-t', type=int, default=600,
              help='Embedding timeout in seconds')
@click.option('--concurrent', '-C', is_flag=True,
              help='Enable concurrent indexing (default: sequential)')
@click.option('--delay', '-d', type=int, default=30,
              help='Delay between workspaces in seconds (default: 30)')
@click.option('--resume', '-r', is_flag=True,
              help='Resume from last failed workspace')
@click.option('--dry-run', is_flag=True,
              help='Show what would be indexed without actually indexing')
def batch_indexer(workspace_list, workspace, config, embed_timeout, concurrent, delay, resume, dry_run):
    """Batch index multiple workspaces with flexible input options.
    
    Examples:
      # From file with workspace paths
      python batch_indexer.py --workspace-list workspaces.txt
      
      # Multiple workspaces as arguments
      python batch_indexer.py --workspace /path/a --workspace /path/b
      
      # With custom config and tree-sitter
      python batch_indexer.py --workspace-list ws.txt --config my_config.json --embed-timeout 1200
      
      # Resume from failure point
      python batch_indexer.py --workspace-list ws.txt --resume
    """
    print("=== Enhanced Batch Code Indexer ===")
    print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get list of workspaces
    workspaces = get_workspace_list(workspace_list, workspace)
    
    if not workspaces:
        print("❌ No workspaces to index")
        return
    
    print(f"Workspaces to index: {len(workspaces)}")
    
    # Create log file
    timestamp = int(time.time())
    log_file = f"batch_index_log_{timestamp}.txt"
    output_file = f"batch_index_output_{timestamp}.log"
    
    print(f"Log file: {log_file}")
    print(f"Output file: {output_file}")
    
    # Initialize log file
    with open(log_file, 'w') as f:
        f.write("Enhanced Batch Indexing Log\\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
        f.write(f"Workspaces: {len(workspaces)}\\n")
        f.write(f"Embed timeout: {embed_timeout}s\\n")
        f.write(f"Concurrent: {concurrent}\\n")
        f.write("=" * 80 + "\\n")
        
        for i, ws in enumerate(workspaces, 1):
            f.write(f"{i:3d}. {ws}\\n")
        f.write("=" * 80 + "\\n")
    
    if dry_run:
        print("📋 DRY RUN - Would index the following workspaces:")
        for i, ws in enumerate(workspaces, 1):
            print(f"  {i:2d}. {ws}")
        return
    
    # Index workspaces
    successful = 0
    failed = 0
    failed_workspaces = []
    
    start_index = 0
    if resume and os.path.exists("batch_failed_workspaces.txt"):
        try:
            with open("batch_failed_workspaces.txt", "r") as f:
                last_failed = f.read().strip()
                if last_failed in workspaces:
                    start_index = workspaces.index(last_failed)
                    print(f"🔄 Resuming from workspace {start_index + 1}: {last_failed}")
        except Exception as e:
            print(f"⚠️  Could not resume from failed workspaces file: {e}")
    
    for i, workspace_path in enumerate(workspaces[start_index:], start_index + 1):
        print(f"\\n[{i}/{len(workspaces)}] Processing workspace...")
        
        # Check if directory exists
        if not os.path.exists(workspace_path):
            print(f"  ⚠️ Directory not found: {workspace_path}")
            with open(log_file, 'a') as f:
                f.write(f"\\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SKIPPED (not found): {workspace_path}\\n")
            failed += 1
            failed_workspaces.append(workspace_path)
            continue
            
        # Index the workspace
        success = index_workspace(workspace_path, config, embed_timeout, log_file, output_file)
        if success:
            successful += 1
        else:
            failed += 1
            failed_workspaces.append(workspace_path)
            # Save failed workspace for resume
            with open("batch_failed_workspaces.txt", "w") as f:
                f.write(workspace_path)
            
        # Brief pause between workspaces (unless concurrent)
        if i < len(workspaces) and not concurrent and delay > 0:
            print(f"  Waiting {delay} seconds before next workspace...")
            time.sleep(delay)
    
    # Clean up resume file if all successful
    if successful == len(workspaces) and os.path.exists("batch_failed_workspaces.txt"):
        try:
            os.remove("batch_failed_workspaces.txt")
        except:
            pass
    
    # Summary
    print(f"\\n=== Batch Indexing Complete ===")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Log file: {log_file}")
    print(f"Output file: {output_file}")
    
    if failed_workspaces:
        failed_file = f"batch_failed_workspaces_{timestamp}.txt"
        with open(failed_file, 'w') as f:
            for ws in failed_workspaces:
                f.write(f"{ws}\\n")
        print(f"Failed workspaces list: {failed_file}")
    
    with open(log_file, 'a') as f:
        f.write(f"\\n=== Batch Indexing Complete ===\\n")
        f.write(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
        f.write(f"Successful: {successful}\\n")
        f.write(f"Failed: {failed}\\n")


def get_workspace_list(workspace_list_file, workspace_args):
    """Get list of workspaces from file and/or arguments."""
    workspaces = []
    
    # From file
    if workspace_list_file:
        try:
            with open(workspace_list_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        workspaces.append(os.path.expanduser(line))
        except Exception as e:
            print(f"⚠️  Error reading workspace list file: {e}")
    
    # From arguments
    for ws in workspace_args:
        workspaces.append(os.path.expanduser(ws))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_workspaces = []
    for ws in workspaces:
        if ws not in seen:
            seen.add(ws)
            unique_workspaces.append(ws)
    
    return unique_workspaces


def create_workspace_config(workspace_path, template_config_path):
    """Create a configuration file for a workspace based on template."""
    # If we have a template config, don't create a workspace-specific one
    if template_config_path and os.path.exists(template_config_path):
        return template_config_path
    
    # Otherwise, create workspace-specific config
    config = CONFIG_TEMPLATE.copy()
    
    # Load template config if provided
    if template_config_path and os.path.exists(template_config_path):
        try:
            with open(template_config_path, 'r') as f:
                template = json.load(f)
            config.update(template)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not load template config: {e}")
    
    # Set workspace-specific values
    config["workspace_path"] = workspace_path
    
    # Create config file in workspace directory
    config_file = os.path.join(workspace_path, "code_index.json")
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"  ⚠️  Warning: Could not create config file: {e}")
        return None
    
    return config_file


def index_workspace(workspace_path, config_template, embed_timeout, log_file, output_file):
    """Index a single workspace."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Indexing: {workspace_path}")
    
    # Change to workspace directory
    original_cwd = os.getcwd()
    os.chdir(workspace_path)
    
    try:
        # Use the provided config template directly
        config_file = config_template if config_template and os.path.exists(config_template) else None
        
        # Prepare timeout log file
        timestamp = int(time.time())
        timeout_log = f"timeout_files_{os.path.basename(workspace_path)}_{timestamp}.txt"
        
        # Run indexing command
        cmd = [
            sys.executable, "-m", "code_index.cli", 
            "index"
        ]
        
        # Add config if available
        if config_file:
            cmd.extend(["--config", config_file])
        
        # Add timeout
        cmd.extend(["--embed-timeout", str(embed_timeout)])
        
        # Add timeout log
        cmd.extend(["--timeout-log", timeout_log])
        
        print(f"  Command: {' '.join(cmd)}")
        
        if "--dry-run" in sys.argv:
            print(f"  📋 Dry run - would execute: {' '.join(cmd)}")
            return True
        
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=embed_timeout * 2  # Double timeout for safety
        )
        
        # Save output to file
        with open(output_file, 'a') as f:
            f.write(f"\\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Workspace: {workspace_path}\\n")
            f.write(f"Return code: {result.returncode}\\n")
            if result.stdout:
                f.write(f"STDOUT:\\n{result.stdout}\\n")
            if result.stderr:
                f.write(f"STDERR:\\n{result.stderr}\\n")
            f.write("-" * 80 + "\\n")
        
        if result.returncode == 0:
            print(f"  ✓ Success: {workspace_path}")
        else:
            print(f"  ✗ Failed: {workspace_path} (exit code: {result.returncode})")
            # Print error details for troubleshooting
            if result.stderr:
                print(f"    Error details: {result.stderr[:200]}...")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"  ⏱️ Timeout: {workspace_path}")
        with open(log_file, 'a') as f:
            f.write(f"\\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] TIMEOUT: {workspace_path}\\n")
            f.write("-" * 80 + "\\n")
        return False
    except Exception as e:
        print(f"  ❌ Error: {workspace_path} ({e})")
        with open(log_file, 'a') as f:
            f.write(f"\\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {workspace_path}\\n")
            f.write(f"Exception: {e}\\n")
            f.write("-" * 80 + "\\n")
        return False
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    batch_indexer()