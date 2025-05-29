#!/usr/bin/env python3
"""
Text Widget Implementation

Provides text rendering with reactive data binding, font management,
and comprehensive styling support for the tinyDisplay framework.
"""

from typing import Union, Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time

from .base import Widget, ReactiveValue, WidgetBounds
from ..core.reactive import ReactiveDataManager


class TextAlignment(Enum):
    """Text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class TextWrap(Enum):
    """Text wrapping options."""
    NONE = "none"
    WORD = "word"
    CHAR = "char"
    ELLIPSIS = "ellipsis"


@dataclass
class FontStyle:
    """Font styling configuration."""
    family: str = "default"
    size: int = 12
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: Tuple[int, int, int] = (255, 255, 255)
    background_color: Optional[Tuple[int, int, int]] = None
    
    def __post_init__(self):
        """Validate font style parameters."""
        if self.size <= 0:
            raise ValueError("Font size must be positive")
        if not all(0 <= c <= 255 for c in self.color):
            raise ValueError("Color values must be between 0 and 255")
        if self.background_color and not all(0 <= c <= 255 for c in self.background_color):
            raise ValueError("Background color values must be between 0 and 255")


@dataclass
class TextLayout:
    """Text layout configuration."""
    alignment: TextAlignment = TextAlignment.LEFT
    wrap: TextWrap = TextWrap.WORD
    line_spacing: float = 1.0
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0)  # top, right, bottom, left
    max_lines: Optional[int] = None
    
    def __post_init__(self):
        """Validate layout parameters."""
        if self.line_spacing <= 0:
            raise ValueError("Line spacing must be positive")
        if not all(p >= 0 for p in self.padding):
            raise ValueError("Padding values must be non-negative")


class FontCache:
    """Font caching system for performance optimization."""
    
    def __init__(self, max_cache_size: int = 50):
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        self._max_cache_size = max_cache_size
        self._lock = threading.RLock()
    
    def get_font(self, font_style: FontStyle) -> Any:
        """Get cached font or create new one."""
        cache_key = self._get_cache_key(font_style)
        
        with self._lock:
            if cache_key in self._cache:
                self._access_times[cache_key] = time.time()
                return self._cache[cache_key]
            
            # Create new font (implementation would depend on rendering backend)
            font = self._create_font(font_style)
            
            # Add to cache
            self._add_to_cache(cache_key, font)
            return font
    
    def _get_cache_key(self, font_style: FontStyle) -> str:
        """Generate cache key for font style."""
        return f"{font_style.family}_{font_style.size}_{font_style.bold}_{font_style.italic}"
    
    def _create_font(self, font_style: FontStyle) -> Any:
        """Create font object - placeholder for actual implementation."""
        # This would integrate with the actual rendering backend
        return {
            'family': font_style.family,
            'size': font_style.size,
            'bold': font_style.bold,
            'italic': font_style.italic
        }
    
    def _add_to_cache(self, cache_key: str, font: Any) -> None:
        """Add font to cache with LRU eviction."""
        if len(self._cache) >= self._max_cache_size:
            # Remove least recently used font
            oldest_key = min(self._access_times.keys(), 
                           key=lambda k: self._access_times[k])
            del self._cache[oldest_key]
            del self._access_times[oldest_key]
        
        self._cache[cache_key] = font
        self._access_times[cache_key] = time.time()
    
    def clear_cache(self) -> None:
        """Clear the font cache."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


# Global font cache instance
_font_cache = FontCache()


