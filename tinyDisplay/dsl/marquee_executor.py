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
    StartAtStatement, SegmentStatement, PositionAtStatement
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
        
    def execute(self, widget_size: Tuple[int, int], container_size: Tuple[int, int]) -> List[Position]:
        """
        Execute the program and generate a timeline.
        
        Args:
            widget_size: The size of the widget being animated (width, height).
            container_size: The size of the container (width, height).
            
        Returns:
            A list of Positions representing the animation timeline.
        """
        # Update widget and container sizes
        self.context.variables["widget"]["width"] = widget_size[0]
        self.context.variables["widget"]["height"] = widget_size[1]
        self.context.variables["container"]["width"] = container_size[0]
        self.context.variables["container"]["height"] = container_size[1]
        
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
        
        # Start with the widget at position (0, 0)
        initial_pos = Position(x=0, y=0)
        self.context.timeline.append(initial_pos)
        
        # Execute the program statements
        self._execute_block(self.program.statements)
        
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
    
    def _execute_block(self, statements: List[Statement]) -> None:
        """
        Execute a block of statements.
        
        Args:
            statements: The statements to execute.
        """
        for stmt in statements:
            if self.context.break_loop or self.context.continue_loop:
                # Exit early if we encountered a BREAK or CONTINUE
                break
                
            self._execute_statement(stmt)
    
    def _execute_statement(self, stmt: Statement) -> None:
        """
        Execute a single statement.
        
        Args:
            stmt: The statement to execute.
        """
        if isinstance(stmt, Block):
            self._execute_block(stmt.statements)
        elif isinstance(stmt, MoveStatement):
            self._execute_move(stmt)
        elif isinstance(stmt, PauseStatement):
            self._execute_pause(stmt)
        elif isinstance(stmt, ResetPositionStatement):
            self._execute_reset_position(stmt)
        elif isinstance(stmt, LoopStatement):
            self._execute_loop(stmt)
        elif isinstance(stmt, IfStatement):
            self._execute_if(stmt)
        elif isinstance(stmt, BreakStatement):
            self.context.break_loop = True
        elif isinstance(stmt, ContinueStatement):
            self.context.continue_loop = True
        elif isinstance(stmt, TimelineStatement):
            self._execute_timeline_statement(stmt)
        # Add other statement types as needed
    
    def _execute_move(self, stmt: MoveStatement) -> None:
        """
        Execute a MOVE statement.
        
        Args:
            stmt: The MOVE statement to execute.
        """
        # Get current position
        current_pos = self.context.timeline[-1]
        current_x = current_pos.x
        current_y = current_pos.y
        
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
            
            # Calculate number of steps
            num_steps = distance // step
            
            # Create a position for each step in the timeline
            for i in range(num_steps):
                new_x = current_x + dx
                new_y = current_y + dy
                
                # Add the same position multiple times based on interval
                for _ in range(interval):
                    pos = Position(x=new_x, y=new_y)
                    self.context.timeline.append(pos)
                    self.context.tick_position += 1
                
                # Update current position
                current_x = new_x
                current_y = new_y
                
                # Update widget position in environment
                self.context.variables["widget"]["x"] = current_x
                self.context.variables["widget"]["y"] = current_y
        
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
                
                # Set initial position
                current_x = start_x
                current_y = start_y
                
                # Create a position for each step
                for i in range(num_steps):
                    current_x += step_x
                    current_y += step_y
                    
                    # Add the same position multiple times based on interval
                    for _ in range(interval):
                        pos = Position(x=int(round(current_x)), y=int(round(current_y)))
                        self.context.timeline.append(pos)
                        self.context.tick_position += 1
                    
                    # Update widget position in environment
                    self.context.variables["widget"]["x"] = current_x
                    self.context.variables["widget"]["y"] = current_y
            
            # Ensure we end exactly at the target position
            if end_x != current_x or end_y != current_y:
                pos = Position(x=end_x, y=end_y)
                self.context.timeline.append(pos)
                self.context.tick_position += 1
                
                # Update widget position in environment
                self.context.variables["widget"]["x"] = end_x
                self.context.variables["widget"]["y"] = end_y
    
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
    
    def _execute_loop(self, stmt: LoopStatement) -> None:
        """
        Execute a LOOP statement.
        
        Args:
            stmt: The LOOP statement to execute.
        """
        # Determine loop count
        count = float('inf') if stmt.count == "INFINITE" else self._evaluate_expression(stmt.count)
        
        # Track loop counter for named loops
        if stmt.name:
            self.context.loop_counters[stmt.name] = 0
        
        # Execute the loop
        iteration = 0
        while iteration < count:
            # Update loop counter if named
            if stmt.name:
                self.context.loop_counters[stmt.name] = iteration
            
            # Reset control flags
            self.context.break_loop = False
            self.context.continue_loop = False
            
            # Execute loop body
            self._execute_block(stmt.body.statements)
            
            # Handle break
            if self.context.break_loop:
                self.context.break_loop = False
                break
                
            # Handle continue
            if self.context.continue_loop:
                self.context.continue_loop = False
                # Continue to next iteration
                pass
            
            iteration += 1
        
        # Clean up loop counter
        if stmt.name:
            del self.context.loop_counters[stmt.name]
    
    def _execute_if(self, stmt: IfStatement) -> None:
        """
        Execute an IF statement.
        
        Args:
            stmt: The IF statement to execute.
        """
        # Evaluate the main condition
        condition_result = self._evaluate_condition(stmt.condition)
        
        if condition_result:
            # Execute the then branch
            self._execute_block(stmt.then_branch.statements)
        else:
            # Check ELSEIF branches
            executed = False
            for condition, block in stmt.elseif_branches:
                if self._evaluate_condition(condition):
                    self._execute_block(block.statements)
                    executed = True
                    break
            
            # Execute ELSE branch if no conditions matched
            if not executed and stmt.else_branch:
                self._execute_block(stmt.else_branch.statements)
    
    def _execute_timeline_statement(self, stmt: TimelineStatement) -> None:
        """
        Execute a timeline-related statement.
        
        Args:
            stmt: The timeline statement to execute.
        """
        if isinstance(stmt, PeriodStatement):
            self.context.period = self._evaluate_expression(stmt.ticks)
        elif isinstance(stmt, StartAtStatement):
            self.context.start_at = self._evaluate_expression(stmt.tick)
        elif isinstance(stmt, SegmentStatement):
            self._execute_segment(stmt)
        elif isinstance(stmt, PositionAtStatement):
            self._execute_position_at(stmt)
    
    def _execute_segment(self, stmt: SegmentStatement) -> None:
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
        
        # Save current state
        prev_segment = self.context.current_segment
        
        # Set current segment
        self.context.current_segment = stmt.name
        
        # Execute the segment body
        self._execute_block(stmt.body.statements)
        
        # Restore previous segment
        self.context.current_segment = prev_segment
    
    def _execute_position_at(self, stmt: PositionAtStatement) -> None:
        """
        Execute a POSITION_AT statement.
        
        Args:
            stmt: The POSITION_AT statement to execute.
        """
        # Get the target tick
        tick = self._evaluate_expression(stmt.tick)
        
        # Save the current timeline position
        prev_tick_position = self.context.tick_position
        
        # Set the timeline position to the target tick
        self.context.tick_position = tick
        
        # Execute the position_at body
        self._execute_block(stmt.body.statements)
        
        # Restore the previous timeline position
        self.context.tick_position = prev_tick_position
    
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
        if name in options:
            return self._evaluate_expression(options[name])
        return default 