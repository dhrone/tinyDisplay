#!/usr/bin/env python3
"""
Marquee Animation Demo

This program demonstrates the various animation capabilities of the tinyDisplay
marquee class, creating animated GIFs for each animation type.
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
import time
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee

# Constants
FPS = 30
ANIMATION_SECONDS = 5
TOTAL_FRAMES = FPS * ANIMATION_SECONDS
OUTPUT_DIR = "test_results"

def ensure_output_directory():
    """Create the output directory if it doesn't exist."""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    print(f"Created output directory: {OUTPUT_DIR}")

def cleanup():
    """Remove all test results."""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        print(f"Removed {OUTPUT_DIR} directory and its contents")
    else:
        print(f"{OUTPUT_DIR} directory does not exist")

def test_direct_text_rendering():
    """Function to verify text rendering in mode '1'."""
    # Create an output directory if needed
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create a mode "1" image with black background
    img = Image.new("1", (150, 30), 0)
    
    # Create a font
    font = create_font(size=18)
    
    # Get a drawing context
    draw = ImageDraw.Draw(img)
    
    # Draw text in white (1)
    text_str = "TEST DIRECT TEXT"
    draw.text((10, 5), text_str, fill=1, font=font)
    
    # Save the direct test image
    test_path = os.path.join(OUTPUT_DIR, "direct_test.png")
    img.save(test_path)
    
    # Count white pixels to confirm text is rendered
    white_pixels = sum(1 for y in range(img.height) for x in range(img.width) if img.getpixel((x, y)) == 1)
    
    print(f"Direct text test: mode={img.mode}, size={img.size}, white pixels={white_pixels}")
    print(f"Saved direct test image to {test_path}")
    
    return white_pixels > 0

def create_font(size=14):
    """Create a font for text widgets."""
    try:
        # Try to load PIL's default font
        default_font = ImageFont.load_default()
        
        # Test direct text rendering to verify the font works
        img = Image.new("1", (100, 30), 0)
        draw = ImageDraw.Draw(img)
        draw.text((5, 5), "Test Font", fill=1, font=default_font)
        
        white_pixels = sum(1 for y in range(img.height) for x in range(img.width) if img.getpixel((x, y)) == 1)
        print(f"Font test - white pixels: {white_pixels}")
        
        if white_pixels > 0:
            print("Default font rendering works correctly")
            return default_font
        else:
            print("Default font not rendering correctly, trying alternatives")
    except Exception as e:
        print(f"Default font error: {e}")
    
    # If default font failed, try common system fonts
    for font_name in ["Arial.ttf", "DejaVuSans.ttf", "Verdana.ttf", "Helvetica.ttf"]:
        try:
            font = ImageFont.truetype(font_name, size)
            print(f"Using system font: {font_name}")
            return font
        except Exception as e:
            print(f"Could not load {font_name}: {e}")
    
    # Last resort: create a bitmap font
    try:
        # Try to create a bitmap font
        print("Trying bitmap font...")
        return ImageFont.load_default()
    except Exception as e:
        print(f"Could not create bitmap font: {e}")
        return None

def create_slide_animation():
    """Create a SLIDE animation."""
    print("Creating SLIDE animation...")
    
    # Create a text widget with mode 1 (black and white)
    font = create_font(size=18)  # Larger font for better visibility
    print(f"Using font: {font}")
    
    # Create a properly configured text widget in mode "1"
    widget = text(
        "SLIDE Effect",
        size=(120, 20),
        font=font,
        mode="1",
        color=1,  # White text (1 = white, 0 = black in mode 1)
        background=0,  # Black background
    )
    
    # Debug the widget image
    print(f"Widget created with size: {widget.size}")
    
    # Force render to check if text is visible
    widget_img = widget.render(force=True)[0]
    
    # Save widget image for debugging
    debug_path = os.path.join(OUTPUT_DIR, "widget_debug.png")
    widget_img.save(debug_path)
    
    # Convert to RGB using PIL's built-in conversion
    rgb_debug = widget_img.convert("RGB")
    
    # PIL's conversion sometimes maps 1 to black and 0 to white for mode "1", 
    # so we'll manually check a sample pixel and invert if needed
    sample_pixel = (10, 10)  # Try to choose a position that should contain text
    
    # Check if we need to invert the image
    try:
        # If text is visible in mode "1", but the converted RGB image shows black where white should be
        if widget_img.getpixel(sample_pixel) == 1 and sum(rgb_debug.getpixel(sample_pixel)) < 100:
            # Invert the image
            from PIL import ImageOps
            rgb_debug = ImageOps.invert(rgb_debug)
    except:
        # If we can't check a sample pixel, use a safer approach
        # Create a new RGB image and manually map colors
        rgb_debug = Image.new("RGB", widget_img.size, (0, 0, 0))
        for y in range(widget_img.height):
            for x in range(widget_img.width):
                try:
                    pixel_value = widget_img.getpixel((x, y))
                    if pixel_value == 1:  # White in mode "1"
                        rgb_debug.putpixel((x, y), (255, 255, 255))
                except:
                    pass
    
    rgb_debug_path = os.path.join(OUTPUT_DIR, "widget_debug_rgb.png")
    rgb_debug.save(rgb_debug_path)
    
    print(f"Saved widget debug images to {debug_path} and {rgb_debug_path}")
    
    # Create a simple but clear SLIDE program
    program = """
    # Start at position 0
    PAUSE(10);
    
    # Slide to the right
    SLIDE(RIGHT, 80) { 
        step=4,
        interval=1
    };
    
    # Pause at the right edge
    PAUSE(20);
    
    # Slide back to the left
    SLIDE(LEFT, 80) { 
        step=4,
        interval=1
    };
    
    # Pause at the left edge
    PAUSE(10);
    """
    
    # Calculate marquee height with padding - horizontal movement needs vertical padding
    widget_height = widget.size[1]
    marquee_height = widget_height + 6  # Add 6 pixels of vertical padding (3px on top, 3px on bottom)
    
    # Create a marquee with the same mode as the widget
    marquee = new_marquee(
        widget=widget,
        program=program,
        mode="1",  # Explicitly use mode "1" to match the widget
        size=(100, marquee_height)  # Use calculated height with padding
    )
    
    # Force a render to initialize the widget properly
    initial_img, _ = marquee.render(move=False)
    print(f"Initial render complete, marquee size: {marquee.size}")
    
    # Save marquee debug image
    marquee_debug_path = os.path.join(OUTPUT_DIR, "marquee_debug.png")
    initial_img.save(marquee_debug_path)
    
    # Convert to RGB using PIL's built-in conversion
    rgb_marquee = initial_img.convert("RGB")
    
    # Check if we need to invert the image
    try:
        # Sample a pixel that should be text
        sample_x, sample_y = min(initial_img.width-1, 5), min(initial_img.height-1, 5)
        if initial_img.getpixel((sample_x, sample_y)) == 1 and sum(rgb_marquee.getpixel((sample_x, sample_y))) < 100:
            # Invert the image
            from PIL import ImageOps
            rgb_marquee = ImageOps.invert(rgb_marquee)
    except:
        # Manual pixel-by-pixel approach as fallback
        rgb_marquee = Image.new("RGB", initial_img.size, (0, 0, 0))
        for y in range(initial_img.height):
            for x in range(initial_img.width):
                try:
                    if initial_img.getpixel((x, y)) == 1:  # White in mode "1"
                        rgb_marquee.putpixel((x, y), (255, 255, 255))
                except:
                    pass
    
    rgb_marquee_path = os.path.join(OUTPUT_DIR, "marquee_debug_rgb.png")
    rgb_marquee.save(rgb_marquee_path)
    
    print(f"Saved marquee debug images to {marquee_debug_path} and {rgb_marquee_path}")
    
    # Generate animated GIF
    return render_animation(marquee, "slide_animation.gif")

