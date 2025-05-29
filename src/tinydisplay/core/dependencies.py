#!/usr/bin/env python3
"""
Dependency Graph Management

Provides sophisticated dependency tracking and update propagation for reactive values,
with cycle detection, batch updates, and performance optimization.
"""

from typing import Dict, Set, List, Optional, Any, Callable, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
import threading
import time
import weakref
from enum import Enum

from .reactive import ReactiveValue, ReactiveChange


class DependencyType(Enum):
    """Types of dependencies between reactive values."""
    DIRECT = "direct"           # Direct dependency
    COMPUTED = "computed"       # Computed dependency
    EXPRESSION = "expression"   # Expression-based dependency
    CONDITIONAL = "conditional" # Conditional dependency


@dataclass
class DependencyEdge:
    """Represents a dependency edge in the graph."""
    from_node: str
    to_node: str
    dependency_type: DependencyType
    weight: float = 1.0
    condition: Optional[Callable[[], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyStats:
    """Statistics for dependency graph performance."""
    total_nodes: int = 0
    total_edges: int = 0
    update_count: int = 0
    batch_count: int = 0
    cycle_detections: int = 0
    average_update_time: float = 0.0
    max_update_time: float = 0.0
    total_update_time: float = 0.0


class DependencyGraph:
    """Manages dependency relationships between reactive values."""
    
    def __init__(self):
        self._nodes: Dict[str, ReactiveValue] = {}
        self._edges: Dict[str, Set[DependencyEdge]] = defaultdict(set)  # from_node -> edges
        self._reverse_edges: Dict[str, Set[DependencyEdge]] = defaultdict(set)  # to_node -> edges
        self._update_queue: deque = deque()
        self._updating: Set[str] = set()
        self._lock = threading.RLock()
        self._batch_updates = False
        self._batch_queue: Set[str] = set()
        self._stats = DependencyStats()
        self._cycle_cache: Dict[Tuple[str, str], bool] = {}
        self._topological_cache: Optional[List[str]] = None
        self._cache_valid = True
        
    def add_node(self, node_id: str, reactive_value: ReactiveValue) -> None:
        """Add a reactive value to the dependency graph."""
        with self._lock:
            self._nodes[node_id] = reactive_value
            self._stats.total_nodes = len(self._nodes)
            self._invalidate_cache()
            
    def remove_node(self, node_id: str) -> None:
        """Remove a reactive value from the dependency graph."""
        with self._lock:
            if node_id in self._nodes:
                # Remove all edges involving this node
                edges_to_remove = []
                
                # Collect outgoing edges
                for edge in self._edges[node_id]:
                    edges_to_remove.append(edge)
                    
                # Collect incoming edges
                for edge in self._reverse_edges[node_id]:
                    edges_to_remove.append(edge)
                    
                # Remove all collected edges
                for edge in edges_to_remove:
                    self.remove_edge(edge.from_node, edge.to_node)
                    
                del self._nodes[node_id]
                self._edges.pop(node_id, None)
                self._reverse_edges.pop(node_id, None)
                self._stats.total_nodes = len(self._nodes)
                self._invalidate_cache()
                
    def add_edge(self, from_node: str, to_node: str, 
                 dependency_type: DependencyType = DependencyType.DIRECT,
                 weight: float = 1.0, condition: Optional[Callable[[], bool]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a dependency edge (from_node affects to_node)."""
        with self._lock:
            if self._would_create_cycle(from_node, to_node):
                self._stats.cycle_detections += 1
                return False
                
            edge = DependencyEdge(
                from_node=from_node,
                to_node=to_node,
                dependency_type=dependency_type,
                weight=weight,
                condition=condition,
                metadata=metadata or {}
            )
            
            self._edges[from_node].add(edge)
            self._reverse_edges[to_node].add(edge)
            self._stats.total_edges += 1
            self._invalidate_cache()
            
            # Set up reactive value dependency
            if from_node in self._nodes and to_node in self._nodes:
                self._nodes[to_node].add_dependency(self._nodes[from_node])
                
            return True
            
    def remove_edge(self, from_node: str, to_node: str) -> bool:
        """Remove a dependency edge."""
        with self._lock:
            edge_to_remove = None
            
            # Find the edge to remove
            for edge in self._edges[from_node]:
                if edge.to_node == to_node:
                    edge_to_remove = edge
                    break
                    
            if edge_to_remove:
                self._edges[from_node].discard(edge_to_remove)
                self._reverse_edges[to_node].discard(edge_to_remove)
                self._stats.total_edges -= 1
                self._invalidate_cache()
                
                # Remove reactive value dependency
                if from_node in self._nodes and to_node in self._nodes:
                    self._nodes[to_node].remove_dependency(self._nodes[from_node])
                    
                return True
                
            return False
            
    def _would_create_cycle(self, from_node: str, to_node: str) -> bool:
        """Check if adding an edge would create a cycle."""
        cache_key = (from_node, to_node)
        if cache_key in self._cycle_cache:
            return self._cycle_cache[cache_key]
            
        # Use DFS to check if to_node can reach from_node
        visited = set()
        stack = [to_node]
        
        while stack:
            current = stack.pop()
            if current == from_node:
                self._cycle_cache[cache_key] = True
                return True
            if current in visited:
                continue
            visited.add(current)
            
            # Add all nodes that current depends on
            for edge in self._edges[current]:
                if edge.condition is None or edge.condition():
                    stack.append(edge.to_node)
                    
        self._cycle_cache[cache_key] = False
        return False
        
    def get_update_order(self, changed_nodes: Set[str]) -> List[str]:
        """Get the order in which nodes should be updated."""
        affected = self._get_affected_nodes(changed_nodes)
        return self._topological_sort(affected)
        
    def _get_affected_nodes(self, changed_nodes: Set[str]) -> Set[str]:
        """Get all nodes affected by the given changes."""
        affected = set(changed_nodes)
        queue = deque(changed_nodes)
        
        while queue:
            current = queue.popleft()
            for edge in self._edges[current]:
                if edge.condition is None or edge.condition():
                    if edge.to_node not in affected:
                        affected.add(edge.to_node)
                        queue.append(edge.to_node)
                        
        return affected
        
    def _topological_sort(self, nodes: Set[str]) -> List[str]:
        """Perform topological sort on the given nodes."""
        if self._cache_valid and self._topological_cache:
            # Filter cached result for requested nodes
            return [node for node in self._topological_cache if node in nodes]
            
        # Calculate in-degrees for affected nodes only
        in_degree = {node: 0 for node in nodes}
        for node in nodes:
            for edge in self._reverse_edges[node]:
                if edge.from_node in nodes and (edge.condition is None or edge.condition()):
                    in_degree[node] += 1
                    
        # Process nodes with no dependencies first
        queue = deque([node for node in nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for edge in self._edges[current]:
                if edge.to_node in nodes and (edge.condition is None or edge.condition()):
                    in_degree[edge.to_node] -= 1
                    if in_degree[edge.to_node] == 0:
                        queue.append(edge.to_node)
                        
        return result
        
    def start_batch_update(self) -> None:
        """Start batching updates for efficiency."""
        with self._lock:
            self._batch_updates = True
            self._batch_queue.clear()
            
    def end_batch_update(self) -> None:
        """End batching and process all queued updates."""
        with self._lock:
            if self._batch_updates:
                self._batch_updates = False
                if self._batch_queue:
                    self._process_batch_updates()
                    
    def queue_update(self, node_id: str) -> None:
        """Queue a node for update."""
        with self._lock:
            if self._batch_updates:
                self._batch_queue.add(node_id)
            else:
                self._process_immediate_update(node_id)
                
    def _process_batch_updates(self) -> None:
        """Process all batched updates in dependency order."""
        start_time = time.time()
        
        changed_nodes = set(self._batch_queue)
        update_order = self.get_update_order(changed_nodes)
        
        for node_id in update_order:
            if node_id in self._nodes:
                reactive_value = self._nodes[node_id]
                if hasattr(reactive_value, '_process_pending_updates'):
                    reactive_value._process_pending_updates()
                    
        self._batch_queue.clear()
        
        # Update statistics
        update_time = time.time() - start_time
        self._stats.batch_count += 1
        self._stats.update_count += len(update_order)
        self._stats.total_update_time += update_time
        self._stats.max_update_time = max(self._stats.max_update_time, update_time)
        
        if self._stats.update_count > 0:
            self._stats.average_update_time = self._stats.total_update_time / self._stats.update_count
            
    def _process_immediate_update(self, node_id: str) -> None:
        """Process an immediate update for a single node."""
        start_time = time.time()
        
        if node_id in self._nodes:
            reactive_value = self._nodes[node_id]
            if hasattr(reactive_value, '_process_pending_updates'):
                reactive_value._process_pending_updates()
                
        # Update statistics
        update_time = time.time() - start_time
        self._stats.update_count += 1
        self._stats.total_update_time += update_time
        self._stats.max_update_time = max(self._stats.max_update_time, update_time)
        
        if self._stats.update_count > 0:
            self._stats.average_update_time = self._stats.total_update_time / self._stats.update_count
            
    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all direct dependencies of a node."""
        dependencies = []
        for edge in self._reverse_edges[node_id]:
            if edge.condition is None or edge.condition():
                dependencies.append(edge.from_node)
        return dependencies
        
    def get_dependents(self, node_id: str) -> List[str]:
        """Get all direct dependents of a node."""
        dependents = []
        for edge in self._edges[node_id]:
            if edge.condition is None or edge.condition():
                dependents.append(edge.to_node)
        return dependents
        
    def get_all_dependencies(self, node_id: str) -> Set[str]:
        """Get all transitive dependencies of a node."""
        dependencies = set()
        queue = deque([node_id])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for edge in self._reverse_edges[current]:
                if edge.condition is None or edge.condition():
                    dependencies.add(edge.from_node)
                    queue.append(edge.from_node)
                    
        dependencies.discard(node_id)  # Remove self
        return dependencies
        
    def get_all_dependents(self, node_id: str) -> Set[str]:
        """Get all transitive dependents of a node."""
        dependents = set()
        queue = deque([node_id])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for edge in self._edges[current]:
                if edge.condition is None or edge.condition():
                    dependents.add(edge.to_node)
                    queue.append(edge.to_node)
                    
        dependents.discard(node_id)  # Remove self
        return dependents
        
    def detect_cycles(self) -> List[List[str]]:
        """Detect all cycles in the dependency graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True
                
            if node in visited:
                return False
                
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for edge in self._edges[node]:
                if edge.condition is None or edge.condition():
                    if dfs(edge.to_node):
                        return True
                        
            rec_stack.remove(node)
            path.pop()
            return False
            
        for node in self._nodes:
            if node not in visited:
                dfs(node)
                
        return cycles
        
    def optimize_graph(self) -> None:
        """Optimize the dependency graph for performance."""
        with self._lock:
            # Remove redundant edges (transitive reduction)
            self._remove_redundant_edges()
            
            # Update topological cache
            self._update_topological_cache()
            
            # Clear cycle cache to force recomputation
            self._cycle_cache.clear()
            
    def _remove_redundant_edges(self) -> None:
        """Remove redundant transitive edges."""
        edges_to_remove = []
        
        for from_node in self._edges:
            direct_targets = {edge.to_node for edge in self._edges[from_node]}
            
            for edge in self._edges[from_node]:
                # Check if there's an indirect path to the same target
                indirect_targets = set()
                for intermediate_edge in self._edges[from_node]:
                    if intermediate_edge.to_node != edge.to_node:
                        indirect_targets.update(self.get_all_dependents(intermediate_edge.to_node))
                        
                if edge.to_node in indirect_targets:
                    edges_to_remove.append((from_node, edge.to_node))
                    
        for from_node, to_node in edges_to_remove:
            self.remove_edge(from_node, to_node)
            
    def _update_topological_cache(self) -> None:
        """Update the cached topological sort."""
        all_nodes = set(self._nodes.keys())
        self._topological_cache = self._topological_sort(all_nodes)
        self._cache_valid = True
        
    def _invalidate_cache(self) -> None:
        """Invalidate cached data."""
        self._cache_valid = False
        self._topological_cache = None
        self._cycle_cache.clear()
        
    def get_stats(self) -> DependencyStats:
        """Get dependency graph statistics."""
        return self._stats
        
    def reset_stats(self) -> None:
        """Reset dependency graph statistics."""
        self._stats = DependencyStats()
        self._stats.total_nodes = len(self._nodes)
        self._stats.total_edges = sum(len(edges) for edges in self._edges.values())
        
    def visualize_graph(self) -> Dict[str, Any]:
        """Generate visualization data for the dependency graph."""
        nodes = []
        edges = []
        
        for node_id, reactive_value in self._nodes.items():
            nodes.append({
                'id': node_id,
                'type': reactive_value.value_type.value,
                'value': str(reactive_value.value)[:50],  # Truncate long values
                'dependencies': len(self._reverse_edges[node_id]),
                'dependents': len(self._edges[node_id])
            })
            
        for from_node, edge_set in self._edges.items():
            for edge in edge_set:
                edges.append({
                    'from': edge.from_node,
                    'to': edge.to_node,
                    'type': edge.dependency_type.value,
                    'weight': edge.weight,
                    'conditional': edge.condition is not None
                })
                
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'cycles': len(self.detect_cycles())
            }
        }
        
    def __repr__(self) -> str:
        return f"DependencyGraph(nodes={len(self._nodes)}, edges={self._stats.total_edges})"


class DependencyTracker:
    """Automatic dependency tracking for reactive values."""
    
    def __init__(self, dependency_graph: DependencyGraph):
        self.dependency_graph = dependency_graph
        self._tracking_stack: List[str] = []
        self._lock = threading.RLock()
        
    def track_access(self, node_id: str) -> None:
        """Track access to a reactive value for dependency detection."""
        with self._lock:
            if self._tracking_stack and self._tracking_stack[-1] != node_id:
                # Current node depends on accessed node
                dependent_id = self._tracking_stack[-1]
                self.dependency_graph.add_edge(node_id, dependent_id, DependencyType.DIRECT)
                
    def start_tracking(self, node_id: str) -> None:
        """Start tracking dependencies for a node."""
        with self._lock:
            self._tracking_stack.append(node_id)
            
    def stop_tracking(self) -> None:
        """Stop tracking dependencies."""
        with self._lock:
            if self._tracking_stack:
                self._tracking_stack.pop()
                
    def get_current_tracking(self) -> Optional[str]:
        """Get the currently tracked node."""
        with self._lock:
            return self._tracking_stack[-1] if self._tracking_stack else None


# Global dependency graph instance
_global_dependency_graph: Optional[DependencyGraph] = None
_global_dependency_tracker: Optional[DependencyTracker] = None


def get_dependency_graph() -> DependencyGraph:
    """Get the global dependency graph instance."""
    global _global_dependency_graph
    if _global_dependency_graph is None:
        _global_dependency_graph = DependencyGraph()
    return _global_dependency_graph


def get_dependency_tracker() -> DependencyTracker:
    """Get the global dependency tracker instance."""
    global _global_dependency_tracker
    if _global_dependency_tracker is None:
        _global_dependency_tracker = DependencyTracker(get_dependency_graph())
    return _global_dependency_tracker


def reset_dependency_system() -> None:
    """Reset the global dependency system."""
    global _global_dependency_graph, _global_dependency_tracker
    _global_dependency_graph = None
    _global_dependency_tracker = None 