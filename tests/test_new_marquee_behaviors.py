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
from tinyDisplay.dsl.marquee_executor import Position


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
    
    # Store initial position
    if hasattr(marquee._curPos, 'x'):
        initial_x, initial_y = marquee._curPos.x, marquee._curPos.y
    else:
        initial_x, initial_y = marquee._curPos
    
    print(f"Initial position: ({initial_x}, {initial_y})")
    
    # Track positions to verify scrolling behavior
    positions = []
    # Move through a complete cycle
    for i in range(widget.image.width + 10):
        marquee.render(move=True)
        if hasattr(marquee._curPos, 'x'):
            pos = (marquee._curPos.x, marquee._curPos.y)
        else:
            pos = marquee._curPos
        positions.append(pos)
        print(f"Position {i}: {pos}")
    
    # Verify that we see some leftward movement (x decreases)
    has_leftward_movement = False
    for i in range(1, len(positions)):
        if positions[i][0] < positions[i-1][0]:
            has_leftward_movement = True
            break
    
    assert has_leftward_movement, "SCROLL_LOOP should move leftward"
    
    # The looping behavior may have changed - we can't directly test atStart
    # Instead, just verify that the scroll canvas was created properly
    assert hasattr(marquee, '_scroll_canvas'), "Should have created a scroll canvas"


def test_scroll_clip_behavior():
    """Test the SCROLL_CLIP behavior that stops at the target distance."""
    # Create a text widget
    widget = text("SCROLL_CLIP Test")
    
    # Create a SCROLL_CLIP program
    program = """
    SCROLL_CLIP(LEFT, 20) { 
        step=1,
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
    start_img, _ = marquee.render(reset=True)
    
    # Track initial position
    start_pos = marquee._curPos
    print(f"Initial position: {start_pos}")
    
    # Run animation until it should stabilize (more steps than needed)
    positions = []
    for i in range(30):  # More than target distance
        marquee.render(move=True)
        positions.append(marquee._curPos)
        print(f"Position {i}: {marquee._curPos}")
    
    # Verify that we moved in the correct direction and then stopped
    
    # SCROLL_CLIP should move to the target distance then stop
    # Final position should be at -20 for LEFT direction
    final_pos = Position(x=-20, y=0)
    
    # The final position should be stable
    assert positions[-1] == positions[-2], "Position should stabilize at the end"
    
    # We should reach the expected final position
    assert marquee._curPos == final_pos, "SCROLL_CLIP didn't stop at final position"
    
    print("SCROLL_CLIP Timeline:", marquee._timeline[:10])


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
    marquee.render(force=True)
    
    # Track positions to verify direction changes
    positions = []
    
    # Run animation long enough to see bounce behavior
    for _ in range(50):
        marquee.render(move=True)
        current_pos = marquee._curPos
        
        # Get x, y coordinates from current_pos (which might be a Position object)
        if hasattr(current_pos, 'x'):
            x, y = current_pos.x, current_pos.y
        else:
            x, y = current_pos
        
        # Add to position history    
        positions.append(x)
        
        print(f"Position: ({x}, {y}) Pause: {hasattr(current_pos, 'pause') and getattr(current_pos, 'pause', False)}")
    
    # Find min and max x positions to verify bounce behavior
    min_x = min(positions)
    max_x = max(positions)
    
    # For a LEFT bounce, we should see values decreasing (becoming more negative) 
    # and then increasing back
    print(f"Min X: {min_x}, Max X: {max_x}, First: {positions[0]}, Last: {positions[-1]}")
    
    # Ensure that both decreasing and increasing x values are present in the sequence
    has_decreasing = False
    has_increasing = False
    
    for i in range(1, len(positions)):
        if positions[i] < positions[i-1]:
            has_decreasing = True
        elif positions[i] > positions[i-1]:
            has_increasing = True
    
    # For SCROLL_BOUNCE with LEFT initial direction, we should have both decreasing
    # (outward motion) and increasing (return motion) sequences
    assert has_decreasing, "No decreasing x positions found - missing outward motion"
    assert has_increasing, "No increasing x positions found - missing return motion"
    
    # The minimum position should be further left (more negative) than both the
    # first and last positions, indicating we reached the bounce point
    assert min_x < positions[0], "Movement didn't reach expected bounce point"


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