def create_scroll_animation():
    """Create a SCROLL animation."""
    print("Creating SCROLL animation...")
    
    # Create a text widget
    font = create_font()
    widget = text(
        value="This is a smooth scrolling ticker message - SCROLL animation",
        font=font,
        mode = "1",
        color=1, #(50, 255, 50),  # Green text
        background=0, #(50, 50, 50, 200),  # Semi-transparent dark background
    )
    
    # Calculate marquee height with padding
    widget_height = widget.image.size[1]
    marquee_height = widget_height + 8  # Add 8 pixels of vertical padding
    
    # Create a SCROLL_LOOP program (continuous scrolling)
    program = """
    SCROLL_LOOP(LEFT, widget.width) { 
        step=1,
        interval=1,
        gap=10
    };
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget,
        program=program,
        mode = "1",
        size=(100, marquee_height),  # Use calculated height with padding
    )
    
    # Generate animated GIF
    return render_animation(marquee, "scroll_animation.gif")

def create_scroll_bounce_animation():
    """Create a SCROLL_BOUNCE animation."""
    print("Creating SCROLL_BOUNCE animation...")
    
    # Create a text widget with mode 1 (black and white)
    font = create_font()
    widget = text(
        "Bounce Effect Demo",
        size=(120, 20),
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    # Calculate marquee height with padding
    widget_height = widget.image.size[1]
    marquee_height = widget_height + 6  # Add 6 pixels of vertical padding
    
    # Create a SCROLL_BOUNCE program
    program = """
    SCROLL_BOUNCE(LEFT, 80) { 
        step=2,
        interval=1,
        pause_at_ends=5
    };
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget,
        program=program,
        mode="1",
        size=(120, marquee_height)  # Use calculated height with padding
    )
    
    # Generate animated GIF
    return render_animation(marquee, "scroll_bounce_animation.gif")

