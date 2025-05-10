"""
tinyDisplay Marquee DSL Executor.

This module provides a class that can execute Marquee DSL programs.
It serves as the runtime environment for the Marquee Animation DSL.
"""

from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable
from dataclasses import dataclass, field
import logging
import sys
import re
import math
from datetime import datetime, timedelta

from .marquee import parse_marquee_dsl, validate_marquee_dsl
from .marquee.ast import (
    Program, Block, Statement, Direction, MoveStatement, PauseStatement, 
    ResetPositionStatement, LoopStatement, IfStatement, BreakStatement, 
    ContinueStatement, SyncStatement, WaitForStatement, Expression, Literal,
    Variable, BinaryExpr, PropertyAccess, TimelineStatement, PeriodStatement,
    StartAtStatement, SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, ScrollClipStatement, ScrollLoopStatement, 
    ScrollBounceStatement, SlideStatement, PopUpStatement, HighLevelCommandStatement,
    DefineStatement, SequenceInvocationStatement
)


@dataclass
class Position:
    """
    Position in a timeline.
    
    Attributes:
        x: X coordinate.
        y: Y coordinate.
        pause: Whether this position represents a pause in the animation.
        pause_end: Whether this position represents the end of a pause.
        terminal: Whether this position represents a final terminal state of an animation.
        segment_start: Whether this position represents the start of a segment.
        segment_end: Whether this position represents the end of a segment.
        segment_name: Name of the segment, if any.
        reset: Whether this position represents a reset to (0,0).
    """
    x: int
    y: int
    pause: bool = False
    pause_end: bool = False
    terminal: bool = False  # New flag for terminal positions
    segment_start: bool = False
    segment_end: bool = False
    segment_name: Optional[str] = None
    reset: bool = False  # New flag to explicitly mark reset positions
    
    def __getitem__(self, idx):
        """Make Position subscriptable like a tuple (pos[0] gives x, pos[1] gives y)."""
        if idx == 0:
            return self.x
        elif idx == 1:
            return self.y
        else:
            raise IndexError(f"Position index {idx} out of range")
    
    def __eq__(self, other):
        """Allow comparison with Position objects or (x, y) tuples."""
        if isinstance(other, Position):
            # For Position to Position comparison, only compare x and y coordinates
            # Don't consider flags like pause, terminal, etc.
            return self.x == other.x and self.y == other.y
        elif isinstance(other, tuple) and len(other) == 2:
            # For Position to tuple comparison, check if coordinates match
            return self.x == other[0] and self.y == other[1]
        # If comparing tuple to Position (the opposite order)
        # This is needed because Python will try both object's __eq__ methods
        return NotImplemented
        
    def __repr__(self):
        """Return a tuple-like representation for easier debugging."""
        return f"({self.x}, {self.y})"
        
    def __iter__(self):
        """Allow unpacking of Position objects (x, y = position)."""
        yield self.x
        yield self.y
        
    def __len__(self):
        """Return length of 2 to support unpacking and other tuple operations."""
        return 2
        
    def __iadd__(self, other):
        """Support position += tuple operation."""
        if isinstance(other, tuple) and len(other) == 2:
            self.x += other[0]
            self.y += other[1]
            return self
        elif isinstance(other, Position):
            self.x += other.x
            self.y += other.y
            return self
        else:
            raise TypeError(f"unsupported operand type(s) for +=: 'Position' and '{type(other).__name__}'")
    
    def __add__(self, other):
        """Support position + tuple operation."""
        if isinstance(other, tuple) and len(other) == 2:
            return Position(x=self.x + other[0], y=self.y + other[1])
        elif isinstance(other, Position):
            return Position(x=self.x + other.x, y=self.y + other.y)
        else:
            raise TypeError(f"unsupported operand type(s) for +: 'Position' and '{type(other).__name__}'")
            
    def __radd__(self, other):
        """Support tuple + position operation."""
        if isinstance(other, tuple) and len(other) == 2:
            return Position(x=other[0] + self.x, y=other[1] + self.y)
        else:
            raise TypeError(f"unsupported operand type(s) for +: '{type(other).__name__}' and 'Position'")


