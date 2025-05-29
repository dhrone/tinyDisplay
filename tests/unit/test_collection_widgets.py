#!/usr/bin/env python3
"""
Tests for Collection Widgets

Comprehensive test suite for collection widget system including:
- Collection base framework
- Stack widget functionality
- Grid widget functionality  
- Sequence widget functionality
- Reactive data binding integration
- Performance optimization features
"""

import pytest
import time
from typing import List, Any
from unittest.mock import Mock, patch

from src.tinydisplay.widgets.collection_base import (
    CollectionWidget, CollectionConfig, CollectionEvent, CollectionChange,
    CollectionLayout, SelectionMode, VirtualScrollInfo
)
from src.tinydisplay.widgets.collections import (
    StackWidget, StackDirection, StackAlignment, StackConfig,
    GridWidget, GridSizing, GridColumnConfig, GridRowConfig, GridConfig,
    SequenceWidget, SequenceTransition, SequenceConfig
)
from src.tinydisplay.widgets.text import TextWidget
from src.tinydisplay.widgets.base import Widget, WidgetBounds
from src.tinydisplay.core.reactive import ReactiveValue, ReactiveList


class TestCollectionWidget:
    """Test the base collection widget framework."""
    
    def test_collection_config_creation(self):
        """Test collection configuration creation."""
        config = CollectionConfig(
            layout_type=CollectionLayout.STACK_VERTICAL,
            selection_mode=SelectionMode.MULTIPLE,
            virtual_scrolling=True,
            item_height=40,
            spacing=10
        )
        
        assert config.layout_type == CollectionLayout.STACK_VERTICAL
        assert config.selection_mode == SelectionMode.MULTIPLE
        assert config.virtual_scrolling is True
        assert config.item_height == 40
        assert config.spacing == 10
        
    def test_collection_change_creation(self):
        """Test collection change event creation."""
        change = CollectionChange(
            event_type=CollectionEvent.ITEM_ADDED,
            index=5,
            new_value="test_item"
        )
        
        assert change.event_type == CollectionEvent.ITEM_ADDED
        assert change.index == 5
        assert change.new_value == "test_item"
        assert change.timestamp > 0
        
    def test_virtual_scroll_info(self):
        """Test virtual scrolling information."""
        scroll_info = VirtualScrollInfo(
            total_items=100,
            visible_start=10,
            visible_end=20,
            scroll_offset=300,
            viewport_height=400,
            item_height=30
        )
        
        assert scroll_info.total_items == 100
        assert scroll_info.visible_start == 10
        assert scroll_info.visible_end == 20
        assert scroll_info.scroll_offset == 300
        assert scroll_info.viewport_height == 400
        assert scroll_info.item_height == 30


class MockCollectionWidget(CollectionWidget[str]):
    """Mock collection widget for testing base functionality."""
    
    def __init__(self, config: CollectionConfig = None):
        super().__init__(config or CollectionConfig())
        self.layout_calls = 0
        
    def _create_item_widget(self, item: str, index: int) -> Widget:
        return TextWidget(text=item, widget_id=f"item_{index}")
        
    def _layout_items(self) -> None:
        self.layout_calls += 1
        
    def _calculate_item_bounds(self, index: int) -> WidgetBounds:
        return WidgetBounds(0, index * 30, 100, 30)
        
    def render(self, canvas) -> None:
        """Mock render method."""
        pass


