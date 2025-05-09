"""
Timeline Coordination Manager for tinyDisplay.

This module provides a central coordination system for interdependent
marquee timelines with SYNC and WAIT_FOR relationships.
"""

import logging
from typing import Dict, Set, Tuple, List, Optional, Any


class TimelineCoordinationManager:
    """
    Manages timeline coordination between interdependent marquee widgets.
    
    This class resolves dependencies between widgets that use SYNC and WAIT_FOR
    statements to coordinate their animations. It ensures deterministic rendering
    by precomputing all timelines with their interdependencies resolved.
    """
    
    def __init__(self):
        """Initialize the coordination manager."""
        self.widgets = {}  # Maps widget_id -> widget reference
        self.sync_events = {}  # Maps event_name -> (widget_id, tick_position)
        self.dependencies = {}  # Maps widget_id -> set of dependent widget_ids
        self.resolved = set()  # Set of widget_ids with resolved timelines
        self.logger = logging.getLogger("tinyDisplay.render.coordination")
        
    def register_widget(self, widget_id, widget):
        """
        Register a widget with the coordination manager.
        
        Args:
            widget_id: Unique identifier for the widget
            widget: Reference to the widget object
        """
        self.logger.debug(f"Registering widget with ID {widget_id}")
        self.widgets[widget_id] = widget
        self.dependencies[widget_id] = set()
        
    def register_sync_event(self, widget_id, event_name, tick_position):
        """
        Register a SYNC event from a widget.
        
        Args:
            widget_id: ID of the widget that generates the event
            event_name: Name of the SYNC event
            tick_position: Timeline position (tick) when the event occurs
        """
        self.logger.debug(f"Registering SYNC event '{event_name}' from widget {widget_id} at tick {tick_position}")
        self.sync_events[event_name] = (widget_id, tick_position)
        
    def register_dependency(self, dependent_widget_id, event_name):
        """
        Register that a widget depends on a SYNC event.
        
        Args:
            dependent_widget_id: ID of the widget waiting for the event
            event_name: Name of the SYNC event being waited for
        """
        if event_name in self.sync_events:
            source_widget_id, _ = self.sync_events[event_name]
            self.logger.debug(f"Registering dependency: Widget {dependent_widget_id} depends on widget {source_widget_id} via event '{event_name}'")
            self.dependencies[source_widget_id].add(dependent_widget_id)
        else:
            self.logger.warning(f"Could not register dependency for event '{event_name}' - event not registered yet")
            
    def get_sync_event_position(self, event_name):
        """
        Get the tick position for a SYNC event.
        
        Args:
            event_name: Name of the SYNC event
            
        Returns:
            Tick position where the event occurs, or None if event not registered
        """
        if event_name in self.sync_events:
            _, tick_position = self.sync_events[event_name]
            return tick_position
        return None
        
    def resolve_timelines(self):
        """
        Resolve all widget timelines based on dependencies.
        
        This method implements a topological sort to resolve widget timelines in 
        dependency order. For circular dependencies, it breaks the cycle by choosing
        a widget to resolve first.
        """
        self.logger.info("Resolving widget timelines...")
        self.resolved.clear()
        
        # Build a dependency graph
        dependency_graph = {}
        for widget_id, dependents in self.dependencies.items():
            dependency_graph[widget_id] = set(dependents)
            
        # Make sure all widgets are in the graph (even without dependencies)
        for widget_id in self.widgets:
            if widget_id not in dependency_graph:
                dependency_graph[widget_id] = set()
                
        # Find an ordering that respects dependencies
        iteration = 0
        max_iterations = len(self.widgets) * 2  # Safeguard against infinite loops
        
        while len(self.resolved) < len(self.widgets) and iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"Resolution iteration {iteration}, resolved so far: {len(self.resolved)}/{len(self.widgets)}")
            
            # Process widgets with no unresolved dependencies
            ready_widgets = []
            for widget_id in self.widgets:
                if widget_id not in self.resolved:
                    deps = set()
                    for dep_id in dependency_graph.get(widget_id, set()):
                        if dep_id not in self.resolved:
                            deps.add(dep_id)
                    
                    if not deps:
                        ready_widgets.append(widget_id)
                        
            # If no widgets are ready, we have a circular dependency
            if not ready_widgets:
                self.logger.warning("Detected circular dependency, breaking cycle")
                self._resolve_circular_dependencies(dependency_graph)
                continue
                
            # Process ready widgets
            for widget_id in ready_widgets:
                self.logger.debug(f"Resolving timeline for widget {widget_id}")
                self._resolve_widget_timeline(widget_id)
                self.resolved.add(widget_id)
        
        if len(self.resolved) < len(self.widgets):
            self.logger.error(f"Failed to resolve all widget timelines. Resolved {len(self.resolved)}/{len(self.widgets)}")
        else:
            self.logger.info(f"Successfully resolved all {len(self.widgets)} widget timelines")
    
    def _resolve_widget_timeline(self, widget_id):
        """
        Resolve a single widget's timeline.
        
        Args:
            widget_id: ID of the widget to resolve
        """
        widget = self.widgets[widget_id]
        # Call the widget's method for computing timeline with resolved events
        if hasattr(widget, '_compute_timeline_with_resolved_events'):
            widget._compute_timeline_with_resolved_events(self)
        else:
            self.logger.warning(f"Widget {widget_id} does not implement _compute_timeline_with_resolved_events")
    
    def _resolve_circular_dependencies(self, dependency_graph):
        """
        Handle circular dependencies by breaking cycles.
        
        Args:
            dependency_graph: The dependency graph (widget_id -> set of dependent widget_ids)
        """
        # Find a cycle
        visited = set()
        path = []
        start_node = next(iter(dependency_graph.keys()))
        cycle = self._find_cycle(dependency_graph, start_node, visited, path)
        
        if cycle:
            # Break the cycle by resolving one widget without its dependencies
            widget_id = cycle[0]
            self.logger.debug(f"Breaking cycle by resolving widget {widget_id} first")
            self._resolve_widget_timeline(widget_id)
            self.resolved.add(widget_id)
        else:
            # If no cycle found but we have a deadlock, just pick an arbitrary unresolved widget
            for widget_id in self.widgets:
                if widget_id not in self.resolved:
                    self.logger.debug(f"No cycle found but deadlock detected, resolving widget {widget_id} first")
                    self._resolve_widget_timeline(widget_id)
                    self.resolved.add(widget_id)
                    break
    
    def _find_cycle(self, graph, node, visited, path):
        """
        Find a cycle in the dependency graph using DFS.
        
        Args:
            graph: The dependency graph
            node: Current node being visited
            visited: Set of visited nodes
            path: Current path in the DFS
            
        Returns:
            List representing a cycle if found, None otherwise
        """
        visited.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                cycle = self._find_cycle(graph, neighbor, visited, path)
                if cycle:
                    return cycle
            elif neighbor in path:
                # Found a cycle
                cycle_start = path.index(neighbor)
                return path[cycle_start:]
        
        path.pop()
        return None
        
    def mark_widget_for_recalculation(self, widget_id):
        """
        Mark a widget and its dependents for recalculation.
        
        Args:
            widget_id: ID of the widget that needs recalculation
        """
        if widget_id in self.resolved:
            self.logger.debug(f"Marking widget {widget_id} for recalculation")
            self.resolved.remove(widget_id)
            
            # Also mark dependents for recalculation
            for dependent_id in self.dependencies.get(widget_id, set()):
                self.mark_widget_for_recalculation(dependent_id)
    
    def clear(self):
        """Clear all registered widgets and events."""
        self.widgets.clear()
        self.sync_events.clear()
        self.dependencies.clear()
        self.resolved.clear()


# Create singleton instance
timeline_manager = TimelineCoordinationManager() 