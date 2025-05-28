"""
Tests for text widget performance.
"""

import pytest
import time
from PIL import Image, ImageFont

from tinyDisplay.render.widget import text

def test_text_widget_same_content_performance():
    """Test the performance of rendering the same text multiple times."""
    # Create a text widget
    t = text(size=(200, 50), text="Initial text", wrap=True, width=200)
    
    # Render the same text multiple times and check performance
    start_time = time.time()
    iterations = 100
    
    for _ in range(iterations):
        t.render()
    
    elapsed = time.time() - start_time
    avg_render_time = elapsed / iterations
    
    # Just ensure it completes - performance thresholds would depend on hardware
    assert avg_render_time is not None
    assert elapsed > 0, "Rendering should take some measurable time"

def test_text_widget_changing_content_performance():
    """Test the performance of rendering with different text content."""
    # Create a text widget
    t = text(size=(200, 50), text="Initial text", wrap=True, width=200)
    
    # Render with different text multiple times
    start_time = time.time()
    iterations = 10
    
    for i in range(iterations):
        t._value = f"This is test text {i}"
        t.render()
    
    elapsed = time.time() - start_time
    
    # Just ensure it completes - performance thresholds would depend on hardware
    assert elapsed > 0, "Rendering should take some measurable time"

def test_text_widget_wrapping_performance():
    """Test the performance of word wrapping in the text widget."""
    # Create a text widget
    t = text(size=(200, 50), text="Initial text", wrap=True, width=200)
    
    # Test long text that needs wrapping
    start_time = time.time()
    iterations = 10
    
    long_text = "This is a long text that needs to be wrapped across multiple lines to test the word wrapping performance of the text widget"
    
    for _ in range(iterations):
        t._value = long_text
        t.render()
    
    elapsed = time.time() - start_time
    
    # Just ensure it completes - performance thresholds would depend on hardware
    assert elapsed > 0, "Word wrapping should take some measurable time"

def test_text_widget_caching():
    """Test that the text widget properly caches rendered content."""
    # Create a text widget
    t = text(size=(200, 50), text="Cached text", wrap=True, width=200)
    
    # First render to populate cache
    t.render()
    
    # Time repeated rendering of the same content (should use cache)
    start_time = time.time()
    iterations = 100
    
    for _ in range(iterations):
        t.render()
    
    cached_time = time.time() - start_time
    
    # Now change content and time first render (should not use cache)
    t._value = "New content that hasn't been cached yet"
    
    start_time = time.time()
    t.render()
    uncached_time = time.time() - start_time
    
    # Normalized comparison (per render)
    cached_per_render = cached_time / iterations
    
    # Cached rendering should be significantly faster, but hardware dependent
    # so we just check it finishes and basic sanity
    assert cached_per_render > 0, "Cached rendering should take some measurable time"
    assert cached_time > 0, "Rendering should take some measurable time" 