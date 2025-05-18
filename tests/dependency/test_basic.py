"""
Basic tests for the dependency management system.

These tests verify the core functionality of the dependency management system,
including registration, event raising, and dispatch.
"""

import pytest
from typing import List

from tinyDisplay.dependency import (
    DependencyManager,
    ChangeEvent,
    ChangeEventProtocol,
    ChangeProcessorProtocol
)


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, manager: DependencyManager, name: str = "mock"):
        self.manager = manager
        self.name = name
        
    def change(self, event_type: str = "changed"):
        """Raise a change event."""
        event = ChangeEvent(event_type=event_type, source=self)
        self.manager.raise_event(event)


class MockDependent(ChangeProcessorProtocol):
    """A simple dependent object that can process change events."""
    
    def __init__(self, name: str = "dependent"):
        self.name = name
        self.events_received = []
        self.processed_count = 0
        
    def process_change(self, events: List[ChangeEventProtocol]):
        """Process change events."""
        self.events_received.extend(events)
        self.processed_count += 1


class TestDependencyRegistration:
    """Test dependency registration and unregistration."""
    
    def test_register_single(self):
        """Test registering a single dependency."""
        dm = DependencyManager()
        obs = MockObservable(dm)
        dep = MockDependent()
        
        handle = dm.register(dep, obs)
        
        assert handle.dependent == dep
        assert handle.observable == obs
        assert handle.is_valid()
        
    def test_register_multiple(self):
        """Test registering multiple dependencies at once."""
        dm = DependencyManager()
        obs1 = MockObservable(dm, "obs1")
        obs2 = MockObservable(dm, "obs2")
        obs3 = MockObservable(dm, "obs3")
        dep = MockDependent()
        
        handles = dm.register(dep, [obs1, obs2, obs3])
        
        assert len(handles) == 3
        assert all(h.dependent == dep for h in handles)
        assert {h.observable for h in handles} == {obs1, obs2, obs3}
        
    def test_unregister_by_handle(self):
        """Test unregistering using the subscription handle."""
        dm = DependencyManager()
        obs = MockObservable(dm)
        dep = MockDependent()
        
        handle = dm.register(dep, obs)
        dm.unregister(handle)
        
        # Change will not be delivered after unregistration
        obs.change()
        dm.dispatch_events()
        
        assert dep.processed_count == 0
        assert len(dep.events_received) == 0
        
    def test_unregister_by_objects(self):
        """Test unregistering using the dependent and observable objects."""
        dm = DependencyManager()
        obs = MockObservable(dm)
        dep = MockDependent()
        
        dm.register(dep, obs)
        dm.unregister(dep, obs)
        
        # Change will not be delivered after unregistration
        obs.change()
        dm.dispatch_events()
        
        assert dep.processed_count == 0
        assert len(dep.events_received) == 0
        
    def test_unregister_all(self):
        """Test unregistering all dependencies for a dependent."""
        dm = DependencyManager()
        obs1 = MockObservable(dm, "obs1")
        obs2 = MockObservable(dm, "obs2")
        dep = MockDependent()
        
        dm.register(dep, [obs1, obs2])
        dm.unregister_all(dep)
        
        # Changes will not be delivered after unregistration
        obs1.change()
        obs2.change()
        dm.dispatch_events()
        
        assert dep.processed_count == 0
        assert len(dep.events_received) == 0


class TestEventDispatch:
    """Test event raising and dispatch."""
    
    def test_single_event_dispatch(self):
        """Test dispatching a single event."""
        dm = DependencyManager()
        obs = MockObservable(dm)
        dep = MockDependent()
        
        dm.register(dep, obs)
        obs.change()
        dm.dispatch_events()
        
        assert dep.processed_count == 1
        assert len(dep.events_received) == 1
        assert dep.events_received[0].source == obs
        assert dep.events_received[0].event_type == "changed"
        
    def test_multiple_event_batch(self):
        """Test batching multiple events for a dependent."""
        dm = DependencyManager()
        obs1 = MockObservable(dm, "obs1")
        obs2 = MockObservable(dm, "obs2")
        dep = MockDependent()
        
        dm.register(dep, [obs1, obs2])
        obs1.change("changed1")
        obs2.change("changed2")
        dm.dispatch_events()
        
        assert dep.processed_count == 1  # Only one batch delivery
        assert len(dep.events_received) == 2
        event_types = {e.event_type for e in dep.events_received}
        assert event_types == {"changed1", "changed2"}


class TestCascadingEvents:
    """Test cascading events within a tick."""
    
    def test_cascading_events(self):
        """Test cascading events where a change handler raises new events."""
        dm = DependencyManager()
        
        # Create test objects
        source = MockObservable(dm, "source")
        intermediate = CascadingDependent(dm, "intermediate")
        final = MockDependent("final")
        
        # Setup dependency chain: source -> intermediate -> final
        dm.register(intermediate, source)
        dm.register(final, intermediate)
        
        # Trigger the initial change
        source.change("initial")
        dm.dispatch_events()
        
        # The intermediate should have received 1 event and generated a cascading event
        assert intermediate.processed_count == 1
        assert len(intermediate.events_received) == 1
        assert intermediate.events_received[0].event_type == "initial"
        
        # The final dependent should have received the cascading event
        assert final.processed_count == 1
        assert len(final.events_received) == 1
        assert final.events_received[0].event_type == "cascaded"
        assert final.events_received[0].source == intermediate


class CascadingDependent(MockDependent):
    """A dependent that also raises events when it processes changes."""
    
    def __init__(self, manager: DependencyManager, name: str = "cascading"):
        super().__init__(name)
        self.manager = manager
        
    def process_change(self, events: List[ChangeEventProtocol]):
        """Process events and generate a new cascading event."""
        super().process_change(events)
        
        # Generate a cascading event
        cascading_event = ChangeEvent(
            event_type="cascaded",
            source=self,
            metadata={"original_events": len(events)}
        )
        self.manager.raise_event(cascading_event)
