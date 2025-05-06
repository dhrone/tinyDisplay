"""
Comprehensive tests for the tinyDisplay Marquee Animation DSL.

This test suite implements all categories from the test plan to ensure
complete coverage of the Marquee Animation DSL functionality.
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
    Program, Block, Direction, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, IfStatement, BreakStatement, ContinueStatement,
    SyncStatement, WaitForStatement, PeriodStatement, StartAtStatement,
    SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, SlideStatement, PopUpStatement,
    SlideAction, Variable, BinaryExpr, Literal, PropertyAccess
)


class TestBasicMovementCommands:
    """Tests for Basic Movement Commands section from the test plan."""
    
    def test_move_with_coordinates(self):
        """Test MOVE with explicit coordinates."""
        source = """
        MOVE(10, 50);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], MoveStatement)
        assert program.statements[0].start_x.value == 10
        assert program.statements[0].end_x.value == 50
        assert program.statements[0].direction is None  # Using coordinates, not direction
    
    def test_two_dimensional_movement(self):
        """Test MOVE with 2D coordinates (from and to positions)."""
        source = """
        MOVE(10, 50, 20, 30);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], MoveStatement)
        assert program.statements[0].start_x.value == 10
        assert program.statements[0].end_x.value == 50
        assert program.statements[0].start_y.value == 20
        assert program.statements[0].end_y.value == 30
    
    def test_direction_constants(self):
        """Test all direction constants in MOVE command."""
        source = """
        MOVE(LEFT, 10);
        MOVE(RIGHT, 20);
        MOVE(UP, 30);
        MOVE(DOWN, 40);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 4
        
        directions = [Direction.LEFT, Direction.RIGHT, Direction.UP, Direction.DOWN]
        distances = [10, 20, 30, 40]
        
        for i, (direction, distance) in enumerate(zip(directions, distances)):
            assert isinstance(program.statements[i], MoveStatement)
            assert program.statements[i].direction == direction
            assert program.statements[i].distance.value == distance
    
    def test_move_with_options(self):
        """Test MOVE with various options."""
        source = """
        MOVE(LEFT, 100) { step=2, interval=3, easing="linear" };
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], MoveStatement)
        assert program.statements[0].direction == Direction.LEFT
        assert program.statements[0].distance.value == 100
        
        options = program.statements[0].options
        assert len(options) == 3
        assert options["step"].value == 2
        assert options["interval"].value == 3
        assert options["easing"].value == "linear"
    
    def test_reset_position_modes(self):
        """Test RESET_POSITION with different modes."""
        source = """
        RESET_POSITION({ mode="seamless" });
        RESET_POSITION({ mode="instant" });
        RESET_POSITION({ mode="fade", duration=5 });
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 3
        
        modes = ["seamless", "instant", "fade"]
        
        for i, mode in enumerate(modes):
            assert isinstance(program.statements[i], ResetPositionStatement)
            assert program.statements[i].options["mode"].value == mode
            
            if mode == "fade":
                assert "duration" in program.statements[i].options
                assert program.statements[i].options["duration"].value == 5


