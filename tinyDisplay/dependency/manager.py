"""
Core dependency manager implementation.

This module provides the DependencyManager class that handles dependency
registration, change event propagation, and notification dispatch.
"""

from typing import Any, Dict, List, Set, Optional, Tuple, Iterable, Union
import weakref
from collections import defaultdict, deque

from .protocols import ChangeEventProtocol, ChangeProcessorProtocol
from .subscription import SubscriptionHandle


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
            self._dispatch_events_batch(events_to_dispatch, visible, namespace_filter)
        
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
            
        # Group events by source
        events_by_source: Dict[Any, List[ChangeEventProtocol]] = defaultdict(list)
        for event in events:
            events_by_source[event.source].append(event)
            
        # Get affected dependents
        dependent_events: Dict[Any, List[ChangeEventProtocol]] = defaultdict(list)
        notified = set()
        
        # For each source, find its dependents
        for source, source_events in events_by_source.items():
            # Skip if source is not in our dependency graph
            if source not in self._dependencies:
                continue
                
            # Get all valid handles for this source
            handles = self._dependencies[source]
            for handle in list(handles):  # Use a copy for safe iteration
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
                    
                # Add events to this dependent's batch
                if dependent not in notified:
                    notified.add(dependent)
                    
                for event in source_events:
                    dependent_events[dependent].append(event)
        
        # Deliver events to each dependent
        self._processing_batch = True
        try:
            for dependent, events_batch in dependent_events.items():
                if isinstance(dependent, ChangeProcessorProtocol):
                    # During this call, new events may be raised and added to secondary queue
                    try:
                        dependent.process_change(events_batch)
                    except Exception as e:
                        # TODO: Add proper logging
                        print(f"Error processing change events: {e}")
        finally:
            self._processing_batch = False
            
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
