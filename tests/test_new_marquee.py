"""
Test the new_marquee class that uses the Marquee DSL.
"""

import sys
import os
from pathlib import Path
import pytest
from PIL import Image

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee


def test_new_marquee_simple_move():
    """Test the new_marquee with a simple MOVE statement."""
    # Create a text widget
    message = text(value="Hello World", size=(100, 20))
    
    # Create a new_marquee that moves the text widget
    program = """
    MOVE(LEFT, 50) { step=1, interval=1 };
    """
    
    marquee_widget = new_marquee(
        widget=message,
        program=program,
        size=(100, 20)
    )
    
    # Render the initial state
    img1, _ = marquee_widget.render(reset=True, move=False)
    
    # Check initial position (0, 0)
    assert marquee_widget._curPos == (0, 0)
    
    # Move one tick
    img2, changed = marquee_widget.render(move=True)
    
    # Should have changed and moved left
    assert changed is True
    assert marquee_widget._curPos == (-1, 0)
    
    # Move a few more ticks and check position
    for i in range(5):
        img_next, _ = marquee_widget.render(move=True)
    
    # Should now be at position (-6, 0)
    assert marquee_widget._curPos == (-6, 0)


def test_new_marquee_loop():
    """Test the new_marquee with a LOOP statement."""
    # Create a text widget
    message = text(value="Testing Loop", size=(100, 20))
    
    # Create a program with a loop
    program = """
    LOOP(3) {
        MOVE(RIGHT, 10) { step=2 };
        PAUSE(2);
    } END;
    """
    
    marquee_widget = new_marquee(
        widget=message,
        program=program,
        size=(100, 20)
    )
    
    # Render the initial state
    marquee_widget.render(reset=True, move=False)
    
    # Execute multiple ticks and track positions
    positions = []
    for i in range(30):  # Should be enough to complete the animation
        marquee_widget.render(move=True)
        positions.append(marquee_widget._curPos)
    
    # Verify the pattern follows the expected loop behavior
    # Each loop: 5 moves right (by 2px) + 2 pauses = 7 ticks per loop × 3 loops = 21 ticks
    # We should see:
    # - 5 positions moving right in increments of 2 (0,0 → 2,0 → 4,0 → 6,0 → 8,0)
    # - 2 ticks paused at (10,0)
    # - Repeat 3 times
    
    # Check that we have rightward movement
    assert (2, 0) in positions
    assert (4, 0) in positions
    assert (6, 0) in positions
    assert (8, 0) in positions
    
    # Check for pauses - the same position appears consecutively
    pause_found = False
    for i in range(1, len(positions)):
        if positions[i] == positions[i-1]:
            pause_found = True
            break
    assert pause_found
    
    # Verify we end up at (0,0) after looping back
    assert positions[-1] == (0, 0)


def test_new_marquee_conditional():
    """Test the new_marquee with an IF statement."""
    # Create a text widget
    message = text(value="Testing IF", size=(100, 20))
    
    # Create a program with a conditional
    program = """
    IF(widget.x < 10) {
        MOVE(RIGHT, 20);
    } ELSE {
        MOVE(LEFT, 20);
    } END;
    """
    
    marquee_widget = new_marquee(
        widget=message,
        program=program,
        size=(100, 20)
    )
    
    # Render the initial state
    marquee_widget.render(reset=True, move=False)
    
    # Execute ticks and track positions
    positions = []
    for i in range(25):  # Should be enough to see the conditional behavior
        marquee_widget.render(move=True)
        positions.append(marquee_widget._curPos)
    
    # Verify the pattern follows the expected conditional behavior
    # We should initially move right until x >= 10, then move left
    
    # Check that we have rightward movement first
    assert (1, 0) in positions
    assert (5, 0) in positions
    assert (9, 0) in positions
    
    # Check that we eventually move left
    left_movement = False
    prev_x = None
    for pos in positions:
        if prev_x is not None and pos[0] < prev_x:
            left_movement = True
            break
        prev_x = pos[0]
    
    assert left_movement


def test_new_marquee_pause():
    """Test the new_marquee with a PAUSE statement."""
    # Create a text widget
    message = text(value="Testing Pause", size=(100, 20))
    
    # Create a program with a pause
    program = """
    MOVE(RIGHT, 10);
    PAUSE(5);
    MOVE(LEFT, 10);
    """
    
    marquee_widget = new_marquee(
        widget=message,
        program=program,
        size=(100, 20)
    )
    
    # Render the initial state
    marquee_widget.render(reset=True, move=False)
    
    # Execute ticks and check atPause property
    at_pause_detected = False
    at_pause_end_detected = False
    
    for i in range(20):  # Should be enough to complete the animation
        marquee_widget.render(move=True)
        
        if marquee_widget.atPause:
            at_pause_detected = True
        
        if marquee_widget.atPauseEnd:
            at_pause_end_detected = True
    
    # Verify pause events were detected
    assert at_pause_detected
    assert at_pause_end_detected


def test_new_marquee_reset_on_change():
    """Test the new_marquee with resetOnChange behavior."""
    # Create a text widget
    message = text(value="Original Text", size=(100, 20))
    
    # Create a program that moves right
    program = """
    MOVE(RIGHT, 50);
    """
    
    marquee_widget = new_marquee(
        widget=message,
        program=program,
        resetOnChange=True,
        size=(100, 20)
    )
    
    # Render the initial state
    marquee_widget.render(reset=True, move=False)
    
    # Move a few ticks
    for i in range(5):
        marquee_widget.render(move=True)
    
    # Save the current position which should be (5, 0)
    pos_before_change = marquee_widget._curPos
    assert pos_before_change[0] > 0
    
    # Change the text widget's value to trigger resetOnChange
    message._value = "New Text"
    
    # Render again - should reset position
    marquee_widget.render(move=True)
    
    # Position should be back to (0, 0)
    assert marquee_widget._curPos == (0, 0)


def test_moveWhen_pauses_animation():
    """Test that moveWhen controls animation progression."""
    # Create a text widget
    message = text(value="Testing moveWhen", size=(100, 20))
    
    # Create a program with movement
    program = """
    MOVE(RIGHT, 50);
    """
    
    # Create marquee with moveWhen=False to prevent movement
    marquee_widget = new_marquee(
        widget=message,
        program=program,
        moveWhen=False,
        size=(100, 20)
    )
    
    # Render the initial state
    marquee_widget.render(reset=True, move=False)
    
    # Initial position should be (0, 0)
    assert marquee_widget._curPos == (0, 0)
    
    # Render with move=True, but moveWhen=False should prevent movement
    marquee_widget.render(move=True)
    marquee_widget.render(move=True)
    marquee_widget.render(move=True)
    
    # Position should still be (0, 0)
    assert marquee_widget._curPos == (0, 0)
    
    # Change moveWhen to True and render again
    marquee_widget._moveWhen = True
    marquee_widget.render(move=True)
    
    # Now position should have changed
    assert marquee_widget._curPos != (0, 0)


if __name__ == "__main__":
    # Run tests manually
    test_new_marquee_simple_move()
    test_new_marquee_loop()
    test_new_marquee_conditional()
    test_new_marquee_pause()
    test_new_marquee_reset_on_change()
    test_moveWhen_pauses_animation()
    print("All tests passed!") 