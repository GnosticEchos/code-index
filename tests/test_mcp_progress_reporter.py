"""
Unit tests for MCP Progress Reporter.

Tests progress reporting functionality including ETA calculations,
batch operations, and MCP-compatible progress updates.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from src.code_index.mcp_server.core.progress_reporter import (
    ProgressReporter,
    ProgressUpdate,
    BatchProgressInfo
)


class TestProgressUpdate:
    """Test cases for ProgressUpdate dataclass."""
    
    def test_progress_update_creation(self):
        """Test creating ProgressUpdate with various parameters."""
        update = ProgressUpdate(
            operation_type="indexing",
            completed_items=50,
            total_items=100,
            current_item="processing file.py",
            elapsed_seconds=30.5,
            eta_seconds=25.2,
            status_message="Processing 50/100 items",
            progress_percentage=50.0,
            items_per_second=1.64,
            batch_info={"current_batch": 2, "total_batches": 5}
        )
        
        assert update.operation_type == "indexing"
        assert update.completed_items == 50
        assert update.total_items == 100
        assert update.current_item == "processing file.py"
        assert update.elapsed_seconds == 30.5
        assert update.eta_seconds == 25.2
        assert update.status_message == "Processing 50/100 items"
        assert update.progress_percentage == 50.0
        assert update.items_per_second == 1.64
        assert update.batch_info["current_batch"] == 2


class TestBatchProgressInfo:
    """Test cases for BatchProgressInfo dataclass."""
    
    def test_batch_progress_info_creation(self):
        """Test creating BatchProgressInfo with various parameters."""
        batch_info = BatchProgressInfo(
            current_batch=3,
            total_batches=10,
            batch_size=20,
            items_in_current_batch=15,
            batch_start_time=time.time(),
            batch_eta_seconds=120.5
        )
        
        assert batch_info.current_batch == 3
        assert batch_info.total_batches == 10
        assert batch_info.batch_size == 20
        assert batch_info.items_in_current_batch == 15
        assert batch_info.batch_start_time > 0
        assert batch_info.batch_eta_seconds == 120.5


class TestProgressReporter:
    """Test cases for ProgressReporter class."""
    
    @pytest.fixture
    def mock_callback(self):
        """Create a mock progress callback."""
        return AsyncMock()
    
    def test_progress_reporter_initialization(self):
        """Test ProgressReporter initialization."""
        reporter = ProgressReporter(
            total_items=100,
            operation_type="indexing",
            update_interval=10,
            min_update_interval=1.0
        )
        
        assert reporter.total_items == 100
        assert reporter.operation_type == "indexing"
        assert reporter.update_interval == 10
        assert reporter.min_update_interval == 1.0
        assert reporter.completed_items == 0
        assert reporter.current_item == ""
        assert reporter.batch_info is None
        assert len(reporter.recent_times) == 0
    
    def test_progress_reporter_with_callback(self, mock_callback):
        """Test ProgressReporter initialization with callback."""
        reporter = ProgressReporter(
            total_items=50,
            progress_callback=mock_callback
        )

        assert reporter.progress_callback is mock_callback
    
    @pytest.mark.asyncio
    async def test_update_progress_basic(self, mock_callback):
        """Test basic progress update."""
        reporter = ProgressReporter(
            total_items=100,
            update_interval=5,
            progress_callback=mock_callback
        )
        
        await reporter.update_progress(10, "processing file1.py")
        
        assert reporter.completed_items == 10
        assert reporter.current_item == "processing file1.py"
        assert len(reporter.recent_times) == 1
        
        # Should trigger callback due to interval
        mock_callback.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_progress_interval_triggering(self, mock_callback):
        """Test progress update interval triggering."""
        reporter = ProgressReporter(
            total_items=100,
            update_interval=10,
            progress_callback=mock_callback
        )
        
        # First update (should trigger - first item)
        await reporter.update_progress(1, "file1.py")
        assert mock_callback.call_count == 1
        
        # Updates within interval (should not trigger)
        mock_callback.reset_mock()
        await reporter.update_progress(5, "file5.py")
        assert mock_callback.call_count == 0
        
        # Update at interval (should trigger)
        await reporter.update_progress(11, "file11.py")
        assert mock_callback.call_count == 1
        
        # Last item (should trigger)
        mock_callback.reset_mock()
        await reporter.update_progress(100, "final_file.py")
        assert mock_callback.call_count == 1
    
    @pytest.mark.asyncio
    async def test_update_progress_time_based_triggering(self, mock_callback):
        """Test time-based progress update triggering."""
        reporter = ProgressReporter(
            total_items=100,
            update_interval=50,  # Large interval
            min_update_interval=0.1,  # Short time interval
            progress_callback=mock_callback
        )
        
        # First update
        await reporter.update_progress(1, "file1.py")
        mock_callback.reset_mock()
        
        # Wait for time interval and update
        await asyncio.sleep(0.15)
        await reporter.update_progress(2, "file2.py")
        
        # Should trigger due to time interval (and possibly first item trigger)
        assert mock_callback.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_start_batch_operation(self, mock_callback):
        """Test starting batch operation."""
        reporter = ProgressReporter(
            total_items=200,
            progress_callback=mock_callback
        )
        
        await reporter.start_batch_operation(
            total_batches=10,
            batch_size=20,
            batch_description="files"
        )
        
        assert reporter.batch_info is not None
        assert reporter.batch_info.total_batches == 10
        assert reporter.batch_info.batch_size == 20
        assert reporter.batch_info.current_batch == 0
        assert reporter.batch_info.items_in_current_batch == 0
        
        # Should trigger callback
        mock_callback.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_batch_progress(self, mock_callback):
        """Test updating batch progress."""
        reporter = ProgressReporter(
            total_items=200,
            progress_callback=mock_callback
        )
        
        # Start batch operation
        await reporter.start_batch_operation(10, 20)
        mock_callback.reset_mock()
        
        # Update batch progress
        await reporter.update_batch_progress(
            batch_num=3,
            items_in_batch=15,
            batch_description="processing batch 3"
        )
        
        assert reporter.batch_info.current_batch == 3
        assert reporter.batch_info.items_in_current_batch == 15
        assert "Batch 3/10" in reporter.current_item
        
        # Should trigger callback
        mock_callback.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_batch_progress_without_start(self, mock_callback):
        """Test updating batch progress without starting batch operation."""
        reporter = ProgressReporter(
            total_items=100,
            progress_callback=mock_callback
        )
        
        # Should handle gracefully
        await reporter.update_batch_progress(1, 10)
        
        # Should not crash and batch_info should remain None
        assert reporter.batch_info is None
    
    @pytest.mark.asyncio
    async def test_complete_batch(self, mock_callback):
        """Test completing a batch."""
        reporter = ProgressReporter(
            total_items=200,
            progress_callback=mock_callback
        )
        
        # Start batch operation
        await reporter.start_batch_operation(10, 20)
        
        # Complete first batch
        await reporter.complete_batch(1, 18)
        
        assert reporter.completed_items == 18
        assert len(reporter.batch_history) == 1
        
        batch_record = reporter.batch_history[0]
        assert batch_record["batch_num"] == 1
        assert batch_record["items_processed"] == 18
        assert batch_record["duration"] > 0
        assert batch_record["items_per_second"] >= 0
        
        # Should trigger callback
        mock_callback.assert_called()
    
    @pytest.mark.asyncio
    async def test_complete_batch_with_eta_calculation(self, mock_callback):
        """Test batch completion with ETA calculation."""
        reporter = ProgressReporter(
            total_items=200,
            progress_callback=mock_callback
        )
        
        # Start batch operation
        await reporter.start_batch_operation(5, 40)
        
        # Complete first batch (creates history for ETA)
        await reporter.complete_batch(1, 40)
        
        # Update second batch (should calculate ETA)
        await reporter.update_batch_progress(2, 20)
        
        # Should have ETA calculation based on first batch
        assert reporter.batch_info.batch_eta_seconds is not None
        assert reporter.batch_info.batch_eta_seconds > 0
    
    def test_calculate_eta_no_progress(self):
        """Test ETA calculation with no progress."""
        reporter = ProgressReporter(total_items=100)
        
        eta = reporter.calculate_eta(0, 10.0)
        assert eta is None
    
    def test_calculate_eta_completed(self):
        """Test ETA calculation when completed."""
        reporter = ProgressReporter(total_items=100)
        
        eta = reporter.calculate_eta(100, 50.0)
        assert eta is None
    
    def test_calculate_eta_with_recent_times(self):
        """Test ETA calculation using recent timing data."""
        reporter = ProgressReporter(total_items=100)
        
        # Simulate recent timing data
        current_time = time.time()
        reporter.recent_times = [
            current_time - 10.0,  # 10 seconds ago
            current_time - 8.0,   # 8 seconds ago
            current_time - 6.0,   # 6 seconds ago
            current_time - 4.0,   # 4 seconds ago
            current_time - 2.0,   # 2 seconds ago
            current_time          # now
        ]
        
        eta = reporter.calculate_eta(50, 30.0)
        
        assert eta is not None
        assert eta > 0
        # Should be reasonable (not too high or too low)
        assert eta < 1000
    
    def test_calculate_eta_fallback_to_average(self):
        """Test ETA calculation fallback to overall average."""
        reporter = ProgressReporter(total_items=100)
        
        # No recent times, should use overall average
        eta = reporter.calculate_eta(25, 10.0)
        
        assert eta is not None
        assert eta == 30.0  # (100-25) / (25/10) = 75 / 2.5 = 30
    
    def test_get_progress_summary_basic(self):
        """Test getting basic progress summary."""
        reporter = ProgressReporter(total_items=100, operation_type="testing")
        reporter.completed_items = 30
        reporter.current_item = "test_file.py"
        
        summary = reporter.get_progress_summary()
        
        assert summary["operation_type"] == "testing"
        assert summary["completed_items"] == 30
        assert summary["total_items"] == 100
        assert summary["progress_percentage"] == 30.0
        assert summary["current_item"] == "test_file.py"
        assert summary["elapsed_seconds"] >= 0
        assert summary["items_per_second"] >= 0
        assert "status" in summary
    
    def test_get_progress_summary_with_batch(self):
        """Test getting progress summary with batch information."""
        reporter = ProgressReporter(total_items=200)
        reporter.batch_info = BatchProgressInfo(
            current_batch=3,
            total_batches=10,
            batch_size=20,
            items_in_current_batch=15,
            batch_start_time=time.time(),
            batch_eta_seconds=120.0
        )
        
        summary = reporter.get_progress_summary()
        
        assert "batch_info" in summary
        batch_info = summary["batch_info"]
        assert batch_info["current_batch"] == 3
        assert batch_info["total_batches"] == 10
        assert batch_info["batch_progress_percentage"] == 30.0
        assert batch_info["items_in_current_batch"] == 15
        assert batch_info["batch_eta_seconds"] == 120.0
    
    def test_get_progress_summary_with_batch_performance(self):
        """Test progress summary with batch performance history."""
        reporter = ProgressReporter(total_items=200)
        reporter.batch_info = BatchProgressInfo(
            current_batch=3,
            total_batches=10,
            batch_size=20,
            items_in_current_batch=15,
            batch_start_time=time.time(),
            batch_eta_seconds=120.0
        )
        
        # Add batch history
        reporter.batch_history = [
            {"batch_num": 1, "duration": 10.0, "items_per_second": 2.0},
            {"batch_num": 2, "duration": 12.0, "items_per_second": 1.67},
        ]
        
        summary = reporter.get_progress_summary()
        
        assert "batch_performance" in summary
        perf = summary["batch_performance"]
        assert perf["average_batch_time"] == 11.0  # (10 + 12) / 2
        assert perf["average_items_per_second"] == 1.83  # (2.0 + 1.67) / 2 rounded to 2 decimals
        assert perf["completed_batches"] == 2
    
    def test_get_status_message_starting(self):
        """Test status message for starting operation."""
        reporter = ProgressReporter(total_items=100, operation_type="indexing")
        
        message = reporter._get_status_message()
        assert "Starting indexing" in message
    
    def test_get_status_message_in_progress(self):
        """Test status message for operation in progress."""
        reporter = ProgressReporter(total_items=100, operation_type="indexing")
        reporter.completed_items = 30
        
        message = reporter._get_status_message()
        assert "Processing 30/100" in message
        assert "30.0%" in message
    
    def test_get_status_message_completed(self):
        """Test status message for completed operation."""
        reporter = ProgressReporter(total_items=100, operation_type="indexing")
        reporter.completed_items = 100
        
        message = reporter._get_status_message()
        assert "Completed indexing" in message
    
    def test_get_status_message_with_batch(self):
        """Test status message with batch information."""
        reporter = ProgressReporter(total_items=200, operation_type="indexing")
        reporter.completed_items = 60
        reporter.batch_info = BatchProgressInfo(
            current_batch=3,
            total_batches=10,
            batch_size=20,
            items_in_current_batch=0,
            batch_start_time=time.time(),
            batch_eta_seconds=None
        )
        
        message = reporter._get_status_message()
        assert "Processing batch 3/10" in message
        assert "30.0%" in message
    
    def test_format_eta_seconds(self):
        """Test ETA formatting in seconds."""
        reporter = ProgressReporter(total_items=100)
        
        assert reporter.format_eta(30) == "30s"
        assert reporter.format_eta(45.7) == "45s"
    
    def test_format_eta_minutes(self):
        """Test ETA formatting in minutes."""
        reporter = ProgressReporter(total_items=100)
        
        assert reporter.format_eta(90) == "1m 30s"
        assert reporter.format_eta(125) == "2m 5s"
        assert reporter.format_eta(3540) == "59m 0s"
    
    def test_format_eta_hours(self):
        """Test ETA formatting in hours."""
        reporter = ProgressReporter(total_items=100)
        
        assert reporter.format_eta(3600) == "1h 0m"
        assert reporter.format_eta(3665) == "1h 1m"
        assert reporter.format_eta(7325) == "2h 2m"
    
    def test_format_eta_none(self):
        """Test ETA formatting with None value."""
        reporter = ProgressReporter(total_items=100)
        
        assert reporter.format_eta(None) == "Unknown"
    
    def test_format_progress_for_mcp(self):
        """Test formatting progress for MCP client."""
        reporter = ProgressReporter(total_items=100, operation_type="indexing")
        reporter.completed_items = 40
        reporter.current_item = "processing file.py"
        
        mcp_progress = reporter.format_progress_for_mcp()
        
        assert mcp_progress["type"] == "progress_update"
        assert mcp_progress["operation"] == "indexing"
        
        progress = mcp_progress["progress"]
        assert progress["completed"] == 40
        assert progress["total"] == 100
        assert progress["percentage"] == 40.0
        assert progress["current"] == "processing file.py"
        
        timing = mcp_progress["timing"]
        assert "elapsed" in timing
        assert "eta" in timing
        assert "rate" in timing
        
        assert "status" in mcp_progress
        assert "timestamp" in mcp_progress
    
    def test_format_progress_for_mcp_with_batch(self):
        """Test formatting progress for MCP client with batch info."""
        reporter = ProgressReporter(total_items=200, operation_type="indexing")
        reporter.completed_items = 80
        reporter.batch_info = BatchProgressInfo(
            current_batch=4,
            total_batches=10,
            batch_size=20,
            items_in_current_batch=0,
            batch_start_time=time.time(),
            batch_eta_seconds=60.0
        )
        
        mcp_progress = reporter.format_progress_for_mcp()
        
        assert "batch" in mcp_progress
        batch = mcp_progress["batch"]
        assert batch["current"] == 4
        assert batch["total"] == 10
        assert batch["percentage"] == 40.0
        assert batch["eta"] == "1m 0s"
    
    @pytest.mark.asyncio
    async def test_send_progress_update_success(self, mock_callback):
        """Test successful progress update sending."""
        reporter = ProgressReporter(
            total_items=100,
            progress_callback=mock_callback
        )
        
        await reporter._send_progress_update()
        
        mock_callback.assert_called_once()
        
        # Check the update object passed to callback
        call_args = mock_callback.call_args[0]
        update = call_args[0]
        
        assert isinstance(update, ProgressUpdate)
        assert update.operation_type == "indexing"
        assert update.total_items == 100
    
    @pytest.mark.asyncio
    async def test_send_progress_update_callback_error(self, mock_callback):
        """Test progress update with callback error."""
        mock_callback.side_effect = Exception("Callback error")
        
        reporter = ProgressReporter(
            total_items=100,
            progress_callback=mock_callback
        )
        
        # Should not raise exception, just log error
        await reporter._send_progress_update()
        
        mock_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_progress_update_no_callback(self):
        """Test progress update without callback."""
        reporter = ProgressReporter(total_items=100)
        
        # Should not raise exception
        await reporter._send_progress_update()


class TestProgressReporterIntegration:
    """Integration tests for progress reporter."""
    
    @pytest.mark.asyncio
    async def test_complete_indexing_workflow(self):
        """Test complete indexing workflow with progress reporting."""
        progress_updates = []
        
        async def capture_progress(update):
            progress_updates.append(update)
        
        reporter = ProgressReporter(
            total_items=50,
            operation_type="indexing",
            update_interval=5,
            progress_callback=capture_progress
        )
        
        # Simulate indexing workflow
        for i in range(1, 51):
            await reporter.update_progress(i, f"file_{i}.py")
            
            # Small delay to simulate processing
            if i % 10 == 0:
                await asyncio.sleep(0.01)
        
        # Should have received multiple progress updates
        assert len(progress_updates) > 0
        
        # Check first and last updates
        first_update = progress_updates[0]
        assert first_update.completed_items >= 0
        assert first_update.total_items == 50
        
        last_update = progress_updates[-1]
        assert last_update.completed_items == 50
        assert last_update.progress_percentage == 100.0
    
    @pytest.mark.asyncio
    async def test_batch_processing_workflow(self):
        """Test batch processing workflow with progress reporting."""
        progress_updates = []
        
        async def capture_progress(update):
            progress_updates.append(update)
        
        reporter = ProgressReporter(
            total_items=100,
            operation_type="batch_indexing",
            progress_callback=capture_progress
        )
        
        # Start batch operation
        await reporter.start_batch_operation(5, 20, "files")
        
        # Process batches
        for batch_num in range(1, 6):
            # Update batch progress
            await reporter.update_batch_progress(
                batch_num=batch_num,
                items_in_batch=20,
                batch_description=f"processing batch {batch_num}"
            )
            
            # Complete batch
            await reporter.complete_batch(batch_num, 20)
            
            # Small delay
            await asyncio.sleep(0.01)
        
        # Should have received progress updates
        assert len(progress_updates) > 0
        
        # Final state should show completion
        final_summary = reporter.get_progress_summary()
        assert final_summary["completed_items"] == 100
        assert len(reporter.batch_history) == 5
        
        # All batches should be recorded
        for i, batch_record in enumerate(reporter.batch_history):
            assert batch_record["batch_num"] == i + 1
            assert batch_record["items_processed"] == 20


if __name__ == "__main__":
    pytest.main([__file__])