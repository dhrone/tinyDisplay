#!/usr/bin/env python3
"""
Z-order Management System

Provides comprehensive layering and z-order management for widgets in tinyDisplay.
Handles layer manipulation, rendering order, visibility, and transparency.
"""

from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from collections import defaultdict

from ..widgets.base import Widget, WidgetBounds


class LayerType(Enum):
    """Types of layers for different widget categories."""
    BACKGROUND = 0      # Background elements
    CONTENT = 100       # Main content widgets
    OVERLAY = 200       # Overlay elements (tooltips, etc.)
    MODAL = 300         # Modal dialogs
    SYSTEM = 400        # System notifications


@dataclass
class LayerInfo:
    """Information about a layer."""
    layer_id: str
    z_order: int
    layer_type: LayerType
    visible: bool = True
    alpha: float = 1.0
    widgets: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)


@dataclass
class LayerChange:
    """Represents a change in layer ordering."""
    widget_id: str
    old_z_order: Optional[int]
    new_z_order: int
    timestamp: float = field(default_factory=time.time)


class LayerManager:
    """Advanced layer management system for widget z-ordering.
    
    Provides:
    - Hierarchical layer management
    - Efficient z-order sorting
    - Layer manipulation methods
    - Change detection and optimization
    - Visibility and transparency support
    """
    
    def __init__(self):
        # Core layer data
        self._layers: Dict[str, LayerInfo] = {}
        self._widget_to_layer: Dict[str, str] = {}
        self._z_order_to_layers: Dict[int, Set[str]] = defaultdict(set)
        
        # Rendering optimization
        self._render_order_cache: Optional[List[str]] = None
        self._cache_dirty = True
        self._last_change_time = time.time()
        
        # Change tracking
        self._change_history: List[LayerChange] = []
        self._max_history_size = 1000
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Event callbacks
        self._change_callbacks: Set[Callable[[LayerChange], None]] = set()
        
        # Performance metrics
        self._sort_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
    
    def create_layer(self, layer_id: str, z_order: int, 
                    layer_type: LayerType = LayerType.CONTENT,
                    visible: bool = True, alpha: float = 1.0) -> bool:
        """Create a new layer.
        
        Args:
            layer_id: Unique identifier for the layer
            z_order: Z-order position (higher = front)
            layer_type: Type of layer for categorization
            visible: Initial visibility state
            alpha: Initial transparency (0.0 = transparent, 1.0 = opaque)
            
        Returns:
            True if layer was created, False if layer_id already exists
        """
        with self._lock:
            if layer_id in self._layers:
                return False
            
            layer_info = LayerInfo(
                layer_id=layer_id,
                z_order=z_order,
                layer_type=layer_type,
                visible=visible,
                alpha=alpha
            )
            
            self._layers[layer_id] = layer_info
            self._z_order_to_layers[z_order].add(layer_id)
            self._invalidate_cache()
            
            return True
    
    def remove_layer(self, layer_id: str) -> bool:
        """Remove a layer and all its widgets.
        
        Args:
            layer_id: Layer to remove
            
        Returns:
            True if layer was removed, False if not found
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            layer_info = self._layers[layer_id]
            
            # Remove all widgets from this layer
            for widget_id in layer_info.widgets.copy():
                self.remove_widget(widget_id)
            
            # Remove layer from z-order mapping
            self._z_order_to_layers[layer_info.z_order].discard(layer_id)
            if not self._z_order_to_layers[layer_info.z_order]:
                del self._z_order_to_layers[layer_info.z_order]
            
            # Remove layer
            del self._layers[layer_id]
            self._invalidate_cache()
            
            return True
    
    def add_widget_to_layer(self, widget_id: str, layer_id: str) -> bool:
        """Add a widget to a specific layer.
        
        Args:
            widget_id: Widget to add
            layer_id: Target layer
            
        Returns:
            True if widget was added, False if layer doesn't exist
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            # Remove from old layer if exists
            self.remove_widget(widget_id)
            
            # Add to new layer
            self._layers[layer_id].widgets.add(widget_id)
            self._layers[layer_id].last_modified = time.time()
            self._widget_to_layer[widget_id] = layer_id
            
            # Record change
            old_z_order = None
            if widget_id in self._widget_to_layer:
                old_layer = self._widget_to_layer[widget_id]
                if old_layer in self._layers:
                    old_z_order = self._layers[old_layer].z_order
            
            change = LayerChange(
                widget_id=widget_id,
                old_z_order=old_z_order,
                new_z_order=self._layers[layer_id].z_order
            )
            self._record_change(change)
            self._invalidate_cache()
            
            return True
    
    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget from all layers.
        
        Args:
            widget_id: Widget to remove
            
        Returns:
            True if widget was removed, False if not found
        """
        with self._lock:
            if widget_id not in self._widget_to_layer:
                return False
            
            layer_id = self._widget_to_layer[widget_id]
            if layer_id in self._layers:
                self._layers[layer_id].widgets.discard(widget_id)
                self._layers[layer_id].last_modified = time.time()
                
                # Record change
                change = LayerChange(
                    widget_id=widget_id,
                    old_z_order=self._layers[layer_id].z_order,
                    new_z_order=None
                )
                self._record_change(change)
            
            del self._widget_to_layer[widget_id]
            self._invalidate_cache()
            
            return True
    
    def set_layer_z_order(self, layer_id: str, new_z_order: int) -> bool:
        """Change a layer's z-order.
        
        Args:
            layer_id: Layer to modify
            new_z_order: New z-order value
            
        Returns:
            True if z-order was changed, False if layer doesn't exist
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            layer_info = self._layers[layer_id]
            old_z_order = layer_info.z_order
            
            if old_z_order == new_z_order:
                return True  # No change needed
            
            # Remove from old z-order
            self._z_order_to_layers[old_z_order].discard(layer_id)
            if not self._z_order_to_layers[old_z_order]:
                del self._z_order_to_layers[old_z_order]
            
            # Add to new z-order
            layer_info.z_order = new_z_order
            layer_info.last_modified = time.time()
            self._z_order_to_layers[new_z_order].add(layer_id)
            
            # Record changes for all widgets in this layer
            for widget_id in layer_info.widgets:
                change = LayerChange(
                    widget_id=widget_id,
                    old_z_order=old_z_order,
                    new_z_order=new_z_order
                )
                self._record_change(change)
            
            self._invalidate_cache()
            return True
    
    def bring_layer_to_front(self, layer_id: str) -> bool:
        """Bring a layer to the front (highest z-order).
        
        Args:
            layer_id: Layer to bring to front
            
        Returns:
            True if layer was moved, False if layer doesn't exist
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            # Find the highest z-order
            max_z_order = max(self._z_order_to_layers.keys()) if self._z_order_to_layers else 0
            
            # Set to one higher than current max
            return self.set_layer_z_order(layer_id, max_z_order + 1)
    
    def send_layer_to_back(self, layer_id: str) -> bool:
        """Send a layer to the back (lowest z-order).
        
        Args:
            layer_id: Layer to send to back
            
        Returns:
            True if layer was moved, False if layer doesn't exist
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            # Find the lowest z-order
            min_z_order = min(self._z_order_to_layers.keys()) if self._z_order_to_layers else 0
            
            # Set to one lower than current min
            return self.set_layer_z_order(layer_id, min_z_order - 1)
    
    def set_layer_visibility(self, layer_id: str, visible: bool) -> bool:
        """Set layer visibility.
        
        Args:
            layer_id: Layer to modify
            visible: New visibility state
            
        Returns:
            True if visibility was changed, False if layer doesn't exist
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            layer_info = self._layers[layer_id]
            if layer_info.visible != visible:
                layer_info.visible = visible
                layer_info.last_modified = time.time()
                self._invalidate_cache()
            
            return True
    
    def set_layer_alpha(self, layer_id: str, alpha: float) -> bool:
        """Set layer transparency.
        
        Args:
            layer_id: Layer to modify
            alpha: Alpha value (0.0 = transparent, 1.0 = opaque)
            
        Returns:
            True if alpha was changed, False if layer doesn't exist
        """
        with self._lock:
            if layer_id not in self._layers:
                return False
            
            # Clamp alpha to valid range
            alpha = max(0.0, min(1.0, alpha))
            
            layer_info = self._layers[layer_id]
            if abs(layer_info.alpha - alpha) > 0.001:  # Avoid floating point precision issues
                layer_info.alpha = alpha
                layer_info.last_modified = time.time()
                # Note: Alpha changes don't invalidate render order cache
            
            return True
    
    def get_render_order(self) -> List[str]:
        """Get widgets in rendering order (back to front).
        
        Returns:
            List of widget IDs in rendering order
        """
        with self._lock:
            if self._render_order_cache is not None and not self._cache_dirty:
                self._cache_hits += 1
                return self._render_order_cache.copy()
            
            self._cache_misses += 1
            self._sort_count += 1
            
            # Build render order
            render_order = []
            
            # Sort layers by z-order
            sorted_z_orders = sorted(self._z_order_to_layers.keys())
            
            for z_order in sorted_z_orders:
                layer_ids = sorted(self._z_order_to_layers[z_order])  # Consistent ordering
                
                for layer_id in layer_ids:
                    layer_info = self._layers[layer_id]
                    
                    # Only include visible layers
                    if layer_info.visible and layer_info.alpha > 0.0:
                        # Sort widgets within layer for consistency
                        sorted_widgets = sorted(layer_info.widgets)
                        render_order.extend(sorted_widgets)
            
            # Cache the result
            self._render_order_cache = render_order.copy()
            self._cache_dirty = False
            
            return render_order
    
    def get_widget_layer(self, widget_id: str) -> Optional[str]:
        """Get the layer containing a widget.
        
        Args:
            widget_id: Widget to find
            
        Returns:
            Layer ID or None if widget not found
        """
        return self._widget_to_layer.get(widget_id)
    
    def get_widget_z_order(self, widget_id: str) -> Optional[int]:
        """Get a widget's effective z-order.
        
        Args:
            widget_id: Widget to query
            
        Returns:
            Z-order value or None if widget not found
        """
        layer_id = self.get_widget_layer(widget_id)
        if layer_id and layer_id in self._layers:
            return self._layers[layer_id].z_order
        return None
    
    def get_layer_info(self, layer_id: str) -> Optional[LayerInfo]:
        """Get information about a layer.
        
        Args:
            layer_id: Layer to query
            
        Returns:
            LayerInfo or None if layer not found
        """
        return self._layers.get(layer_id)
    
    def get_all_layers(self) -> List[LayerInfo]:
        """Get all layers sorted by z-order.
        
        Returns:
            List of LayerInfo objects sorted by z-order
        """
        with self._lock:
            return sorted(self._layers.values(), key=lambda l: l.z_order)
    
    def get_layers_by_type(self, layer_type: LayerType) -> List[LayerInfo]:
        """Get all layers of a specific type.
        
        Args:
            layer_type: Type of layers to retrieve
            
        Returns:
            List of LayerInfo objects of the specified type
        """
        with self._lock:
            return [layer for layer in self._layers.values() 
                   if layer.layer_type == layer_type]
    
    def has_changes_since(self, timestamp: float) -> bool:
        """Check if there have been changes since a timestamp.
        
        Args:
            timestamp: Timestamp to check against
            
        Returns:
            True if there have been changes since timestamp
        """
        return self._last_change_time > timestamp
    
    def get_recent_changes(self, since: Optional[float] = None, 
                          limit: Optional[int] = None) -> List[LayerChange]:
        """Get recent layer changes.
        
        Args:
            since: Only return changes after this timestamp
            limit: Maximum number of changes to return
            
        Returns:
            List of LayerChange objects
        """
        with self._lock:
            changes = self._change_history
            
            if since is not None:
                changes = [c for c in changes if c.timestamp > since]
            
            if limit is not None:
                changes = changes[-limit:]
            
            return changes.copy()
    
    def add_change_callback(self, callback: Callable[[LayerChange], None]) -> None:
        """Add a callback for layer changes.
        
        Args:
            callback: Function to call when layers change
        """
        self._change_callbacks.add(callback)
    
    def remove_change_callback(self, callback: Callable[[LayerChange], None]) -> None:
        """Remove a layer change callback.
        
        Args:
            callback: Callback to remove
        """
        self._change_callbacks.discard(callback)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        with self._lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_layers': len(self._layers),
                'total_widgets': len(self._widget_to_layer),
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'cache_hit_rate_percent': hit_rate,
                'sort_operations': self._sort_count,
                'change_history_size': len(self._change_history)
            }
    
    def clear_performance_stats(self) -> None:
        """Clear performance statistics."""
        with self._lock:
            self._cache_hits = 0
            self._cache_misses = 0
            self._sort_count = 0
    
    def _invalidate_cache(self) -> None:
        """Invalidate the render order cache."""
        self._render_order_cache = None
        self._cache_dirty = True
        self._last_change_time = time.time()
    
    def _record_change(self, change: LayerChange) -> None:
        """Record a layer change for history tracking."""
        self._change_history.append(change)
        
        # Trim history if too large
        if len(self._change_history) > self._max_history_size:
            self._change_history = self._change_history[-self._max_history_size//2:]
        
        # Notify callbacks
        for callback in self._change_callbacks:
            try:
                callback(change)
            except Exception:
                # Don't let callback errors break the layer manager
                pass
    
    def __repr__(self) -> str:
        return (f"LayerManager(layers={len(self._layers)}, "
                f"widgets={len(self._widget_to_layer)})")


# Convenience functions for common layer operations

def create_standard_layers(layer_manager: LayerManager) -> Dict[str, str]:
    """Create standard layers for typical applications.
    
    Args:
        layer_manager: LayerManager to create layers in
        
    Returns:
        Dictionary mapping layer names to layer IDs
    """
    layers = {
        'background': 'bg_layer',
        'content': 'content_layer', 
        'overlay': 'overlay_layer',
        'modal': 'modal_layer',
        'system': 'system_layer'
    }
    
    layer_configs = [
        ('bg_layer', LayerType.BACKGROUND.value, LayerType.BACKGROUND),
        ('content_layer', LayerType.CONTENT.value, LayerType.CONTENT),
        ('overlay_layer', LayerType.OVERLAY.value, LayerType.OVERLAY),
        ('modal_layer', LayerType.MODAL.value, LayerType.MODAL),
        ('system_layer', LayerType.SYSTEM.value, LayerType.SYSTEM),
    ]
    
    for layer_id, z_order, layer_type in layer_configs:
        layer_manager.create_layer(layer_id, z_order, layer_type)
    
    return layers


def optimize_layer_z_orders(layer_manager: LayerManager) -> int:
    """Optimize layer z-orders to minimize gaps.
    
    Args:
        layer_manager: LayerManager to optimize
        
    Returns:
        Number of layers that were reordered
    """
    layers = layer_manager.get_all_layers()
    if len(layers) <= 1:
        return 0
    
    changes = 0
    new_z_order = 0
    
    for layer in layers:
        if layer.z_order != new_z_order:
            layer_manager.set_layer_z_order(layer.layer_id, new_z_order)
            changes += 1
        new_z_order += 1
    
    return changes 