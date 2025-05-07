"""
tinyDisplay Marquee DSL Executor.

This module provides a class that can execute Marquee DSL programs.
It serves as the runtime environment for the Marquee Animation DSL.
"""

from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass
import logging

from .marquee import parse_marquee_dsl, validate_marquee_dsl
from .marquee.ast import (
    Program, Block, Statement, Direction, MoveStatement, PauseStatement, 
    ResetPositionStatement, LoopStatement, IfStatement, BreakStatement, 
    ContinueStatement, SyncStatement, WaitForStatement, Expression, Literal,
    Variable, BinaryExpr, PropertyAccess, TimelineStatement, PeriodStatement,
    StartAtStatement, SegmentStatement, PositionAtStatement,
    ScrollStatement, ScrollClipStatement, ScrollLoopStatement, 
    ScrollBounceStatement, SlideStatement, PopUpStatement, HighLevelCommandStatement
)


@dataclass
class Position:
    """Represents a widget position at a specific tick."""
    x: int
    y: int
    pause: bool = False
    pause_end: bool = False
    segment_start: bool = False
    segment_end: bool = False
    segment_name: Optional[str] = None


@dataclass
class ExecutionContext:
    """Execution context for the Marquee DSL."""
    variables: Dict[str, Any] = None
    timeline: List[Position] = None
    loop_counters: Dict[str, int] = None
    tick_position: int = 0
    break_loop: bool = False
    continue_loop: bool = False
    current_segment: Optional[str] = None
    segments: Dict[str, Tuple[int, int]] = None
    period: Optional[int] = None
    start_at: int = 0
    pauses: List[int] = None
    pause_ends: List[int] = None
    # Add tracking for SCROLL_CLIP starting positions
    scroll_clip_start_x: Optional[int] = None
    scroll_clip_start_y: Optional[int] = None
    scroll_clip_total_moved: Optional[float] = None
    scroll_clip_stabilized: bool = False
    # Add tracking for SLIDE command
    slide_start_x: Optional[int] = None
    slide_start_y: Optional[int] = None
    slide_total_moved: Optional[float] = None
    slide_stabilized: bool = False
    slide_progress: Optional[float] = None
    
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
            
        # Initialize execution context
        self.context = ExecutionContext()
        
        # Initialize standard variables
        self.context.variables = {
            "widget": {"x": 0, "y": 0, "width": 0, "height": 0, "opacity": 1.0},
            "container": {"width": 0, "height": 0},
            "current_tick": 0,
            # Standard easing functions
            "linear": "linear",
            "ease_in": "ease_in",
            "ease_out": "ease_out",
            "ease_in_out": "ease_in_out"
        }
        
        # Add user-defined initial variables
        if initial_variables:
            for name, value in initial_variables.items():
                self.context.variables[name] = value
        
        # Validate the program
        self.errors = validate_marquee_dsl(self.program)
        if self.errors:
            for error in self.errors:
                self.logger.warning(f"Validation warning: {error}")
        
    def execute(self, widget_size: Tuple[int, int], container_size: Tuple[int, int], 
              starting_position: Tuple[int, int] = (0, 0),
              max_steps: Optional[int] = None) -> List[Position]:
        """
        Execute the program and generate a timeline.
        
        Args:
            widget_size: The size of the widget being animated (width, height).
            container_size: The size of the container (width, height).
            starting_position: The initial position (x, y) for the timeline, defaults to (0,0).
            max_steps: Maximum number of steps to generate (None for unlimited).
            
        Returns:
            A list of Positions representing the animation timeline.
        """
        # Update widget and container sizes
        self.context.variables["widget"]["width"] = widget_size[0]
        self.context.variables["widget"]["height"] = widget_size[1]
        self.context.variables["container"]["width"] = container_size[0]
        self.context.variables["container"]["height"] = container_size[1]
        
        # Update widget position with the provided starting position
        self.context.variables["widget"]["x"] = starting_position[0]
        self.context.variables["widget"]["y"] = starting_position[1]
        
        # Clear any previous execution state
        self.context.timeline = []
        self.context.tick_position = 0
        self.context.break_loop = False
        self.context.continue_loop = False
        self.context.current_segment = None
        self.context.segments = {}
        self.context.period = None
        self.context.start_at = 0
        self.context.pauses = []
        self.context.pause_ends = []
        
        # Reset SCROLL_CLIP tracking variables
        self.context.scroll_clip_start_x = None
        self.context.scroll_clip_start_y = None
        self.context.scroll_clip_total_moved = 0
        self.context.scroll_clip_stabilized = False
        
        # Reset SLIDE tracking variables
        self.context.slide_start_x = None
        self.context.slide_start_y = None
        self.context.slide_total_moved = 0
        self.context.slide_stabilized = False
        self.context.slide_progress = None
        
        # Start with the widget at the provided position
        initial_pos = Position(x=starting_position[0], y=starting_position[1])
        self.context.timeline.append(initial_pos)
        
        # Execute the program statements with incremental timeline generation
        self._execute_program_incrementally(max_steps)
        
        # Apply period if defined
        if self.context.period is not None:
            # Trim timeline to period length (keeping the first position)
            if len(self.context.timeline) > self.context.period:
                self.context.timeline = self.context.timeline[:self.context.period]
        
        # Apply start_at
        if self.context.start_at > 0:
            # Rotate the timeline to start at the specified tick
            start_at = min(self.context.start_at, len(self.context.timeline) - 1)
            self.context.timeline = (
                self.context.timeline[start_at:] + self.context.timeline[:start_at]
            )
        
        return self.context.timeline
        
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
        
        while step_count < safety_limit and len(self.context.timeline) < max_timeline_length:
            # Remember current timeline length to detect if any positions were added
            original_timeline_length = len(self.context.timeline)
            
            # Get current position
            current_x = self.context.variables["widget"]["x"]
            current_y = self.context.variables["widget"]["y"]
            
            # Execute one iteration of the program
            self.logger.debug(f"Step {step_count}: Executing program from position ({current_x}, {current_y})")
            self._execute_one_step(self.program.statements)
            
            # Check if the timeline length increased
            new_timeline_length = len(self.context.timeline)
            if new_timeline_length <= original_timeline_length:
                # No new positions added, might be at the end of movement
                stable_position_count += 1
                self.logger.debug(f"No new positions added at step {step_count}")
                
                # Break if stable for a certain number of iterations
                if stable_position_count >= 5:
                    self.logger.debug("Position stabilized, ending timeline generation")
                    break
            else:
                # Reset stable position counter if new positions were added
                stable_position_count = 0
            
            # Check for position loops (repeating the same positions)
            latest_pos = (self.context.variables["widget"]["x"], self.context.variables["widget"]["y"])
            if latest_pos in position_history:
                self.logger.debug(f"Position loop detected at {latest_pos}, ending timeline generation")
                break
            position_history.add(latest_pos)
            
            step_count += 1
            
            # Safety check to avoid very large timelines
            if len(self.context.timeline) >= max_timeline_length:
                self.logger.debug(f"Reached maximum timeline length of {max_timeline_length}")
                break
                
        self.logger.debug(f"Timeline generation completed after {step_count} steps, {len(self.context.timeline)} positions")
    
    def _execute_one_step(self, statements: List[Statement]) -> None:
        """
        Execute one step through the program statements.
        This executes each statement once, allowing for incremental timeline building.
        
        Args:
            statements: The statements to execute.
        """
        for stmt in statements:
            if self.context.break_loop or self.context.continue_loop:
                # Exit early if we encountered a BREAK or CONTINUE
                break
                
            self._execute_statement_once(stmt)
    
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
            self.context.break_loop = True
        elif isinstance(stmt, ContinueStatement):
            self.context.continue_loop = True
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
        
        # Ensure widget position in environment is synced with current position
        # This is crucial for conditionals to work correctly
        self.context.variables["widget"]["x"] = current_x
        self.context.variables["widget"]["y"] = current_y
        
        # Handle direction-based movement
        if stmt.direction is not None:
            # Get distance
            distance = self._evaluate_expression(stmt.distance)
            
            # Get step and interval from options
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # Determine direction vector
            dx, dy = 0, 0
            if stmt.direction == Direction.LEFT:
                dx = -step
            elif stmt.direction == Direction.RIGHT:
                dx = step
            elif stmt.direction == Direction.UP:
                dy = -step
            elif stmt.direction == Direction.DOWN:
                dy = step
            
            # For incremental execution, just move one step
            new_x = current_x + dx
            new_y = current_y + dy
            
            # Add position with appropriate interval
            for _ in range(interval):
                pos = Position(x=new_x, y=new_y)
                self.context.timeline.append(pos)
                self.context.tick_position += 1
            
            # Update widget position in environment
            self.context.variables["widget"]["x"] = new_x
            self.context.variables["widget"]["y"] = new_y
            
            self.logger.debug(f"Updated widget position: x={new_x}, y={new_y}")
        
        # Handle absolute movement (from start to end coordinates)
        else:
            start_x = self._evaluate_expression(stmt.start_x)
            end_x = self._evaluate_expression(stmt.end_x)
            
            # Handle optional Y coordinates
            start_y = current_y
            end_y = current_y
            if stmt.start_y is not None and stmt.end_y is not None:
                start_y = self._evaluate_expression(stmt.start_y)
                end_y = self._evaluate_expression(stmt.end_y)
            
            # Get step and interval from options
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # Calculate total distance and number of steps
            dx = end_x - start_x
            dy = end_y - start_y
            distance = max(abs(dx), abs(dy))
            num_steps = distance // step
            
            if num_steps > 0:
                step_x = dx / num_steps
                step_y = dy / num_steps
                
                # For incremental execution, just move one step from current position
                # If we're not already on this movement path, start at beginning
                if abs(current_x - start_x) > 0.1 or abs(current_y - start_y) > 0.1:
                    # Not on the path yet, start at beginning
                    current_x = start_x
                    current_y = start_y
                
                current_x += step_x
                current_y += step_y
                
                # Add position with appropriate interval
                for _ in range(interval):
                    pos = Position(x=int(round(current_x)), y=int(round(current_y)))
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                
                # Update widget position in environment
                self.context.variables["widget"]["x"] = int(round(current_x))
                self.context.variables["widget"]["y"] = int(round(current_y))
                
                self.logger.debug(f"Updated widget position: x={current_x}, y={current_y}")
    
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
        for _ in range(duration):
            # Create a copy of the current position with pause flag
            pause_pos = Position(
                x=current_pos.x, 
                y=current_pos.y,
                pause=True
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
        # Reset to position (0, 0)
        pos = Position(x=0, y=0)
        self.context.timeline.append(pos)
        self.context.tick_position += 1
        
        # Update widget position in environment
        self.context.variables["widget"]["x"] = 0
        self.context.variables["widget"]["y"] = 0
        
        # Debug log to verify widget position is updating
        self.logger.debug("Reset widget position to (0,0)")
    
    def _execute_if_once(self, stmt: IfStatement) -> None:
        """
        Execute an IF statement for one step.
        
        Args:
            stmt: The IF statement to execute.
        """
        # Evaluate the main condition
        condition_result = self._evaluate_condition(stmt.condition)
        self.logger.debug(f"IF condition evaluated to {condition_result}")
        
        if condition_result:
            # Execute the then branch
            self._execute_one_step(stmt.then_branch.statements)
        else:
            # Check ELSEIF branches
            executed = False
            for condition, block in stmt.elseif_branches:
                if self._evaluate_condition(condition):
                    self._execute_one_step(block.statements)
                    executed = True
                    break
            
            # Execute ELSE branch if no conditions matched
            if not executed and stmt.else_branch:
                self._execute_one_step(stmt.else_branch.statements)
    
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
        
        # Execute loop body once
        self._execute_one_step(stmt.body.statements)
        
        # Update loop counter if named
        if stmt.name:
            self.context.loop_counters[stmt.name] += 1
    
    def _execute_timeline_statement_once(self, stmt: TimelineStatement) -> None:
        """
        Execute a timeline-related statement for one step.
        
        Args:
            stmt: The timeline statement to execute.
        """
        if isinstance(stmt, PeriodStatement):
            self.context.period = self._evaluate_expression(stmt.ticks)
        elif isinstance(stmt, StartAtStatement):
            self.context.start_at = self._evaluate_expression(stmt.tick)
        elif isinstance(stmt, SegmentStatement):
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
        elif isinstance(stmt, PositionAtStatement):
            # Execute the position_at body once
            self._execute_one_step(stmt.body.statements)
    
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
                # Only add the stabilization position once
                if not self.context.scroll_clip_stabilized:
                    self.logger.debug(f"SCROLL_CLIP reached target distance {target_distance}, adding stabilization position")
                    
                    # Add the current position with pause=True to mark it as a stable position
                    pos = Position(x=current_x, y=current_y, pause=True)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    
                    # Mark that we've stabilized this ScrollClip command
                    self.context.scroll_clip_stabilized = True
                return
            
            # Calculate move based on direction
            if direction == Direction.LEFT:
                # Determine step, capped at remaining distance
                remaining = min(step, target_distance - self.context.scroll_clip_total_moved)
                dx, dy = -remaining, 0
            elif direction == Direction.RIGHT:
                remaining = min(step, target_distance - self.context.scroll_clip_total_moved)
                dx, dy = remaining, 0
            elif direction == Direction.UP:
                remaining = min(step, target_distance - self.context.scroll_clip_total_moved)
                dx, dy = 0, -remaining
            elif direction == Direction.DOWN:
                remaining = min(step, target_distance - self.context.scroll_clip_total_moved)
                dx, dy = 0, remaining
            else:
                self.logger.warning(f"Unsupported direction for SCROLL_CLIP: {direction}")
                return
                
            # Update position directly
            new_x = current_x + dx
            new_y = current_y + dy
            
            # Add the position multiple times based on interval
            for _ in range(interval):
                pos = Position(x=new_x, y=new_y)
                self.context.timeline.append(pos)
                self.context.tick_position += 1
            
            # Update widget position in environment
            self.context.variables["widget"]["x"] = new_x
            self.context.variables["widget"]["y"] = new_y
            
            # Update total moved distance
            self.context.scroll_clip_total_moved += abs(dx) + abs(dy)
            
            # Check if we've reached (or exceeded) the target distance after this move
            if self.context.scroll_clip_total_moved >= target_distance:
                self.logger.debug(f"SCROLL_CLIP reached target distance {target_distance}, final position: ({new_x}, {new_y})")
                
                # Add stabilization position if not done yet
                if not self.context.scroll_clip_stabilized:
                    pause_pos = Position(x=new_x, y=new_y, pause=True)
                    self.context.timeline.append(pause_pos)
                    self.context.tick_position += 1
                    self.context.scroll_clip_stabilized = True
            else:
                self.logger.debug(f"SCROLL_CLIP updated position: x={new_x}, y={new_y}, moved so far: {self.context.scroll_clip_total_moved}")
        
        elif isinstance(stmt, ScrollLoopStatement):
            # Handle SCROLL_LOOP
            self.logger.debug(f"Executing SCROLL_LOOP with direction {stmt.direction}")
            
            # Create and execute equivalent move statement
            move_stmt = MoveStatement(
                location=stmt.location,
                direction=stmt.direction,
                distance=stmt.distance,
                options=stmt.options
            )
            
            self._execute_move_once(move_stmt)
            
        elif isinstance(stmt, ScrollBounceStatement):
            # Handle SCROLL_BOUNCE
            self.logger.debug(f"Executing SCROLL_BOUNCE with direction {stmt.direction}")
            
            # Create and execute equivalent move statement
            move_stmt = MoveStatement(
                location=stmt.location,
                direction=stmt.direction,
                distance=stmt.distance,
                options=stmt.options
            )
            
            self._execute_move_once(move_stmt)
            
        elif isinstance(stmt, SlideStatement):
            # Handle SLIDE
            self.logger.debug(f"Executing SLIDE with direction {stmt.direction}")
            
            # Initialize tracking state if not already set
            if not hasattr(self.context, "slide_stabilized"):
                self.context.slide_stabilized = False
                self.context.slide_total_moved = 0
            
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
            if self.context.slide_total_moved >= target_distance:
                # Only add the stabilization position once
                if not self.context.slide_stabilized:
                    self.logger.debug(f"SLIDE reached target distance {target_distance}, adding stabilization position")
                    
                    # Add the current position with pause=True to mark it as a stable position
                    pos = Position(x=current_x, y=current_y, pause=True)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    
                    # Mark that we've stabilized this Slide command
                    self.context.slide_stabilized = True
                
                # Don't add additional positions after stabilizing
                return
            
            # Calculate move based on direction
            if direction == Direction.LEFT:
                # Determine step, capped at remaining distance
                remaining = min(step, target_distance - self.context.slide_total_moved)
                dx, dy = -remaining, 0
            elif direction == Direction.RIGHT:
                remaining = min(step, target_distance - self.context.slide_total_moved)
                dx, dy = remaining, 0
            elif direction == Direction.UP:
                remaining = min(step, target_distance - self.context.slide_total_moved)
                dx, dy = 0, -remaining
            elif direction == Direction.DOWN:
                remaining = min(step, target_distance - self.context.slide_total_moved)
                dx, dy = 0, remaining
            elif direction == Direction.TOP:
                remaining = min(step, target_distance - self.context.slide_total_moved)
                dx, dy = 0, -remaining
            elif direction == Direction.BOTTOM:
                remaining = min(step, target_distance - self.context.slide_total_moved)
                dx, dy = 0, remaining
            else:
                self.logger.warning(f"Unsupported direction for SLIDE: {direction}")
                return
            
            # Update position directly
            new_x = current_x + dx
            new_y = current_y + dy
            
            # Add the position multiple times based on interval
            for _ in range(interval):
                pos = Position(x=new_x, y=new_y)
                self.context.timeline.append(pos)
                self.context.tick_position += 1
            
            # Update widget position in environment
            self.context.variables["widget"]["x"] = new_x
            self.context.variables["widget"]["y"] = new_y
            
            # Update total moved distance
            self.context.slide_total_moved += abs(dx) + abs(dy)
            
            # Check if we've reached (or exceeded) the target distance after this move
            if self.context.slide_total_moved >= target_distance:
                self.logger.debug(f"SLIDE reached target distance {target_distance}, final position: ({new_x}, {new_y})")
                
                # Add stabilization position if not done yet
                if not self.context.slide_stabilized:
                    pause_pos = Position(x=new_x, y=new_y, pause=True)
                    self.context.timeline.append(pause_pos)
                    self.context.tick_position += 1
                    self.context.slide_stabilized = True
            else:
                self.logger.debug(f"SLIDE updated position: x={new_x}, y={new_y}, moved so far: {self.context.slide_total_moved}")
        
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