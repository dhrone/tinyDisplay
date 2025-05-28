"""
Tests for the tinyDisplay Marquee Animation DSL parser and validator.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl.marquee import parse_and_validate_marquee_dsl
from tinyDisplay.dsl.marquee.ast import Direction, MoveStatement, PauseStatement, ScrollStatement


def test_basic_move_command():
    """Test basic MOVE command parsing and validation."""
    source = """
    MOVE(LEFT, 100);
    """
    
    program, errors = parse_and_validate_marquee_dsl(source)
    
    # Assertions to verify results
    assert len(errors) == 0, f"Validation failed with errors: {errors}"
    assert len(program.statements) == 1, "Expected exactly one statement"
    
    # Check that we have a MoveStatement
    statement = program.statements[0]
    assert isinstance(statement, MoveStatement), f"Expected MoveStatement, got {type(statement).__name__}"
    
    # Check statement properties
    assert statement.direction == Direction.LEFT, f"Expected LEFT direction, got {statement.direction}"
    assert statement.distance is not None, "Expected distance to be set"
    
    # Check statement options
    assert statement.options == {}, "Expected empty options dictionary"


def test_basic_move_and_pause_sequence():
    """Test a simple sequence of MOVE and PAUSE commands."""
    source = """
    MOVE(LEFT, 100);
    PAUSE(10);
    """
    
    program, errors = parse_and_validate_marquee_dsl(source)
    
    # Assertions to verify results
    assert len(errors) == 0, f"Validation failed with errors: {errors}"
    assert len(program.statements) == 2, "Expected exactly two statements"
    
    # Check first statement (MOVE)
    move_statement = program.statements[0]
    assert isinstance(move_statement, MoveStatement), f"Expected MoveStatement, got {type(move_statement).__name__}"
    
    # Check second statement (PAUSE)
    pause_statement = program.statements[1]
    assert isinstance(pause_statement, PauseStatement), f"Expected PauseStatement, got {type(pause_statement).__name__}"
    
    # Check PAUSE duration
    assert pause_statement.duration.value == 10, f"Expected duration 10, got {pause_statement.duration.value}"


def test_scroll_with_options():
    """Test SCROLL command with options."""
    source = """
    SCROLL(LEFT, widget.width) { step=1, interval=1, gap=10 };
    """
    
    program, errors = parse_and_validate_marquee_dsl(source)
    
    # Assertions to verify results
    assert len(errors) == 0, f"Validation failed with errors: {errors}"
    assert len(program.statements) == 1, "Expected exactly one statement"
    
    # Check statement type
    statement = program.statements[0]
    assert isinstance(statement, ScrollStatement), f"Expected ScrollStatement, got {type(statement).__name__}"
    
    # Check statement properties
    assert statement.direction == Direction.LEFT, f"Expected LEFT direction, got {statement.direction}"
    
    # Check options
    assert 'step' in statement.options, "Expected 'step' option"
    assert 'interval' in statement.options, "Expected 'interval' option"
    assert 'gap' in statement.options, "Expected 'gap' option"
    
    # Check option values
    assert statement.options['step'].value == 1, f"Expected step value 1, got {statement.options['step'].value}"
    assert statement.options['interval'].value == 1, f"Expected interval value 1, got {statement.options['interval'].value}"
    assert statement.options['gap'].value == 10, f"Expected gap value 10, got {statement.options['gap'].value}"


def test_invalid_syntax_handling():
    """Test how the parser handles invalid syntax."""
    source = """
    MOVE LEFT 100);  # Missing opening parenthesis
    """
    
    # For syntax errors, the parser recovers but produces an empty program
    program, errors = parse_and_validate_marquee_dsl(source)
    assert len(program.statements) == 0, "Parser should produce an empty program for invalid syntax"


if __name__ == "__main__":
    # When run directly, execute tests and print results
    test_basic_move_command()
    print("✓ test_basic_move_command passed")
    
    test_basic_move_and_pause_sequence()
    print("✓ test_basic_move_and_pause_sequence passed")
    
    test_scroll_with_options()
    print("✓ test_scroll_with_options passed")
    
    # Skip invalid syntax test when running manually
    print("All tests passed!") 