class TestControlFlow:
    """Tests for Control Flow section from the test plan."""
    
    def test_basic_loop(self):
        """Test finite loop count."""
        source = """
        LOOP(5) {
            MOVE(LEFT, 10);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], LoopStatement)
        assert program.statements[0].count.value == 5
        assert len(program.statements[0].body.statements) == 1
        assert isinstance(program.statements[0].body.statements[0], MoveStatement)
    
    def test_infinite_loop(self):
        """Test LOOP with INFINITE count."""
        source = """
        LOOP(INFINITE) {
            MOVE(LEFT, 10);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], LoopStatement)
        assert program.statements[0].count == "INFINITE"
    
    def test_named_loop(self):
        """Test LOOP with a name for later reference."""
        source = """
        LOOP(10 AS main_loop) {
            MOVE(LEFT, 10);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], LoopStatement)
        assert program.statements[0].count.value == 10
        assert program.statements[0].name == "main_loop"
    
    def test_if_statement(self):
        """Test simple IF condition."""
        source = """
        IF(widget.x > 100) {
            MOVE(LEFT, 10);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], IfStatement)
        assert program.statements[0].condition is not None
        assert len(program.statements[0].then_branch.statements) == 1
    
    def test_if_else_statement(self):
        """Test IF with ELSE branch."""
        source = """
        IF(widget.x > 100) {
            MOVE(LEFT, 10);
        } ELSE {
            MOVE(RIGHT, 20);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], IfStatement)
        assert program.statements[0].else_branch is not None
        assert len(program.statements[0].else_branch.statements) == 1
    
    def test_if_elseif_else_statement(self):
        """Test IF with multiple conditional branches."""
        source = """
        IF(widget.x > 100) {
            MOVE(LEFT, 10);
        } ELSEIF(widget.x < 50) {
            MOVE(RIGHT, 20);
        } ELSEIF(widget.y > 30) {
            MOVE(UP, 5);
        } ELSE {
            MOVE(DOWN, 15);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], IfStatement)
        assert len(program.statements[0].elseif_branches) == 2
        assert program.statements[0].else_branch is not None
    
    def test_break_statement(self):
        """Test BREAK inside loops."""
        source = """
        LOOP(10) {
            IF(widget.x > 100) {
                BREAK;
            } END;
            MOVE(LEFT, 5);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], LoopStatement)
        assert len(program.statements[0].body.statements) == 2
        
        if_stmt = program.statements[0].body.statements[0]
        assert isinstance(if_stmt, IfStatement)
        assert len(if_stmt.then_branch.statements) == 1
        assert isinstance(if_stmt.then_branch.statements[0], BreakStatement)
    
    def test_continue_statement(self):
        """Test CONTINUE inside loops."""
        source = """
        LOOP(10) {
            IF(widget.x < 50) {
                CONTINUE;
            } END;
            MOVE(LEFT, 5);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], LoopStatement)
        assert len(program.statements[0].body.statements) == 2
        
        if_stmt = program.statements[0].body.statements[0]
        assert isinstance(if_stmt, IfStatement)
        assert len(if_stmt.then_branch.statements) == 1
        assert isinstance(if_stmt.then_branch.statements[0], ContinueStatement)
    
    def test_nested_control_flow(self):
        """Test complex nesting of control structures."""
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
                IF(widget.y > 50) {
                    MOVE(UP, 5);
                } ELSE {
                    MOVE(DOWN, 5);
                } END;
            } END;
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], LoopStatement)
        assert program.statements[0].count == "INFINITE"
        
        # Check first level nesting
        outer_if = program.statements[0].body.statements[0]
        assert isinstance(outer_if, IfStatement)
        assert outer_if.else_branch is not None
        
        # Check second level nesting in then branch
        inner_loop = outer_if.then_branch.statements[0]
        assert isinstance(inner_loop, LoopStatement)
        assert inner_loop.count.value == 5
        
        # Check third level nesting
        inner_if = inner_loop.body.statements[1]
        assert isinstance(inner_if, IfStatement)
        assert isinstance(inner_if.then_branch.statements[0], BreakStatement)
        
        # Check second level nesting in else branch
        else_if = outer_if.else_branch.statements[0]
        assert isinstance(else_if, IfStatement)
        assert else_if.else_branch is not None


class TestHighLevelCommands:
    """Tests for High-Level Commands section from the test plan."""
    
    def test_scroll_command(self):
        """Test SCROLL with various options."""
        source = """
        SCROLL(LEFT, widget.width) { step=2, interval=50, gap=10 };
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], ScrollStatement)
        assert program.statements[0].direction == Direction.LEFT
        assert isinstance(program.statements[0].distance, PropertyAccess)
        
        options = program.statements[0].options
        assert len(options) == 3
        assert options["step"].value == 2
        assert options["interval"].value == 50
        assert options["gap"].value == 10
    
    def test_slide_command(self):
        """Test SLIDE with all actions and directions."""
        source = """
        SLIDE(IN, LEFT, 100) { duration=20 };
        SLIDE(OUT, RIGHT, 50) { duration=15 };
        SLIDE(IN_OUT, UP, 30) { pause=10 };
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 3
        
        actions = [SlideAction.IN, SlideAction.OUT, SlideAction.IN_OUT]
        directions = [Direction.LEFT, Direction.RIGHT, Direction.UP]
        distances = [100, 50, 30]
        
        for i, (action, direction, distance) in enumerate(zip(actions, directions, distances)):
            assert isinstance(program.statements[i], SlideStatement)
            assert program.statements[i].action == action
            assert program.statements[i].direction == direction
            assert program.statements[i].distance.value == distance
    
    def test_popup_command(self):
        """Test POPUP with custom delays and options."""
        source = """
        POPUP({ top_delay=20, bottom_delay=10, duration=30 });
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], PopUpStatement)
        
        options = program.statements[0].options
        assert len(options) == 3
        assert options["top_delay"].value == 20
        assert options["bottom_delay"].value == 10
        assert options["duration"].value == 30
    
    def test_high_level_command_combinations(self):
        """Test sequences of high-level commands."""
        source = """
        SCROLL(LEFT, widget.width) { step=1 };
        PAUSE(10);
        SLIDE(IN, RIGHT, 50);
        POPUP({});
        SLIDE(OUT, LEFT, 50);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 5
        assert isinstance(program.statements[0], ScrollStatement)
        assert isinstance(program.statements[1], PauseStatement)
        assert isinstance(program.statements[2], SlideStatement)
        assert isinstance(program.statements[3], PopUpStatement)
        assert isinstance(program.statements[4], SlideStatement)


