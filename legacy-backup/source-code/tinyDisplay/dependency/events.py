"""
Change event implementations for the dependency management system.

This module provides concrete implementations of the ChangeEventProtocol
for standard change events in the tinyDisplay system.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .protocols import ChangeEventProtocol


@dataclass
class ChangeEvent:
    """Standard implementation of the ChangeEventProtocol.
    
    This class provides a concrete implementation of the ChangeEventProtocol
    that can be used for most change events in the system.
    """
    event_type: str
    source: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    namespace: Optional[str] = None
    id: Optional[str] = None

    def __post_init__(self):
        """Initialize the metadata dict if not provided."""
        if self.metadata is None:
            self.metadata = {}
        
        # Add timestamp to metadata if not already present
        if 'timestamp' not in self.metadata:
            self.metadata['timestamp'] = self.timestamp


class VisibilityChangeEvent(ChangeEvent):
    """Specialized event for visibility changes.
    
    This event is raised when the visibility of an object changes. It extends
    the base ChangeEvent with a boolean 'visible' field for convenience.
    
    Args:
        source: The source object that raised this event.
        visible: The new visibility state (default: True).
        **kwargs: Additional arguments to pass to the parent class.
    """
    
    def __init__(self, source: Any, visible: bool = True, **kwargs):
        """Initialize the event with source and visibility."""
        # Set default values for ChangeEvent
        kwargs.setdefault('event_type', 'visibility_change')
        
        # Initialize the parent class
        super().__init__(source=source, **kwargs)
        
        # Set our custom fields
        self.visible = visible
        self.metadata['visible'] = visible
