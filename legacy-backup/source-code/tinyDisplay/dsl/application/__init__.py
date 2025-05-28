"""
tinyDisplay Application Widget DSL Package.

This package provides parsers, validators, and interpreters for the Application Widget DSL,
which allows declarative definition of UI components for the tinyDisplay system.

[This is a placeholder for future implementation]
"""

from .tokens import Token, TokenType
from .lexer import Lexer
from .ast import (
    # Base types
    Location, Expression, Literal, Variable, PropertyAccess, MacroReference,
    ObjectLiteral, ArrayLiteral, BinaryExpression, Statement, Program,
    
    # Declarations
    ImportStatement, ResourcesBlock, DirDeclaration, FileDeclaration,
    SearchPathDeclaration, EnvBlock, EnvDeclaration, MacroDeclaration,
    DisplayDeclaration, WidgetDeclaration, TimelineBlock, CanvasDeclaration,
    PlacementStatement, StackDeclaration, AppendStatement, SequenceDeclaration,
    SequenceAppendStatement, IndexDeclaration, IndexAppendStatement,
    ThemeDeclaration, StyleDeclaration, StateDeclaration, DataSourceDeclaration,
    BindingStatement, AppDeclaration, ReferenceStatement
)
from .parser import Parser, ParseError
from .validator import Validator, ValidationError 