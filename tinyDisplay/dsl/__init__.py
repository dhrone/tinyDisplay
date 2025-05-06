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
    Token as MarqueeToken, 
    TokenType as MarqueeTokenType, 
    Lexer as MarqueeLexer,
    Direction, 
    SlideAction,
    Parser as MarqueeParser, 
    ParseError as MarqueeParseError,
    Validator as MarqueeValidator, 
    ValidationError as MarqueeValidationError,
    
    # AST nodes
    Location,
    Expression,
    Literal,
    Variable,
    BinaryExpr,
    PropertyAccess,
    Statement,
    Block,
    MoveStatement,
    PauseStatement,
    ResetPositionStatement,
    LoopStatement,
    Condition,
    IfStatement,
    BreakStatement,
    ContinueStatement,
    SyncStatement,
    WaitForStatement,
    TimelineStatement,
    PeriodStatement,
    StartAtStatement,
    SegmentStatement,
    PositionAtStatement,
    ScheduleAtStatement,
    OnVariableChangeStatement,
    ScrollStatement,
    SlideStatement,
    PopUpStatement,
    Program as MarqueeProgram
)

# Re-export application DSL functionality
from .application import (
    # Parser utilities
    Parser as ApplicationParser,
    ParseError as ApplicationParseError,
    Validator as ApplicationValidator, 
    ValidationError as ApplicationValidationError,
    
    # Token-related
    Token as ApplicationToken,
    TokenType as ApplicationTokenType,
    Lexer as ApplicationLexer,
    
    # AST nodes
    # Base types
    Location as AppLocation,
    Expression as AppExpression,
    Literal as AppLiteral,
    Variable as AppVariable,
    PropertyAccess as AppPropertyAccess,
    MacroReference,
    ObjectLiteral,
    ArrayLiteral,
    BinaryExpression,
    Statement as AppStatement,
    Program as ApplicationProgram,
    
    # Declarations
    ImportStatement,
    ResourcesBlock,
    DirDeclaration,
    FileDeclaration,
    SearchPathDeclaration,
    EnvBlock,
    EnvDeclaration,
    MacroDeclaration,
    DisplayDeclaration,
    WidgetDeclaration,
    TimelineBlock,
    CanvasDeclaration,
    PlacementStatement,
    StackDeclaration,
    AppendStatement,
    SequenceDeclaration,
    SequenceAppendStatement,
    IndexDeclaration,
    IndexAppendStatement,
    ThemeDeclaration,
    StyleDeclaration,
    StateDeclaration,
    DataSourceDeclaration,
    BindingStatement,
    AppDeclaration,
    ReferenceStatement
)

# Helper functions for application DSL
from .application.tokens import Token as AppToken, TokenType as AppTokenType
from .application.lexer import Lexer as AppLexer
from .application.parser import Parser as AppParser, ParseError as AppParseError
from .application.validator import Validator as AppValidator, ValidationError as AppValidationError


def parse_application_dsl(source: str) -> ApplicationProgram:
    """
    Parse Application Widget DSL source code.
    
    Args:
        source: The DSL source code to parse.
        
    Returns:
        The parsed AST.
    """
    lexer = AppLexer(source)
    tokens = lexer.scan_tokens()
    parser = AppParser(tokens)
    return parser.parse()


def validate_application_dsl(program: ApplicationProgram) -> list[AppValidationError]:
    """
    Validate an Application Widget DSL AST.
    
    Args:
        program: The AST to validate.
        
    Returns:
        A list of validation errors.
    """
    validator = AppValidator(program)
    return validator.validate()


def parse_and_validate_application_dsl(source: str) -> tuple[ApplicationProgram, list[AppValidationError]]:
    """
    Parse and validate Application Widget DSL source code.
    
    Args:
        source: The DSL source code to parse and validate.
        
    Returns:
        A tuple containing the parsed AST and a list of validation errors.
    """
    lexer = AppLexer(source)
    tokens = lexer.scan_tokens()
    parser = AppParser(tokens)
    program = parser.parse()
    
    # Include parser errors as validation errors
    errors = []
    if parser.errors:
        from .application.ast import Location
        # Convert parser errors to validation errors
        for error_msg in parser.errors:
            # Extract line and column information from error message if available
            import re
            match = re.search(r"Error at line (\d+):(\d+)", error_msg)
            if match:
                line = int(match.group(1))
                column = int(match.group(2))
                location = Location(line, column)
            else:
                location = Location(0, 0)
            errors.append(AppValidationError(location=location, message=f"Syntax error: {error_msg}"))
    
    # Add standard validation errors
    validation_errors = validate_application_dsl(program)
    errors.extend(validation_errors)
    
    return program, errors

# Convenient aliases
parse_dsl = parse_marquee_dsl
validate_dsl = validate_marquee_dsl
parse_and_validate_dsl = parse_and_validate_marquee_dsl 