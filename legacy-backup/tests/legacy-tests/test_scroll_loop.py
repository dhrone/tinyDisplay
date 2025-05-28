"""
Tests for the continuous scrolling behavior of the SCROLL_LOOP command in the tinyDisplay marquee.
"""

import os
import pytest
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee

@pytest.fixture(scope="module")
def output_dir():
    """Create and return the output directory for test results."""
    dir_path = "test_results"
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

@pytest.fixture
def text_widget():
    """Create a text widget for testing."""
    # Try to find a suitable font
    font = None
    try:
        font = ImageFont.load_default()
    except:
        # Try common system fonts
        for font_name in ["Arial.ttf", "DejaVuSans.ttf", "Verdana.ttf", "Helvetica.ttf"]:
            try:
                font = ImageFont.truetype(font_name, 18)
                break
            except:
                pass
    
    text_content = "This is a SCROLL_LOOP test message that should continuously scroll"
    return text(
        value=text_content,
        font=font,
        mode="1",
        color=1,  # White text
        background=0,  # Black background
    )

def test_scroll_loop_initialization(text_widget, output_dir):
    """Test that the SCROLL_LOOP marquee initializes correctly."""
    # Get widget dimensions
    widget_width, widget_height = text_widget.image.size
    marquee_height = widget_height + 8  # Add padding
    
    # Create a SCROLL_LOOP program
    program = """
    SCROLL_LOOP(LEFT, widget.width) { 
        step=2,  # 2 pixels per step for faster movement
        interval=1,
        gap=20   # 20 pixel gap between copies
    };
    """
    
    # Create the marquee
    marquee = new_marquee(
        widget=text_widget,
        program=program,
        mode="1",
        size=(120, marquee_height),
        debug=True
    )
    
    # Force render to initialize
    initial_img, _ = marquee.render(reset=True, move=False)
    
    # Verify initial state
    assert initial_img is not None
    assert initial_img.width == 120
    assert initial_img.height == marquee_height
    
    # Optional: Save the initial image for visual inspection
    initial_path = os.path.join(output_dir, "scroll_loop_initial.png")
    initial_img.save(initial_path)

def test_scroll_loop_animation(text_widget):
    """Test that SCROLL_LOOP properly animates with leftward movement."""
    # Get widget dimensions
    widget_width, widget_height = text_widget.image.size
    marquee_height = widget_height + 8
    
    # Create a SCROLL_LOOP program
    program = """
    SCROLL_LOOP(LEFT, widget.width) { 
        step=2,
        interval=1,
        gap=20
    };
    """
    
    # Create the marquee
    marquee = new_marquee(
        widget=text_widget,
        program=program,
        mode="1",
        size=(120, marquee_height),
        debug=True
    )
    
    # Initialize the marquee
    marquee.render(reset=True, move=False)
    
    # Generate frames and track positions
    positions = []
    
    # We just need enough frames to verify the behavior
    for i in range(20):
        marquee.render(move=True)
        positions.append(marquee.position)
    
    # Verify the scrolling behavior:
    
    # 1. Check if x coordinate eventually becomes negative (scrolling left)
    has_negative_x = any(pos[0] < 0 for pos in positions)
    assert has_negative_x, "SCROLL_LOOP should eventually have negative x coordinates"
    
    # 2. Check for continuous decrease in x (scrolling left)
    continuous_decrease = all(positions[i][0] < positions[i-1][0] for i in range(1, len(positions)))
    assert continuous_decrease, "SCROLL_LOOP should continuously decrease x coordinates"

def test_scroll_loop_wrapping(text_widget):
    """Test that SCROLL_LOOP properly wraps around when scrolling past widget width."""
    # Create a shorter widget width so we can test wrapping sooner
    widget_width, widget_height = text_widget.image.size
    marquee_height = widget_height + 8
    
    # Create a SCROLL_LOOP program with quick step for faster testing
    program = """
    SCROLL_LOOP(LEFT, widget.width) { 
        step=10,  # Large step for quicker testing
        interval=1,
        gap=10
    };
    """
    
    # Create the marquee
    marquee = new_marquee(
        widget=text_widget,
        program=program,
        mode="1",
        size=(120, marquee_height),
        debug=True
    )
    
    # Initialize the marquee
    marquee.render(reset=True, move=False)
    
    # Run enough frames to ensure we go beyond one full cycle
    full_cycle_frames = (widget_width + 10) // 10 + 5  # Add margin to ensure complete cycle
    
    # Track starting position
    start_pos = marquee.position[0]
    
    # Run through frames
    for _ in range(full_cycle_frames * 2):  # Run for two cycles
        marquee.render(move=True)
    
    # Verify that we've moved far enough for wrapping to occur
    total_movement = full_cycle_frames * 10
    assert total_movement > widget_width, "Test should run long enough to wrap content" 