class TestTimelineOptimization:
    """Tests for Timeline Optimization section from the test plan."""
    
    def test_period_statement(self):
        """Test PERIOD declaration."""
        source = """
        PERIOD(100);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], PeriodStatement)
        assert program.statements[0].ticks.value == 100
    
    def test_start_at(self):
        """Test START_AT for delayed start."""
        source = """
        START_AT(10);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], StartAtStatement)
        assert program.statements[0].tick.value == 10
    
    def test_segment(self):
        """Test SEGMENT for named animation sections."""
        source = """
        SEGMENT(intro, 0, 20) {
            MOVE(RIGHT, 50);
            PAUSE(5);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], SegmentStatement)
        assert program.statements[0].name == "intro"
        assert program.statements[0].start_tick.value == 0
        assert program.statements[0].end_tick.value == 20
        assert len(program.statements[0].body.statements) == 2
    
    def test_position_at(self):
        """Test position calculations with POSITION_AT."""
        source = """
        POSITION_AT(t) => {
            MOVE(LEFT, widget.width / 2);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], PositionAtStatement)
        assert isinstance(program.statements[0].tick, Variable)
        assert program.statements[0].tick.name == "t"
        assert len(program.statements[0].body.statements) == 1
    
    def test_schedule_at(self):
        """Test scheduled actions with SCHEDULE_AT."""
        source = """
        SCHEDULE_AT(50, reset_position);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], ScheduleAtStatement)
        assert program.statements[0].tick.value == 50
        assert program.statements[0].action == "reset_position"
    
    def test_on_variable_change(self):
        """Test variable change handling with ON_VARIABLE_CHANGE."""
        source = """
        ON_VARIABLE_CHANGE(temperature) {
            MOVE(LEFT, 10);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], OnVariableChangeStatement)
        assert program.statements[0].variables == ["temperature"]
        assert len(program.statements[0].body.statements) == 1
    
    def test_multiple_variable_monitoring(self):
        """Test monitoring multiple variables with ON_VARIABLE_CHANGE."""
        source = """
        ON_VARIABLE_CHANGE([temperature, humidity, pressure]) {
            MOVE(LEFT, 10);
            PAUSE(5);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], OnVariableChangeStatement)
        assert program.statements[0].variables == ["temperature", "humidity", "pressure"]
        assert len(program.statements[0].body.statements) == 2


class TestSynchronization:
    """Tests for Synchronization section from the test plan."""
    
    def test_sync_event(self):
        """Test SYNC event declaration."""
        source = """
        SYNC(animation_complete);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], SyncStatement)
        assert program.statements[0].event == "animation_complete"
    
    def test_wait_for(self):
        """Test WAIT_FOR with timeout."""
        source = """
        WAIT_FOR(sensor_ready, 100);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], WaitForStatement)
        assert program.statements[0].event == "sensor_ready"
        assert program.statements[0].ticks.value == 100
    
    def test_multiple_sync_points(self):
        """Test coordination between multiple sync points."""
        source = """
        SYNC(point_a);
        MOVE(LEFT, 50);
        SYNC(point_b);
        
        WAIT_FOR(point_a, 10);
        MOVE(RIGHT, 20);
        WAIT_FOR(point_b, 20);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 6
        assert isinstance(program.statements[0], SyncStatement)
        assert program.statements[0].event == "point_a"
        assert isinstance(program.statements[2], SyncStatement)
        assert program.statements[2].event == "point_b"
        assert isinstance(program.statements[3], WaitForStatement)
        assert program.statements[3].event == "point_a"
        assert isinstance(program.statements[5], WaitForStatement)
        assert program.statements[5].event == "point_b"


