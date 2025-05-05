"""
Tests for the tinyDisplay Marquee Animation DSL validator.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl.marquee import (
    parse_marquee_dsl, validate_marquee_dsl, parse_and_validate_marquee_dsl,
    MarqueeValidator, ValidationError
)
from tinyDisplay.dsl.marquee.ast import (
    Program, Block, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, IfStatement, BreakStatement, ContinueStatement
)


def test_break_outside_loop():
    """Test validation detects BREAK statement outside of a loop."""
    source = """
    MOVE(LEFT, 100);
    BREAK;  # Not inside a loop
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("outside a loop" in str(error) for error in errors)


def test_continue_outside_loop():
    """Test validation detects CONTINUE statement outside of a loop."""
    source = """
    MOVE(LEFT, 100);
    CONTINUE;  # Not inside a loop
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("outside a loop" in str(error) for error in errors)


def test_nested_break_continue():
    """Test validation accepts BREAK and CONTINUE inside nested loops."""
    source = """
    LOOP(5) {
        MOVE(LEFT, 10);
        
        LOOP(3) {
            BREAK;  # Valid - inside inner loop
        } END;
        
        CONTINUE;  # Valid - inside outer loop
    } END;
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert len(errors) == 0


def test_invalid_loop_count():
    """Test validation of invalid loop count."""
    source = """
    LOOP(-5) {  # Negative count
        MOVE(LEFT, 10);
    } END;
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("loop count must be positive" in str(error).lower() for error in errors)


def test_missing_end_statements():
    """Test validation of missing END statements."""
    source = """
    LOOP(5) {
        IF(widget.x > 10) {
            MOVE(LEFT, 10);
        } # Missing END for IF
    } END;
    """
    # This will likely fail at parse time rather than validation time
    # but we want to ensure validation catches any unclosed blocks
    _, errors = parse_and_validate_marquee_dsl(source)
    assert len(errors) > 0


def test_move_with_invalid_parameters():
    """Test validation of MOVE with invalid parameters."""
    source = """
    MOVE(DIAGONAL, 100);  # Invalid direction
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("invalid direction" in str(error).lower() for error in errors)


def test_conflicting_movement_options():
    """Test validation of conflicting MOVE options."""
    source = """
    MOVE(LEFT, 100) { step=5, interval=0 };  # interval cannot be 0
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("interval" in str(error).lower() for error in errors)


def test_negative_pause_duration():
    """Test validation of negative PAUSE duration."""
    source = """
    PAUSE(-10);  # Negative duration
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("duration must be positive" in str(error).lower() for error in errors)


def test_segment_overlapping_ticks():
    """Test validation of overlapping SEGMENT declarations."""
    source = """
    SEGMENT(intro, 0, 20) {
        MOVE(RIGHT, 50);
    } END;
    
    SEGMENT(main, 10, 30) {  # Overlaps with 'intro'
        MOVE(LEFT, 30);
    } END;
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("segments overlap" in str(error).lower() for error in errors)


def test_sync_wait_validation():
    """Test validation of SYNC and WAIT_FOR statements."""
    source = """
    SYNC(event1);  # No corresponding event
    WAIT_FOR(event2, 10);  # No corresponding event
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("event not defined" in str(error).lower() for error in errors)


def test_invalid_timeline_period():
    """Test validation of invalid PERIOD declarations."""
    source = """
    MOVE(LEFT, 100);
    PERIOD(0);  # Invalid - period cannot be 0
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("period must be positive" in str(error).lower() for error in errors)


def test_nested_timeline_statements():
    """Test validation of improperly nested timeline statements."""
    source = """
    MOVE(LEFT, 10);
    SEGMENT(test, 0, 20) {
        PERIOD(10);  # PERIOD not allowed inside SEGMENT
    } END;
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("not allowed inside segment" in str(error).lower() for error in errors)


def test_reset_position_invalid_mode():
    """Test validation of invalid RESET_POSITION mode."""
    source = """
    MOVE(LEFT, 100);
    RESET_POSITION({ mode=invalid });  # Invalid mode
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert any("invalid reset mode" in str(error).lower() for error in errors)


def test_complex_conditional_validation():
    """Test validation of complex conditional expressions."""
    source = """
    IF(widget.x > container.width && widget.opacity < 0.5) {
        MOVE(LEFT, 10);
    } ELSEIF(widget.y <= 0 || current_tick % 10 == 0) {
        MOVE(UP, 5);
    } ELSE {
        PAUSE(5);
    } END;
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    assert len(errors) == 0  # All expressions should be valid 