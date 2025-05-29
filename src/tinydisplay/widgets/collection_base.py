#!/usr/bin/env python3
"""
Collection Widget Base Framework

Provides the foundational framework for all collection widgets including
common operations, event handling, reactive data binding, and performance optimization.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic, Iterator, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import weakref

from .base import Widget, ContainerWidget, WidgetBounds, WidgetState
from ..core.reactive import ReactiveValue, ReactiveChange, ReactiveList, ReactiveDict

T = TypeVar('T')


class CollectionEvent(Enum):
    """Types of collection events."""
    ITEM_ADDED = "item_added"
    ITEM_REMOVED = "item_removed"
    ITEM_CHANGED = "item_changed"
    ITEM_MOVED = "item_moved"
    COLLECTION_CLEARED = "collection_cleared"
    LAYOUT_CHANGED = "layout_changed"
    SELECTION_CHANGED = "selection_changed"
    FOCUS_CHANGED = "focus_changed"
    SCROLL_CHANGED = "scroll_changed"


class CollectionLayout(Enum):
    """Collection layout types."""
    STACK_VERTICAL = "stack_vertical"
    STACK_HORIZONTAL = "stack_horizontal"
    GRID = "grid"
    SEQUENCE = "sequence"
    CUSTOM = "custom"


class SelectionMode(Enum):
    """Selection modes for collections."""
    NONE = "none"           # No selection allowed
    SINGLE = "single"       # Single item selection
    MULTIPLE = "multiple"   # Multiple item selection
    RANGE = "range"         # Range selection with shift


@dataclass
class CollectionChange:
    """Represents a change in a collection."""
    event_type: CollectionEvent
    item: Optional[Widget] = None
    index: Optional[int] = None
    old_index: Optional[int] = None
    new_index: Optional[int] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionConfig:
    """Configuration for collection widgets."""
    layout_type: CollectionLayout = CollectionLayout.STACK_VERTICAL
    selection_mode: SelectionMode = SelectionMode.SINGLE
    virtual_scrolling: bool = False
    item_height: int = 30
    item_width: int = 100
    spacing: int = 5
    padding: int = 10
    auto_layout: bool = True
    lazy_loading: bool = False
    max_visible_items: int = 100
    enable_animations: bool = True
    enable_drag_drop: bool = False


@dataclass
class VirtualScrollInfo:
    """Information for virtual scrolling."""
    total_items: int = 0
    visible_start: int = 0
    visible_end: int = 0
    scroll_offset: int = 0
    viewport_height: int = 0
    item_height: int = 30
    buffer_size: int = 5  # Extra items to render outside viewport


class CollectionWidget(ContainerWidget, Generic[T], ABC):
    """Abstract base class for collection widgets."""
    
    def __init__(self, config: Optional[CollectionConfig] = None, widget_id: Optional[str] = None):
        super().__init__(widget_id)
        
        # Configuration
        self._config = config or CollectionConfig()
        
        # Collection data
        self._items: List[T] = []
        self._item_widgets: Dict[int, Widget] = {}  # index -> widget
        self._widget_items: Dict[str, int] = {}     # widget_id -> index
        self._item_data: Dict[int, Dict[str, Any]] = {}  # index -> metadata
        
        # Collection state
        self._selected_indices: Set[int] = set()
        self._focused_index: Optional[int] = None
        self._last_selected_index: Optional[int] = None
        
        # Virtual scrolling
        self._virtual_scroll: VirtualScrollInfo = VirtualScrollInfo()
        self._rendered_items: Set[int] = set()
        
        # Event handling
        self._event_handlers: Dict[CollectionEvent, Set[Callable[[CollectionChange], None]]] = {
            event: set() for event in CollectionEvent
        }
        
        # Reactive integration
        self._reactive_data: Optional[ReactiveValue] = None
        self._reactive_binding_active = False
        
        # Performance tracking
        self._layout_pending = False
        self._last_layout_time = 0.0
        self._layout_count = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Item factory and customization
        self._item_factory: Optional[Callable[[T, int], Widget]] = None
        self._item_configurator: Optional[Callable[[Widget, T, int], None]] = None
        
    @property
    def config(self) -> CollectionConfig:
        """Get collection configuration."""
        return self._config
        
    @property
    def item_count(self) -> int:
        """Get the number of items in the collection."""
        return len(self._items)
        
    @property
    def selected_indices(self) -> Set[int]:
        """Get currently selected item indices."""
        return self._selected_indices.copy()
        
    @property
    def focused_index(self) -> Optional[int]:
        """Get currently focused item index."""
        return self._focused_index
        
    @property
    def virtual_scroll_info(self) -> VirtualScrollInfo:
        """Get virtual scrolling information."""
        return self._virtual_scroll
        
    # Abstract methods for subclasses
    @abstractmethod
    def _create_item_widget(self, item: T, index: int) -> Widget:
        """Create a widget for the given item."""
        pass
        
    @abstractmethod
    def _layout_items(self) -> None:
        """Layout all item widgets according to collection type."""
        pass
        
    @abstractmethod
    def _calculate_item_bounds(self, index: int) -> WidgetBounds:
        """Calculate bounds for item at given index."""
        pass
        
    # Core collection operations
    def add_item(self, item: T, index: Optional[int] = None) -> None:
        """Add an item to the collection."""
        with self._lock:
            if index is None:
                index = len(self._items)
            else:
                index = max(0, min(index, len(self._items)))
                
            # Insert item
            self._items.insert(index, item)
            
            # Update widget mappings for items after insertion point
            self._update_widget_mappings_after_insert(index)
            
            # Create and add widget if in visible range
            if self._should_render_item(index):
                widget = self._create_item_widget(item, index)
                self._item_widgets[index] = widget
                self._widget_items[widget.widget_id] = index
                self.add_child(widget)
                self._rendered_items.add(index)
                
            # Update virtual scroll info
            self._virtual_scroll.total_items = len(self._items)
            
            # Trigger layout update
            self._schedule_layout()
            
            # Fire event
            change = CollectionChange(
                event_type=CollectionEvent.ITEM_ADDED,
                item=self._item_widgets.get(index),
                index=index,
                new_value=item
            )
            self._fire_event(change)
            
    def remove_item(self, index: int) -> Optional[T]:
        """Remove an item from the collection."""
        with self._lock:
            if not 0 <= index < len(self._items):
                return None
                
            # Get item and widget
            item = self._items[index]
            widget = self._item_widgets.get(index)
            
            # Remove from data structures
            self._items.pop(index)
            if widget:
                self.remove_child(widget.widget_id)
                del self._item_widgets[index]
                del self._widget_items[widget.widget_id]
                self._rendered_items.discard(index)
                
            # Remove item metadata
            self._item_data.pop(index, None)
            
            # Update widget mappings for items after removal point
            self._update_widget_mappings_after_remove(index)
            
            # Update selection and focus
            self._update_selection_after_remove(index)
            self._update_focus_after_remove(index)
            
            # Update virtual scroll info
            self._virtual_scroll.total_items = len(self._items)
            
            # Trigger layout update
            self._schedule_layout()
            
            # Fire event
            change = CollectionChange(
                event_type=CollectionEvent.ITEM_REMOVED,
                item=widget,
                index=index,
                old_value=item
            )
            self._fire_event(change)
            
            return item
            
    def move_item(self, from_index: int, to_index: int) -> bool:
        """Move an item from one position to another."""
        with self._lock:
            if not (0 <= from_index < len(self._items) and 0 <= to_index < len(self._items)):
                return False
                
            if from_index == to_index:
                return True
                
            # Get item and widget
            item = self._items[from_index]
            widget = self._item_widgets.get(from_index)
            
            # Remove from old position
            self._items.pop(from_index)
            if widget:
                del self._item_widgets[from_index]
                del self._widget_items[widget.widget_id]
                self._rendered_items.discard(from_index)
                
            # Adjust target index if necessary
            if to_index > from_index:
                to_index -= 1
                
            # Insert at new position
            self._items.insert(to_index, item)
            
            # Update all widget mappings
            self._rebuild_widget_mappings()
            
            # Re-add widget if in visible range
            if widget and self._should_render_item(to_index):
                self._item_widgets[to_index] = widget
                self._widget_items[widget.widget_id] = to_index
                self._rendered_items.add(to_index)
                
            # Update selection and focus
            self._update_selection_after_move(from_index, to_index)
            self._update_focus_after_move(from_index, to_index)
            
            # Trigger layout update
            self._schedule_layout()
            
            # Fire event
            change = CollectionChange(
                event_type=CollectionEvent.ITEM_MOVED,
                item=widget,
                old_index=from_index,
                new_index=to_index,
                new_value=item
            )
            self._fire_event(change)
            
            return True
            
    def clear_items(self) -> None:
        """Clear all items from the collection."""
        with self._lock:
            # Remove all widgets
            for widget in self._item_widgets.values():
                self.remove_child(widget.widget_id)
                
            # Clear data structures
            self._items.clear()
            self._item_widgets.clear()
            self._widget_items.clear()
            self._item_data.clear()
            self._rendered_items.clear()
            self._selected_indices.clear()
            self._focused_index = None
            self._last_selected_index = None
            
            # Reset virtual scroll
            self._virtual_scroll.total_items = 0
            self._virtual_scroll.visible_start = 0
            self._virtual_scroll.visible_end = 0
            
            # Fire event
            change = CollectionChange(event_type=CollectionEvent.COLLECTION_CLEARED)
            self._fire_event(change)
            
    def get_item(self, index: int) -> Optional[T]:
        """Get an item by index."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
        
    def get_item_widget(self, index: int) -> Optional[Widget]:
        """Get the widget for an item by index."""
        return self._item_widgets.get(index)
        
    def find_item_index(self, item: T) -> Optional[int]:
        """Find the index of an item."""
        try:
            return self._items.index(item)
        except ValueError:
            return None
            
    def find_widget_index(self, widget_id: str) -> Optional[int]:
        """Find the index of a widget by ID."""
        return self._widget_items.get(widget_id)
        
    # Selection management
    def set_selection(self, indices: Union[int, Set[int], List[int]]) -> None:
        """Set the selected item indices."""
        with self._lock:
            if isinstance(indices, int):
                indices = {indices}
            elif isinstance(indices, list):
                indices = set(indices)
                
            old_selection = self._selected_indices.copy()
            
            # Filter valid indices based on selection mode
            if self._config.selection_mode == SelectionMode.NONE:
                self._selected_indices = set()
            elif self._config.selection_mode == SelectionMode.SINGLE:
                if indices:
                    valid_index = next(iter(i for i in indices if 0 <= i < len(self._items)), None)
                    self._selected_indices = {valid_index} if valid_index is not None else set()
                else:
                    self._selected_indices = set()
            else:  # MULTIPLE or RANGE
                self._selected_indices = {i for i in indices if 0 <= i < len(self._items)}
                
            if old_selection != self._selected_indices:
                # Update last selected for range selection
                if self._selected_indices:
                    self._last_selected_index = max(self._selected_indices)
                    
                change = CollectionChange(
                    event_type=CollectionEvent.SELECTION_CHANGED,
                    old_value=old_selection,
                    new_value=self._selected_indices.copy()
                )
                self._fire_event(change)
                
    def add_to_selection(self, index: int) -> None:
        """Add an index to the selection."""
        if self._config.selection_mode in (SelectionMode.MULTIPLE, SelectionMode.RANGE):
            current = self._selected_indices.copy()
            current.add(index)
            self.set_selection(current)
        else:
            self.set_selection(index)
            
    def remove_from_selection(self, index: int) -> None:
        """Remove an index from the selection."""
        if index in self._selected_indices:
            current = self._selected_indices.copy()
            current.remove(index)
            self.set_selection(current)
            
    def select_range(self, start_index: int, end_index: int) -> None:
        """Select a range of items."""
        if self._config.selection_mode == SelectionMode.RANGE:
            start = min(start_index, end_index)
            end = max(start_index, end_index)
            indices = set(range(start, end + 1))
            self.set_selection(indices)
            
    def clear_selection(self) -> None:
        """Clear all selection."""
        self.set_selection(set())
        
    # Focus management
    def set_focus(self, index: Optional[int]) -> None:
        """Set the focused item index."""
        with self._lock:
            if index is not None and not (0 <= index < len(self._items)):
                return
                
            old_focus = self._focused_index
            self._focused_index = index
            
            if old_focus != self._focused_index:
                change = CollectionChange(
                    event_type=CollectionEvent.FOCUS_CHANGED,
                    index=self._focused_index,
                    old_value=old_focus,
                    new_value=self._focused_index
                )
                self._fire_event(change)
                
    def focus_next(self) -> bool:
        """Focus the next item."""
        if self._focused_index is None:
            if self._items:
                self.set_focus(0)
                return True
        elif self._focused_index < len(self._items) - 1:
            self.set_focus(self._focused_index + 1)
            return True
        return False
        
    def focus_previous(self) -> bool:
        """Focus the previous item."""
        if self._focused_index is None:
            if self._items:
                self.set_focus(len(self._items) - 1)
                return True
        elif self._focused_index > 0:
            self.set_focus(self._focused_index - 1)
            return True
        return False
        
    # Reactive data binding
    def bind_reactive_data(self, reactive_data: ReactiveValue) -> None:
        """Bind collection to reactive data source."""
        with self._lock:
            if self._reactive_data:
                self._reactive_data.unbind(self._on_reactive_data_changed)
                
            self._reactive_data = reactive_data
            self._reactive_binding_active = True
            reactive_data.bind(self._on_reactive_data_changed)
            
            # Initial sync
            self._sync_from_reactive_data()
            
    def unbind_reactive_data(self) -> None:
        """Unbind from reactive data source."""
        with self._lock:
            if self._reactive_data:
                self._reactive_data.unbind(self._on_reactive_data_changed)
                self._reactive_data = None
                self._reactive_binding_active = False
                
    def _on_reactive_data_changed(self, change: ReactiveChange) -> None:
        """Handle reactive data changes."""
        if self._reactive_binding_active:
            self._sync_from_reactive_data()
            
    def _sync_from_reactive_data(self) -> None:
        """Sync collection from reactive data source."""
        if not self._reactive_data:
            return
            
        data = self._reactive_data.value
        if isinstance(data, list):
            # Clear and rebuild collection
            self.clear_items()
            for item in data:
                self.add_item(item)
        elif isinstance(data, dict):
            # Handle dictionary data
            self.clear_items()
            for key, value in data.items():
                self.add_item(value)
                
    # Virtual scrolling and performance
    def _should_render_item(self, index: int) -> bool:
        """Check if an item should be rendered."""
        if not self._config.virtual_scrolling:
            return True
            
        # Check if item is in visible range with buffer
        buffer = self._virtual_scroll.buffer_size
        start = max(0, self._virtual_scroll.visible_start - buffer)
        end = min(len(self._items), self._virtual_scroll.visible_end + buffer)
        
        return start <= index < end
        
    def update_virtual_scroll(self, scroll_offset: int, viewport_height: int) -> None:
        """Update virtual scrolling parameters."""
        with self._lock:
            self._virtual_scroll.scroll_offset = scroll_offset
            self._virtual_scroll.viewport_height = viewport_height
            
            # Calculate visible range
            item_height = self._config.item_height
            visible_start = max(0, scroll_offset // item_height)
            visible_count = (viewport_height // item_height) + 2  # +2 for partial items
            visible_end = min(len(self._items), visible_start + visible_count)
            
            old_start = self._virtual_scroll.visible_start
            old_end = self._virtual_scroll.visible_end
            
            self._virtual_scroll.visible_start = visible_start
            self._virtual_scroll.visible_end = visible_end
            
            # Update rendered items if range changed
            if old_start != visible_start or old_end != visible_end:
                self._update_rendered_items()
                
    def _update_rendered_items(self) -> None:
        """Update which items are rendered based on virtual scrolling."""
        if not self._config.virtual_scrolling:
            return
            
        # Determine which items should be rendered
        should_render = set()
        for i in range(len(self._items)):
            if self._should_render_item(i):
                should_render.add(i)
                
        # Remove items that shouldn't be rendered
        to_remove = self._rendered_items - should_render
        for index in to_remove:
            widget = self._item_widgets.get(index)
            if widget:
                self.remove_child(widget.widget_id)
                del self._item_widgets[index]
                del self._widget_items[widget.widget_id]
                
        # Add items that should be rendered
        to_add = should_render - self._rendered_items
        for index in to_add:
            if index < len(self._items):
                item = self._items[index]
                widget = self._create_item_widget(item, index)
                self._item_widgets[index] = widget
                self._widget_items[widget.widget_id] = index
                self.add_child(widget)
                
        self._rendered_items = should_render
        
        # Trigger layout update
        self._schedule_layout()
        
    # Layout management
    def _schedule_layout(self) -> None:
        """Schedule a layout update."""
        if not self._layout_pending and self._config.auto_layout:
            self._layout_pending = True
            # Use a simple immediate layout for now
            # In a real implementation, this might be deferred
            self._perform_layout()
            
    def _perform_layout(self) -> None:
        """Perform the actual layout."""
        if not self._layout_pending:
            return
            
        start_time = time.time()
        
        try:
            self._layout_items()
            self._layout_count += 1
            
            # Fire layout changed event
            change = CollectionChange(event_type=CollectionEvent.LAYOUT_CHANGED)
            self._fire_event(change)
            
        finally:
            self._layout_pending = False
            self._last_layout_time = time.time() - start_time
            
    # Event handling
    def add_event_handler(self, event_type: CollectionEvent, 
                         handler: Callable[[CollectionChange], None]) -> None:
        """Add an event handler for collection events."""
        self._event_handlers[event_type].add(handler)
        
    def remove_event_handler(self, event_type: CollectionEvent,
                           handler: Callable[[CollectionChange], None]) -> None:
        """Remove an event handler."""
        self._event_handlers[event_type].discard(handler)
        
    def _fire_event(self, change: CollectionChange) -> None:
        """Fire a collection event."""
        for handler in self._event_handlers[change.event_type].copy():
            try:
                handler(change)
            except Exception as e:
                print(f"Error in collection event handler: {e}")
                
    # Item factory and customization
    def set_item_factory(self, factory: Callable[[T, int], Widget]) -> None:
        """Set a custom item factory function."""
        self._item_factory = factory
        
    def set_item_configurator(self, configurator: Callable[[Widget, T, int], None]) -> None:
        """Set a custom item configurator function."""
        self._item_configurator = configurator
        
    # Utility methods
    def _update_widget_mappings_after_insert(self, insert_index: int) -> None:
        """Update widget mappings after item insertion."""
        new_item_widgets = {}
        new_widget_items = {}
        
        for index, widget in self._item_widgets.items():
            if index >= insert_index:
                new_index = index + 1
                new_item_widgets[new_index] = widget
                new_widget_items[widget.widget_id] = new_index
            else:
                new_item_widgets[index] = widget
                new_widget_items[widget.widget_id] = index
                
        self._item_widgets = new_item_widgets
        self._widget_items = new_widget_items
        
        # Update rendered items set
        new_rendered = set()
        for index in self._rendered_items:
            if index >= insert_index:
                new_rendered.add(index + 1)
            else:
                new_rendered.add(index)
        self._rendered_items = new_rendered
        
    def _update_widget_mappings_after_remove(self, remove_index: int) -> None:
        """Update widget mappings after item removal."""
        new_item_widgets = {}
        new_widget_items = {}
        
        for index, widget in self._item_widgets.items():
            if index > remove_index:
                new_index = index - 1
                new_item_widgets[new_index] = widget
                new_widget_items[widget.widget_id] = new_index
            elif index < remove_index:
                new_item_widgets[index] = widget
                new_widget_items[widget.widget_id] = index
                
        self._item_widgets = new_item_widgets
        self._widget_items = new_widget_items
        
        # Update rendered items set
        new_rendered = set()
        for index in self._rendered_items:
            if index > remove_index:
                new_rendered.add(index - 1)
            elif index < remove_index:
                new_rendered.add(index)
        self._rendered_items = new_rendered
        
    def _rebuild_widget_mappings(self) -> None:
        """Rebuild all widget mappings after major changes."""
        new_item_widgets = {}
        new_widget_items = {}
        new_rendered = set()
        
        # Rebuild mappings based on current widget positions
        for widget_id, old_index in list(self._widget_items.items()):
            widget = self._item_widgets.get(old_index)
            if widget and old_index < len(self._items):
                # Find new index for this widget's item
                # This is a simplified approach - in practice, you might need
                # more sophisticated tracking
                new_item_widgets[old_index] = widget
                new_widget_items[widget_id] = old_index
                new_rendered.add(old_index)
                
        self._item_widgets = new_item_widgets
        self._widget_items = new_widget_items
        self._rendered_items = new_rendered
        
    def _update_selection_after_remove(self, remove_index: int) -> None:
        """Update selection after item removal."""
        new_selection = set()
        for index in self._selected_indices:
            if index < remove_index:
                new_selection.add(index)
            elif index > remove_index:
                new_selection.add(index - 1)
                
        if new_selection != self._selected_indices:
            self.set_selection(new_selection)
            
    def _update_focus_after_remove(self, remove_index: int) -> None:
        """Update focus after item removal."""
        if self._focused_index is not None:
            if self._focused_index == remove_index:
                # Focus was on removed item, move to next available
                if remove_index < len(self._items):
                    self.set_focus(remove_index)
                elif len(self._items) > 0:
                    self.set_focus(len(self._items) - 1)
                else:
                    self.set_focus(None)
            elif self._focused_index > remove_index:
                self.set_focus(self._focused_index - 1)
                
    def _update_selection_after_move(self, from_index: int, to_index: int) -> None:
        """Update selection after item move."""
        if from_index in self._selected_indices:
            new_selection = self._selected_indices.copy()
            new_selection.remove(from_index)
            new_selection.add(to_index)
            self.set_selection(new_selection)
            
    def _update_focus_after_move(self, from_index: int, to_index: int) -> None:
        """Update focus after item move."""
        if self._focused_index == from_index:
            self.set_focus(to_index)
            
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'item_count': len(self._items),
            'rendered_items': len(self._rendered_items),
            'layout_count': self._layout_count,
            'last_layout_time': self._last_layout_time,
            'virtual_scrolling': self._config.virtual_scrolling,
            'selection_count': len(self._selected_indices),
            'focused_index': self._focused_index
        }
        
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(id={self.widget_id}, "
                f"items={len(self._items)}, "
                f"selected={len(self._selected_indices)}, "
                f"layout={self._config.layout_type.value})") 