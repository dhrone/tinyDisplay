#!/usr/bin/env python3
"""
Test Suite for TextWidget

Comprehensive tests for text widget functionality including reactive binding,
font styling, layout management, and performance validation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.tinydisplay.widgets.text import (
    TextWidget, FontStyle, TextLayout, TextAlignment, TextWrap, FontCache
)
from src.tinydisplay.widgets.base import ReactiveValue, WidgetBounds


class TestFontStyle:
    """Test FontStyle configuration and validation."""
    
    def test_font_style__default_values__correct_initialization(self):
        """Test FontStyle with default values."""
        style = FontStyle()
        assert style.family == "default"
        assert style.size == 12
        assert style.bold is False
        assert style.italic is False
        assert style.underline is False
        assert style.color == (255, 255, 255)
        assert style.background_color is None
    
    def test_font_style__custom_values__correct_initialization(self):
        """Test FontStyle with custom values."""
        style = FontStyle(
            family="Arial",
            size=16,
            bold=True,
            italic=True,
            color=(128, 128, 128),
            background_color=(0, 0, 0)
        )
        assert style.family == "Arial"
        assert style.size == 16
        assert style.bold is True
        assert style.italic is True
        assert style.color == (128, 128, 128)
        assert style.background_color == (0, 0, 0)
    
    def test_font_style__invalid_size__raises_error(self):
        """Test FontStyle with invalid size raises ValueError."""
        with pytest.raises(ValueError, match="Font size must be positive"):
            FontStyle(size=0)
        
        with pytest.raises(ValueError, match="Font size must be positive"):
            FontStyle(size=-5)
    
    def test_font_style__invalid_color__raises_error(self):
        """Test FontStyle with invalid color raises ValueError."""
        with pytest.raises(ValueError, match="Color values must be between 0 and 255"):
            FontStyle(color=(256, 128, 128))
        
        with pytest.raises(ValueError, match="Color values must be between 0 and 255"):
            FontStyle(color=(-1, 128, 128))
    
    def test_font_style__invalid_background_color__raises_error(self):
        """Test FontStyle with invalid background color raises ValueError."""
        with pytest.raises(ValueError, match="Background color values must be between 0 and 255"):
            FontStyle(background_color=(256, 128, 128))


class TestTextLayout:
    """Test TextLayout configuration and validation."""
    
    def test_text_layout__default_values__correct_initialization(self):
        """Test TextLayout with default values."""
        layout = TextLayout()
        assert layout.alignment == TextAlignment.LEFT
        assert layout.wrap == TextWrap.WORD
        assert layout.line_spacing == 1.0
        assert layout.padding == (0, 0, 0, 0)
        assert layout.max_lines is None
    
    def test_text_layout__custom_values__correct_initialization(self):
        """Test TextLayout with custom values."""
        layout = TextLayout(
            alignment=TextAlignment.CENTER,
            wrap=TextWrap.CHAR,
            line_spacing=1.5,
            padding=(5, 10, 5, 10),
            max_lines=3
        )
        assert layout.alignment == TextAlignment.CENTER
        assert layout.wrap == TextWrap.CHAR
        assert layout.line_spacing == 1.5
        assert layout.padding == (5, 10, 5, 10)
        assert layout.max_lines == 3
    
    def test_text_layout__invalid_line_spacing__raises_error(self):
        """Test TextLayout with invalid line spacing raises ValueError."""
        with pytest.raises(ValueError, match="Line spacing must be positive"):
            TextLayout(line_spacing=0)
        
        with pytest.raises(ValueError, match="Line spacing must be positive"):
            TextLayout(line_spacing=-0.5)
    
    def test_text_layout__invalid_padding__raises_error(self):
        """Test TextLayout with invalid padding raises ValueError."""
        with pytest.raises(ValueError, match="Padding values must be non-negative"):
            TextLayout(padding=(-1, 0, 0, 0))


class TestFontCache:
    """Test FontCache functionality."""
    
    def test_font_cache__initialization__correct_state(self):
        """Test FontCache initialization."""
        cache = FontCache(max_cache_size=10)
        assert len(cache._cache) == 0
        assert len(cache._access_times) == 0
        assert cache._max_cache_size == 10
    
    def test_font_cache__get_font__creates_and_caches(self):
        """Test font creation and caching."""
        cache = FontCache(max_cache_size=5)
        style = FontStyle(family="Arial", size=16, bold=True)
        
        font1 = cache.get_font(style)
        font2 = cache.get_font(style)
        
        # Should return same cached font
        assert font1 is font2
        assert len(cache._cache) == 1
    
    def test_font_cache__lru_eviction__removes_oldest(self):
        """Test LRU eviction when cache is full."""
        cache = FontCache(max_cache_size=2)
        
        style1 = FontStyle(family="Arial", size=12)
        style2 = FontStyle(family="Times", size=14)
        style3 = FontStyle(family="Courier", size=16)
        
        # Fill cache
        cache.get_font(style1)
        cache.get_font(style2)
        assert len(cache._cache) == 2
        
        # Add third font - should evict first
        cache.get_font(style3)
        assert len(cache._cache) == 2
        
        # First font should be evicted
        cache_key1 = cache._get_cache_key(style1)
        assert cache_key1 not in cache._cache
    
    def test_font_cache__clear_cache__empties_cache(self):
        """Test cache clearing."""
        cache = FontCache()
        style = FontStyle(family="Arial", size=16)
        
        cache.get_font(style)
        assert len(cache._cache) == 1
        
        cache.clear_cache()
        assert len(cache._cache) == 0
        assert len(cache._access_times) == 0


class TestTextWidget:
    """Test TextWidget functionality."""
    
    def test_text_widget__initialization__correct_state(self):
        """Test TextWidget initialization with default values."""
        widget = TextWidget()
        
        assert widget.text == ""
        assert isinstance(widget._text, ReactiveValue)
        assert widget._font_style.size == 12
        assert widget._layout.alignment == TextAlignment.LEFT
        assert widget._needs_layout is True
    
    def test_text_widget__initialization_with_string__creates_reactive(self):
        """Test TextWidget initialization with string text."""
        widget = TextWidget("Hello World")
        
        assert widget.text == "Hello World"
        assert isinstance(widget._text, ReactiveValue)
        assert widget._text.value == "Hello World"
    
    def test_text_widget__initialization_with_reactive__uses_reactive(self):
        """Test TextWidget initialization with ReactiveValue."""
        reactive_text = ReactiveValue("Reactive Text")
        widget = TextWidget(reactive_text)
        
        assert widget.text == "Reactive Text"
        assert widget._text is reactive_text
    
    def test_text_widget__set_text_string__updates_reactive(self):
        """Test setting text with string value."""
        widget = TextWidget("Initial")
        
        widget.text = "Updated"
        
        assert widget.text == "Updated"
        assert widget._text.value == "Updated"
        assert widget._needs_layout is True
    
    def test_text_widget__set_text_reactive__replaces_reactive(self):
        """Test setting text with ReactiveValue."""
        widget = TextWidget("Initial")
        new_reactive = ReactiveValue("New Reactive")
        
        widget.text = new_reactive
        
        assert widget.text == "New Reactive"
        assert widget._text is new_reactive
    
    def test_text_widget__reactive_text_change__triggers_update(self):
        """Test that reactive text changes trigger widget updates."""
        reactive_text = ReactiveValue("Initial")
        widget = TextWidget(reactive_text)
        
        # Mock the mark dirty method
        widget._mark_dirty = Mock()
        
        # Change reactive value
        reactive_text.value = "Changed"
        
        # Verify widget was marked dirty
        widget._mark_dirty.assert_called()
        assert widget._needs_layout is True
    
    def test_text_widget__font_style_property__get_set(self):
        """Test font style property getter and setter."""
        widget = TextWidget()
        new_style = FontStyle(size=16, bold=True, color=(255, 0, 0))
        
        widget.font_style = new_style
        
        assert widget.font_style is new_style
        assert widget._needs_layout is True
    
    def test_text_widget__layout_property__get_set(self):
        """Test layout property getter and setter."""
        widget = TextWidget()
        new_layout = TextLayout(alignment=TextAlignment.CENTER, wrap=TextWrap.CHAR)
        
        widget.layout = new_layout
        
        assert widget.layout is new_layout
        assert widget._needs_layout is True
    
    def test_text_widget__set_text_color__updates_style(self):
        """Test setting text color."""
        widget = TextWidget()
        
        widget.set_text_color((255, 128, 0))
        
        assert widget._font_style.color == (255, 128, 0)
    
    def test_text_widget__set_font_size__updates_style(self):
        """Test setting font size."""
        widget = TextWidget()
        
        widget.set_font_size(20)
        
        assert widget._font_style.size == 20
        assert widget._needs_layout is True
    
    def test_text_widget__set_font_size_invalid__raises_error(self):
        """Test setting invalid font size raises error."""
        widget = TextWidget()
        
        with pytest.raises(ValueError, match="Font size must be positive"):
            widget.set_font_size(0)
    
    def test_text_widget__set_alignment__updates_layout(self):
        """Test setting text alignment."""
        widget = TextWidget()
        
        widget.set_alignment(TextAlignment.RIGHT)
        
        assert widget._layout.alignment == TextAlignment.RIGHT
        assert widget._needs_layout is True
    
    def test_text_widget__size_change__triggers_layout(self):
        """Test that size changes trigger layout recalculation."""
        widget = TextWidget("Test text")
        widget._needs_layout = False  # Reset layout flag
        
        # Mock the mark dirty method
        widget._mark_dirty = Mock()
        
        # Change size
        widget.size = (200, 100)
        
        # Verify layout is needed
        assert widget._needs_layout is True
        widget._mark_dirty.assert_called()


class TestTextWidgetLayout:
    """Test TextWidget layout and text wrapping functionality."""
    
    def test_text_widget__calculate_layout__empty_text(self):
        """Test layout calculation with empty text."""
        widget = TextWidget("")
        widget.size = (100, 50)
        
        widget._calculate_layout()
        
        assert widget._text_bounds == WidgetBounds(0, 0, 0, 0)
        assert len(widget._rendered_lines) == 0
        assert widget._needs_layout is False
    
    def test_text_widget__calculate_layout__single_line(self):
        """Test layout calculation with single line text."""
        widget = TextWidget("Hello World")
        widget.size = (200, 50)
        
        widget._calculate_layout()
        
        assert len(widget._rendered_lines) == 1
        assert widget._rendered_lines[0] == "Hello World"
        assert widget._text_bounds is not None
        assert widget._needs_layout is False
    
    def test_text_widget__wrap_by_words__multiple_lines(self):
        """Test word wrapping creates multiple lines."""
        widget = TextWidget("This is a long line that should wrap")
        widget.size = (50, 100)  # Narrow width to force wrapping
        widget._layout.wrap = TextWrap.WORD
        
        widget._calculate_layout()
        
        assert len(widget._rendered_lines) > 1
        # Verify no line is empty (unless original text had empty lines)
        for line in widget._rendered_lines:
            if line:  # Skip empty lines from original text
                assert len(line.strip()) > 0
    
    def test_text_widget__wrap_by_characters__breaks_words(self):
        """Test character wrapping breaks words."""
        widget = TextWidget("Supercalifragilisticexpialidocious")
        widget.size = (50, 100)  # Narrow width
        widget._layout.wrap = TextWrap.CHAR
        
        widget._calculate_layout()
        
        assert len(widget._rendered_lines) > 1
        # Verify lines are not empty
        for line in widget._rendered_lines:
            assert len(line) > 0
    
    def test_text_widget__wrap_with_ellipsis__adds_ellipsis(self):
        """Test ellipsis wrapping adds ellipsis to long lines."""
        widget = TextWidget("This is a very long line that should be truncated")
        widget.size = (50, 30)  # Narrow width
        widget._layout.wrap = TextWrap.ELLIPSIS
        
        widget._calculate_layout()
        
        # Should have lines with ellipsis
        has_ellipsis = any("..." in line for line in widget._rendered_lines)
        assert has_ellipsis
    
    def test_text_widget__max_lines__limits_output(self):
        """Test max_lines limits the number of rendered lines."""
        widget = TextWidget("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        widget.size = (200, 100)
        widget._layout.max_lines = 3
        
        widget._calculate_layout()
        
        assert len(widget._rendered_lines) == 3
    
    def test_text_widget__alignment_left__correct_positioning(self):
        """Test left alignment positioning."""
        widget = TextWidget("Test")
        widget.size = (100, 50)
        widget.position = (10, 20)
        widget._layout.alignment = TextAlignment.LEFT
        
        widget._calculate_layout()
        
        assert widget._text_bounds.x == 10  # Should be at widget position
    
    def test_text_widget__alignment_center__correct_positioning(self):
        """Test center alignment positioning."""
        widget = TextWidget("Test")
        widget.size = (100, 50)
        widget.position = (10, 20)
        widget._layout.alignment = TextAlignment.CENTER
        
        widget._calculate_layout()
        
        # Should be centered within widget bounds
        assert widget._text_bounds.x >= 10
    
    def test_text_widget__padding__affects_layout(self):
        """Test padding affects text layout."""
        widget = TextWidget("Test")
        widget.size = (100, 50)
        widget.position = (10, 20)
        widget._layout.padding = (5, 10, 5, 15)  # top, right, bottom, left
        
        widget._calculate_layout()
        
        # Text should be offset by left and top padding
        assert widget._text_bounds.x == 10 + 15  # position + left padding
        assert widget._text_bounds.y == 20 + 5   # position + top padding


class TestTextWidgetRendering:
    """Test TextWidget rendering functionality."""
    
    def test_text_widget__render__invisible_widget_skipped(self):
        """Test that invisible widgets are not rendered."""
        widget = TextWidget("Test")
        widget.visible = False
        canvas = Mock()
        
        widget.render(canvas)
        
        # Should not call any canvas methods
        assert not canvas.method_calls
    
    def test_text_widget__render__zero_alpha_skipped(self):
        """Test that widgets with zero alpha are not rendered."""
        widget = TextWidget("Test")
        widget.alpha = 0.0
        canvas = Mock()
        
        widget.render(canvas)
        
        # Should not call any canvas methods
        assert not canvas.method_calls
    
    def test_text_widget__render__triggers_layout_calculation(self):
        """Test that rendering triggers layout calculation if needed."""
        widget = TextWidget("Test")
        widget._needs_layout = True
        widget._calculate_layout = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget._calculate_layout.assert_called_once()
    
    def test_text_widget__render__marks_widget_clean(self):
        """Test that rendering marks widget as clean."""
        widget = TextWidget("Test")
        widget.mark_clean = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget.mark_clean.assert_called_once()
    
    @patch('src.tinydisplay.widgets.text._font_cache')
    def test_text_widget__render__uses_font_cache(self, mock_cache):
        """Test that rendering uses font cache."""
        widget = TextWidget("Test")
        canvas = Mock()
        mock_font = Mock()
        mock_cache.get_font.return_value = mock_font
        
        widget.render(canvas)
        
        mock_cache.get_font.assert_called_once_with(widget._font_style)


class TestTextWidgetPerformance:
    """Test TextWidget performance characteristics."""
    
    @pytest.mark.performance
    def test_text_widget__creation_performance__meets_target(self):
        """Test widget creation performance."""
        start_time = time.perf_counter()
        
        widgets = []
        for i in range(100):
            widget = TextWidget(f"Widget {i}")
            widgets.append(widget)
        
        creation_time = time.perf_counter() - start_time
        
        # Should create 100 widgets in under 50ms (realistic target)
        assert creation_time < 0.05
        assert len(widgets) == 100
    
    @pytest.mark.performance
    def test_text_widget__layout_performance__meets_target(self):
        """Test layout calculation performance."""
        widget = TextWidget("This is a long text that will require wrapping " * 10)
        widget.size = (100, 200)
        
        start_time = time.perf_counter()
        
        for _ in range(100):
            widget._needs_layout = True
            widget._calculate_layout()
        
        layout_time = time.perf_counter() - start_time
        
        # Should perform 100 layout calculations in under 50ms
        assert layout_time < 0.05
    
    @pytest.mark.performance
    def test_text_widget__reactive_update_performance__meets_target(self):
        """Test reactive update performance."""
        reactive_text = ReactiveValue("Initial")
        widget = TextWidget(reactive_text)
        
        start_time = time.perf_counter()
        
        for i in range(1000):
            reactive_text.value = f"Update {i}"
        
        update_time = time.perf_counter() - start_time
        
        # Should handle 1000 reactive updates in under 50ms
        assert update_time < 0.05


class TestTextWidgetIntegration:
    """Test TextWidget integration with other systems."""
    
    def test_text_widget__reactive_data_manager_integration(self):
        """Test integration with ReactiveDataManager."""
        from src.tinydisplay.core.reactive import ReactiveDataManager
        
        manager = ReactiveDataManager()
        binding = manager.create_direct_binding("test_text", "Initial Text")
        
        # Create reactive value and bind to the binding
        reactive_text = ReactiveValue("Initial Text")
        widget = TextWidget(reactive_text)
        
        # Simulate binding update by directly setting reactive value
        reactive_text.value = "Updated Text"
        
        # Widget should reflect the change
        assert widget.text == "Updated Text"
    
    def test_text_widget__multiple_reactive_bindings(self):
        """Test widget with multiple reactive bindings."""
        text_reactive = ReactiveValue("Hello")
        size_reactive = ReactiveValue(16)
        
        widget = TextWidget(text_reactive)
        
        # Bind font size to reactive value
        size_reactive.bind(lambda old, new: setattr(widget, '_font_style', 
                                                   FontStyle(size=new)))
        
        # Update both values
        text_reactive.value = "World"
        size_reactive.value = 20
        
        assert widget.text == "World"
        # Note: This test demonstrates the pattern, actual implementation
        # would need proper reactive binding for font properties
    
    def test_text_widget__canvas_integration(self):
        """Test TextWidget integration with canvas system."""
        # This would test integration with actual canvas when available
        widget = TextWidget("Canvas Test")
        mock_canvas = Mock()
        
        # Should not raise errors
        widget.render(mock_canvas)
        
        # Verify widget state is correct
        assert widget.text == "Canvas Test"
        assert widget.visible is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 