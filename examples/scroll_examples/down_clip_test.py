#!/usr/bin/env python3
"""
DOWN SCROLL_CLIP Test Script

This script tests the vertical scrolling behavior of the SCROLL_CLIP command in the tinyDisplay marquee.
"""

import os
import sys
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
FPS = 30
TOTAL_FRAMES = 100

def create_font(size=18):
    """Create a font for text rendering."""
    try:
        return ImageFont.load_default()
    except:
        # Try common system fonts
        for font_name in ["Arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf", "NotoSans-Regular.ttf"]:
            try:
                return ImageFont.truetype(font_name, size=size)
            except:
                pass
    # Last resort: use a bitmap font
    return ImageFont.load_default()

def down_clip_test():
    """Test SCROLL_CLIP DOWN animation."""
    print("Testing SCROLL_CLIP DOWN animation...")
    
    # Create a text widget
    font = create_font(size=16)
    widget = text(
        "DOWN CLIP TEST",
        size=(120, 20),
        font=font,
        mode="1",  # Binary mode (black and white)
        color=1,   # White text
        background=0,  # Black background
    )
    
    # Print widget dimensions
    widget_width, widget_height = widget.image.size
    print(f"Widget size: {widget.size}")
    
    # Create a marquee with only DOWN SCROLL_CLIP
    # Use larger vertical size with padding to accommodate downward movement
    marquee_height = widget_height + 30
    
    program = """
    # Move down by 20 pixels
    SCROLL_CLIP(DOWN, 20) { 
        step=2,
        interval=1
    };
    
    # Pause after completing the down movement
    PAUSE(10);
    
    # Move back to origin 
    RESET_POSITION();
    
    # Pause at origin
    PAUSE(5);
    """
    
    # Create a marquee that logs its timeline
    class DebugMarquee(new_marquee):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
        def debug_timeline(self):
            """Print debug info about the timeline and positions."""
            if not hasattr(self, '_timeline') or not self._timeline:
                print("No timeline generated!")
                return
                
            print(f"\nTimeline with {len(self._timeline)} positions:")
            
            # Group into moves and pauses
            moves = []
            pauses = []
            
            for pos in self._timeline:
                if hasattr(pos, 'pause') and pos.pause:
                    pauses.append((pos.x, pos.y))
                else:
                    moves.append((pos.x, pos.y))
            
            print(f"Movement positions ({len(moves)}):")
            unique_coords = set()
            
            # First, show positional data arranged by y-coordinate
            all_y_coords = sorted(set(y for _, y in moves))
            for y in all_y_coords:
                x_coords = [x for x, y_pos in moves if y_pos == y]
                unique_coords.update((x, y) for x in x_coords)
                print(f"  y={y}: x = {sorted(set(x_coords))}")
            
            # Print all unique positions in order
            print("\nAll positions in timeline:")
            for i, pos in enumerate(self._timeline):
                x = pos.x if hasattr(pos, 'x') else pos[0]
                y = pos.y if hasattr(pos, 'y') else pos[1]
                pos_type = "PAUSE" if (hasattr(pos, 'pause') and pos.pause) else "MOVE"
                print(f"  {i:3d}: ({x:3d}, {y:3d}) - {pos_type}")
    
    # Create the test marquee
    marquee = DebugMarquee(
        widget=widget,
        program=program,
        mode="1",
        size=(widget_width, marquee_height),
        debug=True  # Enable debug mode
    )
    
    # Force a render to initialize the timeline
    _ = marquee.render(move=False)
    
    # Debug the timeline
    marquee.debug_timeline()
    
    # Generate frames for the animation
    frames = []
    print(f"\nGenerating {TOTAL_FRAMES} frames...")
    for frame_num in range(TOTAL_FRAMES):
        # Render the marquee
        img, _ = marquee.render(tick=frame_num, move=True)
        
        # Get current position
        current_pos = marquee.position
        pos_x = current_pos.x if hasattr(current_pos, 'x') else current_pos[0]
        pos_y = current_pos.y if hasattr(current_pos, 'y') else current_pos[1]
        
        # Log every 5 frames
        if frame_num % 5 == 0:
            print(f"  Frame {frame_num}/{TOTAL_FRAMES} - Position: ({pos_x}, {pos_y})")
        
        # Create a larger canvas with grid for better visualization
        padding = 20
        canvas_width = widget_width + padding * 2
        canvas_height = marquee_height + padding * 2
        canvas = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        
        # Draw a grid in dark gray
        grid_spacing = 5
        grid_color = (30, 30, 30)
        for x in range(0, canvas_width, grid_spacing):
            draw.line([(x, 0), (x, canvas_height)], fill=grid_color)
        for y in range(0, canvas_height, grid_spacing):
            draw.line([(0, y), (canvas_width, y)], fill=grid_color)
        
        # Draw the marquee area
        draw.rectangle(
            [(padding-1, padding-1), (padding+widget_width, padding+marquee_height)],
            outline=(50, 50, 50)
        )
        
        # Draw origin marker at (0, 0) position
        draw.rectangle(
            [(padding-2, padding-2), (padding+2, padding+2)],
            outline=(100, 100, 100),
            width=1,
            fill=(50, 50, 50)
        )
        
        # Convert and paste the marquee image
        if img.mode == "1":
            rgb_img = Image.new("RGB", img.size, (0, 0, 0))
            for y in range(img.height):
                for x in range(img.width):
                    if img.getpixel((x, y)) == 1:  # White in mode "1"
                        rgb_img.putpixel((x, y), (255, 255, 255))
            canvas.paste(rgb_img, (padding, padding))
        else:
            canvas.paste(img, (padding, padding))
        
        # Draw position marker
        marker_x = padding + pos_x
        marker_y = padding + pos_y
        draw.rectangle(
            [(marker_x-3, marker_y-3), (marker_x+3, marker_y+3)],
            outline=(200, 200, 200),
            fill=(255, 50, 50)
        )
        
        # Add frame counter and position info
        draw.text(
            (5, canvas_height-15),
            f"Frame: {frame_num} | Pos: ({pos_x}, {pos_y})",
            fill=(200, 200, 200),
            font=create_font(10)
        )
        
        frames.append(canvas)
    
    # Save as animated GIF
    output_filename = os.path.join(OUTPUT_DIR, "down_clip_test.gif")
    frames[0].save(
        output_filename,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=1000//FPS,  # Duration in ms
        loop=0  # Loop forever
    )
    print(f"Saved animation to {output_filename}")
    return output_filename

if __name__ == "__main__":
    down_clip_test()
    print("Test completed successfully") 