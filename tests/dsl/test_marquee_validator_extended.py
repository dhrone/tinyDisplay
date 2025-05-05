"""
Tests for the tinyDisplay Marquee Animation DSL validator - extended scenarios.

This test suite focuses on more complex validation cases and edge cases to
increase test coverage for the Marquee DSL validator.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl.marquee import (
    parse_marquee_dsl, validate_marquee_dsl, parse_and_validate_marquee_dsl
)
from tinyDisplay.dsl.marquee.validator import Validator, ValidationError


def test_move_with_zero_interval():
    """Test validation of MOVE with zero interval value."""
    source = """
    MOVE(LEFT, 100) { interval=0 };  # Zero interval not allowed
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error was reported
    assert len(errors) == 1
    assert "interval" in str(errors[0]).lower()
    assert "zero" in str(errors[0]).lower()


def test_negative_pause_values():
    """Test validation of negative PAUSE durations."""
    source = """
    PAUSE(-10);  # Negative duration not allowed
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error was reported
    assert len(errors) == 1
    assert "duration" in str(errors[0]).lower()
    assert "positive" in str(errors[0]).lower()


def test_multiple_validation_errors():
    """Test reporting of multiple validation errors."""
    source = """
    PAUSE(-5);  # Error 1: Negative pause
    BREAK;      # Error 2: BREAK outside loop
    PERIOD(0);  # Error 3: Zero period
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that all errors were reported
    assert len(errors) == 3


