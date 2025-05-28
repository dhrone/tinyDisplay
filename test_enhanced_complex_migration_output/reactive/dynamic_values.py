"""
Dynamic Values Engine with asteval and RxPY integration.
"""

import ast
import time
import asteval
from typing import Dict, Any, Set, List, Optional, Callable
from dataclasses import dataclass
import networkx as nx
from rx import Observable
from rx.subject import Subject

@dataclass
class DynamicValueInfo:
    """Information about a dynamic value"""
    name: str
    expression: str
    dependencies: Set[str]
    compiled_expr: Optional[asteval.Interpreter]
    subscribers: Set[str]
    last_result: Any = None
    last_update: float = 0

class DynamicValuesEngine:
    """Engine for evaluating dynamic expressions with dependency tracking"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.dynamic_values: Dict[str, DynamicValueInfo] = {}
        self.dependency_graph = nx.DiGraph()
        self.observables: Dict[str, Subject] = {}
        self.expression_cache: Dict[str, asteval.Interpreter] = {}
    
    def create_dynamic_value(self, name: str, expression: str) -> str:
        """Create new dynamic value from expression"""
        
        # Extract dependencies
        dependencies = self._extract_dependencies(expression)
        
        # Create dynamic value info
        dv_info = DynamicValueInfo(
            name=name,
            expression=expression,
            dependencies=dependencies,
            compiled_expr=None,
            subscribers=set()
        )
        
        self.dynamic_values[name] = dv_info
        self.observables[name] = Subject()
        
        # Add to dependency graph
        self.dependency_graph.add_node(name)
        for dep in dependencies:
            self.dependency_graph.add_edge(dep, name)
        
        # Subscribe to data dependencies
        for dep in dependencies:
            self.data_manager.subscribe(dep, self._on_dependency_change)
        
        return name
    
    def get_value(self, name: str, timestamp: Optional[float] = None) -> Any:
        """Get current value of dynamic expression"""
        if name not in self.dynamic_values:
            return None
        
        dv_info = self.dynamic_values[name]
        
        # Check if we need to recompute
        if self._needs_recomputation(dv_info, timestamp):
            result = self._evaluate_expression(dv_info, timestamp)
            dv_info.last_result = result
            dv_info.last_update = timestamp or time.time()
            
            # Notify subscribers
            self.observables[name].on_next(result)
            
            return result
        
        return dv_info.last_result
    
    def subscribe(self, name: str, widget_id: str) -> Observable:
        """Subscribe to dynamic value changes"""
        if name in self.dynamic_values:
            self.dynamic_values[name].subscribers.add(widget_id)
        
        return self.observables.get(name, Subject())
    
    def unsubscribe(self, name: str, widget_id: str):
        """Unsubscribe from dynamic value"""
        if name in self.dynamic_values:
            self.dynamic_values[name].subscribers.discard(widget_id)
    
    def _extract_dependencies(self, expression: str) -> Set[str]:
        """Extract data dependencies from expression using AST"""
        dependencies = set()
        
        try:
            tree = ast.parse(expression, mode='eval')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    # Handle sensor.temperature, weather.humidity, etc.
                    if isinstance(node.value, ast.Name):
                        dep = f"{node.value.id}.{node.attr}"
                        dependencies.add(dep)
                elif isinstance(node, ast.Subscript):
                    # Handle sensor['temperature'] if key is literal
                    if isinstance(node.value, ast.Name) and isinstance(node.slice, ast.Constant):
                        dep = f"{node.value.id}.{node.slice.value}"
                        dependencies.add(dep)
        
        except SyntaxError:
            # Fallback to simple pattern matching
            import re
            dot_refs = re.findall(r'(\w+\.\w+)', expression)
            dependencies.update(dot_refs)
        
        return dependencies
    
    def _needs_recomputation(self, dv_info: DynamicValueInfo, timestamp: Optional[float]) -> bool:
        """Check if dynamic value needs recomputation"""
        if dv_info.last_result is None:
            return True
        
        # Check if any dependencies have changed
        for dep in dv_info.dependencies:
            latest_data = self.data_manager.get_current_value(dep)
            if latest_data != dv_info.last_result:  # Simplified check
                return True
        
        return False
    
    def _evaluate_expression(self, dv_info: DynamicValueInfo, timestamp: Optional[float]) -> Any:
        """Evaluate dynamic expression"""
        
        # Get or create compiled expression
        if dv_info.compiled_expr is None:
            dv_info.compiled_expr = asteval.Interpreter()
        
        # Build context with current data
        context = {}
        for dep in dv_info.dependencies:
            value = self.data_manager.get_current_value(dep)
            
            # Handle dot notation (sensor.temperature -> context['sensor']['temperature'])
            if '.' in dep:
                parts = dep.split('.')
                if parts[0] not in context:
                    context[parts[0]] = {}
                context[parts[0]][parts[1]] = value
            else:
                context[dep] = value
        
        # Add timestamp if provided
        if timestamp:
            context['timestamp'] = timestamp
            context['time'] = timestamp
        
        try:
            return dv_info.compiled_expr.eval(dv_info.expression, context)
        except Exception as e:
            print(f"Error evaluating expression '{dv_info.expression}': {e}")
            return None
    
    def _on_dependency_change(self, stream_id: str, new_value: Any):
        """Handle dependency data change"""
        
        # Find all dynamic values that depend on this stream
        affected_values = []
        for name, dv_info in self.dynamic_values.items():
            if stream_id in dv_info.dependencies:
                affected_values.append(name)
        
        # Invalidate and potentially recompute affected values
        for name in affected_values:
            if self.dynamic_values[name].subscribers:  # Only if someone is listening
                self.get_value(name)  # This will trigger recomputation
