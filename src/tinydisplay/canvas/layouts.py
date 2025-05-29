#!/usr/bin/env python3
"""
Layout Manager Framework

Provides layout managers for automatic widget positioning including:
- AbsoluteLayout for precise positioning
- FlowLayout for automatic widget flow
- GridLayout for row/column arrangements
- Layout constraint system for responsive design
- Layout animation and transition support
- Layout performance optimization
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import threading
import time

from ..widgets.base import Widget, WidgetBounds


class LayoutDirection(Enum):
    """Layout direction options."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class Alignment(Enum):
    """Alignment options for layout managers."""
    START = "start"      # Left/Top
    CENTER = "center"    # Center
    END = "end"         # Right/Bottom
    STRETCH = "stretch"  # Fill available space
    BASELINE = "baseline"  # Align to text baseline


class WrapMode(Enum):
    """Wrap behavior for flow layouts."""
    NO_WRAP = "no_wrap"      # Don't wrap, overflow
    WRAP = "wrap"            # Wrap to next line/column
    WRAP_REVERSE = "wrap_reverse"  # Wrap in reverse order


@dataclass
class LayoutConstraints:
    """Layout constraints for responsive design."""
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    aspect_ratio: Optional[float] = None  # width/height ratio
    flex_grow: float = 0.0    # How much to grow relative to other widgets
    flex_shrink: float = 1.0  # How much to shrink relative to other widgets
    flex_basis: Optional[int] = None  # Initial size before growing/shrinking
    
    def apply_to_size(self, width: int, height: int) -> Tuple[int, int]:
        """Apply constraints to a size.
        
        Args:
            width, height: Original size
            
        Returns:
            Constrained size
        """
        # Apply width constraints
        if self.min_width is not None:
            width = max(width, self.min_width)
        if self.max_width is not None:
            width = min(width, self.max_width)
            
        # Apply height constraints
        if self.min_height is not None:
            height = max(height, self.min_height)
        if self.max_height is not None:
            height = min(height, self.max_height)
            
        # Apply aspect ratio if specified
        if self.aspect_ratio is not None:
            # Maintain aspect ratio, adjusting height
            height = int(width / self.aspect_ratio)
            
        return (width, height)


@dataclass
class LayoutMargin:
    """Margin specification for layout spacing."""
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0
    
    @classmethod
    def uniform(cls, margin: int) -> 'LayoutMargin':
        """Create uniform margin on all sides."""
        return cls(margin, margin, margin, margin)
    
    @classmethod
    def symmetric(cls, horizontal: int, vertical: int) -> 'LayoutMargin':
        """Create symmetric margin."""
        return cls(horizontal, vertical, horizontal, vertical)


