"""
Test the new marquee behavior statements in the Marquee DSL.
"""

import sys
import os
from pathlib import Path
import pytest
from PIL import Image, ImageChops

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee
from tinyDisplay.utility import image2Text


def test_scroll_loop_behavior():
    """Test the SCROLL_LOOP behavior with seamless wrapping."""
    # Create a text widget wider than the container
    widget = text("This is a scrolling ticker message")
    
    # Create a SCROLL_LOOP program
    program = """
    SCROLL_LOOP(LEFT, widget.width) { 
        step=1, 
        interval=1, 
        gap=5 
    };
    """
    
    # Create a marquee with a narrow container
    container_width = 20
    container_height = 8
    marquee = new_marquee(
        widget=widget, 
        program=program, 
        size=(container_width, container_height)
    )
    
    # Initial render
    start_img, _ = marquee.render()
    
    # Ensure the scroll canvas was created with shadow copies
    assert hasattr(marquee, '_scroll_canvas')
    assert marquee._scroll_canvas.width > widget.image.width
    
    # Move through a complete cycle
    for _ in range(widget.image.width + 5):  
        end_img, _ = marquee.render()
    
    # Check if we're back at the start position (should loop)
    assert marquee.atStart, "Marquee didn't loop back to the start"
    
    # The image after one cycle should match the starting image
    diff = ImageChops.difference(start_img, end_img).getbbox()
    assert diff is None, f"Images don't match after one cycle {diff}\n{image2Text(start_img)}\n{image2Text(end_img)}"


def test_scroll_clip_behavior():
    """Test the SCROLL_CLIP behavior that scrolls and then stops."""
    # Create a text widget
    widget = text("Clipped scroll")
    
    # Create a SCROLL_CLIP program
    program = """
    SCROLL_CLIP(LEFT, 50) { 
        step=2,
        interval=1
    };
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget, 
        program=program, 
        size=(100, 20)
    )
    
    # Initial render
    marquee.render()
    start_pos = marquee._curPos
    
    # Track positions
    positions = [start_pos]
    
    # Run animation until it stops changing (should reach end and stop)
    max_iterations = 100  # Safety limit
    last_pos = start_pos
    for i in range(max_iterations):
        marquee.render()
        positions.append(marquee._curPos)
        
        # If position hasn't changed in several iterations, we've stopped
        if i > 5 and all(p == positions[-1] for p in positions[-5:]):
            break
    
    # Verify we stopped at a different position than start
    assert positions[-1] != start_pos, "SCROLL_CLIP didn't move"
    
    # Verify that the final position is reached and no more movement
    final_pos = positions[-1]
    marquee.render()  # One more render
    assert marquee._curPos == final_pos, "SCROLL_CLIP didn't stop at final position"
    
    # Check that we don't have shadow copies (SCROLL_CLIP doesn't need them)
    if hasattr(marquee, '_scroll_canvas'):
        assert marquee._scroll_canvas.width <= widget.image.width * 1.5, "Should not create shadow copies for SCROLL_CLIP"


def test_scroll_bounce_behavior():
    """Test the SCROLL_BOUNCE behavior that ping-pongs back and forth."""
    # Create a text widget
    widget = text("Bounce effect")
    
    # Create a SCROLL_BOUNCE program
    program = """
    SCROLL_BOUNCE(LEFT, 30) { 
        step=2,
        interval=1,
        pause_at_ends=2
    };
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget, 
        program=program, 
        size=(100, 20)
    )
    
    # Initial render
    marquee.render()
    start_pos = marquee._curPos
    
    # Track positions to detect direction changes
    positions = [start_pos]
    direction_changes = 0
    
    # Run animation long enough to see bounce behavior
    for _ in range(50):
        marquee.render()
        current_pos = marquee._curPos
        
        # Print position for debugging
        print(f"Position: ({current_pos[0]}, {current_pos[1]}) Pause: {hasattr(current_pos, 'pause') and current_pos.pause}")
        
        positions.append(current_pos)
        
        # Detect direction changes by looking at x coordinate trends
        if len(positions) >= 3:
            prev_direction = positions[-3][0] - positions[-2][0]
            current_direction = positions[-2][0] - positions[-1][0]
            
            # If sign changes, we've reversed direction
            if (prev_direction > 0 and current_direction < 0) or \
               (prev_direction < 0 and current_direction > 0):
                direction_changes += 1
                print(f"Direction change detected! Current direction: {current_direction}")
    
    # Should have at least one direction change (ideally two for a complete cycle)
    assert direction_changes > 0, "SCROLL_BOUNCE didn't change direction"
    
    # Check we have pauses at the ends
    has_pause = False
    for i in range(len(positions) - 1):
        # Check if consecutive positions have the same coordinates
        if positions[i][0] == positions[i+1][0] and positions[i][1] == positions[i+1][1]:
            has_pause = True
            print(f"Pause detected at positions[{i}] and positions[{i+1}]")
            break
    
    # If we didn't find pauses using coordinates, check the pause flag
    if not has_pause:
        for i, pos in enumerate(positions):
            if hasattr(pos, 'pause') and pos.pause:
                has_pause = True
                print(f"Pause flag detected at positions[{i}]")
                break
    
    assert has_pause, "SCROLL_BOUNCE didn't pause at the ends"


def test_slide_behavior():
    """Test the SLIDE behavior that moves in one direction and stops."""
    # Create a text widget
    widget = text("Slide effect")
    
    # Create a SLIDE program
    program = """
    SLIDE(RIGHT, 40) { 
        step=2,
        interval=1,
        easing=ease_out
    };
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget, 
        program=program, 
        size=(100, 20)
    )
    
    # Initial render
    marquee.render()
    start_pos = marquee._curPos
    
    # Run animation until it stops changing or maximum iterations
    positions = [start_pos]
    max_iterations = 50
    
    for i in range(max_iterations):
        marquee.render()
        positions.append(marquee._curPos)
        
        # If position hasn't changed in several iterations, we've stopped
        if i > 5 and all(p == positions[-1] for p in positions[-5:]):
            break
    
    # Verify we moved in the right direction (increasing x for RIGHT)
    assert positions[-1][0] > start_pos[0], "SLIDE didn't move in the right direction"
    
    # Verify we stopped moving at the end
    final_pos = positions[-1]
    for _ in range(5):
        marquee.render()
    assert marquee._curPos == final_pos, "SLIDE didn't stop at final position"


if __name__ == "__main__":
    # Run tests manually
    test_scroll_loop_behavior()
    test_scroll_clip_behavior()
    test_scroll_bounce_behavior()
    test_slide_behavior()
    print("All marquee behavior tests passed!") 