"""
Dynamic value system for tinyDisplay.

This module provides a more intuitive way to define dynamic properties
for widgets, with automatic dependency tracking.
"""
import re
import logging

class DynamicValue:
    """Represents a value that should be evaluated at runtime."""
    def __init__(self, expression, dependencies=None):
        self.expression = expression
        self.dependencies = dependencies or self._infer_dependencies(expression)
        self.previous_value = None
        self.changed = False
        
    def _infer_dependencies(self, expression):
        """Attempt to infer dependencies from the expression."""
        dependencies = []
        if isinstance(expression, str):
            # Simple parsing to detect database references like db['key']
            matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\['[^']*'\]", expression)
            dependencies.extend(matches)
        return dependencies
    
    def __repr__(self):
        return f"Dynamic({self.expression})"


class DependencyRegistry:
    """Tracks relationships between widgets and data sources."""
    
    def __init__(self):
        self.dependencies = {}  # data_source -> set(widgets)
        self.widget_dependencies = {}  # widget -> set(data_sources)
        self.logger = logging.getLogger("tinyDisplay")
    
    def register(self, widget, data_source):
        """Register a dependency between widget and data source."""
        if data_source not in self.dependencies:
            self.dependencies[data_source] = set()
        self.dependencies[data_source].add(widget)
        
        if widget not in self.widget_dependencies:
            self.widget_dependencies[widget] = set()
        self.widget_dependencies[widget].add(data_source)
        
        self.logger.debug(f"Registered dependency: {widget.name} depends on {data_source}")
    
    def get_dependent_widgets(self, data_source):
        """Get all widgets that depend on a specific data source."""
        return self.dependencies.get(data_source, set())
    
    def notify_data_change(self, data_source):
        """Mark all widgets dependent on this data for update."""
        affected_widgets = self.get_dependent_widgets(data_source)
        self.logger.debug(f"Data change in {data_source} affects {len(affected_widgets)} widgets")
        
        for widget in affected_widgets:
            widget.mark_for_update()


# Create global registry
dependency_registry = DependencyRegistry()


def dynamic(expression, dependencies=None):
    """Mark a value as dynamic for widget properties.
    
    Args:
        expression: String expression or callable to evaluate at runtime
        dependencies: Optional explicit list of data sources this depends on
    
    Returns:
        DynamicValue object that will be recognized during widget initialization
    """
    return DynamicValue(expression, dependencies) 