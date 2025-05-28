"""
Graph management utilities for the dependency system.

This module provides functionality for analyzing the dependency graph,
including topological sorting, cycle detection, and strongly connected
component identification.
"""

from typing import Dict, Set, List, Any, Tuple, Optional, Iterator
from collections import defaultdict, deque


def topological_sort(graph: Dict[Any, Set[Any]]) -> Tuple[List[Any], Set[Tuple[Any, Any]]]:
    """Perform a topological sort on a directed graph using Kahn's algorithm.
    
    This implementation also detects cycles in the graph.
    
    Args:
        graph: A dictionary mapping nodes to sets of their dependencies.
            For dependency management, this should be the reverse of the 
            dependency graph (i.e., nodes mapped to their dependents).
            
    Returns:
        A tuple containing:
        - A list of nodes in topological order (if no cycles)
        - A set of edges that form cycles (empty if no cycles)
    """
    # Create a copy of the graph to avoid modifying the original
    working_graph = {node: set(edges) for node, edges in graph.items()}
    
    # Create a dictionary mapping nodes to their in-degree (number of dependencies)
    in_degree = defaultdict(int)
    
    # Initialize in-degrees and ensure all nodes are in the working graph
    for node, edges in working_graph.items():
        for edge in edges:
            in_degree[edge] += 1
        
        # Ensure node is in in_degree even if it has no incoming edges
        if node not in in_degree:
            in_degree[node] = 0
    
    # Queue of nodes with no dependencies (in-degree of 0)
    queue = deque([node for node, degree in in_degree.items() if degree == 0])
    
    # List to store topologically sorted nodes
    sorted_nodes = []
    
    # Process nodes with no dependencies
    while queue:
        node = queue.popleft()
        sorted_nodes.append(node)
        
        # Reduce in-degree of nodes that depend on this node
        if node in working_graph:
            for dependent in working_graph[node]:
                in_degree[dependent] -= 1
                
                # If dependent now has no dependencies, add it to the queue
                if in_degree[dependent] == 0:
                    queue.append(dependent)
    
    # Check for cycles: if we've processed all nodes, there are no cycles
    # Otherwise, the remaining edges form cycles
    cycle_edges = set()
    
    if len(sorted_nodes) < len(in_degree):
        # There are cycles in the graph
        # Identify edges that form cycles (nodes with non-zero in-degree)
        for node, edges in working_graph.items():
            for edge in edges:
                if in_degree[edge] > 0:
                    cycle_edges.add((node, edge))
    
    return sorted_nodes, cycle_edges


def identify_strongly_connected_components(graph: Dict[Any, Set[Any]]) -> List[Set[Any]]:
    """Identify strongly connected components (SCCs) in a directed graph.
    
    Uses Kosaraju's algorithm to find strongly connected components.
    
    Args:
        graph: A dictionary mapping nodes to sets of their dependencies.
        
    Returns:
        A list of sets, where each set contains the nodes in a strongly
        connected component.
    """
    # Step 1: Perform DFS and store nodes in order of completion
    def dfs(node, visited, stack):
        """Depth-first search to order nodes."""
        visited.add(node)
        
        # Visit all neighbors
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor, visited, stack)
        
        # Push node to stack after all neighbors are processed
        stack.append(node)
    
    # Step 2: Create the transpose of the graph (reverse all edges)
    def transpose() -> Dict[Any, Set[Any]]:
        """Create the transpose of the graph."""
        transposed = defaultdict(set)
        
        for node, edges in graph.items():
            # Ensure node is in the transposed graph even if it has no outgoing edges
            if not edges:
                transposed[node]
            
            # Reverse all edges
            for edge in edges:
                transposed[edge].add(node)
        
        return transposed
    
    # Step 3: Perform DFS on transposed graph in order of completion
    def dfs_transposed(node, visited, component):
        """DFS on transposed graph to identify components."""
        visited.add(node)
        component.add(node)
        
        for neighbor in transposed.get(node, set()):
            if neighbor not in visited:
                dfs_transposed(neighbor, visited, component)
    
    # Get all nodes in the graph
    nodes = set()
    for node, edges in graph.items():
        nodes.add(node)
        nodes.update(edges)
    
    # Step 1: Perform DFS and store nodes in order of completion
    visited = set()
    stack = []
    
    for node in nodes:
        if node not in visited:
            dfs(node, visited, stack)
    
    # Step 2: Create the transpose of the graph
    transposed = transpose()
    
    # Step 3: Perform DFS on transposed graph in order of completion
    visited.clear()
    components = []
    
    while stack:
        node = stack.pop()
        if node not in visited:
            component = set()
            dfs_transposed(node, visited, component)
            components.append(component)
    
    return components


def break_cycles(graph: Dict[Any, Set[Any]], 
                components: Optional[List[Set[Any]]] = None) -> Dict[Any, Set[Any]]:
    """Break cycles in a directed graph by removing minimum feedback arc set.
    
    This is a simple implementation that removes one edge from each cycle.
    For more sophisticated algorithms, a minimum feedback arc set algorithm
    could be used.
    
    Args:
        graph: A dictionary mapping nodes to sets of their dependencies.
        components: Optional list of strongly connected components. If not
            provided, they will be computed.
            
    Returns:
        A modified copy of the graph with cycles broken.
    """
    # Create a copy of the graph to avoid modifying the original
    acyclic_graph = {node: set(edges) for node, edges in graph.items()}
    
    # If components not provided, compute them
    if components is None:
        components = identify_strongly_connected_components(graph)
    
    # For each component with more than one node (i.e., a potential cycle)
    for component in components:
        if len(component) > 1:
            # Find a minimum set of edges to remove to break cycles
            # Simple approach: run topological sort on the subgraph and
            # identify cycle edges
            subgraph = {
                node: edges.intersection(component)
                for node, edges in graph.items()
                if node in component
            }
            
            _, cycle_edges = topological_sort(subgraph)
            
            # Remove cycle edges from the acyclic graph
            for source, target in cycle_edges:
                if target in acyclic_graph.get(source, set()):
                    acyclic_graph[source].remove(target)
                
                # If we've removed all edges for a node, ensure it still exists in the graph
                if source in acyclic_graph and not acyclic_graph[source]:
                    acyclic_graph[source] = set()
    
    return acyclic_graph
