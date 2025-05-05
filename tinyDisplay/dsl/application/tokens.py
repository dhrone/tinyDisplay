"""
Token definitions for the tinyDisplay Application Widget DSL.

This module defines the token types and constants used by the lexer.
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional, Union


class TokenType(Enum):
    """Enum representing all possible token types in the Application Widget DSL."""
    # Special tokens
    EOF = auto()
    ERROR = auto()
    
    # Literals
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    IDENTIFIER = auto()
    BOOLEAN = auto()  # true/false
    PATH_LITERAL = auto()  # file path
    
    # Keywords - Definition
    DEFINE = auto()
    AS = auto()
    
    # Keywords - Widget types
    WIDGET = auto()
    TEXT = auto()
    IMAGE = auto()
    PROGRESSBAR = auto()
    LINE = auto()
    RECTANGLE = auto()
    
    # Keywords - Collections
    CANVAS = auto()
    STACK = auto()
    SEQUENCE = auto()
    INDEX = auto()
    
    # Keywords - Collection operations
    PLACE = auto()
    APPEND = auto()
    AT = auto()
    Z = auto()
    WHEN = auto()
    ACTIVE = auto()
    DEFAULT = auto()
    GAP = auto()
    
    # Keywords - Theme and styling
    THEME = auto()
    STYLE = auto()
    
    # Keywords - State and data
    STATE = auto()
    DATASOURCE = auto()
    BIND = auto()
    TO = auto()
    
    # Keywords - Application structure
    APP = auto()
    REFERENCE = auto()
    SCREENS = auto()
    DATASOURCES = auto()
    
    # Keywords - Timeline and animation
    TIMELINE = auto()
    
    # Keywords - Display configuration
    DISPLAY = auto()
    INTERFACE = auto()
    COLOR_MODE = auto()
    PINS = auto()
    
    # Keywords - Resource management
    RESOURCES = auto()
    PATH = auto()
    FILE = auto()
    SEARCH_PATH = auto()
    ENV = auto()
    
    # Keywords - Import
    IMPORT = auto()
    FROM = auto()
    
    # Keywords - Macro
    MACRO = auto()
    
    # Punctuation and operators
    LEFT_PAREN = auto()      # (
    RIGHT_PAREN = auto()     # )
    LEFT_BRACE = auto()      # {
    RIGHT_BRACE = auto()     # }
    LEFT_BRACKET = auto()    # [
    RIGHT_BRACKET = auto()   # ]
    COMMA = auto()           # ,
    DOT = auto()             # .
    SEMICOLON = auto()       # ;
    COLON = auto()           # :
    AT_SIGN = auto()         # @
    DOLLAR_SIGN = auto()     # $
    SLASH = auto()           # /
    
    # Operators
    PLUS = auto()            # +
    MINUS = auto()           # -
    STAR = auto()            # *
    EQUALS = auto()          # =
    EQUAL_EQUAL = auto()     # ==
    NOT_EQUALS = auto()      # !=
    GREATER = auto()         # >
    LESS = auto()            # <
    GREATER_EQUALS = auto()  # >=
    LESS_EQUALS = auto()     # <=


@dataclass
class Token:
    """Represents a token in the DSL source code."""
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int
    
    def __str__(self) -> str:
        """String representation of the token."""
        if self.literal is not None:
            return f"{self.type.name}({self.lexeme})[{self.literal}] at {self.line}:{self.column}"
        return f"{self.type.name}({self.lexeme}) at {self.line}:{self.column}"


# Keywords mapping
KEYWORDS = {
    # Definition keywords
    "DEFINE": TokenType.DEFINE,
    "AS": TokenType.AS,
    
    # Widget types
    "WIDGET": TokenType.WIDGET,
    "Text": TokenType.TEXT,
    "Image": TokenType.IMAGE,
    "ProgressBar": TokenType.PROGRESSBAR,
    "Line": TokenType.LINE,
    "Rectangle": TokenType.RECTANGLE,
    
    # Collections
    "CANVAS": TokenType.CANVAS,
    "STACK": TokenType.STACK,
    "SEQUENCE": TokenType.SEQUENCE,
    "INDEX": TokenType.INDEX,
    
    # Collection operations
    "PLACE": TokenType.PLACE,
    "APPEND": TokenType.APPEND,
    "AT": TokenType.AT,
    "Z": TokenType.Z,
    "WHEN": TokenType.WHEN,
    "ACTIVE": TokenType.ACTIVE,
    "DEFAULT": TokenType.DEFAULT,
    "GAP": TokenType.GAP,
    
    # Theme and styling
    "THEME": TokenType.THEME,
    "STYLE": TokenType.STYLE,
    
    # State and data
    "STATE": TokenType.STATE,
    "DATASOURCE": TokenType.DATASOURCE,
    "BIND": TokenType.BIND,
    "TO": TokenType.TO,
    
    # Application structure
    "APP": TokenType.APP,
    "REFERENCE": TokenType.REFERENCE,
    "SCREENS": TokenType.SCREENS,
    "DATASOURCES": TokenType.DATASOURCES,
    
    # Timeline
    "TIMELINE": TokenType.TIMELINE,
    
    # Display configuration
    "DISPLAY": TokenType.DISPLAY,
    "INTERFACE": TokenType.INTERFACE,
    "COLOR_MODE": TokenType.COLOR_MODE,
    "PINS": TokenType.PINS,
    
    # Resource management
    "RESOURCES": TokenType.RESOURCES,
    "PATH": TokenType.PATH,
    "FILE": TokenType.FILE,
    "SEARCH_PATH": TokenType.SEARCH_PATH,
    "ENV": TokenType.ENV,
    
    # Import
    "IMPORT": TokenType.IMPORT,
    "FROM": TokenType.FROM,
    
    # Macro
    "MACRO": TokenType.MACRO,
    
    # Boolean literals
    "true": TokenType.BOOLEAN,
    "false": TokenType.BOOLEAN,
} 