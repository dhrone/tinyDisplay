"""
Tests for concurrency in the dependency management system.
"""

import unittest
import threading
import time
from typing import List, Set, Dict, Any

from tinyDisplay.dependency.manager import DependencyManager
from tinyDisplay.dependency.events import ChangeEvent
from tinyDisplay.dependency.protocols import ChangeProcessorProtocol, ChangeEventProtocol

class TestDependencyConcurrency(unittest.TestCase):
    """Test concurrent operations in the dependency management system."""
    
    def setUp(self):
        self.manager = DependencyManager()
    
    def test_concurrent_events(self):
        """Test that the system handles concurrent events from multiple sources."""
        num_observables = 2
        events_per_observable = 3
        
        # Create observables and a single dependent
        observables = [MockObservable(self.manager, f"obs_{i}") for i in range(num_observables)]
        dependent = CountingDependent("test_dependent")
        
        # Track which events we've generated
        generated_events = set()
        generated_lock = threading.Lock()
        
        # Track which events have been processed
        processed_events = set()
        processed_lock = threading.Lock()
        
        # Create a wrapper around our dependent to track processed events
        class TrackingDependent(ChangeProcessorProtocol):
            def __init__(self, delegate, lock, processed_set):
                self.delegate = delegate
                self.lock = lock
                self.processed_set = processed_set
    
            def process_change(self, events):
                with self.lock:
                    for event in events:
                        self.processed_set.add(event.event_type)
                return self.delegate.process_change(events)
        
        # Wrap our dependent to track processed events
        tracking_dep = TrackingDependent(dependent, processed_lock, processed_events)
        
        # Register the tracking dependent with all observables
        for obs in observables:
            self.manager.register(tracking_dep, obs)
        
        # Function to trigger events from a thread
        def trigger_events(obs, num_events, event_prefix):
            for i in range(num_events):
                event_id = f"{event_prefix}_{i}"
                with generated_lock:
                    generated_events.add(event_id)
                obs.change(event_id)
                time.sleep(0.01)  # Small delay to spread out events
        
        # Start a thread for each observable
        threads = []
        for i, obs in enumerate(observables):
            t = threading.Thread(
                target=trigger_events,
                args=(obs, events_per_observable, f"obs{i}"),
                daemon=True
            )
            threads.append(t)
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Process events until all expected events are handled or timeout
        start_time = time.time()
        timeout = 5.0  # Increased timeout to 5 seconds
        
        try:
            while time.time() - start_time < timeout:
                # Process any pending events
                self.manager.dispatch_events()
                
                # Check if we've processed all expected events
                if len(processed_events) >= num_observables * events_per_observable:
                    break
                    
                time.sleep(0.05)  # Small sleep to prevent busy waiting
            
            # Wait for all threads to finish (with timeout)
            for t in threads:
                t.join(timeout=0.5)
            
            # Process any remaining events one last time
            self.manager.dispatch_events()
            
            # Log what happened for debugging
            print(f"\nGenerated events: {sorted(generated_events)}")
            print(f"Processed events: {sorted(processed_events)}")
            print(f"Dependent count: {dependent.count}")
            
            # Check if all generated events were processed
            missing_events = generated_events - processed_events
            if missing_events:
                print(f"Warning: {len(missing_events)} events were not processed: {missing_events}")
            
            # Verify all expected events were processed
            expected_events = {f"obs{i}_{j}" for i in range(num_observables) for j in range(events_per_observable)}
            missing_events = expected_events - processed_events
            self.assertFalse(
                missing_events,
                f"Missing {len(missing_events)} events: {sorted(missing_events)[:5]}{'...' if len(missing_events) > 5 else ''}"
            )
            
            # The dependent's count should be <= the number of events due to batching
            self.assertGreaterEqual(
                len(processed_events),
                dependent.count,
                f"Dependent count ({dependent.count}) should be <= number of processed events ({len(processed_events)}) due to batching"
            )
            self.assertGreater(
                dependent.count,
                0,
                "Dependent should have processed at least one batch of events"
            )
            
            # Verify we can still register and unregister after concurrent operations
            new_obs = MockObservable(self.manager, "new_obs")
            new_dep = CountingDependent("new_dep")
            self.manager.register(new_dep, new_obs)
            new_obs.change("test_event")
            self.manager.dispatch_events()
            self.assertEqual(new_dep.count, 1, "Should be able to register new dependents after concurrent operations")
            
        except Exception as e:
            # Print additional debug info if something goes wrong
            print(f"\nTest failed with exception: {e}")
            print(f"Generated events: {generated_events}")
            print(f"Processed events: {processed_events}")
            print(f"Dependent count: {dependent.count}")
            if hasattr(dependent, 'last_events') and dependent.last_events:
                print(f"Last events: {[e.event_type for e in dependent.last_events]}")
            raise


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, manager, name: str = "mock"):
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