class LayoutManager(ABC):
    """Abstract base class for layout managers.
    
    Provides the interface that all layout managers must implement
    for automatic widget positioning and sizing.
    """
    
    def __init__(self):
        self._animation_enabled = False
        self._animation_duration = 0.3  # seconds
        self._last_layout_time = 0.0
        
    @abstractmethod
    def layout_widgets(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets within the given canvas bounds.
        
        Args:
            widgets: List of widgets to layout
            canvas_bounds: Available space for layout
        """
        pass
    
    @abstractmethod
    def get_preferred_size(self, widgets: List[Widget]) -> Tuple[int, int]:
        """Get preferred size for the given widgets.
        
        Args:
            widgets: List of widgets to calculate size for
            
        Returns:
            Preferred (width, height) for layout
        """
        pass
    
    def enable_animation(self, enabled: bool = True, duration: float = 0.3) -> None:
        """Enable or disable layout animations.
        
        Args:
            enabled: Whether to enable animations
            duration: Animation duration in seconds
        """
        self._animation_enabled = enabled
        self._animation_duration = duration
    
    def needs_relayout(self, widgets: List[Widget]) -> bool:
        """Check if layout needs to be recalculated.
        
        Args:
            widgets: List of widgets to check
            
        Returns:
            True if relayout is needed
        """
        # Simple implementation: check if any widget is dirty
        return any(widget.needs_render() for widget in widgets)
    
    def _animate_widget_to_position(self, widget: Widget, target_position: Tuple[int, int]) -> None:
        """Animate widget to target position if animation is enabled.
        
        Args:
            widget: Widget to animate
            target_position: Target position
        """
        if not self._animation_enabled:
            widget.position = target_position
            return
        
        # Simple linear interpolation animation
        start_position = widget.position
        start_time = time.time()
        
        def update_position():
            elapsed = time.time() - start_time
            progress = min(elapsed / self._animation_duration, 1.0)
            
            # Linear interpolation
            current_x = int(start_position[0] + (target_position[0] - start_position[0]) * progress)
            current_y = int(start_position[1] + (target_position[1] - start_position[1]) * progress)
            
            widget.position = (current_x, current_y)
            
            if progress < 1.0:
                # Continue animation (in real implementation, would use proper animation system)
                pass
        
        update_position()


class AbsoluteLayout(LayoutManager):
    """Layout manager for absolute positioning.
    
    Widgets maintain their absolute positions with optional validation
    and constraint enforcement.
    """
    
    def __init__(self, validate_bounds: bool = True):
        super().__init__()
        self.validate_bounds = validate_bounds
    
    def layout_widgets(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets using their absolute positions.
        
        Args:
            widgets: List of widgets to layout
            canvas_bounds: Canvas bounds for validation
        """
        for widget in widgets:
            if hasattr(widget, 'position'):
                x, y = widget.position
                
                if self.validate_bounds:
                    # Ensure widget stays within canvas bounds
                    widget_width, widget_height = widget.size
                    
                    # Clamp position to keep widget visible
                    x = max(canvas_bounds.x, min(x, canvas_bounds.right - widget_width))
                    y = max(canvas_bounds.y, min(y, canvas_bounds.bottom - widget_height))
                    
                    if (x, y) != widget.position:
                        self._animate_widget_to_position(widget, (x, y))
    
    def get_preferred_size(self, widgets: List[Widget]) -> Tuple[int, int]:
        """Get preferred size based on widget positions and sizes.
        
        Args:
            widgets: List of widgets
            
        Returns:
            Minimum size to contain all widgets
        """
        if not widgets:
            return (0, 0)
        
        max_right = 0
        max_bottom = 0
        
        for widget in widgets:
            if hasattr(widget, 'position') and hasattr(widget, 'size'):
                x, y = widget.position
                width, height = widget.size
                max_right = max(max_right, x + width)
                max_bottom = max(max_bottom, y + height)
        
        return (max_right, max_bottom)


class FlowLayout(LayoutManager):
    """Layout manager for automatic widget flow.
    
    Arranges widgets in a flowing manner, wrapping to new lines/columns
    when space is exhausted.
    """
    
    def __init__(self, direction: LayoutDirection = LayoutDirection.HORIZONTAL,
                 spacing: int = 5, line_spacing: int = 5,
                 wrap_mode: WrapMode = WrapMode.WRAP,
                 alignment: Alignment = Alignment.START):
        super().__init__()
        self.direction = direction
        self.spacing = spacing
        self.line_spacing = line_spacing
        self.wrap_mode = wrap_mode
        self.alignment = alignment
    
    def layout_widgets(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets in flow arrangement.
        
        Args:
            widgets: List of widgets to layout
            canvas_bounds: Available space for layout
        """
        if not widgets:
            return
        
        if self.direction == LayoutDirection.HORIZONTAL:
            self._layout_horizontal_flow(widgets, canvas_bounds)
        else:
            self._layout_vertical_flow(widgets, canvas_bounds)
    
    def _layout_horizontal_flow(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets in horizontal flow."""
        current_x = canvas_bounds.x
        current_y = canvas_bounds.y
        line_height = 0
        
        for widget in widgets:
            widget_width, widget_height = widget.size
            
            # Check if widget fits on current line
            if (self.wrap_mode == WrapMode.WRAP and 
                current_x + widget_width > canvas_bounds.right and 
                current_x > canvas_bounds.x):
                
                # Move to next line
                current_x = canvas_bounds.x
                current_y += line_height + self.line_spacing
                line_height = 0
            
            # Position widget
            target_position = (current_x, current_y)
            self._animate_widget_to_position(widget, target_position)
            
            # Update position for next widget
            current_x += widget_width + self.spacing
            line_height = max(line_height, widget_height)
    
    def _layout_vertical_flow(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets in vertical flow."""
        current_x = canvas_bounds.x
        current_y = canvas_bounds.y
        column_width = 0
        
        for widget in widgets:
            widget_width, widget_height = widget.size
            
            # Check if widget fits in current column
            if (self.wrap_mode == WrapMode.WRAP and 
                current_y + widget_height > canvas_bounds.bottom and 
                current_y > canvas_bounds.y):
                
                # Move to next column
                current_x += column_width + self.spacing
                current_y = canvas_bounds.y
                column_width = 0
            
            # Position widget
            target_position = (current_x, current_y)
            self._animate_widget_to_position(widget, target_position)
            
            # Update position for next widget
            current_y += widget_height + self.line_spacing
            column_width = max(column_width, widget_width)
    
    def get_preferred_size(self, widgets: List[Widget]) -> Tuple[int, int]:
        """Get preferred size for flow layout.
        
        Args:
            widgets: List of widgets
            
        Returns:
            Preferred size for layout
        """
        if not widgets:
            return (0, 0)
        
        if self.direction == LayoutDirection.HORIZONTAL:
            # Calculate total width and maximum height
            total_width = sum(widget.size[0] for widget in widgets)
            total_width += self.spacing * (len(widgets) - 1)
            max_height = max(widget.size[1] for widget in widgets)
            return (total_width, max_height)
        else:
            # Calculate maximum width and total height
            max_width = max(widget.size[0] for widget in widgets)
            total_height = sum(widget.size[1] for widget in widgets)
            total_height += self.line_spacing * (len(widgets) - 1)
            return (max_width, total_height)


class GridLayout(LayoutManager):
    """Layout manager for grid arrangements.
    
    Arranges widgets in a regular grid with configurable rows, columns,
    spacing, and alignment options.
    """
    
    def __init__(self, rows: int, columns: int, 
                 spacing: Tuple[int, int] = (5, 5),
                 cell_alignment: Alignment = Alignment.CENTER,
                 uniform_cell_size: bool = False):
        super().__init__()
        self.rows = rows
        self.columns = columns
        self.spacing = spacing  # (horizontal, vertical)
        self.cell_alignment = cell_alignment
        self.uniform_cell_size = uniform_cell_size
    
    def layout_widgets(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets in grid arrangement.
        
        Args:
            widgets: List of widgets to layout
            canvas_bounds: Available space for layout
        """
        if not widgets:
            return
        
        # Calculate cell dimensions
        available_width = canvas_bounds.width - (self.columns - 1) * self.spacing[0]
        available_height = canvas_bounds.height - (self.rows - 1) * self.spacing[1]
        
        cell_width = available_width // self.columns
        cell_height = available_height // self.rows
        
        # Layout widgets in grid
        for i, widget in enumerate(widgets):
            if i >= self.rows * self.columns:
                break  # More widgets than grid cells
            
            row = i // self.columns
            col = i % self.columns
            
            # Calculate cell position
            cell_x = canvas_bounds.x + col * (cell_width + self.spacing[0])
            cell_y = canvas_bounds.y + row * (cell_height + self.spacing[1])
            
            # Calculate widget position within cell based on alignment
            widget_width, widget_height = widget.size
            
            if self.uniform_cell_size:
                # Force widget to fill cell
                widget.size = (cell_width, cell_height)
                widget_x = cell_x
                widget_y = cell_y
            else:
                # Position widget within cell based on alignment
                if self.cell_alignment == Alignment.START:
                    widget_x = cell_x
                    widget_y = cell_y
                elif self.cell_alignment == Alignment.CENTER:
                    widget_x = cell_x + (cell_width - widget_width) // 2
                    widget_y = cell_y + (cell_height - widget_height) // 2
                elif self.cell_alignment == Alignment.END:
                    widget_x = cell_x + cell_width - widget_width
                    widget_y = cell_y + cell_height - widget_height
                elif self.cell_alignment == Alignment.STRETCH:
                    widget.size = (cell_width, cell_height)
                    widget_x = cell_x
                    widget_y = cell_y
                else:
                    widget_x = cell_x
                    widget_y = cell_y
            
            target_position = (widget_x, widget_y)
            self._animate_widget_to_position(widget, target_position)
    
    def get_preferred_size(self, widgets: List[Widget]) -> Tuple[int, int]:
        """Get preferred size for grid layout.
        
        Args:
            widgets: List of widgets
            
        Returns:
            Preferred size for grid
        """
        if not widgets:
            return (0, 0)
        
        if self.uniform_cell_size:
            # Use maximum widget size for all cells
            max_width = max(widget.size[0] for widget in widgets)
            max_height = max(widget.size[1] for widget in widgets)
        else:
            # Calculate average cell size
            total_width = sum(widget.size[0] for widget in widgets)
            total_height = sum(widget.size[1] for widget in widgets)
            max_width = total_width // len(widgets)
            max_height = total_height // len(widgets)
        
        # Calculate total grid size
        total_width = self.columns * max_width + (self.columns - 1) * self.spacing[0]
        total_height = self.rows * max_height + (self.rows - 1) * self.spacing[1]
        
        return (total_width, total_height)
    
    def set_grid_size(self, rows: int, columns: int) -> None:
        """Update grid dimensions.
        
        Args:
            rows: Number of rows
            columns: Number of columns
        """
        self.rows = max(1, rows)
        self.columns = max(1, columns)


class FlexLayout(LayoutManager):
    """Flexible layout manager with CSS Flexbox-like behavior.
    
    Provides flexible sizing and positioning with grow/shrink factors
    and sophisticated alignment options.
    """
    
    def __init__(self, direction: LayoutDirection = LayoutDirection.HORIZONTAL,
                 justify_content: Alignment = Alignment.START,
                 align_items: Alignment = Alignment.STRETCH,
                 wrap: WrapMode = WrapMode.NO_WRAP,
                 gap: int = 0):
        super().__init__()
        self.direction = direction
        self.justify_content = justify_content
        self.align_items = align_items
        self.wrap = wrap
        self.gap = gap
    
    def layout_widgets(self, widgets: List[Widget], canvas_bounds: WidgetBounds) -> None:
        """Layout widgets using flexible layout algorithm.
        
        Args:
            widgets: List of widgets to layout
            canvas_bounds: Available space for layout
        """
        if not widgets:
            return
        
        # Get layout constraints for each widget
        constraints = []
        for widget in widgets:
            if hasattr(widget, 'layout_constraints'):
                constraints.append(widget.layout_constraints)
            else:
                constraints.append(LayoutConstraints())
        
        if self.direction == LayoutDirection.HORIZONTAL:
            self._layout_horizontal_flex(widgets, constraints, canvas_bounds)
        else:
            self._layout_vertical_flex(widgets, constraints, canvas_bounds)
    
    def _layout_horizontal_flex(self, widgets: List[Widget], 
                               constraints: List[LayoutConstraints],
                               canvas_bounds: WidgetBounds) -> None:
        """Layout widgets horizontally with flex behavior."""
        available_width = canvas_bounds.width - self.gap * (len(widgets) - 1)
        
        # Calculate initial sizes
        total_flex_grow = sum(c.flex_grow for c in constraints)
        total_basis = sum(c.flex_basis or widget.size[0] for widget, c in zip(widgets, constraints))
        
        # Distribute extra space
        extra_space = max(0, available_width - total_basis)
        
        current_x = canvas_bounds.x
        
        for widget, constraint in zip(widgets, constraints):
            # Calculate widget width
            basis_width = constraint.flex_basis or widget.size[0]
            
            if total_flex_grow > 0 and constraint.flex_grow > 0:
                grow_width = int(extra_space * (constraint.flex_grow / total_flex_grow))
                widget_width = basis_width + grow_width
            else:
                widget_width = basis_width
            
            # Apply constraints
            widget_width, widget_height = constraint.apply_to_size(widget_width, widget.size[1])
            
            # Calculate Y position based on alignment
            if self.align_items == Alignment.START:
                widget_y = canvas_bounds.y
            elif self.align_items == Alignment.CENTER:
                widget_y = canvas_bounds.y + (canvas_bounds.height - widget_height) // 2
            elif self.align_items == Alignment.END:
                widget_y = canvas_bounds.bottom - widget_height
            elif self.align_items == Alignment.STRETCH:
                widget_y = canvas_bounds.y
                widget_height = canvas_bounds.height
            else:
                widget_y = canvas_bounds.y
            
            # Update widget size and position
            widget.size = (widget_width, widget_height)
            target_position = (current_x, widget_y)
            self._animate_widget_to_position(widget, target_position)
            
            current_x += widget_width + self.gap
    
    def _layout_vertical_flex(self, widgets: List[Widget], 
                             constraints: List[LayoutConstraints],
                             canvas_bounds: WidgetBounds) -> None:
        """Layout widgets vertically with flex behavior."""
        available_height = canvas_bounds.height - self.gap * (len(widgets) - 1)
        
        # Calculate initial sizes
        total_flex_grow = sum(c.flex_grow for c in constraints)
        total_basis = sum(c.flex_basis or widget.size[1] for widget, c in zip(widgets, constraints))
        
        # Distribute extra space
        extra_space = max(0, available_height - total_basis)
        
        current_y = canvas_bounds.y
        
        for widget, constraint in zip(widgets, constraints):
            # Calculate widget height
            basis_height = constraint.flex_basis or widget.size[1]
            
            if total_flex_grow > 0 and constraint.flex_grow > 0:
                grow_height = int(extra_space * (constraint.flex_grow / total_flex_grow))
                widget_height = basis_height + grow_height
            else:
                widget_height = basis_height
            
            # Apply constraints
            widget_width, widget_height = constraint.apply_to_size(widget.size[0], widget_height)
            
            # Calculate X position based on alignment
            if self.align_items == Alignment.START:
                widget_x = canvas_bounds.x
            elif self.align_items == Alignment.CENTER:
                widget_x = canvas_bounds.x + (canvas_bounds.width - widget_width) // 2
            elif self.align_items == Alignment.END:
                widget_x = canvas_bounds.right - widget_width
            elif self.align_items == Alignment.STRETCH:
                widget_x = canvas_bounds.x
                widget_width = canvas_bounds.width
            else:
                widget_x = canvas_bounds.x
            
            # Update widget size and position
            widget.size = (widget_width, widget_height)
            target_position = (widget_x, current_y)
            self._animate_widget_to_position(widget, target_position)
            
            current_y += widget_height + self.gap
    
    def get_preferred_size(self, widgets: List[Widget]) -> Tuple[int, int]:
        """Get preferred size for flex layout.
        
        Args:
            widgets: List of widgets
            
        Returns:
            Preferred size for layout
        """
        if not widgets:
            return (0, 0)
        
        if self.direction == LayoutDirection.HORIZONTAL:
            total_width = sum(widget.size[0] for widget in widgets) + self.gap * (len(widgets) - 1)
            max_height = max(widget.size[1] for widget in widgets)
            return (total_width, max_height)
        else:
            max_width = max(widget.size[0] for widget in widgets)
            total_height = sum(widget.size[1] for widget in widgets) + self.gap * (len(widgets) - 1)
            return (max_width, total_height)


# Utility functions for layout management
def create_absolute_layout(validate_bounds: bool = True) -> AbsoluteLayout:
    """Create an absolute layout manager.
    
    Args:
        validate_bounds: Whether to validate widget bounds
        
    Returns:
        AbsoluteLayout instance
    """
    return AbsoluteLayout(validate_bounds)


def create_flow_layout(direction: LayoutDirection = LayoutDirection.HORIZONTAL,
                      spacing: int = 5) -> FlowLayout:
    """Create a flow layout manager.
    
    Args:
        direction: Layout direction
        spacing: Spacing between widgets
        
    Returns:
        FlowLayout instance
    """
    return FlowLayout(direction, spacing)


def create_grid_layout(rows: int, columns: int, spacing: Tuple[int, int] = (5, 5)) -> GridLayout:
    """Create a grid layout manager.
    
    Args:
        rows: Number of rows
        columns: Number of columns
        spacing: Horizontal and vertical spacing
        
    Returns:
        GridLayout instance
    """
    return GridLayout(rows, columns, spacing) 