# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Widget ring buffer functionality for the tinyDisplay system
"""
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw

from tinyDisplay.render.widget import scroll, text
from tinyDisplay.utility import compareImage as ci, dataset


def test_text_widget_buffer_change_detection():
    """Test that the buffer correctly tracks changes in a text widget."""
    # Create dataset for dynamic text value
    db = {"value": "initial"}
    ds = dataset()
    ds.add("db", db)
    
    # Create text widget with buffer size 4
    w = text(dvalue="db['value']", dataset=ds, bufferSize=4)
    
    # Verify buffer is enabled and empty
    stats = w.buffer_stats()
    assert stats["enabled"] is True
    assert stats["max_size"] == 4
    # The buffer may contain 1 entry due to initial render during widget creation
    assert stats["size"] <= 1
    
    # Clear existing buffer entries
    w._imageBuffer.clear()
    
    # Render twice with same value
    w.render(force=True) # Force to ensure it's marked as changed
    w.render()
    
    # Verify buffer contains two entries with first one marked as changed
    buffer = w.get_buffer()
    assert len(buffer) == 2
    assert buffer[0][1] is True  # First render should be forced to change
    assert buffer[1][1] is False  # Second render should not have changed
    
    # Change the value and render again
    db["value"] = "changed"
    ds.update("db", db)
    w.render()
    
    # Verify buffer shows the change
    buffer = w.get_buffer()
    assert len(buffer) == 3
    assert buffer[2][1] is True  # Third render should mark as changed
    
    # Verify images are different
    assert not ci(buffer[0][0], buffer[2][0])


def test_scroll_widget_no_change_during_pause():
    """Test that scroll widget buffer correctly shows no changes during pause."""
    # Create text widget
    t = text(value="Test Text")
    
    # Create scroll widget with 3-tick pause at start and buffer size 4
    s = scroll(
        widget=t,
        actions=[("pause", 3), ("rtl",)],
        bufferSize=4
    )
    
    # Clear any existing buffer entries
    s._imageBuffer.clear()
    
    # Render three times (should be paused, no change)
    s.render(force=True) # Force to ensure it's marked as changed
    s.render(tick=1)
    s.render(tick=2)
    
    # Verify buffer contents
    buffer = s.get_buffer()
    assert len(buffer) == 3
    
    # First render should be marked as changed since we forced it
    assert buffer[0][1] is True
    
    # Next two renders should show no change during pause
    assert buffer[1][1] is False
    assert buffer[2][1] is False
    
    # Render once more to move to RTL movement
    s.render(tick=3)
    
    # Verify buffer shows the movement change
    buffer = s.get_buffer()
    assert len(buffer) == 4
    assert buffer[3][1] is True  # Fourth render should show change


def test_scroll_widget_static_method():
    """Test the static method for comparing images in the buffer."""
    # Create text widget
    t = text(value="Test Text")
    
    # Create scroll widget with 3-tick pause at start and buffer size 4
    s = scroll(
        widget=t,
        actions=[("pause", 3), ("rtl",)],
        bufferSize=4
    )
    
    # Clear any existing buffer entries
    s._imageBuffer.clear()
    
    # Case 1: Test with images that are identical but with different changed flags
    base_img = s.image.copy()
    # First three images are identical, only first one is marked as changed
    s._imageBuffer.append((base_img.copy(), True))   # First render is changed
    s._imageBuffer.append((base_img.copy(), False))  # Second render no change
    s._imageBuffer.append((base_img.copy(), False))  # Third render no change
    
    # Verify static returns True when images are identical and only first is marked changed
    assert s.static(3) is True
    
    # Case 2: Test with images that have different changed flags
    # Add a fourth entry with change=True for the movement
    s._imageBuffer.append((base_img.copy(), True))
    
    # This should be False because the fourth entry is marked as changed
    assert s.static(4) is False
    
    # Case 3: Test with visually different images but unchanged flags
    s._imageBuffer.clear()
    
    # Create visually different images
    original_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(original_img)
    draw.rectangle((0, 0, 5, 5), fill="white")
    
    # Add first image
    s._imageBuffer.append((original_img.copy(), True))
    
    # Create a second image with different content
    different_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(different_img)
    draw.rectangle((5, 5, 9, 9), fill="white")
    
    # Add second image marked as unchanged, but visually different
    s._imageBuffer.append((different_img, False))
    
    # This should return False because images are visually different,
    # even though only the first is marked as changed
    assert s.static(2) is False
    
    # Case 4: Test with differently sized images
    s._imageBuffer.clear()
    
    # Add first image
    s._imageBuffer.append((Image.new("RGBA", (10, 10), (0, 0, 0, 0)), True))
    
    # Add second image with different size
    s._imageBuffer.append((Image.new("RGBA", (20, 20), (0, 0, 0, 0)), False))
    
    # This should return False because images have different dimensions
    assert s.static(2) is False


def test_buffer_print_and_save():
    """Test the print and save methods of the buffer."""
    # Create text widget with simple text
    t = text(value="A")
    
    # Create scroll widget with 3-tick pause at start and buffer size 4
    s = scroll(
        widget=t,
        actions=[("pause", 3), ("rtl",)],
        bufferSize=4
    )
    
    # Clear any existing buffer entries
    s._imageBuffer.clear()
    
    # Render four times
    for i in range(4):
        s.render(tick=i)
    
    # Test save functionality
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_buffer.png"
        s.save(str(test_file), 4)
        
        # Verify file exists and has content
        assert os.path.exists(test_file)
        assert os.path.getsize(test_file) > 0


def test_default_buffer_behavior():
    """Test default buffer behavior (size 1, essentially disabled)."""
    # Create text widget with default buffer size (1)
    w = text(value="Test Text")
    
    # Verify buffer is reported as disabled
    stats = w.buffer_stats()
    assert stats["enabled"] is False
    assert stats["max_size"] == 1
    
    # Verify get_buffer returns None
    assert w.get_buffer() is None
    
    # Verify static always returns True
    assert w.static() is True
    assert w.static(5) is True 