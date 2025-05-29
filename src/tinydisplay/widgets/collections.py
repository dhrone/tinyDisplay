#!/usr/bin/env python3
"""
Collection Widget Implementations

Provides concrete implementations of collection widgets including Stack, Grid, and Sequence widgets
for sophisticated layout management and dynamic content organization.
"""

from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import math
import time

from .base import Widget, WidgetBounds
from .text import TextWidget
from .collection_base import (
    CollectionWidget, CollectionConfig, CollectionLayout, SelectionMode,
    CollectionEvent, CollectionChange, VirtualScrollInfo
)
from ..core.reactive import ReactiveValue


class StackDirection(Enum):
    """Stack arrangement directions."""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class StackAlignment(Enum):
    """Stack item alignment options."""
    START = "start"         # Top/Left
    CENTER = "center"       # Center
    END = "end"            # Bottom/Right
    STRETCH = "stretch"     # Fill available space


@dataclass
class StackConfig(CollectionConfig):
    """Configuration for stack widgets."""
    direction: StackDirection = StackDirection.VERTICAL
    alignment: StackAlignment = StackAlignment.START
    spacing: int = 5
    padding: int = 10
    wrap: bool = False
    reverse: bool = False
    
    def __post_init__(self):
        self.layout_type = (CollectionLayout.STACK_VERTICAL 
                           if self.direction == StackDirection.VERTICAL 
                           else CollectionLayout.STACK_HORIZONTAL)


