"""
tinyDisplay Marquee DSL Executor.

This module provides a class that can execute Marquee DSL programs.
It serves as the runtime environment for the Marquee Animation DSL.
"""

from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
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
    """
    x: int
    y: int
    pause: bool = False
    pause_end: bool = False
    terminal: bool = False  # New flag for terminal positions
    segment_start: bool = False
    segment_end: bool = False
    segment_name: Optional[str] = None
    
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
        return False
        
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
    break_loop: bool = False
    continue_loop: bool = False
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
        
        # Reset bounce tracking variables
        self.context.bounce_direction = None
        self.context.bounce_total_moved = 0
        self.context.bounce_max_distance = 0
        self.context.bounce_at_edge = False
        self.context.bounce_paused_ticks = 0
        self.context.bounce_pause_duration = 0
        
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
                    
                    # Add the current position with terminal=True to mark it as a final state
                    pos = Position(x=current_x, y=current_y, terminal=True)
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
                    pause_pos = Position(x=new_x, y=new_y, terminal=True)
                    self.context.timeline.append(pause_pos)
                    self.context.tick_position += 1
                    self.context.scroll_clip_stabilized = True
            else:
                self.logger.debug(f"SCROLL_CLIP updated position: x={new_x}, y={new_y}, moved so far: {self.context.scroll_clip_total_moved}")
        
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
            
            # For compatibility with the position reset mechanism,
            # use the classic MoveStatement but limit timeline generation
            # to one complete cycle when setting the period
            move_stmt = MoveStatement(
                location=stmt.location,
                direction=direction,
                distance=distance,
                options=stmt.options
            )
            
            # Execute the move once
            self._execute_move_once(move_stmt)
            
            # Set period if not already defined
            # This is the key optimization - we only need one full cycle of positions
            if self.context.period is None:
                cycle_length = min_cycle_len * interval
                self.context.period = cycle_length
                self.logger.debug(f"Setting implicit PERIOD({cycle_length}) for SCROLL_LOOP")
        
        elif isinstance(stmt, ScrollBounceStatement):
            # Handle SCROLL_BOUNCE
            self.logger.debug(f"Executing SCROLL_BOUNCE with direction {stmt.direction}")
            
            # Initialize tracking state if not already set
            if not hasattr(self.context, "bounce_direction") or self.context.bounce_direction is None:
                # Debug direction value
                self.logger.debug(f"Initializing SCROLL_BOUNCE direction: {stmt.direction} (type: {type(stmt.direction)})")
                
                # Start with the initial direction
                self.context.bounce_direction = stmt.direction
                self.context.bounce_total_moved = 0
                self.context.bounce_max_distance = self._evaluate_expression(stmt.distance)
                self.context.bounce_at_edge = False
                self.context.bounce_paused_ticks = 0
                self.context.bounce_pause_duration = self._get_option(stmt.options, "pause_at_ends", 0)
                
                # Fallback to LEFT if direction is somehow None
                if self.context.bounce_direction is None:
                    self.logger.warning("Direction was None, defaulting to LEFT")
                    self.context.bounce_direction = Direction.LEFT
            
            # Get current position
            current_pos = self.context.timeline[-1]
            current_x = current_pos.x
            current_y = current_pos.y
            
            # Get parameters
            step = self._get_option(stmt.options, "step", 1)
            interval = self._get_option(stmt.options, "interval", 1)
            
            # Check if we're pausing at an edge
            if self.context.bounce_at_edge:
                # If we've paused enough ticks, flip direction and continue
                if self.context.bounce_paused_ticks >= self.context.bounce_pause_duration:
                    # Reset pause state
                    self.context.bounce_at_edge = False
                    self.context.bounce_paused_ticks = 0
                    
                    # Reverse direction
                    if self.context.bounce_direction == Direction.LEFT:
                        self.context.bounce_direction = Direction.RIGHT
                    elif self.context.bounce_direction == Direction.RIGHT:
                        self.context.bounce_direction = Direction.LEFT
                    elif self.context.bounce_direction == Direction.UP:
                        self.context.bounce_direction = Direction.DOWN
                    elif self.context.bounce_direction == Direction.DOWN:
                        self.context.bounce_direction = Direction.UP
                    
                    self.logger.debug(f"SCROLL_BOUNCE reversed direction to {self.context.bounce_direction}")
                    
                    # Reset total moved for the new direction
                    self.context.bounce_total_moved = 0
                else:
                    # Add another pause position at the exact same coordinate as the last position
                    pos = Position(x=current_x, y=current_y, pause=True)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    self.context.bounce_paused_ticks += 1
                    return
            
            # Calculate move based on current bounce direction
            if self.context.bounce_direction == Direction.LEFT:
                dx, dy = -step, 0
            elif self.context.bounce_direction == Direction.RIGHT:
                dx, dy = step, 0
            elif self.context.bounce_direction == Direction.UP:
                dx, dy = 0, -step
            elif self.context.bounce_direction == Direction.DOWN:
                dx, dy = 0, step
            else:
                self.logger.warning(f"Unsupported direction for SCROLL_BOUNCE: {self.context.bounce_direction}")
                return
            
            # Update position
            new_x = current_x + dx
            new_y = current_y + dy
            
            # Update total distance moved in current direction
            self.context.bounce_total_moved += abs(dx) + abs(dy)
            
            # Check if we're at a boundary
            if self.context.bounce_total_moved >= self.context.bounce_max_distance:
                self.logger.debug(f"SCROLL_BOUNCE reached edge at distance {self.context.bounce_total_moved}")
                
                # Start pausing at edge if pause is configured
                if self.context.bounce_pause_duration > 0:
                    self.logger.debug(f"SCROLL_BOUNCE pausing at edge for {self.context.bounce_pause_duration} ticks")
                    self.context.bounce_at_edge = True
                    self.context.bounce_paused_ticks = 0
                    
                    # Add a pause position
                    pause_pos = Position(x=new_x, y=new_y, pause=True)
                    self.context.timeline.append(pause_pos)
                    self.context.tick_position += 1
                    
                    # Increment paused ticks (but we still need to return 
                    # to prevent adding the regular position)
                    self.context.bounce_paused_ticks += 1
                    return
                else:
                    # No pause, immediately reverse direction
                    # Reverse direction
                    if self.context.bounce_direction == Direction.LEFT:
                        self.context.bounce_direction = Direction.RIGHT
                    elif self.context.bounce_direction == Direction.RIGHT:
                        self.context.bounce_direction = Direction.LEFT
                    elif self.context.bounce_direction == Direction.UP:
                        self.context.bounce_direction = Direction.DOWN
                    elif self.context.bounce_direction == Direction.DOWN:
                        self.context.bounce_direction = Direction.UP
                    
                    self.logger.debug(f"SCROLL_BOUNCE reversed direction to {self.context.bounce_direction}")
                    
                    # Reset total moved for the new direction
                    self.context.bounce_total_moved = 0
                    
                    # Add a position at the edge
                    pos = Position(x=new_x, y=new_y)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                    return
            
            # Add the position multiple times based on interval
            for _ in range(interval):
                pos = Position(x=new_x, y=new_y)
                self.context.timeline.append(pos)
                self.context.tick_position += 1
            
            # Update widget position in environment
            self.context.variables["widget"]["x"] = new_x
            self.context.variables["widget"]["y"] = new_y
        
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
                    
                    # Add the current position with terminal=True to mark it as a final state
                    pos = Position(x=current_x, y=current_y, terminal=True)
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
                    pause_pos = Position(x=new_x, y=new_y, terminal=True)
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