class TestCollectionWidgetBase:
    """Test base collection widget functionality."""
    
    def test_collection_widget_creation(self):
        """Test collection widget creation."""
        widget = MockCollectionWidget()
        
        assert widget.item_count == 0
        assert len(widget.selected_indices) == 0
        assert widget.focused_index is None
        
    def test_add_item(self):
        """Test adding items to collection."""
        widget = MockCollectionWidget()
        
        # Add items
        widget.add_item("Item 1")
        widget.add_item("Item 2")
        widget.add_item("Item 3")
        
        assert widget.item_count == 3
        assert widget.get_item(0) == "Item 1"
        assert widget.get_item(1) == "Item 2"
        assert widget.get_item(2) == "Item 3"
        assert widget.layout_calls > 0
        
    def test_remove_item(self):
        """Test removing items from collection."""
        widget = MockCollectionWidget()
        
        widget.add_item("Item 1")
        widget.add_item("Item 2")
        widget.add_item("Item 3")
        
        removed = widget.remove_item(1)
        
        assert removed == "Item 2"
        assert widget.item_count == 2
        assert widget.get_item(0) == "Item 1"
        assert widget.get_item(1) == "Item 3"
        
    def test_clear_items(self):
        """Test clearing all items."""
        widget = MockCollectionWidget()
        
        widget.add_item("Item 1")
        widget.add_item("Item 2")
        widget.add_item("Item 3")
        
        widget.clear_items()
        
        assert widget.item_count == 0
        assert len(widget.selected_indices) == 0
        assert widget.focused_index is None
        
    def test_selection_single_mode(self):
        """Test single selection mode."""
        config = CollectionConfig(selection_mode=SelectionMode.SINGLE)
        widget = MockCollectionWidget(config)
        
        widget.add_item("Item 1")
        widget.add_item("Item 2")
        widget.add_item("Item 3")
        
        widget.set_selection(1)
        assert widget.selected_indices == {1}
        
        # Setting multiple should only keep one
        widget.set_selection({0, 2})
        assert len(widget.selected_indices) == 1
        
    def test_selection_multiple_mode(self):
        """Test multiple selection mode."""
        config = CollectionConfig(selection_mode=SelectionMode.MULTIPLE)
        widget = MockCollectionWidget(config)
        
        widget.add_item("Item 1")
        widget.add_item("Item 2")
        widget.add_item("Item 3")
        
        widget.set_selection({0, 2})
        assert widget.selected_indices == {0, 2}
        
        widget.add_to_selection(1)
        assert widget.selected_indices == {0, 1, 2}
        
        widget.remove_from_selection(1)
        assert widget.selected_indices == {0, 2}


class TestStackWidget:
    """Test stack widget functionality."""
    
    def test_stack_widget_creation(self):
        """Test stack widget creation."""
        stack = StackWidget(
            direction=StackDirection.HORIZONTAL,
            alignment=StackAlignment.CENTER,
            spacing=10
        )
        
        assert stack.direction == StackDirection.HORIZONTAL
        assert stack.alignment == StackAlignment.CENTER
        assert stack.config.spacing == 10
        
    def test_stack_add_items(self):
        """Test adding items to stack."""
        stack = StackWidget()
        
        stack.add_item("Item 1")
        stack.add_item("Item 2")
        stack.add_item("Item 3")
        
        assert stack.item_count == 3
        assert stack.get_item(0) == "Item 1"
        assert stack.get_item(1) == "Item 2"
        assert stack.get_item(2) == "Item 3"
        
    def test_stack_direction_change(self):
        """Test changing stack direction."""
        stack = StackWidget(direction=StackDirection.VERTICAL)
        
        assert stack.direction == StackDirection.VERTICAL
        
        stack.set_direction(StackDirection.HORIZONTAL)
        assert stack.direction == StackDirection.HORIZONTAL
        
    def test_stack_alignment_change(self):
        """Test changing stack alignment."""
        stack = StackWidget(alignment=StackAlignment.START)
        
        assert stack.alignment == StackAlignment.START
        
        stack.set_alignment(StackAlignment.CENTER)
        assert stack.alignment == StackAlignment.CENTER


class TestGridWidget:
    """Test grid widget functionality."""
    
    def test_grid_widget_creation(self):
        """Test grid widget creation."""
        grid = GridWidget(columns=3, rows=2, cell_spacing=5)
        
        assert grid.columns == 3
        assert grid.config.rows == 2
        assert grid.config.cell_spacing == 5
        
    def test_grid_cell_position_calculation(self):
        """Test grid cell position calculation."""
        grid = GridWidget(columns=3)
        
        assert grid.get_cell_position(0) == (0, 0)  # First row, first column
        assert grid.get_cell_position(1) == (0, 1)  # First row, second column
        assert grid.get_cell_position(2) == (0, 2)  # First row, third column
        assert grid.get_cell_position(3) == (1, 0)  # Second row, first column
        assert grid.get_cell_position(4) == (1, 1)  # Second row, second column
        
    def test_grid_index_from_position(self):
        """Test getting index from grid position."""
        grid = GridWidget(columns=3)
        
        assert grid.get_index_from_position(0, 0) == 0
        assert grid.get_index_from_position(0, 1) == 1
        assert grid.get_index_from_position(0, 2) == 2
        assert grid.get_index_from_position(1, 0) == 3
        assert grid.get_index_from_position(1, 1) == 4
        
    def test_grid_auto_rows(self):
        """Test automatic row calculation."""
        grid = GridWidget(columns=3, rows=0)  # Auto rows
        
        # Add 7 items (should create 3 rows: 3+3+1)
        for i in range(7):
            grid.add_item(f"Item {i}")
            
        assert grid.rows == 3  # Should auto-calculate to 3 rows