def test_complex_nested_statements_validation():
    """Test validation of timeline statements inside other blocks."""
    source = """
    POSITION_AT(10) => {  
        SEGMENT(inner, 10, 20) {  # Error: SEGMENT nested inside POSITION_AT
            PAUSE(5);
        } END;
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error about nested timeline statements was reported
    assert len(errors) == 1
    assert "segment" in str(errors[0]).lower()
    assert "inside" in str(errors[0]).lower() or "nest" in str(errors[0]).lower() or "timeline" in str(errors[0]).lower()


def test_nested_timeline_statements():
    """Test validation of nested timeline statements, which is not allowed."""
    source = """
    SEGMENT(outer, 0, 50) {
        MOVE(LEFT, 20);
        
        POSITION_AT(10) => {  # Error: POSITION_AT nested inside SEGMENT
            MOVE(RIGHT, 10);
        } END;
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error about nested POSITION_AT was reported
    assert len(errors) == 1
    assert "position_at" in str(errors[0]).lower()
    assert "inside" in str(errors[0]).lower() or "blocks" in str(errors[0]).lower()


def test_period_inside_timeline_blocks():
    """Test validation of PERIOD inside timeline blocks, which is not allowed."""
    source = """
    SEGMENT(test, 0, 100) {
        MOVE(LEFT, 20);
        PERIOD(50);  # Error: PERIOD not allowed inside SEGMENT
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error about PERIOD inside SEGMENT was reported
    assert len(errors) == 1
    assert "period" in str(errors[0]).lower()
    assert "inside segment" in str(errors[0]).lower()


def test_negative_tick_values():
    """Test validation of negative tick values in timeline statements."""
    source = """
    START_AT(-10);  # Error: Negative tick
    SEGMENT(test, -5, 20) {  # Error: Negative start tick
        MOVE(LEFT, 10);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that errors for negative ticks were reported
    assert len(errors) == 2
    assert any("not be negative" in str(error).lower() for error in errors)


def test_segment_validation():
    """Test validation of SEGMENT statements with various issues."""
    source = """
    SEGMENT(first, 0, 30) {
        MOVE(LEFT, 10);
    } END;
    
    SEGMENT(second, 20, 50) {  # Error: Overlaps with 'first'
        MOVE(RIGHT, 20);
    } END;
    
    SEGMENT(third, 60, 40) {  # Error: end < start
        MOVE(UP, 30);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that both segment errors were reported
    assert len(errors) == 2
    assert any("overlaps" in str(error).lower() for error in errors)
    assert any("greater than" in str(error).lower() for error in errors)


def test_wait_for_undefined_event():
    """Test validation of WAIT_FOR with undefined events."""
    source = """
    WAIT_FOR(nonexistent_event, 10);  # Error: Event not defined
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error about undefined event was reported
    # This test generates two errors - one during validation and one in post-validation
    assert len(errors) >= 1  
    assert any("not defined" in str(error).lower() for error in errors)
    assert any("nonexistent_event" in str(error).lower() for error in errors)


def test_invalid_reset_mode():
    """Test validation of RESET_POSITION with invalid mode."""
    source = """
    RESET_POSITION({ mode="invalid_mode" });  # Error: Invalid mode value
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error about invalid mode was reported
    assert len(errors) == 1
    assert "mode" in str(errors[0]).lower()
    assert "invalid" in str(errors[0]).lower()


def test_loop_count_validation():
    """Test validation of LOOP count values."""
    source = """
    LOOP(0) {  # Error: Zero not allowed for loop count
        MOVE(LEFT, 10);
    } END;
    
    LOOP(-5) {  # Error: Negative not allowed for loop count
        MOVE(RIGHT, 20);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that errors for invalid loop counts were reported
    assert len(errors) == 2
    assert all("loop count" in str(error).lower() for error in errors)
    assert all("positive" in str(error).lower() for error in errors)


def test_sync_and_wait_for_events():
    """Test validation of SYNC and WAIT_FOR statements with matching events."""
    source = """
    SYNC(animation_complete);  # Define event
    WAIT_FOR(animation_complete, 100);  # Use defined event
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate no errors were reported for valid event usage
    assert len(errors) == 0


def test_zero_wait_ticks():
    """Test validation of WAIT_FOR with zero ticks."""
    source = """
    SYNC(event);
    WAIT_FOR(event, 0);  # Error: Zero not allowed for wait ticks
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate that an error was reported for zero ticks
    assert len(errors) == 1
    assert "ticks" in str(errors[0]).lower()
    assert "positive" in str(errors[0]).lower()


def test_complex_valid_program():
    """Test a complex but valid program to ensure no false positives."""
    source = """
    /* Initialize timeline */
    START_AT(10);
    PERIOD(200);
    
    /* Define events */
    SYNC(intro_complete);
    
    /* Title animation */
    SEGMENT(intro, 10, 50) {
        MOVE(LEFT, 100) { step=2, interval=1 };
    } END;
    
    /* Wait for intro to complete */
    WAIT_FOR(intro_complete, 50);
    
    /* Main loop animation */
    LOOP(INFINITE) {
        IF(widget.x > container.width) {
            RESET_POSITION({ mode="seamless" });
        } END;
        
        MOVE(LEFT, widget.width + 20) { step=1, interval=1, gap=10 };
    } END;
    """
    
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    
    # Validate no errors were reported for this valid program
    assert len(errors) == 0


if __name__ == "__main__":
    # When run directly, execute tests and print results
    test_move_with_zero_interval()
    print("✓ test_move_with_zero_interval passed")
    
    test_negative_pause_values()
    print("✓ test_negative_pause_values passed")
    
    test_multiple_validation_errors()
    print("✓ test_multiple_validation_errors passed")
    
    test_complex_nested_statements_validation()
    print("✓ test_complex_nested_statements_validation passed")
    
    test_nested_timeline_statements()
    print("✓ test_nested_timeline_statements passed")
    
    test_period_inside_timeline_blocks()
    print("✓ test_period_inside_timeline_blocks passed")
    
    test_negative_tick_values()
    print("✓ test_negative_tick_values passed")
    
    test_segment_validation()
    print("✓ test_segment_validation passed")
    
    test_wait_for_undefined_event()
    print("✓ test_wait_for_undefined_event passed")
    
    test_invalid_reset_mode()
    print("✓ test_invalid_reset_mode passed")
    
    test_loop_count_validation()
    print("✓ test_loop_count_validation passed")
    
    test_sync_and_wait_for_events()
    print("✓ test_sync_and_wait_for_events passed")
    
    test_zero_wait_ticks()
    print("✓ test_zero_wait_ticks passed")
    
    test_complex_valid_program()
    print("✓ test_complex_valid_program passed")
    
    print("All tests passed!") 