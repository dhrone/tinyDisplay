#!/usr/bin/env python3
"""
Tests for Advanced Canvas Composition

Tests the advanced canvas composition features including:
- Coordinate transformation utilities
- Clipping and overflow management
- Layout managers
- Viewport and scrolling
- Canvas nesting and hierarchical layouts
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.tinydisplay.canvas.transforms import (
    CoordinateMode, Position, CoordinateTransform, CoordinateValidator,
    create_absolute_position, create_relative_position, create_parent_relative_position
)
from src.tinydisplay.canvas.clipping import (
    ClippingMode, ClippingRegion, ClippingManager, OverflowDetector, ClippingOptimizer,
    create_clipping_region, clip_bounds_to_region
)
from src.tinydisplay.canvas.layouts import (
    LayoutDirection, Alignment, WrapMode, LayoutConstraints, LayoutMargin,
    AbsoluteLayout, FlowLayout, GridLayout, FlexLayout,
    create_absolute_layout, create_flow_layout, create_grid_layout
)
from src.tinydisplay.canvas.viewport import (
    ScrollDirection, ScrollBehavior, ScrollBarVisibility, ViewportConfig, ScrollEvent,
    Viewport, ContentVirtualizer, create_viewport, create_virtualizing_viewport
)
from src.tinydisplay.canvas.nesting import (
    CanvasRelationship, CanvasTreeNode, NestedCanvas, CanvasHierarchyManager,
    get_hierarchy_manager, create_nested_canvas, find_common_ancestor
)
from src.tinydisplay.canvas import CanvasConfig
from src.tinydisplay.widgets.base import Widget, WidgetBounds


class TestCoordinateTransforms:
    """Test coordinate transformation utilities."""
    
    def test_position_creation(self):
        """Test position creation with different modes."""
        # Absolute position
        abs_pos = create_absolute_position(100, 200)
        assert abs_pos.x == 100
        assert abs_pos.y == 200
        assert abs_pos.mode == CoordinateMode.ABSOLUTE
        
        # Relative position
        rel_pos = create_relative_position(0.5, 0.75)
        assert rel_pos.x == 0.5
        assert rel_pos.y == 0.75
        assert rel_pos.mode == CoordinateMode.RELATIVE
        
        # Parent-relative position
        parent_rel_pos = create_parent_relative_position(0.25, 0.5)
        assert parent_rel_pos.x == 0.25
        assert parent_rel_pos.y == 0.5
        assert parent_rel_pos.mode == CoordinateMode.PARENT_RELATIVE
    
    def test_position_validation(self):
        """Test position validation."""
        # Valid absolute position
        abs_pos = Position(100, 200, CoordinateMode.ABSOLUTE)
        assert abs_pos.validate()
        
        # Valid relative position
        rel_pos = Position(0.5, 0.75, CoordinateMode.RELATIVE)
        assert rel_pos.validate()
        
        # Invalid relative position (out of range)
        invalid_rel_pos = Position(1.5, -0.5, CoordinateMode.RELATIVE)
        assert not invalid_rel_pos.validate()
    
    def test_position_to_absolute(self):
        """Test position conversion to absolute coordinates."""
        canvas_bounds = WidgetBounds(10, 20, 200, 100)
        
        # Absolute position (no conversion)
        abs_pos = Position(150, 80, CoordinateMode.ABSOLUTE)
        abs_x, abs_y = abs_pos.to_absolute(canvas_bounds)
        assert abs_x == 150
        assert abs_y == 80
        
        # Relative position
        rel_pos = Position(0.5, 0.75, CoordinateMode.RELATIVE)
        abs_x, abs_y = rel_pos.to_absolute(canvas_bounds)
        assert abs_x == 110  # 10 + 0.5 * 200
        assert abs_y == 95   # 20 + 0.75 * 100
        
        # Parent-relative position
        parent_bounds = WidgetBounds(0, 0, 400, 300)
        parent_rel_pos = Position(0.25, 0.5, CoordinateMode.PARENT_RELATIVE)
        abs_x, abs_y = parent_rel_pos.to_absolute(canvas_bounds, parent_bounds)
        assert abs_x == 100  # 0 + 0.25 * 400
        assert abs_y == 150  # 0 + 0.5 * 300
    
    def test_coordinate_transform(self):
        """Test coordinate transformation between parent and child."""
        parent_bounds = WidgetBounds(0, 0, 400, 300)
        child_bounds = WidgetBounds(50, 75, 200, 150)
        
        transform = CoordinateTransform(parent_bounds, child_bounds)
        
        # Parent to child transformation
        child_x, child_y = transform.parent_to_child(100, 125)
        assert child_x == 50   # 100 - 50
        assert child_y == 50   # 125 - 75
        
        # Child to parent transformation
        parent_x, parent_y = transform.child_to_parent(50, 50)
        assert parent_x == 100  # 50 + 50
        assert parent_y == 125  # 50 + 75
        
        # Round trip should return original coordinates
        original_x, original_y = 100, 125
        child_x, child_y = transform.parent_to_child(original_x, original_y)
        back_x, back_y = transform.child_to_parent(child_x, child_y)
        assert back_x == original_x
        assert back_y == original_y
    
    def test_coordinate_validator(self):
        """Test coordinate validation utilities."""
        canvas_bounds = WidgetBounds(0, 0, 200, 100)
        
        # Valid position within bounds
        valid_pos = Position(50, 25, CoordinateMode.ABSOLUTE)
        assert CoordinateValidator.validate_position(valid_pos, canvas_bounds)
        
        # Invalid position outside bounds
        invalid_pos = Position(250, 150, CoordinateMode.ABSOLUTE)
        assert not CoordinateValidator.validate_position(invalid_pos, canvas_bounds)
        
        # Clamp position to bounds
        clamped_pos = CoordinateValidator.clamp_position_to_canvas(invalid_pos, canvas_bounds)
        assert clamped_pos.x == 199  # Clamped to right edge - 1
        assert clamped_pos.y == 99   # Clamped to bottom edge - 1


class TestClippingSystem:
    """Test clipping and overflow management."""
    
    def test_clipping_region_creation(self):
        """Test clipping region creation."""
        region = create_clipping_region(10, 20, 100, 80, ClippingMode.STRICT)
        assert region.bounds.x == 10
        assert region.bounds.y == 20
        assert region.bounds.width == 100
        assert region.bounds.height == 80
        assert region.mode == ClippingMode.STRICT
        assert region.enabled
    
    def test_clipping_region_operations(self):
        """Test clipping region operations."""
        region = ClippingRegion(WidgetBounds(10, 20, 100, 80))
        
        # Test point containment
        assert region.contains_point(50, 60)
        assert not region.contains_point(5, 15)
        assert not region.contains_point(150, 120)
        
        # Test bounds containment
        contained_bounds = WidgetBounds(20, 30, 50, 40)
        assert region.contains_bounds(contained_bounds)
        
        overlapping_bounds = WidgetBounds(5, 15, 50, 40)
        assert not region.contains_bounds(overlapping_bounds)
        
        # Test bounds clipping
        clipped = region.clip_bounds(overlapping_bounds)
        assert clipped.x == 10  # Clipped to region left
        assert clipped.y == 20  # Clipped to region top
    
    def test_clipping_manager(self):
        """Test clipping manager functionality."""
        manager = ClippingManager()
        
        # Initially no clipping
        assert manager.get_active_clipping_bounds() is None
        
        # Add clipping region
        region1 = ClippingRegion(WidgetBounds(10, 20, 100, 80))
        manager.push_clipping_region(region1)
        
        active_bounds = manager.get_active_clipping_bounds()
        assert active_bounds is not None
        assert active_bounds.x == 10
        assert active_bounds.y == 20
        
        # Test widget visibility
        visible_widget = WidgetBounds(50, 60, 20, 15)
        assert manager.is_widget_visible(visible_widget)
        assert manager.is_widget_fully_visible(visible_widget)
        
        invisible_widget = WidgetBounds(200, 200, 20, 15)
        assert not manager.is_widget_visible(invisible_widget)
        
        # Add nested clipping region
        region2 = ClippingRegion(WidgetBounds(20, 30, 50, 40))
        manager.push_clipping_region(region2)
        
        # Active region should be intersection
        active_bounds = manager.get_active_clipping_bounds()
        assert active_bounds.x == 20
        assert active_bounds.y == 30
        assert active_bounds.width == 50
        assert active_bounds.height == 40
        
        # Remove clipping region
        removed = manager.pop_clipping_region()
        assert removed == region2
        
        # Should revert to previous region
        active_bounds = manager.get_active_clipping_bounds()
        assert active_bounds.x == 10
        assert active_bounds.y == 20
    
    def test_overflow_detector(self):
        """Test overflow detection."""
        detector = OverflowDetector()
        container_bounds = WidgetBounds(10, 20, 100, 80)
        
        # Widget within bounds
        contained_widget = WidgetBounds(20, 30, 50, 40)
        overflow = detector.detect_overflow(contained_widget, container_bounds)
        assert not overflow['any']
        assert not overflow['left']
        assert not overflow['right']
        assert not overflow['top']
        assert not overflow['bottom']
        
        # Widget overflowing right and bottom
        overflowing_widget = WidgetBounds(80, 70, 60, 50)
        overflow = detector.detect_overflow(overflowing_widget, container_bounds)
        assert overflow['any']
        assert not overflow['left']
        assert overflow['right']
        assert not overflow['top']
        assert overflow['bottom']
        
        # Calculate overflow amounts
        amounts = detector.calculate_overflow_amount(overflowing_widget, container_bounds)
        assert amounts['right'] == 30  # 140 - 110
        assert amounts['bottom'] == 20  # 120 - 100
        
        # Test overflow strategy suggestion
        strategy = detector.suggest_overflow_strategy(overflowing_widget, container_bounds)
        assert strategy in ['clip', 'scroll', 'resize']
    
    def test_clipping_optimizer(self):
        """Test clipping optimization."""
        optimizer = ClippingOptimizer()
        
        widget_bounds = WidgetBounds(10, 20, 50, 40)
        clip_bounds = WidgetBounds(0, 0, 100, 80)
        
        # First call should miss cache
        result1 = optimizer.optimized_clip(widget_bounds, clip_bounds)
        stats = optimizer.get_cache_stats()
        assert stats['cache_misses'] == 1
        assert stats['cache_hits'] == 0
        
        # Second call should hit cache
        result2 = optimizer.optimized_clip(widget_bounds, clip_bounds)
        stats = optimizer.get_cache_stats()
        assert stats['cache_hits'] == 1
        assert result1 == result2


class TestLayoutManagers:
    """Test layout manager functionality."""
    
    def create_mock_widgets(self, count: int, size: tuple = (50, 30)) -> list:
        """Create mock widgets for testing."""
        widgets = []
        for i in range(count):
            widget = Mock(spec=Widget)
            widget.size = size
            widget.position = (0, 0)
            widgets.append(widget)
        return widgets
    
    def test_layout_constraints(self):
        """Test layout constraints."""
        constraints = LayoutConstraints(
            min_width=50,
            max_width=200,
            min_height=30,
            max_height=100,
            aspect_ratio=2.0
        )
        
        # Apply constraints to size
        constrained_width, constrained_height = constraints.apply_to_size(300, 150)
        assert constrained_width == 200  # Clamped to max_width
        assert constrained_height == 100  # Calculated from aspect ratio: 200/2.0
        
        # Test minimum constraints
        small_width, small_height = constraints.apply_to_size(20, 10)
        assert small_width == 50   # Clamped to min_width
        assert small_height == 25  # Calculated from aspect ratio: 50/2.0
    
    def test_absolute_layout(self):
        """Test absolute layout manager."""
        layout = create_absolute_layout(validate_bounds=True)
        widgets = self.create_mock_widgets(3)
        
        # Set widget positions
        widgets[0].position = (10, 20)
        widgets[1].position = (100, 50)
        widgets[2].position = (200, 80)
        
        canvas_bounds = WidgetBounds(0, 0, 300, 200)
        
        # Layout should maintain positions within bounds
        layout.layout_widgets(widgets, canvas_bounds)
        
        # Positions should be unchanged (within bounds)
        assert widgets[0].position == (10, 20)
        assert widgets[1].position == (100, 50)
        assert widgets[2].position == (200, 80)
        
        # Test preferred size calculation
        preferred_width, preferred_height = layout.get_preferred_size(widgets)
        assert preferred_width == 250  # 200 + 50 (widget width)
        assert preferred_height == 110  # 80 + 30 (widget height)
    
    def test_flow_layout(self):
        """Test flow layout manager."""
        layout = create_flow_layout(LayoutDirection.HORIZONTAL, spacing=10)
        widgets = self.create_mock_widgets(4, (60, 40))
        
        canvas_bounds = WidgetBounds(0, 0, 200, 100)
        
        # Layout widgets
        layout.layout_widgets(widgets, canvas_bounds)
        
        # Check horizontal flow positioning
        assert widgets[0].position == (0, 0)
        assert widgets[1].position == (70, 0)   # 60 + 10 spacing
        assert widgets[2].position == (140, 0)  # 70 + 60 + 10
        # Fourth widget should wrap to next line
        assert widgets[3].position == (0, 45)   # New line: 40 + 5 line_spacing
        
        # Test preferred size
        preferred_width, preferred_height = layout.get_preferred_size(widgets)
        assert preferred_width == 270  # 4 * 60 + 3 * 10 spacing
        assert preferred_height == 40
    
    def test_grid_layout(self):
        """Test grid layout manager."""
        layout = create_grid_layout(2, 3, spacing=(5, 5))  # 2 rows, 3 columns
        widgets = self.create_mock_widgets(6, (40, 30))
        
        canvas_bounds = WidgetBounds(0, 0, 200, 100)
        
        # Layout widgets
        layout.layout_widgets(widgets, canvas_bounds)
        
        # Calculate expected cell size
        available_width = 200 - 2 * 5  # Subtract horizontal spacing
        available_height = 100 - 1 * 5  # Subtract vertical spacing
        cell_width = available_width // 3  # 3 columns
        cell_height = available_height // 2  # 2 rows
        
        # Check grid positioning (widgets centered in cells)
        expected_positions = [
            (0, 0),                                    # Row 0, Col 0
            (cell_width + 5, 0),                      # Row 0, Col 1
            (2 * (cell_width + 5), 0),                # Row 0, Col 2
            (0, cell_height + 5),                     # Row 1, Col 0
            (cell_width + 5, cell_height + 5),        # Row 1, Col 1
            (2 * (cell_width + 5), cell_height + 5)   # Row 1, Col 2
        ]
        
        for i, widget in enumerate(widgets):
            # Positions should be at cell origins (START alignment)
            assert widget.position[0] >= expected_positions[i][0] - 5
            assert widget.position[1] >= expected_positions[i][1] - 5
    
    def test_flex_layout(self):
        """Test flexible layout manager."""
        layout = FlexLayout(
            direction=LayoutDirection.HORIZONTAL,
            justify_content=Alignment.START,
            align_items=Alignment.STRETCH,
            gap=10
        )
        
        widgets = self.create_mock_widgets(3, (50, 30))
        
        # Add layout constraints to widgets
        widgets[0].layout_constraints = LayoutConstraints(flex_grow=1.0)
        widgets[1].layout_constraints = LayoutConstraints(flex_grow=2.0)
        widgets[2].layout_constraints = LayoutConstraints(flex_grow=1.0)
        
        canvas_bounds = WidgetBounds(0, 0, 300, 100)
        
        # Layout widgets
        layout.layout_widgets(widgets, canvas_bounds)
        
        # Check that widgets are positioned horizontally with gaps
        assert widgets[0].position[0] == 0
        assert widgets[1].position[0] > widgets[0].position[0] + 50
        assert widgets[2].position[0] > widgets[1].position[0] + 50
        
        # Check that widgets are stretched vertically (align_items=STRETCH)
        for widget in widgets:
            assert widget.size[1] == 100  # Stretched to canvas height


class TestViewportSystem:
    """Test viewport and scrolling functionality."""
    
    def test_viewport_creation(self):
        """Test viewport creation and basic properties."""
        viewport = create_viewport(200, 150, 400, 300, smooth_scrolling=True)
        
        assert viewport.config.width == 200
        assert viewport.config.height == 150
        assert viewport.config.content_width == 400
        assert viewport.config.content_height == 300
        assert viewport.config.smooth_scrolling
        
        # Initial scroll position
        assert viewport.scroll_x == 0
        assert viewport.scroll_y == 0
        
        # Scrolling capabilities
        assert viewport.can_scroll_horizontal
        assert viewport.can_scroll_vertical
    
    def test_viewport_scrolling(self):
        """Test viewport scrolling operations."""
        viewport = create_viewport(200, 150, 400, 300, smooth_scrolling=False)
        
        # Scroll to specific position
        viewport.scroll_to(50, 75)
        assert viewport.scroll_x == 50
        assert viewport.scroll_y == 75
        
        # Scroll by relative amount
        viewport.scroll_by(25, 25)
        assert viewport.scroll_x == 75
        assert viewport.scroll_y == 100
        
        # Test scroll bounds clamping
        viewport.scroll_to(500, 400)  # Beyond content bounds
        assert viewport.scroll_x == 200  # 400 - 200 (viewport width)
        assert viewport.scroll_y == 150  # 300 - 150 (viewport height)
        
        # Test negative scroll clamping
        viewport.scroll_to(-50, -25)
        assert viewport.scroll_x == 0
        assert viewport.scroll_y == 0
    
    def test_viewport_coordinate_conversion(self):
        """Test viewport coordinate conversion."""
        viewport = create_viewport(200, 150, 400, 300, smooth_scrolling=False)
        viewport.scroll_to(50, 75)
        
        # Viewport to content coordinates
        content_x, content_y = viewport.viewport_to_content_coords(100, 50)
        assert content_x == 150  # 100 + 50 (scroll_x)
        assert content_y == 125  # 50 + 75 (scroll_y)
        
        # Content to viewport coordinates
        viewport_x, viewport_y = viewport.content_to_viewport_coords(150, 125)
        assert viewport_x == 100  # 150 - 50 (scroll_x)
        assert viewport_y == 50   # 125 - 75 (scroll_y)
    
    def test_viewport_scroll_into_view(self):
        """Test scroll into view functionality."""
        viewport = create_viewport(200, 150, 400, 300, smooth_scrolling=False)
        
        # Scroll to make bounds visible
        target_bounds = WidgetBounds(250, 200, 50, 40)
        viewport.scroll_into_view(target_bounds)
        
        # Should scroll to show the target bounds
        visible_bounds = viewport.visible_bounds
        assert target_bounds.right <= visible_bounds.right
        assert target_bounds.bottom <= visible_bounds.bottom
    
    def test_viewport_events(self):
        """Test viewport event handling."""
        viewport = create_viewport(200, 150, 400, 300, smooth_scrolling=False)
        
        # Add scroll listener
        events = []
        def scroll_listener(event):
            events.append(event)
        
        viewport.add_scroll_listener(scroll_listener)
        
        # Trigger scroll
        viewport.scroll_by(25, 50)
        
        # Check event was fired
        assert len(events) == 1
        event = events[0]
        assert event.delta_x == 25
        assert event.delta_y == 50
        assert event.scroll_x == 25
        assert event.scroll_y == 50
    
    def test_content_virtualizer(self):
        """Test content virtualization."""
        items = [f"Item {i}" for i in range(1000)]  # Large list
        
        # Create viewport with non-smooth scrolling for predictable behavior
        content_height = len(items) * 25
        viewport = create_viewport(200, 150, 200, content_height, smooth_scrolling=False)
        virtualizer = ContentVirtualizer(viewport, item_height=25)
        virtualizer.set_items(items)
        
        # Check content height was set correctly
        assert viewport.config.content_height == 25000  # 1000 * 25
        
        # Get visible items (should be much less than total)
        visible_items = virtualizer.get_visible_items()
        assert len(visible_items) <= 10  # Should only show ~6-7 items in 150px viewport
        
        # Scroll to specific item
        virtualizer.scroll_to_item(500)
        
        # Check that viewport scrolled to show item 500
        expected_y = 500 * 25
        assert viewport.scroll_y >= expected_y - 150  # Within viewport range
        assert viewport.scroll_y <= expected_y


class TestCanvasNesting:
    """Test canvas nesting and hierarchy."""
    
    def test_nested_canvas_creation(self):
        """Test nested canvas creation and hierarchy."""
        config = CanvasConfig(width=400, height=300)
        
        # Create root canvas
        root_canvas = create_nested_canvas(config, canvas_id="root")
        assert root_canvas.is_root
        assert root_canvas.is_leaf  # Initially has no children, so it's a leaf
        assert root_canvas.depth == 0
        
        # Create child canvas
        child_config = CanvasConfig(width=200, height=150)
        child_canvas = create_nested_canvas(child_config, parent=root_canvas, canvas_id="child")
        
        assert not child_canvas.is_root
        assert child_canvas.is_leaf
        assert child_canvas.depth == 1
        assert child_canvas.parent == root_canvas
        assert child_canvas in root_canvas.children
        
        # Now root canvas should not be a leaf
        assert not root_canvas.is_leaf
    
    def test_canvas_hierarchy_operations(self):
        """Test canvas hierarchy operations."""
        config = CanvasConfig(width=400, height=300)
        
        # Create hierarchy: root -> child1, child2 -> grandchild
        root = create_nested_canvas(config, canvas_id="root")
        child1 = create_nested_canvas(config, parent=root, canvas_id="child1")
        child2 = create_nested_canvas(config, parent=root, canvas_id="child2")
        grandchild = create_nested_canvas(config, parent=child1, canvas_id="grandchild")
        
        # Test relationships
        assert root.get_relationship(child1) == CanvasRelationship.CHILD
        assert child1.get_relationship(root) == CanvasRelationship.PARENT
        assert child1.get_relationship(child2) == CanvasRelationship.SIBLING
        assert root.get_relationship(grandchild) == CanvasRelationship.DESCENDANT
        assert grandchild.get_relationship(root) == CanvasRelationship.ANCESTOR
        
        # Test hierarchy traversal
        ancestors = grandchild.get_ancestors()
        assert len(ancestors) == 2
        assert ancestors[0] == child1  # Immediate parent
        assert ancestors[1] == root    # Root
        
        descendants = root.get_descendants()
        assert len(descendants) == 3
        assert child1 in descendants
        assert child2 in descendants
        assert grandchild in descendants
        
        siblings = child1.get_siblings()
        assert len(siblings) == 1
        assert child2 in siblings
    
    def test_coordinate_transformation_hierarchy(self):
        """Test coordinate transformation in canvas hierarchy."""
        root_config = CanvasConfig(width=400, height=300)
        root = create_nested_canvas(root_config, canvas_id="root")
        root.position = (0, 0)
        root.size = (400, 300)
        
        child_config = CanvasConfig(width=200, height=150)
        child = create_nested_canvas(child_config, parent=root, canvas_id="child")
        child.position = (50, 75)
        child.size = (200, 150)
        
        # Test coordinate transformation
        child_x, child_y = child.transform_from_parent(100, 125)
        assert child_x == 50   # 100 - 50 (child offset)
        assert child_y == 50   # 125 - 75 (child offset)
        
        parent_x, parent_y = child.transform_to_parent(50, 50)
        assert parent_x == 100  # 50 + 50 (child offset)
        assert parent_y == 125  # 50 + 75 (child offset)
        
        # Test world coordinate transformation
        world_x, world_y = child.transform_to_world(25, 25)
        assert world_x == 75   # 25 + 50 (child offset)
        assert world_y == 100  # 25 + 75 (child offset)
        
        local_x, local_y = child.transform_from_world(75, 100)
        assert local_x == 25   # 75 - 50 (child offset)
        assert local_y == 25   # 100 - 75 (child offset)
    
    def test_canvas_hierarchy_manager(self):
        """Test canvas hierarchy manager."""
        manager = get_hierarchy_manager()
        
        # Create test hierarchy
        config = CanvasConfig(width=200, height=150)
        root1 = create_nested_canvas(config, canvas_id="root1")
        root2 = create_nested_canvas(config, canvas_id="root2")
        child = create_nested_canvas(config, parent=root1, canvas_id="child")
        
        # Test manager operations
        assert manager.get_canvas_by_id("root1") == root1
        assert manager.get_canvas_by_id("child") == child
        assert manager.get_canvas_by_id("nonexistent") is None
        
        root_canvases = manager.get_root_canvases()
        assert root1 in root_canvases
        assert root2 in root_canvases
        assert child not in root_canvases
        
        # Test hierarchy statistics
        stats = manager.get_hierarchy_stats()
        assert stats['total_canvases'] >= 3
        assert stats['root_canvases'] >= 2
        assert stats['max_depth'] >= 1
    
    def test_find_common_ancestor(self):
        """Test finding common ancestor of canvases."""
        config = CanvasConfig(width=200, height=150)
        
        # Create hierarchy: root -> child1, child2 -> grandchild1, grandchild2
        root = create_nested_canvas(config, canvas_id="root")
        child1 = create_nested_canvas(config, parent=root, canvas_id="child1")
        child2 = create_nested_canvas(config, parent=root, canvas_id="child2")
        grandchild1 = create_nested_canvas(config, parent=child1, canvas_id="grandchild1")
        grandchild2 = create_nested_canvas(config, parent=child2, canvas_id="grandchild2")
        
        # Test common ancestor finding
        common = find_common_ancestor(grandchild1, grandchild2)
        assert common == root
        
        # When one canvas is an ancestor of another, the ancestor should be returned
        common = find_common_ancestor(child1, grandchild1)
        assert common == child1
        
        common = find_common_ancestor(child1, child2)
        assert common == root


class TestCanvasCompositionIntegration:
    """Integration tests for canvas composition features."""
    
    def test_layout_with_clipping(self):
        """Test layout managers with clipping."""
        # Create layout with clipping
        layout = FlowLayout(LayoutDirection.HORIZONTAL, spacing=10)
        clipping_manager = ClippingManager()
        
        # Add clipping region
        clip_region = create_clipping_region(0, 0, 150, 100)
        clipping_manager.push_clipping_region(clip_region)
        
        # Create widgets that would overflow
        widgets = []
        for i in range(5):
            widget = Mock(spec=Widget)
            widget.size = (40, 30)
            widget.position = (0, 0)
            widgets.append(widget)
        
        canvas_bounds = WidgetBounds(0, 0, 300, 100)
        
        # Layout widgets
        layout.layout_widgets(widgets, canvas_bounds)
        
        # Check which widgets are visible after clipping
        visible_widgets = []
        for widget in widgets:
            widget_bounds = WidgetBounds(widget.position[0], widget.position[1], 
                                       widget.size[0], widget.size[1])
            if clipping_manager.is_widget_visible(widget_bounds):
                visible_widgets.append(widget)
        
        # Should have fewer visible widgets due to clipping
        assert len(visible_widgets) < len(widgets)
    
    def test_nested_canvas_with_viewport(self):
        """Test nested canvas with viewport scrolling."""
        # Create parent canvas with viewport
        parent_config = CanvasConfig(width=300, height=200)
        parent_canvas = create_nested_canvas(parent_config, canvas_id="parent")
        
        viewport = create_viewport(300, 200, 600, 400, smooth_scrolling=False)
        
        # Create child canvas within scrollable area
        child_config = CanvasConfig(width=200, height=150)
        child_canvas = create_nested_canvas(child_config, parent=parent_canvas, canvas_id="child")
        child_canvas.position = (250, 250)  # Positioned in scrollable area
        child_canvas.size = (200, 150)
        
        # Initially child might not be visible
        child_world_bounds = child_canvas.world_bounds
        visible_bounds = viewport.visible_bounds
        
        # Scroll to make child visible
        viewport.scroll_into_view(child_world_bounds)
        
        # Check that viewport scrolled to show child
        new_visible_bounds = viewport.visible_bounds
        assert new_visible_bounds.intersects(child_world_bounds)
    
    def test_performance_with_many_widgets(self):
        """Test performance with many widgets and complex layouts."""
        # Create many widgets
        widget_count = 100
        widgets = []
        for i in range(widget_count):
            widget = Mock(spec=Widget)
            widget.size = (20, 20)
            widget.position = (0, 0)
            widgets.append(widget)
        
        # Test grid layout performance
        layout = GridLayout(10, 10, spacing=(2, 2))
        canvas_bounds = WidgetBounds(0, 0, 500, 500)
        
        start_time = time.time()
        layout.layout_widgets(widgets, canvas_bounds)
        layout_time = time.time() - start_time
        
        # Should complete quickly (under 100ms for 100 widgets)
        assert layout_time < 0.1
        
        # Test clipping performance with many widgets
        clipping_manager = ClippingManager()
        clip_region = create_clipping_region(0, 0, 250, 250)
        clipping_manager.push_clipping_region(clip_region)
        
        start_time = time.time()
        visible_count = 0
        for widget in widgets:
            widget_bounds = WidgetBounds(widget.position[0], widget.position[1],
                                       widget.size[0], widget.size[1])
            if clipping_manager.is_widget_visible(widget_bounds):
                visible_count += 1
        clipping_time = time.time() - start_time
        
        # Should complete quickly
        assert clipping_time < 0.05
        assert visible_count < widget_count  # Some should be clipped


if __name__ == '__main__':
    pytest.main([__file__]) 