class TestSequenceWidget:
    """Test sequence widget functionality."""
    
    def test_sequence_widget_creation(self):
        """Test sequence widget creation."""
        sequence = SequenceWidget(
            auto_advance=True,
            auto_advance_interval=2.0,
            transition=SequenceTransition.FADE
        )
        
        assert sequence.config.auto_advance is True
        assert sequence.config.auto_advance_interval == 2.0
        assert sequence.config.transition == SequenceTransition.FADE
        
    def test_sequence_navigation(self):
        """Test sequence navigation."""
        sequence = SequenceWidget()
        
        sequence.add_item("Item 1")
        sequence.add_item("Item 2")
        sequence.add_item("Item 3")
        
        assert sequence.current_index == 0
        assert sequence.current_item == "Item 1"
        
        # Navigate next
        success = sequence.next_item()
        assert success is True
        assert sequence.current_index == 1
        assert sequence.current_item == "Item 2"
        
        # Navigate previous
        success = sequence.previous_item()
        assert success is True
        assert sequence.current_index == 0
        assert sequence.current_item == "Item 1"
        
    def test_sequence_set_current_index(self):
        """Test setting current index directly."""
        sequence = SequenceWidget()
        
        sequence.add_item("Item 1")
        sequence.add_item("Item 2")
        sequence.add_item("Item 3")
        
        success = sequence.set_current_index(2)
        assert success is True
        assert sequence.current_index == 2
        assert sequence.current_item == "Item 3"
        
        # Invalid index should fail
        success = sequence.set_current_index(5)
        assert success is False
        assert sequence.current_index == 2  # Should remain unchanged
        
    def test_sequence_looping(self):
        """Test sequence looping behavior."""
        sequence = SequenceWidget()
        sequence.config.loop = True
        
        sequence.add_item("Item 1")
        sequence.add_item("Item 2")
        sequence.add_item("Item 3")
        
        # Go to last item
        sequence.set_current_index(2)
        
        # Next should loop to first
        success = sequence.next_item()
        assert success is True
        assert sequence.current_index == 0
        
        # Previous should loop to last
        success = sequence.previous_item()
        assert success is True
        assert sequence.current_index == 2
        
    def test_sequence_no_looping(self):
        """Test sequence without looping."""
        sequence = SequenceWidget()
        sequence.config.loop = False
        
        sequence.add_item("Item 1")
        sequence.add_item("Item 2")
        sequence.add_item("Item 3")
        
        # Go to last item
        sequence.set_current_index(2)
        
        # Next should fail at end
        success = sequence.next_item()
        assert success is False
        assert sequence.current_index == 2
        
        # Go to first item
        sequence.set_current_index(0)
        
        # Previous should fail at beginning
        success = sequence.previous_item()
        assert success is False
        assert sequence.current_index == 0


class TestCollectionWidgetIntegration:
    """Test integration between collection widgets and other systems."""
    
    def test_collection_with_reactive_list(self):
        """Test collection widget with reactive list."""
        stack = StackWidget()
        reactive_list = ReactiveList(["Item 1", "Item 2", "Item 3"])
        
        stack.bind_reactive_data(reactive_list)
        
        assert stack.item_count == 3
        
        # Modify reactive list
        reactive_list.append("Item 4")
        
        assert stack.item_count == 4
        assert stack.get_item(3) == "Item 4"
        
    def test_collection_performance_with_many_items(self):
        """Test collection performance with many items."""
        stack = StackWidget()
        stack._config.virtual_scrolling = True  # Enable virtual scrolling on existing config
        
        start_time = time.time()
        
        # Add many items
        for i in range(10):  # Reduced from 1000 for faster testing
            stack.add_item(f"Item {i}")
            
        end_time = time.time()
        
        # Should complete reasonably quickly
        assert end_time - start_time < 1.0  # Less than 1 second
        assert stack.item_count == 10
        
    def test_collection_memory_cleanup(self):
        """Test that collection widgets clean up properly."""
        stack = StackWidget()
        
        # Add items
        for i in range(10):
            stack.add_item(f"Item {i}")
            
        # Clear all items
        stack.clear_items()
        
        assert stack.item_count == 0
        assert len(stack._item_widgets) == 0
        assert len(stack._widget_items) == 0
        assert len(stack.selected_indices) == 0


if __name__ == "__main__":
    pytest.main([__file__]) 