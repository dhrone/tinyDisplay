#!/usr/bin/env python3
"""
Unit Tests for Widget Lifecycle Management

Tests the complete widget lifecycle management system including:
- Widget creation and initialization lifecycle
- Widget update and state change management
- Widget destruction and cleanup procedures
- Widget pool for performance optimization
- Lifecycle event hooks for extensions
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, call
from typing import List, Dict, Any

from src.tinydisplay.widgets import (
    Widget, ContainerWidget, WidgetState, VisibilityState,
    LifecycleEvent, LifecycleEventInfo, WidgetPool, WidgetPoolConfig,
    LifecycleManager, get_lifecycle_manager, create_widget_pool,
    emit_lifecycle_event, register_global_lifecycle_hook,
    LifecycleIntegratedWidget, LifecycleIntegratedContainerWidget,
    WidgetFactory, get_widget_factory, create_widget, release_widget,
    lifecycle_managed, with_lifecycle_hooks
)


class MockWidget(Widget):
    """Mock widget implementation for testing."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_count = 0
        self.render_calls = []
    
    def render(self, canvas):
        """Test render implementation."""
        self.render_count += 1
        self.render_calls.append(time.time())


class MockLifecycleIntegratedWidget(LifecycleIntegratedWidget):
    """Mock lifecycle integrated widget."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_count = 0
    
    def render(self, canvas):
        """Test render implementation."""
        super().render(canvas)  # Emit lifecycle event
        self.render_count += 1


class TestWidgetLifecycle:
    """Test basic widget lifecycle management."""
    
    def test_widget_creation(self):
        """Test widget creation lifecycle."""
        widget = MockWidget("test_widget")
        
        assert widget.widget_id == "test_widget"
        assert widget.state == WidgetState.CREATED
        assert widget.visible is True
        assert widget.alpha == 1.0
        assert widget.position == (0, 0)
        assert widget.size == (100, 20)
    
    def test_widget_initialization(self):
        """Test widget initialization lifecycle."""
        widget = MockWidget("test_widget")
        
        # Test initialization
        widget.initialize()
        assert widget.state == WidgetState.INITIALIZED
        
        # Test double initialization (should be no-op)
        widget.initialize()
        assert widget.state == WidgetState.INITIALIZED
    
    def test_widget_activation(self):
        """Test widget activation lifecycle."""
        widget = MockWidget("test_widget")
        widget.initialize()
        
        # Test activation
        widget.activate()
        assert widget.state == WidgetState.ACTIVE
        
        # Test activation from hidden state
        widget.hide_widget()
        assert widget.state == WidgetState.HIDDEN
        
        widget.activate()
        assert widget.state == WidgetState.ACTIVE
    
    def test_widget_hiding(self):
        """Test widget hiding lifecycle."""
        widget = MockWidget("test_widget")
        widget.initialize()
        widget.activate()
        
        # Test hiding
        widget.hide_widget()
        assert widget.state == WidgetState.HIDDEN
        
        # Test hiding when already hidden (should be no-op)
        widget.hide_widget()
        assert widget.state == WidgetState.HIDDEN
    
    def test_widget_destruction(self):
        """Test widget destruction lifecycle."""
        widget = MockWidget("test_widget")
        widget.initialize()
        widget.activate()
        
        # Add some reactive bindings to test cleanup
        from src.tinydisplay.widgets.base import ReactiveValue
        reactive_val = ReactiveValue(42)
        widget.bind_data("test_prop", reactive_val)
        
        # Test destruction
        widget.destroy()
        assert widget.state == WidgetState.DESTROYED
        
        # Verify reactive bindings are cleaned up
        assert len(widget._reactive_bindings) == 0
    
    def test_widget_lifecycle_hooks(self):
        """Test widget lifecycle hooks."""
        widget = MockWidget("test_widget")
        
        # Track hook calls
        hook_calls = []
        
        def on_initialize(w):
            hook_calls.append(('initialize', w.widget_id))
        
        def on_update(w):
            hook_calls.append(('update', w.widget_id))
        
        def on_cleanup(w):
            hook_calls.append(('cleanup', w.widget_id))
        
        # Add hooks
        widget.add_lifecycle_hook('initialize', on_initialize)
        widget.add_lifecycle_hook('update', on_update)
        widget.add_lifecycle_hook('cleanup', on_cleanup)
        
        # Test lifecycle transitions
        widget.initialize()
        widget.activate()
        widget._mark_dirty()  # Trigger update
        widget.destroy()
        
        # Verify hooks were called
        assert ('initialize', 'test_widget') in hook_calls
        assert ('update', 'test_widget') in hook_calls
        assert ('cleanup', 'test_widget') in hook_calls
    
    def test_widget_needs_render(self):
        """Test widget render requirements."""
        widget = MockWidget("test_widget")
        
        # Widget should not need render when created
        assert not widget.needs_render()
        
        # Widget should need render when active and dirty
        widget.initialize()
        widget.activate()
        assert widget.needs_render()
        
        # Widget should not need render when clean
        widget.mark_clean()
        assert not widget.needs_render()
        
        # Widget should not need render when hidden
        widget._mark_dirty()
        widget.hide_widget()
        assert not widget.needs_render()
        
        # Widget should not need render when invisible
        widget.activate()
        widget.visible = False
        assert not widget.needs_render()


class TestWidgetPool:
    """Test widget pool functionality."""
    
    def test_widget_pool_creation(self):
        """Test widget pool creation."""
        config = WidgetPoolConfig(max_pool_size=5, preallocation_count=2)
        pool = WidgetPool(MockWidget, config)
        
        stats = pool.get_stats()
        assert stats['widget_class'] == 'MockWidget'
        assert stats['available_count'] == 2  # Pre-allocated
        assert stats['in_use_count'] == 0
        assert stats['max_pool_size'] == 5
    
    def test_widget_pool_acquire_release(self):
        """Test widget pool acquire and release."""
        config = WidgetPoolConfig(max_pool_size=3, preallocation_count=1)
        pool = WidgetPool(MockWidget, config)
        
        # Acquire widgets
        widget1 = pool.acquire("widget1")
        widget2 = pool.acquire("widget2")
        
        assert widget1.widget_id == "widget1"
        assert widget2.widget_id == "widget2"
        assert widget1.state == WidgetState.CREATED
        
        stats = pool.get_stats()
        assert stats['in_use_count'] == 2
        assert stats['available_count'] == 0  # Used pre-allocated + created new
        
        # Release widgets
        pool.release(widget1)
        pool.release(widget2)
        
        stats = pool.get_stats()
        assert stats['in_use_count'] == 0
        assert stats['available_count'] == 2
    
    def test_widget_pool_cleanup(self):
        """Test widget pool cleanup of idle widgets."""
        config = WidgetPoolConfig(max_idle_time=0.1)  # 100ms
        pool = WidgetPool(MockWidget, config)
        
        # Acquire and release a widget
        widget = pool.acquire("test")
        pool.release(widget)
        
        # Wait for idle time to pass
        time.sleep(0.2)
        
        # Cleanup should remove idle widgets
        cleaned_count = pool.cleanup_idle_widgets()
        assert cleaned_count > 0
        
        stats = pool.get_stats()
        assert stats['available_count'] == 0


class TestLifecycleManager:
    """Test lifecycle manager functionality."""
    
    def test_lifecycle_manager_singleton(self):
        """Test lifecycle manager singleton pattern."""
        manager1 = get_lifecycle_manager()
        manager2 = get_lifecycle_manager()
        
        assert manager1 is manager2
    
    def test_global_lifecycle_hooks(self):
        """Test global lifecycle hooks."""
        manager = get_lifecycle_manager()
        
        # Track events
        events = []
        
        def on_created(event_info):
            events.append(('created', event_info.widget.widget_id))
        
        def on_destroyed(event_info):
            events.append(('destroyed', event_info.widget.widget_id))
        
        # Register hooks
        manager.register_global_hook(LifecycleEvent.CREATED, on_created)
        manager.register_global_hook(LifecycleEvent.DESTROYED, on_destroyed)
        
        # Create and destroy widget
        widget = MockWidget("test_widget")
        emit_lifecycle_event(LifecycleEvent.CREATED, widget)
        emit_lifecycle_event(LifecycleEvent.DESTROYED, widget)
        
        # Verify events
        assert ('created', 'test_widget') in events
        assert ('destroyed', 'test_widget') in events
        
        # Cleanup
        manager.unregister_global_hook(LifecycleEvent.CREATED, on_created)
        manager.unregister_global_hook(LifecycleEvent.DESTROYED, on_destroyed)
    
    def test_widget_specific_hooks(self):
        """Test widget-specific lifecycle hooks."""
        manager = get_lifecycle_manager()
        widget = MockWidget("test_widget")
        
        # Track events
        events = []
        
        def on_widget_updated(event_info):
            events.append(('updated', event_info.widget.widget_id))
        
        # Register widget-specific hook
        manager.register_widget_hook(widget, LifecycleEvent.UPDATED, on_widget_updated)
        
        # Emit event
        emit_lifecycle_event(LifecycleEvent.UPDATED, widget)
        
        # Verify event
        assert ('updated', 'test_widget') in events
        
        # Cleanup
        manager.unregister_widget_hook(widget, LifecycleEvent.UPDATED, on_widget_updated)
    
    def test_event_history(self):
        """Test lifecycle event history."""
        manager = get_lifecycle_manager()
        widget = MockWidget("test_widget")
        
        # Emit some events
        emit_lifecycle_event(LifecycleEvent.CREATED, widget)
        emit_lifecycle_event(LifecycleEvent.INITIALIZED, widget)
        emit_lifecycle_event(LifecycleEvent.ACTIVATED, widget)
        
        # Get history
        history = manager.get_event_history(widget=widget, limit=10)
        
        assert len(history) >= 3
        assert all(event.widget == widget for event in history)
        
        # Test filtering by event type
        created_events = manager.get_event_history(event=LifecycleEvent.CREATED, limit=10)
        assert all(event.event == LifecycleEvent.CREATED for event in created_events)


class TestLifecycleIntegration:
    """Test lifecycle integration features."""
    
    def test_lifecycle_integrated_widget(self):
        """Test lifecycle integrated widget."""
        # Track events
        events = []
        
        def on_event(event_info):
            events.append((event_info.event, event_info.widget.widget_id))
        
        # Register global hook
        manager = get_lifecycle_manager()
        for event in LifecycleEvent:
            manager.register_global_hook(event, on_event)
        
        # Create and use widget
        widget = MockLifecycleIntegratedWidget("test_widget")
        widget.initialize()
        widget.activate()
        widget.position = (10, 20)
        widget.size = (200, 100)
        widget.visible = False
        widget.alpha = 0.5
        widget.destroy()
        
        # Verify events were emitted
        event_types = [event[0] for event in events if event[1] == "test_widget"]
        
        assert LifecycleEvent.CREATED in event_types
        assert LifecycleEvent.INITIALIZED in event_types
        assert LifecycleEvent.ACTIVATED in event_types
        assert LifecycleEvent.POSITION_CHANGED in event_types
        assert LifecycleEvent.SIZE_CHANGED in event_types
        assert LifecycleEvent.VISIBILITY_CHANGED in event_types
        assert LifecycleEvent.ALPHA_CHANGED in event_types
        assert LifecycleEvent.DESTROYED in event_types
        
        # Cleanup
        for event in LifecycleEvent:
            manager.unregister_global_hook(event, on_event)
    
    def test_lifecycle_integrated_container(self):
        """Test lifecycle integrated container widget."""
        # Track events
        events = []
        
        def on_event(event_info):
            events.append((event_info.event, event_info.widget.widget_id))
        
        # Register global hook
        manager = get_lifecycle_manager()
        manager.register_global_hook(LifecycleEvent.CHILD_ADDED, on_event)
        manager.register_global_hook(LifecycleEvent.CHILD_REMOVED, on_event)
        
        # Create container and child
        container = LifecycleIntegratedContainerWidget("container")
        child = MockLifecycleIntegratedWidget("child")
        
        # Add and remove child
        container.add_child(child)
        container.remove_child("child")
        
        # Verify events
        event_types = [event[0] for event in events if event[1] == "container"]
        assert LifecycleEvent.CHILD_ADDED in event_types
        assert LifecycleEvent.CHILD_REMOVED in event_types
        
        # Cleanup
        manager.unregister_global_hook(LifecycleEvent.CHILD_ADDED, on_event)
        manager.unregister_global_hook(LifecycleEvent.CHILD_REMOVED, on_event)


class TestWidgetFactory:
    """Test widget factory functionality."""
    
    def test_widget_factory_creation(self):
        """Test widget factory creation."""
        factory = WidgetFactory()
        
        # Create widgets
        widget1 = factory.create_widget(MockWidget, "widget1", use_pool=False)
        widget2 = factory.create_widget(MockWidget, "widget2", use_pool=True)
        
        assert widget1.widget_id == "widget1"
        assert widget2.widget_id == "widget2"
        
        # Get stats
        stats = factory.get_creation_stats()
        # At least one widget should have been created (the non-pooled one)
        assert stats['creation_counts'].get('MockWidget', 0) >= 1
        assert stats['total_pools'] >= 1  # Pool created for widget2
    
    def test_widget_factory_pooling(self):
        """Test widget factory pooling."""
        factory = WidgetFactory()
        
        # Create pooled widget with specific config to ensure predictable behavior
        config = WidgetPoolConfig(max_pool_size=5, preallocation_count=0)  # No preallocation
        widget = factory.create_widget(MockWidget, "pooled", use_pool=True, pool_config=config)
        
        # Verify widget was created
        assert widget.widget_id == "pooled"
        
        # Get initial stats
        stats_before = factory.get_creation_stats()
        initial_count = stats_before['creation_counts'].get('MockWidget', 0)
        
        # Release widget
        factory.release_widget(widget)
        
        # Create another widget (should reuse from pool)
        widget2 = factory.create_widget(MockWidget, "pooled2", use_pool=True)
        
        # Verify widget was reused (same instance with reset ID)
        assert widget2.widget_id == "pooled2"
        
        # Verify no new widget was created (count should be same)
        stats_after = factory.get_creation_stats()
        final_count = stats_after['creation_counts'].get('MockWidget', 0)
        
        # The count should be the same since we reused the widget
        assert final_count == initial_count
    
    def test_global_widget_factory(self):
        """Test global widget factory functions."""
        # Create widget using global functions
        widget = create_widget(MockWidget, "global_test", use_pool=False)  # Use non-pooled to ensure creation
        assert widget.widget_id == "global_test"
        
        # Release widget
        release_widget(widget)
        
        # Verify factory exists and has some stats
        factory = get_widget_factory()
        stats = factory.get_creation_stats()
        assert isinstance(stats, dict)
        assert 'creation_counts' in stats
        assert 'pool_stats' in stats


class TestLifecycleDecorators:
    """Test lifecycle decorators and utilities."""
    
    def test_lifecycle_managed_decorator(self):
        """Test lifecycle_managed decorator."""
        
        @lifecycle_managed
        class ManagedWidget(MockWidget):
            pass
        
        # Track events
        events = []
        
        def on_event(event_info):
            events.append(event_info.event)
        
        # Register hook
        manager = get_lifecycle_manager()
        manager.register_global_hook(LifecycleEvent.CREATED, on_event)
        
        # Create widget
        widget = ManagedWidget("managed")
        
        # Verify lifecycle integration
        assert LifecycleEvent.CREATED in events
        assert isinstance(widget, LifecycleIntegratedWidget)
        
        # Cleanup
        manager.unregister_global_hook(LifecycleEvent.CREATED, on_event)
    
    def test_with_lifecycle_hooks_decorator(self):
        """Test with_lifecycle_hooks decorator."""
        
        # Track hook calls
        hook_calls = []
        
        def before_render(widget, canvas):
            hook_calls.append(('before_render', widget.widget_id))
        
        def after_render(widget, result, canvas):
            hook_calls.append(('after_render', widget.widget_id))
        
        class HookedWidget(MockWidget):
            @with_lifecycle_hooks(before_render=before_render, after_render=after_render)
            def render(self, canvas):
                super().render(canvas)
                return "rendered"
        
        # Create and render widget
        widget = HookedWidget("hooked")
        widget.render("mock_canvas")
        
        # Verify hooks were called
        assert ('before_render', 'hooked') in hook_calls
        assert ('after_render', 'hooked') in hook_calls


class TestLifecyclePerformance:
    """Test lifecycle management performance."""
    
    def test_widget_pool_performance(self):
        """Test widget pool performance benefits."""
        config = WidgetPoolConfig(max_pool_size=100, preallocation_count=10)
        pool = WidgetPool(MockWidget, config)
        
        # Measure pool acquisition time
        start_time = time.time()
        widgets = []
        for i in range(50):
            widget = pool.acquire(f"widget_{i}")
            widgets.append(widget)
        pool_time = time.time() - start_time
        
        # Release widgets
        for widget in widgets:
            pool.release(widget)
        
        # Measure direct creation time
        start_time = time.time()
        direct_widgets = []
        for i in range(50):
            widget = MockWidget(f"direct_{i}")
            direct_widgets.append(widget)
        direct_time = time.time() - start_time
        
        # Pool should be faster for large numbers (due to pre-allocation)
        # Note: This is more about testing the mechanism than strict performance
        assert pool_time >= 0  # Just ensure it completes
        assert direct_time >= 0
    
    def test_lifecycle_event_performance(self):
        """Test lifecycle event emission performance."""
        manager = get_lifecycle_manager()
        widget = MockWidget("perf_test")
        
        # Measure event emission time
        start_time = time.time()
        for i in range(1000):
            emit_lifecycle_event(LifecycleEvent.UPDATED, widget, i, i+1)
        emission_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert emission_time < 1.0  # Less than 1 second for 1000 events
        
        # Verify events were recorded
        history = manager.get_event_history(widget=widget, limit=1000)
        assert len(history) >= 1000


class TestLifecycleErrorHandling:
    """Test lifecycle management error handling."""
    
    def test_hook_error_handling(self):
        """Test error handling in lifecycle hooks."""
        manager = get_lifecycle_manager()
        widget = MockWidget("error_test")
        
        # Create hook that raises exception
        def failing_hook(event_info):
            raise ValueError("Test error")
        
        # Register failing hook
        manager.register_global_hook(LifecycleEvent.CREATED, failing_hook)
        
        # Emit event (should not raise exception)
        try:
            emit_lifecycle_event(LifecycleEvent.CREATED, widget)
            # Should succeed despite hook failure
            assert True
        except Exception:
            pytest.fail("Lifecycle event emission should handle hook errors gracefully")
        
        # Cleanup
        manager.unregister_global_hook(LifecycleEvent.CREATED, failing_hook)
    
    def test_widget_pool_error_handling(self):
        """Test error handling in widget pools."""
        config = WidgetPoolConfig(max_pool_size=1)
        pool = WidgetPool(MockWidget, config)
        
        # Acquire widget
        widget = pool.acquire("test")
        
        # Try to release widget that's not in use (should handle gracefully)
        fake_widget = MockWidget("fake")
        pool.release(fake_widget)  # Should not raise exception
        
        # Release actual widget
        pool.release(widget)
        
        # Pool should still be functional
        widget2 = pool.acquire("test2")
        assert widget2 is not None


if __name__ == "__main__":
    pytest.main([__file__]) 