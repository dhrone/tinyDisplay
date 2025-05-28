"""
Tests for scroll widget printing functionality
"""

import pytest
from PIL import Image

from tinyDisplay.render.widget import scroll, text

def test_scroll_widget_printing():
    """Test that the scroll widget correctly prints and buffers frames"""
    # Create a text widget
    t = text(value='ABCDEF')

    # Create a scroll widget with RTL movement and specific size
    s = scroll(
        widget=t, 
        actions=[('rtl',)], 
        size=(15, 8),
        bufferSize=4
    )

    # Clear any existing buffer entries
    s._imageBuffer.clear()

    # Render multiple frames with increasing tick values to show scrolling
    for i in range(6):
        s.render(tick=i)
        # Verify image exists
        assert s.image is not None
        assert s.image.width == 15
        assert s.image.height == 8

    # Check if buffer contains the right number of frames
    buffer = s.get_buffer()
    assert len(buffer) <= 4, "Buffer should not exceed buffer size"
    
    # Test that the buffer actually contains different frames
    if len(buffer) >= 2:
        # Compare first and last frames
        first_img = buffer[0][0]
        last_img = buffer[-1][0]
        
        # Convert to binary for comparison
        first_binary = first_img.convert('1')
        last_binary = last_img.convert('1')
        
        # Check if images are different
        are_different = False
        for y in range(min(first_binary.height, last_binary.height)):
            for x in range(min(first_binary.width, last_binary.width)):
                if first_binary.getpixel((x, y)) != last_binary.getpixel((x, y)):
                    are_different = True
                    break
            if are_different:
                break
        
        assert are_different, "First and last animation frames should be different"

def test_scroll_buffer_capacity():
    """Test that the scroll widget respects buffer size limits"""
    # Create a text widget
    t = text(value='ABCDEF')

    # Create a scroll widget with small buffer
    buffer_size = 3
    s = scroll(
        widget=t, 
        actions=[('rtl',)], 
        size=(15, 8),
        bufferSize=buffer_size
    )

    # Clear any existing buffer entries
    s._imageBuffer.clear()

    # Render more frames than the buffer size
    for i in range(buffer_size + 5):
        s.render(tick=i)

    # Check if buffer is limited to specified size
    buffer = s.get_buffer()
    assert len(buffer) <= buffer_size, f"Buffer should be limited to {buffer_size} frames" 