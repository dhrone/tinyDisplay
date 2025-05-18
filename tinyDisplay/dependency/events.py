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
