"""
Protocols for the dependency management system.

This module defines the structural typing protocols that define the interfaces
for change events and processors in the dependency system.
"""

from typing import Protocol, Any, Dict, List, runtime_checkable


@runtime_checkable
class ChangeEventProtocol(Protocol):
    """Defines the interface for all change events.
    
    Any object that adheres to this protocol can be used as a change event
    in the dependency management system.
    """
    event_type: str               # e.g. "image_updated", "size_changed"
    source: Any                   # Object that emitted the change
    metadata: Dict[str, Any]      # Additional data (crop rect, dimensions, timestamp)


@runtime_checkable
class ChangeProcessorProtocol(Protocol):
    """Defines the interface for any object that processes change events.
    
    Any object that implements this protocol can receive and process change 
    events from the dependency management system.
    """
    def process_change(self, events: List[ChangeEventProtocol]) -> None:
        """Process a batch of change events.
        
        Args:
            events: A list of change events to process.
        """
        ...
