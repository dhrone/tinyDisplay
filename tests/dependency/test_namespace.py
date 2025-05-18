"""
Tests for namespaced dependency managers.

These tests verify the namespace isolation functionality of the dependency management system.
"""

import pytest
from typing import List

from tinyDisplay.dependency import (
    DependencyManager,
    NamespacedDependencyManager,
    ChangeEvent,
    ChangeEventProtocol,
    ChangeProcessorProtocol
)


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, manager: DependencyManager, name: str = "mock"):
        self.manager = manager
        self.name = name
        
        # If this is a namespaced manager, get its namespace ID
        self.namespace = getattr(manager, 'namespace_id', None)
        
    def change(self, event_type: str = "changed"):
        """Raise a change event."""
        # Create event with namespace if available
        event = ChangeEvent(event_type=event_type, source=self, namespace=self.namespace)
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
            metadata={"original_events": len(events)},
            namespace=getattr(self.manager, 'namespace_id', None)
        )
        self.manager.raise_event(cascading_event)


class TestNamespacedManager:
    """Test namespaced dependency managers."""
    
    def test_namespace_isolation(self):
        """Test that namespaces properly isolate registrations."""
        # Create two namespaced managers with different namespaces
        ns1 = NamespacedDependencyManager(namespace="ns1")
        ns2 = NamespacedDependencyManager(namespace="ns2")
        
        # Create test objects
        obs1 = MockObservable(ns1, "obs1")
        obs2 = MockObservable(ns2, "obs2")
        dep1 = MockDependent("dep1")
        dep2 = MockDependent("dep2")
        
        # Register dependencies in different namespaces
        ns1.register(dep1, obs1)
        ns2.register(dep2, obs2)
        
        # Trigger changes in both observables
        obs1.change("ns1_event")
        obs2.change("ns2_event")
        
        # Dispatch only in namespace 1
        ns1.dispatch_events()
        
        # Dependent 1 should receive events, dependent 2 should not
        assert dep1.processed_count == 1
        assert len(dep1.events_received) == 1
        assert dep1.events_received[0].event_type == "ns1_event"
        
        assert dep2.processed_count == 0
        assert len(dep2.events_received) == 0
        
        # Now dispatch in namespace 2
        ns2.dispatch_events()
        
        # Dependent 2 should now receive its events
        assert dep2.processed_count == 1
        assert len(dep2.events_received) == 1
        assert dep2.events_received[0].event_type == "ns2_event"
    
    def test_clear_namespace(self):
        """Test clearing a namespace."""
        # Create a namespaced manager
        ns = NamespacedDependencyManager(namespace="test_ns")
        
        # Create test objects
        obs = MockObservable(ns, "obs")
        dep = MockDependent("dep")
        
        # Register dependency
        ns.register(dep, obs)
        
        # Clear the namespace
        ns.clear()
        
        # Trigger a change
        obs.change()
        ns.dispatch_events()
        
        # Dependent should not receive any events
        assert dep.processed_count == 0
        assert len(dep.events_received) == 0
    
    def test_global_visibility(self):
        """Test that namespaced registrations are visible to the global manager."""
        # Create a namespaced manager and get the global manager
        global_dm = DependencyManager()
        ns = NamespacedDependencyManager(namespace="test_ns", global_manager=global_dm)
        
        # Create test objects
        obs = MockObservable(ns, "obs")
        dep = MockDependent("dep")
        
        # Register dependency in the namespace
        ns.register(dep, obs)
        
        # Trigger a change
        obs.change()
        
        # Dispatch from the global manager without namespace filter
        global_dm.dispatch_events()
        
        # Dependent should receive events
        assert dep.processed_count == 1
        assert len(dep.events_received) == 1
        
    def test_cross_namespace_visibility(self):
        """Test visibility of dependencies across namespaces."""
        # Create two namespaced managers with the same global manager
        global_dm = DependencyManager()
        ns1 = NamespacedDependencyManager(namespace="ns1", global_manager=global_dm)
        ns2 = NamespacedDependencyManager(namespace="ns2", global_manager=global_dm)
        
        # Create test objects
        obs = MockObservable(global_dm, "obs")
        dep1 = MockDependent("dep1")
        dep2 = MockDependent("dep2")
        
        # Register dependencies in different namespaces
        ns1.register(dep1, obs)
        ns2.register(dep2, obs)
        
        # Trigger a change in the observable
        obs.change()
        
        # Dispatch only in namespace 1
        ns1.dispatch_events()
        
        # Only dependent 1 should receive events
        assert dep1.processed_count == 1
        assert len(dep1.events_received) == 1
        
        assert dep2.processed_count == 0
        assert len(dep2.events_received) == 0

        # Dispatch only in namespace 2
        ns2.dispatch_events()
        
        # Now dependent 2 should also receive events
        assert dep2.processed_count == 1
        assert len(dep2.events_received) == 1
    
    def test_multiple_events_cross_namespace(self):
        """Test multiple events propagating across namespaces."""
        # Create two namespaced managers with the same global manager
        global_dm = DependencyManager()
        ns1 = NamespacedDependencyManager(namespace="ns1", global_manager=global_dm)
        ns2 = NamespacedDependencyManager(namespace="ns2", global_manager=global_dm)
        
        # Create test objects
        obs = MockObservable(global_dm, "obs")
        dep1 = MockDependent("dep1")
        dep2 = MockDependent("dep2")
        
        # Register dependencies in different namespaces
        ns1.register(dep1, obs)
        ns2.register(dep2, obs)
        
        # Trigger multiple changes in the observable
        obs.change("event1")
        obs.change("event2")
        obs.change("event3")
        
        # Dispatch in namespace 1
        ns1.dispatch_events()
        
        # Dependent 1 should receive all three events
        assert dep1.processed_count == 1
        assert len(dep1.events_received) == 3
        event_types = [e.event_type for e in dep1.events_received]
        assert sorted(event_types) == ["event1", "event2", "event3"]
        
        # Dependent 2 should not receive events yet
        assert dep2.processed_count == 0
        
        # Dispatch in namespace 2
        ns2.dispatch_events()
        
        # Now dependent 2 should also receive all three events
        assert dep2.processed_count == 1
        assert len(dep2.events_received) == 3
        event_types = [e.event_type for e in dep2.events_received]
        assert sorted(event_types) == ["event1", "event2", "event3"]
    
    def test_global_and_namespaced_events(self):
        """Test mixing global and namespaced events."""
        # Create namespaced managers
        global_dm = DependencyManager()
        ns1 = NamespacedDependencyManager(namespace="ns1", global_manager=global_dm)
        ns2 = NamespacedDependencyManager(namespace="ns2", global_manager=global_dm)
        
        # Create test objects with different managers
        global_obs = MockObservable(global_dm, "global_obs")
        ns1_obs = MockObservable(ns1, "ns1_obs")
        ns2_obs = MockObservable(ns2, "ns2_obs")
        
        # Create dependents
        dep1 = MockDependent("dep1")
        dep2 = MockDependent("dep2")
        
        # Register dependencies across namespaces
        # dep1 depends on global and ns1 observables
        ns1.register(dep1, global_obs)
        ns1.register(dep1, ns1_obs)
        
        # dep2 depends on global and ns2 observables
        ns2.register(dep2, global_obs)
        ns2.register(dep2, ns2_obs)
        
        # Trigger changes in all observables
        global_obs.change("global_event")
        ns1_obs.change("ns1_event")
        ns2_obs.change("ns2_event")
        
        # Dispatch in namespace 1
        ns1.dispatch_events()
        
        # Dependent 1 should receive global and ns1 events
        assert dep1.processed_count == 1
        assert len(dep1.events_received) == 2
        event_types = [e.event_type for e in dep1.events_received]
        assert "global_event" in event_types
        assert "ns1_event" in event_types
        assert "ns2_event" not in event_types
        
        # Dependent 2 should not have any events yet
        assert dep2.processed_count == 0
        
        # Dispatch in namespace 2
        ns2.dispatch_events()
        
        # Dependent 2 should receive global and ns2 events
        assert dep2.processed_count == 1
        assert len(dep2.events_received) == 2
        event_types = [e.event_type for e in dep2.events_received]
        assert "global_event" in event_types
        assert "ns2_event" in event_types
        assert "ns1_event" not in event_types
    
    def test_global_dispatch_all_namespaces(self):
        """Test that global dispatch delivers events to all namespaces."""
        # Create namespaced managers
        global_dm = DependencyManager()
        ns1 = NamespacedDependencyManager(namespace="ns1", global_manager=global_dm)
        ns2 = NamespacedDependencyManager(namespace="ns2", global_manager=global_dm)
        
        # Create test objects
        global_obs = MockObservable(global_dm, "global_obs")
        ns1_obs = MockObservable(ns1, "ns1_obs")
        ns2_obs = MockObservable(ns2, "ns2_obs")
        
        # Create dependents in different namespaces
        dep1 = MockDependent("dep1")
        dep2 = MockDependent("dep2")
        
        # Register dependencies
        ns1.register(dep1, global_obs)
        ns1.register(dep1, ns1_obs)
        ns2.register(dep2, global_obs)
        ns2.register(dep2, ns2_obs)
        
        # Trigger changes
        global_obs.change("global_event")
        ns1_obs.change("ns1_event")
        ns2_obs.change("ns2_event")
        
        # Dispatch from the global manager
        global_dm.dispatch_events()
        
        # Both dependents should receive their respective events
        # Dependent 1 should have global and ns1 events
        assert dep1.processed_count == 1
        assert len(dep1.events_received) == 2
        dep1_event_types = [e.event_type for e in dep1.events_received]
        assert "global_event" in dep1_event_types
        assert "ns1_event" in dep1_event_types
        
        # Dependent 2 should have global and ns2 events
        assert dep2.processed_count == 1
        assert len(dep2.events_received) == 2
        dep2_event_types = [e.event_type for e in dep2.events_received]
        assert "global_event" in dep2_event_types
        assert "ns2_event" in dep2_event_types
    
    def test_cascading_events_across_namespaces(self):
        """Test cascading events across namespace boundaries."""
        # Create namespaced managers
        global_dm = DependencyManager()
        ns1 = NamespacedDependencyManager(namespace="ns1", global_manager=global_dm)
        ns2 = NamespacedDependencyManager(namespace="ns2", global_manager=global_dm)
        
        # Create a chain of observables and dependents that span namespaces
        # global_source -> ns1_intermediate -> ns2_final
        global_source = MockObservable(global_dm, "global_source")
        ns1_intermediate = CascadingDependent(ns1, "ns1_intermediate")
        ns2_final = MockDependent("ns2_final")
        
        # Register dependencies across namespaces
        ns1.register(ns1_intermediate, global_source)
        ns2.register(ns2_final, ns1_intermediate)
        
        # Trigger the initial change
        global_source.change("initial")
        
        # Dispatch from the global manager
        global_dm.dispatch_events()
        
        # Check intermediate received the initial event
        assert ns1_intermediate.processed_count == 1
        assert len(ns1_intermediate.events_received) == 1
        assert ns1_intermediate.events_received[0].event_type == "initial"
        
        # Check final received the cascaded event
        assert ns2_final.processed_count == 1
        assert len(ns2_final.events_received) == 1
        assert ns2_final.events_received[0].event_type == "cascaded"
        
