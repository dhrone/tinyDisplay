import unittest
from typing import List, Set, Dict, Any, Optional
from collections import defaultdict

from tinyDisplay.dependency.manager import DependencyManager
from tinyDisplay.dependency.events import ChangeEvent
from tinyDisplay.dependency.graph import topological_sort, identify_strongly_connected_components
from tinyDisplay.dependency.protocols import ChangeProcessorProtocol, ChangeEventProtocol


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, manager: DependencyManager, name: str = "mock"):
        self.manager = manager
        self.name = name
        
    def change(self, event_type: str = "changed"):
        """Raise a change event."""
        event = ChangeEvent(event_type=event_type, source=self)
        self.manager.raise_event(event)


class Counter(ChangeProcessorProtocol):
    """Simple counter class for tracking event processing."""
    def __init__(self, name: str = "counter"):
        self.name = name
        self.count = 0
        self.last_events = None
    
    def process_change(self, events: List[ChangeEventProtocol]):
        self.count += 1
        self.last_events = events


class CycleProcessor(ChangeProcessorProtocol):
    """Processor that creates cyclic dependencies when processing events."""
    def __init__(self, manager: DependencyManager, observable: Any):
        self.manager = manager
        self.observable = observable
        self.processed_events = []
    
    def process_change(self, events: List[ChangeEvent]):
        self.processed_events.extend(events)
        # Raise a new event on the observable, potentially creating a cycle
        self.manager.raise_event(ChangeEvent(self, "cycle_event"))


