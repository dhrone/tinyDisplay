"""
Dynamic value system for tinyDisplay.

This module provides a more intuitive way to define dynamic properties
for widgets, with automatic dependency tracking.

Note: The DynamicValue class has been removed. Please use the dynamic() function
which creates dynamicValue objects from tinyDisplay.utility.evaluator.
"""
import logging
import re
import warnings
from tinyDisplay.utility.variable_dependencies import variable_registry

# Remove the direct import to avoid circular imports
# from tinyDisplay.utility.evaluator import dynamicValue

# NOTE: dynamicValue class has been removed. Use dynamic() function instead,
# which now creates dynamicValue objects from the evaluator module.

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
        
        # Also notify the variable registry with specific field paths
        # This is a best-effort approximation to connect the legacy system with the new system
        field_paths = [f"{data_source}['{key}']" for key in affected_widgets]
        for field_path in field_paths:
            variable_registry.notify_field_change(field_path)


# Create global registry
dependency_registry = DependencyRegistry()


def dynamic(expression, dependencies=None, depends_on=None):
    """Mark a value as dynamic for widget properties.
    
    Args:
        expression: String expression or callable to evaluate at runtime
        dependencies: Optional explicit list of data sources this depends on
        depends_on: Optional dynamicValue or list of dynamicValues that this value depends on
    
    Returns:
        dynamicValue object that will be recognized during widget initialization
        
    Examples:
        Basic usage:
        ```python
        # Simple dependency automatically detected
        progress = dynamic("data['progress']")
        
        # Using explicit dependencies
        counter = dynamic("count")
        double_counter = dynamic("count * 2", depends_on=counter)
        
        # Adding dependencies later
        progress_text = dynamic("f'Progress: {progress}%'")
        progress_text.depends_on(progress)
        
        # Multiple dependencies
        combined = dynamic("value1 + value2")
        combined.depends_on(dynamic_value1, dynamic_value2)
        ```
    """
    # Import dynamicValue here to avoid circular imports
    from tinyDisplay.utility.evaluator import dynamicValue
    
    # Get the global dataset if available
    try:
        from tinyDisplay import global_dataset
        dataset = global_dataset.get_dataset()
    except (ImportError, AttributeError):
        dataset = None
    
    # Create a new dynamicValue with the appropriate parameters
    dv = dynamicValue(
        name=f"dynamic({expression})",
        dataset=dataset,
        source=expression,
        dependencies=dependencies,
        depends_on=depends_on
    )
    
    # Compile the expression if it's a string
    if isinstance(expression, str):
        dv.compile(expression, dynamic=True)
    
    return dv 