#!/usr/bin/env python3
"""
Test Visibility and Transparency Controls

Tests for the enhanced visibility and transparency functionality in Story 1.4 Task 6.
"""

import pytest
import time
from unittest.mock import Mock

from src.tinydisplay.widgets import (
    Widget, ContainerWidget, VisibilityState, VisibilityAnimation, 
    TransparencyConfig, WidgetState
)


class TestWidget(Widget):
    """Simple test widget implementation."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_count = 0
    
    def render(self, canvas):
        """Simple render implementation."""
        self.render_count += 1


class TestVisibilityState:
    """Test visibility state management."""
    
    def test_initial_visibility_state(self):
        """Test initial visibility state."""
        widget = TestWidget("test_widget")
        
        assert widget.visibility_state == VisibilityState.VISIBLE
        assert widget.visible is True
        assert widget.alpha == 1.0
        assert widget.effective_alpha == 1.0
    
    def test_show_hide_methods(self):
        """Test show and hide methods."""
        widget = TestWidget("test_widget")
        
        # Test hide
        widget.hide()
        assert widget.visibility_state == VisibilityState.HIDDEN
        assert widget.visible is False
        
        # Test show
        widget.show()
        assert widget.visibility_state == VisibilityState.VISIBLE
        assert widget.visible is True
    
    def test_collapse_method(self):
        """Test collapse method."""
        widget = TestWidget("test_widget")
        
        widget.collapse()
        assert widget.visibility_state == VisibilityState.COLLAPSED
        assert widget.visible is False
    
    def test_toggle_visibility(self):
        """Test visibility toggle."""
        widget = TestWidget("test_widget")
        
        # Initially visible
        assert widget.visibility_state == VisibilityState.VISIBLE
        
        # Toggle to hidden
        widget.toggle_visibility()
        assert widget.visibility_state == VisibilityState.HIDDEN
        
        # Toggle back to visible
        widget.toggle_visibility()
        assert widget.visibility_state == VisibilityState.VISIBLE


class TestTransparencyControls:
    """Test transparency and alpha controls."""
    
    def test_alpha_property(self):
        """Test alpha property."""
        widget = TestWidget("test_widget")
        
        # Test setting alpha
        widget.alpha = 0.5
        assert widget.alpha == 0.5
        assert widget.effective_alpha == 0.5
        
        # Test alpha clamping
        widget.alpha = 1.5
        assert widget.alpha == 1.0
        
        widget.alpha = -0.5
        assert widget.alpha == 0.0
    
    def test_transparency_config(self):
        """Test transparency configuration."""
        widget = TestWidget("test_widget")
        
        # Test custom transparency config
        config = TransparencyConfig(
            inherit_from_parent=False,
            min_alpha=0.2,
            max_alpha=0.8
        )
        widget.transparency_config = config
        
        assert widget.transparency_config.min_alpha == 0.2
        assert widget.transparency_config.max_alpha == 0.8
        assert not widget.transparency_config.inherit_from_parent
    
    def test_effective_alpha_calculation(self):
        """Test effective alpha calculation with constraints."""
        widget = TestWidget("test_widget")
        
        # Set transparency config with constraints
        config = TransparencyConfig(min_alpha=0.2, max_alpha=0.8)
        widget.transparency_config = config
        
        # Test alpha within range
        widget.alpha = 0.5
        assert widget.effective_alpha == 0.5
        
        # Test alpha below minimum (should be clamped)
        widget.alpha = 0.1
        assert widget.effective_alpha == 0.2
        
        # Test alpha above maximum (should be clamped)
        widget.alpha = 0.9
        assert widget.effective_alpha == 0.8
    
    def test_parent_alpha_inheritance(self):
        """Test alpha inheritance from parent."""
        parent = ContainerWidget("parent")
        child = TestWidget("child")
        
        # Add child to parent
        parent.add_child(child)
        
        # Set parent alpha
        parent.alpha = 0.5
        
        # Child should inherit parent alpha
        assert child.effective_alpha == 0.5  # 1.0 * 0.5
        
        # Set child alpha
        child.alpha = 0.8
        
        # Child effective alpha should be child * parent
        assert child.effective_alpha == 0.4  # 0.8 * 0.5
    
    def test_alpha_inheritance_disabled(self):
        """Test alpha inheritance when disabled."""
        parent = ContainerWidget("parent")
        child = TestWidget("child")
        
        # Disable inheritance
        config = TransparencyConfig(inherit_from_parent=False)
        child.transparency_config = config
        
        parent.add_child(child)
        parent.alpha = 0.5
        child.alpha = 0.8
        
        # Child should not inherit parent alpha
        assert child.effective_alpha == 0.8


class TestVisibilityAnimations:
    """Test visibility animations."""
    
    def test_animated_show_hide(self):
        """Test animated show and hide."""
        widget = TestWidget("test_widget")
        
        # Start with hidden widget
        widget.hide()
        assert widget.visibility_state == VisibilityState.HIDDEN
        
        # Animate show
        animation_config = VisibilityAnimation(duration=0.1)
        widget.show(animated=True, animation_config=animation_config)
        
        assert widget.visibility_state == VisibilityState.FADING_IN
        assert widget.is_animating
        assert widget.alpha == 0.0  # Should start at 0
        
        # Animate hide
        widget.hide(animated=True, animation_config=animation_config)
        
        assert widget.visibility_state == VisibilityState.FADING_OUT
        assert widget.is_animating
    
    def test_alpha_animation(self):
        """Test alpha animation."""
        widget = TestWidget("test_widget")
        
        # Start alpha animation
        widget.set_alpha_animated(0.5, duration=0.1)
        
        assert widget.is_animating
        
        # Animation should be in progress
        assert widget._current_animation['type'] == 'alpha'
        assert widget._animation_target_alpha == 0.5
    
    def test_animation_completion_callback(self):
        """Test animation completion callback."""
        widget = TestWidget("test_widget")
        callback_called = []
        
        def on_complete():
            callback_called.append(True)
        
        # Start animation with callback
        animation_config = VisibilityAnimation(duration=0.01, on_complete=on_complete)
        widget.hide(animated=True, animation_config=animation_config)
        
        # Wait for animation to complete
        time.sleep(0.02)
        widget.update_animations()
        
        assert len(callback_called) == 1
        assert not widget.is_animating
    
    def test_animation_update(self):
        """Test animation update mechanism."""
        widget = TestWidget("test_widget")
        
        # Start fade out animation
        widget.set_alpha_animated(0.0, duration=0.1)
        initial_alpha = widget.alpha
        
        # Simulate time passing
        widget._animation_start_time = time.time() - 0.05  # 50% through
        widget.update_animations()
        
        # Alpha should be between initial and target
        assert 0.0 <= widget.alpha <= initial_alpha
        assert widget.is_animating


class TestEasingFunctions:
    """Test easing functions."""
    
    def test_linear_easing(self):
        """Test linear easing."""
        widget = TestWidget("test_widget")
        
        assert widget._apply_easing(0.0, "linear") == 0.0
        assert widget._apply_easing(0.5, "linear") == 0.5
        assert widget._apply_easing(1.0, "linear") == 1.0
    
    def test_ease_in_easing(self):
        """Test ease in easing."""
        widget = TestWidget("test_widget")
        
        assert widget._apply_easing(0.0, "ease_in") == 0.0
        assert widget._apply_easing(1.0, "ease_in") == 1.0
        
        # Ease in should be slower at start
        mid_point = widget._apply_easing(0.5, "ease_in")
        assert mid_point < 0.5
    
    def test_ease_out_easing(self):
        """Test ease out easing."""
        widget = TestWidget("test_widget")
        
        assert widget._apply_easing(0.0, "ease_out") == 0.0
        assert widget._apply_easing(1.0, "ease_out") == 1.0
        
        # Ease out should be faster at start
        mid_point = widget._apply_easing(0.5, "ease_out")
        assert mid_point > 0.5
    
    def test_ease_in_out_easing(self):
        """Test ease in out easing."""
        widget = TestWidget("test_widget")
        
        assert widget._apply_easing(0.0, "ease_in_out") == 0.0
        assert widget._apply_easing(0.5, "ease_in_out") == 0.5
        assert widget._apply_easing(1.0, "ease_in_out") == 1.0


class TestContainerVisibilityPropagation:
    """Test visibility propagation in containers."""
    
    def test_visibility_propagation(self):
        """Test visibility propagation to children."""
        container = ContainerWidget("container")
        child1 = TestWidget("child1")
        child2 = TestWidget("child2")
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Hide container
        container.hide()
        
        # Children should be hidden
        assert child1.visibility_state == VisibilityState.HIDDEN
        assert child2.visibility_state == VisibilityState.HIDDEN
        
        # Show container
        container.show()
        
        # Children should be visible
        assert child1.visibility_state == VisibilityState.VISIBLE
        assert child2.visibility_state == VisibilityState.VISIBLE
    
    def test_show_hide_all_children(self):
        """Test show/hide all children methods."""
        container = ContainerWidget("container")
        child1 = TestWidget("child1")
        child2 = TestWidget("child2")
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Hide all children
        container.hide_all_children()
        
        assert child1.visibility_state == VisibilityState.HIDDEN
        assert child2.visibility_state == VisibilityState.HIDDEN
        
        # Show all children
        container.show_all_children()
        
        assert child1.visibility_state == VisibilityState.VISIBLE
        assert child2.visibility_state == VisibilityState.VISIBLE
    
    def test_animated_children_visibility(self):
        """Test animated visibility changes for children."""
        container = ContainerWidget("container")
        child1 = TestWidget("child1")
        child2 = TestWidget("child2")
        
        container.add_child(child1)
        container.add_child(child2)
        
        # Animate hide all children
        animation_config = VisibilityAnimation(duration=0.1)
        container.hide_all_children(animated=True, animation_config=animation_config)
        
        assert child1.visibility_state == VisibilityState.FADING_OUT
        assert child2.visibility_state == VisibilityState.FADING_OUT
        assert child1.is_animating
        assert child2.is_animating
    
    def test_update_all_animations(self):
        """Test updating animations for container and children."""
        container = ContainerWidget("container")
        child = TestWidget("child")
        
        container.add_child(child)
        
        # Start animations
        container.set_alpha_animated(0.5, duration=0.1)
        child.set_alpha_animated(0.3, duration=0.1)
        
        assert container.is_animating
        assert child.is_animating
        
        # Update all animations
        container.update_all_animations()
        
        # Both should still be animating (since duration hasn't passed)
        assert container.is_animating
        assert child.is_animating


class TestLifecycleHooks:
    """Test visibility and transparency lifecycle hooks."""
    
    def test_visibility_changed_hook(self):
        """Test visibility changed lifecycle hook."""
        widget = TestWidget("test_widget")
        hook_calls = []
        
        def on_visibility_changed(w):
            hook_calls.append(w.visibility_state)
        
        widget.add_lifecycle_hook('visibility_changed', on_visibility_changed)
        
        # Change visibility
        widget.hide()
        widget.show()
        
        assert len(hook_calls) == 2
        assert VisibilityState.HIDDEN in hook_calls
        assert VisibilityState.VISIBLE in hook_calls
    
    def test_alpha_changed_hook(self):
        """Test alpha changed lifecycle hook."""
        widget = TestWidget("test_widget")
        hook_calls = []
        
        def on_alpha_changed(w):
            hook_calls.append(w.alpha)
        
        widget.add_lifecycle_hook('alpha_changed', on_alpha_changed)
        
        # Change alpha
        widget.alpha = 0.5
        widget.alpha = 0.8
        
        assert len(hook_calls) == 2
        assert 0.5 in hook_calls
        assert 0.8 in hook_calls


class TestRenderingIntegration:
    """Test integration with rendering system."""
    
    def test_needs_render_with_visibility(self):
        """Test needs_render considers visibility."""
        widget = TestWidget("test_widget")
        widget.initialize()
        widget.activate()
        
        # Visible widget should need render when dirty
        assert widget.needs_render()
        
        # Hidden widget should not need render
        widget.hide()
        assert not widget.needs_render()
        
        # Show widget again
        widget.show()
        assert widget.needs_render()
    
    def test_effective_alpha_in_rendering(self):
        """Test effective alpha is available for rendering."""
        parent = ContainerWidget("parent")
        child = TestWidget("child")
        
        parent.add_child(child)
        parent.alpha = 0.6
        child.alpha = 0.8
        
        # Effective alpha should be computed
        assert child.effective_alpha == 0.48  # 0.6 * 0.8
        
        # This would be used by rendering system
        assert child.effective_alpha != child.alpha


if __name__ == "__main__":
    # Run basic functionality test
    print("Testing Visibility and Transparency Controls...")
    
    # Test basic visibility
    widget = TestWidget("test_widget")
    print(f"Initial state: visible={widget.visible}, alpha={widget.alpha}")
    
    # Test hide/show
    widget.hide()
    print(f"After hide: visible={widget.visible}, state={widget.visibility_state}")
    
    widget.show()
    print(f"After show: visible={widget.visible}, state={widget.visibility_state}")
    
    # Test alpha animation
    print("Starting alpha animation...")
    widget.set_alpha_animated(0.5, duration=0.1)
    print(f"Animation started: is_animating={widget.is_animating}")
    
    # Test container with children
    container = ContainerWidget("container")
    child1 = TestWidget("child1")
    child2 = TestWidget("child2")
    
    container.add_child(child1)
    container.add_child(child2)
    
    container.alpha = 0.5
    print(f"Container alpha: {container.alpha}")
    print(f"Child1 effective alpha: {child1.effective_alpha}")
    print(f"Child2 effective alpha: {child2.effective_alpha}")
    
    print("Visibility and Transparency Controls test completed successfully!") 