class TestErrorHandlingAndEdgeCases:
    """Tests for Error Handling & Edge Cases section from the test plan."""
    
    def test_syntax_errors(self):
        """Test recovery from various syntax errors."""
        source = """
        MOVE(LEFT; // Missing closing parenthesis and semicolon instead of )
        """
        
        program, errors = parse_and_validate_marquee_dsl(source)
        # We expect either parser errors or semantic errors
        assert program.is_empty or len(errors) > 0
    
    def test_semantic_errors(self):
        """Test validation of incorrect semantics."""
        source = """
        BREAK;  # BREAK outside of a loop
        """
        
        program, errors = parse_and_validate_marquee_dsl(source)
        assert len(errors) > 0  # Should have errors
        assert "break" in str(errors[0]).lower()  # Error should mention BREAK
    
    def test_empty_program(self):
        """Test parsing an empty string."""
        source = ""
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 0  # Should have no statements
    
    def test_complex_nesting(self):
        """Test deeply nested control structures."""
        source = """
        LOOP(5) {
            IF(widget.x > 100) {
                LOOP(3) {
                    IF(widget.y > 50) {
                        LOOP(2) {
                            MOVE(LEFT, 10);
                        } END;
                    } END;
                } END;
            } END;
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 1
        # Just verify it parses, detailed structure checks would be too verbose
    
    def test_comments(self):
        """Test parsing with different comment styles."""
        source = """
        # This is a single line comment
        MOVE(LEFT, 10);  # End of line comment
        /* This is a
           multi-line comment */
        PAUSE(5);
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 2
        assert isinstance(program.statements[0], MoveStatement)
        assert isinstance(program.statements[1], PauseStatement)
    
    def test_whitespace_handling(self):
        """Test parsing with various whitespace patterns."""
        source = """
        MOVE(LEFT,10);
        MOVE(  LEFT  ,  10  );
        MOVE(
            LEFT,
            10
        );
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 3
        for stmt in program.statements:
            assert isinstance(stmt, MoveStatement)
            assert stmt.direction == Direction.LEFT
            assert stmt.distance.value == 10


class TestCompleteAnimationSequences:
    """Tests for Complete Animation Sequences section from the test plan."""
    
    def test_marquee_scroll(self):
        """Test a complete text scrolling animation."""
        source = """
        # Define animation parameters
        PERIOD(200);
        START_AT(0);
        
        # Initial positioning
        MOVE(RIGHT, widget.width);
        
        # Main scrolling loop
        LOOP(INFINITE) {
            # Scroll text from right to left
            SCROLL(LEFT, widget.width + container.width) { step=1, interval=2 };
            
            # Pause at the end before restarting
            PAUSE(20);
            
            # Reset position for next iteration
            RESET_POSITION({ mode="seamless" });
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 4  # PERIOD, START_AT, MOVE, LOOP
        assert isinstance(program.statements[0], PeriodStatement)
        assert isinstance(program.statements[1], StartAtStatement)
        assert isinstance(program.statements[2], MoveStatement)
        assert isinstance(program.statements[3], LoopStatement)
        assert program.statements[3].count == "INFINITE"
        
        # Check loop body
        loop_body = program.statements[3].body.statements
        assert len(loop_body) == 3
        assert isinstance(loop_body[0], ScrollStatement)
        assert isinstance(loop_body[1], PauseStatement)
        assert isinstance(loop_body[2], ResetPositionStatement)
    
    def test_popup_animation(self):
        """Test a complete popup animation sequence."""
        source = """
        # Popup animation with phases
        PERIOD(100);
        
        # Initial popup
        POPUP({ top_delay=5, bottom_delay=10, duration=15 });
        
        # Wait for user interaction
        WAIT_FOR(user_interaction, 200);
        
        # Exit animation
        SLIDE(OUT, DOWN, 50) { duration=20 };
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 4
        assert isinstance(program.statements[0], PeriodStatement)
        assert isinstance(program.statements[1], PopUpStatement)
        assert isinstance(program.statements[2], WaitForStatement)
        assert isinstance(program.statements[3], SlideStatement)
        assert program.statements[3].action == SlideAction.OUT
        assert program.statements[3].direction == Direction.DOWN
    
    def test_multi_widget_coordination(self):
        """Test coordinated animations with multiple parts."""
        source = """
        # Define sync points
        SYNC(title_ready);
        SYNC(content_ready);
        
        # Title animation
        SEGMENT(title_animation, 0, 50) {
            SLIDE(IN, LEFT, 100);
            SYNC(title_ready);
        } END;
        
        # Content animation, waits for title
        SEGMENT(content_animation, 0, 100) {
            WAIT_FOR(title_ready, 60);
            SLIDE(IN, UP, 50);
            SYNC(content_ready);
        } END;
        
        # Footer animation, waits for content
        SEGMENT(footer_animation, 0, 150) {
            WAIT_FOR(content_ready, 120);
            SLIDE(IN, RIGHT, 30);
        } END;
        """
        
        program = parse_marquee_dsl(source)
        assert len(program.statements) == 5  # 2 SYNCs + 3 SEGMENTs
        
        # Check sync points
        assert isinstance(program.statements[0], SyncStatement)
        assert program.statements[0].event == "title_ready"
        assert isinstance(program.statements[1], SyncStatement)
        assert program.statements[1].event == "content_ready"
        
        # Check segments
        assert isinstance(program.statements[2], SegmentStatement)
        assert program.statements[2].name == "title_animation"
        assert isinstance(program.statements[3], SegmentStatement)
        assert program.statements[3].name == "content_animation"
        assert isinstance(program.statements[4], SegmentStatement)
        assert program.statements[4].name == "footer_animation"


if __name__ == "__main__":
    # When run directly, execute the tests
    pytest.main(["-xvs", __file__]) 