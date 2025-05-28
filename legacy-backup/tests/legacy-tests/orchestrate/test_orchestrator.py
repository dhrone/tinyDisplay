"""
Tests for the RenderOrchestrator class.
"""

import unittest
from unittest.mock import MagicMock, patch
import time
from PIL import Image

from tinyDisplay.dependency.manager import DependencyManager
from tinyDisplay.orchestrate.orchestrator import RenderOrchestrator
from tinyDisplay.dependency.protocols import ChangeEventProtocol


class MockCanvas:
    """Mock canvas for testing."""
    
    def __init__(self):
        self.render_calls = 0
        self.test_image = Image.new('RGB', (100, 100), color='black')
    
    def render(self):
        """Return a test image and mark as changed."""
        self.render_calls += 1
        return self.test_image, True


class MockEvent(ChangeEventProtocol):
    """Mock event for testing."""
    
    def __init__(self, source=None):
        self.source = source or object()
        self.timestamp = time.time()
        
    @property
    def event_source(self):
        return self.source
    
    @property
    def event_timestamp(self):
        return self.timestamp


class TestRenderOrchestrator(unittest.TestCase):
    """Test cases for the RenderOrchestrator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.dependency_manager = DependencyManager()
        self.dataset = {}
        self.canvas = MockCanvas()
        
        # Patch multiprocessing.Process to avoid actual process creation in tests
        self.process_patcher = patch('tinyDisplay.orchestrate.orchestrator.multiprocessing.Process')
        self.mock_process = self.process_patcher.start()
        
        # Create instance with reduced worker count for testing
        self.orchestrator = RenderOrchestrator(
            self.dependency_manager,
            self.dataset,
            self.canvas,
            max_queue_size=5,
            mode="threading"  # Use threading mode to enable worker creation
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.process_patcher.stop()
        
        # Clean up orchestrator
        if hasattr(self, 'orchestrator'):
            self.orchestrator.shutdown()
    
    def test_initialization(self):
        """Test that the orchestrator initializes correctly."""
        self.orchestrator.initialize(worker_count=2)
        
        # Check that worker processes were started
        self.assertEqual(len(self.orchestrator.workers), 2)
        self.assertEqual(len(self.orchestrator.worker_command_queues), 2)
        
    def test_render_next_frame_empty_queue(self):
        """Test rendering when queue is empty."""
        # Import the Empty exception that orchestrator is expecting
        from queue import Empty
        
        # Save original queue
        original_queue = self.orchestrator.render_queue
        
        try:
            # Mock empty queue
            self.orchestrator.render_queue = MagicMock()
            self.orchestrator.render_queue.get_nowait.side_effect = Empty()
            
            # Call render_next_frame
            result = self.orchestrator.render_next_frame(1)
            
            # Should fall back to synchronous rendering
            self.assertEqual(result, self.canvas.test_image)
        finally:
            # Restore original queue for proper cleanup
            self.orchestrator.render_queue = original_queue
        self.assertEqual(self.canvas.render_calls, 1)
    
    def test_handle_state_change(self):
        """Test handling of state changes."""
        # Import the Empty exception that orchestrator is expecting
        from queue import Empty
        
        # Save original queue
        original_queue = self.orchestrator.render_queue
        
        try:
            # Mock queue with some items
            mock_queue = MagicMock()
            # Provide enough items in side_effect for both the test and the teardown
            mock_queue.get_nowait.side_effect = [
                MagicMock(), MagicMock(), Empty(), Empty(), Empty(), Empty()
            ]
            self.orchestrator.render_queue = mock_queue
            
            # Trigger state change
            event = MockEvent()
            self.orchestrator.handle_state_change(event)
            
            # Should have tried to get items from queue
            self.assertEqual(mock_queue.get_nowait.call_count, 3)
        finally:
            # Restore original queue for proper cleanup
            self.orchestrator.render_queue = original_queue
    
    def test_shutdown(self):
        """Test proper shutdown of orchestrator."""
        # Initialize with mock workers
        self.orchestrator.initialize(worker_count=2)
        
        # Mock workers and command queues
        self.orchestrator.workers = [MagicMock() for _ in range(2)]
        for worker_id in self.orchestrator.worker_command_queues:
            self.orchestrator.worker_command_queues[worker_id] = MagicMock()
        
        # Mock heartbeat monitor
        self.orchestrator._heartbeat_monitor = MagicMock()
        self.orchestrator._heartbeat_monitor.is_alive.return_value = True
        
        # Shutdown
        self.orchestrator.shutdown()
        
        # Verify heartbeat stop event was set
        self.assertTrue(self.orchestrator._heartbeat_stop_event.is_set())
        
        # Verify all workers were joined
        for worker in self.orchestrator.workers:
            worker.join.assert_called_once()


if __name__ == '__main__':
    unittest.main()
