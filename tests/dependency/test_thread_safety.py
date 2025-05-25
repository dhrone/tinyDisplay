"""
Tests for thread safety in the DependencyManager implementation.

These tests verify that the DependencyManager handles concurrent operations
correctly in a multi-threaded environment.
"""

import unittest
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Set, Dict, Any, Optional

from tinyDisplay.dependency.manager import DependencyManager, get_global_manager
from tinyDisplay.dependency.events import ChangeEvent, VisibilityChangeEvent
from tinyDisplay.dependency.protocols import ChangeProcessorProtocol, ChangeEventProtocol
from tinyDisplay.dependency.visibility.protocols import VisibilityAware


class TestThreadSafety(unittest.TestCase):
    """Test suite for verifying thread safety in the DependencyManager."""
    
    def setUp(self):
        self.manager = DependencyManager()
        
    def test_concurrent_registration(self):
        """Test that concurrent registration operations are thread-safe."""
        # We'll create a fixed number of objects and have multiple threads register dependencies
        num_threads = 10
        num_objects = 20
        iterations_per_thread = 50
        
        # Create a set of objects to use in the test
        observables = [MockObservable(f"observable_{i}") for i in range(num_objects)]
        dependents = [MockDependent(f"dependent_{i}") for i in range(num_objects)]
        
        # Track registrations to validate results
        successful_registrations = []
        registration_lock = threading.Lock()
        
        # Function to be executed by each thread
        def register_random_dependencies():
            local_registrations = []
            for _ in range(iterations_per_thread):
                # Randomly select an observable and a dependent
                observable = random.choice(observables)
                dependent = random.choice(dependents)
                
                # Register the dependency
                handle = self.manager.register(dependent, observable)
                local_registrations.append((dependent, observable, handle))
                
                # Small sleep to increase chance of thread interleaving
                time.sleep(0.001)
            
            # Add local registrations to the global list
            with registration_lock:
                successful_registrations.extend(local_registrations)
        
        # Start threads for concurrent registration
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=register_random_dependencies)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Verify that all registrations are correctly recorded in the manager
        for dependent, observable, handle in successful_registrations:
            # Check if the handle is in the dependencies for this observable
            observable_deps = self.manager._dependencies.get(observable, set())
            self.assertTrue(
                any(h.dependent == dependent and h.observable == observable for h in observable_deps),
                f"Dependency {dependent.name} -> {observable.name} not found in manager's dependencies"
            )
            
            # Check if the handle is in the reverse dependencies for this dependent
            dependent_deps = self.manager._reverse_dependencies.get(dependent, set())
            self.assertTrue(
                any(h.dependent == dependent and h.observable == observable for h in dependent_deps),
                f"Dependency {dependent.name} -> {observable.name} not found in manager's reverse dependencies"
            )
            
        # Verify that we can unregister all these dependencies
        for dependent, observable, handle in successful_registrations:
            self.manager.unregister(handle)
    
    def test_concurrent_unregistration(self):
        """Test that concurrent unregistration operations are thread-safe."""
        # First create a large number of dependencies
        num_objects = 20
        
        # Create objects and register dependencies
        observables = [MockObservable(f"observable_{i}") for i in range(num_objects)]
        dependents = [MockDependent(f"dependent_{i}") for i in range(num_objects)]
        
        # Create a mesh of dependencies (each dependent depends on all observables)
        handles = []
        for dependent in dependents:
            for observable in observables:
                handle = self.manager.register(dependent, observable)
                handles.append((dependent, observable, handle))
        
        # Shuffle the handles to ensure random access patterns
        random.shuffle(handles)
        
        # Split handles among threads
        num_threads = 5
        handles_per_thread = [[] for _ in range(num_threads)]
        
        for i, handle_tuple in enumerate(handles):
            thread_idx = i % num_threads
            handles_per_thread[thread_idx].append(handle_tuple)
        
        # Function to unregister a batch of dependencies
        def unregister_batch(batch):
            for dependent, observable, handle in batch:
                # Use either handle-based or object-based unregistration
                if random.choice([True, False]):
                    self.manager.unregister(handle)
                else:
                    self.manager.unregister(dependent, observable)
                    
                # Small sleep to increase chance of thread interleaving
                time.sleep(0.001)
        
        # Start threads for concurrent unregistration
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=unregister_batch, args=(handles_per_thread[i],))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Verify all dependencies were unregistered
        for dependent, observable, _ in handles:
            # Check the dependencies were removed
            observable_deps = self.manager._dependencies.get(observable, set())
            self.assertFalse(
                any(h.dependent == dependent and h.observable == observable for h in observable_deps),
                f"Dependency {dependent.name} -> {observable.name} still exists in manager's dependencies"
            )
            
    def test_unregister_all_thread_safety(self):
        """Test that unregister_all is thread-safe."""
        # Create a dependent with many observables
        dependent = MockDependent("test_dependent")
        observables = [MockObservable(f"observable_{i}") for i in range(100)]
        
        # Register dependencies
        for observable in observables:
            self.manager.register(dependent, observable)
        
        # Create functions that will run concurrently: 
        # 1. One thread unregistering all dependencies
        # 2. Multiple threads raising events
        
        # Flag to control when threads should start and stop
        running = threading.Event()
        running.set()
        
        # Thread to unregister all dependencies
        def unregister_all_thread():
            self.manager.unregister_all(dependent)
            
        # Threads to raise events from observables
        def raise_events_thread():
            while running.is_set():
                for observable in random.sample(observables, 10):  # Take a random subset
                    observable.raise_event(self.manager, "test_event")
                time.sleep(0.01)
        
        # Start event-raising threads
        event_threads = []
        for _ in range(5):
            thread = threading.Thread(target=raise_events_thread)
            thread.daemon = True
            event_threads.append(thread)
            thread.start()
        
        # Give event threads a moment to start raising events
        time.sleep(0.1)
        
        # Now run the unregister_all operation
        unregister_thread = threading.Thread(target=unregister_all_thread)
        unregister_thread.start()
        unregister_thread.join()
        
        # Signal event threads to stop and wait for them
        running.clear()
        for thread in event_threads:
            thread.join(timeout=1.0)
        
        # Verify all dependencies were removed
        self.assertNotIn(dependent, self.manager._reverse_dependencies)
        
        # Process any pending events to ensure no errors
        self.manager.dispatch_events()
    
    def test_global_manager_thread_safety(self):
        """Test that the global manager singleton is created thread-safely."""
        # Clear the global manager if it exists
        import tinyDisplay.dependency.manager
        tinyDisplay.dependency.manager._global_manager = None
        
        # Function to get the global manager from a thread
        results = []
        results_lock = threading.Lock()
        
        def get_manager():
            manager = get_global_manager()
            with results_lock:
                results.append(manager)
        
        # Create many threads to get the global manager simultaneously
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=get_manager)
            threads.append(thread)
        
        # Start all threads at approximately the same time
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify that all threads got the same manager instance
        first_manager = results[0]
        for manager in results[1:]:
            self.assertIs(manager, first_manager, "All threads should get the same global manager instance")
    
    def test_concurrent_event_raising(self):
        """Test that raising events concurrently is thread-safe."""
        # Create a single dependent and multiple observables
        dependent = CountingDependent("counter")
        observables = [MockObservable(f"observable_{i}") for i in range(10)]
        
        # Register the dependent with all observables
        for observable in observables:
            self.manager.register(dependent, observable)
        
        # Counter for raised events
        event_count = 0
        event_count_lock = threading.Lock()
        
        # Function to raise many events from an observable
        def raise_events(observable, count):
            nonlocal event_count
            for i in range(count):
                observable.raise_event(self.manager, f"event_{observable.name}_{i}")
                with event_count_lock:
                    event_count += 1
                # Small sleep to increase interleaving
                time.sleep(0.001)
        
        # Start threads to raise events concurrently
        threads = []
        events_per_observable = 50
        for observable in observables:
            thread = threading.Thread(target=raise_events, args=(observable, events_per_observable))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify that all events were queued
        total_events = len(observables) * events_per_observable
        self.assertEqual(event_count, total_events, f"Expected {total_events} events to be raised")
        
        # Now dispatch events and verify they were received
        max_iterations = 10  # Give it enough iterations to process all events
        for _ in range(max_iterations):
            self.manager.dispatch_events()
            if dependent.count >= total_events:  # We might have batching
                break
            time.sleep(0.01)  # Small sleep between dispatch calls
        
        # Verify the dependent processed all events (accounting for batching)
        self.assertGreaterEqual(
            dependent.events_processed, 
            total_events,
            f"Expected at least {total_events} events to be processed, got {dependent.events_processed}"
        )
    
    def test_concurrent_visibility_changes(self):
        """Test that concurrent visibility changes are handled thread-safely."""
        # Create visibility-aware objects
        num_objects = 10
        visibles = [VisibilityAwareObject(f"visible_{i}") for i in range(num_objects)]
        dependents = [CountingDependent(f"dep_{i}") for i in range(5)]
        
        # Register dependencies
        for dependent in dependents:
            for visible in visibles:
                self.manager.register(dependent, visible)
        
        # Function to toggle visibility of random objects
        def toggle_visibility():
            for _ in range(20):
                obj = random.choice(visibles)
                obj.set_visibility(self.manager, not obj.visible)
                time.sleep(0.001)
        
        # Function to raise normal events from random objects
        def raise_events():
            for _ in range(20):
                obj = random.choice(visibles)
                obj.raise_event(self.manager, "test_event")
                time.sleep(0.001)
        
        # Run threads concurrently
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=toggle_visibility))
            threads.append(threading.Thread(target=raise_events))
        
        for thread in threads:
            thread.start()
        
        # While other threads are running, also dispatch events periodically
        for _ in range(5):
            self.manager.dispatch_events()
            time.sleep(0.01)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Final dispatch to process any remaining events
        self.manager.dispatch_events()
        
        # Test passes if no exceptions were raised
        # The specific number of events received is not deterministic due to visibility changes
    
    def test_visibility_pruning_thread_safety(self):
        """Test that the visibility pruning mechanism is thread-safe."""
        # Create visibility-aware objects in a chain: A -> B -> C -> D
        # Where B will be toggled invisible/visible to test pruning
        source = VisibilityAwareObject("source")
        middle1 = VisibilityAwareObject("middle1")
        middle2 = VisibilityAwareObject("middle2")
        end = CountingDependent("end")
        
        # Register the chain
        self.manager.register(middle1, source)
        self.manager.register(middle2, middle1)
        self.manager.register(end, middle2)
        
        # Make middle1 a CascadingRelay to actively propagate events
        middle1.make_relay(self.manager)
        middle2.make_relay(self.manager)
        
        # Thread to toggle visibility of middle1
        def toggle_middle_visibility():
            for _ in range(10):
                middle1.set_visibility(self.manager, False)
                time.sleep(0.002)  # Short pause while invisible
                middle1.set_visibility(self.manager, True)
                time.sleep(0.002)  # Short pause while visible
        
        # Thread to continuously raise events
        def raise_source_events():
            for i in range(50):
                source.raise_event(self.manager, f"source_event_{i}")
                time.sleep(0.001)
        
        # Thread to dispatch events
        def dispatch_events():
            for _ in range(10):
                self.manager.dispatch_events()
                time.sleep(0.005)
        
        # Run threads concurrently
        threads = [
            threading.Thread(target=toggle_middle_visibility),
            threading.Thread(target=raise_source_events),
            threading.Thread(target=dispatch_events)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Final dispatch
        self.manager.dispatch_events()
        
        # Verify some events made it through - the exact count depends on timing
        # and whether events were raised during visible periods
        # The test is primarily checking that we don't crash or deadlock
        print(f"End received {end.events_processed} events in the visibility pruning test")
    
    def test_visibility_cache_thread_safety(self):
        """Test that the visibility cache is managed thread-safely."""
        # Create a large graph of objects with visibility
        graph_size = 20
        visibles = [VisibilityAwareObject(f"node_{i}") for i in range(graph_size)]
        
        # Create random connections in the graph
        for i in range(graph_size):
            # Connect each node to 2-4 random other nodes
            for _ in range(random.randint(2, 4)):
                target_idx = random.randint(0, graph_size - 1)
                if target_idx != i:  # Avoid self-loops
                    self.manager.register(visibles[target_idx], visibles[i])
        
        # Make some nodes relays
        for i in range(0, graph_size, 3):  # Every third node is a relay
            visibles[i].make_relay(self.manager)
        
        # Thread to toggle visibility of random nodes
        def toggle_random_visibility():
            for _ in range(30):
                # Choose 1-3 random nodes to toggle
                for node in random.sample(visibles, random.randint(1, 3)):
                    node.set_visibility(self.manager, not node.visible)
                time.sleep(0.001)
        
        # Thread to raise events from random nodes
        def raise_random_events():
            for _ in range(40):
                node = random.choice(visibles)
                node.raise_event(self.manager, "test_event")
                time.sleep(0.001)
        
        # Thread to dispatch events with visibility filtering
        def dispatch_with_visibility():
            for _ in range(10):
                # Get the currently visible set
                visible_set = {node for node in visibles if node.visible}
                self.manager.dispatch_events(visible=visible_set)
                time.sleep(0.003)
        
        # Run threads concurrently
        threads = [
            threading.Thread(target=toggle_random_visibility),
            threading.Thread(target=toggle_random_visibility),
            threading.Thread(target=raise_random_events),
            threading.Thread(target=raise_random_events),
            threading.Thread(target=dispatch_with_visibility),
            threading.Thread(target=dispatch_with_visibility)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Final dispatch
        visible_set = {node for node in visibles if node.visible}
        self.manager.dispatch_events(visible=visible_set)
        
        # Test passes if no exceptions are raised
    
    def test_stress_concurrent_operations(self):
        """Stress test with all operations happening concurrently."""
        # Create a pool of objects to work with
        num_objects = 20
        observables = [MockObservable(f"observable_{i}") for i in range(num_objects)]
        dependents = [CountingDependent(f"dependent_{i}") for i in range(num_objects)]
        
        # Add some visibility-aware objects to the mix
        visibles = [VisibilityAwareObject(f"visible_{i}") for i in range(10)]
        observables.extend(visibles)
        
        # Operations to perform concurrently
        def register_operation():
            for _ in range(10):
                observable = random.choice(observables)
                dependent = random.choice(dependents)
                self.manager.register(dependent, observable)
                time.sleep(0.001)
        
        def unregister_operation():
            for _ in range(5):
                dependent = random.choice(dependents)
                self.manager.unregister_all(dependent)
                time.sleep(0.002)
        
        def raise_events_operation():
            for _ in range(20):
                observable = random.choice(observables)
                observable.raise_event(self.manager, "stress_test_event")
                time.sleep(0.001)
        
        def toggle_visibility_operation():
            for _ in range(10):
                visible = random.choice(visibles)
                visible.set_visibility(self.manager, not visible.visible)
                time.sleep(0.002)
        
        def dispatch_events_operation():
            for _ in range(5):
                # Randomly decide whether to use visibility filtering
                if random.choice([True, False]):
                    visible_set = {obj for obj in visibles if obj.visible}
                    self.manager.dispatch_events(visible=visible_set)
                else:
                    self.manager.dispatch_events()
                time.sleep(0.005)
        
        # Create a mix of operations to run concurrently
        operations = []
        for _ in range(10):
            operations.append(register_operation)
        for _ in range(5):
            operations.append(unregister_operation)
        for _ in range(15):
            operations.append(raise_events_operation)
        for _ in range(8):
            operations.append(toggle_visibility_operation)
        for _ in range(3):
            operations.append(dispatch_events_operation)
        
        # Shuffle operations for randomness
        random.shuffle(operations)
        
        # Run operations concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            futures = [executor.submit(op) for op in operations]
            
            # Wait for all operations to complete
            for future in futures:
                # If any operation raised an exception, this will re-raise it
                future.result()
        
        # Final dispatch to process any remaining events
        self.manager.dispatch_events()
        
        # No assertions needed - the test passes if no exceptions were raised


class VisibilityAwareObject(ChangeProcessorProtocol, VisibilityAware):
    """A test object that implements the VisibilityAware protocol for testing visibility features.
    
    Based on the tinyDisplay visibility system design, this object:
    1. Explicitly raises visibility change events when its visibility changes
    2. Provides an is_visible() method to check visibility state
    3. Can act as a relay to propagate events through the dependency graph
    """
    
    def __init__(self, name: str = "visible_obj"):
        self.name = name
        self.visible = True
        self._is_relay = False
        self._manager = None
    
    def is_visible(self) -> bool:
        """Return whether this object is currently visible."""
        return self.visible
    
    def set_visible(self, visible: bool) -> None:
        """Set the visibility state of the object.
        
        Implements the VisibilityAware protocol.
        
        Args:
            visible: Whether the object should be visible.
        """
        self.set_visibility(self._manager, visible)
    
    def set_visibility(self, manager, visible: bool) -> None:
        """Set the visibility of this object and raise a visibility change event."""
        if self.visible != visible:
            self.visible = visible
            # Save the manager reference for later use
            if manager is not None:
                self._manager = manager
                # Raise a visibility change event
                event = VisibilityChangeEvent(self, visible)
                manager.raise_event(event)
    
    def raise_event(self, manager, event_type: str = "changed"):
        """Raise a normal change event through the manager."""
        event = ChangeEvent(event_type, self, {"source": self.name})
        manager.raise_event(event)
    
    def make_relay(self, manager):
        """Make this object a cascading relay that re-emits received events."""
        self._is_relay = True
        self._manager = manager
    
    def process_change(self, events: List[ChangeEventProtocol]):
        """Process change events. If this is a relay, re-emit them with self as the source."""
        if self._is_relay:
            # We need to store a reference to the manager when making this a relay
            if not hasattr(self, '_manager') or self._manager is None:
                return True
                
            for event in events:
                if isinstance(event, VisibilityChangeEvent):
                    # For visibility events, propagate with same visibility value
                    relay_event = VisibilityChangeEvent(self, event.visible)
                else:
                    # For regular events, copy metadata
                    relay_event = ChangeEvent(
                        f"relay_{event.event_type}", 
                        self, 
                        metadata=event.metadata.copy() if hasattr(event, 'metadata') else {}
                    )
                self._manager.raise_event(relay_event)
        return True
    
    def __repr__(self):
        return f"VisibilityAwareObject({self.name}, visible={self.visible})"


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, name: str = "mock"):
        self.name = name
    
    def raise_event(self, manager, event_type: str = "changed"):
        """Raise a change event through the manager."""
        event = ChangeEvent(event_type, self, {"source": self.name})
        manager.raise_event(event)
        
    def __repr__(self):
        return f"MockObservable({self.name})"


class MockDependent:
    """A simple dependent object for testing."""
    
    def __init__(self, name: str = "dependent"):
        self.name = name
    
    def __repr__(self):
        return f"MockDependent({self.name})"


class CountingDependent:
    """A dependent that counts processed events."""
    
    def __init__(self, name: str = "counter"):
        self.name = name
        self.count = 0  # Number of process_change calls
        self.events_processed = 0  # Total number of events processed
        self.last_events: List[ChangeEventProtocol] = []
    
    def process_change(self, events: List[ChangeEventProtocol]):
        """Process change events by counting them."""
        self.count += 1
        self.events_processed += len(events)
        self.last_events = events
        return True
    
    def __repr__(self):
        return f"CountingDependent({self.name}, count={self.count}, events={self.events_processed})"


if __name__ == "__main__":
    unittest.main()
