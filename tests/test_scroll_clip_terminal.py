import pytest
from PIL import Image, ImageChops

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee
from tinyDisplay.dsl.marquee_executor import Position


def test_scroll_clip_terminal_flag():
    """Test that SCROLL_CLIP correctly sets and maintains the terminal flag."""
    # Create a text widget
    widget = text("SCROLL_CLIP Terminal Test")
    
    # Create a marquee with SCROLL_CLIP
    program = """
    SCROLL_CLIP(LEFT, 20) { 
        step=1,
        interval=1
    };
    SYNC("clip_complete");
    """
    
    # Create a marquee
    marquee = new_marquee(
        widget=widget, 
        program=program, 
        size=(100, 20)
    )
    
    # Initial render
    marquee.render(force=True)
    
    # Check that the timeline has been generated
    assert len(marquee._timeline) >= 20, "Timeline should have at least 20 positions"
    
    # Verify the timeline uses Position objects, not tuples
    for i, pos in enumerate(marquee._timeline):
        assert isinstance(pos, Position), f"Position {i} should be a Position object, not {type(pos)}"
    
    # The last position should have terminal=True for SCROLL_CLIP
    last_position = marquee._timeline[-1]
    assert hasattr(last_position, 'terminal'), "Last position should have a terminal attribute"
    
    # Move the marquee through its positions
    for i in range(len(marquee._timeline)):
        result = marquee.render()
        # Keep track of current position 
        current_pos = marquee._curPos
        
        # Check if we're at the last position
        if i == len(marquee._timeline) - 1:
            assert hasattr(current_pos, 'terminal'), "Final position should have terminal attribute"
            assert current_pos.terminal, "Terminal flag should be True for final position"
    
    # Check that after reaching the last position, the marquee stops advancing
    # Render a few more times
    last_pos = marquee._curPos
    for _ in range(5):
        marquee.render()
        # Position should stay the same because it's terminal
        assert marquee._curPos == last_pos, "Position should not change after reaching terminal position"
    
    # Verify the terminal flag is maintained
    assert hasattr(marquee._curPos, 'terminal'), "Terminal attribute should be maintained"
    assert marquee._curPos.terminal, "Terminal flag should remain True"
    
    
def test_scroll_clip_vs_loop():
    """Test the difference between SCROLL_CLIP (stops) and SCROLL_LOOP (continuous)."""
    # Create a text widget
    widget = text("Terminal vs Continuous Test")
    
    # Create a marquee with SCROLL_CLIP
    clip_program = """
    SCROLL_CLIP(LEFT, 20) { 
        step=1,
        interval=1
    };
    """
    
    clip_marquee = new_marquee(
        widget=widget, 
        program=clip_program, 
        size=(100, 20)
    )
    
    # Create a marquee with SCROLL_LOOP (should be continuous)
    loop_program = """
    SCROLL_LOOP(LEFT, 20) { 
        step=1,
        interval=1
    };
    """
    
    loop_marquee = new_marquee(
        widget=widget, 
        program=loop_program, 
        size=(100, 20)
    )
    
    # Initial render
    clip_marquee.render(force=True)
    loop_marquee.render(force=True)
    
    # Run both marquees for a full cycle 
    for i in range(max(len(clip_marquee._timeline), len(loop_marquee._timeline))):
        clip_marquee.render()
        loop_marquee.render()
    
    # Check the clip marquee's position after one more render
    clip_last_pos = clip_marquee._curPos
    clip_marquee.render()
    assert clip_marquee._curPos == clip_last_pos, "SCROLL_CLIP should stop at terminal position"
    
    # Check the loop marquee's position after one more render
    loop_last_pos = loop_marquee._curPos
    loop_marquee.render()
    assert loop_marquee._curPos != loop_last_pos, "SCROLL_LOOP should continue moving"
    
    # Verify terminal flags
    assert getattr(clip_marquee._curPos, 'terminal', False), "SCROLL_CLIP should have terminal flag set"
    assert not getattr(loop_marquee._curPos, 'terminal', False), "SCROLL_LOOP should not have terminal flag" 