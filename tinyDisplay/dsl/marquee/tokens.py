"""
Token definitions for the tinyDisplay Marquee Animation DSL.

This module defines the token types and constants used by the lexer.
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional, Union


class TokenType(Enum):
    """Enum representing all possible token types in the Marquee DSL."""
    # Special tokens
    EOF = auto()
    ERROR = auto()
    
    # Literals
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    IDENTIFIER = auto()
    
    # Keywords - Movement
    MOVE = auto()
    PAUSE = auto()
    RESET_POSITION = auto()
    
    # Keywords - Direction constants
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    
    # Keywords - Control flow
    LOOP = auto()
    END = auto()
    INFINITE = auto()
    IF = auto()
    ELSEIF = auto()
    ELSE = auto()
    BREAK = auto()
    CONTINUE = auto()
    AS = auto()
    
    # Keywords - Synchronization
    SYNC = auto()
    WAIT_FOR = auto()
    
    # Keywords - High-level commands
    SCROLL = auto()
    SLIDE = auto()
    POPUP = auto()
    
    # Keywords - Timeline optimization
    PERIOD = auto()
    START_AT = auto()
    SEGMENT = auto()
    POSITION_AT = auto()
    SCHEDULE_AT = auto()
    
    # Keywords - Variable handling
    ON_VARIABLE_CHANGE = auto()
    
    # Punctuation and operators
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    COMMA = auto()
    DOT = auto()
    SEMICOLON = auto()
    EQUALS = auto()
    ARROW = auto()  # => for POSITION_AT
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    
    # Comparison operators
    EQUAL_EQUAL = auto()
    NOT_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()


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
    # Movement commands
    "MOVE": TokenType.MOVE,
    "PAUSE": TokenType.PAUSE,
    "RESET_POSITION": TokenType.RESET_POSITION,
    
    # Direction constants
    "LEFT": TokenType.LEFT,
    "RIGHT": TokenType.RIGHT,
    "UP": TokenType.UP,
    "DOWN": TokenType.DOWN,
    
    # Control flow
    "LOOP": TokenType.LOOP,
    "END": TokenType.END,
    "INFINITE": TokenType.INFINITE,
    "IF": TokenType.IF,
    "ELSEIF": TokenType.ELSEIF,
    "ELSE": TokenType.ELSE,
    "BREAK": TokenType.BREAK,
    "CONTINUE": TokenType.CONTINUE,
    "AS": TokenType.AS,
    
    # Synchronization
    "SYNC": TokenType.SYNC,
    "WAIT_FOR": TokenType.WAIT_FOR,
    
    # High-level commands
    "SCROLL": TokenType.SCROLL,
    "SLIDE": TokenType.SLIDE,
    "POPUP": TokenType.POPUP,
    
    # Timeline optimization
    "PERIOD": TokenType.PERIOD,
    "START_AT": TokenType.START_AT,
    "SEGMENT": TokenType.SEGMENT,
    "POSITION_AT": TokenType.POSITION_AT,
    "SCHEDULE_AT": TokenType.SCHEDULE_AT,
    
    # Variable handling
    "ON_VARIABLE_CHANGE": TokenType.ON_VARIABLE_CHANGE,
} 