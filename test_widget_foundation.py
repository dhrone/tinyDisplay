#!/usr/bin/env python3
"""
Test script for widget foundation components.

Tests the basic functionality of the widget foundation implemented in Story 1.4.
"""

from src.tinydisplay.widgets import Widget, ContainerWidget, ReactiveValue, WidgetState
from src.tinydisplay.canvas import Canvas, CanvasConfig
from src.tinydisplay.rendering import RenderingEngine, RenderingConfig
from src.tinydisplay.core import get_reactive_manager


class TestWidget(Widget):
    """Simple test widget implementation."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_count = 0
    
    def render(self, canvas):
        """Simple render implementation."""
        self.render_count += 1
        print(f"Rendering {self.widget_id} (count: {self.render_count})")


def test_widget_lifecycle():
    """Test widget lifecycle management."""
    print("=== Testing Widget Lifecycle ===")
    
    widget = TestWidget("test_widget")
    print(f"Initial state: {widget.state}")
    
    # Test lifecycle transitions
    widget.initialize()
    print(f"After initialize: {widget.state}")
    
    widget.activate()
    print(f"After activate: {widget.state}")
    
    widget.hide()
    print(f"After hide: {widget.state}")
    
    widget.activate()
    print(f"After reactivate: {widget.state}")
    
    widget.destroy()
    print(f"After destroy: {widget.state}")


def test_reactive_values():
    """Test reactive value system."""
    print("\n=== Testing Reactive Values ===")
    
    # Create reactive value
    reactive_val = ReactiveValue(42)
    print(f"Initial value: {reactive_val.value}")
    
    # Track changes
    changes = []
    def on_change(old, new):
        changes.append((old, new))
        print(f"Value changed: {old} -> {new}")
    
    reactive_val.bind(on_change)
    
    # Test value changes
    reactive_val.value = 100
    reactive_val.value = 200
    
    print(f"Total changes: {len(changes)}")


def test_widget_properties():
    """Test widget property system."""
    print("\n=== Testing Widget Properties ===")
    
    widget = TestWidget("prop_test")
    
    # Test position
    print(f"Initial position: {widget.position}")
    widget.position = (10, 20)
    print(f"New position: {widget.position}")
    
    # Test size
    print(f"Initial size: {widget.size}")
    widget.size = (200, 100)
    print(f"New size: {widget.size}")
    
    # Test visibility
    print(f"Initial visibility: {widget.visible}")
    widget.visible = False
    print(f"New visibility: {widget.visible}")
    
    # Test alpha
    print(f"Initial alpha: {widget.alpha}")
    widget.alpha = 0.5
    print(f"New alpha: {widget.alpha}")
    
    # Test z-order
    print(f"Initial z-order: {widget.z_order}")
    widget.z_order = 10
    print(f"New z-order: {widget.z_order}")


def test_canvas_composition():
    """Test canvas and widget composition."""
    print("\n=== Testing Canvas Composition ===")
    
    # Create canvas
    config = CanvasConfig(width=128, height=64)
    canvas = Canvas(config)
    
    print(f"Canvas size: {canvas.width}x{canvas.height}")
    print(f"Canvas state: {canvas.state}")
    
    # Initialize canvas
    canvas.initialize()
    canvas.activate()
    print(f"Canvas state after activation: {canvas.state}")
    
    # Create and add widgets
    widget1 = TestWidget("widget1")
    widget2 = TestWidget("widget2")
    
    canvas.add_widget(widget1, position=(10, 10), z_order=1)
    canvas.add_widget(widget2, position=(50, 30), z_order=2)
    
    print(f"Canvas has {len(canvas.get_children())} widgets")
    
    # Test widget positioning
    widgets_at_pos = canvas.get_widgets_at_position(15, 15)
    print(f"Widgets at (15, 15): {len(widgets_at_pos)}")
    
    # Test rendering
    if canvas.needs_render():
        print("Canvas needs rendering")
        canvas.render()
        print("Canvas rendered")


def test_rendering_engine():
    """Test basic rendering engine functionality."""
    print("\n=== Testing Rendering Engine ===")
    
    # Create rendering config
    config = RenderingConfig(target_fps=60.0, memory_limit_mb=16)
    engine = RenderingEngine(config)
    
    print(f"Engine state: {engine.state}")
    print(f"Target FPS: {engine.config.target_fps}")
    print(f"Memory limit: {engine.config.memory_limit_mb}MB")
    
    # Initialize engine
    if engine.initialize():
        print("Engine initialized successfully")
    else:
        print("Engine initialization failed")
    
    print(f"Memory usage: {engine.memory_usage:.1f}%")


def test_reactive_manager():
    """Test reactive data manager."""
    print("\n=== Testing Reactive Manager ===")
    
    manager = get_reactive_manager()
    
    # Create direct binding
    binding = manager.create_direct_binding("test_value", 42)
    print(f"Direct binding value: {manager.get_value('test_value')}")
    
    # Update value
    manager.set_value("test_value", 100)
    print(f"Updated binding value: {manager.get_value('test_value')}")
    
    # Get stats
    stats = manager.get_binding_stats()
    print(f"Binding stats: {stats}")


def main():
    """Run all foundation tests."""
    print("Testing tinyDisplay Widget Foundation (Story 1.4)")
    print("=" * 50)
    
    try:
        test_widget_lifecycle()
        test_reactive_values()
        test_widget_properties()
        test_canvas_composition()
        test_rendering_engine()
        test_reactive_manager()
        
        print("\n" + "=" * 50)
        print("✅ All foundation tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 