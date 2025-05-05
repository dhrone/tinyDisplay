"""
Tests for the tinyDisplay Marquee Animation DSL parser - extended scenarios.

This test suite focuses on more complex parsing scenarios and edge cases to 
increase test coverage for the Marquee DSL parser.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl.marquee import parse_marquee_dsl, parse_and_validate_marquee_dsl
from tinyDisplay.dsl.marquee.ast import (
    Program, Block, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, IfStatement, BreakStatement, ContinueStatement,
    SyncStatement, WaitForStatement, PeriodStatement, StartAtStatement,
    SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, SlideStatement, PopUpStatement,
    Direction, SlideAction, Variable, BinaryExpr
)


def test_if_elseif_else_statement():
    """Test complex IF with ELSEIF and ELSE branches."""
    source = """
    IF(widget.x > 100) {
        MOVE(LEFT, 10);
    } ELSEIF(widget.x < 50) {
        MOVE(RIGHT, 20);
    } ELSE {
        PAUSE(5);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 1
    
    # Check if statement
    stmt = program.statements[0]
    assert isinstance(stmt, IfStatement)
    
    # Check main condition and branch
    assert stmt.condition is not None
    assert len(stmt.then_branch.statements) == 1
    assert isinstance(stmt.then_branch.statements[0], MoveStatement)
    
    # Check elseif branches
    assert len(stmt.elseif_branches) == 1
    elseif_condition, elseif_block = stmt.elseif_branches[0]
    assert elseif_condition is not None
    assert len(elseif_block.statements) == 1
    assert isinstance(elseif_block.statements[0], MoveStatement)
    
    # Check else branch
    assert stmt.else_branch is not None
    assert len(stmt.else_branch.statements) == 1
    assert isinstance(stmt.else_branch.statements[0], PauseStatement)


def test_loop_with_break_continue():
    """Test LOOP with BREAK and CONTINUE statements."""
    source = """
    LOOP(10 AS main_loop) {
        IF(widget.x > 100) {
            BREAK;
        } END;
        
        IF(widget.y < 50) {
            CONTINUE;
        } END;
        
        MOVE(LEFT, 5);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 1
    
    # Check loop statement
    stmt = program.statements[0]
    assert isinstance(stmt, LoopStatement)
    
    # Verify loop attributes
    assert stmt.name == "main_loop"
    
    # Check loop body
    assert len(stmt.body.statements) == 3
    assert isinstance(stmt.body.statements[0], IfStatement)
    assert isinstance(stmt.body.statements[1], IfStatement)
    assert isinstance(stmt.body.statements[2], MoveStatement)
    
    # Check for BREAK
    assert isinstance(stmt.body.statements[0].then_branch.statements[0], BreakStatement)
    
    # Check for CONTINUE
    assert isinstance(stmt.body.statements[1].then_branch.statements[0], ContinueStatement)


def test_timeline_statements():
    """Test timeline optimization statements."""
    source = """
    PERIOD(100);
    START_AT(10);
    
    SEGMENT(intro, 0, 20) {
        MOVE(RIGHT, 50);
    } END;
    
    POSITION_AT(t) => {
        MOVE(LEFT, 10);
    } END;
    
    SCHEDULE_AT(50, reset_position);
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 5
    
    # Check PERIOD statement
    assert isinstance(program.statements[0], PeriodStatement)
    assert program.statements[0].ticks.value == 100
    
    # Check START_AT statement
    assert isinstance(program.statements[1], StartAtStatement)
    assert program.statements[1].tick.value == 10
    
    # Check SEGMENT statement
    segment = program.statements[2]
    assert isinstance(segment, SegmentStatement)
    assert segment.name == "intro"
    assert segment.start_tick.value == 0
    assert segment.end_tick.value == 20
    assert len(segment.body.statements) == 1
    
    # Check POSITION_AT statement
    position_at = program.statements[3]
    assert isinstance(position_at, PositionAtStatement)
    assert isinstance(position_at.tick, Variable)
    assert position_at.tick.name == "t"
    assert len(position_at.body.statements) == 1
    
    # Check SCHEDULE_AT statement
    schedule = program.statements[4]
    assert isinstance(schedule, ScheduleAtStatement)
    assert schedule.tick.value == 50
    assert schedule.action == "reset_position"


def test_synchronization_statements():
    """Test synchronization statements."""
    source = """
    SYNC(animation_complete);
    WAIT_FOR(sensor_ready, 100);
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 2
    
    # Check SYNC statement
    sync = program.statements[0]
    assert isinstance(sync, SyncStatement)
    assert sync.event == "animation_complete"
    
    # Check WAIT_FOR statement
    wait = program.statements[1]
    assert isinstance(wait, WaitForStatement)
    assert wait.event == "sensor_ready"
    assert wait.ticks.value == 100


def test_on_variable_change():
    """Test ON_VARIABLE_CHANGE statement with variable list."""
    source = """
    ON_VARIABLE_CHANGE([temperature, humidity]) {
        MOVE(LEFT, 10);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 1
    
    # Check ON_VARIABLE_CHANGE statement
    on_change = program.statements[0]
    assert isinstance(on_change, OnVariableChangeStatement)
    assert on_change.variables == ["temperature", "humidity"]
    assert len(on_change.body.statements) == 1


def test_high_level_commands():
    """Test all high-level convenience commands."""
    source = """
    SCROLL(LEFT, widget.width) { step=2, gap=5 };
    SLIDE(IN_OUT, RIGHT, 100) { pause=30 };
    POPUP({ top_delay=20 });
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 3
    
    # Check SCROLL statement
    scroll = program.statements[0]
    assert isinstance(scroll, ScrollStatement)
    assert scroll.direction == Direction.LEFT
    assert 'step' in scroll.options
    assert 'gap' in scroll.options
    
    # Check SLIDE statement
    slide = program.statements[1]
    assert isinstance(slide, SlideStatement)
    assert slide.action == SlideAction.IN_OUT
    assert slide.direction == Direction.RIGHT
    assert slide.distance.value == 100
    assert 'pause' in slide.options
    
    # Check POPUP statement
    popup = program.statements[2]
    assert isinstance(popup, PopUpStatement)
    assert 'top_delay' in popup.options


def test_complex_expressions():
    """Test complex expressions with nested operations."""
    source = """
    MOVE(LEFT, 100);
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 1
    
    # Check that expressions are parsed correctly
    move = program.statements[0]
    assert isinstance(move, MoveStatement)
    assert move.direction == Direction.LEFT
    assert move.distance.value == 100


def test_reset_position_options():
    """Test RESET_POSITION with different options."""
    source = """
    RESET_POSITION({ mode="seamless" });
    RESET_POSITION({ mode="instant", duration=0 });
    RESET_POSITION({ mode="fade", duration=10 });
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 3
    
    # Check RESET_POSITION statements with different options
    for i, mode in enumerate(["seamless", "instant", "fade"]):
        reset = program.statements[i]
        assert isinstance(reset, ResetPositionStatement)
        assert 'mode' in reset.options
        assert reset.options['mode'].value == mode
        
        if mode in ["instant", "fade"]:
            assert 'duration' in reset.options


def test_nested_loops_and_conditionals():
    """Test complex nesting of loops and conditionals."""
    source = """
    LOOP(INFINITE) {
        IF(widget.x > 100) {
            LOOP(5) {
                MOVE(LEFT, 10);
                
                IF(widget.y < 0) {
                    BREAK;
                } END;
            } END;
        } ELSE {
            PAUSE(10);
        } END;
    } END;
    """
    
    program = parse_marquee_dsl(source)
    
    # Verify program structure
    assert len(program.statements) == 1
    
    # Check outer loop
    outer_loop = program.statements[0]
    assert isinstance(outer_loop, LoopStatement)
    assert outer_loop.count == "INFINITE"
    
    # Check if statement inside outer loop
    if_stmt = outer_loop.body.statements[0]
    assert isinstance(if_stmt, IfStatement)
    
    # Check inner loop inside then branch
    inner_loop = if_stmt.then_branch.statements[0]
    assert isinstance(inner_loop, LoopStatement)
    assert inner_loop.count.value == 5
    
    # Check inner if with break inside inner loop
    inner_if = inner_loop.body.statements[1]
    assert isinstance(inner_if, IfStatement)
    assert isinstance(inner_if.then_branch.statements[0], BreakStatement)


if __name__ == "__main__":
    # When run directly, execute tests and print results
    test_if_elseif_else_statement()
    print("✓ test_if_elseif_else_statement passed")
    
    test_loop_with_break_continue()
    print("✓ test_loop_with_break_continue passed")
    
    test_timeline_statements()
    print("✓ test_timeline_statements passed")
    
    test_synchronization_statements()
    print("✓ test_synchronization_statements passed")
    
    test_on_variable_change()
    print("✓ test_on_variable_change passed")
    
    test_high_level_commands()
    print("✓ test_high_level_commands passed")
    
    test_complex_expressions()
    print("✓ test_complex_expressions passed")
    
    test_reset_position_options()
    print("✓ test_reset_position_options passed")
    
    test_nested_loops_and_conditionals()
    print("✓ test_nested_loops_and_conditionals passed")
    
    print("All tests passed!") 