class TextWidget(Widget):
    """Text widget with reactive data binding and comprehensive styling.
    
    Supports dynamic text content, font styling, layout options, and
    automatic re-rendering when bound data changes.
    
    Args:
        text: Initial text content or reactive value
        font_style: Font styling configuration
        layout: Text layout configuration
        **kwargs: Additional widget arguments
        
    Example:
        >>> widget = TextWidget("Hello World", 
        ...                     font_style=FontStyle(size=16, bold=True),
        ...                     layout=TextLayout(alignment=TextAlignment.CENTER))
        >>> widget.bind_data("text", reactive_data_source)
    """
    
    __slots__ = (
        '_text', '_font_style', '_layout', '_rendered_lines', 
        '_text_bounds', '_needs_layout', '_last_layout_size'
    )
    
    def __init__(
        self,
        text: Union[str, ReactiveValue] = "",
        font_style: Optional[FontStyle] = None,
        layout: Optional[TextLayout] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        
        # Text content
        self._text = self._ensure_reactive(text)
        self._text.bind(self._on_text_changed)
        
        # Styling and layout
        self._font_style = font_style or FontStyle()
        self._layout = layout or TextLayout()
        
        # Layout state
        self._rendered_lines: list[str] = []
        self._text_bounds: Optional[WidgetBounds] = None
        self._needs_layout = True
        self._last_layout_size: Optional[Tuple[int, int]] = None
        
        # Bind to size changes for re-layout
        self._size.bind(self._on_size_changed)
    
    @property
    def text(self) -> str:
        """Get current text content."""
        return self._text.value
    
    @text.setter
    def text(self, value: Union[str, ReactiveValue]) -> None:
        """Set text content."""
        if isinstance(value, ReactiveValue):
            self._text.unbind(self._on_text_changed)
            self._text = value
            self._text.bind(self._on_text_changed)
        else:
            self._text.value = value
        self._needs_layout = True
        self._mark_dirty()
    
    @property
    def font_style(self) -> FontStyle:
        """Get current font style."""
        return self._font_style
    
    @font_style.setter
    def font_style(self, style: FontStyle) -> None:
        """Set font style."""
        self._font_style = style
        self._needs_layout = True
        self._mark_dirty()
    
    @property
    def layout(self) -> TextLayout:
        """Get current layout configuration."""
        return self._layout
    
    @layout.setter
    def layout(self, layout: TextLayout) -> None:
        """Set layout configuration."""
        self._layout = layout
        self._needs_layout = True
        self._mark_dirty()
    
    def set_text_color(self, color: Tuple[int, int, int]) -> None:
        """Set text color."""
        self._font_style.color = color
        self._mark_dirty()
    
    def set_font_size(self, size: int) -> None:
        """Set font size."""
        if size <= 0:
            raise ValueError("Font size must be positive")
        self._font_style.size = size
        self._needs_layout = True
        self._mark_dirty()
    
    def set_alignment(self, alignment: TextAlignment) -> None:
        """Set text alignment."""
        self._layout.alignment = alignment
        self._needs_layout = True
        self._mark_dirty()
    
    def get_text_bounds(self) -> Optional[WidgetBounds]:
        """Get the bounds of the rendered text."""
        if self._needs_layout:
            self._calculate_layout()
        return self._text_bounds
    
    def get_line_count(self) -> int:
        """Get the number of rendered lines."""
        if self._needs_layout:
            self._calculate_layout()
        return len(self._rendered_lines)
    
    def render(self, canvas: 'Canvas') -> None:
        """Render the text widget to the canvas."""
        if not self.visible or self.alpha <= 0:
            return
        
        # Calculate layout if needed
        if self._needs_layout:
            self._calculate_layout()
        
        # Get font from cache
        font = _font_cache.get_font(self._font_style)
        
        # Render background if specified
        if self._font_style.background_color:
            self._render_background(canvas)
        
        # Render text lines
        self._render_text_lines(canvas, font)
        
        # Mark as clean
        self.mark_clean()
    
    def _ensure_reactive(self, value: Union[str, ReactiveValue]) -> ReactiveValue:
        """Convert string values to ReactiveValue instances."""
        if isinstance(value, ReactiveValue):
            return value
        return ReactiveValue(value)
    
    def _on_text_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive text updates."""
        self._needs_layout = True
        self._mark_dirty()
    
    def _on_size_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle size changes that require re-layout."""
        self._needs_layout = True
        self._mark_dirty()
    
    def _calculate_layout(self) -> None:
        """Calculate text layout and line wrapping."""
        if not self._needs_layout:
            return
        
        current_size = self.size
        text_content = str(self._text.value)
        
        # Clear previous layout
        self._rendered_lines.clear()
        
        if not text_content:
            self._text_bounds = WidgetBounds(0, 0, 0, 0)
            self._needs_layout = False
            return
        
        # Calculate available space
        padding = self._layout.padding
        available_width = current_size[0] - padding[1] - padding[3]  # right + left
        available_height = current_size[1] - padding[0] - padding[2]  # top + bottom
        
        if available_width <= 0 or available_height <= 0:
            self._text_bounds = WidgetBounds(0, 0, 0, 0)
            self._needs_layout = False
            return
        
        # Perform text wrapping
        self._wrap_text(text_content, available_width)
        
        # Calculate text bounds
        self._calculate_text_bounds()
        
        self._needs_layout = False
        self._last_layout_size = current_size
    
    def _wrap_text(self, text: str, available_width: int) -> None:
        """Wrap text according to layout configuration."""
        if self._layout.wrap == TextWrap.NONE:
            self._rendered_lines = text.split('\n')
        elif self._layout.wrap == TextWrap.WORD:
            self._wrap_by_words(text, available_width)
        elif self._layout.wrap == TextWrap.CHAR:
            self._wrap_by_characters(text, available_width)
        elif self._layout.wrap == TextWrap.ELLIPSIS:
            self._wrap_with_ellipsis(text, available_width)
        
        # Apply max lines limit
        if self._layout.max_lines and len(self._rendered_lines) > self._layout.max_lines:
            self._rendered_lines = self._rendered_lines[:self._layout.max_lines]
            if self._layout.wrap == TextWrap.ELLIPSIS and self._rendered_lines:
                # Add ellipsis to last line
                last_line = self._rendered_lines[-1]
                if len(last_line) > 3:
                    self._rendered_lines[-1] = last_line[:-3] + "..."
    
    def _wrap_by_words(self, text: str, available_width: int) -> None:
        """Wrap text by word boundaries."""
        lines = text.split('\n')
        self._rendered_lines = []
        
        for line in lines:
            if not line:
                self._rendered_lines.append("")
                continue
            
            words = line.split()
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                
                # Estimate if line fits (simplified - real implementation would measure text)
                if self._estimate_text_width(test_line) <= available_width:
                    current_line = test_line
                else:
                    if current_line:
                        self._rendered_lines.append(current_line)
                        current_line = word
                    else:
                        # Single word is too long, force it
                        self._rendered_lines.append(word)
            
            if current_line:
                self._rendered_lines.append(current_line)
    
    def _wrap_by_characters(self, text: str, available_width: int) -> None:
        """Wrap text by character boundaries."""
        lines = text.split('\n')
        self._rendered_lines = []
        
        for line in lines:
            while line:
                # Find maximum characters that fit
                max_chars = self._find_max_chars_that_fit(line, available_width)
                if max_chars <= 0:
                    max_chars = 1  # Always include at least one character
                
                self._rendered_lines.append(line[:max_chars])
                line = line[max_chars:]
    
    def _wrap_with_ellipsis(self, text: str, available_width: int) -> None:
        """Wrap text with ellipsis for overflow."""
        lines = text.split('\n')
        self._rendered_lines = []
        
        for line in lines:
            if self._estimate_text_width(line) <= available_width:
                self._rendered_lines.append(line)
            else:
                # Find maximum characters that fit with ellipsis
                ellipsis = "..."
                max_chars = self._find_max_chars_that_fit(
                    line + ellipsis, available_width
                ) - len(ellipsis)
                
                if max_chars > 0:
                    self._rendered_lines.append(line[:max_chars] + ellipsis)
                else:
                    self._rendered_lines.append(ellipsis)
    
    def _estimate_text_width(self, text: str) -> int:
        """Estimate text width - simplified implementation."""
        # This is a simplified estimation - real implementation would use font metrics
        char_width = self._font_style.size * 0.6  # Rough approximation
        return int(len(text) * char_width)
    
    def _find_max_chars_that_fit(self, text: str, available_width: int) -> int:
        """Find maximum number of characters that fit in available width."""
        if not text:
            return 0
        
        # Binary search for optimal character count
        left, right = 0, len(text)
        
        while left < right:
            mid = (left + right + 1) // 2
            if self._estimate_text_width(text[:mid]) <= available_width:
                left = mid
            else:
                right = mid - 1
        
        return left
    
    def _calculate_text_bounds(self) -> None:
        """Calculate the bounds of the rendered text."""
        if not self._rendered_lines:
            self._text_bounds = WidgetBounds(0, 0, 0, 0)
            return
        
        # Calculate text dimensions
        line_height = int(self._font_style.size * self._layout.line_spacing)
        total_height = len(self._rendered_lines) * line_height
        
        max_width = 0
        for line in self._rendered_lines:
            line_width = self._estimate_text_width(line)
            max_width = max(max_width, line_width)
        
        # Calculate position based on alignment and padding
        padding = self._layout.padding
        x = self.position[0] + padding[3]  # left padding
        y = self.position[1] + padding[0]  # top padding
        
        # Adjust x position for alignment
        available_width = self.size[0] - padding[1] - padding[3]
        if self._layout.alignment == TextAlignment.CENTER:
            x += (available_width - max_width) // 2
        elif self._layout.alignment == TextAlignment.RIGHT:
            x += available_width - max_width
        
        self._text_bounds = WidgetBounds(x, y, max_width, total_height)
    
    def _render_background(self, canvas: 'Canvas') -> None:
        """Render background color if specified."""
        if not self._font_style.background_color:
            return
        
        # This would integrate with the actual canvas rendering backend
        # For now, it's a placeholder
        pass
    
    def _render_text_lines(self, canvas: 'Canvas', font: Any) -> None:
        """Render the text lines to the canvas."""
        if not self._rendered_lines or not self._text_bounds:
            return
        
        line_height = int(self._font_style.size * self._layout.line_spacing)
        current_y = self._text_bounds.y
        
        for line in self._rendered_lines:
            if not line:
                current_y += line_height
                continue
            
            # Calculate line position based on alignment
            line_x = self._calculate_line_x_position(line)
            
            # Render line (placeholder - would integrate with actual canvas)
            self._render_line(canvas, line, line_x, current_y, font)
            
            current_y += line_height
    
    def _calculate_line_x_position(self, line: str) -> int:
        """Calculate x position for a line based on alignment."""
        if not self._text_bounds:
            return 0
        
        base_x = self._text_bounds.x
        
        if self._layout.alignment == TextAlignment.LEFT:
            return base_x
        
        line_width = self._estimate_text_width(line)
        available_width = self.size[0] - self._layout.padding[1] - self._layout.padding[3]
        
        if self._layout.alignment == TextAlignment.CENTER:
            return base_x + (available_width - line_width) // 2
        elif self._layout.alignment == TextAlignment.RIGHT:
            return base_x + available_width - line_width
        
        return base_x
    
    def _render_line(self, canvas: 'Canvas', line: str, x: int, y: int, font: Any) -> None:
        """Render a single line of text."""
        # This is a placeholder for actual text rendering
        # Real implementation would integrate with the canvas rendering backend
        pass
    
    def __repr__(self) -> str:
        return (f"TextWidget(id={self.widget_id}, text='{self.text[:20]}...', "
                f"font_size={self._font_style.size}, visible={self.visible})") 