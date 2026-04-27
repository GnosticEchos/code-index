#!/usr/bin/env python3
"""
Test TUI integration with actual indexing service.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from code_index.ui.tui_integration import TUIInterface
from code_index.errors import ErrorHandler

def test_tui_integration():
    """Test TUI integration with indexing service."""
    print("Testing TUI integration with indexing service...")
    
    try:
        error_handler = ErrorHandler()
        tui_interface = TUIInterface(error_handler)
        
        # Test starting indexing with TUI
        print("Starting TUI indexing...")
        # Test TUI progress display
        total_files = 10
        overall_task_id = tui_interface.start_indexing(total_files)
        
        # Verify task was created
        assert overall_task_id is not None, "Failed to create overall task"
        
        # Simulate progress updates
        for i in range(total_files):
            tui_interface.update_indexing_progress(
                overall_task_id=overall_task_id,
                completed_files=i + 1,
                total_files=total_files,
                current_file=f"file_{i}.py",
                speed=100.0,
                eta=5.0,
                total_blocks=50,
                processed_blocks=i * 5,
                language_info="Python"
            )
        
        tui_interface.close()
        print("TUI indexing completed successfully")
        
    except Exception as e:
        print(f"TUI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print("Running TUI integration test...")
    success = test_tui_integration()
    print(f"TUI integration: {'PASS' if success else 'FAIL'}")