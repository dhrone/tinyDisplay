#!/usr/bin/env python3
"""
Test Z-order Management System

Tests for the comprehensive layering and z-order management functionality.
"""

import pytest
import time
from unittest.mock import Mock

from src.tinydisplay.canvas.layering import (
    LayerManager, LayerInfo, LayerChange, LayerType,
    create_standard_layers, optimize_layer_z_orders
)


class TestLayerManager:
    """Test LayerManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.layer_manager = LayerManager()
    
    def test_create_layer(self):
        """Test layer creation."""
        # Test successful layer creation
        assert self.layer_manager.create_layer("test_layer", 10, LayerType.CONTENT)
        
        # Test duplicate layer creation fails
        assert not self.layer_manager.create_layer("test_layer", 20, LayerType.OVERLAY)
        
        # Verify layer info
        layer_info = self.layer_manager.get_layer_info("test_layer")
        assert layer_info is not None
        assert layer_info.layer_id == "test_layer"
        assert layer_info.z_order == 10
        assert layer_info.layer_type == LayerType.CONTENT
        assert layer_info.visible is True
        assert layer_info.alpha == 1.0
    
    def test_remove_layer(self):
        """Test layer removal."""
        # Create and add widgets to layer
        self.layer_manager.create_layer("test_layer", 10)
        self.layer_manager.add_widget_to_layer("widget1", "test_layer")
        self.layer_manager.add_widget_to_layer("widget2", "test_layer")
        
        # Remove layer
        assert self.layer_manager.remove_layer("test_layer")
        
        # Verify layer and widgets are gone
        assert self.layer_manager.get_layer_info("test_layer") is None
        assert self.layer_manager.get_widget_layer("widget1") is None
        assert self.layer_manager.get_widget_layer("widget2") is None
        
        # Test removing non-existent layer
        assert not self.layer_manager.remove_layer("non_existent")
    
    def test_widget_layer_management(self):
        """Test adding and removing widgets from layers."""
        # Create layers
        self.layer_manager.create_layer("layer1", 10)
        self.layer_manager.create_layer("layer2", 20)
        
        # Add widget to layer
        assert self.layer_manager.add_widget_to_layer("widget1", "layer1")
        assert self.layer_manager.get_widget_layer("widget1") == "layer1"
        assert self.layer_manager.get_widget_z_order("widget1") == 10
        
        # Move widget to different layer
        assert self.layer_manager.add_widget_to_layer("widget1", "layer2")
        assert self.layer_manager.get_widget_layer("widget1") == "layer2"
        assert self.layer_manager.get_widget_z_order("widget1") == 20
        
        # Remove widget
        assert self.layer_manager.remove_widget("widget1")
        assert self.layer_manager.get_widget_layer("widget1") is None
        
        # Test adding to non-existent layer
        assert not self.layer_manager.add_widget_to_layer("widget2", "non_existent")
    
    def test_z_order_manipulation(self):
        """Test z-order changes."""
        # Create layers
        self.layer_manager.create_layer("layer1", 10)
        self.layer_manager.create_layer("layer2", 20)
        self.layer_manager.create_layer("layer3", 30)
        
        # Test z-order change
        assert self.layer_manager.set_layer_z_order("layer1", 25)
        assert self.layer_manager.get_layer_info("layer1").z_order == 25
        
        # Test bring to front
        assert self.layer_manager.bring_layer_to_front("layer1")
        assert self.layer_manager.get_layer_info("layer1").z_order == 31  # 30 + 1
        
        # Test send to back
        assert self.layer_manager.send_layer_to_back("layer1")
        assert self.layer_manager.get_layer_info("layer1").z_order == 9  # 10 - 1
        
        # Test with non-existent layer
        assert not self.layer_manager.set_layer_z_order("non_existent", 100)
    
    def test_visibility_and_transparency(self):
        """Test visibility and transparency controls."""
        self.layer_manager.create_layer("test_layer", 10)
        
        # Test visibility
        assert self.layer_manager.set_layer_visibility("test_layer", False)
        assert not self.layer_manager.get_layer_info("test_layer").visible
        
        assert self.layer_manager.set_layer_visibility("test_layer", True)
        assert self.layer_manager.get_layer_info("test_layer").visible
        
        # Test transparency
        assert self.layer_manager.set_layer_alpha("test_layer", 0.5)
        assert abs(self.layer_manager.get_layer_info("test_layer").alpha - 0.5) < 0.001
        
        # Test alpha clamping
        assert self.layer_manager.set_layer_alpha("test_layer", 1.5)
        assert self.layer_manager.get_layer_info("test_layer").alpha == 1.0
        
        assert self.layer_manager.set_layer_alpha("test_layer", -0.5)
        assert self.layer_manager.get_layer_info("test_layer").alpha == 0.0
        
        # Test with non-existent layer
        assert not self.layer_manager.set_layer_visibility("non_existent", False)
        assert not self.layer_manager.set_layer_alpha("non_existent", 0.5)
    
    def test_render_order(self):
        """Test render order generation."""
        # Create layers with widgets
        self.layer_manager.create_layer("back", 10)
        self.layer_manager.create_layer("middle", 20)
        self.layer_manager.create_layer("front", 30)
        
        self.layer_manager.add_widget_to_layer("widget1", "back")
        self.layer_manager.add_widget_to_layer("widget2", "middle")
        self.layer_manager.add_widget_to_layer("widget3", "front")
        self.layer_manager.add_widget_to_layer("widget4", "back")
        
        # Get render order
        render_order = self.layer_manager.get_render_order()
        
        # Should be sorted by z-order (back to front)
        expected_order = ["widget1", "widget4", "widget2", "widget3"]
        assert render_order == expected_order
        
        # Test with invisible layer
        self.layer_manager.set_layer_visibility("middle", False)
        render_order = self.layer_manager.get_render_order()
        expected_order = ["widget1", "widget4", "widget3"]
        assert render_order == expected_order
        
        # Test with transparent layer
        self.layer_manager.set_layer_visibility("middle", True)
        self.layer_manager.set_layer_alpha("middle", 0.0)
        render_order = self.layer_manager.get_render_order()
        expected_order = ["widget1", "widget4", "widget3"]
        assert render_order == expected_order
    
    def test_render_order_caching(self):
        """Test render order caching for performance."""
        # Create layers with widgets
        self.layer_manager.create_layer("layer1", 10)
        self.layer_manager.add_widget_to_layer("widget1", "layer1")
        
        # First call should miss cache
        render_order1 = self.layer_manager.get_render_order()
        stats = self.layer_manager.get_performance_stats()
        assert stats['cache_misses'] == 1
        assert stats['cache_hits'] == 0
        
        # Second call should hit cache
        render_order2 = self.layer_manager.get_render_order()
        stats = self.layer_manager.get_performance_stats()
        assert stats['cache_misses'] == 1
        assert stats['cache_hits'] == 1
        assert render_order1 == render_order2
        
        # Modifying layers should invalidate cache
        self.layer_manager.add_widget_to_layer("widget2", "layer1")
        render_order3 = self.layer_manager.get_render_order()
        stats = self.layer_manager.get_performance_stats()
        assert stats['cache_misses'] == 2
    
    def test_layer_queries(self):
        """Test layer query methods."""
        # Create layers of different types
        self.layer_manager.create_layer("bg", 0, LayerType.BACKGROUND)
        self.layer_manager.create_layer("content1", 100, LayerType.CONTENT)
        self.layer_manager.create_layer("content2", 110, LayerType.CONTENT)
        self.layer_manager.create_layer("overlay", 200, LayerType.OVERLAY)
        
        # Test get all layers
        all_layers = self.layer_manager.get_all_layers()
        assert len(all_layers) == 4
        assert all_layers[0].layer_id == "bg"  # Should be sorted by z-order
        assert all_layers[-1].layer_id == "overlay"
        
        # Test get layers by type
        content_layers = self.layer_manager.get_layers_by_type(LayerType.CONTENT)
        assert len(content_layers) == 2
        assert all(layer.layer_type == LayerType.CONTENT for layer in content_layers)
        
        background_layers = self.layer_manager.get_layers_by_type(LayerType.BACKGROUND)
        assert len(background_layers) == 1
        assert background_layers[0].layer_id == "bg"
    
    def test_change_tracking(self):
        """Test change tracking and history."""
        # Create layer and add widget
        self.layer_manager.create_layer("test_layer", 10)
        self.layer_manager.add_widget_to_layer("widget1", "test_layer")
        
        # Check change history
        changes = self.layer_manager.get_recent_changes()
        assert len(changes) == 1
        assert changes[0].widget_id == "widget1"
        assert changes[0].new_z_order == 10
        
        # Move widget to different z-order
        self.layer_manager.set_layer_z_order("test_layer", 20)
        changes = self.layer_manager.get_recent_changes()
        assert len(changes) == 2  # Original add + z-order change
        
        # Test timestamp filtering
        time.sleep(0.01)  # Small delay
        timestamp = time.time()
        self.layer_manager.add_widget_to_layer("widget2", "test_layer")
        
        recent_changes = self.layer_manager.get_recent_changes(since=timestamp)
        assert len(recent_changes) == 1
        assert recent_changes[0].widget_id == "widget2"
        
        # Test limit
        limited_changes = self.layer_manager.get_recent_changes(limit=1)
        assert len(limited_changes) == 1
    
    def test_change_callbacks(self):
        """Test change notification callbacks."""
        callback_calls = []
        
        def test_callback(change: LayerChange):
            callback_calls.append(change)
        
        # Add callback
        self.layer_manager.add_change_callback(test_callback)
        
        # Create layer and add widget
        self.layer_manager.create_layer("test_layer", 10)
        self.layer_manager.add_widget_to_layer("widget1", "test_layer")
        
        # Should have received callback
        assert len(callback_calls) == 1
        assert callback_calls[0].widget_id == "widget1"
        
        # Remove callback
        self.layer_manager.remove_change_callback(test_callback)
        self.layer_manager.add_widget_to_layer("widget2", "test_layer")
        
        # Should not have received new callback
        assert len(callback_calls) == 1
    
    def test_performance_stats(self):
        """Test performance statistics."""
        # Initial stats
        stats = self.layer_manager.get_performance_stats()
        assert stats['total_layers'] == 0
        assert stats['total_widgets'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        
        # Create layers and widgets
        self.layer_manager.create_layer("layer1", 10)
        self.layer_manager.add_widget_to_layer("widget1", "layer1")
        
        # Check updated stats
        stats = self.layer_manager.get_performance_stats()
        assert stats['total_layers'] == 1
        assert stats['total_widgets'] == 1
        
        # Generate some cache activity
        self.layer_manager.get_render_order()  # Cache miss
        self.layer_manager.get_render_order()  # Cache hit
        
        stats = self.layer_manager.get_performance_stats()
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['cache_hit_rate_percent'] == 50.0
        
        # Clear stats
        self.layer_manager.clear_performance_stats()
        stats = self.layer_manager.get_performance_stats()
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
    
    def test_thread_safety(self):
        """Test thread safety of layer operations."""
        import threading
        import time
        
        # Create initial layer
        self.layer_manager.create_layer("test_layer", 10)
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    widget_id = f"widget_{worker_id}_{i}"
                    self.layer_manager.add_widget_to_layer(widget_id, "test_layer")
                    time.sleep(0.001)  # Small delay to encourage race conditions
                    self.layer_manager.remove_widget(widget_id)
                results.append(f"Worker {worker_id} completed")
            except Exception as e:
                errors.append(f"Worker {worker_id} error: {e}")
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 3


class TestStandardLayers:
    """Test standard layer creation utilities."""
    
    def test_create_standard_layers(self):
        """Test standard layer creation."""
        layer_manager = LayerManager()
        layer_map = create_standard_layers(layer_manager)
        
        # Check all standard layers were created
        expected_layers = ['background', 'content', 'overlay', 'modal', 'system']
        assert all(layer_name in layer_map for layer_name in expected_layers)
        
        # Check z-order progression
        bg_info = layer_manager.get_layer_info(layer_map['background'])
        content_info = layer_manager.get_layer_info(layer_map['content'])
        overlay_info = layer_manager.get_layer_info(layer_map['overlay'])
        modal_info = layer_manager.get_layer_info(layer_map['modal'])
        system_info = layer_manager.get_layer_info(layer_map['system'])
        
        assert bg_info.z_order < content_info.z_order
        assert content_info.z_order < overlay_info.z_order
        assert overlay_info.z_order < modal_info.z_order
        assert modal_info.z_order < system_info.z_order
        
        # Check layer types
        assert bg_info.layer_type == LayerType.BACKGROUND
        assert content_info.layer_type == LayerType.CONTENT
        assert overlay_info.layer_type == LayerType.OVERLAY
        assert modal_info.layer_type == LayerType.MODAL
        assert system_info.layer_type == LayerType.SYSTEM


class TestLayerOptimization:
    """Test layer optimization utilities."""
    
    def test_optimize_layer_z_orders(self):
        """Test z-order optimization."""
        layer_manager = LayerManager()
        
        # Create layers with gaps in z-order
        layer_manager.create_layer("layer1", 10)
        layer_manager.create_layer("layer2", 50)
        layer_manager.create_layer("layer3", 100)
        layer_manager.create_layer("layer4", 150)
        
        # Optimize
        changes = optimize_layer_z_orders(layer_manager)
        assert changes == 4  # All layers should be reordered
        
        # Check new z-orders are sequential
        layers = layer_manager.get_all_layers()
        for i, layer in enumerate(layers):
            assert layer.z_order == i
        
        # Test with already optimized layers
        changes = optimize_layer_z_orders(layer_manager)
        assert changes == 0  # No changes needed
        
        # Test with single layer
        single_manager = LayerManager()
        single_manager.create_layer("single", 100)
        changes = optimize_layer_z_orders(single_manager)
        assert changes == 1  # Should be set to 0
        
        # Test with empty manager
        empty_manager = LayerManager()
        changes = optimize_layer_z_orders(empty_manager)
        assert changes == 0


if __name__ == "__main__":
    # Run basic functionality test
    print("Testing Z-order Management System...")
    
    # Test LayerManager
    layer_manager = LayerManager()
    
    # Create standard layers
    layers = create_standard_layers(layer_manager)
    print(f"Created standard layers: {list(layers.keys())}")
    
    # Add some widgets
    layer_manager.add_widget_to_layer("widget1", layers['background'])
    layer_manager.add_widget_to_layer("widget2", layers['content'])
    layer_manager.add_widget_to_layer("widget3", layers['overlay'])
    
    # Get render order
    render_order = layer_manager.get_render_order()
    print(f"Render order: {render_order}")
    
    # Test layer manipulation
    layer_manager.bring_layer_to_front(layers['background'])
    new_render_order = layer_manager.get_render_order()
    print(f"After bringing background to front: {new_render_order}")
    
    # Performance stats
    stats = layer_manager.get_performance_stats()
    print(f"Performance stats: {stats}")
    
    print("Z-order Management System test completed successfully!") 