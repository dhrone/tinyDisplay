"""
Core dependency manager implementation.

This module provides the DependencyManager class that handles dependency
registration, change event propagation, and notification dispatch.
"""

from typing import Any, Dict, List, Set, Optional, Tuple, Iterable, Union
import weakref
from collections import defaultdict, deque
import time

from .protocols import ChangeEventProtocol, ChangeProcessorProtocol
from .subscription import SubscriptionHandle
from .graph import topological_sort, identify_strongly_connected_components, break_cycles


# Global dependency manager instance
_global_manager = None


def get_global_manager():
    """Get the global dependency manager instance.
    
    Returns:
        The global DependencyManager instance.
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = DependencyManager()
    return _global_manager


class DependencyManager:
    """Manages dependencies between objects and dispatches change events.
    
    This class is responsible for:
    1. Tracking dependency relationships between observables and dependents
    2. Collecting change events from observables
    3. Dispatching batched change events to dependents
    4. Managing the dependency graph and handling cycles
    """
    
    def __init__(self):
        """Initialize a new dependency manager."""
        # Mapping from observable to set of subscription handles
        self._dependencies: Dict[Any, Set[SubscriptionHandle]] = defaultdict(set)
        
        # Reverse mapping from dependent to set of subscription handles
        self._reverse_dependencies: Dict[Any, Set[SubscriptionHandle]] = defaultdict(set)
        
        # Queue for global events (no namespace) to be dispatched in the current tick
        self._primary_queue: deque[ChangeEventProtocol] = deque()
        
        # Queue for cascading events generated during dispatch
        self._secondary_queue: deque[ChangeEventProtocol] = deque()
        
        # Queues for namespaced events, keyed by namespace
        self._namespace_queues: Dict[str, deque[ChangeEventProtocol]] = defaultdict(deque)
        
        # Track which namespaces have processed which global events
        # Maps (event_id -> set of namespace_ids)
        self._processed_events: Dict[str, Set[str]] = defaultdict(set)
        
        # Cache of last known visibility for efficient pruning
        self._last_visible_set: Optional[Set[Any]] = None
        
        # Cache of pruned dependencies for visibility optimization
        self._pruned_dependency_cache: Dict[Any, Set[Any]] = {}
        
        # Performance metrics
        self._perf_metrics = {
            'total_dispatch_time': 0.0,
            'dispatch_count': 0,
            'events_processed': 0,
            'deduplication_savings': 0,
        }
        
        # Enable debug mode for detailed performance logging
        self._debug_mode = False
        
        # Maximum number of cascading iterations per tick
        self._max_iterations = 10
        
        # Flag to indicate whether we're currently processing batch events
        # Used to determine which queue to add events to
        self._processing_batch = False
        
        # Registry of namespaced managers
        self._namespaces: Dict[str, Any] = {}
        
        # Flag to prevent infinite recursion when delegating to namespaces
        self._delegating_to_namespaces = False
        
    def register(self, dependent: Any, 
                 target: Union[Any, Iterable[Any]]) -> Union[SubscriptionHandle, List[SubscriptionHandle]]:
        """Register a dependency relationship.
        
        Args:
            dependent: The object that depends on the target(s).
            target: An observable object or list of observable objects.
            
        Returns:
            A SubscriptionHandle or list of SubscriptionHandle objects.
        """
        # Handle bulk registration
        if hasattr(target, '__iter__') and not isinstance(target, (str, bytes)):
            return [self._register_single(dependent, t) for t in target]
        else:
            # Single target registration
            return self._register_single(dependent, target)
            
    def _register_single(self, dependent: Any, observable: Any) -> SubscriptionHandle:
        """Register a single dependency relationship.
        
        Args:
            dependent: The object that depends on the observable.
            observable: The object being observed.
            
        Returns:
            A SubscriptionHandle for the registration.
        """
        # Create a subscription handle
        handle = SubscriptionHandle(dependent, observable)
        
        # Add to the dependency graph
        self._dependencies[observable].add(handle)
        self._reverse_dependencies[dependent].add(handle)
        
        return handle
    
    def unregister(self, handle_or_dependent: Any, target: Any = None) -> None:
        """Unregister a dependency relationship.
        
        Can be called with either:
        1. A SubscriptionHandle
        2. A dependent and target pair
        
        Args:
            handle_or_dependent: Either a SubscriptionHandle or a dependent object.
            target: If handle_or_dependent is a dependent, the target to unregister.
        """
        if target is None and isinstance(handle_or_dependent, SubscriptionHandle):
            # Handle mode: unregister by subscription handle
            handle = handle_or_dependent
            observable = handle.observable
            dependent = handle.dependent
            
            if observable is not None and dependent is not None:
                # Remove from both mappings
                self._dependencies[observable].discard(handle)
                self._reverse_dependencies[dependent].discard(handle)
                
                # Clean up empty sets
                if not self._dependencies[observable]:
                    del self._dependencies[observable]
                if not self._reverse_dependencies[dependent]:
                    del self._reverse_dependencies[dependent]
        elif target is not None:
            # Dependent/target mode: find and unregister the matching handle
            dependent = handle_or_dependent
            
            # Find handles that match the dependent/target pair
            if dependent in self._reverse_dependencies:
                handles_to_remove = []
                for handle in self._reverse_dependencies[dependent]:
                    if handle.observable == target:
                        handles_to_remove.append(handle)
                
                # Unregister each matching handle
                for handle in handles_to_remove:
                    self.unregister(handle)
    
    def unregister_all(self, dependent: Any) -> None:
        """Unregister all dependencies for a dependent.
        
        Args:
            dependent: The dependent object to unregister all subscriptions for.
        """
        if dependent in self._reverse_dependencies:
            handles = list(self._reverse_dependencies[dependent])
            for handle in handles:
                self.unregister(handle)
    
    def raise_event(self, event: ChangeEventProtocol) -> None:
        """Enqueue a change event for later dispatch.
        
        Args:
            event: The change event to enqueue.
        """
        # Check if the event has a namespace
        event_namespace = getattr(event, 'namespace', None)
        
        # If we're in the middle of dispatching events (in a cascade), add to secondary queue
        if hasattr(self, '_processing_batch') and self._processing_batch:
            self._secondary_queue.append(event)
        else:
            # Store in appropriate queue based on namespace
            if event_namespace is None:
                # Global events go to the primary queue
                self._primary_queue.append(event)
            else:
                # Namespaced events go to their respective namespace queue
                self._namespace_queues[event_namespace].append(event)
    
    def register_namespace(self, namespace_id: str, namespace_manager: Any) -> None:
        """Register a namespaced manager with this global manager.
        
        Args:
            namespace_id: The unique identifier for the namespace.
            namespace_manager: The namespaced manager instance.
        """
        self._namespaces[namespace_id] = namespace_manager
    
    def unregister_namespace(self, namespace_id: str) -> None:
        """Unregister a namespaced manager from this global manager.
        
        Args:
            namespace_id: The unique identifier for the namespace to unregister.
        """
        if namespace_id in self._namespaces:
            del self._namespaces[namespace_id]
    
    def set_debug_mode(self, enabled: bool = True) -> None:
        """Enable or disable debug mode for performance monitoring.
        
        Args:
            enabled: Whether to enable debug mode.
        """
        self._debug_mode = enabled
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the dependency manager.
        
        Returns:
            A dictionary of performance metrics.
        """
        return dict(self._perf_metrics)
    
    def compute_pruned_dependencies(self, visible: Set[Any]) -> Dict[Any, Set[Any]]:
        """Compute a pruned dependency graph based on visibility.
        
        This optimization creates a subgraph of the dependency graph that only
        includes dependencies that are visible or that have visible dependents.
        
        Args:
            visible: Set of objects that are visible.
            
        Returns:
            A pruned dependency graph mapping observables to visible dependents.
        """
        # Start with objects that are directly visible
        pruned_graph = {}
        visited = set()
        processing_queue = deque(visible)
        
        # Traverse the dependency graph in reverse, from dependents to observables
        while processing_queue:
            dependent = processing_queue.popleft()
            
            # Skip if already processed
            if dependent in visited:
                continue
                
            visited.add(dependent)
            
            # Get observables this dependent depends on
            if dependent in self._reverse_dependencies:
                observables = set()
                
                for handle in self._reverse_dependencies[dependent]:
                    if handle.is_valid() and handle.observable is not None:
                        observable = handle.observable
                        observables.add(observable)
                        
                        # Add this dependent to the pruned graph for this observable
                        if observable not in pruned_graph:
                            pruned_graph[observable] = set()
                        pruned_graph[observable].add(dependent)
                        
                        # Add the observable to the processing queue to continue traversal
                        # Only if it's not already visited
                        if observable not in visited:
                            processing_queue.append(observable)
        
        return pruned_graph
    
    def dispatch_events(self, visible: Optional[Set[Any]] = None, 
                       namespace_filter: Optional[Set[str]] = None,
                       intra_tick_cascade: bool = True, 
                       delegate_to_namespaces: bool = True) -> None:
        """Dispatch all queued events to their dependents.
        
        Args:
            visible: Optional set of objects that are visible and should receive events.
            namespace_filter: Optional set of namespaces to filter events by.
            intra_tick_cascade: Whether to handle cascading events within this tick.
            delegate_to_namespaces: Whether to delegate events to registered namespaces.
                                   This is only relevant for the global dependency manager.
        """
        start_time = time.time()
        
        # OPTIMIZATION: Update visibility cache if visibility has changed
        if visible is not None and visible != self._last_visible_set:
            self._last_visible_set = visible
            # Compute pruned dependency graph based on new visibility
            self._pruned_dependency_cache = self.compute_pruned_dependencies(visible)
        
        # Collect all events to dispatch based on namespace filtering
        events_to_dispatch = []
        
        # Get current namespace context, if any
        current_namespace = None
        if namespace_filter and len(namespace_filter) == 1:
            current_namespace = next(iter(namespace_filter))
        
        # Handle global events (those with no namespace)
        # We keep these in the queue unless we're processing the global scope
        global_events = list(self._primary_queue)
        processed_global_events = []
        
        if global_events:
            if not current_namespace:
                # If we're dispatching in global scope, process all global events
                # and clear the global queue
                events_to_dispatch.extend(global_events)
                self._primary_queue.clear()
            else:
                # If we're dispatching in a namespace, only process global events
                # that haven't been processed by this namespace yet
                for event in global_events:
                    if hasattr(event, 'id') and event.id:
                        event_id = event.id
                    else:
                        # Generate a unique ID for this event if it doesn't have one
                        event_id = str(id(event))
                        if hasattr(event, 'id'):
                            event.id = event_id
                    
                    # If this namespace hasn't processed this event yet, include it
                    if current_namespace not in self._processed_events.get(event_id, set()):
                        events_to_dispatch.append(event)
                        processed_global_events.append(event)
                        # Mark this event as processed by this namespace
                        self._processed_events[event_id].add(current_namespace)
        
        # Include events from specific namespaces if requested
        if namespace_filter:
            # Only include events from the specified namespaces
            for ns_id in namespace_filter:
                if ns_id in self._namespace_queues and self._namespace_queues[ns_id]:
                    ns_events = list(self._namespace_queues[ns_id])
                    self._namespace_queues[ns_id].clear()
                    events_to_dispatch.extend(ns_events)
        elif not self._delegating_to_namespaces:
            # If no namespace filter and this is a direct call (not delegation),
            # include events from all namespaces
            for ns_id, queue in self._namespace_queues.items():
                if queue:
                    ns_events = list(queue)
                    queue.clear()
                    events_to_dispatch.extend(ns_events)
            
            # Also clean up the processed events tracking when doing a full dispatch
            self._processed_events.clear()
        
        # Dispatch the collected events
        if events_to_dispatch:
            # OPTIMIZATION: Use the pruned dependency graph if visibility is enabled
            if visible is not None and self._pruned_dependency_cache:
                # If we have a pruned dependency graph, use it for efficient dispatch
                self._dispatch_events_batch_pruned(events_to_dispatch, self._pruned_dependency_cache, namespace_filter)
            else:
                # Otherwise, use the standard dispatch method
                self._dispatch_events_batch(events_to_dispatch, visible, namespace_filter)
        
        # Update performance metrics
        end_time = time.time()
        dispatch_time = end_time - start_time
        self._perf_metrics['total_dispatch_time'] += dispatch_time
        self._perf_metrics['dispatch_count'] += 1
        
        if self._debug_mode:
            print(f"Dispatch took {dispatch_time * 1000:.2f}ms for {len(events_to_dispatch)} events")
        
        # Handle cascading events if enabled
        if intra_tick_cascade and self._secondary_queue:
            iterations = 0
            while self._secondary_queue and iterations < self._max_iterations:
                # Process secondary queue
                cascading_events = list(self._secondary_queue)
                self._secondary_queue.clear()
                
                # Dispatch cascading events
                self._dispatch_events_batch(cascading_events, visible, namespace_filter)
                
                iterations += 1
                
            # If we hit the iteration limit, move any remaining events 
            # back to their appropriate queues based on namespace
            if self._secondary_queue:
                while self._secondary_queue:
                    event = self._secondary_queue.popleft()
                    # Re-raise the event to place it in the appropriate queue
                    self.raise_event(event)
                    
        # Delegate to registered namespaces if appropriate
        if delegate_to_namespaces and not self._delegating_to_namespaces and self._namespaces:
            try:
                self._delegating_to_namespaces = True
                
                # If a namespace filter is provided, only delegate to those namespaces
                namespaces_to_delegate = namespace_filter or self._namespaces.keys()
                
                for ns_id in namespaces_to_delegate:
                    if ns_id in self._namespaces:
                        # Call dispatch_events on the namespaced manager
                        # We pass along the visible set but not the namespace filter
                        # since the namespaced manager only cares about its own namespace
                        self._namespaces[ns_id].dispatch_events(
                            visible=visible,
                            intra_tick_cascade=intra_tick_cascade
                        )
            finally:
                self._delegating_to_namespaces = False
    
    def _dispatch_events_batch(self, events: List[ChangeEventProtocol], 
                              visible: Optional[Set[Any]], 
                              namespace_filter: Optional[Set[str]]) -> None:
        """Dispatch a batch of events to their dependents.
        
        Args:
            events: List of events to dispatch.
            visible: Optional set of objects that are visible and should receive events.
            namespace_filter: Optional set of namespaces to filter events by.
        """
        start_time = time.time()
        
        if not events:
            return
            
        # Filter events by namespace if a namespace filter is provided
        if namespace_filter:
            filtered_events = []
            for event in events:
                # If the event has no namespace, it's considered part of the global namespace
                # If the event has a namespace, check if it's in the filter
                event_namespace = getattr(event, 'namespace', None)
                if event_namespace is None or event_namespace in namespace_filter:
                    filtered_events.append(event)
            events = filtered_events
            
            # If no events remain after filtering, return early
            if not events:
                return
        
        # PERFORMANCE OPTIMIZATION: Deduplicate events by (event_type, source)
        # This reduces redundant processing when multiple events of the same type
        # are raised from the same source
        original_count = len(events)
        deduplicated_events = {}
        for event in events:
            # Use (event_type, source) as the deduplication key
            dedup_key = (event.event_type, event.source)
            
            # If we already have an event with this key, merge metadata if possible
            if dedup_key in deduplicated_events:
                existing_event = deduplicated_events[dedup_key]
                if hasattr(existing_event, 'metadata') and hasattr(event, 'metadata'):
                    # Merge metadata, keeping the latest values
                    existing_event.metadata.update(event.metadata)
            else:
                # Otherwise, keep this event
                deduplicated_events[dedup_key] = event
        
        # Convert back to list after deduplication
        events = list(deduplicated_events.values())
        
        # Update deduplication metrics
        deduplication_savings = original_count - len(events)
        self._perf_metrics['deduplication_savings'] += deduplication_savings
        self._perf_metrics['events_processed'] += len(events)
        
        # Group events by source
        events_by_source: Dict[Any, List[ChangeEventProtocol]] = defaultdict(list)
        for event in events:
            events_by_source[event.source].append(event)
            
        # Build the dependency subgraph for topological sorting
        # This is a graph of dependencies affected by the current events
        dependency_subgraph = {}
        reverse_subgraph = {}
        affected_dependents = set()
        
        # For each source, find its dependents and build the subgraph
        for source, _ in events_by_source.items():
            # Skip if source is not in our dependency graph
            if source not in self._dependencies:
                continue
            
            # Get all valid handles for this source
            handles = [h for h in self._dependencies[source] if h.is_valid()]
            
            # Filter by namespace and visibility
            valid_dependents = []
            for handle in handles:
                # Skip invalid handles or filtered namespaces
                if not handle.is_valid():
                    # Clean up invalid handles
                    self.unregister(handle)
                    continue
                
                if namespace_filter and handle.namespace not in namespace_filter:
                    continue
                
                dependent = handle.dependent
                
                # Skip if not visible (if visibility filtering is enabled)
                if visible is not None and dependent not in visible:
                    continue
                
                valid_dependents.append(dependent)
                affected_dependents.add(dependent)
            
            # Add to subgraph
            for dependent in valid_dependents:
                # In the reverse subgraph, source depends on dependent
                if source not in reverse_subgraph:
                    reverse_subgraph[source] = set()
                reverse_subgraph[source].add(dependent)
                
                # In the dependency subgraph, dependent depends on source
                if dependent not in dependency_subgraph:
                    dependency_subgraph[dependent] = set()
                dependency_subgraph[dependent].add(source)
        
        # Find cycles and sort dependents topologically
        if affected_dependents:
            # Identify cycles in the dependency subgraph
            components = identify_strongly_connected_components(dependency_subgraph)
            cycles_detected = any(len(component) > 1 for component in components)
            
            if cycles_detected:
                # Break cycles if found
                acyclic_graph = break_cycles(dependency_subgraph, components)
                # Use the acyclic graph for topological sorting
                sorted_dependents, _ = topological_sort(acyclic_graph)
            else:
                # No cycles, can directly sort
                sorted_dependents, _ = topological_sort(dependency_subgraph)
            
            # Map of dependent to the events it should receive
            dependent_events: Dict[Any, List[ChangeEventProtocol]] = defaultdict(list)
            
            # For each source, find its dependents and map events
            for source, source_events in events_by_source.items():
                # Skip if source is not in our reverse subgraph
                if source not in reverse_subgraph:
                    continue
                
                # Add events to each dependent's batch
                for dependent in reverse_subgraph[source]:
                    for event in source_events:
                        dependent_events[dependent].append(event)
            
            # Deliver events to each dependent in topological order
            self._processing_batch = True
            try:
                for dependent in sorted_dependents:
                    if dependent in dependent_events and isinstance(dependent, ChangeProcessorProtocol):
                        events_batch = dependent_events[dependent]
                        # During this call, new events may be raised and added to secondary queue
                        try:
                            dependent.process_change(events_batch)
                        except Exception as e:
                            # TODO: Add proper logging
                            print(f"Error processing change events: {e}")
            finally:
                self._processing_batch = False
        
        end_time = time.time()
        # Optional: Log the time taken for batch dispatch (useful for performance monitoring)
        if hasattr(self, '_debug_mode') and self._debug_mode:
            print(f"Batch dispatch: {len(events)} events to {len(affected_dependents)} dependents in {(end_time - start_time) * 1000:.2f}ms")
    
    def _dispatch_events_batch_pruned(self, events: List[ChangeEventProtocol],
                                    pruned_graph: Dict[Any, Set[Any]],
                                    namespace_filter: Optional[Set[str]] = None) -> None:
        """Dispatch a batch of events using a pre-computed pruned dependency graph.
        
        This is an optimized version of _dispatch_events_batch that uses a pre-computed
        pruned dependency graph for faster event dispatch when visibility filtering is enabled.
        
        Args:
            events: List of events to dispatch.
            pruned_graph: A pre-computed graph mapping observables to their visible dependents.
            namespace_filter: Optional set of namespaces to filter events by.
        """
        start_time = time.time()
        
        if not events:
            return
            
        # Filter events by namespace if a namespace filter is provided
        if namespace_filter:
            filtered_events = []
            for event in events:
                event_namespace = getattr(event, 'namespace', None)
                if event_namespace is None or event_namespace in namespace_filter:
                    filtered_events.append(event)
            events = filtered_events
            
            if not events:
                return
                
        # PERFORMANCE OPTIMIZATION: Deduplicate events
        original_count = len(events)
        deduplicated_events = {}
        for event in events:
            dedup_key = (event.event_type, event.source)
            if dedup_key in deduplicated_events:
                existing_event = deduplicated_events[dedup_key]
                if hasattr(existing_event, 'metadata') and hasattr(event, 'metadata'):
                    existing_event.metadata.update(event.metadata)
            else:
                deduplicated_events[dedup_key] = event
                
        events = list(deduplicated_events.values())
        
        # Update deduplication metrics
        deduplication_savings = original_count - len(events)
        self._perf_metrics['deduplication_savings'] += deduplication_savings
        self._perf_metrics['events_processed'] += len(events)
        
        # Group events by source
        events_by_source = defaultdict(list)
        for event in events:
            events_by_source[event.source].append(event)
            
        # Fast path: Map events directly to visible dependents using pruned graph
        affected_dependents = set()
        dependency_subgraph = {}
        dependent_events = defaultdict(list)
        
        # For each source with events, check if it's in the pruned graph
        for source, source_events in events_by_source.items():
            # Skip sources not in the pruned graph
            if source not in pruned_graph:
                continue
                
            # Get visible dependents for this source from pruned graph
            visible_dependents = pruned_graph[source]
            
            # Filter by namespace if needed
            if namespace_filter:
                # Get handles for this source to check namespaces
                source_handles = self._dependencies.get(source, set())
                for dependent in visible_dependents:
                    # Find the handle connecting source to dependent
                    namespace_match = False
                    for handle in source_handles:
                        if handle.dependent == dependent and handle.is_valid():
                            if handle.namespace is None or handle.namespace in namespace_filter:
                                namespace_match = True
                                break
                                
                    if namespace_match:
                        affected_dependents.add(dependent)
                        # Build dependency graph for topological sort
                        if dependent not in dependency_subgraph:
                            dependency_subgraph[dependent] = set()
                        dependency_subgraph[dependent].add(source)
                        
                        # Map events to this dependent
                        for event in source_events:
                            dependent_events[dependent].append(event)
            else:
                # No namespace filtering, use all visible dependents
                affected_dependents.update(visible_dependents)
                
                # Build dependency graph and map events
                for dependent in visible_dependents:
                    # Build dependency graph for topological sort
                    if dependent not in dependency_subgraph:
                        dependency_subgraph[dependent] = set()
                    dependency_subgraph[dependent].add(source)
                    
                    # Map events to this dependent
                    for event in source_events:
                        dependent_events[dependent].append(event)
        
        # Topologically sort and deliver events
        if affected_dependents:
            # Find and handle cycles
            components = identify_strongly_connected_components(dependency_subgraph)
            cycles_detected = any(len(component) > 1 for component in components)
            
            if cycles_detected:
                acyclic_graph = break_cycles(dependency_subgraph, components)
                sorted_dependents, _ = topological_sort(acyclic_graph)
            else:
                sorted_dependents, _ = topological_sort(dependency_subgraph)
                
            # Deliver events in topological order
            self._processing_batch = True
            try:
                for dependent in sorted_dependents:
                    if dependent in dependent_events and isinstance(dependent, ChangeProcessorProtocol):
                        events_batch = dependent_events[dependent]
                        try:
                            dependent.process_change(events_batch)
                        except Exception as e:
                            print(f"Error processing change events: {e}")
            finally:
                self._processing_batch = False
                
        end_time = time.time()
        if self._debug_mode:
            print(f"Pruned batch dispatch: {len(events)} events to {len(affected_dependents)} dependents in {(end_time - start_time) * 1000:.2f}ms")
            
    def clear(self, namespace: Optional[str] = None) -> None:
        """Clear all dependencies or those in a specific namespace.
        
        Args:
            namespace: Optional namespace to clear. If None, clears all dependencies.
        """
        if namespace is None:
            # Clear everything
            self._dependencies.clear()
            self._reverse_dependencies.clear()
            self._primary_queue.clear()
            self._secondary_queue.clear()
        else:
            # Find all handles in the namespace
            handles_to_remove = []
            
            # Collect handles from both mappings
            for handles in self._dependencies.values():
                for handle in handles:
                    if handle.namespace == namespace:
                        handles_to_remove.append(handle)
                        
            # Unregister each handle
            for handle in handles_to_remove:
                self.unregister(handle)
