#!/usr/bin/env python3
"""
Custom Widgets Module
Contains widgets grouped by functionality: custom
"""

from widgets.base import Widget, Makeanimation
from typing import List, Dict, Any

class CustomWidgets:
    """Widget module for custom functionality"""
    
    def __init__(self):
        self.widgets: List[Widget] = []
        self._initialize_widgets()
    
    def _initialize_widgets(self):
        """Initialize all widgets in this module"""
        self.makeanimation = Makeanimation()
        
        # Add all widgets to the module
        for widget_name in dir(self):
            widget = getattr(self, widget_name)
            if isinstance(widget, Widget):
                self.widgets.append(widget)
    
    def add(self, widget: Widget):
        """Add a widget to this module"""
        self.widgets.append(widget)
    
    def get_widget(self, name: str) -> Widget:
        """Get widget by name"""
        return getattr(self, name, None)
    
    def render_all(self):
        """Render all widgets in this module"""
        for widget in self.widgets:
            widget.render()
    
    def get_widgets_by_type(self, widget_type: str) -> List[Widget]:
        """Get all widgets of a specific type"""
        return [w for w in self.widgets if w.__class__.__name__.lower() == widget_type.lower()]