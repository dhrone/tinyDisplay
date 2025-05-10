#!/usr/bin/env python3
"""
SCROLL_LOOP Test Script

This script tests the continuous scrolling behavior of the SCROLL_LOOP command in the tinyDisplay marquee.
"""

import os
import sys
from pathlib import Path
import logging
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='[%(name)s] %(levelname)s: %(message)s')

# Set up constants
OUTPUT_DIR = "test_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_font(size=18):
    """Create a font for text rendering."""
    try:
        return ImageFont.load_default()
    except:
        # Try common system fonts
        for font_name in ["Arial.ttf", "DejaVuSans.ttf", "Verdana.ttf", "Helvetica.ttf"]:
            try:
                return ImageFont.truetype(font_name, size)
            except:
                pass
    return None

def test_scroll_loop():
    """Test the SCROLL_LOOP behavior with debug logs enabled."""
    # Create a text widget with clear content
    font = create_font()
    text_content = "This is a SCROLL_LOOP test message that should continuously scroll"
    widget = text(
        value=text_content,
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    print(f"Widget created with size: {widget.image.size}")
    
    # Calculate marquee dimensions
    widget_width, widget_height = widget.image.size
    marquee_height = widget_height + 8  # Add padding
    
    # Create a SCROLL_LOOP program with specific parameters
    program = """
    SCROLL_LOOP(LEFT, widget.width) { 
        step=2,  # 2 pixels per step for faster movement
        interval=1,
        gap=20   # 20 pixel gap between copies
    };
    """
    
    # Create the marquee with debug mode enabled
    marquee = new_marquee(
        widget=widget,
        program=program,
        mode="1",
        size=(120, marquee_height),  # Fixed width viewing window
        debug=True  # Enable debug logging
    )
    
    # Force render to initialize the marquee
    initial_img, _ = marquee.render(reset=True, move=False)
    
    # Save the initial image
    initial_path = os.path.join(OUTPUT_DIR, "scroll_loop_initial.png")
    initial_img.save(initial_path)
    print(f"Saved initial image to {initial_path}")
    
    # Generate a sequence of frames and track positions
    num_frames = 100
    frames = []
    positions = []
    
    print(f"Generating {num_frames} frames to visualize the scrolling behavior...")
    
    for i in range(num_frames):
        # Render the next frame
        img, _ = marquee.render(move=True)
        
        # Convert to RGB for better visibility in the output GIF
        rgb_img = Image.new("RGB", img.size, (0, 0, 0))
        for y in range(img.height):
            for x in range(img.width):
                try:
                    if img.getpixel((x, y)) == 1:  # White in mode "1"
                        rgb_img.putpixel((x, y), (255, 255, 255))
                except:
                    pass
        
        # Create a frame with position information
        frame = Image.new("RGB", (img.width, img.height + 30), (50, 50, 50))
        frame.paste(rgb_img, (0, 0))
        
        # Add position text
        draw = ImageDraw.Draw(frame)
        pos = marquee.position
        draw.text((5, img.height + 5), f"Frame {i}: pos={pos}", fill=(255, 255, 255), font=font)
        
        frames.append(frame)
        positions.append(pos)
        
        # Print progress every 10 frames
        if i % 10 == 0:
            print(f"Frame {i}: position = {pos}")
    
    # Save as animated GIF
    output_path = os.path.join(OUTPUT_DIR, "scroll_loop_test.gif")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=50,  # 50ms per frame (20 fps)
        loop=0  # Loop forever
    )
    print(f"Saved animation to {output_path}")
    
    # Verify the scrolling behavior
    # Check if x coordinate eventually becomes negative (scrolling left)
    has_negative_x = any(pos[0] < 0 for pos in positions)
    print(f"Scrolling behavior verification - has negative x coordinates: {has_negative_x}")
    
    # Check for continuous decrease in x (scrolling left)
    continuous_decrease = all(positions[i][0] < positions[i-1][0] for i in range(1, len(positions)))
    print(f"Continuous leftward scrolling: {continuous_decrease}")
    
    # Return to verify the tests in the console output
    return positions

if __name__ == "__main__":
    positions = test_scroll_loop()
    print("Test complete.") 