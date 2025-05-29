#!/usr/bin/env python3
"""
Comprehensive Tests for Widget Base Class Coverage

This test file specifically targets the missing coverage areas in base.py
to bring the coverage up to >90% as required by operational guidelines.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, call
from typing import List, Dict, Any

from src.tinydisplay.widgets.base import (
    Widget, ContainerWidget, ReactiveValue, WidgetState, VisibilityState,
    WidgetBounds, VisibilityAnimation, TransparencyConfig
)


class MockWidget(Widget):
    """Concrete widget implementation for testing."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_count = 0
        self.render_calls = []
    
    def render(self, canvas):
        """Test render implementation."""
        self.render_count += 1
        self.render_calls.append(time.time())


class MockContainerWidget(ContainerWidget):
    """Concrete container widget implementation for testing."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_count = 0
        self.render_calls = []
    
    def render(self, canvas):
        """Test render implementation."""
        self.render_count += 1
        self.render_calls.append(time.time())


class TestWidgetBounds:
    """Test WidgetBounds functionality."""
    
    def test_widget_bounds_properties(self):
        """Test WidgetBounds properties and methods."""
        bounds = WidgetBounds(10, 20, 100, 50)
        
        assert bounds.x == 10
        assert bounds.y == 20
        assert bounds.width == 100
        assert bounds.height == 50
        assert bounds.right == 110
        assert bounds.bottom == 70
    
    def test_widget_bounds_contains_point(self):
        """Test point containment checking."""
        bounds = WidgetBounds(10, 20, 100, 50)
        
        # Points inside
        assert bounds.contains_point(50, 40) is True
        assert bounds.contains_point(10, 20) is True  # Top-left corner
        assert bounds.contains_point(109, 69) is True  # Bottom-right (exclusive)
        
        # Points outside
        assert bounds.contains_point(5, 40) is False  # Left
        assert bounds.contains_point(50, 15) is False  # Above
        assert bounds.contains_point(115, 40) is False  # Right
        assert bounds.contains_point(50, 75) is False  # Below
        assert bounds.contains_point(110, 70) is False  # Exactly on right/bottom edge
    
    def test_widget_bounds_intersects(self):
        """Test bounds intersection detection."""
        bounds1 = WidgetBounds(10, 10, 50, 50)  # 10,10 to 60,60
        
        # Overlapping bounds
        bounds2 = WidgetBounds(30, 30, 50, 50)  # 30,30 to 80,80
        assert bounds1.intersects(bounds2) is True
        assert bounds2.intersects(bounds1) is True
        
        # Adjacent bounds (no overlap)
        bounds3 = WidgetBounds(60, 10, 50, 50)  # 60,10 to 110,60
        assert bounds1.intersects(bounds3) is False
        assert bounds3.intersects(bounds1) is False
        
        # Completely separate bounds
        bounds4 = WidgetBounds(100, 100, 50, 50)  # 100,100 to 150,150
        assert bounds1.intersects(bounds4) is False
        assert bounds4.intersects(bounds1) is False
        
        # One inside the other
        bounds5 = WidgetBounds(20, 20, 20, 20)  # 20,20 to 40,40
        assert bounds1.intersects(bounds5) is True
        assert bounds5.intersects(bounds1) is True


class TestReactiveValue:
    """Test ReactiveValue functionality."""
    
    def test_reactive_value_basic_operations(self):
        """Test basic reactive value operations."""
        rv = ReactiveValue(42)
        
        assert rv.value == 42
        
        # Test value change
        rv.value = 100
        assert rv.value == 100
    
    def test_reactive_value_observers(self):
        """Test reactive value observer pattern."""
        rv = ReactiveValue(10)
        
        # Track observer calls
        observer_calls = []
        
        def observer(old_val, new_val):
            observer_calls.append((old_val, new_val))
        
        # Bind observer
        rv.bind(observer)
        
        # Change value
        rv.value = 20
        assert len(observer_calls) == 1
        assert observer_calls[0] == (10, 20)
        
        # Change again
        rv.value = 30
        assert len(observer_calls) == 2
        assert observer_calls[1] == (20, 30)
        
        # Unbind observer
        rv.unbind(observer)
        rv.value = 40
        assert len(observer_calls) == 2  # No new calls
    
    def test_reactive_value_dependencies(self):
        """Test reactive value dependency system."""
        source = ReactiveValue(5)
        dependent = ReactiveValue(0)
        
        # Track dependency changes
        dependency_calls = []
        
        def on_dependency_changed(old_val, new_val):
            dependency_calls.append((old_val, new_val))
        
        # Mock the dependency change handler
        dependent._on_dependency_changed = on_dependency_changed
        
        # Add dependency
        dependent.add_dependency(source)
        
        # Change source value
        source.value = 10
        assert len(dependency_calls) == 1
        assert dependency_calls[0] == (5, 10)
        
        # Remove dependency
        dependent.remove_dependency(source)
        source.value = 15
        assert len(dependency_calls) == 1  # No new calls
    
    def test_reactive_value_observer_error_handling(self):
        """Test error handling in reactive value observers."""
        rv = ReactiveValue(1)
        
        # Observer that raises exception
        def failing_observer(old_val, new_val):
            raise ValueError("Test error")
        
        # Observer that works
        working_calls = []
        def working_observer(old_val, new_val):
            working_calls.append((old_val, new_val))
        
        rv.bind(failing_observer)
        rv.bind(working_observer)
        
        # Change value - should not raise exception
        rv.value = 2
        
        # Working observer should still be called
        assert len(working_calls) == 1
        assert working_calls[0] == (1, 2)


class TestWidgetVisibilityAndAnimations:
    """Test widget visibility and animation functionality."""
    
    def test_widget_show_hide_basic(self):
        """Test basic show/hide functionality."""
        widget = MockWidget("test")
        
        # Test show (non-animated)
        widget._visibility_state = VisibilityState.HIDDEN
        widget.show(animated=False)
        
        assert widget._visibility_state == VisibilityState.VISIBLE
        assert widget.visible is True
    
    def test_widget_show_already_visible(self):
        """Test show when already visible."""
        widget = MockWidget("test")
        widget._visibility_state = VisibilityState.VISIBLE
        
        # Should be no-op
        widget.show(animated=False)
        assert widget._visibility_state == VisibilityState.VISIBLE
    
    def test_widget_hide_basic(self):
        """Test basic hide functionality."""
        widget = MockWidget("test")
        
        # Test hide (non-animated)
        widget._visibility_state = VisibilityState.VISIBLE
        widget.hide(animated=False)
        
        assert widget._visibility_state == VisibilityState.HIDDEN
        assert widget.visible is False
    
    def test_widget_hide_already_hidden(self):
        """Test hide when already hidden."""
        widget = MockWidget("test")
        widget._visibility_state = VisibilityState.HIDDEN
        
        # Should be no-op
        widget.hide(animated=False)
        assert widget._visibility_state == VisibilityState.HIDDEN
    
    def test_widget_collapse(self):
        """Test widget collapse functionality."""
        widget = MockWidget("test")
        
        widget.collapse()
        
        assert widget._visibility_state == VisibilityState.COLLAPSED
        assert widget.visible is False
    
    def test_widget_toggle_visibility(self):
        """Test visibility toggling."""
        widget = MockWidget("test")
        
        # Start visible, toggle to hidden
        widget._visibility_state = VisibilityState.VISIBLE
        widget.toggle_visibility(animated=False)
        assert widget._visibility_state == VisibilityState.HIDDEN
        
        # Toggle back to visible
        widget.toggle_visibility(animated=False)
        assert widget._visibility_state == VisibilityState.VISIBLE
    
    def test_widget_animated_show(self):
        """Test animated show functionality."""
        widget = MockWidget("test")
        widget._visibility_state = VisibilityState.HIDDEN
        
        animation_config = VisibilityAnimation(duration=0.1, easing="linear")
        widget.show(animated=True, animation_config=animation_config)
        
        assert widget._visibility_state == VisibilityState.FADING_IN
        assert widget.visible is True
        assert widget.alpha == 0.0
        assert widget._current_animation is not None
        assert widget._current_animation['type'] == 'fade_in'
    
    def test_widget_animated_hide(self):
        """Test animated hide functionality."""
        widget = MockWidget("test")
        widget._visibility_state = VisibilityState.VISIBLE
        widget.alpha = 1.0
        
        animation_config = VisibilityAnimation(duration=0.1, easing="linear")
        widget.hide(animated=True, animation_config=animation_config)
        
        assert widget._visibility_state == VisibilityState.FADING_OUT
        assert widget._current_animation is not None
        assert widget._current_animation['type'] == 'fade_out'
    
    def test_widget_alpha_animation(self):
        """Test alpha animation functionality."""
        widget = MockWidget("test")
        widget.alpha = 0.0
        
        # Test animation setup
        callback_called = []
        def on_complete():
            callback_called.append(True)
        
        widget.set_alpha_animated(1.0, duration=0.1, on_complete=on_complete)
        
        assert widget._current_animation is not None
        assert widget._current_animation['type'] == 'alpha'
        assert widget._current_animation['duration'] == 0.1
        assert widget._current_animation['on_complete'] == on_complete
        assert widget._animation_target_alpha == 1.0
    
    def test_widget_alpha_animation_no_change(self):
        """Test alpha animation when target equals current."""
        widget = MockWidget("test")
        widget.alpha = 0.5
        
        callback_called = []
        def on_complete():
            callback_called.append(True)
        
        # Target same as current - should call callback immediately
        widget.set_alpha_animated(0.5, on_complete=on_complete)
        
        assert len(callback_called) == 1
        assert widget._current_animation is None
    
    def test_widget_update_animations_alpha(self):
        """Test animation update for alpha animations."""
        widget = MockWidget("test")
        widget.alpha = 0.0
        
        # Start animation
        widget.set_alpha_animated(1.0, duration=0.1)
        start_time = time.time()
        widget._animation_start_time = start_time
        
        # Simulate mid-animation
        with patch('time.time', return_value=start_time + 0.05):  # 50% through
            widget.update_animations()
            # Should be approximately 0.5
            assert 0.4 <= widget.alpha <= 0.6
        
        # Simulate animation complete
        with patch('time.time', return_value=start_time + 0.2):  # Past duration
            widget.update_animations()
            assert widget.alpha == 1.0
            assert widget._current_animation is None
    
    def test_widget_update_animations_fade_in(self):
        """Test animation update for fade in animations."""
        widget = MockWidget("test")
        
        # Start fade in animation
        animation_config = VisibilityAnimation(duration=0.1)
        widget._start_fade_in_animation(animation_config)
        start_time = time.time()
        widget._animation_start_time = start_time
        
        # Simulate animation complete
        with patch('time.time', return_value=start_time + 0.2):
            widget.update_animations()
            assert widget.alpha == 1.0
            assert widget._visibility_state == VisibilityState.VISIBLE
            assert widget.visible is True
            assert widget._current_animation is None
    
    def test_widget_update_animations_fade_out(self):
        """Test animation update for fade out animations."""
        widget = MockWidget("test")
        
        # Start fade out animation
        animation_config = VisibilityAnimation(duration=0.1)
        widget._start_fade_out_animation(animation_config)
        start_time = time.time()
        widget._animation_start_time = start_time
        
        # Simulate animation complete
        with patch('time.time', return_value=start_time + 0.2):
            widget.update_animations()
            assert widget.alpha == 0.0
            assert widget._visibility_state == VisibilityState.HIDDEN
            assert widget.visible is False
            assert widget._current_animation is None
    
    def test_widget_update_animations_with_callback(self):
        """Test animation completion callback."""
        widget = MockWidget("test")
        
        callback_called = []
        def on_complete():
            callback_called.append(True)
        
        # Start animation with callback
        widget.set_alpha_animated(1.0, duration=0.1, on_complete=on_complete)
        start_time = time.time()
        widget._animation_start_time = start_time
        
        # Complete animation
        with patch('time.time', return_value=start_time + 0.2):
            widget.update_animations()
            
        assert len(callback_called) == 1
    
    def test_widget_easing_functions(self):
        """Test animation easing functions."""
        widget = MockWidget("test")
        
        # Test linear easing
        assert widget._apply_easing(0.5, "linear") == 0.5
        
        # Test ease_in
        result = widget._apply_easing(0.5, "ease_in")
        assert result == 0.25  # 0.5^2
        
        # Test ease_out
        result = widget._apply_easing(0.5, "ease_out")
        assert result == 0.75  # 1 - (1-0.5)^2
        
        # Test ease_in_out
        result = widget._apply_easing(0.25, "ease_in_out")
        assert result == 0.125  # 2 * 0.25^2
        
        result = widget._apply_easing(0.75, "ease_in_out")
        assert result == 0.875  # 1 - 2 * (1-0.75)^2
        
        # Test ease_in_cubic
        result = widget._apply_easing(0.5, "ease_in_cubic")
        assert result == 0.125  # 0.5^3
        
        # Test ease_out_cubic
        result = widget._apply_easing(0.5, "ease_out_cubic")
        assert result == 0.875  # 1 - (1-0.5)^3
        
        # Test ease_in_out_cubic
        result = widget._apply_easing(0.25, "ease_in_out_cubic")
        assert result == 0.0625  # 4 * 0.25^3
        
        # Test unknown easing (should default to ease_in_out)
        result = widget._apply_easing(0.5, "unknown")
        expected = widget._apply_easing(0.5, "ease_in_out")
        assert result == expected


class TestWidgetReactiveBinding:
    """Test widget reactive data binding functionality."""
    
    def test_widget_bind_data(self):
        """Test binding reactive data to widget properties."""
        widget = MockWidget("test")
        reactive_val = ReactiveValue(100)
        
        widget.bind_data("test_prop", reactive_val)
        
        assert "test_prop" in widget._reactive_bindings
        assert widget._reactive_bindings["test_prop"] == reactive_val
    
    def test_widget_bind_data_replace_existing(self):
        """Test replacing existing reactive binding."""
        widget = MockWidget("test")
        reactive_val1 = ReactiveValue(100)
        reactive_val2 = ReactiveValue(200)
        
        # Bind first value
        widget.bind_data("test_prop", reactive_val1)
        
        # Replace with second value
        widget.bind_data("test_prop", reactive_val2)
        
        assert widget._reactive_bindings["test_prop"] == reactive_val2
    
    def test_widget_unbind_data(self):
        """Test unbinding reactive data."""
        widget = MockWidget("test")
        reactive_val = ReactiveValue(100)
        
        widget.bind_data("test_prop", reactive_val)
        assert "test_prop" in widget._reactive_bindings
        
        widget.unbind_data("test_prop")
        assert "test_prop" not in widget._reactive_bindings
    
    def test_widget_unbind_data_nonexistent(self):
        """Test unbinding non-existent reactive data."""
        widget = MockWidget("test")
        
        # Should not raise exception
        widget.unbind_data("nonexistent_prop")
    
    def test_widget_get_reactive_value(self):
        """Test getting reactive value by property name."""
        widget = MockWidget("test")
        reactive_val = ReactiveValue(100)
        
        widget.bind_data("test_prop", reactive_val)
        
        retrieved = widget.get_reactive_value("test_prop")
        assert retrieved == reactive_val
        
        # Test non-existent property
        assert widget.get_reactive_value("nonexistent") is None
    
    def test_widget_reactive_data_change_triggers_dirty(self):
        """Test that reactive data changes mark widget as dirty."""
        widget = MockWidget("test")
        reactive_val = ReactiveValue(100)
        
        widget.bind_data("test_prop", reactive_val)
        widget.mark_clean()
        assert not widget.is_dirty
        
        # Change reactive value
        reactive_val.value = 200
        
        assert widget.is_dirty


class TestWidgetTransparency:
    """Test widget transparency and alpha inheritance."""
    
    def test_widget_transparency_config(self):
        """Test transparency configuration."""
        widget = MockWidget("test")
        
        config = TransparencyConfig(
            inherit_from_parent=False,
            min_alpha=0.1,
            max_alpha=0.9,
            blend_mode="multiply"
        )
        
        widget.transparency_config = config
        
        assert widget.transparency_config == config
        assert widget.transparency_config.inherit_from_parent is False
        assert widget.transparency_config.min_alpha == 0.1
        assert widget.transparency_config.max_alpha == 0.9
    
    def test_widget_effective_alpha_no_parent(self):
        """Test effective alpha calculation without parent."""
        widget = MockWidget("test")
        widget.alpha = 0.5
        
        widget._transparency_config.inherit_from_parent = False
        widget._update_effective_alpha()
        
        assert widget.effective_alpha == 0.5
    
    def test_widget_effective_alpha_with_parent(self):
        """Test effective alpha calculation with parent inheritance."""
        parent = MockWidget("parent")
        child = MockWidget("child")
        
        parent.alpha = 0.8
        parent._effective_alpha = 0.8
        child.alpha = 0.5
        child._transparency_config.inherit_from_parent = True
        
        child.set_parent_widget(parent)
        
        # Effective alpha should be child.alpha * parent.effective_alpha
        assert child.effective_alpha == 0.4  # 0.5 * 0.8
    
    def test_widget_effective_alpha_constraints(self):
        """Test effective alpha with min/max constraints."""
        widget = MockWidget("test")
        widget.alpha = 0.05  # Below min
        widget._transparency_config.min_alpha = 0.1
        widget._transparency_config.max_alpha = 0.9
        widget._transparency_config.inherit_from_parent = False
        
        widget._update_effective_alpha()
        
        assert widget.effective_alpha == 0.1  # Clamped to min
        
        # Test max constraint
        widget.alpha = 0.95  # Above max
        widget._update_effective_alpha()
        
        assert widget.effective_alpha == 0.9  # Clamped to max
    
    def test_widget_set_parent_widget(self):
        """Test setting parent widget."""
        parent = MockWidget("parent")
        child = MockWidget("child")
        
        child.set_parent_widget(parent)
        
        assert child._parent_widget == parent
    
    def test_widget_alpha_change_propagation(self):
        """Test alpha change propagation to children."""
        parent = MockContainerWidget("parent")
        child = MockWidget("child")
        
        # Set up parent-child relationship
        child._transparency_config.inherit_from_parent = True
        parent.add_child(child)  # This sets up the parent-child relationship
        
        # Mock child's update method to track calls
        original_update = child._update_effective_alpha
        child._update_effective_alpha = Mock(side_effect=original_update)
        
        # Change parent alpha - this should trigger propagation to children
        parent._on_alpha_changed(0.5, 0.8)
        
        # Child should have its effective alpha updated
        child._update_effective_alpha.assert_called_once()


class TestContainerWidget:
    """Test ContainerWidget functionality."""
    
    def test_container_widget_creation(self):
        """Test container widget creation."""
        container = MockContainerWidget("container")
        
        assert container.widget_id == "container"
        assert len(container._children) == 0
        assert len(container._child_order) == 0
    
    def test_container_add_child(self):
        """Test adding child to container."""
        container = MockContainerWidget("container")
        child = MockWidget("child")
        
        container.add_child(child)
        
        assert "child" in container._children
        assert container._children["child"] == child
        assert "child" in container._child_order
        assert child._parent_widget == container
    
    def test_container_add_duplicate_child(self):
        """Test adding child with duplicate ID."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child")
        child2 = MockWidget("child")  # Same ID
        
        container.add_child(child1)
        container.add_child(child2)  # Should not add duplicate
        
        assert len(container._children) == 1
        assert len(container._child_order) == 1
    
    def test_container_remove_child(self):
        """Test removing child from container."""
        container = MockContainerWidget("container")
        child = MockWidget("child")
        
        container.add_child(child)
        removed = container.remove_child("child")
        
        assert removed == child
        assert "child" not in container._children
        assert "child" not in container._child_order
        assert child._parent_widget is None
    
    def test_container_remove_nonexistent_child(self):
        """Test removing non-existent child."""
        container = MockContainerWidget("container")
        
        removed = container.remove_child("nonexistent")
        assert removed is None
    
    def test_container_get_child(self):
        """Test getting child by ID."""
        container = MockContainerWidget("container")
        child = MockWidget("child")
        
        container.add_child(child)
        
        retrieved = container.get_child("child")
        assert retrieved == child
        
        # Test non-existent child
        assert container.get_child("nonexistent") is None
    
    def test_container_get_children(self):
        """Test getting all children in order."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child1")
        child2 = MockWidget("child2")
        child3 = MockWidget("child3")
        
        container.add_child(child1)
        container.add_child(child2)
        container.add_child(child3)
        
        children = container.get_children()
        assert len(children) == 3
        assert children[0] == child1
        assert children[1] == child2
        assert children[2] == child3
    
    def test_container_propagate_visibility_to_children(self):
        """Test visibility propagation to children."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child1")
        child2 = MockWidget("child2")
        
        # Set up children with different visibility states
        child1._visibility_state = VisibilityState.VISIBLE
        child2._visibility_state = VisibilityState.HIDDEN
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Mock show/hide methods
        child1.show = Mock()
        child1.hide = Mock()
        child2.show = Mock()
        child2.hide = Mock()
        
        # Propagate visibility = True
        container.propagate_visibility_to_children(True)
        child1.show.assert_called_once()
        child2.show.assert_not_called()  # Already hidden, shouldn't show
        
        # Reset mocks
        child1.show.reset_mock()
        child2.show.reset_mock()
        
        # Propagate visibility = False
        container.propagate_visibility_to_children(False)
        child1.hide.assert_called_once()
        child2.hide.assert_called_once()
    
    def test_container_show_all_children(self):
        """Test showing all children."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child1")
        child2 = MockWidget("child2")
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Mock show methods
        child1.show = Mock()
        child2.show = Mock()
        
        animation_config = VisibilityAnimation(duration=0.5)
        container.show_all_children(animated=True, animation_config=animation_config)
        
        child1.show.assert_called_once_with(True, animation_config)
        child2.show.assert_called_once_with(True, animation_config)
    
    def test_container_hide_all_children(self):
        """Test hiding all children."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child1")
        child2 = MockWidget("child2")
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Mock hide methods
        child1.hide = Mock()
        child2.hide = Mock()
        
        animation_config = VisibilityAnimation(duration=0.5)
        container.hide_all_children(animated=True, animation_config=animation_config)
        
        child1.hide.assert_called_once_with(True, animation_config)
        child2.hide.assert_called_once_with(True, animation_config)
    
    def test_container_update_all_animations(self):
        """Test updating animations for container and children."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child1")
        child2 = MockContainerWidget("child2")  # Nested container
        grandchild = MockWidget("grandchild")
        
        child2.add_child(grandchild)
        container.add_child(child1)
        container.add_child(child2)
        
        # Mock update_animations methods
        container.update_animations = Mock()
        child1.update_animations = Mock()
        child2.update_all_animations = Mock()
        
        # Call the real method
        MockContainerWidget.update_all_animations(container)
        
        container.update_animations.assert_called_once()
        child1.update_animations.assert_called_once()
        child2.update_all_animations.assert_called_once()
    
    def test_container_destroy(self):
        """Test container destruction with children."""
        container = MockContainerWidget("container")
        child1 = MockWidget("child1")
        child2 = MockWidget("child2")
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Mock child destroy methods
        child1.destroy = Mock()
        child2.destroy = Mock()
        
        container.destroy()
        
        child1.destroy.assert_called_once()
        child2.destroy.assert_called_once()
        assert len(container._children) == 0
        assert len(container._child_order) == 0


class TestWidgetUtilityMethods:
    """Test widget utility and helper methods."""
    
    def test_widget_contains_point(self):
        """Test widget point containment."""
        widget = MockWidget("test")
        widget.position = (10, 20)
        widget.size = (100, 50)
        
        # Points inside
        assert widget.contains_point(50, 40) is True
        assert widget.contains_point(10, 20) is True  # Top-left corner
        
        # Points outside
        assert widget.contains_point(5, 40) is False
        assert widget.contains_point(50, 15) is False
        assert widget.contains_point(115, 40) is False
        assert widget.contains_point(50, 75) is False
    
    def test_widget_intersects_widget(self):
        """Test widget intersection detection."""
        widget1 = MockWidget("widget1")
        widget1.position = (10, 10)
        widget1.size = (50, 50)
        
        widget2 = MockWidget("widget2")
        widget2.position = (30, 30)
        widget2.size = (50, 50)
        
        # Should intersect
        assert widget1.intersects_widget(widget2) is True
        assert widget2.intersects_widget(widget1) is True
        
        # Move widget2 away
        widget2.position = (100, 100)
        assert widget1.intersects_widget(widget2) is False
        assert widget2.intersects_widget(widget1) is False
    
    def test_widget_bounds_property(self):
        """Test widget bounds property calculation."""
        widget = MockWidget("test")
        widget.position = (15, 25)
        widget.size = (80, 60)
        
        bounds = widget.bounds
        assert bounds.x == 15
        assert bounds.y == 25
        assert bounds.width == 80
        assert bounds.height == 60
        assert bounds.right == 95
        assert bounds.bottom == 85
    
    def test_widget_repr(self):
        """Test widget string representation."""
        widget = MockWidget("test_widget")
        widget.position = (10, 20)
        widget.size = (100, 50)
        
        repr_str = repr(widget)
        assert "MockWidget" in repr_str
        assert "test_widget" in repr_str
        assert "(10, 20)" in repr_str
        assert "(100, 50)" in repr_str


class TestWidgetLifecycleHooks:
    """Test widget lifecycle hook functionality."""
    
    def test_widget_add_lifecycle_hook(self):
        """Test adding lifecycle hooks."""
        widget = MockWidget("test")
        
        hook_calls = []
        def test_hook(w):
            hook_calls.append(w.widget_id)
        
        widget.add_lifecycle_hook('update', test_hook)
        
        assert test_hook in widget._lifecycle_hooks['update']
    
    def test_widget_remove_lifecycle_hook(self):
        """Test removing lifecycle hooks."""
        widget = MockWidget("test")
        
        def test_hook(w):
            pass
        
        widget.add_lifecycle_hook('update', test_hook)
        assert test_hook in widget._lifecycle_hooks['update']
        
        widget.remove_lifecycle_hook('update', test_hook)
        assert test_hook not in widget._lifecycle_hooks['update']
    
    def test_widget_call_lifecycle_hooks(self):
        """Test calling lifecycle hooks."""
        widget = MockWidget("test")
        
        hook_calls = []
        def test_hook1(w):
            hook_calls.append(f"hook1_{w.widget_id}")
        
        def test_hook2(w):
            hook_calls.append(f"hook2_{w.widget_id}")
        
        widget.add_lifecycle_hook('update', test_hook1)
        widget.add_lifecycle_hook('update', test_hook2)
        
        widget._call_lifecycle_hooks('update')
        
        assert len(hook_calls) == 2
        assert "hook1_test" in hook_calls
        assert "hook2_test" in hook_calls
    
    def test_widget_lifecycle_hook_error_handling(self):
        """Test error handling in lifecycle hooks."""
        widget = MockWidget("test")
        
        def failing_hook(w):
            raise ValueError("Test error")
        
        working_calls = []
        def working_hook(w):
            working_calls.append(w.widget_id)
        
        widget.add_lifecycle_hook('update', failing_hook)
        widget.add_lifecycle_hook('update', working_hook)
        
        # Should not raise exception
        widget._call_lifecycle_hooks('update')
        
        # Working hook should still be called
        assert len(working_calls) == 1
        assert working_calls[0] == "test"


class TestWidgetStateTransitions:
    """Test widget state transition functionality."""
    
    def test_widget_initialization(self):
        """Test widget initialization state transition."""
        widget = MockWidget("test")
        
        assert widget.state == WidgetState.CREATED
        
        widget.initialize()
        assert widget.state == WidgetState.INITIALIZED
    
    def test_widget_activation(self):
        """Test widget activation state transition."""
        widget = MockWidget("test")
        widget.initialize()
        
        widget.activate()
        assert widget.state == WidgetState.ACTIVE
    
    def test_widget_hide_lifecycle(self):
        """Test widget hide lifecycle method."""
        widget = MockWidget("test")
        widget.initialize()
        widget.activate()
        
        widget.hide_widget()
        assert widget.state == WidgetState.HIDDEN
    
    def test_widget_destruction(self):
        """Test widget destruction state transition."""
        widget = MockWidget("test")
        widget.initialize()
        
        widget.destroy()
        assert widget.state == WidgetState.DESTROYED
    
    def test_widget_is_animating_property(self):
        """Test widget is_animating property."""
        widget = MockWidget("test")
        
        assert widget.is_animating is False
        
        # Start animation with different target alpha
        widget.alpha = 0.0
        widget.set_alpha_animated(1.0, duration=0.1)
        assert widget.is_animating is True
        
        # Complete animation
        start_time = time.time()
        widget._animation_start_time = start_time
        with patch('time.time', return_value=start_time + 0.2):
            widget.update_animations()
        
        assert widget.is_animating is False


class TestWidgetCleanupAndErrorHandling:
    """Test widget cleanup and error handling functionality."""
    
    def test_widget_cleanup_reactive_bindings(self):
        """Test cleanup of reactive bindings on destroy."""
        widget = MockWidget("test")
        reactive_val = ReactiveValue(100)
        
        widget.bind_data("test_prop", reactive_val)
        assert len(widget._reactive_bindings) == 1
        
        widget.destroy()
        assert len(widget._reactive_bindings) == 0
    
    def test_widget_needs_render(self):
        """Test widget needs_render functionality."""
        widget = MockWidget("test")
        
        # Widget needs to be active and visible to need rendering
        widget.initialize()
        widget.activate()
        widget.visible = True
        
        # Widget starts dirty
        assert widget.needs_render() is True
        
        # Mark clean
        widget.mark_clean()
        assert widget.needs_render() is False
        
        # Mark dirty again
        widget._mark_dirty()
        assert widget.needs_render() is True
        
        # Test when not visible
        widget.visible = False
        assert widget.needs_render() is False
        
        # Test when not active
        widget.visible = True
        widget._state = WidgetState.HIDDEN
        assert widget.needs_render() is False
    
    def test_widget_mark_dirty_with_values(self):
        """Test _mark_dirty with old and new values."""
        widget = MockWidget("test")
        widget.mark_clean()
        
        # Mark dirty with values
        widget._mark_dirty("old_value", "new_value")
        assert widget.is_dirty is True


if __name__ == "__main__":
    pytest.main([__file__]) 