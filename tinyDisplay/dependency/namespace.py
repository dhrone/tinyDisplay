"""
Namespace support for the dependency management system.

This module provides a NamespacedDependencyManager which acts as a facade over
the global dependency manager but tags all registrations with a namespace identifier.
"""

from typing import Any, Dict, List, Set, Optional, Iterable, Union
import uuid
from collections import defaultdict, deque

from .protocols import ChangeEventProtocol, ChangeProcessorProtocol
from .subscription import SubscriptionHandle
from .manager import DependencyManager, get_global_manager


class NamespacedDependencyManager:
    """A facade over the global dependency manager with namespace isolation.
    
    This class provides a namespaced view of the global dependency manager,
    allowing for modular components and isolated testing environments.
    """
    
    def __init__(self, namespace: Optional[str] = None, global_manager: Optional[DependencyManager] = None):
        """Initialize a new namespaced dependency manager.
        
        Args:
            namespace: The namespace identifier. If None, a unique ID will be generated.
            global_manager: The global dependency manager to use. If None, the default
                           global manager will be used.
        """
        self.namespace_id = namespace or f"ns_{uuid.uuid4()}"
        self._global_manager = global_manager or get_global_manager()
        self._handles: Set[SubscriptionHandle] = set()
        
        # Register this namespace with the global manager
        self._global_manager.register_namespace(self.namespace_id, self)
        
    def register(self, dependent: Any, 
                target: Union[Any, Iterable[Any]]) -> Union[SubscriptionHandle, List[SubscriptionHandle]]:
        """Register a dependency relationship with namespace tagging.
        
        Args:
            dependent: The object that depends on the target(s).
            target: An observable object or list of observable objects.
            
        Returns:
            A SubscriptionHandle or list of SubscriptionHandle objects.
        """
        # Delegate to global manager
        result = self._global_manager.register(dependent, target)
        
        # Tag the handle(s) with this namespace
        if isinstance(result, list):
            for handle in result:
                handle.namespace = self.namespace_id
                self._handles.add(handle)
            return result
        else:
            result.namespace = self.namespace_id
            self._handles.add(result)
            return result
            
    def unregister(self, handle_or_dependent: Any, target: Any = None) -> None:
        """Unregister a dependency relationship.
        
        Args:
            handle_or_dependent: Either a SubscriptionHandle or a dependent object.
            target: If handle_or_dependent is a dependent, the target to unregister.
        """
        # Delegate to global manager
        self._global_manager.unregister(handle_or_dependent, target)
        
        # Remove handle from our tracking if it's a handle
        if target is None and isinstance(handle_or_dependent, SubscriptionHandle):
            self._handles.discard(handle_or_dependent)
    
    def unregister_all(self, dependent: Any) -> None:
        """Unregister all dependencies for a dependent within this namespace.
        
        Args:
            dependent: The dependent object to unregister all subscriptions for.
        """
        # Find all handles for this dependent in our namespace
        handles_to_remove = []
        
        for handle in self._handles:
            if handle.dependent == dependent:
                handles_to_remove.append(handle)
                
        # Unregister each handle
        for handle in handles_to_remove:
            self.unregister(handle)
    
    def raise_event(self, event: ChangeEventProtocol) -> None:
        """Enqueue a change event for later dispatch.
        
        Args:
            event: The change event to enqueue.
        """
        # Set the namespace on the event if it's our standard ChangeEvent
        if hasattr(event, 'namespace') and event.namespace is None:
            event.namespace = self.namespace_id
            
        # Delegate to the global manager
        # All events go to the global manager, which delegates back to namespaces as needed
        self._global_manager.raise_event(event)
    
    def dispatch_events(self, visible: Optional[Set[Any]] = None, 
                      intra_tick_cascade: bool = True) -> None:
        """Dispatch all queued events to their dependents within this namespace.
        
        Args:
            visible: Optional set of objects that are visible and should receive events.
        """
        # Delegate to the global manager but filter by this namespace
        # This ensures consistency and that the global manager drives the event dispatch
        # Note that we disable delegation to namespaces to prevent infinite recursion
        self._global_manager.dispatch_events(
            visible=visible,
            namespace_filter={self.namespace_id},
            intra_tick_cascade=intra_tick_cascade,
            delegate_to_namespaces=False
        )
    
    # We no longer need the _dispatch_events_batch method since we're delegating to the global manager
    
    def clear(self) -> None:
        """Clear all dependencies in this namespace."""
        # Delegate to global manager with namespace filter
        self._global_manager.clear(namespace=self.namespace_id)
        self._handles.clear()
        
    def __del__(self):
        """Clean up when this namespace manager is garbage collected."""
        try:
            self._global_manager.unregister_namespace(self.namespace_id)
        except:
            # Ignore errors during cleanup
            pass
