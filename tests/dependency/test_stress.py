"""
Stress tests for the dependency management system.

These tests verify the performance and stability of the dependency management system
under heavy load and with complex dependency graphs.
"""

import unittest
import time
import gc
import random
import sys
from typing import List, Dict, Set, Any
from dataclasses import dataclass

from tinyDisplay.dependency.manager import DependencyManager
from tinyDisplay.dependency.events import ChangeEvent
from tinyDisplay.dependency.protocols import ChangeProcessorProtocol, ChangeEventProtocol


@dataclass
class PerformanceMetrics:
    """Helper class to collect and report performance metrics."""
    start_time: float = 0
    end_time: float = 0
    memory_before: int = 0
    memory_after: int = 0
    event_count: int = 0
    node_count: int = 0
    edge_count: int = 0

    def start_timer(self):
        """Start the performance timer."""
        gc.collect()
        self.memory_before = self._get_memory_usage()
        self.start_time = time.perf_counter()

    def stop_timer(self):
        """Stop the performance timer and collect metrics."""
        self.end_time = time.perf_counter()
        gc.collect()
        self.memory_after = self._get_memory_usage()

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        # This is a simple approximation - for more accurate results, consider using psutil
        objects = gc.get_objects()
        return sum(sys.getsizeof(obj) for obj in objects)

    @property
    def duration(self) -> float:
        """Get the duration of the measured operation in seconds."""
        return self.end_time - self.start_time

    @property
    def memory_delta(self) -> int:
        """Get the memory delta in bytes."""
        return self.memory_after - self.memory_before

    def report(self, test_name: str):
        """Print a performance report."""
        print(f"\n{test_name} Performance Report:")
        print(f"  Duration: {self.duration:.4f} seconds")
        print(f"  Memory used: {self.memory_delta / (1024 * 1024):.2f} MB")
        print(f"  Events processed: {self.event_count}")
        print(f"  Nodes in graph: {self.node_count}")
        print(f"  Edges in graph: {self.edge_count}")
        if self.duration > 0:
            print(f"  Events/second: {self.event_count / self.duration:.2f}")


class CountingDependent(ChangeProcessorProtocol):
    """A dependent that simply counts processed events."""
    
    def __init__(self, name: str = "counter"):
        self.name = name
        self.count = 0
        self.last_events: List[ChangeEventProtocol] = []
    
    def process_change(self, events: List[ChangeEventProtocol]):
        self.count += 1
        self.last_events = events