class TestAdvancedDependencies(unittest.TestCase):
    def setUp(self):
        # Create a fresh dependency manager for each test
        self.manager = DependencyManager()
    
    def test_topological_sorting(self):
        """Test that dependencies are processed in topological order."""
        # Create a simple dependency chain: A -> B -> C
        a = MockObservable(self.manager, "A")
        b = MockObservable(self.manager, "B")
        c = MockObservable(self.manager, "C")
        
        # Counters to track processing order
        counter_a = Counter("counter_a")
        counter_b = Counter("counter_b")
        counter_c = Counter("counter_c")
        
        # Counter objects are the dependents, MockObservables are the observables
        self.manager.register(counter_a, a)
        self.manager.register(counter_b, b)
        self.manager.register(counter_c, c)
        
        # Set up chain dependencies - counter_c depends on B, counter_b depends on A
        self.manager.register(counter_b, a)
        self.manager.register(counter_c, b)
        
        # Raise event on A
        a.change("test_event")
        self.manager.dispatch_events()
        
        # Verify processing order through counts
        # counter_a and counter_b should process because A changed
        self.assertEqual(counter_a.count, 1)
        self.assertEqual(counter_b.count, 1)
        self.assertEqual(counter_c.count, 0)  # Not affected by A directly
        
        # Reset counters
        counter_a.count = 0
        counter_b.count = 0
        counter_c.count = 0
        
        # Raise event on B, only counter_b and counter_c should be affected
        b.change("test_event")
        self.manager.dispatch_events()
        
        self.assertEqual(counter_a.count, 0)  # Not affected by B
        self.assertEqual(counter_b.count, 1)
        self.assertEqual(counter_c.count, 1)
    
    def test_cycle_detection_and_resolution(self):
        """Test that cycles are properly detected and resolved."""
        # This test verifies that our cyclic dependency resolution works properly
        
        # Create objects with a cycle in dependencies
        a = MockObservable(self.manager, "A")
        b = MockObservable(self.manager, "B")
        c = MockObservable(self.manager, "C")
        
        # Create counters to track dependencies
        counter_a = Counter("counter_a")
        counter_b = Counter("counter_b")
        counter_c = Counter("counter_c")
        
        # Set up a dependency cycle:  
        # counter_a depends on A
        # counter_b depends on B
        # counter_c depends on C
        # And: A depends on B, B depends on C, C depends on A (cycle)
        self.manager.register(counter_a, a)
        self.manager.register(counter_b, b)
        self.manager.register(counter_c, c)
        
        # Create the cycle in observables
        self.manager.register(a, b)  # A depends on changes to B
        self.manager.register(b, c)  # B depends on changes to C
        self.manager.register(c, a)  # C depends on changes to A (creating a cycle)
        
        # Start the cycle by changing A
        a.change("cycle_test")
        
        # This should not hang thanks to cycle detection
        # Without cycle detection, this would cause infinite recursion
        self.manager.dispatch_events()
        
        # Each counter should have processed exactly once
        self.assertEqual(counter_a.count, 1)
        self.assertEqual(counter_b.count, 0)  # B didn't actually change
        self.assertEqual(counter_c.count, 0)  # C didn't actually change
    
    def test_event_deduplication(self):
        """Test that duplicate events are properly deduplicated."""
        # Create a simple observable and dependent
        observable = MockObservable(self.manager, "Observable")
        dependent = Counter("counter")
        
        # Set up dependency - dependent depends on observable
        self.manager.register(dependent, observable)
        
        # Raise multiple events of the same type on the same source
        for i in range(5):
            observable.change("test_event")
        
        # Dispatch events
        self.manager.dispatch_events()
        
        # The dependent should have been processed only once due to deduplication
        self.assertEqual(dependent.count, 1)
        
        # And should have received only one event due to deduplication
        self.assertEqual(len(dependent.last_events), 1)
    
    def test_event_deduplication_with_metadata(self):
        """Test that duplicate events merge metadata correctly."""
        # Create a test observable and dependent
        observable = MockObservable(self.manager, "Observable")
        dependent = Counter("counter")
        
        # Set up dependency - dependent depends on observable
        self.manager.register(dependent, observable)
        
        # Create events with different metadata
        event1 = ChangeEvent(source=observable, event_type="test_event")
        event1.metadata = {"key1": "value1", "common": "original"}
        
        event2 = ChangeEvent(source=observable, event_type="test_event")
        event2.metadata = {"key2": "value2", "common": "updated"}
        
        # Raise both events
        self.manager.raise_event(event1)
        self.manager.raise_event(event2)
        
        # Dispatch events
        self.manager.dispatch_events()
        
        # The dependent should have been processed only once due to deduplication
        self.assertEqual(dependent.count, 1)
        
        # And should have received only one event with merged metadata
        self.assertEqual(len(dependent.last_events), 1)
        merged_metadata = dependent.last_events[0].metadata
        
        # Check that metadata was properly merged
        self.assertEqual(merged_metadata["key1"], "value1")
        self.assertEqual(merged_metadata["key2"], "value2")
        # The later value should override the earlier one
        self.assertEqual(merged_metadata["common"], "updated")
    
    def test_visibility_filtering_simple(self):
        """Test that events are only delivered to visible dependents."""
        # Create observables and dependents
        observable1 = MockObservable(self.manager, "Observable1")
        observable2 = MockObservable(self.manager, "Observable2")
        
        dependent1 = Counter("dep1")
        dependent2 = Counter("dep2")
        dependent3 = Counter("dep3")
        
        # Set up dependencies - dependents depend on observables
        self.manager.register(dependent1, observable1)
        self.manager.register(dependent2, observable1)
        self.manager.register(dependent3, observable2)
        
        # Raise events
        observable1.change("test_event")
        observable2.change("test_event")
        
        # Dispatch events with visibility filtering
        # Only dependent1 and dependent3 are visible
        visible_set = {dependent1, dependent3}
        self.manager.dispatch_events(visible=visible_set)
        
        # Check that only visible dependents received events
        self.assertEqual(dependent1.count, 1)  # Visible
        self.assertEqual(dependent2.count, 0)  # Not visible
        self.assertEqual(dependent3.count, 1)  # Visible
    
    def test_pruned_dependencies_computation(self):
        """Test that compute_pruned_dependencies correctly preserves dependencies through invisible nodes."""
        # This test directly verifies the behavior of the pruned dependency graph computation
        
        # Create a test graph with objects
        a = MockObservable(self.manager, "A")
        b = MockObservable(self.manager, "B")  # This will be invisible
        c = MockObservable(self.manager, "C")
        
        # Create dependents for these objects
        dependent_a = Counter("dependent_a")
        dependent_b = Counter("dependent_b")  # This will be invisible
        dependent_c = Counter("dependent_c")
        
        # Create a dependency chain: dependent_a -> a, dependent_b -> b, dependent_c -> c
        self.manager.register(dependent_a, a)
        self.manager.register(dependent_b, b)
        self.manager.register(dependent_c, c)
        
        # Also create dependencies between the observables: b depends on a, c depends on b
        self.manager.register(b, a)  # b depends on a
        self.manager.register(c, b)  # c depends on b
        
        # Define the visible set - dependent_b is not visible
        visible_set = {dependent_a, dependent_c}
        
        # Compute the pruned dependency graph
        pruned_graph = self.manager.compute_pruned_dependencies(visible_set)
        
        # Verify the pruned graph structure
        # 1. a should be in the graph because dependent_a depends on it
        self.assertIn(a, pruned_graph, "Observable A should be in the pruned graph")
        self.assertIn(dependent_a, pruned_graph[a], "dependent_a should be connected to A in pruned graph")
        
        # 2. c should be in the graph because dependent_c depends on it
        self.assertIn(c, pruned_graph, "Observable C should be in the pruned graph")
        self.assertIn(dependent_c, pruned_graph[c], "dependent_c should be connected to C in pruned graph")
        
        # 3. b might be in the graph if the pruning preserves it as part of the dependency chain
        # If b is in the graph, it should not have dependent_b as its dependent (since it's invisible)
        if b in pruned_graph:
            self.assertNotIn(dependent_b, pruned_graph[b], "Invisible dependent_b should not be in the pruned graph")
    
    def test_visibility_filtering(self):
        """Test pruned dependency dispatch with an invisible node in the chain."""
        # Create EventTrackers that will report when they process events
        class EventTracker(ChangeProcessorProtocol):
            def __init__(self, name):
                self.name = name
                self.events_processed = []
            
            def process_change(self, events):
                self.events_processed.extend(events)
                
        # Create a cascading observable that automatically propagates changes
        class CascadingObservable(ChangeProcessorProtocol):
            def __init__(self, manager, name):
                self.manager = manager
                self.name = name
                self.events_received = []
            
            def process_change(self, events):
                self.events_received.extend(events)
                # Re-emit a new event when we receive one - this creates the cascade
                self.manager.raise_event(ChangeEvent(source=self, event_type="cascaded"))
        
        # Creating a simpler test case that clearly shows the dependency chain
        a = MockObservable(self.manager, "A")  # Source observable
        b = MockObservable(self.manager, "B")  # Middle observable (will be invisible)
        c = MockObservable(self.manager, "C")  # Final observable
        
        # Create trackers for each observable
        tracker_a = EventTracker("tracker_A")  # Visible
        tracker_b = EventTracker("tracker_B")  # Will be invisible
        tracker_c = EventTracker("tracker_C")  # Visible
        
        # Each tracker tracks changes to its corresponding observable
        self.manager.register(tracker_a, a)
        self.manager.register(tracker_b, b)
        self.manager.register(tracker_c, c)
        
        # Create a special connector class that will update an observable when it receives events
        class ObservableUpdater(ChangeProcessorProtocol):
            def __init__(self, target_observable, name):
                self.target = target_observable
                self.name = name
                self.events_received = []
                
            def process_change(self, events):
                self.events_received.extend(events)
                # When we receive events, update the target observable
                self.target.change("cascaded-" + self.name)
        
        # Create the connectors for our dependency chain
        a_to_b_connector = ObservableUpdater(b, "A-to-B")  # Updates B when A changes
        b_to_c_connector = ObservableUpdater(c, "B-to-C")  # Updates C when B changes
        
        # Register the connectors to listen to their respective sources
        self.manager.register(a_to_b_connector, a)  # a_to_b_connector listens for changes on A
        self.manager.register(b_to_c_connector, b)  # b_to_c_connector listens for changes on B
        
        # First, verify basic event propagation works without visibility filtering
        # 1. Test A -> tracker_a
        a.change("test_direct")
        self.manager.dispatch_events(intra_tick_cascade=True)
        self.assertTrue(any(e.source == a for e in tracker_a.events_processed), 
                     "tracker_a should receive events directly from A")
        
        # 2. Test that the cascading from A through the connectors works
        self.assertTrue(any(e.source == a for e in a_to_b_connector.events_received), 
                     "a_to_b_connector should receive events from A")
        
        # Verify the cascade reached tracker_b through a_to_b_connector
        self.assertTrue(any(e.source == b for e in tracker_b.events_processed), 
                     "tracker_b should receive events from cascaded B updates")
        
        # 3. Clear all tracking data for the next test
        tracker_a.events_processed = []
        tracker_b.events_processed = []
        tracker_c.events_processed = []
        a_to_b_connector.events_received = []
        b_to_c_connector.events_received = []
        
        # 4. Test that changes to B reach tracker_b and also cascade to C
        b.change("test_b_changes")
        self.manager.dispatch_events(intra_tick_cascade=True)
        self.assertTrue(any(e.source == b for e in tracker_b.events_processed), 
                     "tracker_b should receive events when B changes")
        self.assertTrue(any(e.source == b for e in b_to_c_connector.events_received), 
                     "b_to_c_connector should receive events when B changes")
        # C should receive cascaded events from B
        self.assertTrue(any(e.source == c for e in tracker_c.events_processed), 
                     "tracker_c should receive events when C changes due to B")
        
        # 5. Clear tracking data again
        tracker_a.events_processed = []
        tracker_b.events_processed = []
        tracker_c.events_processed = []
        a_to_b_connector.events_received = []
        b_to_c_connector.events_received = []
        
        # 6. Now test the full chain without visibility filtering
        a.change("test_full_chain")
        self.manager.dispatch_events(intra_tick_cascade=True)
        
        # Verify each step in the chain received events
        self.assertTrue(any(e.source == a for e in tracker_a.events_processed),
                     "Step 1: tracker_a should receive events from A")
        self.assertTrue(any(e.source == a for e in a_to_b_connector.events_received),
                     "Step 2: a_to_b_connector should receive events from A")
        self.assertTrue(any(e.source == b for e in tracker_b.events_processed),
                     "Step 3: tracker_b should receive events from B (updated by connector)")
        self.assertTrue(any(e.source == b for e in b_to_c_connector.events_received),
                     "Step 4: b_to_c_connector should receive events from B")
        self.assertTrue(any(e.source == c for e in tracker_c.events_processed),
                     "Step 5: tracker_c should receive events from C (updated by connector)")
        
        # 7. Clear all tracking data again
        tracker_a.events_processed = []
        tracker_b.events_processed = []
        tracker_c.events_processed = []
        a_to_b_connector.events_received = []
        b_to_c_connector.events_received = []
        
        # 8. Now for the key test - with visibility filtering
        # Set tracker_b as invisible but keep the connectors in the visible set
        # This tests that our pruned dependency graph preserves the chain even when
        # intermediate dependents (tracker_b) are invisible
        visible_set = {tracker_a, tracker_c, a_to_b_connector, b_to_c_connector}
        # This means that a, b, c, and tracker_b are all invisible and should not receive events
        
        # Trigger a change at the start of the chain.  Even though a is invisible it can still raise change events
        # and cascade them to the visible nodes in the chain
        a.change("test_visibility")
        self.manager.dispatch_events(visible=visible_set, intra_tick_cascade=True)
        
        # Verify tracker_a still receives events (it's visible)
        self.assertTrue(any(e.source == a for e in tracker_a.events_processed),
                     "With visibility filtering: tracker_a should receive events from A")
        
        # tracker_b should NOT have received any events since it's invisible
        self.assertEqual(len(tracker_b.events_processed), 0,
                      "Invisible tracker_b should not receive events")
        
        # The connectors should still function in the chain
        self.assertTrue(any(e.source == a for e in a_to_b_connector.events_received),
                     "a_to_b_connector should still receive events from A with visibility filtering")

        # b_to_c connector should not receive events from b since b is invisible
        self.assertEqual(len(b_to_c_connector.events_received), 0,
                     "b_to_c_connector should not receive events from B since b is invisible")
        
        # tracker_c should not receive events since b is invisible, so b_to_c_connector didn't
        # receive events and the chain is pruned
        self.assertEqual(len(tracker_c.events_processed), 0,
                        "tracker_c should not receive events since it is invisible")
    
    def test_visibility_filtering_cascading(self):
        """Test pruned dependency dispatch with an invisible node using CascadingObservable pattern.
        
        This test verifies that when we have a chain of dependencies with active event propagation:
        A → relay_a_to_b → relay_b_to_c → C
        
        And if b is invisible but the other nodes are visible, events will still properly
        propagate from A to C through the relays, since the relays actively raise their own events.
        """
        # Create EventTrackers that will report when they process events
        class EventTracker(ChangeProcessorProtocol):
            def __init__(self, name):
                self.name = name
                self.events_processed = []
            
            def process_change(self, events):
                self.events_processed.extend(events)
                
        # Create a cascading observable that actively raises new events when it receives events
        class CascadingRelay(ChangeProcessorProtocol):
            def __init__(self, manager, name):
                self.manager = manager
                self.name = name
                self.events_received = []
                
            def process_change(self, events):
                # Store all events for verification
                self.events_received.extend(events)
                # ACTIVE PROPAGATION: Re-emit each received event with self as the source
                for event in events:
                    # Create a new event with this object as source
                    self.manager.raise_event(ChangeEvent(source=self, 
                                                        event_type=f"relayed_{event.event_type}",
                                                        metadata={"original_source": event.source}))
        
        # Creating test case with observable nodes
        a = MockObservable(self.manager, "A")  # Source observable
        b = MockObservable(self.manager, "B")  # Middle observable (will be invisible)
        c = MockObservable(self.manager, "C")  # Target observable
        
        # Setup the active propagation chain with relays
        relay_a_to_b = CascadingRelay(self.manager, "relay-A-to-B") # Actively forwards A's events
        relay_b_to_c = CascadingRelay(self.manager, "relay-B-to-C") # Actively forwards B's events
        
        # Create trackers to observe events at different points
        tracker_a = EventTracker("tracker_A")  # Visible
        tracker_b = EventTracker("tracker_B")  # Will be invisible
        tracker_c = EventTracker("tracker_C")  # Visible
        
        # Set up the dependency graph - who listens to whom
        self.manager.register(tracker_a, a)         # tracker_a watches A
        self.manager.register(relay_a_to_b, a)      # relay_a_to_b watches A
        
        self.manager.register(tracker_b, b)         # tracker_b watches B
        self.manager.register(relay_b_to_c, relay_a_to_b)  # relay_b_to_c watches relay_a_to_b (key dependency)
        
        self.manager.register(tracker_c, c)         # tracker_c watches C
        self.manager.register(tracker_c, relay_b_to_c)  # tracker_c also watches relay_b_to_c
        
        # First, verify that normal event propagation works without visibility filtering
        a.change("test_cascading_normal")
        self.manager.dispatch_events()
        
        # Verify tracker_a receives A's events
        self.assertTrue(any(e.source == a for e in tracker_a.events_processed),
                     "tracker_a should receive direct events from A")
        
        # Verify relay_a_to_b receives A's events and should emit its own
        self.assertTrue(any(e.source == a for e in relay_a_to_b.events_received),
                     "relay_a_to_b should receive events from A")
        
        # Verify relay_b_to_c receives events from relay_a_to_b (active propagation)
        self.assertTrue(any(e.source == relay_a_to_b for e in relay_b_to_c.events_received),
                     "relay_b_to_c should receive events from relay_a_to_b")
        
        # Verify tracker_c gets events from relay_b_to_c
        self.assertTrue(any(e.source == relay_b_to_c for e in tracker_c.events_processed),
                     "tracker_c should receive events from relay_b_to_c")
        
        # Clear all tracking data
        tracker_a.events_processed = []
        tracker_b.events_processed = []
        tracker_c.events_processed = []
        relay_a_to_b.events_received = []
        relay_b_to_c.events_received = []
        
        # Now test with visibility filtering - make tracker_b invisible
        # The relays remain in the visible set to maintain active propagation
        visible_set = {tracker_a, tracker_c, relay_a_to_b, relay_b_to_c}
        
        a.change("test_cascading_with_visibility")
        self.manager.dispatch_events(visible=visible_set)
        
        # Verify tracker_a still receives A's events (it's visible)
        self.assertTrue(any(e.source == a for e in tracker_a.events_processed),
                     "With visibility filtering: tracker_a should receive events from A")
        
        # Verify tracker_b gets NO events (it's invisible)
        self.assertEqual(len(tracker_b.events_processed), 0,
                     "Invisible tracker_b should not receive any events")
        
        # Verify relay_a_to_b still gets events from A (it's visible)
        self.assertTrue(any(e.source == a for e in relay_a_to_b.events_received),
                     "relay_a_to_b should receive events from A with visibility filtering")
        
        # Verify relay_b_to_c still gets events from relay_a_to_b (both visible)
        self.assertTrue(any(e.source == relay_a_to_b for e in relay_b_to_c.events_received),
                     "relay_b_to_c should receive events from relay_a_to_b with visibility filtering")
        
        # THIS IS THE KEY ASSERTION: tracker_c should still receive events from relay_b_to_c
        # This shows the pruned dependency graph properly preserves active propagation chains
        self.assertTrue(any(e.source == relay_b_to_c for e in tracker_c.events_processed),
                     "tracker_c should receive events through the relay chain despite tracker_b being invisible")

    def test_performance_metrics(self):
        """Test that performance metrics are collected accurately."""
        # Enable debug mode to collect metrics
        self.manager.set_debug_mode(True)
        
        # Create test objects
        observable = MockObservable(self.manager, "Observable")
        dependent = Counter("counter")
        
        # Set up dependency - dependent depends on observable
        self.manager.register(dependent, observable)
        
        # Raise multiple events that will be deduplicated
        for i in range(10):
            observable.change("test_event")
        
        # Dispatch events
        self.manager.dispatch_events()
        
        # Get metrics
        metrics = self.manager.get_performance_metrics()
        
        # Verify metrics
        self.assertEqual(metrics["dispatch_count"], 1)
        self.assertEqual(metrics["events_processed"], 1)  # After deduplication
        self.assertEqual(metrics["deduplication_savings"], 9)  # 10 events - 1 after dedup
        
        # Total dispatch time should be positive
        self.assertGreater(metrics["total_dispatch_time"], 0)


if __name__ == '__main__':
    unittest.main()
