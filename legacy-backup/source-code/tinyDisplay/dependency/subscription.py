"""
Subscription management for the dependency system.

This module provides the SubscriptionHandle class that represents a
registered dependency relationship between an observable and a dependent.
"""

from typing import Any, Optional, Hashable
import weakref
import uuid


class SubscriptionHandle:
    """Handle to a subscription between a dependent and an observable.
    
    This class represents a subscription relationship and provides a way to
    unregister the subscription later. It uses weak references to avoid
    memory leaks.
    """
    
    def __init__(self, dependent: Any, observable: Any, namespace: Optional[str] = None):
        """Initialize a new subscription handle.
        
        Args:
            dependent: The object that depends on the observable.
            observable: The object being observed.
            namespace: Optional namespace this subscription belongs to.
        """
        self.id = str(uuid.uuid4())
        # Use weak references to avoid memory leaks
        self.dependent_ref = weakref.ref(dependent)
        self.observable_ref = weakref.ref(observable)
        self.namespace = namespace
        
    @property
    def dependent(self) -> Any:
        """Get the dependent object if it still exists."""
        return self.dependent_ref() if self.dependent_ref is not None else None
        
    @property
    def observable(self) -> Any:
        """Get the observable object if it still exists."""
        return self.observable_ref() if self.observable_ref is not None else None
        
    def is_valid(self) -> bool:
        """Check if both dependent and observable still exist."""
        return self.dependent is not None and self.observable is not None
        
    def __eq__(self, other):
        """Check if this handle is equal to another."""
        if not isinstance(other, SubscriptionHandle):
            return False
        return self.id == other.id
        
    def __hash__(self):
        """Hash based on the unique ID."""
        return hash(self.id)
