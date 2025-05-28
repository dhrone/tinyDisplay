#!/usr/bin/env python3
"""
Container Layout Manager
Handles container layout for widget hierarchies
"""

from typing import List, Dict, Any
from widgets.base import Widget

class ContainerLayout:
    """Layout manager for container layouts"""
    
    def __init__(self, properties: Dict[str, Any] = None):
        self.properties = properties or {}
    
    def apply_layout(self, widgets: List[Widget]):
        """Apply container layout to widgets"""
        if not widgets:
            return
        
        # Implementation specific to container layout
        if "container" == "container":
            self._apply_container_layout(widgets)
        elif "container" == "group":
            self._apply_group_layout(widgets)
        else:
            self._apply_default_layout(widgets)
    
    def _apply_container_layout(self, widgets: List[Widget]):
        """Apply container layout"""
        # Stack widgets vertically with padding
        y_offset = 0
        padding = self.properties.get('padding', 10)
        
        for widget in widgets:
            widget.position(0, y_offset)
            y_offset += widget.height + padding
    
    def _apply_group_layout(self, widgets: List[Widget]):
        """Apply group layout"""
        # Arrange widgets in a grid
        cols = self.properties.get('columns', 2)
        spacing = self.properties.get('spacing', 5)
        
        for i, widget in enumerate(widgets):
            row = i // cols
            col = i % cols
            x = col * (widget.width + spacing)
            y = row * (widget.height + spacing)
            widget.position(x, y)
    
    def _apply_default_layout(self, widgets: List[Widget]):
        """Apply default layout"""
        # Simple horizontal layout
        x_offset = 0
        spacing = self.properties.get('spacing', 5)
        
        for widget in widgets:
            widget.position(x_offset, 0)
            x_offset += widget.width + spacing
