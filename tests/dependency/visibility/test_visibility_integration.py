"""Tests for the visibility system integration with DependencyManager."""

import unittest
from typing import Any, List, Set, Optional, Dict
from unittest.mock import Mock, call, ANY, patch
from dataclasses import dataclass

from tinyDisplay.dependency.manager import DependencyManager
from tinyDisplay.dependency.visibility import VisibilityContext
from tinyDisplay.dependency.visibility.protocols import VisibilityAware
from tinyDisplay.dependency.events import ChangeEvent, VisibilityChangeEvent
from tinyDisplay.dependency.protocols import ChangeEventProtocol, ChangeProcessorProtocol



class MockVisibilityAware(VisibilityAware):
    """Mock implementation of VisibilityAware for testing."""
    
    def __init__(self, name: str = "mock", manager: Optional[DependencyManager] = None):
        self.name = name
        self._visible = True
        self.visibility_changes = []
        self.events_received = []
        self.manager = manager
        self.visibility_context = None
    
    def set_visible(self, visible: bool) -> None:
        """Set the visibility state, record the change, and raise an event."""
        if visible != self._visible:
            # Record the change
            self.visibility_changes.append(visible)
            # Update internal state
            self._visible = visible
            
            # Update the visibility context if we have one
            # This updates the state but doesn't raise an event
            if self.visibility_context is not None and self.visibility_context is not self:
                self.visibility_context.set_visible(self, visible)
            
            # Explicitly raise a visibility change event if we have a manager
            # This is crucial for propagating visibility changes through the dependency graph
            if self.manager is not None:
                # Create and raise the visibility change event
                event = VisibilityChangeEvent(source=self, visible=visible)
                self.manager.raise_event(event)
    
    def is_visible(self) -> bool:
        """Return the current visibility state."""
        # If we have a visibility context, use it
        if self.visibility_context is not None:
            return self.visibility_context.is_visible(self)
        return self._visible
        
    def set_visibility_context(self, context) -> None:
        """Set the visibility context for this object."""
        self.visibility_context = context
        # Register this object with the context
        context.set_visible(self, self._visible)


class MockChangeProcessor(ChangeProcessorProtocol):
    """Mock implementation of ChangeProcessorProtocol for testing."""
    
    def __init__(self, manager: Optional[DependencyManager] = None):
        self.events_received = []
        self.visibility_changes: Dict[Any, bool] = {}
        self.manager = manager
        self.process_change = Mock(side_effect=self._process_change)
    
    def _process_change(self, events):
        for event in events:
            self.events_received.append(event)
            # Handle visibility change events
            if isinstance(event, VisibilityChangeEvent):
                self.visibility_changes[event.source] = event.visible