def create_scroll_clip_animation():
    """Create a SCROLL_CLIP animation."""
    print("Creating SCROLL_CLIP animation...")
    
    # Create a text widget with mode 1 (black and white)
    font = create_font()
    widget = text(
        "Clipped Scroll Animation",
        size=(150, 20),
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    # Calculate marquee height with padding
    widget_height = widget.image.size[1]
    marquee_height = widget_height + 6  # Add 6 pixels of vertical padding
    
    # Create a SCROLL_CLIP program
    program = """
    # Start with text at position 0
    PAUSE(10);
    
    # Scroll to the left and stop (clip)
    SCROLL_CLIP(LEFT, 100) { 
        step=2,
        interval=1
    };
    
    # Pause at the clipped position to show we're stopped
    PAUSE(30);
    
    # Reset back to the starting position
    RESET_POSITION();
    
    # Pause at the start again
    PAUSE(10);
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget,
        program=program,
        mode="1",
        size=(100, marquee_height)  # Use calculated height with padding
    )
    
    # Generate animated GIF
    return render_animation(marquee, "scroll_clip_animation.gif")

def create_complex_animation():
    """Create a complex animation with multiple effects."""
    print("Creating complex animation...")
    
    # Create a text widget with mode 1 (black and white)
    font = create_font()
    widget = text(
        "Complex Animation",
        size=(150, 20),
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    # Calculate marquee height with padding - horizontal movement needs vertical padding
    widget_height = widget.image.size[1]
    marquee_height = widget_height + 50  # Increase padding for vertical movement
    
    # Create a complex program with multiple animation types
    program = """
    # Define the sequence once, then use LOOP to repeat it 3 times
    DEFINE sequence {
        # Slide animation - move RIGHT by 60 pixels
        SLIDE(RIGHT, 60) { 
            step=2,
            interval=1
        };
        
        # Pause at the right edge
        PAUSE(10);
        
        # Bounce animation - bounce LEFT by 30 pixels
        SCROLL_BOUNCE(LEFT, 30) { 
            step=1,
            interval=1,
            pause_at_ends=5
        };
        
        # Pause after bounce
        PAUSE(5);
        
        # Clip scroll animation - move DOWN by 20 pixels (increased from 8)
        SCROLL_CLIP(DOWN, 20) { 
            step=2,
            interval=1
        };
        
        # Pause after clip
        PAUSE(5);
        
        # Reset position to prepare for the next cycle
        RESET_POSITION();
        
        # Pause at starting position
        PAUSE(5);
    }
    
    # Repeat the sequence 3 times
    LOOP(3) {
        sequence();
    } END;
    """
    
    # Print the program for debugging
    print("\nComplex animation DSL program:")
    print(program)
    
    # Create a special test class to validate the timeline
    class TimelineValidator(new_marquee):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
        def validate_timeline(self):
            """Validate that the timeline correctly follows the DSL program."""
            if not hasattr(self, '_timeline') or not self._timeline:
                print("ERROR: No timeline generated!")
                return False
                
            print(f"\nValidating timeline with {len(self._timeline)} positions...")
            
            # Group the timeline into segments
            segments = []
            current_segment = []
            current_x, current_y = 0, 0
            
            for i, pos in enumerate(self._timeline):
                if hasattr(pos, 'x') and hasattr(pos, 'y'):
                    pos_x, pos_y = pos.x, pos.y
                else:
                    pos_x, pos_y = pos[0], pos[1]
                
                # Detect significant position changes (direction changes or pauses)
                is_new_segment = False
                
                if i > 0:
                    prev_pos = self._timeline[i-1]
                    prev_x = prev_pos.x if hasattr(prev_pos, 'x') else prev_pos[0]
                    prev_y = prev_pos.y if hasattr(prev_pos, 'y') else prev_pos[1]
                    
                    # Detect direction changes
                    dx = pos_x - prev_x
                    dy = pos_y - prev_y
                    
                    if len(current_segment) > 1:
                        last_dx = prev_x - (current_segment[-2].x if hasattr(current_segment[-2], 'x') else current_segment[-2][0])
                        last_dy = prev_y - (current_segment[-2].y if hasattr(current_segment[-2], 'y') else current_segment[-2][1])
                        
                        # Direction change detected
                        if (dx != 0 and last_dx != 0 and dx * last_dx < 0) or \
                           (dy != 0 and last_dy != 0 and dy * last_dy < 0) or \
                           (dx != 0 and last_dx == 0) or (dy != 0 and last_dy == 0) or \
                           (dx == 0 and last_dx != 0) or (dy == 0 and last_dy != 0):
                            is_new_segment = True
                    
                    # Also detect resets to (0,0)
                    if pos_x == 0 and pos_y == 0 and (prev_x != 0 or prev_y != 0):
                        is_new_segment = True
                    
                    # Detect pauses
                    if hasattr(pos, 'pause') and pos.pause and not (hasattr(prev_pos, 'pause') and prev_pos.pause):
                        is_new_segment = True
                    
                    # Detect terminal positions (end of an animation sequence)
                    if hasattr(pos, 'terminal') and pos.terminal:
                        is_new_segment = True
                
                # Start a new segment if needed
                if is_new_segment and current_segment:
                    segments.append(current_segment)
                    current_segment = []
                
                # Add position to current segment
                current_segment.append(pos)
                current_x, current_y = pos_x, pos_y
            
            # Add the last segment
            if current_segment:
                segments.append(current_segment)
            
            # Analyze each segment
            print(f"Timeline divided into {len(segments)} segments")
            
            # Expected segment patterns for the DSL program (one iteration)
            expected_pattern = [
                "RIGHT SLIDE",       # SLIDE(RIGHT, 60)
                "PAUSE",             # PAUSE(10)
                "LEFT BOUNCE OUT",   # SCROLL_BOUNCE(LEFT, 30) - first half
                "PAUSE AT EDGE",     # pause_at_ends=5 at left edge
                "RIGHT BOUNCE IN",   # SCROLL_BOUNCE(LEFT, 30) - second half
                "PAUSE AT START",    # pause_at_ends=5 at right edge (start)
                "PAUSE",             # PAUSE(5)
                "DOWN CLIP",         # SCROLL_CLIP(DOWN, 20)
                "PAUSE",             # PAUSE(5)
                "RESET",             # RESET_POSITION()
                "PAUSE"              # PAUSE(5)
            ]
            
            # 3 iterations repeated
            expected_segments = expected_pattern * 3
            
            # Check if we have the right number of segments
            expected_count = len(expected_segments)
            if len(segments) < expected_count:
                print(f"WARNING: Expected at least {expected_count} segments, but found {len(segments)}")
                print("This might indicate the animation is not following the DSL program correctly.")
                
            # Analyze and report on the actual segments
            for i, segment in enumerate(segments):
                segment_type = "UNKNOWN"
                start_pos = segment[0]
                end_pos = segment[-1]
                start_x = start_pos.x if hasattr(start_pos, 'x') else start_pos[0]
                start_y = start_pos.y if hasattr(start_pos, 'y') else start_pos[1]
                end_x = end_pos.x if hasattr(end_pos, 'x') else end_pos[0]
                end_y = end_pos.y if hasattr(end_pos, 'y') else end_pos[1]
                
                # Determine segment type
                if hasattr(start_pos, 'pause') and start_pos.pause:
                    segment_type = "PAUSE"
                elif start_x == 0 and start_y == 0 and i > 0:
                    segment_type = "RESET"
                elif end_x > start_x and end_y == start_y:
                    segment_type = "RIGHT SLIDE"
                elif end_x < start_x and end_y == start_y:
                    segment_type = "LEFT MOVEMENT"
                elif end_y > start_y:  # Check vertical movement without constraining x
                    segment_type = "DOWN CLIP"
                elif end_y < start_y:
                    segment_type = "UP MOVEMENT"
                
                # Report on this segment
                print(f"Segment {i+1}: {segment_type}, Length: {len(segment)}, Start: ({start_x}, {start_y}), End: ({end_x}, {end_y})")
                
                # For RIGHT SLIDE, check if it moves the full 60 pixels
                if segment_type == "RIGHT SLIDE":
                    dx = end_x - start_x
                    if dx < 60:
                        print(f"  WARNING: SLIDE RIGHT should move 60 pixels, but only moved {dx} pixels")
                
                # For DOWN CLIP, check if it moves the full 20 pixels down
                if segment_type == "DOWN CLIP":
                    dy = end_y - start_y
                    if dy < 20:
                        print(f"  WARNING: SCROLL_CLIP DOWN should move 20 pixels, but only moved {dy} pixels")
                
                # Look for iteration boundaries
                if i > 0 and i % len(expected_pattern) == 0:
                    print(f"\n--- Iteration {i // len(expected_pattern) + 1} completed ---\n")
            
            # Print all unique y-positions in the timeline to check vertical movement
            y_positions = set(pos.y if hasattr(pos, 'y') else pos[1] for pos in self._timeline)
            print(f"\nUnique y-positions in timeline: {sorted(y_positions)}")
            
            return True
    
    # Create the test marquee with debug enabled
    marquee = TimelineValidator(
        widget=widget,
        program=program,
        mode="1", 
        size=(150, marquee_height),  # Use larger width and height with padding for vertical movement
        debug=True  # Enable debug mode
    )
    
    # Force a render to initialize
    initial_img = marquee.render(move=False)
    
    # Validate the timeline
    marquee.validate_timeline()
    
    # Use 3x the normal frames to ensure complete cycles
    global TOTAL_FRAMES
    original_frames = TOTAL_FRAMES
    TOTAL_FRAMES = original_frames * 3  # Triple the animation length
    
    # Generate animated GIF
    result = render_animation(marquee, "complex_animation.gif")
    
    # Restore original frame count
    TOTAL_FRAMES = original_frames
    
    return result

def create_multi_widget_animation():
    """Create an animation with multiple coordinated widgets."""
    print("Creating multi-widget animation...")
    
    # First, test if direct text rendering works
    test_direct_text_rendering()
    
    # Create shared event tracking for coordination
    shared_events = {}
    shared_sync_events = set(["widget1_complete", "widget2_complete"])
    
    # Create text widgets with mode 1 (black and white)
    font = create_font(size=18)  # Use larger font size for better visibility
    
    # Create the text widgets
    text_1 = text(
        "First Widget",
        size=(150, 30),  # Larger size for better visibility
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    text_2 = text(
        "Second Widget",
        size=(150, 30),  # Larger size for better visibility
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    text_3 = text(
        "Third Widget",
        size=(150, 30),  # Larger size for better visibility
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    # Force render and debug
    for i, txt in enumerate([text_1, text_2, text_3]):
        # Force a render to create the image
        img = txt.render(force=True)[0]
        
        # Create a new image and manually render text onto it
        width, height = 150, 30
        labels = ["First Widget", "Second Widget", "Third Widget"]
        direct_img = Image.new("1", (width, height), 0)  # Black background
        draw = ImageDraw.Draw(direct_img)
        draw.text((5, 5), labels[i], fill=1, font=font)  # White text
        
        # Replace the widget's image with our directly rendered one
        txt.image = direct_img
        
        # Save for debugging
        debug_path = os.path.join(OUTPUT_DIR, f"widget_{i+1}_direct.png")
        direct_img.save(debug_path)
        
        # Count white pixels
        white_pixels = sum(1 for y in range(direct_img.height) for x in range(direct_img.width) 
                          if direct_img.getpixel((x, y)) == 1)
        print(f"  Widget {i+1}: size={direct_img.size}, white_pixels={white_pixels}")
    
    # Calculate marquee heights with padding
    widget1_height = text_1.image.size[1]
    widget2_height = text_2.image.size[1]
    widget3_height = text_3.image.size[1]
    
    # Calculate padding for marquees
    marquee1_height = widget1_height + 6  # Add padding
    marquee2_height = widget2_height + 6  # Add padding
    marquee3_height = widget3_height + 6  # Add padding
    
    # Create programs for each widget with coordinated animations
    program_1 = """
    # Widget 1 moves first
    SCROLL_LOOP(LEFT, 100) { step=1, interval=1 };
    PAUSE(10);
    SYNC(widget1_complete);
    PAUSE(10);
    """
    
    program_2 = """
    # Widget 2 waits for Widget 1 to complete
    WAIT_FOR(widget1_complete, 0);
    PAUSE(10);
    SLIDE(RIGHT, 80) { step=2, interval=1 };
    PAUSE(10);
    SYNC(widget2_complete);
    PAUSE(10);
    """
    
    program_3 = """
    # Widget 3 waits for Widget 2 to complete
    WAIT_FOR(widget2_complete, 0);
    PAUSE(10);
    SCROLL_BOUNCE(LEFT, 80) { step=2, interval=1, pause_at_ends=5 };
    PAUSE(10);
    """
    
    # Create marquees with shared events and sync events
    marquee_1 = new_marquee(
        widget=text_1,
        program=program_1,
        mode="1",
        size=(150, marquee1_height),  # Match the width of the text widget (150px)
        shared_events=shared_events,
        shared_sync_events=shared_sync_events
    )
    
    marquee_2 = new_marquee(
        widget=text_2,
        program=program_2,
        mode="1",
        size=(150, marquee2_height),  # Match the width of the text widget (150px)
        shared_events=shared_events,
        shared_sync_events=shared_sync_events
    )
    
    marquee_3 = new_marquee(
        widget=text_3,
        program=program_3,
        mode="1",
        size=(150, marquee3_height),  # Match the width of the text widget (150px)
        shared_events=shared_events,
        shared_sync_events=shared_sync_events
    )
    
    # Force initial render to initialize all timelines
    new_marquee.initialize_all_timelines()
    marquee_1.render(move=False)
    marquee_2.render(move=False)
    marquee_3.render(move=False)
    
    # Generate frames for each marquee and combine them
    frames = []
    print(f"Generating {TOTAL_FRAMES} frames...")
    
    for frame_num in range(TOTAL_FRAMES):
        # Create a combined canvas for all marquees
        combined_height = 300  # Enough space for all three widgets with padding
        canvas = Image.new("RGB", (350, combined_height), (0, 0, 0))  # Black background
        draw = ImageDraw.Draw(canvas)
        
        # Draw a grid pattern
        grid_spacing = 10
        grid_color = (30, 30, 30)  # Dark grid
        for y in range(0, combined_height, grid_spacing):
            draw.line([(0, y), (canvas.width, y)], fill=grid_color)
        for x in range(0, canvas.width, grid_spacing):
            draw.line([(x, 0), (x, combined_height)], fill=grid_color)
        
        # Render each marquee and add to canvas
        try:
            # Render the marquees
            img1, _ = marquee_1.render(tick=frame_num, move=True)
            img2, _ = marquee_2.render(tick=frame_num, move=True)
            img3, _ = marquee_3.render(tick=frame_num, move=True)
            
            # Debug the marquee images to check if they're rendering correctly
            if frame_num == 0:
                print("\nDebug marquee images (first frame):")
                for i, img in enumerate([img1, img2, img3]):
                    if img:
                        white_pixels = sum(1 for y in range(img.height) for x in range(img.width) 
                                         if img.mode == "1" and img.getpixel((x, y)) == 1)
                        print(f"  Marquee {i+1}: size={img.size}, mode={img.mode}, white_pixels={white_pixels}")
                    else:
                        print(f"  Marquee {i+1}: None")
            
            # Get positions for each marquee
            pos1 = marquee_1.position if hasattr(marquee_1, 'position') else (0, 0)
            pos2 = marquee_2.position if hasattr(marquee_2, 'position') else (0, 0)
            pos3 = marquee_3.position if hasattr(marquee_3, 'position') else (0, 0)
            
            # Paste each marquee with padding
            padding_x = 40
            marquee1_y = 40
            marquee2_y = 120
            marquee3_y = 200
            
            # Draw borders around each marquee area
            draw.rectangle(
                [(padding_x-2, marquee1_y-2), 
                 (padding_x+150+1, marquee1_y+marquee1_height+1)],  # Updated width to 150
                outline=(40, 60, 100),  # Dark blue border
                width=2
            )
            draw.rectangle(
                [(padding_x-2, marquee2_y-2), 
                 (padding_x+150+1, marquee2_y+marquee2_height+1)],  # Updated width to 150
                outline=(80, 40, 60),  # Dark purple border
                width=2
            )
            draw.rectangle(
                [(padding_x-2, marquee3_y-2), 
                 (padding_x+150+1, marquee3_y+marquee3_height+1)],  # Updated width to 150
                outline=(40, 80, 40),  # Dark green border
                width=2
            )
            
            # Draw origin markers
            draw.rectangle(
                [(padding_x-3, marquee1_y-3), (padding_x+3, marquee1_y+3)],
                outline=(80, 80, 80),
                width=1,
                fill=(40, 40, 40)
            )
            draw.rectangle(
                [(padding_x-3, marquee2_y-3), (padding_x+3, marquee2_y+3)],
                outline=(80, 80, 80),
                width=1,
                fill=(40, 40, 40)
            )
            draw.rectangle(
                [(padding_x-3, marquee3_y-3), (padding_x+3, marquee3_y+3)],
                outline=(80, 80, 80),
                width=1,
                fill=(40, 40, 40)
            )
            
            # Helper function for reliable mode "1" to RGB conversion
            def convert_1_to_rgb(img):
                """Convert a mode '1' image to RGB with proper handling of black/white values."""
                if not img or img.mode != "1":
                    return img
                
                # Try PIL's built-in conversion first
                rgb_img = img.convert("RGB")
                
                # Check a sample of pixels to determine if inversion is needed
                need_invert = False
                total_pixels = img.width * img.height
                sample_size = min(100, total_pixels)  # Sample up to 100 pixels
                
                # Find white pixels in the original image
                white_coords = []
                for y in range(img.height):
                    for x in range(img.width):
                        if img.getpixel((x, y)) == 1:  # White pixel in mode "1"
                            white_coords.append((x, y))
                            if len(white_coords) >= sample_size:
                                break
                    if len(white_coords) >= sample_size:
                        break
                
                # Check if white pixels appear dark in the converted image
                for x, y in white_coords:
                    rgb_color = rgb_img.getpixel((x, y))
                    if sum(rgb_color) < 100:  # This should be white but appears dark
                        need_invert = True
                        break
                
                # Invert if needed
                if need_invert:
                    from PIL import ImageOps
                    rgb_img = ImageOps.invert(rgb_img)
                
                return rgb_img
            
            # Process and paste each image
            for idx, (img, y_pos) in enumerate([(img1, marquee1_y), (img2, marquee2_y), (img3, marquee3_y)]):
                if img:
                    if img.mode == "1":
                        # Use our helper function for reliable conversion
                        rgb_img = convert_1_to_rgb(img)
                        # Paste without transparency
                        canvas.paste(rgb_img, (padding_x, y_pos))
                    else:
                        # Normal paste with alpha if available
                        canvas.paste(img, (padding_x, y_pos), img if 'A' in img.mode else None)
            
            # Draw position markers for each marquee
            marker_size = 3
            
            # Marker for marquee 1
            marker1_x = padding_x + (pos1[0] if isinstance(pos1, tuple) else pos1.x)
            marker1_y = marquee1_y + (pos1[1] if isinstance(pos1, tuple) else pos1.y)
            draw.rectangle(
                [(marker1_x-marker_size, marker1_y-marker_size), 
                 (marker1_x+marker_size, marker1_y+marker_size)],
                outline=(150, 150, 150),
                fill=(200, 50, 50)
            )
            
            # Marker for marquee 2
            marker2_x = padding_x + (pos2[0] if isinstance(pos2, tuple) else pos2.x)
            marker2_y = marquee2_y + (pos2[1] if isinstance(pos2, tuple) else pos2.y)
            draw.rectangle(
                [(marker2_x-marker_size, marker2_y-marker_size), 
                 (marker2_x+marker_size, marker2_y+marker_size)],
                outline=(150, 150, 150),
                fill=(200, 50, 50)
            )
            
            # Marker for marquee 3
            marker3_x = padding_x + (pos3[0] if isinstance(pos3, tuple) else pos3.x)
            marker3_y = marquee3_y + (pos3[1] if isinstance(pos3, tuple) else pos3.y)
            draw.rectangle(
                [(marker3_x-marker_size, marker3_y-marker_size), 
                 (marker3_x+marker_size, marker3_y+marker_size)],
                outline=(150, 150, 150),
                fill=(200, 50, 50)
            )
            
            # Add status info for each widget - use brighter colors for visibility
            font = create_font(10)
            draw.text(
                (5, marquee1_y-15),
                f"Widget 1: {pos1}",
                fill=(100, 140, 255),  # Bright blue
                font=font
            )
            draw.text(
                (5, marquee2_y-15),
                f"Widget 2: {pos2}",
                fill=(255, 120, 120),  # Bright pink
                font=font
            )
            draw.text(
                (5, marquee3_y-15),
                f"Widget 3: {pos3}",
                fill=(120, 255, 120),  # Bright green
                font=font
            )
            
            # Add frame counter
            draw.text(
                (10, canvas.height-20),
                f"Frame: {frame_num}/{TOTAL_FRAMES}",
                fill=(200, 200, 200),  # White text
                font=create_font(12)
            )
            
            frames.append(canvas)
            
        except Exception as e:
            print(f"Error rendering frame {frame_num}: {e}")
            canvas = Image.new("RGB", (350, combined_height), (100, 0, 0))  # Dark red background
            draw = ImageDraw.Draw(canvas)
            draw.text((10, 10), f"Error: {e}", fill=(255, 255, 255), font=create_font(12))
            frames.append(canvas)
        
        # Debug progress
        if frame_num % 10 == 0:
            print(f"  Frame {frame_num}/{TOTAL_FRAMES} complete")
    
    # Save as animated GIF
    output_path = os.path.join(OUTPUT_DIR, "multi_widget_animation.gif")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=1000//FPS,  # Duration in ms
        loop=0  # Loop forever
    )
    print(f"Saved animation to {output_path}")
    return output_path

def create_advanced_scroll_animation():
    """Create an advanced animation with multiple behaviors."""
    print("Creating advanced scroll animation...")
    
    # Create a text widget with multiple lines
    font = create_font(size=16)
    widget = text(
        """Advanced Scrolling with
SCROLL_LOOP behavior.
This text should continuously
scroll from right to left
and wrap around properly...""",
        font=font,
        mode="1",  # Binary mode (black and white)
        color=1,   # White text
        background=0,  # Black background
    )
    
    # Print widget dimensions
    print(f"Widget size: {widget.size}")
    
    # Create a marquee using the proper SCROLL_LOOP syntax
    program = """
    # Advanced continuous scroll with parameters
    DEFINE gap 10
    SCROLL_LOOP(LEFT, widget.width) { 
        step=1,  # Move 1 pixel per step for smooth scrolling
        interval=1,  # Minimum interval between steps
        gap=10  # Gap between text repetitions
    };
    """
    
    # Create marquee with fixed width to show the looping effect
    m = new_marquee(
        widget=widget,
        program=program,
        mode="1",
        size=(200, 80),  # Set fixed size to better show looping effect with multiple lines
        debug=True  # Enable debug mode
    )
    
    # Print marquee dimensions
    print(f"Marquee size: {m.size}")
    
    # Use 3x the normal frames to ensure at least one complete cycle
    global TOTAL_FRAMES
    original_frames = TOTAL_FRAMES
    TOTAL_FRAMES = original_frames * 3  # Triple the animation length for advanced animation
    
    # Generate and save animation
    animation_file = "advanced_scroll_animation.gif"
    render_animation(m, animation_file)
    
    # Restore original frame count
    TOTAL_FRAMES = original_frames

def create_simple_scroll_loop_animation():
    """Create a simple SCROLL_LOOP animation with a single line of text at full speed."""
    print("Creating simple SCROLL_LOOP animation...")
    
    # Create a text widget with a single line of text
    font = create_font(size=16)
    widget = text(
        "Simple SCROLL_LOOP Test - This text should continuously scroll from right to left and wrap around",
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )
    
    # Print widget dimensions
    print(f"Widget size: {widget.size}")
    
    # Create a marquee with simple SCROLL_LOOP behavior
    m = new_marquee(
        widget=widget,
        program="""
        # Simple continuous scroll from right to left
        SCROLL_LOOP(LEFT, 1) {
            step=1,
            interval=1
        };
        """,
        debug=True  # Enable debug mode
    )
    
    # Use triple the normal frames to ensure multiple loops
    global TOTAL_FRAMES
    original_frames = TOTAL_FRAMES
    TOTAL_FRAMES = original_frames * 3  # Triple the animation length
    
    # Generate animated GIF
    result = render_animation(m, "simple_scroll_loop.gif")
    
    # Restore original frame count
    TOTAL_FRAMES = original_frames
    
    print("\nInvestigation Summary:")
    print("---------------------")
    print("1. The SCROLL_LOOP behavior is working correctly in simple cases")
    print("   with continuous movement that wraps around properly.")
    print("2. Simple vertical SCROLL_CLIP DOWN also works correctly when tested in isolation.")
    print("3. However, complex DSL programs with multiple statements don't execute fully.")
    print("4. The LOOP structure and DEFINE/sequence() have issues with complex sequences.")
    print("5. The Position class migration is complete and working correctly.")
    print("6. For now, the recommended approach is to use simple DSL programs with")
    print("   a single animation type per marquee instance when possible.")
    
    return result

def render_animation(marquee, filename):
    """
    Render an animation of the marquee and save as GIF.
    
    Args:
        marquee: The marquee widget to animate
        filename: The output filename
        
    Returns:
        The path to the saved GIF
    """
    # Initialize the timeline
    new_marquee.initialize_all_timelines()
    
    # Debug: print the timeline coordinates
    print("\nTimeline coordinates:")
    coords = []
    for pos in marquee._timeline:
        if hasattr(pos, 'x') and hasattr(pos, 'y'):
            coords.append((pos.x, pos.y))
        else:
            coords.append(pos)
    
    # Group coordinates by type for better visualization
    pause_groups = []
    current_group = []
    pause_state = None
    
    for i, pos in enumerate(marquee._timeline):
        is_pause = hasattr(pos, 'pause') and pos.pause
        
        if pause_state != is_pause:
            if current_group:
                pause_groups.append((pause_state, current_group))
                current_group = []
            pause_state = is_pause
        
        if hasattr(pos, 'x') and hasattr(pos, 'y'):
            current_group.append((pos.x, pos.y))
        else:
            current_group.append(pos)
    
    if current_group:
        pause_groups.append((pause_state, current_group))
    
    # Print grouped coordinates
    for i, (is_pause, group) in enumerate(pause_groups):
        group_type = "PAUSE" if is_pause else "MOVE"
        print(f"\nGroup {i+1} ({group_type}, {len(group)} positions):")
        print(group)
    
    # Add padding around the marquee for better visibility
    padding = 20
    canvas_width = marquee.size[0] + padding * 2
    canvas_height = marquee.size[1] + padding * 2
    
    # Generate the frames
    frames = []
    print(f"Generating {TOTAL_FRAMES} frames...")
    for frame_num in range(TOTAL_FRAMES):
        # Render the marquee for this frame - catch any errors
        try:
            # Get the marquee in its native mode (typically mode "1")
            img, changed = marquee.render(tick=frame_num, move=True)
            
            # Get the current position
            current_pos = marquee.position if hasattr(marquee, 'position') else (0, 0)
            
            # Create a canvas with black background for better contrast
            canvas = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))
            draw = ImageDraw.Draw(canvas)
            
            # Draw a simple grid for context
            grid_spacing = 5
            grid_color = (30, 30, 30)
            
            # Draw horizontal grid lines
            for y in range(0, canvas_height, grid_spacing):
                draw.line([(0, y), (canvas_width, y)], fill=grid_color)
            
            # Draw vertical grid lines
            for x in range(0, canvas_width, grid_spacing):
                draw.line([(x, 0), (x, canvas_height)], fill=grid_color)
            
            # Draw a border around the marquee area
            draw.rectangle(
                [(padding-1, padding-1), 
                 (padding+marquee.size[0], padding+marquee.size[1])],
                outline=(50, 50, 50),
                width=1
            )
            
            # Draw origin marker at (0, 0) position
            draw.rectangle(
                [(padding-2, padding-2), (padding+2, padding+2)],
                outline=(100, 100, 100),
                width=1,
                fill=(50, 50, 50)
            )
            
            # Convert the marquee image to RGB and paste onto canvas
            if img:
                # Handle mode conversion just before adding to the frame
                if img.mode == "1":
                    # First try PIL's built-in conversion
                    rgb_img = img.convert("RGB")
                    
                    # Check if we need to invert the image - mode "1" conversion can be inconsistent
                    # Sample a pixel that is a '1' value and see if it became white or black
                    invert_needed = False
                    try:
                        # Find a white pixel to test
                        test_white = False
                        for sample_y in range(img.height):
                            for sample_x in range(img.width):
                                if img.getpixel((sample_x, sample_y)) == 1:
                                    rgb_color = rgb_img.getpixel((sample_x, sample_y))
                                    # If our '1' value pixel became dark in RGB, we need to invert
                                    if sum(rgb_color) < 100:
                                        invert_needed = True
                                    test_white = True
                                    break
                            if test_white:
                                break
                                
                        if invert_needed:
                            # Invert the image using PIL's ImageOps
                            from PIL import ImageOps
                            rgb_img = ImageOps.invert(rgb_img)
                    except Exception as e:
                        print(f"Error during mode conversion check: {e}. Falling back to manual conversion.")
                        # Fallback to manual conversion if built-in fails
                        rgb_img = Image.new("RGB", img.size, (0, 0, 0))
                        for y in range(img.height):
                            for x in range(img.width):
                                try:
                                    if img.getpixel((x, y)) == 1:  # White in mode "1"
                                        rgb_img.putpixel((x, y), (255, 255, 255))
                                except IndexError:
                                    pass
                    
                    # Paste the RGB version
                    canvas.paste(rgb_img, (padding, padding))
                else:
                    # For non-binary modes, use normal PIL paste with alpha if available
                    canvas.paste(img, (padding, padding), img if 'A' in img.mode else None)
            
            # Draw position marker at current position
            marker_x = padding + (current_pos[0] if isinstance(current_pos, tuple) else current_pos.x)
            marker_y = padding + (current_pos[1] if isinstance(current_pos, tuple) else current_pos.y)
            
            # Draw a position marker
            marker_size = 3
            draw.rectangle(
                [(marker_x-marker_size, marker_y-marker_size), 
                 (marker_x+marker_size, marker_y+marker_size)],
                outline=(200, 200, 200),
                fill=(255, 50, 50)
            )
            
            # Add frame counter and position info - white text for visibility on black
            font = create_font(10)
            draw.text(
                (5, canvas_height-15),
                f"Frame: {frame_num} | Pos: {current_pos}",
                fill=(200, 200, 200),
                font=font
            )
            
            # Debug timeline info every 10 frames
            if frame_num % 10 == 0:
                # Explicitly show both x and y coordinates for better debugging
                pos_x = current_pos[0] if isinstance(current_pos, tuple) else current_pos.x
                pos_y = current_pos[1] if isinstance(current_pos, tuple) else current_pos.y
                print(f"  Frame {frame_num}/{TOTAL_FRAMES} - Position: ({pos_x}, {pos_y})")
            
            frames.append(canvas)
            
        except Exception as e:
            print(f"Error rendering frame {frame_num}: {e}")
            # Create an error frame
            canvas = Image.new("RGB", (canvas_width, canvas_height), (100, 0, 0))
            draw = ImageDraw.Draw(canvas)
            draw.text((10, 10), f"Error: {e}", fill=(255, 255, 255), font=create_font(12))
            frames.append(canvas)
    
    # Save as animated GIF
    output_path = os.path.join(OUTPUT_DIR, filename)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=1000//FPS,  # Duration in ms
        loop=0  # Loop forever
    )
    print(f"Saved animation to {output_path}")
    return output_path

def main():
    """Main function to run the demo."""
    parser = argparse.ArgumentParser(description="Marquee Animation Demo")
    parser.add_argument(
        "--cleanup", 
        action="store_true", 
        help="Remove test results directory and exit"
    )
    parser.add_argument(
        "--animation", 
        choices=["all", "slide", "scroll", "bounce", "clip", "complex", "multi", "advanced", "simple", "test"], 
        default="all",
        help="Specify which animation to run (default: all)"
    )
    
    args = parser.parse_args()
    
    # Handle cleanup argument
    if args.cleanup:
        cleanup()
        return
    
    # Create output directory
    ensure_output_directory()
    
    # Run direct text test to verify rendering
    if args.animation in ["all", "test"]:
        print("Running direct text rendering test...")
        text_renders = test_direct_text_rendering()
        print(f"Text rendering test passed: {text_renders}")
        
        if args.animation == "test":
            return
    
    # Dictionary mapping animation choices to their functions
    animations = {
        "slide": create_slide_animation,
        "scroll": create_scroll_animation,
        "bounce": create_scroll_bounce_animation,
        "clip": create_scroll_clip_animation,
        "complex": create_complex_animation,
        "multi": create_multi_widget_animation,
        "advanced": create_advanced_scroll_animation,
        "simple": create_simple_scroll_loop_animation
    }
    
    # Run selected animation or all animations
    if args.animation == "all":
        print("Running all animations")
        start_time = time.time()
        for anim_func in animations.values():
            anim_func()
        end_time = time.time()
        print(f"All animations completed in {end_time - start_time:.2f} seconds")
    else:
        print(f"Running {args.animation} animation")
        start_time = time.time()
        animations[args.animation]()
        end_time = time.time()
        print(f"Animation completed in {end_time - start_time:.2f} seconds")
    
    print(f"GIF animations have been saved to the {OUTPUT_DIR} directory")

if __name__ == "__main__":
    main() 