"""
Tests for error handling in the dependency management system.
"""

import unittest
from unittest.mock import MagicMock
from typing import List

from tinyDisplay.dependency.manager import DependencyManager
from tinyDisplay.dependency.events import ChangeEvent
from tinyDisplay.dependency.protocols import ChangeProcessorProtocol, ChangeEventProtocol

class TestDependencyErrorHandling(unittest.TestCase):
    """Test error handling and edge cases in the dependency management system."""
    
    def setUp(self):
        self.manager = DependencyManager()
        self.observable = MockObservable(self.manager, "test_observable")
        self.dependent = CountingDependent("test_dependent")
    
    def test_duplicate_registration(self):
        """Test that duplicate registrations are handled gracefully."""
        # First registration should succeed
        self.manager.register(self.dependent, self.observable)
        
        # Second registration should be a no-op or handled gracefully
        self.manager.register(self.dependent, self.observable)
        
        # Should still be able to receive events
        self.observable.change("test_event")
        self.manager.dispatch_events()
        
        self.assertEqual(self.dependent.count, 1)
    
    def test_unregister_nonexistent(self):
        """Test unregistering a non-existent dependency."""
        # This should not raise an error
        self.manager.unregister(self.dependent, self.observable)
        
        # Register and then unregister
        self.manager.register(self.dependent, self.observable)
        self.manager.unregister(self.dependent, self.observable)
        
        # Unregister again should be a no-op
        self.manager.unregister(self.dependent, self.observable)
    
    def test_invalid_observable(self):
        """Test registering with an invalid observable."""
        with self.assertRaises(TypeError):
            self.manager.register(self.dependent, None)
    
    def test_invalid_dependent(self):
        """Test registering with an invalid dependent."""
        with self.assertRaises(TypeError):
            self.manager.register(None, self.observable)
    
    def test_event_processing_error(self):
        """Test that errors in event processing don't break the system."""
        class FailingDependent(ChangeProcessorProtocol):
            def process_change(self, events):
                raise ValueError("Simulated error in event processing")
        
        # Create a dependent that will fail
        failing_dep = FailingDependent()
        
        # Also create a working dependent to verify it still works
        working_dep = CountingDependent("working")
        
        # Register both
        self.manager.register(failing_dep, self.observable)
        self.manager.register(working_dep, self.observable)
        
        # This should not raise
        self.observable.change("test_event")
        
        # The working dependent should still receive the event
        self.manager.dispatch_events()
        self.assertEqual(working_dep.count, 1)


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, manager: DependencyManager, name: str = "mock"):
        self.manager = manager
        self.name = name
    
    def change(self, event_type: str = "changed"):
        """Raise a change event."""
        event = ChangeEvent(event_type=event_type, source=self)
        self.manager.raise_event(event)


class CountingDependent(ChangeProcessorProtocol):
    """A dependent that simply counts processed events."""
    
    def __init__(self, name: str = "counter"):
        self.name = name
        self.count = 0
        self.last_events: List[ChangeEventProtocol] = []
    
    def process_change(self, events: List[ChangeEventProtocol]):
        self.count += 1
        self.last_events = events
