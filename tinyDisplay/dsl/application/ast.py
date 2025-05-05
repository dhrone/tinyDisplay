"""
Abstract Syntax Tree (AST) for the tinyDisplay Application Widget DSL.

This module defines the node classes that make up the AST for the DSL.
Each class represents a different construct in the language.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Union, Any


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
    """A literal value (number, string, boolean, etc.)."""
    value: Union[int, float, str, bool]


@dataclass
class Variable(Expression):
    """A variable reference."""
    name: str


@dataclass
class PropertyAccess(Expression):
    """A property access expression (e.g., THEME.accent)."""
    object: Union[str, Expression]
    property: str


@dataclass
class MacroReference(Expression):
    """A reference to a macro (e.g., @SCREEN_WIDTH)."""
    name: str


@dataclass
class ObjectLiteral(Expression):
    """An object literal (e.g., { x: 10, y: 20 })."""
    properties: Dict[str, Expression]


@dataclass
class ArrayLiteral(Expression):
    """An array literal (e.g., [1, 2, 3])."""
    elements: List[Expression]


@dataclass
class BinaryExpression(Expression):
    """A binary expression (e.g., a + b)."""
    left: Expression
    operator: str
    right: Expression


@dataclass
class Statement:
    """Base class for all statements."""
    location: Location


@dataclass
class Program:
    """The root of the AST, representing a complete program."""
    statements: List[Statement]
    
    @property
    def is_empty(self) -> bool:
        """Check if the program is empty."""
        return len(self.statements) == 0


# Definition statements

@dataclass
class ImportStatement(Statement):
    """
    An IMPORT statement.
    
    Example:
    IMPORT widget1, widget2 FROM "file.dsl";
    IMPORT * FROM "file.dsl";
    """
    imports: List[str]  # '*' for import all
    source: str
    

@dataclass
class ResourcesBlock(Statement):
    """
    A RESOURCES block.
    
    Example:
    DEFINE RESOURCES {
        fonts: "path/to/fonts/";
        FILE logo: "images/logo.png";
        SEARCH_PATH images: ["dir1/", "dir2/"];
    }
    """
    declarations: List[Statement]  # DirDecl, FileDecl, or SearchPathDecl


@dataclass
class DirDeclaration(Statement):
    """
    A directory path declaration.
    
    Example:
    fonts: "path/to/fonts/";
    """
    path_type: str  # "fonts", "images", etc.
    path: str


@dataclass
class FileDeclaration(Statement):
    """
    A file declaration.
    
    Example:
    FILE logo: "images/logo.png";
    """
    name: str
    path: str


@dataclass
class SearchPathDeclaration(Statement):
    """
    A search path declaration.
    
    Example:
    SEARCH_PATH fonts: ["dir1/", "dir2/"];
    """
    path_type: str
    paths: List[str]


@dataclass
class EnvBlock(Statement):
    """
    An ENV block.
    
    Example:
    DEFINE ENV {
        APP_HOME: "/home/user/app";
    }
    """
    declarations: List[Statement]  # EnvDeclaration


@dataclass
class EnvDeclaration(Statement):
    """
    An environment variable declaration.
    
    Example:
    APP_HOME: "/home/user/app";
    """
    name: str
    value: str


@dataclass
class MacroDeclaration(Statement):
    """
    A MACRO declaration.
    
    Example:
    DEFINE MACRO SCREEN_WIDTH 128;
    DEFINE MACRO CENTER_POS(width, height) { x: (SCREEN_WIDTH - width) / 2, y: 10 };
    """
    name: str
    parameters: List[str]  # Empty for simple macros
    value: Expression
    

@dataclass
class DisplayDeclaration(Statement):
    """
    A DISPLAY declaration.
    
    Example:
    DEFINE DISPLAY "main" {
        width: 128,
        height: 64,
        color_mode: "1",
        
        INTERFACE {
            type: "spi",
            bus: 0,
            device: 0
        }
    }
    """
    name: str
    properties: Dict[str, Expression]
    interface: Optional[Dict[str, Expression]] = None


@dataclass
class WidgetDeclaration(Statement):
    """
    A WIDGET declaration.
    
    Example:
    DEFINE WIDGET "title" AS Text {
        value: "Hello World",
        size: (128, 16),
        foreground: "white",
        background: "black"
    }
    """
    name: str
    type: str
    properties: Dict[str, Expression]
    timeline: Optional["TimelineBlock"] = None


@dataclass
class TimelineBlock(Statement):
    """
    A TIMELINE block containing Marquee Animation DSL.
    
    Example:
    TIMELINE {
        MOVE(LEFT, 100) { step=1, interval=2 };
        PAUSE(10);
    }
    """
    marquee_ast: Any  # This will hold the Marquee DSL AST


@dataclass
class CanvasDeclaration(Statement):
    """
    A CANVAS declaration.
    
    Example:
    DEFINE CANVAS "main" {
        size: (128, 64),
        background: "black",
        
        PLACE "title" AT (10, 10) Z 100;
        PLACE "status" AT (10, 30) Z 100;
    }
    """
    name: str
    properties: Dict[str, Expression]
    placements: List["PlacementStatement"] = field(default_factory=list)


@dataclass
class PlacementStatement(Statement):
    """
    A PLACE statement.
    
    Example:
    PLACE "title" AT (10, 10) Z 100;
    """
    widget_name: str
    x: Expression
    y: Expression
    z: Optional[Expression] = None
    justification: Optional[str] = None


@dataclass
class StackDeclaration(Statement):
    """
    A STACK declaration.
    
    Example:
    DEFINE STACK "header" {
        orientation: "horizontal",
        gap: 2,
        
        APPEND "logo";
        APPEND "title" GAP 5;
    }
    """
    name: str
    properties: Dict[str, Expression]
    appends: List["AppendStatement"] = field(default_factory=list)


@dataclass
class AppendStatement(Statement):
    """
    An APPEND statement.
    
    Example:
    APPEND "logo";
    APPEND "title" GAP 5;
    """
    widget_name: str
    gap: Optional[Expression] = None


@dataclass
class SequenceDeclaration(Statement):
    """
    A SEQUENCE declaration.
    
    Example:
    DEFINE SEQUENCE "screens" {
        defaultCanvas: "welcome",
        
        APPEND "home" ACTIVE WHEN "{page == 'home'}";
        APPEND "settings" ACTIVE WHEN "{page == 'settings'}";
    }
    """
    name: str
    properties: Dict[str, Expression]
    appends: List["SequenceAppendStatement"] = field(default_factory=list)


@dataclass
class SequenceAppendStatement(Statement):
    """
    A sequence APPEND statement with optional ACTIVE WHEN condition.
    
    Example:
    APPEND "home" ACTIVE WHEN "{page == 'home'}";
    """
    widget_name: str
    condition: Optional[Expression] = None


@dataclass
class IndexDeclaration(Statement):
    """
    An INDEX declaration.
    
    Example:
    DEFINE INDEX "volumeLevel" {
        value: "{volume}",
        
        APPEND "muted";
        APPEND "low";
        APPEND "medium";
        APPEND "high";
    }
    """
    name: str
    properties: Dict[str, Expression]
    appends: List["IndexAppendStatement"] = field(default_factory=list)


@dataclass
class IndexAppendStatement(Statement):
    """
    An index APPEND statement.
    
    Example:
    APPEND "muted";
    """
    widget_name: str


@dataclass
class ThemeDeclaration(Statement):
    """
    A THEME declaration.
    
    Example:
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue"
    }
    """
    name: str
    properties: Dict[str, Expression]


@dataclass
class StyleDeclaration(Statement):
    """
    A STYLE declaration.
    
    Example:
    DEFINE STYLE "heading" {
        foreground: THEME.accent,
        font: "roboto.fnt",
        size: (0, 16)
    }
    """
    name: str
    properties: Dict[str, Expression]


@dataclass
class StateDeclaration(Statement):
    """
    A STATE declaration.
    
    Example:
    DEFINE STATE "currentPage" AS STRING DEFAULT "home";
    """
    name: str
    type: str  # "BOOL", "NUMBER", "STRING", "OBJECT"
    default_value: Optional[Expression] = None


@dataclass
class DataSourceDeclaration(Statement):
    """
    A DATASOURCE declaration.
    
    Example:
    DEFINE DATASOURCE "weather" {
        type: "http",
        url: "https://api.example.com/weather",
        refresh: 300,
        mapping: {
            "temperature": "$.current.temp_c",
            "humidity": "$.current.humidity"
        }
    }
    """
    name: str
    properties: Dict[str, Expression]


@dataclass
class BindingStatement(Statement):
    """
    A BIND statement.
    
    Example:
    BIND "{temperature}" TO "weather.temperature";
    """
    variable: str
    target: str


@dataclass
class AppDeclaration(Statement):
    """
    An APP declaration.
    
    Example:
    DEFINE APP "weatherStation" {
        theme: "dark",
        defaultScreen: "home",
        
        SCREENS {
            REFERENCE "home";
            REFERENCE "settings";
        }
        
        DATASOURCES {
            REFERENCE "weather";
            REFERENCE "system";
        }
    }
    """
    name: str
    properties: Dict[str, Expression]
    screens: List["ReferenceStatement"] = field(default_factory=list)
    datasources: List["ReferenceStatement"] = field(default_factory=list)


@dataclass
class ReferenceStatement(Statement):
    """
    A REFERENCE statement.
    
    Example:
    REFERENCE "home";
    """
    target_name: str 