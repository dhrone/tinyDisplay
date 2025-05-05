"""
tinyDisplay Domain-Specific Language (DSL) Package.

This package provides parsers, validators, and interpreters for tinyDisplay DSLs,
which allow declarative definition of animations and UI components.
"""

# Re-export marquee DSL functionality
from .marquee import (
    # Parser utilities
    parse_marquee_dsl,
    validate_marquee_dsl,
    parse_and_validate_marquee_dsl,
    
    # Classes
    Token, TokenType, Lexer,
    Direction, SlideAction,
    Parser, ParseError,
    Validator, ValidationError,
    
    # AST nodes
    Location, Expression, Literal, Variable, BinaryExpr, PropertyAccess,
    Statement, Block, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, Condition, IfStatement, BreakStatement, ContinueStatement,
    SyncStatement, WaitForStatement, TimelineStatement, PeriodStatement,
    StartAtStatement, SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, SlideStatement, PopUpStatement,
    Program
)

# Convenient aliases
parse_dsl = parse_marquee_dsl
validate_dsl = validate_marquee_dsl
parse_and_validate_dsl = parse_and_validate_marquee_dsl 