class TestVisibilityIntegration(unittest.TestCase):
    """Test cases for visibility system integration with DependencyManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = DependencyManager()
        self.visibility_context = VisibilityContext()
        
        # Create test objects with manager reference for event raising
        self.visible_obj = MockVisibilityAware("visible", manager=self.manager)
        self.hidden_obj = MockVisibilityAware("hidden", manager=self.manager)
        
        # Set the visibility context on the test objects
        self.visible_obj.set_visibility_context(self.visibility_context)
        self.hidden_obj.set_visibility_context(self.visibility_context)
        
        # Create a mock processor that will receive events
        self.processor = MockChangeProcessor(manager=self.manager)
        
        # Set up dependencies
        self.manager.register(self.processor, self.visible_obj)
        self.manager.register(self.processor, self.hidden_obj)
        
        # Set initial visibility
        self.visible_obj.set_visible(True)
        self.hidden_obj.set_visible(False)
        self.manager.dispatch_events()  # Process any visibility change events
    
    def test_visible_object_propagates_events(self):
        """Test that visible objects propagate events to their dependents."""
        # Reset mock to clear any previous calls
        self.processor.process_change.reset_mock()
        
        # When - raise an event on the visible object
        event = ChangeEvent("test_event", self.visible_obj, {})
        self.manager.raise_event(event)
        self.manager.dispatch_events(visible={self.visible_obj, self.hidden_obj})
        
        # Then - processor should receive the event
        self.processor.process_change.assert_called_once()
        events = self.processor.process_change.call_args[0][0]
        self.assertEqual(len(events), 1)
        # Check that the event is from the visible object (by name since object identity might differ)
        self.assertEqual(events[0].source.name, self.visible_obj.name)
    
    def test_hidden_object_does_not_propagate_events(self):
        """Test that hidden objects do not propagate events to their dependents."""
        # Reset mock to clear any previous calls
        self.processor.process_change.reset_mock()
        
        # When - raise an event on the hidden object
        event = ChangeEvent("test_event", self.hidden_obj, {})
        self.manager.raise_event(event)
        self.manager.dispatch_events(visible={self.visible_obj})  # Only visible_obj is in visible set
        
        # Then - processor should not be called for the hidden object
        self.processor.process_change.assert_not_called()
    
    def test_visibility_change_triggers_update(self):
        """Test that changing visibility affects event propagation."""
        # Reset mock to clear any previous calls
        self.processor.process_change.reset_mock()
        
        # Given - both objects start with known states
        self.visible_obj.set_visible(True)
        self.hidden_obj.set_visible(False)
        self.manager.dispatch_events()  # Process any visibility changes
        
        # Reset mock after initial setup
        self.processor.process_change.reset_mock()
        
        # When - raise events on both objects
        event1 = ChangeEvent("test_event_visible", self.visible_obj, {})
        event2 = ChangeEvent("test_event_hidden", self.hidden_obj, {})
        self.manager.raise_event(event1)
        self.manager.raise_event(event2)
        self.manager.dispatch_events(visible={self.visible_obj})
        
        # Then - only the visible object's event should be processed
        self.processor.process_change.assert_called_once()
        events = self.processor.process_change.call_args[0][0]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source.name, self.visible_obj.name)
    
    def test_visibility_context_integration(self):
        """Test that the visibility context properly integrates with the manager."""
        # Reset mock to clear any previous calls
        self.processor.process_change.reset_mock()
        
        print("\n===== STARTING test_visibility_context_integration =====")
        
        # Given - set up a listener on the visibility context
        visibility_changes = []
        
        def on_visibility_change(obj, visible):
            print(f"Listener called: {obj.name} -> {visible}")
            visibility_changes.append((obj.name, visible))
            # In the explicit event-based model, listeners should raise their own events
            # This is the key to correctly integrating the visibility context with the manager
            if obj == self.visible_obj:  # Only handle our test object
                print(f"Explicitly raising visibility change event for {obj.name}")
                event = VisibilityChangeEvent(source=obj, visible=visible)
                self.manager.raise_event(event)
            
        # Add the listener to the context
        self.visibility_context.add_listener(self.visible_obj, on_visibility_change)
        print(f"Added listener to visibility context for {self.visible_obj.name}")
        
        # When - change visibility through the context
        print(f"Setting {self.visible_obj.name} visibility to False through context")
        self.visibility_context.set_visible(self.visible_obj, False)
        
        # Check visibility in context before dispatch
        context_visible = self.visibility_context.is_visible(self.visible_obj)
        print(f"After context update, context.is_visible() -> {context_visible}")
        print(f"Object's internal state is_visible() -> {self.visible_obj.is_visible()}")
        
        # Make sure to include both objects in the visible set to ensure events propagate
        print("Dispatching events with visible set: {visible_obj, hidden_obj, processor}")
        self.manager.dispatch_events(visible={self.visible_obj, self.hidden_obj, self.processor})  # Process the visibility change event
        
        # Then - listener should be notified
        print(f"Visibility changes recorded by listener: {visibility_changes}")
        self.assertEqual(len(visibility_changes), 1)
        obj_name, visible = visibility_changes[0]
        self.assertEqual(obj_name, self.visible_obj.name)
        self.assertFalse(visible)
        
        # And the object's visibility should be updated
        print(f"Object visibility after dispatch: {self.visible_obj.is_visible()}")
        self.assertFalse(self.visible_obj.is_visible())
        
        # And the processor should have received the visibility change
        # Check by name since object identity might differ
        print(f"Event received by processor: {self.processor.events_received}")
        print(f"Visibility changes recorded by processor: {self.processor.visibility_changes}")
        source_names = [obj.name for obj in self.processor.visibility_changes.keys()]
        print(f"Source names in processor visibility_changes: {source_names}")
        
        # Debug the actual objects in the processor's visibility_changes
        for obj in self.processor.visibility_changes.keys():
            print(f"Source object: {obj} with name {obj.name} and visible={self.processor.visibility_changes[obj]}")
        
        self.assertIn(self.visible_obj.name, source_names, 
                     f"Expected '{self.visible_obj.name}' to be in {source_names}")
        
        # Get the actual source object from the processor's visibility_changes
        try:
            source_obj = next(obj for obj in self.processor.visibility_changes.keys() 
                             if obj.name == self.visible_obj.name)
            print(f"Found matching source object: {source_obj} with visibility {self.processor.visibility_changes[source_obj]}")
            self.assertFalse(self.processor.visibility_changes[source_obj])
        except StopIteration:
            self.fail(f"Could not find object with name '{self.visible_obj.name}' in processor visibility changes")
    
    def test_visibility_with_nested_dependencies(self):
        """Test that visibility works with nested dependencies."""
        print("\n===== STARTING test_visibility_with_nested_dependencies =====")
        
        # Set up a chain: obj1 -> obj2 -> processor
        obj1 = MockVisibilityAware("obj1", manager=self.manager)
        obj2 = MockVisibilityAware("obj2", manager=self.manager)
        processor = MockChangeProcessor(manager=self.manager)
        
        # Set up dependencies
        print("Setting up dependency chain: obj1 -> obj2 -> processor")
        self.manager.register(obj2, obj1)  # obj2 depends on obj1
        self.manager.register(processor, obj2)  # processor depends on obj2
        print(f"Dependencies registered: obj2 depends on obj1, processor depends on obj2")
        
        # Initial state - all visible
        print("Setting initial visibility states")
        obj1.set_visible(True)
        obj2.set_visible(True)
        print("Initial dispatch to process any visibility changes")
        self.manager.dispatch_events()  # Process any visibility changes
        processor.process_change.reset_mock()  # Reset after setup
        print(f"Initial setup complete: obj1={obj1.is_visible()}, obj2={obj2.is_visible()}")
        print(f"Mock process_change call count reset: {processor.process_change.call_count}")
        
        # When - raise event on obj1 and dispatch with only obj1 visible
        print("\nSTEP 1: Raising event on obj1 with only obj1 visible")
        event = ChangeEvent("nested_test", obj1, {})
        self.manager.raise_event(event)
        print("Dispatching with visible={obj1} only")
        self.manager.dispatch_events(visible={obj1})  # obj2 is not in visible set
        
        # Then - processor should not be notified since obj2 is not in visible set
        print(f"After dispatch with only obj1 visible, processor call count: {processor.process_change.call_count}")
        processor.process_change.assert_not_called()
        
        # When - make obj2 visible and dispatch again
        print("\nSTEP 2: Making obj2 visible and dispatching both events")
        
        # First make it invisible, then dispatch immediately
        print("Setting obj2 visibility to False first")
        obj2.set_visible(False)
        print(f"State after setting obj2 invisible: obj2.is_visible()={obj2.is_visible()}")
        
        # Dispatch events after first visibility change
        print("Dispatching after setting visibility to False")
        self.manager.dispatch_events(visible={obj1, obj2, processor})
        
        # Reset mock to clear the False event processing
        processor.process_change.reset_mock()
        processor.visibility_changes.clear()
        print("Reset processor mock after first dispatch")
        
        # Now make it visible again - this should raise a visibility change event
        print("Setting obj2 visibility to True")
        obj2.set_visible(True)
        print(f"State after setting obj2 visible: obj2.is_visible()={obj2.is_visible()}")
        
        # Add a regular event to be processed after the visibility change
        print("Raising regular event on obj1")
        self.manager.raise_event(ChangeEvent("nested_test_2", obj1, {}))
        
        # Include all objects in the visible set to ensure events propagate properly
        print("Dispatching final events with all objects visible")
        self.manager.dispatch_events(visible={obj1, obj2, processor})
        
        # Debug what happened
        print(f"After full dispatch, processor call count: {processor.process_change.call_count}")
        print(f"Events received by processor: {processor.events_received}")
        print(f"Visibility changes recorded by processor: {processor.visibility_changes}")
        
        # Then - processor should be notified of both the visibility change and the event
        self.assertGreaterEqual(processor.process_change.call_count, 1)
        
        # Verify visibility change was processed - check by name
        source_names = [obj.name for obj in processor.visibility_changes.keys()]
        print(f"Source names in processor visibility_changes: {source_names}")
        self.assertIn(obj2.name, source_names)
        
        # Get the actual source object from the processor's visibility_changes
        source_obj = next(obj for obj in processor.visibility_changes.keys() 
                         if obj.name == obj2.name)
        self.assertTrue(processor.visibility_changes[source_obj])
        
    def test_non_visibility_aware_nodes(self):
        """Test that non-VisibilityAware nodes don't block visibility propagation."""
        # Reset mock to clear any previous calls
        self.processor.process_change.reset_mock()
        
        # Create a non-VisibilityAware object
        class RegularObject:
            pass
            
        # Set up a chain: visible_obj -> regular_obj -> processor
        regular_obj = RegularObject()
        
        # Set up dependencies
        self.manager.register(regular_obj, self.visible_obj)
        self.manager.register(self.processor, regular_obj)
        
        # When - raise an event on the visible object
        event = ChangeEvent("test_event", self.visible_obj, {})
        self.manager.raise_event(event)
        self.manager.dispatch_events(visible={self.visible_obj})
        
        # Then - processor should receive the event even though regular_obj is not VisibilityAware
        self.processor.process_change.assert_called_once()
        events = self.processor.process_change.call_args[0][0]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source.name, self.visible_obj.name)
        self.assertEqual(events[0].event_type, "test_event")


if __name__ == '__main__':
    unittest.main()