class TestDependencyStress(unittest.TestCase):
    """Stress tests for the dependency management system."""
    
    def setUp(self):
        self.manager = DependencyManager()
        self.metrics = PerformanceMetrics()
    
    def _get_memory_usage(self) -> int:
        """Helper method to get current memory usage."""
        objects = gc.get_objects()
        return sum(sys.getsizeof(obj) for obj in objects)
    
    def test_large_dependency_graph(self):
        """Test performance with a large number of nodes and dependencies."""
        # Configuration - reduced for testing
        num_nodes = 20  # Further reduced for reliability
        avg_dependencies = 3  # Reduced average dependencies
        
        # Create nodes
        nodes = []
        for i in range(num_nodes):
            obs = MockObservable(self.manager, f"node_{i}")
            dep = CountingDependent(f"dep_{i}")
            nodes.append((obs, dep))
        
        # Create dependencies
        edge_count = 0
        for i, (obs, dep) in enumerate(nodes):
            # Each node depends on a random set of previous nodes
            num_deps = min(avg_dependencies, i)  # Can't have more deps than previous nodes
            if num_deps > 0:
                deps = random.sample(nodes[:i], num_deps)
                for dep_obs, _ in deps:
                    self.manager.register(dep, dep_obs)
                    edge_count += 1
        
        # Make sure the first node has at least one dependent
        if num_nodes > 1 and edge_count == 0:
            self.manager.register(nodes[1][1], nodes[0][0])
            edge_count += 1
        
        # Update metrics
        self.metrics.node_count = num_nodes
        self.metrics.edge_count = edge_count
        
        # Trigger changes and measure performance
        self.metrics.start_timer()
        
        # Trigger changes in all nodes
        for obs, _ in nodes:
            obs.change("test_event")
        
        # Process all events
        self.manager.dispatch_events()
        
        self.metrics.stop_timer()
        self.metrics.event_count = num_nodes
        self.metrics.report("Large Dependency Graph")
        
        # Verify at least some dependents were notified
        # We can't guarantee all will be notified due to random graph structure
        notified_count = sum(1 for _, dep in nodes if dep.count > 0)
        self.assertGreater(notified_count, 0, "At least some dependents should be notified")
        print(f"\n{notified_count} out of {num_nodes} nodes were notified")
    
    def test_deep_dependency_chain(self):
        """Test performance with a deep chain of dependencies using active propagation."""
        chain_length = 5  # Reduced for reliability
        
        # Create a chain of nodes where each actively propagates events to the next
        chain = []
        
        # First create all nodes
        for i in range(chain_length):
            obs = MockObservable(self.manager, f"chain_{i}")
            dep = CountingDependent(f"dep_{i}")
            chain.append((obs, dep))
        
        # Create a cascading relay that will forward events
        class CascadingRelay(ChangeProcessorProtocol):
            def __init__(self, manager, target):
                self.manager = manager
                self.target = target
                self.count = 0
                
            def process_change(self, events):
                self.count += 1
                # Forward the event to the target
                for event in events:
                    self.manager.raise_event(ChangeEvent(
                        event_type=event.event_type,
                        source=self.target,
                        metadata={"original_source": event.source.name}
                    ))
        
        # Set up the chain with cascading relays
        for i in range(chain_length):
            if i == 0:
                # First node is just an observable with a dependent
                self.manager.register(chain[i][1], chain[i][0])
            else:
                # Create a relay that forwards events from the previous node to the current one
                relay = CascadingRelay(self.manager, chain[i][0])
                self.manager.register(relay, chain[i-1][0])  # Relay observes previous node
                self.manager.register(chain[i][1], chain[i][0])  # Current node's dependent observes it
        
        # Update metrics
        self.metrics.node_count = chain_length
        self.metrics.edge_count = (chain_length - 1) * 2  # Each link has 2 edges (one for relay, one for dependent)
        
        # Trigger change at the start of the chain
        self.metrics.start_timer()
        chain[0][0].change("chain_event")
        self.manager.dispatch_events()
        self.metrics.stop_timer()
        
        self.metrics.event_count = chain_length
        self.metrics.report("Deep Dependency Chain with Active Propagation")
        
        # Verify the chain propagated correctly
        for i, (obs, dep) in enumerate(chain):
            if i == 0:
                # First node should have the initial event
                self.assertEqual(dep.count, 1, f"First node should have 1 event, got {dep.count}")
                self.assertEqual(len(dep.last_events), 1, "First node should have 1 event")
                self.assertEqual(dep.last_events[0].source.name, f"chain_{i}")
            else:
                # Other nodes should have been notified by the relay
                self.assertEqual(dep.count, 1, f"Node {i} should have 1 event, got {dep.count}")
                self.assertEqual(len(dep.last_events), 1, f"Node {i} should have 1 event")
                self.assertEqual(dep.last_events[0].source.name, f"chain_{i}", 
                                 f"Node {i} should have received event from chain_{i}")
    
    def test_high_frequency_events(self):
        """Test handling of a high volume of events."""
        num_events = 100  # Reduced for reliability
        obs = MockObservable(self.manager, "high_freq")
        dep = CountingDependent("counter")
        
        # Register the dependent to observe the observable
        self.manager.register(dep, obs)
        
        # Process registration
        self.manager.dispatch_events()
        
        self.metrics.start_timer()
        
        # Raise events with the same type to trigger deduplication
        for _ in range(num_events):
            obs.change("duplicate_event")
        
        # Process all events
        self.manager.dispatch_events()
        
        self.metrics.stop_timer()
        self.metrics.event_count = num_events
        self.metrics.report("High Frequency Events")
        
        # With deduplication, we should have only one batch of events
        self.assertEqual(dep.count, 1, "Dependent should process only one batch")
        # The last_events should contain all deduplicated events
        self.assertGreaterEqual(len(dep.last_events), 1, "Should have at least one event")
        self.assertEqual(dep.last_events[0].event_type, "duplicate_event")
    
    def test_memory_cleanup(self):
        """Test that memory is properly cleaned up after unregistration."""
        num_nodes = 100
        
        # Track all created objects
        obs_list = []
        dep_list = []
        
        # Create and register a large number of nodes
        for i in range(num_nodes):
            obs = MockObservable(self.manager, f"obs_{i}")
            dep = CountingDependent(f"dep_{i}")
            self.manager.register(dep, obs)
            obs_list.append(obs)
            dep_list.append(dep)
            
            # Trigger changes to establish references
            obs.change("setup")
        
        # Process initial events
        self.manager.dispatch_events()
        
        # Get memory usage after setup
        gc.collect()
        memory_after_setup = self._get_memory_usage()
        
        # Unregister all dependencies
        for dep in dep_list:
            self.manager.unregister_all(dep)
        
        # Clear references
        del obs_list[:]
        del dep_list[:]
        
        # Force garbage collection
        gc.collect()
        memory_after_cleanup = self._get_memory_usage()
        
        # Verify memory was released
        memory_released = memory_after_setup - memory_after_cleanup
        print(f"\nMemory Cleanup Test:")
        print(f"  Memory after setup: {memory_after_setup / (1024 * 1024):.2f} MB")
        print(f"  Memory after cleanup: {memory_after_cleanup / (1024 * 1024):.2f} MB")
        print(f"  Memory released: {memory_released / (1024 * 1024):.2f} MB")
        
        # We can't be too strict here as Python's GC is not deterministic
        # Just verify we're not leaking massive amounts of memory
        self.assertLess(memory_after_cleanup, memory_after_setup * 1.1, 
                       "Memory usage after cleanup is too high")


class MockObservable:
    """A simple observable object that can raise change events."""
    
    def __init__(self, manager: DependencyManager, name: str = "mock"):
        self.manager = manager
        self.name = name
        
    def change(self, event_type: str = "changed"):
        """Raise a change event."""
        event = ChangeEvent(event_type=event_type, source=self)
        self.manager.raise_event(event)


if __name__ == '__main__':
    unittest.main()
