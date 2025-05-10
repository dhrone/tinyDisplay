"""
Abstract Syntax Tree (AST) for the tinyDisplay Marquee Animation DSL.

This module defines the node classes that make up the AST for the DSL.
Each class represents a different construct in the language.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Union, Any


class Direction(Enum):
    """Direction constants for movement."""
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    TOP = auto()
    BOTTOM = auto()


class SlideAction(Enum):
    """Actions for slide animations."""
    IN = auto()
    OUT = auto()
    IN_OUT = auto()


@dataclass
class Location:
    """Source code location for error reporting."""
    line: int
    column: int
    
    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass
class Expression:
    """Base class for all expressions."""
    location: Location


@dataclass
class Literal(Expression):
    """A literal value (number, string, etc.)."""
    value: Union[int, float, str, bool]


@dataclass
class Variable(Expression):
    """A variable reference."""
    name: str


@dataclass
class BinaryExpr(Expression):
    """A binary expression (e.g., a + b)."""
    left: Expression
    operator: str
    right: Expression


@dataclass
class PropertyAccess(Expression):
    """A property access expression (e.g., widget.x)."""
    object: Expression
    property: str


@dataclass
class Statement:
    """Base class for all statements."""
    location: Location


@dataclass
class Block(Statement):
    """A block of statements."""
    statements: List[Statement]


@dataclass
class MoveStatement(Statement):
    """
    A MOVE statement.
    
    Examples:
    - MOVE(startX, endX);
    - MOVE(startX, endX, startY, endY);
    - MOVE(LEFT, distance);
    """
    # For MOVE(startX, endX, startY, endY)
    start_x: Optional[Expression] = None
    end_x: Optional[Expression] = None
    start_y: Optional[Expression] = None
    end_y: Optional[Expression] = None
    
    # For MOVE(direction, distance)
    direction: Optional[Direction] = None
    distance: Optional[Expression] = None
    
    # Options like step, interval, etc.
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class PauseStatement(Statement):
    """A PAUSE statement (e.g., PAUSE(10))."""
    duration: Expression
    

@dataclass
class ResetPositionStatement(Statement):
    """A RESET_POSITION statement."""
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class LoopStatement(Statement):
    """
    A LOOP statement.
    
    Examples:
    - LOOP(5) { ... } END;
    - LOOP(INFINITE AS name) { ... } END;
    """
    count: Union[Expression, str]  # Expression or "INFINITE"
    body: Block
    name: Optional[str] = None


@dataclass
class Condition:
    """A condition in an IF statement."""
    left: Expression
    operator: str
    right: Expression
    location: Location


@dataclass
class IfStatement(Statement):
    """
    An IF statement.
    
    Examples:
    - IF(condition) { ... } END;
    - IF(condition) { ... } ELSEIF(condition) { ... } ELSE { ... } END;
    """
    condition: Condition
    then_branch: Block
    elseif_branches: List[tuple[Condition, Block]] = field(default_factory=list)
    else_branch: Optional[Block] = None


@dataclass
class BreakStatement(Statement):
    """A BREAK statement."""
    pass


@dataclass
class ContinueStatement(Statement):
    """A CONTINUE statement."""
    pass


@dataclass
class SyncStatement(Statement):
    """A SYNC statement (e.g., SYNC(event))."""
    event: str


@dataclass
class WaitForStatement(Statement):
    """A WAIT_FOR statement (e.g., WAIT_FOR(event, ticks))."""
    event: str
    ticks: Expression


@dataclass
class TimelineStatement(Statement):
    """Base class for timeline-related statements."""
    pass


@dataclass
class PeriodStatement(TimelineStatement):
    """A PERIOD statement (e.g., PERIOD(100))."""
    ticks: Expression


@dataclass
class StartAtStatement(TimelineStatement):
    """A START_AT statement (e.g., START_AT(10))."""
    tick: Expression


@dataclass
class SegmentStatement(TimelineStatement):
    """
    A SEGMENT statement.
    
    Example:
    SEGMENT(name, startTick, endTick) { ... } END;
    """
    name: str
    start_tick: Expression
    end_tick: Expression
    body: Block


@dataclass
class PositionAtStatement(TimelineStatement):
    """
    A POSITION_AT statement.
    
    Example:
    POSITION_AT(tick) => { ... } END;
    """
    tick: Expression
    body: Block


@dataclass
class ScheduleAtStatement(TimelineStatement):
    """A SCHEDULE_AT statement (e.g., SCHEDULE_AT(tick, action))."""
    tick: Expression
    action: str


@dataclass
class OnVariableChangeStatement(Statement):
    """
    An ON_VARIABLE_CHANGE statement.
    
    Examples:
    - ON_VARIABLE_CHANGE(variable) { ... } END;
    - ON_VARIABLE_CHANGE([var1, var2]) { ... } END;
    """
    variables: List[str]
    body: Block


@dataclass
class HighLevelCommandStatement(Statement):
    """Base class for high-level commands."""
    pass


@dataclass
class ScrollStatement(HighLevelCommandStatement):
    """
    A SCROLL statement (legacy).
    
    Example:
    SCROLL(direction, distance) { options };
    """
    direction: Direction
    distance: Expression
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class ScrollClipStatement(HighLevelCommandStatement):
    """
    A SCROLL_CLIP statement.
    
    Example:
    SCROLL_CLIP(direction, distance) { options };
    
    One-way scrolling that stops at the end.
    """
    direction: Direction
    distance: Expression
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class ScrollLoopStatement(HighLevelCommandStatement):
    """
    A SCROLL_LOOP statement.
    
    Example:
    SCROLL_LOOP(direction, distance) { options };
    
    Continuous scrolling with wrapping (traditional ticker/marquee).
    """
    direction: Direction
    distance: Expression
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class ScrollBounceStatement(HighLevelCommandStatement):
    """
    A SCROLL_BOUNCE statement.
    
    Example:
    SCROLL_BOUNCE(direction, distance) { options };
    
    Ping-pong scrolling that reverses direction at boundaries.
    """
    direction: Direction
    distance: Expression
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class SlideStatement(HighLevelCommandStatement):
    """
    A SLIDE statement.
    
    Example:
    SLIDE(direction, distance) { options };
    
    One-way movement with optional easing that stops at the end.
    """
    direction: Direction
    distance: Expression
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class PopUpStatement(HighLevelCommandStatement):
    """
    A POPUP statement.
    
    Example:
    POPUP({ options });
    """
    options: Dict[str, Expression] = field(default_factory=dict)


@dataclass
class DefineStatement(Statement):
    """
    Define a named sequence of statements that can be invoked later.
    
    Example:
    DEFINE sequence_name { ... };
    """
    name: str
    body: Block
    

@dataclass
class SequenceInvocationStatement(Statement):
    """
    Invocation of a previously defined sequence.
    
    Example:
    sequence_name();
    """
    name: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class Program:
    """The root of the AST, representing a complete program."""
    statements: List[Statement]
    
    @property
    def is_empty(self) -> bool:
        """Check if the program is empty."""
        return len(self.statements) == 0 