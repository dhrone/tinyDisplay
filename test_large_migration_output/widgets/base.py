"""
Base widget classes for the new reactive architecture.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Set, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RenderResult:
    """Result of widget rendering"""
    content: Any
    position: Tuple[int, int]
    size: Tuple[int, int]
    changed: bool = True
    render_time: float = 0

@dataclass
class RenderContext:
    """Context provided to widgets during rendering"""
    timestamp: float
    data_manager: Any
    dynamic_values_engine: Any
    display_config: Dict[str, Any]

class ReactiveWidget(ABC):
    """Base class for reactive widgets"""
    
    def __init__(self, widget_id: str, config: Dict[str, Any]):
        self.widget_id = widget_id
        self.config = config
        self.subscriptions: Set[str] = set()
        self.is_dirty = True
        self.last_render_time = 0
        self.render_cache: Optional[RenderResult] = None
        self.position = config.get('position', (0, 0))
        self.size = config.get('size', (100, 20))
        self.visible = config.get('visible', True)
    
    def subscribe_to_data(self, data_path: str) -> None:
        """Subscribe to data changes"""
        if data_path not in self.subscriptions:
            self.subscriptions.add(data_path)
    
    def subscribe_to_dynamic_value(self, dv_name: str) -> None:
        """Subscribe to dynamic value changes"""
        if dv_name not in self.subscriptions:
            self.subscriptions.add(f"dv:{dv_name}")
    
    def invalidate(self) -> None:
        """Mark widget as needing re-render"""
        self.is_dirty = True
        self.render_cache = None
    
    def is_visible(self) -> bool:
        """Check if widget is visible"""
        return self.visible
    
    @abstractmethod
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render widget content"""
        pass
    
    def cleanup(self) -> None:
        """Cleanup subscriptions"""
        self.subscriptions.clear()

class TextWidget(ReactiveWidget):
    """Text display widget"""
    
    def __init__(self, widget_id: str, config: Dict[str, Any]):
        super().__init__(widget_id, config)
        self.text_source = config.get('text_source')
        self.font_size = config.get('font_size', 12)
        self.color = config.get('color', 'white')
        
        if self.text_source:
            self.subscribe_to_dynamic_value(self.text_source)
    
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render text widget"""
        
        # Get text from dynamic value
        text = ""
        if self.text_source:
            text = context.dynamic_values_engine.get_value(self.text_source, timestamp)
        
        result = RenderResult(
            content={'text': str(text), 'font_size': self.font_size, 'color': self.color},
            position=self.position,
            size=self.size,
            changed=self.is_dirty,
            render_time=timestamp
        )
        
        self.is_dirty = False
        self.last_render_time = timestamp
        self.render_cache = result
        
        return result

class ImageWidget(ReactiveWidget):
    """Image display widget"""
    
    def __init__(self, widget_id: str, config: Dict[str, Any]):
        super().__init__(widget_id, config)
        self.image_source = config.get('image_source')
        
        if self.image_source:
            self.subscribe_to_dynamic_value(self.image_source)
    
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render image widget"""
        
        # Get image path from dynamic value
        image_path = ""
        if self.image_source:
            image_path = context.dynamic_values_engine.get_value(self.image_source, timestamp)
        
        result = RenderResult(
            content={'image_path': str(image_path)},
            position=self.position,
            size=self.size,
            changed=self.is_dirty,
            render_time=timestamp
        )
        
        self.is_dirty = False
        self.last_render_time = timestamp
        self.render_cache = result
        
        return result