class StackWidget(CollectionWidget[Any]):
    """Stack widget that arranges children vertically or horizontally."""
    
    def __init__(self, direction: StackDirection = StackDirection.VERTICAL,
                 alignment: StackAlignment = StackAlignment.START,
                 spacing: int = 5, widget_id: Optional[str] = None):
        
        config = StackConfig(
            direction=direction,
            alignment=alignment,
            spacing=spacing,
            layout_type=(CollectionLayout.STACK_VERTICAL 
                        if direction == StackDirection.VERTICAL 
                        else CollectionLayout.STACK_HORIZONTAL)
        )
        super().__init__(config, widget_id)
        
        # Stack-specific properties
        self._total_size = 0
        self._max_cross_size = 0
        
    @property
    def direction(self) -> StackDirection:
        """Get stack direction."""
        return self._config.direction
        
    @property
    def alignment(self) -> StackAlignment:
        """Get stack alignment."""
        return self._config.alignment
        
    def set_direction(self, direction: StackDirection) -> None:
        """Set stack direction."""
        if self._config.direction != direction:
            self._config.direction = direction
            self._config.layout_type = (CollectionLayout.STACK_VERTICAL 
                                      if direction == StackDirection.VERTICAL 
                                      else CollectionLayout.STACK_HORIZONTAL)
            self._schedule_layout()
            
    def set_alignment(self, alignment: StackAlignment) -> None:
        """Set stack alignment."""
        if self._config.alignment != alignment:
            self._config.alignment = alignment
            self._schedule_layout()
            
    def set_spacing(self, spacing: int) -> None:
        """Set spacing between items."""
        if self._config.spacing != spacing:
            self._config.spacing = spacing
            self._schedule_layout()
            
    def _create_item_widget(self, item: Any, index: int) -> Widget:
        """Create a widget for the given item."""
        if self._item_factory:
            widget = self._item_factory(item, index)
        elif isinstance(item, Widget):
            widget = item
        elif isinstance(item, str):
            widget = TextWidget(text=item, widget_id=f"{self.widget_id}_item_{index}")
        else:
            widget = TextWidget(text=str(item), widget_id=f"{self.widget_id}_item_{index}")
            
        # Apply item configurator if set
        if self._item_configurator:
            self._item_configurator(widget, item, index)
            
        return widget
        
    def _layout_items(self) -> None:
        """Layout all item widgets in stack arrangement."""
        if not self._item_widgets:
            return
            
        # Calculate available space
        container_bounds = self.bounds
        padding = self._config.padding
        spacing = self._config.spacing
        
        available_width = container_bounds.width - (2 * padding)
        available_height = container_bounds.height - (2 * padding)
        
        if self._config.direction == StackDirection.VERTICAL:
            self._layout_vertical(available_width, available_height, padding, spacing)
        else:
            self._layout_horizontal(available_width, available_height, padding, spacing)
            
    def _layout_vertical(self, available_width: int, available_height: int, 
                        padding: int, spacing: int) -> None:
        """Layout items vertically."""
        current_y = padding
        max_width = 0
        
        # Calculate total height needed
        total_height = 0
        item_heights = []
        
        for index in sorted(self._item_widgets.keys()):
            widget = self._item_widgets[index]
            widget_height = widget.size[1] if widget.size[1] > 0 else self._config.item_height
            item_heights.append(widget_height)
            total_height += widget_height
            max_width = max(max_width, widget.size[0])
            
        # Add spacing
        if len(item_heights) > 1:
            total_height += spacing * (len(item_heights) - 1)
            
        # Calculate starting Y based on alignment
        if self._config.alignment == StackAlignment.CENTER:
            current_y = padding + max(0, (available_height - total_height) // 2)
        elif self._config.alignment == StackAlignment.END:
            current_y = padding + max(0, available_height - total_height)
        else:  # START
            current_y = padding
            
        # Position each item
        for i, index in enumerate(sorted(self._item_widgets.keys())):
            widget = self._item_widgets[index]
            widget_height = item_heights[i]
            
            # Calculate X position based on alignment
            if self._config.alignment == StackAlignment.STRETCH:
                widget_x = padding
                widget_width = available_width
            elif self._config.alignment == StackAlignment.CENTER:
                widget_width = widget.size[0] if widget.size[0] > 0 else self._config.item_width
                widget_x = padding + max(0, (available_width - widget_width) // 2)
            elif self._config.alignment == StackAlignment.END:
                widget_width = widget.size[0] if widget.size[0] > 0 else self._config.item_width
                widget_x = padding + max(0, available_width - widget_width)
            else:  # START
                widget_width = widget.size[0] if widget.size[0] > 0 else self._config.item_width
                widget_x = padding
                
            # Set widget position and size
            widget.position = (widget_x, current_y)
            if self._config.alignment == StackAlignment.STRETCH:
                widget.size = (widget_width, widget_height)
                
            current_y += widget_height + spacing
            
        self._total_size = total_height
        self._max_cross_size = max_width
        
    def _layout_horizontal(self, available_width: int, available_height: int,
                          padding: int, spacing: int) -> None:
        """Layout items horizontally."""
        current_x = padding
        max_height = 0
        
        # Calculate total width needed
        total_width = 0
        item_widths = []
        
        for index in sorted(self._item_widgets.keys()):
            widget = self._item_widgets[index]
            widget_width = widget.size[0] if widget.size[0] > 0 else self._config.item_width
            item_widths.append(widget_width)
            total_width += widget_width
            max_height = max(max_height, widget.size[1])
            
        # Add spacing
        if len(item_widths) > 1:
            total_width += spacing * (len(item_widths) - 1)
            
        # Calculate starting X based on alignment
        if self._config.alignment == StackAlignment.CENTER:
            current_x = padding + max(0, (available_width - total_width) // 2)
        elif self._config.alignment == StackAlignment.END:
            current_x = padding + max(0, available_width - total_width)
        else:  # START
            current_x = padding
            
        # Position each item
        for i, index in enumerate(sorted(self._item_widgets.keys())):
            widget = self._item_widgets[index]
            widget_width = item_widths[i]
            
            # Calculate Y position based on alignment
            if self._config.alignment == StackAlignment.STRETCH:
                widget_y = padding
                widget_height = available_height
            elif self._config.alignment == StackAlignment.CENTER:
                widget_height = widget.size[1] if widget.size[1] > 0 else self._config.item_height
                widget_y = padding + max(0, (available_height - widget_height) // 2)
            elif self._config.alignment == StackAlignment.END:
                widget_height = widget.size[1] if widget.size[1] > 0 else self._config.item_height
                widget_y = padding + max(0, available_height - widget_height)
            else:  # START
                widget_height = widget.size[1] if widget.size[1] > 0 else self._config.item_height
                widget_y = padding
                
            # Set widget position and size
            widget.position = (current_x, widget_y)
            if self._config.alignment == StackAlignment.STRETCH:
                widget.size = (widget_width, widget_height)
                
            current_x += widget_width + spacing
            
        self._total_size = total_width
        self._max_cross_size = max_height
        
    def _calculate_item_bounds(self, index: int) -> WidgetBounds:
        """Calculate bounds for item at given index."""
        widget = self._item_widgets.get(index)
        if widget:
            return widget.bounds
        else:
            # Estimate bounds for virtual scrolling
            padding = self._config.padding
            spacing = self._config.spacing
            
            if self._config.direction == StackDirection.VERTICAL:
                y = padding + index * (self._config.item_height + spacing)
                return WidgetBounds(padding, y, self._config.item_width, self._config.item_height)
            else:
                x = padding + index * (self._config.item_width + spacing)
                return WidgetBounds(x, padding, self._config.item_width, self._config.item_height)
                
    def get_total_size(self) -> int:
        """Get total size of all items in the main axis."""
        return self._total_size
        
    def get_max_cross_size(self) -> int:
        """Get maximum size in the cross axis."""
        return self._max_cross_size
        
    def render(self, canvas) -> None:
        """Render the stack widget and all its items."""
        # Render all visible child widgets
        for widget in self._item_widgets.values():
            if widget.visible and widget.needs_render():
                widget.render(canvas)


# Grid Widget Implementation
class GridSizing(Enum):
    """Grid sizing modes."""
    FIXED = "fixed"           # Fixed size
    AUTO = "auto"            # Size to content
    PROPORTIONAL = "proportional"  # Proportional sizing


@dataclass
class GridColumnConfig:
    """Configuration for a grid column."""
    sizing: GridSizing = GridSizing.AUTO
    size: int = 100
    min_size: int = 50
    max_size: int = 500
    weight: float = 1.0


@dataclass
class GridRowConfig:
    """Configuration for a grid row."""
    sizing: GridSizing = GridSizing.AUTO
    size: int = 30
    min_size: int = 20
    max_size: int = 200
    weight: float = 1.0


@dataclass
class GridConfig(CollectionConfig):
    """Configuration for grid widgets."""
    columns: int = 3
    rows: int = 0  # 0 = auto-calculate
    column_configs: List[GridColumnConfig] = field(default_factory=list)
    row_configs: List[GridRowConfig] = field(default_factory=list)
    cell_spacing: int = 2
    show_grid_lines: bool = False
    
    def __post_init__(self):
        self.layout_type = CollectionLayout.GRID
        
        # Ensure we have column configs
        while len(self.column_configs) < self.columns:
            self.column_configs.append(GridColumnConfig())


class GridWidget(CollectionWidget[Any]):
    """Grid widget that arranges children in rows and columns."""
    
    def __init__(self, columns: int = 3, rows: int = 0,
                 cell_spacing: int = 2, widget_id: Optional[str] = None):
        
        config = GridConfig(
            columns=columns,
            rows=rows,
            cell_spacing=cell_spacing,
            layout_type=CollectionLayout.GRID
        )
        super().__init__(config, widget_id)
        
        # Grid-specific properties
        self._column_widths: List[int] = []
        self._row_heights: List[int] = []
        self._calculated_rows = 0
        
    @property
    def columns(self) -> int:
        """Get number of columns."""
        return self._config.columns
        
    @property
    def rows(self) -> int:
        """Get number of rows."""
        return self._calculated_rows
        
    def set_columns(self, columns: int) -> None:
        """Set number of columns."""
        if self._config.columns != columns:
            self._config.columns = columns
            # Ensure we have enough column configs
            while len(self._config.column_configs) < columns:
                self._config.column_configs.append(GridColumnConfig())
            self._schedule_layout()
            
    def set_column_config(self, column: int, config: GridColumnConfig) -> None:
        """Set configuration for a specific column."""
        if 0 <= column < len(self._config.column_configs):
            self._config.column_configs[column] = config
            self._schedule_layout()
            
    def set_row_config(self, row: int, config: GridRowConfig) -> None:
        """Set configuration for a specific row."""
        # Ensure we have enough row configs
        while len(self._config.row_configs) <= row:
            self._config.row_configs.append(GridRowConfig())
        self._config.row_configs[row] = config
        self._schedule_layout()
        
    def get_cell_position(self, index: int) -> Tuple[int, int]:
        """Get (row, column) position for item index."""
        if self._config.columns <= 0:
            return (0, 0)
        row = index // self._config.columns
        col = index % self._config.columns
        return (row, col)
        
    def get_index_from_position(self, row: int, col: int) -> int:
        """Get item index from (row, column) position."""
        return row * self._config.columns + col
        
    def _create_item_widget(self, item: Any, index: int) -> Widget:
        """Create a widget for the given item."""
        if self._item_factory:
            widget = self._item_factory(item, index)
        elif isinstance(item, Widget):
            widget = item
        elif isinstance(item, str):
            widget = TextWidget(text=item, widget_id=f"{self.widget_id}_item_{index}")
        else:
            widget = TextWidget(text=str(item), widget_id=f"{self.widget_id}_item_{index}")
            
        # Apply item configurator if set
        if self._item_configurator:
            self._item_configurator(widget, item, index)
            
        return widget
        
    def _layout_items(self) -> None:
        """Layout all item widgets in grid arrangement."""
        if not self._item_widgets:
            return
            
        # Calculate grid dimensions
        self._calculate_grid_dimensions()
        
        # Calculate column widths and row heights
        self._calculate_column_widths()
        self._calculate_row_heights()
        
        # Position items
        self._position_grid_items()
        
    def _calculate_grid_dimensions(self) -> None:
        """Calculate the number of rows needed."""
        item_count = len(self._items)
        if item_count == 0:
            self._calculated_rows = 0
        elif self._config.rows > 0:
            self._calculated_rows = self._config.rows
        else:
            self._calculated_rows = math.ceil(item_count / self._config.columns)
            
    def _calculate_column_widths(self) -> None:
        """Calculate width for each column."""
        container_bounds = self.bounds
        padding = self._config.padding
        spacing = self._config.cell_spacing
        
        available_width = container_bounds.width - (2 * padding)
        if self._config.columns > 1:
            available_width -= spacing * (self._config.columns - 1)
            
        self._column_widths = []
        
        # Calculate widths based on column configs
        fixed_width = 0
        auto_columns = []
        proportional_columns = []
        total_weight = 0
        
        for i in range(self._config.columns):
            config = self._config.column_configs[i] if i < len(self._config.column_configs) else GridColumnConfig()
            
            if config.sizing == GridSizing.FIXED:
                width = max(config.min_size, min(config.max_size, config.size))
                self._column_widths.append(width)
                fixed_width += width
            elif config.sizing == GridSizing.AUTO:
                auto_columns.append(i)
                self._column_widths.append(0)  # Will calculate later
            else:  # PROPORTIONAL
                proportional_columns.append(i)
                self._column_widths.append(0)  # Will calculate later
                total_weight += config.weight
                
        # Calculate auto column widths (simplified - use equal distribution)
        remaining_width = available_width - fixed_width
        if auto_columns:
            auto_width = max(50, remaining_width // (len(auto_columns) + len(proportional_columns)))
            for col in auto_columns:
                self._column_widths[col] = auto_width
                remaining_width -= auto_width
                
        # Calculate proportional column widths
        if proportional_columns and remaining_width > 0:
            for col in proportional_columns:
                config = self._config.column_configs[col]
                if total_weight > 0:
                    width = int(remaining_width * config.weight / total_weight)
                    width = max(config.min_size, min(config.max_size, width))
                    self._column_widths[col] = width
                    
    def _calculate_row_heights(self) -> None:
        """Calculate height for each row."""
        container_bounds = self.bounds
        padding = self._config.padding
        spacing = self._config.cell_spacing
        
        available_height = container_bounds.height - (2 * padding)
        if self._calculated_rows > 1:
            available_height -= spacing * (self._calculated_rows - 1)
            
        self._row_heights = []
        
        # For now, use equal height distribution
        # In a more sophisticated implementation, this would consider row configs
        if self._calculated_rows > 0:
            row_height = max(self._config.item_height, available_height // self._calculated_rows)
            self._row_heights = [row_height] * self._calculated_rows
            
    def _position_grid_items(self) -> None:
        """Position all grid items."""
        padding = self._config.padding
        spacing = self._config.cell_spacing
        
        for index in sorted(self._item_widgets.keys()):
            widget = self._item_widgets[index]
            row, col = self.get_cell_position(index)
            
            if row >= len(self._row_heights) or col >= len(self._column_widths):
                continue
                
            # Calculate position
            x = padding + sum(self._column_widths[:col])
            if col > 0:
                x += spacing * col
                
            y = padding + sum(self._row_heights[:row])
            if row > 0:
                y += spacing * row
                
            # Set widget position and size
            widget.position = (x, y)
            widget.size = (self._column_widths[col], self._row_heights[row])
            
    def _calculate_item_bounds(self, index: int) -> WidgetBounds:
        """Calculate bounds for item at given index."""
        row, col = self.get_cell_position(index)
        
        if (row < len(self._row_heights) and col < len(self._column_widths)):
            padding = self._config.padding
            spacing = self._config.cell_spacing
            
            x = padding + sum(self._column_widths[:col])
            if col > 0:
                x += spacing * col
                
            y = padding + sum(self._row_heights[:row])
            if row > 0:
                y += spacing * row
                
            return WidgetBounds(x, y, self._column_widths[col], self._row_heights[row])
        else:
            # Fallback for virtual scrolling
            return WidgetBounds(0, 0, self._config.item_width, self._config.item_height)

    def render(self, canvas) -> None:
        """Render the grid widget and all its items."""
        # Render all visible child widgets
        for widget in self._item_widgets.values():
            if widget.visible and widget.needs_render():
                widget.render(canvas)


# Sequence Widget Implementation
class SequenceTransition(Enum):
    """Sequence transition types."""
    NONE = "none"
    SLIDE = "slide"
    FADE = "fade"
    SCALE = "scale"


@dataclass
class SequenceConfig(CollectionConfig):
    """Configuration for sequence widgets."""
    show_indicators: bool = True
    show_navigation: bool = True
    auto_advance: bool = False
    auto_advance_interval: float = 3.0
    transition: SequenceTransition = SequenceTransition.SLIDE
    transition_duration: float = 0.3
    loop: bool = True
    
    def __post_init__(self):
        self.layout_type = CollectionLayout.SEQUENCE


class SequenceWidget(CollectionWidget[Any]):
    """Sequence widget that displays items one at a time with navigation."""
    
    def __init__(self, auto_advance: bool = False, 
                 auto_advance_interval: float = 3.0,
                 transition: SequenceTransition = SequenceTransition.SLIDE,
                 widget_id: Optional[str] = None):
        
        config = SequenceConfig(
            auto_advance=auto_advance,
            auto_advance_interval=auto_advance_interval,
            transition=transition,
            layout_type=CollectionLayout.SEQUENCE,
            selection_mode=SelectionMode.SINGLE
        )
        super().__init__(config, widget_id)
        
        # Sequence-specific properties
        self._current_index = 0
        self._transition_active = False
        self._auto_advance_timer: Optional[float] = None
        self._last_advance_time = 0.0
        
    @property
    def current_index(self) -> int:
        """Get current item index."""
        return self._current_index
        
    @property
    def current_item(self) -> Any:
        """Get current item."""
        return self.get_item(self._current_index)
        
    def next_item(self) -> bool:
        """Navigate to next item."""
        if self._current_index < len(self._items) - 1:
            return self.set_current_index(self._current_index + 1)
        elif self._config.loop and self._items:
            return self.set_current_index(0)
        return False
        
    def previous_item(self) -> bool:
        """Navigate to previous item."""
        if self._current_index > 0:
            return self.set_current_index(self._current_index - 1)
        elif self._config.loop and self._items:
            return self.set_current_index(len(self._items) - 1)
        return False
        
    def set_current_index(self, index: int) -> bool:
        """Set current item index."""
        if not (0 <= index < len(self._items)):
            return False
            
        if index != self._current_index:
            old_index = self._current_index
            self._current_index = index
            
            # Update selection to match current index
            self.set_selection(index)
            
            # Trigger layout update to show only current item
            self._schedule_layout()
            
            # Reset auto-advance timer
            self._last_advance_time = time.time()
            
            # Fire event
            change = CollectionChange(
                event_type=CollectionEvent.FOCUS_CHANGED,
                index=index,
                old_value=old_index,
                new_value=index
            )
            self._fire_event(change)
            
        return True
        
    def start_auto_advance(self) -> None:
        """Start automatic advancement."""
        self._config.auto_advance = True
        self._last_advance_time = time.time()
        
    def stop_auto_advance(self) -> None:
        """Stop automatic advancement."""
        self._config.auto_advance = False
        
    def _create_item_widget(self, item: Any, index: int) -> Widget:
        """Create a widget for the given item."""
        if self._item_factory:
            widget = self._item_factory(item, index)
        elif isinstance(item, Widget):
            widget = item
        elif isinstance(item, str):
            widget = TextWidget(text=item, widget_id=f"{self.widget_id}_item_{index}")
        else:
            widget = TextWidget(text=str(item), widget_id=f"{self.widget_id}_item_{index}")
            
        # Apply item configurator if set
        if self._item_configurator:
            self._item_configurator(widget, item, index)
            
        return widget
        
    def _layout_items(self) -> None:
        """Layout items - only show current item."""
        if not self._item_widgets:
            return
            
        container_bounds = self.bounds
        padding = self._config.padding
        
        # Hide all widgets first
        for widget in self._item_widgets.values():
            widget.visible = False
            
        # Show and position only the current item
        current_widget = self._item_widgets.get(self._current_index)
        if current_widget:
            current_widget.visible = True
            current_widget.position = (padding, padding)
            current_widget.size = (
                container_bounds.width - 2 * padding,
                container_bounds.height - 2 * padding
            )
            
        # Check for auto-advance
        if self._config.auto_advance and not self._transition_active:
            current_time = time.time()
            if current_time - self._last_advance_time >= self._config.auto_advance_interval:
                self.next_item()
                
    def _calculate_item_bounds(self, index: int) -> WidgetBounds:
        """Calculate bounds for item at given index."""
        container_bounds = self.bounds
        padding = self._config.padding
        
        return WidgetBounds(
            padding, 
            padding,
            container_bounds.width - 2 * padding,
            container_bounds.height - 2 * padding
        )
        
    def add_item(self, item: Any, index: Optional[int] = None) -> None:
        """Add an item to the sequence."""
        super().add_item(item, index)
        
        # If this is the first item, make it current
        if len(self._items) == 1:
            self._current_index = 0
            self.set_selection(0)
            
    def remove_item(self, index: int) -> Optional[Any]:
        """Remove an item from the sequence."""
        result = super().remove_item(index)
        
        if result is not None:
            # Adjust current index if necessary
            if self._current_index >= len(self._items):
                self._current_index = max(0, len(self._items) - 1)
            elif self._current_index > index:
                self._current_index -= 1
                
            # Update selection
            if self._items:
                self.set_selection(self._current_index)
            else:
                self.clear_selection()
                
        return result
        
    def get_sequence_info(self) -> Dict[str, Any]:
        """Get sequence state information."""
        return {
            'current_index': self._current_index,
            'total_items': len(self._items),
            'auto_advance': self._config.auto_advance,
            'auto_advance_interval': self._config.auto_advance_interval,
            'transition': self._config.transition.value,
            'loop': self._config.loop
        }
        
    def render(self, canvas) -> None:
        """Render the sequence widget and its current item."""
        # Only render the current visible item
        current_widget = self._item_widgets.get(self._current_index)
        if current_widget and current_widget.visible and current_widget.needs_render():
            current_widget.render(canvas) 