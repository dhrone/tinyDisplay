"""
tinyDisplay Dependency Management System

This package implements a comprehensive dependency management system for tinyDisplay.
It handles subscription management, change events, and notification dispatch.
"""

from .manager import DependencyManager, get_global_manager
from .protocols import ChangeEventProtocol, ChangeProcessorProtocol
from .events import ChangeEvent
from .subscription import SubscriptionHandle
from .namespace import NamespacedDependencyManager

__all__ = [
    'DependencyManager',
    'get_global_manager',
    'ChangeEventProtocol',
    'ChangeProcessorProtocol',
    'ChangeEvent',
    'SubscriptionHandle',
    'NamespacedDependencyManager',
]
