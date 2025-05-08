"""
Validator for the tinyDisplay Marquee Animation DSL.

This module provides a validator that checks the AST for semantic errors before execution.
"""
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass

from .ast import (
    Location, Expression, Literal, Variable, BinaryExpr, PropertyAccess,
    Statement, Block, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, Condition, IfStatement, BreakStatement, ContinueStatement,
    SyncStatement, WaitForStatement, TimelineStatement, PeriodStatement,
    StartAtStatement, SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, ScrollClipStatement, ScrollLoopStatement,
    ScrollBounceStatement, SlideStatement, PopUpStatement,
    Program, Direction, SlideAction, HighLevelCommandStatement
)


@dataclass
class ValidationError:
    """An error detected during validation."""
    location: Location
    message: str
    
    def __str__(self) -> str:
        return f"Validation error at {self.location}: {self.message}"


class Validator:
    """
    Validator for the tinyDisplay DSL.
    
    Checks the AST for semantic errors before execution.
    """
    
    def __init__(self, program: Program):
        """
        Initialize the validator with an AST.
        
        Args:
            program: The AST to validate.
        """
        self.program = program
        self.errors: List[ValidationError] = []
        
        # Track current scope for variables and loop validation
        self.in_loop: bool = False
        self.loop_stack: List[str] = []
        self.defined_variables: Set[str] = set()
        self.defined_events: Set[str] = set()
        
        # Track synchronization events
        self.defined_sync_events: Set[str] = set()
        self.used_sync_events: Set[str] = set()
        
        # Track timeline properties
        self.has_timeline_statements: bool = False
        self.in_segment: bool = False
        self.in_position_at: bool = False
        
        # Track segments for overlap detection
        self.segments: List[Tuple[str, int, int, Location]] = []
    
    def validate(self) -> List[ValidationError]:
        """
        Validate the AST.
        
        Returns:
            A list of validation errors, or an empty list if validation succeeded.
        """
        # Define standard variables
        self.defined_variables.update([
            "widget", "container", "current_tick",
        ])
        
        # Validate the program
        self._validate_program(self.program)
        
        # Check for undefined events - make this a softer warning
        # since events might be defined in another widget
        for event in self.used_sync_events:
            if event not in self.defined_sync_events:
                self.errors.append(ValidationError(
                    location=Location(0, 0),  # We don't have location for these post-validations
                    message=f"Event '{event}' is used but may need to be defined elsewhere."
                ))
        
        return self.errors
    
    def _validate_program(self, program: Program) -> None:
        """Validate a program (the root of the AST)."""
        for stmt in program.statements:
            self._validate_statement(stmt)
    
    def _validate_statement(self, stmt: Statement) -> None:
        """Validate any statement."""
        if isinstance(stmt, Block):
            self._validate_block(stmt)
        elif isinstance(stmt, MoveStatement):
            self._validate_move_statement(stmt)
        elif isinstance(stmt, PauseStatement):
            self._validate_pause_statement(stmt)
        elif isinstance(stmt, ResetPositionStatement):
            self._validate_reset_statement(stmt)
        elif isinstance(stmt, LoopStatement):
            self._validate_loop_statement(stmt)
        elif isinstance(stmt, IfStatement):
            self._validate_if_statement(stmt)
        elif isinstance(stmt, BreakStatement):
            self._validate_break_statement(stmt)
        elif isinstance(stmt, ContinueStatement):
            self._validate_continue_statement(stmt)
        elif isinstance(stmt, SyncStatement):
            self._validate_sync_statement(stmt)
        elif isinstance(stmt, WaitForStatement):
            self._validate_wait_for_statement(stmt)
        elif isinstance(stmt, TimelineStatement):
            self._validate_timeline_statement(stmt)
        elif isinstance(stmt, OnVariableChangeStatement):
            self._validate_on_variable_change_statement(stmt)
        elif isinstance(stmt, HighLevelCommandStatement):
            self._validate_high_level_command(stmt)
    
    def _validate_block(self, block: Block) -> None:
        """Validate a block of statements."""
        for stmt in block.statements:
            self._validate_statement(stmt)
    
    def _validate_move_statement(self, stmt: MoveStatement) -> None:
        """Validate a MOVE statement."""
        # Validate the movement parameters
        if stmt.direction is not None:
            # MOVE(direction, distance)
            if stmt.direction not in [Direction.LEFT, Direction.RIGHT, Direction.UP, Direction.DOWN]:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message=f"Invalid direction: {stmt.direction}. Expected LEFT, RIGHT, UP, or DOWN."
                ))
            self._validate_expression(stmt.distance)
        else:
            # MOVE(startX, endX, startY, endY)
            self._validate_expression(stmt.start_x)
            self._validate_expression(stmt.end_x)
            
            if stmt.start_y is not None and stmt.end_y is not None:
                self._validate_expression(stmt.start_y)
                self._validate_expression(stmt.end_y)
            elif stmt.start_y is not None or stmt.end_y is not None:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="If startY is provided, endY must also be provided, and vice versa."
                ))
        
        # Validate options
        self._validate_options(stmt.options, {
            "step": "integer",
            "interval": "integer",
            "easing": "string",
            "gap": "integer",
        }, stmt.location)
        
        # Validate that interval is not zero
        if "interval" in stmt.options and isinstance(stmt.options["interval"], Literal):
            if isinstance(stmt.options["interval"].value, int) and stmt.options["interval"].value == 0:
                self.errors.append(ValidationError(
                    location=stmt.options["interval"].location,
                    message="Interval must not be zero."
                ))
    
    def _validate_pause_statement(self, stmt: PauseStatement) -> None:
        """Validate a PAUSE statement."""
        self._validate_expression(stmt.duration)
        
        # Ensure duration is a positive number
        if isinstance(stmt.duration, Literal) and isinstance(stmt.duration.value, (int, float)):
            if stmt.duration.value < 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="PAUSE duration must be positive."
                ))
    
    def _validate_reset_statement(self, stmt: ResetPositionStatement) -> None:
        """Validate a RESET_POSITION statement."""
        # Validate options
        self._validate_options(stmt.options, {
            "mode": "string",
            "duration": "integer",
        }, stmt.location)
        
        # Validate mode value if present
        if "mode" in stmt.options:
            mode_expr = stmt.options["mode"]
            valid_modes = ["seamless", "instant", "fade"]
            
            if isinstance(mode_expr, Literal) and isinstance(mode_expr.value, str):
                mode = mode_expr.value
                if mode not in valid_modes:
                    self.errors.append(ValidationError(
                        location=mode_expr.location,
                        message=f"Invalid reset mode '{mode}'. Expected one of: {', '.join(valid_modes)}."
                    ))
            else:
                # For non-literal modes, we have to trust they'll be valid at runtime
                pass
    
    def _validate_loop_statement(self, stmt: LoopStatement) -> None:
        """Validate a LOOP statement."""
        # Validate loop count
        if isinstance(stmt.count, Expression):
            self._validate_expression(stmt.count)
            
            # Check if the count is a literal and ensure it's positive
            if isinstance(stmt.count, Literal) and isinstance(stmt.count.value, (int, float)):
                if stmt.count.value <= 0:
                    self.errors.append(ValidationError(
                        location=stmt.location,
                        message="Loop count must be positive."
                    ))
        elif stmt.count != "INFINITE":
            self.errors.append(ValidationError(
                location=stmt.location,
                message="Loop count must be a positive number or INFINITE."
            ))
        
        # Track loop context for BREAK and CONTINUE statements
        previous_in_loop = self.in_loop
        self.in_loop = True
        
        # Track named loops
        if stmt.name:
            self.loop_stack.append(stmt.name)
        
        # Validate loop body
        self._validate_block(stmt.body)
        
        # Restore loop context
        if stmt.name:
            self.loop_stack.pop()
        
        self.in_loop = previous_in_loop
    
    def _validate_if_statement(self, stmt: IfStatement) -> None:
        """Validate an IF statement."""
        # Validate main condition
        self._validate_condition(stmt.condition)
        
        # Validate then branch
        self._validate_block(stmt.then_branch)
        
        # Validate ELSEIF branches
        for condition, block in stmt.elseif_branches:
            self._validate_condition(condition)
            self._validate_block(block)
        
        # Validate ELSE branch if present
        if stmt.else_branch:
            self._validate_block(stmt.else_branch)
    
    def _validate_break_statement(self, stmt: BreakStatement) -> None:
        """Validate a BREAK statement."""
        if not self.in_loop:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="BREAK statement outside of a loop. BREAK can only be used inside a LOOP."
            ))
    
    def _validate_continue_statement(self, stmt: ContinueStatement) -> None:
        """Validate a CONTINUE statement."""
        if not self.in_loop:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="CONTINUE statement outside of a loop. CONTINUE can only be used inside a LOOP."
            ))
    
    def _validate_sync_statement(self, stmt: SyncStatement) -> None:
        """Validate a SYNC statement."""
        # Register event as defined
        self.defined_sync_events.add(stmt.event)
    
    def _validate_wait_for_statement(self, stmt: WaitForStatement) -> None:
        """Validate a WAIT_FOR statement."""
        # Register event as used
        self.used_sync_events.add(stmt.event)
        
        # We remove this strict check since events may be defined externally
        # or in another widget that shares events
        # if stmt.event not in self.defined_sync_events:
        #     self.errors.append(ValidationError(
        #         location=stmt.location,
        #         message=f"Event '{stmt.event}' used in WAIT_FOR statement is not defined."
        #     ))
        
        # Validate ticks
        self._validate_expression(stmt.ticks)
        
        # Ensure ticks is a positive number
        if isinstance(stmt.ticks, Literal) and isinstance(stmt.ticks.value, (int, float)):
            if stmt.ticks.value <= 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="WAIT_FOR ticks must be positive."
                ))
    
    def _validate_timeline_statement(self, stmt: TimelineStatement) -> None:
        """Validate a timeline statement."""
        self.has_timeline_statements = True
        
        if isinstance(stmt, PeriodStatement):
            self._validate_period_statement(stmt)
        elif isinstance(stmt, StartAtStatement):
            self._validate_start_at_statement(stmt)
        elif isinstance(stmt, SegmentStatement):
            self._validate_segment_statement(stmt)
        elif isinstance(stmt, PositionAtStatement):
            self._validate_position_at_statement(stmt)
        elif isinstance(stmt, ScheduleAtStatement):
            self._validate_schedule_at_statement(stmt)
    
    def _validate_period_statement(self, stmt: PeriodStatement) -> None:
        """Validate a PERIOD statement."""
        # Check if we're in a segment or position_at block
        if self.in_segment:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="PERIOD statement not allowed inside SEGMENT blocks."
            ))
            
        if self.in_position_at:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="PERIOD statement not allowed inside POSITION_AT blocks."
            ))
            
        self._validate_expression(stmt.ticks)
        
        # Ensure ticks is a positive number
        if isinstance(stmt.ticks, Literal) and isinstance(stmt.ticks.value, (int, float)):
            if stmt.ticks.value <= 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="PERIOD ticks must be positive."
                ))
    
    def _validate_start_at_statement(self, stmt: StartAtStatement) -> None:
        """Validate a START_AT statement."""
        # Check if we're in a segment or position_at block
        if self.in_segment:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="START_AT statement not allowed inside SEGMENT blocks."
            ))
            
        if self.in_position_at:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="START_AT statement not allowed inside POSITION_AT blocks."
            ))
            
        self._validate_expression(stmt.tick)
        
        # Ensure tick is not negative
        if isinstance(stmt.tick, Literal) and isinstance(stmt.tick.value, (int, float)):
            if stmt.tick.value < 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="START_AT tick must not be negative."
                ))
    
    def _validate_segment_statement(self, stmt: SegmentStatement) -> None:
        """Validate a SEGMENT statement."""
        # Check if we're already in a segment or position_at block
        if self.in_segment or self.in_position_at:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="Cannot nest SEGMENT statements inside other timeline blocks."
            ))
        
        self._validate_expression(stmt.start_tick)
        self._validate_expression(stmt.end_tick)
        
        # Ensure ticks are not negative
        if isinstance(stmt.start_tick, Literal) and isinstance(stmt.start_tick.value, (int, float)):
            if stmt.start_tick.value < 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="SEGMENT start_tick must not be negative."
                ))
        
        if isinstance(stmt.end_tick, Literal) and isinstance(stmt.end_tick.value, (int, float)):
            if stmt.end_tick.value < 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="SEGMENT end_tick must not be negative."
                ))
            
            # Check if the end tick is greater than the start tick
            if isinstance(stmt.start_tick, Literal) and isinstance(stmt.start_tick.value, (int, float)):
                if stmt.start_tick.value >= stmt.end_tick.value:
                    self.errors.append(ValidationError(
                        location=stmt.location,
                        message="SEGMENT end_tick must be greater than start_tick."
                    ))
            
            # Check for overlapping segments
            if isinstance(stmt.start_tick, Literal) and isinstance(stmt.end_tick, Literal):
                start = stmt.start_tick.value
                end = stmt.end_tick.value
                
                for seg_name, seg_start, seg_end, seg_loc in self.segments:
                    # Check if this segment overlaps with any existing segment
                    if (start <= seg_end and end >= seg_start):
                        self.errors.append(ValidationError(
                            location=stmt.location,
                            message=f"Segment '{stmt.name}' overlaps with segment '{seg_name}'. Segments must not overlap."
                        ))
                
                # Add this segment to the list
                self.segments.append((stmt.name, start, end, stmt.location))
                
        # Set context for nested validation
        prev_in_segment = self.in_segment
        self.in_segment = True
        
        # Validate body
        self._validate_block(stmt.body)
        
        # Restore context
        self.in_segment = prev_in_segment
    
    def _validate_position_at_statement(self, stmt: PositionAtStatement) -> None:
        """Validate a POSITION_AT statement."""
        # Check if we're already in a segment or position_at block
        if self.in_segment or self.in_position_at:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="Cannot nest POSITION_AT statements inside other timeline blocks."
            ))
            
        self._validate_expression(stmt.tick)
        
        # Ensure tick is not negative
        if isinstance(stmt.tick, Literal) and isinstance(stmt.tick.value, (int, float)):
            if stmt.tick.value < 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="POSITION_AT tick must not be negative."
                ))
        
        # Set context for nested validation
        prev_in_position_at = self.in_position_at
        self.in_position_at = True
        
        # Validate body
        self._validate_block(stmt.body)
        
        # Restore context
        self.in_position_at = prev_in_position_at
    
    def _validate_schedule_at_statement(self, stmt: ScheduleAtStatement) -> None:
        """Validate a SCHEDULE_AT statement."""
        # Check if we're in a segment or position_at block
        if self.in_segment:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="SCHEDULE_AT statement not allowed inside SEGMENT blocks."
            ))
            
        if self.in_position_at:
            self.errors.append(ValidationError(
                location=stmt.location,
                message="SCHEDULE_AT statement not allowed inside POSITION_AT blocks."
            ))
            
        self._validate_expression(stmt.tick)
        
        # Ensure tick is not negative
        if isinstance(stmt.tick, Literal) and isinstance(stmt.tick.value, (int, float)):
            if stmt.tick.value < 0:
                self.errors.append(ValidationError(
                    location=stmt.location,
                    message="SCHEDULE_AT tick must not be negative."
                ))
    
    def _validate_on_variable_change_statement(self, stmt: OnVariableChangeStatement) -> None:
        """Validate an ON_VARIABLE_CHANGE statement."""
        # Validate body
        self._validate_block(stmt.body)
    
    def _validate_high_level_command(self, stmt: HighLevelCommandStatement) -> None:
        """Validate a high-level command."""
        if isinstance(stmt, ScrollStatement):
            self._validate_scroll_statement(stmt)
        elif isinstance(stmt, ScrollClipStatement):
            self._validate_scroll_clip_statement(stmt)
        elif isinstance(stmt, ScrollLoopStatement):
            self._validate_scroll_loop_statement(stmt)
        elif isinstance(stmt, ScrollBounceStatement):
            self._validate_scroll_bounce_statement(stmt)
        elif isinstance(stmt, SlideStatement):
            self._validate_slide_statement(stmt)
        elif isinstance(stmt, PopUpStatement):
            self._validate_popup_statement(stmt)
    
    def _validate_scroll_statement(self, stmt: ScrollStatement) -> None:
        """Validate a SCROLL statement (legacy)."""
        self._validate_expression(stmt.distance)
        
        # Validate options
        self._validate_options(stmt.options, {
            "step": "integer",
            "interval": "integer",
            "gap": "integer",
            "repeat": "any",
            "reset_mode": "string",
        }, stmt.location)
    
    def _validate_scroll_clip_statement(self, stmt: ScrollClipStatement) -> None:
        """Validate a SCROLL_CLIP statement."""
        self._validate_expression(stmt.distance)
        
        # Validate options
        self._validate_options(stmt.options, {
            "step": "integer",
            "interval": "integer",
            "easing": "string",
            "pause_at_end": "integer",
            "auto_stop_when_invisible": "boolean",  # Whether to stop scrolling when widget is outside container
        }, stmt.location)
    
    def _validate_scroll_loop_statement(self, stmt: ScrollLoopStatement) -> None:
        """Validate a SCROLL_LOOP statement."""
        self._validate_expression(stmt.distance)
        
        # Validate options
        self._validate_options(stmt.options, {
            "step": "integer",
            "interval": "integer",
            "gap": "integer",
            "repeat": "any",
            "pause_at_wrap": "integer",
        }, stmt.location)
    
    def _validate_scroll_bounce_statement(self, stmt: ScrollBounceStatement) -> None:
        """Validate a SCROLL_BOUNCE statement."""
        self._validate_expression(stmt.distance)
        
        # Validate options
        self._validate_options(stmt.options, {
            "step": "integer",
            "interval": "integer",
            "pause_at_ends": "integer",
            "repeat": "any",
        }, stmt.location)
    
    def _validate_slide_statement(self, stmt: SlideStatement) -> None:
        """Validate a SLIDE statement."""
        self._validate_expression(stmt.distance)
        
        # Validate options
        self._validate_options(stmt.options, {
            "step": "integer",
            "interval": "integer",
            "easing": "string",
            "pause_after": "integer",
        }, stmt.location)
    
    def _validate_popup_statement(self, stmt: PopUpStatement) -> None:
        """Validate a POPUP statement."""
        # Validate options
        self._validate_options(stmt.options, {
            "top_delay": "integer",
            "bottom_delay": "integer",
            "screens": "integer",
            "step": "integer",
            "interval": "integer",
        }, stmt.location)
    
    def _validate_condition(self, condition: Condition) -> None:
        """Validate a condition."""
        self._validate_expression(condition.left)
        self._validate_expression(condition.right)
    
    def _validate_expression(self, expr: Expression) -> None:
        """Validate an expression."""
        if isinstance(expr, Literal):
            # Literals are always valid
            pass
        elif isinstance(expr, Variable):
            # Check if the variable is defined
            if expr.name not in self.defined_variables:
                # This is a soft error - the variable might be defined at runtime
                self.errors.append(ValidationError(
                    location=expr.location,
                    message=f"Variable '{expr.name}' used but not defined."
                ))
        elif isinstance(expr, BinaryExpr):
            # Validate both sides of the binary expression
            self._validate_expression(expr.left)
            self._validate_expression(expr.right)
        elif isinstance(expr, PropertyAccess):
            # Validate the object
            self._validate_expression(expr.object)
    
    def _validate_options(self, options: Dict[str, Expression], valid_options: Dict[str, str], location: Location) -> None:
        """
        Validate options.
        
        Args:
            options: The options to validate.
            valid_options: A dictionary of valid option names to expected types.
            location: The location for error reporting.
        """
        for name, expr in options.items():
            # Check if the option is valid
            if name not in valid_options:
                self.errors.append(ValidationError(
                    location=location,
                    message=f"Unknown option '{name}'."
                ))
                continue
            
            # Validate the expression
            self._validate_expression(expr)
            
            # Check the type if it's a literal
            if isinstance(expr, Literal):
                expected_type = valid_options[name]
                if expected_type == "integer" and not isinstance(expr.value, int):
                    self.errors.append(ValidationError(
                        location=expr.location,
                        message=f"Option '{name}' should be an integer, got {type(expr.value).__name__}."
                    ))
                elif expected_type == "string" and not isinstance(expr.value, str):
                    self.errors.append(ValidationError(
                        location=expr.location,
                        message=f"Option '{name}' should be a string, got {type(expr.value).__name__}."
                    )) 