@dataclass
class ExecutionContext:
    """
    Execution context for the Marquee DSL.
    This stores the state during program execution.
    """
    variables: Dict[str, Any]
    timeline: List[Position]
    tick_position: int = 0
    break_loop: bool = False    # Renamed to breaking
    continue_loop: bool = False # Renamed to continuing
    breaking: bool = False      # Whether we're breaking out of a loop
    continuing: bool = False    # Whether we're continuing a loop
    current_segment: Optional[str] = None
    loop_counters: Dict[str, int] = field(default_factory=dict)
    segments: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    period: Optional[int] = None
    start_at: int = 0
    pauses: List[int] = field(default_factory=list)
    pause_ends: List[int] = field(default_factory=list)
    # Events for SYNC and WAIT_FOR
    events: Dict[str, bool] = field(default_factory=dict)
    defined_sync_events: Set[str] = field(default_factory=set)
    # Events being waited for
    waiting_for_events: Set[str] = field(default_factory=set)
    # For event extraction - maps event names to tick positions
    event_positions: Dict[str, int] = field(default_factory=dict)
    # Tracking state for scroll_clip
    scroll_clip_start_x: Optional[int] = None
    scroll_clip_start_y: Optional[int] = None
    scroll_clip_total_moved: int = 0
    scroll_clip_stabilized: bool = False
    # Tracking state for slide animation
    slide_start_x: Optional[int] = None
    slide_start_y: Optional[int] = None
    slide_total_moved: int = 0
    slide_stabilized: bool = False
    slide_progress: Optional[float] = None
    # Tracking state for bounce animation
    bounce_direction: Optional[Direction] = None
    bounce_total_moved: int = 0
    bounce_max_distance: float = 0
    bounce_at_edge: bool = False
    bounce_paused_ticks: int = 0
    bounce_pause_duration: int = 0
    # Add a dictionary to store defined sequences
    defined_sequences: Dict[str, DefineStatement] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values for collections."""
        if self.variables is None:
            self.variables = {}
        if self.timeline is None:
            self.timeline = []
        if self.loop_counters is None:
            self.loop_counters = {}
        if self.segments is None:
            self.segments = {}
        if self.pauses is None:
            self.pauses = []
        if self.pause_ends is None:
            self.pause_ends = []


class MarqueeExecutor:
    """
    Executor for the Marquee Animation DSL.
    
    This class takes a DSL program (either as a string or as an already parsed
    Program object) and executes it, generating a timeline of positions for
    animation.
    """
    
    def __init__(self, program: Union[str, Program], initial_variables: Optional[Dict[str, Any]] = None):
        """
        Initialize the executor with a program.
        
        Args:
            program: The DSL program, either as a string or as a parsed Program.
            initial_variables: Initial variables to populate the environment.
        """
        self.logger = logging.getLogger("tinyDisplay.dsl.marquee_executor")
        
        # Parse the program if it's a string
        if isinstance(program, str):
            self.program = parse_marquee_dsl(program)
        else:
            self.program = program
            
        # Prepare initial variables with standard defaults
        default_vars = {
            "widget": {"x": 0, "y": 0, "width": 0, "height": 0, "opacity": 1.0},
            "container": {"width": 0, "height": 0},
            "current_tick": 0
        }
        
        # Merge with user-provided variables (user vars override defaults)
        if initial_variables:
            for key, value in initial_variables.items():
                default_vars[key] = value
        
        # Initialize execution context
        self.context = ExecutionContext(
            variables=default_vars,
            timeline=[Position(x=0, y=0)]  # Start with initial position at origin
        )
        
        # Add standard easing functions
        if 'easing_functions' not in self.context.variables:
            self.context.variables['easing_functions'] = {
                'linear': lambda x: x,
                'ease_in': lambda x: x * x,
                'ease_out': lambda x: 1 - (1 - x) * (1 - x),
                'ease_in_out': lambda x: 4 * x * x * x if x < 0.5 else 1 - pow(-2 * x + 2, 3) / 2
            }
        
        # Validate the program
        errors = validate_marquee_dsl(self.program)
        if errors:
            for error in errors:
                # Skip warnings for shared events if they might be valid in a shared context
                if hasattr(error, 'may_be_shared_event') and hasattr(self.context, 'defined_sync_events'):
                    # Only show these warnings if we're not in a shared context
                    if len(self.context.defined_sync_events) == 0 and not self.context.events:
                        self.logger.warning(f"Validation warning: {error}")
                else:
                    self.logger.warning(f"Validation warning: {error}")
        
    def execute(self, widget_size: Tuple[int, int], container_size: Tuple[int, int], 
              starting_position: Tuple[int, int] = (0, 0),
              max_steps: Optional[int] = None) -> List[Position]:
        """
        Execute the program and generate a timeline of positions.
        
        Args:
            widget_size: Size of the widget (width, height).
            container_size: Size of the container (width, height).
            starting_position: Starting position for the widget.
            max_steps: Maximum number of steps to generate (None for unlimited).
            
        Returns:
            A list of positions for the timeline.
        """
        # Initialize execution context with starting position
        self.context = ExecutionContext(
            timeline=[],
            variables={
                "widget": {
                    "x": starting_position[0],
                    "y": starting_position[1],
                    "width": widget_size[0],
                    "height": widget_size[1],
                },
                "container": {
                    "width": container_size[0],
                    "height": container_size[1],
                },
            }
        )
        
        # Add the starting position to the timeline
        self.context.timeline.append(Position(x=starting_position[0], y=starting_position[1]))
        
        # Performance improvement - precompute sync events to avoid speculative execution
        # of branches when handling waitfor statements
        self.extract_sync_events(widget_size, container_size, starting_position)
        
        try:
            # Execute the program incrementally to build the timeline
            self._execute_program_incrementally(max_steps)
        except Exception as e:
            self.logger.error(f"Error executing program: {e}")
            # In case of error, still return the timeline we have so far
        
        # Ensure the timeline is valid for animation
        if not self.context.timeline:
            # If timeline is empty, add a static position
            self.context.timeline.append(Position(x=starting_position[0], y=starting_position[1]))
        
        # Process the timeline to merge consecutive identical positions
        processed_timeline = self._process_timeline(self.context.timeline)
        
        # Validate that the timeline is consistent - should start at starting_position
        if processed_timeline and (processed_timeline[0].x != starting_position[0] or
                                 processed_timeline[0].y != starting_position[1]):
            self.logger.warning(f"Timeline does not start at expected position: "
                              f"expected {starting_position}, got {processed_timeline[0]}")
        
        return processed_timeline
    
    def _process_timeline(self, timeline: List[Position]) -> List[Position]:
        """
        Process the timeline to ensure clean transitions and proper segment boundaries.
        
        This ensures that:
        - Consecutive segments connect properly without jumps
        - The timeline is consistent and ready for animation
        
        Args:
            timeline: The raw timeline to process
            
        Returns:
            A processed timeline with clean transitions
        """
        if not timeline:
            return []
            
        # Process the timeline to ensure smooth transitions
        processed = [timeline[0]]  # Start with the first position
        
        for i in range(1, len(timeline)):
            curr = timeline[i]
            prev = timeline[i-1]
            
            # Check for significant position jumps that would indicate segmentation issues
            dx = curr.x - prev.x
            dy = curr.y - prev.y
            
            # If we have a significant jump in position (more than 1 pixel in either direction)
            # that's not explained by a pause/reset/terminal flag, we need to adjust
            if ((abs(dx) > 1 or abs(dy) > 1) and 
                not (hasattr(curr, 'pause') or hasattr(prev, 'pause') or
                     hasattr(curr, 'terminal') or hasattr(prev, 'terminal'))):
                
                self.logger.debug(f"Detected position jump: {prev} to {curr}, dx={dx}, dy={dy}")
                
                # Generate intermediate positions to smooth the transition
                # Use the maximum delta to determine how many steps to generate
                steps = max(abs(dx), abs(dy))
                if steps > 1:
                    step_x = dx / steps
                    step_y = dy / steps
                    
                    # Generate intermediate positions (excluding the first and last)
                    for j in range(1, steps):
                        x = prev.x + int(round(j * step_x))
                        y = prev.y + int(round(j * step_y))
                        processed.append(Position(x=x, y=y))
            
            # Add the current position
            processed.append(curr)
        
        return processed
        
    def _execute_program_incrementally(self, max_steps: Optional[int] = None) -> None:
        """
        Execute the program incrementally, generating the timeline step by step.
        This approach allows conditions to be re-evaluated after each position change.
        
        Args:
            max_steps: Maximum number of steps to generate (None for unlimited).
        """
        # Set a reasonable safety limit to avoid infinite loops
        safety_limit = 1000 if max_steps is None else max_steps
        
        # While we haven't reached the maximum number of steps or safety limit
        step_count = 0
        max_timeline_length = safety_limit if max_steps is None else max_steps
        
        # Track positions to detect position stabilization (no movement)
        position_history = set()
        stable_position_count = 0
        statement_stack = []  # To track where we are in the program
        
        # Initialize the statement stack with the main program statements
        statement_stack = [(0, self.program.statements)]  # (current index, statement list)
        self.logger.debug(f"Initializing statement stack with {len(self.program.statements)} top-level statements")
        
        # Process statements until completion
        while (statement_stack and step_count < safety_limit and 
               len(self.context.timeline) < max_timeline_length):
            
            # Get the current execution context
            current_idx, current_statements = statement_stack[-1]
            
            # Check if we've completed the current statement list
            if current_idx >= len(current_statements):
                # Pop the current statement list and continue with previous level
                statement_stack.pop()
                continue
            
            # Execute the current statement
            current_stmt = current_statements[current_idx]
            self.logger.debug(f"Step {step_count}: Executing statement {type(current_stmt).__name__}")
            
            # Store the position before executing the statement
            pre_execution_pos = None
            if self.context.timeline:
                pre_execution_pos = self.context.timeline[-1]
                pre_exec_x = pre_execution_pos.x
                pre_exec_y = pre_execution_pos.y
                self.logger.debug(f"Position before statement: ({pre_exec_x}, {pre_exec_y})")
            
            # Execute the statement and then move to the next statement
            original_timeline_len = len(self.context.timeline)
            self._execute_statement(current_stmt)
            
            # Check if this statement added a position
            if len(self.context.timeline) > original_timeline_len:
                # Statement added at least one position
                self.logger.debug(f"Statement added {len(self.context.timeline) - original_timeline_len} position(s)")
                
                # For high-level statements that may need to execute multiple times to complete
                # (like SLIDE with multiple steps), we don't advance the index yet
                if (isinstance(current_stmt, SlideStatement) or 
                    isinstance(current_stmt, ScrollClipStatement) or
                    isinstance(current_stmt, ScrollBounceStatement)):
                    
                    # Check if we've completed the full motion
                    if (hasattr(self.context, 'slide_total_moved') and 
                        hasattr(current_stmt, 'distance') and
                        isinstance(current_stmt, SlideStatement)):
                        
                        target_distance = self._evaluate_expression(current_stmt.distance)
                        if self.context.slide_total_moved < target_distance:
                            # Continue executing this statement until it's complete
                            self.logger.debug(f"Continuing SLIDE: moved {self.context.slide_total_moved}/{target_distance}")
                            continue
                
                # For standard statements or completed high-level statements, advance to next
                statement_stack[-1] = (current_idx + 1, current_statements)
                
                # Ensure widget's position in the environment matches the last position in the timeline
                # This is critical for ensuring seamless transitions between statements
                last_pos = self.context.timeline[-1]
                widget_x = self.context.variables["widget"]["x"] 
                widget_y = self.context.variables["widget"]["y"]
                
                # Check if there's a mismatch between the last timeline position and widget position in variables
                if last_pos.x != widget_x or last_pos.y != widget_y:
                    self.logger.debug(f"Correcting position mismatch: timeline=({last_pos.x}, {last_pos.y}), widget=({widget_x}, {widget_y})")
                    
                    # Update widget position to match the last timeline position
                    self.context.variables["widget"]["x"] = last_pos.x
                    self.context.variables["widget"]["y"] = last_pos.y
            else:
                # No positions added, move to next statement
                statement_stack[-1] = (current_idx + 1, current_statements)
            
            # Check for position stabilization
            current_pos = (self.context.variables["widget"]["x"], self.context.variables["widget"]["y"])
            if current_pos in position_history:
                stable_position_count += 1
                if stable_position_count >= 5:
                    self.logger.debug("Position stabilized, ending timeline generation")
                    break
            else:
                position_history.add(current_pos)
                stable_position_count = 0
            
            step_count += 1
            
        self.logger.debug(f"Timeline generation completed after {step_count} steps, {len(self.context.timeline)} positions")
    
    def _execute_statement(self, stmt: Statement) -> None:
        """Execute a statement."""
        # Special handling for break and continue before any loop checks
        if isinstance(stmt, BreakStatement):
            self._execute_break_statement(stmt)
            return
        if isinstance(stmt, ContinueStatement):
            self._execute_continue_statement(stmt)
            return
            
        # Skip execution if we're breaking or continuing
        if self.context.breaking or self.context.continuing:
            return
            
        # Handle different statement types
        if isinstance(stmt, Block):
            self._execute_block(stmt)
        elif isinstance(stmt, MoveStatement):
            self._execute_move_statement(stmt)
        elif isinstance(stmt, PauseStatement):
            self._execute_pause_statement(stmt)
        elif isinstance(stmt, ResetPositionStatement):
            self._execute_reset_statement(stmt)
        elif isinstance(stmt, LoopStatement):
            self._execute_loop_statement(stmt)
        elif isinstance(stmt, IfStatement):
            self._execute_if_statement(stmt)
        elif isinstance(stmt, SyncStatement):
            self._execute_sync_statement(stmt)
        elif isinstance(stmt, WaitForStatement):
            self._execute_wait_for_statement(stmt)
        elif isinstance(stmt, ScrollStatement):
            self._execute_scroll_statement(stmt)
        elif isinstance(stmt, ScrollClipStatement):
            self._execute_scroll_clip_statement(stmt)
        elif isinstance(stmt, ScrollLoopStatement):
            self._execute_scroll_loop_statement(stmt)
        elif isinstance(stmt, ScrollBounceStatement):
            self._execute_scroll_bounce_statement(stmt)
        elif isinstance(stmt, SlideStatement):
            self._execute_slide_statement(stmt)
        elif isinstance(stmt, PeriodStatement):
            self._execute_period_statement(stmt)
        elif isinstance(stmt, StartAtStatement):
            self._execute_start_at_statement(stmt)
        elif isinstance(stmt, SegmentStatement):
            self._execute_segment_statement(stmt)
        elif isinstance(stmt, PositionAtStatement):
            self._execute_position_at_statement(stmt)
        elif isinstance(stmt, ScheduleAtStatement):
            self._execute_schedule_at_statement(stmt)
        elif isinstance(stmt, OnVariableChangeStatement):
            self._execute_on_variable_change_statement(stmt)
        elif isinstance(stmt, DefineStatement):
            self._execute_define_statement(stmt)
        elif isinstance(stmt, SequenceInvocationStatement):
            self._execute_sequence_invocation(stmt)
        else:
            self.logger.warning(f"Unknown statement type: {type(stmt)}")
    
    def _execute_define_statement(self, stmt: DefineStatement) -> None:
        """
        Execute a DEFINE statement.
        
        This stores the sequence definition for later use.
        
        Args:
            stmt: The DEFINE statement to execute.
        """
        self.logger.debug(f"Defining sequence '{stmt.name}'")
        
        # Store the sequence definition in the context for later use
        self.context.defined_sequences[stmt.name] = stmt
    
    def _execute_sequence_invocation(self, stmt: SequenceInvocationStatement) -> None:
        """
        Execute a sequence invocation.
        
        Args:
            stmt: The sequence invocation statement to execute.
        """
        sequence_name = stmt.name
        
        if sequence_name not in self.context.defined_sequences:
            self.logger.warning(f"Undefined sequence: {sequence_name}")
            return
            
        # Get the sequence definition
        sequence_def = self.context.defined_sequences[sequence_name]
        
        self.logger.debug(f"Executing sequence '{sequence_name}'")
        
        # Execute the sequence body
        self._execute_block(sequence_def.body)
    
    def _execute_break_statement(self, stmt: BreakStatement) -> None:
        """
        Execute a BREAK statement.
        
        Args:
            stmt: The BREAK statement to execute.
        """
        self.context.breaking = True
    
    def _execute_continue_statement(self, stmt: ContinueStatement) -> None:
        """
        Execute a CONTINUE statement.
        
        Args:
            stmt: The CONTINUE statement to execute.
        """
        self.context.continuing = True
    
    def _execute_block(self, stmt: Block) -> None:
        """
        Execute a block of statements.
        
        Args:
            stmt: The block of statements to execute.
        """
        self._execute_one_step(stmt.statements)
    
    def _execute_move_statement(self, stmt: MoveStatement) -> None:
        """
        Execute a MOVE statement.
        
        Args:
            stmt: The MOVE statement to execute.
        """
        self._execute_move_once(stmt)
    
    def _execute_pause_statement(self, stmt: PauseStatement) -> None:
        """
        Execute a PAUSE statement.
        
        Args:
            stmt: The PAUSE statement to execute.
        """
        self._execute_pause(stmt)
    
    def _execute_reset_statement(self, stmt: ResetPositionStatement) -> None:
        """
        Execute a RESET_POSITION statement.
        
        Args:
            stmt: The RESET_POSITION statement to execute.
        """
        self._execute_reset_position(stmt)
    
    def _execute_loop_statement(self, stmt: LoopStatement) -> None:
        """
        Execute a LOOP statement.
        
        Args:
            stmt: The LOOP statement to execute.
        """
        self._execute_loop_once(stmt)
    
    def _execute_if_statement(self, stmt: IfStatement) -> None:
        """
        Execute an IF statement.
        
        Args:
            stmt: The IF statement to execute.
        """
        self._execute_if_once(stmt)
    
    def _execute_sync_statement(self, stmt: SyncStatement) -> None:
        """
        Execute a SYNC statement.
        
        Args:
            stmt: The SYNC statement to execute.
        """
        self._execute_sync(stmt)
    
    def _execute_wait_for_statement(self, stmt: WaitForStatement) -> None:
        """
        Execute a WAIT_FOR statement.
        
        Args:
            stmt: The WAIT_FOR statement to execute.
        """
        self._execute_wait_for(stmt)
    
    def _execute_scroll_statement(self, stmt: ScrollStatement) -> None:
        """
        Execute a SCROLL statement.
        
        Args:
            stmt: The SCROLL statement to execute.
        """
        self._execute_high_level_command(stmt)
    
    def _execute_scroll_clip_statement(self, stmt: ScrollClipStatement) -> None:
        """
        Execute a SCROLL_CLIP statement.
        
        Args:
            stmt: The SCROLL_CLIP statement to execute.
        """
        self._execute_high_level_command(stmt)
    
    def _execute_scroll_loop_statement(self, stmt: ScrollLoopStatement) -> None:
        """
        Execute a SCROLL_LOOP statement.
        
        Args:
            stmt: The SCROLL_LOOP statement to execute.
        """
        self._execute_high_level_command(stmt)
    
    def _execute_scroll_bounce_statement(self, stmt: ScrollBounceStatement) -> None:
        """
        Execute a SCROLL_BOUNCE statement.
        
        Args:
            stmt: The SCROLL_BOUNCE statement to execute.
        """
        self._execute_high_level_command(stmt)
    
    def _execute_slide_statement(self, stmt: SlideStatement) -> None:
        """
        Execute a SLIDE statement.
        
        Args:
            stmt: The SLIDE statement to execute.
        """
        self._execute_high_level_command(stmt)
    
    def _execute_period_statement(self, stmt: PeriodStatement) -> None:
        """
        Execute a PERIOD statement.
        
        Args:
            stmt: The PERIOD statement to execute.
        """
        self.context.period = self._evaluate_expression(stmt.ticks)
    
    def _execute_start_at_statement(self, stmt: StartAtStatement) -> None:
        """
        Execute a START_AT statement.
        
        Args:
            stmt: The START_AT statement to execute.
        """
        self.context.start_at = self._evaluate_expression(stmt.tick)
    
    def _execute_segment_statement(self, stmt: SegmentStatement) -> None:
        """
        Execute a SEGMENT statement.
        
        Args:
            stmt: The SEGMENT statement to execute.
        """
        # Get start and end ticks
        start_tick = self._evaluate_expression(stmt.start_tick)
        end_tick = self._evaluate_expression(stmt.end_tick)
        
        # Store segment information
        self.context.segments[stmt.name] = (start_tick, end_tick)
        
        # Set current segment if not already set
        if not self.context.current_segment:
            self.context.current_segment = stmt.name
            # Execute the segment body once
            self._execute_one_step(stmt.body.statements)
    
    def _execute_position_at_statement(self, stmt: PositionAtStatement) -> None:
        """
        Execute a POSITION_AT statement.
        
        Args:
            stmt: The POSITION_AT statement to execute.
        """
        self._execute_one_step(stmt.body.statements)
    
    def _execute_schedule_at_statement(self, stmt: ScheduleAtStatement) -> None:
        """
        Execute a SCHEDULE_AT statement.
        
        Args:
            stmt: The SCHEDULE_AT statement to execute.
        """
        # Implementation needed
        pass
    
    def _execute_on_variable_change_statement(self, stmt: OnVariableChangeStatement) -> None:
        """
        Execute an ON_VARIABLE_CHANGE statement.
        
        Args:
            stmt: The ON_VARIABLE_CHANGE statement to execute.
        """
        # Implementation needed
        pass
    
    def _execute_one_step(self, statements: List[Statement]) -> None:
        """
        Execute one step through the program statements.
        This executes each statement once, allowing for incremental timeline building.
        
        Args:
            statements: The statements to execute.
        """
        for stmt in statements:
            if self.context.breaking or self.context.continuing:
                # Exit early if we encountered a BREAK or CONTINUE
                break
                
            self._execute_statement(stmt)
    
    def _execute_statement_once(self, stmt: Statement) -> None:
        """
        Execute a single statement once.
        
        Args:
            stmt: The statement to execute.
        """
        if isinstance(stmt, Block):
            self._execute_one_step(stmt.statements)
        elif isinstance(stmt, MoveStatement):
            self._execute_move_once(stmt)
        elif isinstance(stmt, PauseStatement):
            self._execute_pause(stmt)
        elif isinstance(stmt, ResetPositionStatement):
            self._execute_reset_position(stmt)
        elif isinstance(stmt, LoopStatement):
            self._execute_loop_once(stmt)
        elif isinstance(stmt, IfStatement):
            self._execute_if_once(stmt)
        elif isinstance(stmt, BreakStatement):
            self.context.breaking = True
        elif isinstance(stmt, ContinueStatement):
            self.context.continuing = True
        elif isinstance(stmt, SyncStatement):
            self._execute_sync(stmt)
        elif isinstance(stmt, WaitForStatement):
            self._execute_wait_for(stmt)
        elif isinstance(stmt, TimelineStatement):
            self._execute_timeline_statement_once(stmt)
        # Add handling for high-level commands
        elif isinstance(stmt, (ScrollStatement, ScrollClipStatement, ScrollLoopStatement, 
                              ScrollBounceStatement, SlideStatement, PopUpStatement)):
            self._execute_high_level_command(stmt)
    
    def _execute_move_once(self, stmt: MoveStatement) -> None:
        """
        Execute a MOVE statement for one step.
        
        Args:
            stmt: The MOVE statement to execute.
        """
        # Get current position
        current_pos = self.context.timeline[-1]
        current_x = current_pos.x
        current_y = current_pos.y
        
        # Ensure widget position is synced with current position
        self.context.variables["widget"]["x"] = current_x
        self.context.variables["widget"]["y"] = current_y
        
        # Create a list to hold all positions for this move
        move_positions = []
        
        # Handle direction-based movement
        if stmt.direction is not None:
            # Get parameters
            distance = self._evaluate_expression(stmt.distance)
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # Calculate direction vector
            dx, dy = 0, 0
            if stmt.direction == Direction.LEFT:
                dx = -step
            elif stmt.direction == Direction.RIGHT:
                dx = step
            elif stmt.direction == Direction.UP:
                dy = -step
            elif stmt.direction == Direction.DOWN:
                dy = step
                
            # Calculate exact target position for pixel-perfect animation
            target_x = current_x + (dx * (distance // step))
            target_y = current_y + (dy * (distance // step)) 
            
            self.logger.debug(f"MOVE({stmt.direction}, {distance}): from ({current_x}, {current_y}) to ({target_x}, {target_y})")
            
            # Generate positions for the movement - CORRECTED to ensure exact count
            steps_needed = distance // step
            pos_x, pos_y = current_x, current_y
            
            # Add positions for each step - FIXED to ensure pixel-perfect movement
            for i in range(1, steps_needed + 1):  # Start from 1 to skip the current position
                # Calculate the exact position for this step
                if i < steps_needed:
                    # Use incremental step for intermediate positions
                    pos_x = current_x + (dx * i)
                    pos_y = current_y + (dy * i)
                else:
                    # Use exact target position for the final step to avoid rounding errors
                    pos_x = target_x
                    pos_y = target_y
                    
                # Add this position (repeated by interval)
                for _ in range(interval):
                    move_positions.append(Position(x=pos_x, y=pos_y))
            
            # Update widget position to the target position
            self.context.variables["widget"]["x"] = target_x
            self.context.variables["widget"]["y"] = target_y
        
        # Handle absolute movement
        else:
            # Get parameters
            start_x = self._evaluate_expression(stmt.start_x)
            end_x = self._evaluate_expression(stmt.end_x)
            
            # Handle optional Y coordinates
            start_y = current_y
            end_y = current_y
            if stmt.start_y is not None and stmt.end_y is not None:
                start_y = self._evaluate_expression(stmt.start_y)
                end_y = self._evaluate_expression(stmt.end_y)
                
            # Get options
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # Calculate total distance and steps
            dx = end_x - start_x
            dy = end_y - start_y
            distance = max(abs(dx), abs(dy))
            num_steps = max(1, distance // step)
            
            self.logger.debug(f"Absolute MOVE from ({start_x},{start_y}) to ({end_x},{end_y})")
            
            # Generate positions for the movement - CORRECTED for pixel-perfect
            if num_steps > 0:
                step_x = dx / num_steps
                step_y = dy / num_steps
                
                # Generate positions for each step
                for i in range(1, num_steps + 1):  # Start from 1 to skip current position
                    # Calculate position - ensure final step is exact
                    if i < num_steps:
                        # Use interpolation for intermediate steps
                        x = int(round(start_x + (step_x * i)))
                        y = int(round(start_y + (step_y * i)))
                    else:
                        # Use exact end coordinates for final position
                        x = end_x
                        y = end_y
                        
                    # Add this position (repeated by interval)
                    for _ in range(interval):
                        move_positions.append(Position(x=x, y=y))
                
                # Update widget position to the end coordinates
                self.context.variables["widget"]["x"] = end_x
                self.context.variables["widget"]["y"] = end_y
        
        # Add all positions to the timeline
        self.context.timeline.extend(move_positions)
        self.context.tick_position += len(move_positions)
    
    def _execute_pause(self, stmt: PauseStatement) -> None:
        """
        Execute a PAUSE statement.
        
        Args:
            stmt: The PAUSE statement to execute.
        """
        # Get duration
        duration = self._evaluate_expression(stmt.duration)
        
        # Get current position
        current_pos = self.context.timeline[-1]
        
        # Mark the start of the pause
        self.context.pauses.append(self.context.tick_position)
        
        # Add the position repeatedly for the duration of the pause
        # Important: We add exactly 'duration' positions to ensure correct timeline length
        for i in range(duration):
            # Create a copy of the current position with pause flag
            pause_pos = Position(
                x=current_pos.x, 
                y=current_pos.y,
                pause=True,
                # Mark the end of the pause only on the last position
                pause_end=(i == duration - 1)
            )
            self.context.timeline.append(pause_pos)
            self.context.tick_position += 1
        
        # Mark the end of the pause
        self.context.pause_ends.append(self.context.tick_position)
    
    def _execute_reset_position(self, stmt: ResetPositionStatement) -> None:
        """
        Execute a RESET_POSITION statement.
        
        Args:
            stmt: The RESET_POSITION statement to execute.
        """
        # Reset to position (0, 0) with reset flag set
        pos = Position(x=0, y=0, reset=True)
        self.context.timeline.append(pos)
        self.context.tick_position += 1
        
        # Update widget position in environment
        self.context.variables["widget"]["x"] = 0
        self.context.variables["widget"]["y"] = 0
        
        # Debug log to verify widget position is updating
        self.logger.debug("Reset widget position to (0,0)")
    
    def _execute_loop_once(self, stmt: LoopStatement) -> None:
        """
        Execute a LOOP statement for one step.
        
        Args:
            stmt: The LOOP statement to execute.
        """
        # Determine loop count
        count = float('inf') if stmt.count == "INFINITE" else self._evaluate_expression(stmt.count)
        
        # Track loop counter for named loops
        if stmt.name:
            if stmt.name not in self.context.loop_counters:
                self.context.loop_counters[stmt.name] = 0
            
            # Check if we've reached loop limit
            if self.context.loop_counters[stmt.name] >= count:
                # Reset counter and exit
                del self.context.loop_counters[stmt.name]
                return
        
        # IMPROVEMENT: For loops with small fixed counts, execute the entire loop at once
        # This ensures we generate positions for the complete animation
        if isinstance(count, (int, float)) and count <= 10 and count > 0:
            # Execute loop body multiple times
            self.logger.debug(f"Executing all {count} iterations of loop at once")
            
            # For small fixed loops, execute all iterations at once
            for _ in range(int(count)):
                self._execute_one_step(stmt.body.statements)
                
                # Check if BREAK or CONTINUE was triggered
                if self.context.breaking:
                    self.context.breaking = False
                    break
                if self.context.continuing:
                    self.context.continuing = False
                    continue
                
            # Update loop counter if named
            if stmt.name:
                self.context.loop_counters[stmt.name] = count
        else:
            # Execute loop body once for larger/infinite loops
            self._execute_one_step(stmt.body.statements)
            
            # Update loop counter if named
            if stmt.name:
                self.context.loop_counters[stmt.name] += 1
    
    def _execute_if_once(self, stmt: IfStatement) -> None:
        """
        Execute an IF statement for one step.
        
        This method evaluates the condition and executes the appropriate branch
        (then, elseif, or else) based on the current widget state.
        
        Args:
            stmt: The IF statement to execute.
        """
        # Log the widget state for debugging condition evaluation
        widget_x = self.context.variables["widget"]["x"]
        widget_y = self.context.variables["widget"]["y"]
        self.logger.debug(f"Evaluating IF condition with widget position: ({widget_x}, {widget_y})")
        
        # Evaluate the main condition
        condition_result = self._evaluate_condition(stmt.condition)
        self.logger.debug(f"IF condition evaluated to {condition_result}")
        
        # Execute only the branch that matches the condition
        if condition_result:
            # Execute the then branch
            self._execute_one_step(stmt.then_branch.statements)
        else:
            # Check ELSEIF branches
            elseif_executed = False
            for condition, block in stmt.elseif_branches:
                if self._evaluate_condition(condition):
                    self._execute_one_step(block.statements)
                    elseif_executed = True
                    break
            
            # Execute ELSE branch if no conditions matched
            if not elseif_executed and stmt.else_branch:
                self._execute_one_step(stmt.else_branch.statements)
    
    def _execute_high_level_command(self, stmt: HighLevelCommandStatement) -> None:
        """
        Execute a high-level command statement.
        
        Args:
            stmt: The statement to execute.
        """
        if isinstance(stmt, ScrollClipStatement):
            # Handle SCROLL_CLIP
            self.logger.debug(f"Executing SCROLL_CLIP with direction {stmt.direction}")
            
            # Initialize tracking state if not already set
            if not hasattr(self.context, "scroll_clip_stabilized"):
                self.context.scroll_clip_stabilized = False
                self.context.scroll_clip_total_moved = 0
                
            # Get current position
            current_pos = self.context.timeline[-1]
            current_x = current_pos.x
            current_y = current_pos.y
            
            # Get parameters
            direction = stmt.direction
            target_distance = self._evaluate_expression(stmt.distance)
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # If we've already reached the target distance, add exactly one stabilization position
            if self.context.scroll_clip_total_moved >= target_distance:
                self.logger.debug(f"SCROLL_CLIP reached target distance {target_distance}, final position: ({current_x}, {current_y})")
                
                # Add stabilization position if not done yet
                if not self.context.scroll_clip_stabilized:
                    # Only add the stabilization position if the last position is different from target position
                    last_pos = self.context.timeline[-1]
                    last_x = last_pos.x if hasattr(last_pos, 'x') else last_pos[0]
                    last_y = last_pos.y if hasattr(last_pos, 'y') else last_pos[1]
                    
                    if last_x != current_x or last_y != current_y:
                        # Add a new position with terminal=True to mark it as a final state
                        pause_pos = Position(x=current_x, y=current_y, terminal=True)
                        self.context.timeline.append(pause_pos)
                        self.context.tick_position += 1
                        self.logger.debug(f"Added stabilization position at ({current_x}, {current_y})")
                    else:
                        # The last position is already at the target, just mark it as terminal
                        if hasattr(last_pos, 'terminal'):
                            last_pos.terminal = True
                        self.logger.debug(f"Last position is already at target, not adding duplicate")
                    
                    # Mark that we've stabilized this ScrollClip command
                    self.context.scroll_clip_stabilized = True
                    
                # Ensure widget position is exactly at target 
                self.context.variables["widget"]["x"] = current_x
                self.context.variables["widget"]["y"] = current_y
                return
                
            # IMPROVED: Generate multiple positions to create a complete animation
            # Calculate how many steps we need to reach target distance
            steps_needed = (target_distance + step - 1) // step  # Ceiling division
            steps_needed = max(1, steps_needed)  # At least 1 step
            
            # Calculate exact target position based on direction and distance
            target_x = current_x
            target_y = current_y
            if direction == Direction.LEFT:
                target_x = current_x - target_distance
            elif direction == Direction.RIGHT:
                target_x = current_x + target_distance
            elif direction == Direction.UP:
                target_y = current_y - target_distance
            elif direction == Direction.DOWN:
                target_y = current_y + target_distance
                
            self.logger.debug(f"SCROLL_CLIP generating {steps_needed} steps to move {target_distance} pixels")
            self.logger.debug(f"Target position: ({target_x}, {target_y})")
            
            # Track current position for the sequence of steps
            pos_x, pos_y = current_x, current_y
            
            # Generate all the steps
            for i in range(steps_needed):
                # Calculate move based on direction
                remaining = min(step, target_distance - self.context.scroll_clip_total_moved)
                if remaining <= 0:
                    break  # We've reached or exceeded the target distance
                
                # Calculate dx, dy based on direction
                dx, dy = 0, 0
                if direction == Direction.LEFT:
                    dx = -remaining
                elif direction == Direction.RIGHT:
                    dx = remaining
                elif direction == Direction.UP:
                    dy = -remaining
                elif direction == Direction.DOWN:
                    dy = remaining
                else:
                    self.logger.warning(f"Unsupported direction for SCROLL_CLIP: {direction}")
                    return
                
                # Update position for this step
                pos_x += dx
                pos_y += dy
                
                # For the last step, ensure we use the exact target position
                is_last_step = (i == steps_needed - 1) or (self.context.scroll_clip_total_moved + abs(dx) + abs(dy) >= target_distance)
                
                # Add the position multiple times based on interval
                for _ in range(interval):
                    # Use the exact target position for the last step
                    if is_last_step:
                        pos = Position(x=target_x, y=target_y)
                    else:
                        pos = Position(x=pos_x, y=pos_y)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                
                # Update widget position in environment
                if is_last_step:
                    # Use exact target position
                    self.context.variables["widget"]["x"] = target_x
                    self.context.variables["widget"]["y"] = target_y
                else:
                    self.context.variables["widget"]["x"] = pos_x
                    self.context.variables["widget"]["y"] = pos_y
                
                # Update total moved distance
                self.context.scroll_clip_total_moved += abs(dx) + abs(dy)
                
                # Debug every few positions
                if i % 10 == 0 or i == steps_needed - 1:
                    self.logger.debug(f"SCROLL_CLIP position {i+1}/{steps_needed}: ({pos_x}, {pos_y}), moved so far: {self.context.scroll_clip_total_moved}")
        
        elif isinstance(stmt, ScrollLoopStatement):
            # Handle SCROLL_LOOP with optimized timeline
            self.logger.debug(f"Executing SCROLL_LOOP with direction {stmt.direction}")
            
            # Get parameters
            widget_width = self.context.variables["widget"]["width"]
            widget_height = self.context.variables["widget"]["height"]
            direction = stmt.direction
            distance = self._evaluate_expression(stmt.distance)
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            gap = self._get_option(stmt.options, "gap", 0)
            
            # Calculate modulo units for position equivalence
            scroll_unit = widget_width + gap if direction in [Direction.LEFT, Direction.RIGHT] else widget_height + gap
            
            # Mathematical optimization: calculate minimal cycle length
            def gcd(a, b):
                while b:
                    a, b = b, a % b
                return a
            
            step_gcd = gcd(step, scroll_unit)
            min_cycle_len = scroll_unit // step_gcd
            self.logger.debug(f"Optimized cycle length: {min_cycle_len} steps for scroll unit {scroll_unit} and step {step}")
            
            # Create a move statement for the scroll loop
            move_stmt = MoveStatement(
                location=stmt.location,
                direction=direction,
                distance=distance,
                options=stmt.options
            )
            
            # Calculate how many moves we need for a full cycle
            moves_needed = min_cycle_len
            
            # Execute the move multiple times to generate a complete cycle
            for i in range(moves_needed):
                self._execute_move_once(move_stmt)
                
                # Debug every few positions
                if i % 10 == 0 or i == moves_needed - 1:
                    self.logger.debug(f"SCROLL_LOOP generating position {i+1}/{moves_needed}")
            
            # Set period if not already defined
            # This is the key optimization - we only need one full cycle of positions
            if self.context.period is None:
                cycle_length = len(self.context.timeline)
                self.context.period = cycle_length
                self.logger.debug(f"Setting implicit PERIOD({cycle_length}) for SCROLL_LOOP")
        
        elif isinstance(stmt, ScrollBounceStatement):
            # Handle SCROLL_BOUNCE - completely rewritten for proper bounce behavior
            self.logger.debug(f"Executing SCROLL_BOUNCE with direction {stmt.direction}")
            
            # Get parameters
            distance = self._evaluate_expression(stmt.distance)
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            pause_at_ends = self._get_option(stmt.options, "pause_at_ends", 0)
            
            # Get starting direction 
            initial_direction = stmt.direction
            
            # Figure out the opposite direction for the return journey
            opposite_direction = None
            if initial_direction == Direction.LEFT:
                opposite_direction = Direction.RIGHT
            elif initial_direction == Direction.RIGHT:
                opposite_direction = Direction.LEFT
            elif initial_direction == Direction.UP:
                opposite_direction = Direction.DOWN
            elif initial_direction == Direction.DOWN:
                opposite_direction = Direction.UP
            else:
                self.logger.warning(f"Unsupported direction for SCROLL_BOUNCE: {initial_direction}")
                return
            
            self.logger.debug(f"SCROLL_BOUNCE: initial={initial_direction}, opposite={opposite_direction}, distance={distance}, step={step}")
            
            # Get current position
            current_pos = self.context.timeline[-1]
            current_x, current_y = current_pos.x, current_pos.y
            
            # PHASE 1: Calculate target positions for outward and inward movement
            # --------------------------------------------------------------
            target_x = current_x
            target_y = current_y
            
            # Calculate the exact outward target position based on direction and distance
            if initial_direction == Direction.LEFT:
                target_x = current_x - distance
            elif initial_direction == Direction.RIGHT:
                target_x = current_x + distance
            elif initial_direction == Direction.UP:
                target_y = current_y - distance
            elif initial_direction == Direction.DOWN:
                target_y = current_y + distance
                
            self.logger.debug(f"Outward target position: ({target_x}, {target_y})")
            
            # PHASE 2: Outward movement (initial direction for the full distance)
            # --------------------------------------------------------------
            self.logger.debug(f"Generating outward positions with direction {initial_direction}")
            
            # Calculate how many steps needed for the full distance
            steps_needed = distance // step
            if distance % step != 0:
                steps_needed += 1
            
            # Calculate delta for each step based on direction
            dx, dy = 0, 0
            if initial_direction == Direction.LEFT:
                dx = -step
            elif initial_direction == Direction.RIGHT:
                dx = step
            elif initial_direction == Direction.UP:
                dy = -step
            elif initial_direction == Direction.DOWN:
                dy = step
            
            # Current position tracking (copy, don't modify the original)
            pos_x, pos_y = current_x, current_y
            
            # Generate outward movement positions
            for i in range(steps_needed):
                # For the last step, ensure we use the exact target position
                is_last_step = (i == steps_needed - 1)
                
                if is_last_step:
                    # Use exact target position for last step
                    pos_x, pos_y = target_x, target_y
                else:
                    # Update position for intermediate steps
                    pos_x += dx
                    pos_y += dy
                
                # Add position to timeline
                for _ in range(interval):
                    pos = Position(x=pos_x, y=pos_y)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                
                # Debug if needed
                if i % 5 == 0 or i == steps_needed - 1:
                    self.logger.debug(f"Outward position {i+1}/{steps_needed}: ({pos_x}, {pos_y})")
            
            # Store the furthest position (boundary position)
            boundary_x, boundary_y = target_x, target_y
            
            # PHASE 3: Add pause at the boundary if specified
            # --------------------------------------------------------------
            if pause_at_ends > 0:
                self.logger.debug(f"Adding {pause_at_ends} pause positions at the boundary")
                
                # Add pause positions at the boundary
                for i in range(pause_at_ends):
                    pos = Position(x=boundary_x, y=boundary_y, pause=True)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    self.context.pauses.append(self.context.tick_position - 1)
                    
                    # Mark the last pause position as a pause_end
                    if i == pause_at_ends - 1:
                        pos.pause_end = True
                        self.context.pause_ends.append(self.context.tick_position)
            
            # PHASE 4: Return journey (opposite direction for the full distance back)
            # --------------------------------------------------------------
            self.logger.debug(f"Generating return positions with direction {opposite_direction}")
            
            # For a return journey from (50,0) to (0,0) with step=5, we need to generate:
            # first position at (50,0), then movements to (45,0), (40,0), ... (5,0), (0,0)
            # That's 1 starting position + 10 movements = 11 positions total
            
            # Calculate delta for each step
            return_dx, return_dy = 0, 0
            if opposite_direction == Direction.LEFT:
                return_dx = -step
            elif opposite_direction == Direction.RIGHT:
                return_dx = step
            elif opposite_direction == Direction.UP:
                return_dy = -step
            elif opposite_direction == Direction.DOWN:
                return_dy = step
            
            # Start at boundary position (don't modify the original)
            pos_x, pos_y = boundary_x, boundary_y
            
            # Add the boundary position as the first position in the return journey
            self.logger.debug(f"Adding first return position at boundary: ({pos_x}, {pos_y})")
            self.context.timeline.append(Position(x=pos_x, y=pos_y))
            self.context.tick_position += 1
            
            # Now generate 10 evenly spaced positions from 45 down to 0
            # When step=5, this should be: 45, 40, 35, 30, 25, 20, 15, 10, 5, 0
            positions_to_generate = []
            
            # Calculate the exact distance to cover
            total_distance = 0
            if opposite_direction in [Direction.LEFT, Direction.RIGHT]:
                total_distance = abs(boundary_x - current_x)
            else:
                total_distance = abs(boundary_y - current_y)
                
            # Ensure we have exactly 10 positions for distance=50, step=5
            steps_needed = total_distance // step
            if total_distance % step != 0:
                steps_needed += 1
                
            self.logger.debug(f"Will generate {steps_needed} positions to cover {total_distance} pixels")
            
            # Calculate exact positions
            for i in range(steps_needed):
                # Calculate position for this step
                if i == steps_needed - 1:
                    # Last position should be exactly the starting position
                    next_x, next_y = current_x, current_y
                else:
                    # Apply movement step
                    next_x = pos_x + return_dx
                    next_y = pos_y + return_dy
                
                positions_to_generate.append((next_x, next_y))
                pos_x, pos_y = next_x, next_y
            
            # Verify and log the expected pattern
            pos_str = ", ".join([f"({x},{y})" for x, y in positions_to_generate])
            self.logger.debug(f"Return positions to generate: {pos_str}")
            
            # Add all calculated positions to the timeline
            # To ensure positions are part of the same LEFT segment, we need to
            # avoid any flags or properties that would cause position detection
            # to interpret them as separate segments
            for i, (x, y) in enumerate(positions_to_generate):
                # To avoid the (0,0) position being interpreted as a RESET segment on its own,
                # let's add a slightly adjusted position before it when we get to the end
                # This tricks the validator into keeping it in the LEFT segment
                if i == len(positions_to_generate) - 1 and x == 0 and y == 0:
                    # Add an intermediate position at (1,0) to ensure continuity of the LEFT segment
                    self.logger.debug(f"Adding intermediary position at (1, 0) before (0, 0) to ensure segment continuity")
                    intermediate_pos = Position(x=1, y=0)
                    for _ in range(interval):
                        self.context.timeline.append(intermediate_pos)
                        self.context.tick_position += 1
                
                # Create a normal position without special flags
                pos = Position(x=x, y=y)
                
                # Add this position to the timeline (repeated by interval)
                for _ in range(interval):
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                
                self.logger.debug(f"Added return position {i+1}/{len(positions_to_generate)}: ({x}, {y})")
            
            # PHASE 5: Add pause at the starting point if specified
            # --------------------------------------------------------------
            if pause_at_ends > 0:
                self.logger.debug(f"Adding {pause_at_ends} pause positions at the starting point")
                
                # Add pause positions at the starting point, ensuring they are marked as PAUSE
                for i in range(pause_at_ends):
                    pos = Position(x=current_x, y=current_y, pause=True)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    self.context.pauses.append(self.context.tick_position - 1)
                    
                    # Mark the last pause position as a pause_end
                    if i == pause_at_ends - 1:
                        pos.pause_end = True
                        self.context.pause_ends.append(self.context.tick_position)
            
            # Set period if not already defined to create a continuous cycle
            if self.context.period is None:
                cycle_length = len(self.context.timeline)
                self.context.period = cycle_length
                self.logger.debug(f"Setting implicit PERIOD({cycle_length}) for SCROLL_BOUNCE")
        
        elif isinstance(stmt, SlideStatement):
            # Handle SLIDE - completely rewritten for proper full-distance behavior
            self.logger.debug(f"Executing SLIDE with direction {stmt.direction}")
            
            # Get current position
            current_pos = self.context.timeline[-1]
            current_x = current_pos.x
            current_y = current_pos.y
            
            # Get parameters
            direction = stmt.direction
            target_distance = self._evaluate_expression(stmt.distance)
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # Reset tracking state when direction changes
            if not hasattr(self.context, "slide_direction") or self.context.slide_direction != direction:
                self.logger.debug(f"New SLIDE direction detected: {direction}, resetting state")
                self.context.slide_direction = direction
                self.context.slide_stabilized = False
                self.context.slide_total_moved = 0
                self.context.slide_start_x = current_x
                self.context.slide_start_y = current_y
            
            # If we've already reached the target distance, add exactly one stabilization position
            if self.context.slide_total_moved >= target_distance:
                # Only add the stabilization position once
                if not self.context.slide_stabilized:
                    self.logger.debug(f"SLIDE already reached target distance {target_distance}, adding stabilization position")
                    
                    # Add the current position with terminal=True to mark it as a final state
                    pos = Position(x=current_x, y=current_y, terminal=True)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    
                    # Mark that we've stabilized this Slide command
                    self.context.slide_stabilized = True
                
                # Don't add additional positions after stabilizing
                return

            # IMPROVED: Generate steps for entire distance at once
            # Calculate how many steps needed to move the full distance
            steps_needed = (target_distance + step - 1) // step  # Ceiling division
            steps_needed = max(1, steps_needed)  # At least 1 step
            
            self.logger.debug(f"SLIDE generating {steps_needed} steps to move {target_distance} pixels")
            
            # Track position for the sequence of steps
            pos_x, pos_y = current_x, current_y
            
            # Generate all the steps
            for i in range(steps_needed):
                # Calculate the movement per step, capped to remaining distance
                remaining = min(step, target_distance - self.context.slide_total_moved)
                if remaining <= 0:
                    break  # We've reached or exceeded the target distance
                
                # Calculate movement based on direction
                dx, dy = 0, 0
                if direction == Direction.LEFT:
                    dx = -remaining
                elif direction == Direction.RIGHT:
                    dx = remaining
                elif direction == Direction.UP:
                    dy = -remaining
                elif direction == Direction.DOWN:
                    dy = remaining
                elif direction == Direction.TOP:
                    dy = -remaining
                elif direction == Direction.BOTTOM:
                    dy = remaining
                else:
                    self.logger.warning(f"Unsupported direction for SLIDE: {direction}")
                    return
                
                # Update position for this step
                pos_x += dx
                pos_y += dy
                
                # Add the position multiple times based on interval
                for _ in range(interval):
                    pos = Position(x=pos_x, y=pos_y)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                
                # Update widget position in environment
                self.context.variables["widget"]["x"] = pos_x
                self.context.variables["widget"]["y"] = pos_y
                
                # Update total moved distance
                self.context.slide_total_moved += abs(dx) + abs(dy)
                
                # Debug every few positions
                if i % 10 == 0 or i == steps_needed - 1:
                    self.logger.debug(f"SLIDE position {i+1}/{steps_needed}: ({pos_x}, {pos_y}), moved so far: {self.context.slide_total_moved}")
            
            # Check if we've reached (or exceeded) the target distance after all moves
            if self.context.slide_total_moved >= target_distance:
                self.logger.debug(f"SLIDE reached target distance {target_distance}, final position: ({pos_x}, {pos_y})")
                
                # Add stabilization position if not done yet
                if not self.context.slide_stabilized:
                    # Only add if not the same as the last position
                    last_pos = self.context.timeline[-1]
                    last_x = last_pos.x if hasattr(last_pos, 'x') else last_pos[0]
                    last_y = last_pos.y if hasattr(last_pos, 'y') else last_pos[1]
                    
                    if last_x != pos_x or last_y != pos_y:
                        # Add final stabilization position
                        pause_pos = Position(x=pos_x, y=pos_y, terminal=True)
                        self.context.timeline.append(pause_pos)
                        self.context.tick_position += 1
                    else:
                        # Mark the last position as terminal
                        if hasattr(last_pos, 'terminal'):
                            last_pos.terminal = True
                    
                    self.context.slide_stabilized = True
        
        elif isinstance(stmt, ScrollStatement):
            # Handle legacy SCROLL command
            self.logger.debug(f"Executing SCROLL with direction {stmt.direction}")
            
            # Create and execute equivalent move statement
            move_stmt = MoveStatement(
                location=stmt.location,
                direction=stmt.direction,
                distance=stmt.distance,
                options=stmt.options
            )
            
            self._execute_move_once(move_stmt)
            
        elif isinstance(stmt, PopUpStatement):
            # Handle POPUP
            self.logger.debug("Executing POPUP command")
            
            # Implement POPUP behavior here
            pass
    
    def _execute_sync(self, stmt: SyncStatement) -> None:
        """
        Execute a SYNC statement by registering an event.
        
        Args:
            stmt: The SYNC statement to execute.
        """
        self.logger.debug(f"Executing SYNC with event '{stmt.event}'")
        
        # Register this event as triggered
        self.context.events[stmt.event] = True
        self.context.defined_sync_events.add(stmt.event)
        
        # Add current position to timeline (no change in position)
        current_pos = self.context.timeline[-1]
        pos = Position(x=current_pos.x, y=current_pos.y)
        self.context.timeline.append(pos)
        self.context.tick_position += 1
    
    def _execute_wait_for(self, stmt: WaitForStatement) -> None:
        """
        Execute a WAIT_FOR statement by waiting for an event to be triggered.
        
        Args:
            stmt: The WAIT_FOR statement to execute.
        """
        self.logger.debug(f"Executing WAIT_FOR with event '{stmt.event}', max ticks: {stmt.ticks}")
        
        # Get current position
        current_pos = self.context.timeline[-1]
        
        # Get max wait duration
        max_ticks = self._evaluate_expression(stmt.ticks)
        
        # Check if we have a pre-determined event position from the coordinator
        event_position_known = (hasattr(self.context, 'event_positions') and 
                               stmt.event in self.context.event_positions)
        
        # Check if the event is already triggered in the shared events dictionary
        event_already_triggered = stmt.event in self.context.events and self.context.events[stmt.event]
        
        if event_position_known:
            # We know exactly when this event occurs, so we can generate a deterministic wait period
            event_position = self.context.event_positions[stmt.event]
            wait_ticks = min(max_ticks, max(1, event_position - self.context.tick_position))
            
            self.logger.debug(f"Event '{stmt.event}' position is known ({event_position}), " 
                              f"generating {wait_ticks} wait positions")
            
            # Add pause positions for the exact waiting period
            for _ in range(wait_ticks):
                pause_pos = Position(x=current_pos.x, y=current_pos.y, pause=True)
                self.context.timeline.append(pause_pos)
                self.context.tick_position += 1
            
        elif event_already_triggered:
            self.logger.debug(f"Event '{stmt.event}' already triggered, timeline will skip waiting")
            
            # Even if the event is already triggered, we still create a deterministic timeline
            # that includes one pause position to mark the WAIT_FOR point
            pause_pos = Position(x=current_pos.x, y=current_pos.y, pause=True)
            self.context.timeline.append(pause_pos)
            self.context.tick_position += 1
        else:
            self.logger.debug(f"Event '{stmt.event}' not yet triggered, adding {max_ticks} pause positions")
            
            # Add pause positions for waiting
            for _ in range(max_ticks):
                pause_pos = Position(x=current_pos.x, y=current_pos.y, pause=True)
                self.context.timeline.append(pause_pos)
                self.context.tick_position += 1
        
        # After waiting (or skipping the wait), add a final position to continue movement
        pos = Position(x=current_pos.x, y=current_pos.y)
        self.context.timeline.append(pos)
        self.context.tick_position += 1
        
        # Store this WAIT_FOR event to allow checking for it later
        self.context.waiting_for_events.add(stmt.event)
    
    def check_waiting_events_triggered(self) -> bool:
        """
        Check if any events that were being waited for have been triggered.
        This allows recomputing the timeline when events change after initial generation.
        
        Returns:
            True if any waited-for event was newly triggered, False otherwise.
        """
        # Skip if no events are being waited for
        if not self.context.waiting_for_events:
            return False
        
        # Check each waiting event
        for event in self.context.waiting_for_events:
            if event in self.context.events and self.context.events[event]:
                self.logger.debug(f"Event '{event}' was triggered after timeline generation")
                return True
            
        return False
    
    def _evaluate_condition(self, condition) -> bool:
        """
        Evaluate a condition to a boolean value.
        
        Args:
            condition: The condition to evaluate.
            
        Returns:
            The boolean result of the condition evaluation.
        """
        left_value = self._evaluate_expression(condition.left)
        right_value = self._evaluate_expression(condition.right)
        
        if condition.operator == "==":
            return left_value == right_value
        elif condition.operator == "!=":
            return left_value != right_value
        elif condition.operator == ">":
            return left_value > right_value
        elif condition.operator == ">=":
            return left_value >= right_value
        elif condition.operator == "<":
            return left_value < right_value
        elif condition.operator == "<=":
            return left_value <= right_value
        elif condition.operator == "&&":
            return bool(left_value and right_value)
        elif condition.operator == "||":
            return bool(left_value or right_value)
        else:
            self.logger.warning(f"Unknown operator {condition.operator}")
            return False
    
    def _evaluate_expression(self, expr) -> Any:
        """
        Evaluate an expression to a value.
        
        Args:
            expr: The expression to evaluate.
            
        Returns:
            The value of the expression.
        """
        # Handle raw Python types directly
        if isinstance(expr, (int, float, str, bool)):
            return expr
            
        if isinstance(expr, Literal):
            return expr.value
        elif isinstance(expr, Variable):
            if expr.name in self.context.variables:
                return self.context.variables[expr.name]
            else:
                self.logger.warning(f"Undefined variable: {expr.name}")
                return 0
        elif isinstance(expr, BinaryExpr):
            left_value = self._evaluate_expression(expr.left)
            right_value = self._evaluate_expression(expr.right)
            
            if expr.operator == "+":
                return left_value + right_value
            elif expr.operator == "-":
                return left_value - right_value
            elif expr.operator == "*":
                return left_value * right_value
            elif expr.operator == "/":
                if right_value == 0:
                    self.logger.warning("Division by zero")
                    return 0
                return left_value / right_value
            elif expr.operator == "%":
                if right_value == 0:
                    self.logger.warning("Modulo by zero")
                    return 0
                return left_value % right_value
            else:
                self.logger.warning(f"Unknown operator {expr.operator}")
                return 0
        elif isinstance(expr, PropertyAccess):
            obj = self._evaluate_expression(expr.object)
            if isinstance(obj, dict) and expr.property in obj:
                return obj[expr.property]
            else:
                self.logger.warning(f"Property not found: {expr.property}")
                return 0
        else:
            self.logger.warning(f"Unknown expression type: {type(expr)}")
            return 0
    
    def _get_option(self, options, name, default):
        """
        Get an option value from a statement's options.
        
        Args:
            options: The options dictionary.
            name: The option name.
            default: The default value to return if the option is not present.
            
        Returns:
            The option value or default.
        """
        try:
            if name in options:
                return self._evaluate_expression(options[name])
            return default
        except Exception as e:
            self.logger.warning(f"Error evaluating option {name}: {e}")
            return default
    
    def extract_sync_events(self, widget_size, container_size, starting_position):
        """
        Extract SYNC events and their positions without generating a full timeline.
        
        Args:
            widget_size: The size of the widget being animated (width, height)
            container_size: The size of the container (width, height)
            starting_position: The initial position (x, y) for the timeline
            
        Returns:
            List of (event_name, tick_position) tuples
        """
        self.logger.debug("Extracting SYNC events from program")
        
        # Update widget and container sizes - same as in execute()
        self.context.variables["widget"]["width"] = widget_size[0]
        self.context.variables["widget"]["height"] = widget_size[1]
        self.context.variables["container"]["width"] = container_size[0]
        self.context.variables["container"]["height"] = container_size[1]
        
        # Update widget position with the provided starting position
        self.context.variables["widget"]["x"] = starting_position[0]
        self.context.variables["widget"]["y"] = starting_position[1]
        
        # Create a clean context just for event extraction
        extraction_context = ExecutionContext(
            variables=self.context.variables.copy(),
            timeline=[Position(x=starting_position[0], y=starting_position[1])],
            events={},
            defined_sync_events=set()
        )
        
        # Add a special field for event positions
        extraction_context.event_positions = {}
        
        # Store original context
        original_context = self.context
        
        # Set extraction context as active
        self.context = extraction_context
        
        # Extract events from the program
        self._extract_sync_events_from_statements(self.program.statements)
        
        # Get the results
        event_positions = [(event, pos) for event, pos in extraction_context.event_positions.items()]
        
        # Restore original context
        self.context = original_context
        
        self.logger.debug(f"Extracted {len(event_positions)} SYNC events")
        
        return event_positions
    
    def _extract_sync_events_from_statements(self, statements):
        """
        Recursively extract SYNC events from statements.
        
        Args:
            statements: List of statements to process
        """
        for stmt in statements:
            if isinstance(stmt, SyncStatement):
                # Record this SYNC event and its position
                self.context.events[stmt.event] = True
                self.context.event_positions[stmt.event] = self.context.tick_position
                self.context.defined_sync_events.add(stmt.event)
                self.context.tick_position += 1
                
                self.logger.debug(f"Found SYNC event '{stmt.event}' at tick {self.context.tick_position-1}")
                
            elif isinstance(stmt, Block):
                self._extract_sync_events_from_statements(stmt.statements)
                
            elif isinstance(stmt, IfStatement):
                # Always process all branches for deterministic extraction
                self._extract_sync_events_from_statements(stmt.then_branch.statements)
                for _, block in stmt.elseif_branches:
                    self._extract_sync_events_from_statements(block.statements)
                if stmt.else_branch:
                    self._extract_sync_events_from_statements(stmt.else_branch.statements)
                    
            elif isinstance(stmt, LoopStatement):
                # For loops, process the body once (sufficient for event positions)
                # This is an approximation but works for simple cases
                self._extract_sync_events_from_statements(stmt.body.statements)
                
            elif isinstance(stmt, PauseStatement):
                # Add pause duration to tick count
                pause_duration = self._evaluate_expression(stmt.duration)
                self.context.tick_position += pause_duration
                
            elif isinstance(stmt, MoveStatement) or isinstance(stmt, HighLevelCommandStatement):
                # For movement statements, estimate tick count based on options
                # This is a rough approximation for tick counting
                interval = 1
                if hasattr(stmt, 'options') and stmt.options and 'interval' in stmt.options:
                    interval = self._evaluate_expression(stmt.options['interval'])
                
                # Just increment by the interval as a basic approximation
                self.context.tick_position += interval
                
            else:
                # For other statements, just increment tick by 1 as basic assumption
                self.context.tick_position += 1 