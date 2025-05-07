"""
tinyDisplay Marquee Animation DSL Package.

This package provides parsers, validators, and interpreters for the Marquee Animation DSL,
which allows declarative definition of widget animations for the tinyDisplay system.
"""

from .tokens import Token, TokenType
from .lexer import Lexer
from .ast import (
    Direction, SlideAction, Location,
    Expression, Literal, Variable, BinaryExpr, PropertyAccess,
    Statement, Block, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, Condition, IfStatement, BreakStatement, ContinueStatement,
    SyncStatement, WaitForStatement, TimelineStatement, PeriodStatement,
    StartAtStatement, SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, ScrollClipStatement, 
    ScrollLoopStatement, ScrollBounceStatement, SlideStatement, PopUpStatement,
    Program
)
from .parser import Parser, ParseError
from .validator import Validator, ValidationError


def parse_marquee_dsl(source: str) -> Program:
    """
    Parse a Marquee DSL string into an AST.
    
    Args:
        source: The DSL source code to parse.
        
    Returns:
        A Program representing the parsed DSL.
        
    Raises:
        ParseError: If the DSL contains syntax errors.
    """
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()
    
    parser = Parser(tokens)
    program = parser.parse()
    
    return program


def validate_marquee_dsl(program: Program) -> list[ValidationError]:
    """
    Validate a parsed Marquee DSL AST.
    
    Args:
        program: The AST to validate.
        
    Returns:
        A list of validation errors, or an empty list if validation succeeded.
    """
    validator = Validator(program)
    return validator.validate()


def parse_and_validate_marquee_dsl(source: str) -> tuple[Program, list[ValidationError]]:
    """
    Parse and validate a Marquee DSL string.
    
    Args:
        source: The DSL source code to parse and validate.
        
    Returns:
        A tuple of (Program, list of validation errors).
    """
    program = parse_marquee_dsl(source)
    errors = validate_marquee_dsl(program)
    return program, errors 