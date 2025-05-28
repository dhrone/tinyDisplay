#!/usr/bin/env python3
"""
Canvas Manager for Multi-Canvas tinyDisplay Applications
Handles multiple canvases and their coordination
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from widgets.base import Widget

@dataclass
class Canvas:
    """Canvas configuration"""
    name: str
    width: int
    height: int
    widgets: List[Widget]
    is_primary: bool = False
    z_order: int = 0

class CanvasManager:
    """Manages multiple canvases in complex applications"""
    
    def __init__(self):
        self.canvases: Dict[str, Canvas] = {}
        self.primary_canvas: Optional[Canvas] = None
    
    def create_canvas(self, name: str, width: int, height: int, is_primary: bool = False) -> Canvas:
        """Create a new canvas"""
        canvas = Canvas(
            name=name,
            width=width,
            height=height,
            widgets=[],
            is_primary=is_primary
        )
        
        self.canvases[name] = canvas
        if is_primary:
            self.primary_canvas = canvas
        
        return canvas
    
    def get_canvas(self, name: str) -> Optional[Canvas]:
        """Get canvas by name"""
        return self.canvases.get(name)
    
    def add_widget_to_canvas(self, canvas_name: str, widget: Widget):
        """Add widget to specific canvas"""
        if canvas_name in self.canvases:
            self.canvases[canvas_name].widgets.append(widget)
    
    def render_all(self):
        """Render all canvases"""
        for canvas in self.canvases.values():
            self._render_canvas(canvas)
    
    def _render_canvas(self, canvas: Canvas):
        """Render a specific canvas"""
        # Implementation for canvas rendering
        pass
    
    def run(self):
        """Run the canvas manager"""
        self.render_all()
