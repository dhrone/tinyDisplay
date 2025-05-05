"""
Parser for the tinyDisplay Application Widget DSL.

This module provides a recursive descent parser that converts a stream of tokens
into an Abstract Syntax Tree (AST).
"""
from typing import List, Dict, Optional, Union, Callable, Any, Tuple
import sys

from .tokens import Token, TokenType
from .ast import (
    Location, Expression, Literal, Variable, PropertyAccess, MacroReference,
    ObjectLiteral, ArrayLiteral, BinaryExpression, Statement, Program,
    ImportStatement, ResourcesBlock, DirDeclaration, FileDeclaration,
    SearchPathDeclaration, EnvBlock, EnvDeclaration, MacroDeclaration,
    DisplayDeclaration, WidgetDeclaration, TimelineBlock, CanvasDeclaration,
    PlacementStatement, StackDeclaration, AppendStatement, SequenceDeclaration,
    SequenceAppendStatement, IndexDeclaration, IndexAppendStatement,
    ThemeDeclaration, StyleDeclaration, StateDeclaration, DataSourceDeclaration,
    BindingStatement, AppDeclaration, ReferenceStatement
)

# Import the Marquee parser to use for TIMELINE blocks
from ..marquee.parser import Parser as MarqueeParser
from ..marquee.tokens import TokenType as MarqueeTokenType
from ..marquee.lexer import Lexer as MarqueeLexer


class ParseError(Exception):
    """Exception raised when a parsing error occurs."""
    pass


class Parser:
    """
    Parser for the tinyDisplay Application DSL.
    
    Converts a stream of tokens into an Abstract Syntax Tree (AST).
    """
    
    def __init__(self, tokens: List[Token]):
        """
        Initialize the parser with a list of tokens.
        
        Args:
            tokens: The tokens to parse.
        """
        self.tokens = tokens
        self.current = 0
        self.errors: List[str] = []
    
    def parse(self) -> Program:
        """
        Parse the tokens into an AST.
        
        Returns:
            The parsed AST.
        """
        statements = []
        
        try:
            while not self._is_at_end():
                statements.append(self._declaration())
        except ParseError as e:
            self.errors.append(str(e))
            # Synchronize to recover from error
            self._synchronize()
        
        return Program(statements)
    
    def _declaration(self) -> Statement:
        """Parse a declaration statement."""
        try:
            # Check for DEFINE keyword
            if self._match(TokenType.DEFINE):
                return self._define_statement()
            
            # Check for BIND statement
            if self._match(TokenType.BIND):
                return self._bind_statement()
            
            # Check for IMPORT statement
            if self._match(TokenType.IMPORT):
                return self._import_statement()
            
            # Default case - unsupported statement
            token = self._peek()
            self._error(token, f"Expected a declaration but got '{token.lexeme}'.")
        
        except ParseError as e:
            self.errors.append(str(e))
            self._synchronize()
        
        # Return a placeholder statement
        return Statement(Location(0, 0))
    
    def _define_statement(self) -> Statement:
        """Parse a DEFINE statement."""
        # Check what type of definition we have
        if self._match(TokenType.WIDGET):
            return self._widget_declaration()
        elif self._match(TokenType.CANVAS):
            return self._canvas_declaration()
        elif self._match(TokenType.STACK):
            return self._stack_declaration()
        elif self._match(TokenType.SEQUENCE):
            return self._sequence_declaration()
        elif self._match(TokenType.INDEX):
            return self._index_declaration()
        elif self._match(TokenType.THEME):
            return self._theme_declaration()
        elif self._match(TokenType.STYLE):
            return self._style_declaration()
        elif self._match(TokenType.STATE):
            return self._state_declaration()
        elif self._match(TokenType.DATASOURCE):
            return self._datasource_declaration()
        elif self._match(TokenType.APP):
            return self._app_declaration()
        elif self._match(TokenType.RESOURCES):
            return self._resources_block()
        elif self._match(TokenType.ENV):
            return self._env_block()
        elif self._match(TokenType.MACRO):
            return self._macro_declaration()
        elif self._match(TokenType.DISPLAY):
            return self._display_declaration()
        else:
            token = self._peek()
            self._error(token, f"Expected a definition type after DEFINE but got '{token.lexeme}'.")
            return Statement(Location(0, 0))
    
    def _widget_declaration(self) -> WidgetDeclaration:
        """Parse a widget declaration."""
        # DEFINE WIDGET "name" AS WidgetType { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected widget name in quotes.")
        name = name_token.literal
        
        self._consume(TokenType.AS, error_message="Expected 'AS' after widget name.")
        
        # Widget type
        type_token = self._consume(
            TokenType.TEXT, TokenType.IMAGE, TokenType.PROGRESSBAR, 
            TokenType.LINE, TokenType.RECTANGLE, TokenType.IDENTIFIER,
            error_message="Expected widget type."
        )
        widget_type = type_token.lexeme
        
        # Properties block
        properties = self._properties_block()
        
        # Check for timeline block
        timeline = None
        if self._check(TokenType.TIMELINE):
            timeline = self._timeline_block()
        
        location = Location(name_token.line, name_token.column)
        return WidgetDeclaration(name, widget_type, properties, timeline, location)
    
    def _timeline_block(self) -> TimelineBlock:
        """Parse a TIMELINE block with Marquee DSL."""
        timeline_token = self._consume(TokenType.TIMELINE, error_message="Expected TIMELINE.")
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after TIMELINE.")
        
        # Extract the content of the timeline block
        start_token = self.tokens[self.current]
        start_position = self.current
        brace_depth = 1
        
        while brace_depth > 0 and not self._is_at_end():
            if self._peek().type == TokenType.LEFT_BRACE:
                brace_depth += 1
            elif self._peek().type == TokenType.RIGHT_BRACE:
                brace_depth -= 1
            self._advance()
        
        if brace_depth > 0:
            self._error(self._peek(), "Unterminated TIMELINE block.")
        
        # Extract the Marquee DSL content
        marquee_tokens = self.tokens[start_position:self.current-1]
        
        # Convert to Marquee DSL tokens
        marquee_tokens_converted = self._convert_to_marquee_tokens(marquee_tokens)
        
        # Parse using Marquee parser
        marquee_parser = MarqueeParser(marquee_tokens_converted)
        marquee_ast = marquee_parser.parse()
        
        location = Location(timeline_token.line, timeline_token.column)
        return TimelineBlock(marquee_ast, location)
    
    def _convert_to_marquee_tokens(self, tokens: List[Token]) -> List[Any]:
        """Convert Application DSL tokens to Marquee DSL tokens."""
        # This is a placeholder. In a real implementation, this would convert between token types
        # For simplicity, we're assuming both token types are compatible enough to pass through
        return tokens
    
    def _canvas_declaration(self) -> CanvasDeclaration:
        """Parse a canvas declaration."""
        # DEFINE CANVAS "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected canvas name in quotes.")
        name = name_token.literal
        
        # Open the properties block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after canvas name.")
        
        properties: Dict[str, Expression] = {}
        placements: List[PlacementStatement] = []
        
        # Parse properties and PLACE statements
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.PLACE):
                placements.append(self._place_statement())
            else:
                prop, value = self._property()
                properties[prop] = value
        
        # Close the properties block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after canvas properties.")
        
        location = Location(name_token.line, name_token.column)
        return CanvasDeclaration(name, properties, placements, location)
    
    def _place_statement(self) -> PlacementStatement:
        """Parse a PLACE statement."""
        # PLACE "widget" AT (x, y) Z z;
        widget_token = self._consume(TokenType.STRING, error_message="Expected widget name in quotes.")
        widget_name = widget_token.literal
        
        self._consume(TokenType.AT, error_message="Expected 'AT' after widget name.")
        
        # Coordinates (x, y)
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' for coordinates.")
        x = self._expression()
        self._consume(TokenType.COMMA, error_message="Expected ',' after x coordinate.")
        y = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after coordinates.")
        
        # Optional Z-order
        z = None
        if self._match(TokenType.Z):
            z_token = self._consume(TokenType.INTEGER, TokenType.FLOAT, error_message="Expected numeric z-order after 'Z'.")
            z = Literal(z_token.literal, Location(z_token.line, z_token.column))
        
        # Optional justification
        justification = None
        if self._match(TokenType.STRING):
            justification = self._previous().literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after PLACE statement.")
        
        location = Location(widget_token.line, widget_token.column)
        return PlacementStatement(widget_name, x, y, z, justification, location)
    
    def _stack_declaration(self) -> StackDeclaration:
        """Parse a stack declaration."""
        # DEFINE STACK "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected stack name in quotes.")
        name = name_token.literal
        
        # Open the properties block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after stack name.")
        
        properties: Dict[str, Expression] = {}
        appends: List[AppendStatement] = []
        
        # Parse properties and APPEND statements
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.APPEND):
                appends.append(self._append_statement())
            else:
                prop, value = self._property()
                properties[prop] = value
        
        # Close the properties block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after stack properties.")
        
        location = Location(name_token.line, name_token.column)
        return StackDeclaration(name, properties, appends, location)
    
    def _append_statement(self) -> AppendStatement:
        """Parse an APPEND statement."""
        # APPEND "widget" [GAP n];
        widget_token = self._consume(TokenType.STRING, error_message="Expected widget name in quotes.")
        widget_name = widget_token.literal
        
        # Optional gap
        gap = None
        if self._match(TokenType.GAP):
            gap_token = self._consume(TokenType.INTEGER, TokenType.FLOAT, error_message="Expected numeric gap after 'GAP'.")
            gap = Literal(gap_token.literal, Location(gap_token.line, gap_token.column))
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after APPEND statement.")
        
        location = Location(widget_token.line, widget_token.column)
        return AppendStatement(widget_name, gap, location)
    
    def _sequence_declaration(self) -> SequenceDeclaration:
        """Parse a sequence declaration."""
        # DEFINE SEQUENCE "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected sequence name in quotes.")
        name = name_token.literal
        
        # Open the properties block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after sequence name.")
        
        properties: Dict[str, Expression] = {}
        appends: List[SequenceAppendStatement] = []
        
        # Parse properties and APPEND statements
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.APPEND):
                appends.append(self._sequence_append_statement())
            else:
                prop, value = self._property()
                properties[prop] = value
        
        # Close the properties block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after sequence properties.")
        
        location = Location(name_token.line, name_token.column)
        return SequenceDeclaration(name, properties, appends, location)
    
    def _sequence_append_statement(self) -> SequenceAppendStatement:
        """Parse a sequence APPEND statement."""
        # APPEND "widget" [ACTIVE WHEN condition];
        widget_token = self._consume(TokenType.STRING, error_message="Expected widget name in quotes.")
        widget_name = widget_token.literal
        
        # Optional condition
        condition = None
        if self._match(TokenType.ACTIVE):
            self._consume(TokenType.WHEN, error_message="Expected 'WHEN' after 'ACTIVE'.")
            condition = self._expression()
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after APPEND statement.")
        
        location = Location(widget_token.line, widget_token.column)
        return SequenceAppendStatement(widget_name, condition, location)
    
    def _index_declaration(self) -> IndexDeclaration:
        """Parse an index declaration."""
        # DEFINE INDEX "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected index name in quotes.")
        name = name_token.literal
        
        # Open the properties block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after index name.")
        
        properties: Dict[str, Expression] = {}
        appends: List[IndexAppendStatement] = []
        
        # Parse properties and APPEND statements
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.APPEND):
                appends.append(self._index_append_statement())
            else:
                prop, value = self._property()
                properties[prop] = value
        
        # Close the properties block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after index properties.")
        
        location = Location(name_token.line, name_token.column)
        return IndexDeclaration(name, properties, appends, location)
    
    def _index_append_statement(self) -> IndexAppendStatement:
        """Parse an index APPEND statement."""
        # APPEND "widget";
        widget_token = self._consume(TokenType.STRING, error_message="Expected widget name in quotes.")
        widget_name = widget_token.literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after APPEND statement.")
        
        location = Location(widget_token.line, widget_token.column)
        return IndexAppendStatement(widget_name, location)
    
    def _theme_declaration(self) -> ThemeDeclaration:
        """Parse a theme declaration."""
        # DEFINE THEME "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected theme name in quotes.")
        name = name_token.literal
        
        properties = self._properties_block()
        
        location = Location(name_token.line, name_token.column)
        return ThemeDeclaration(name, properties, location)
    
    def _style_declaration(self) -> StyleDeclaration:
        """Parse a style declaration."""
        # DEFINE STYLE "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected style name in quotes.")
        name = name_token.literal
        
        properties = self._properties_block()
        
        location = Location(name_token.line, name_token.column)
        return StyleDeclaration(name, properties, location)
    
    def _state_declaration(self) -> StateDeclaration:
        """Parse a state declaration."""
        # DEFINE STATE "name" AS type [DEFAULT value];
        name_token = self._consume(TokenType.STRING, error_message="Expected state name in quotes.")
        name = name_token.literal
        
        self._consume(TokenType.AS, error_message="Expected 'AS' after state name.")
        
        # State type
        type_token = self._consume(TokenType.IDENTIFIER, error_message="Expected state type.")
        state_type = type_token.literal
        
        # Optional default value
        default_value = None
        if self._match(TokenType.DEFAULT):
            value_token = self._advance()
            value_location = Location(value_token.line, value_token.column)
            
            if value_token.type in [TokenType.INTEGER, TokenType.FLOAT, TokenType.STRING, TokenType.BOOLEAN]:
                default_value = Literal(value_token.literal, value_location)
            else:
                self._error(value_token, "Expected literal value after DEFAULT.")
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after state declaration.")
        
        location = Location(name_token.line, name_token.column)
        return StateDeclaration(name, state_type, default_value, location)
    
    def _datasource_declaration(self) -> DataSourceDeclaration:
        """Parse a datasource declaration."""
        # DEFINE DATASOURCE "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected datasource name in quotes.")
        name = name_token.literal
        
        properties = self._properties_block()
        
        location = Location(name_token.line, name_token.column)
        return DataSourceDeclaration(name, properties, location)
    
    def _bind_statement(self) -> BindingStatement:
        """Parse a BIND statement."""
        # BIND "{variable}" TO "target.property";
        variable_token = self._consume(TokenType.STRING, error_message="Expected variable name in quotes or braces.")
        variable = variable_token.literal
        
        self._consume(TokenType.TO, error_message="Expected 'TO' after variable.")
        
        target_token = self._consume(TokenType.STRING, error_message="Expected target in quotes.")
        target = target_token.literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after binding.")
        
        location = Location(variable_token.line, variable_token.column)
        return BindingStatement(variable, target, location)
    
    def _app_declaration(self) -> AppDeclaration:
        """Parse an app declaration."""
        # DEFINE APP "name" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected app name in quotes.")
        name = name_token.literal
        
        # Open the app block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after app name.")
        
        properties: Dict[str, Expression] = {}
        screens: List[ReferenceStatement] = []
        datasources: List[ReferenceStatement] = []
        
        # Parse properties and blocks
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.SCREENS):
                screens = self._reference_block("SCREENS")
            elif self._match(TokenType.DATASOURCES):
                datasources = self._reference_block("DATASOURCES")
            else:
                prop, value = self._property()
                properties[prop] = value
        
        # Close the app block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after app properties.")
        
        location = Location(name_token.line, name_token.column)
        return AppDeclaration(name, properties, screens, datasources, location)
    
    def _reference_block(self, block_name: str) -> List[ReferenceStatement]:
        """Parse a block of references."""
        # SCREENS { REFERENCE "name"; ... }
        self._consume(TokenType.LEFT_BRACE, error_message=f"Expected '{{' after {block_name}.")
        
        references: List[ReferenceStatement] = []
        
        # Parse REFERENCE statements
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.REFERENCE):
                name_token = self._consume(TokenType.STRING, error_message="Expected reference name in quotes.")
                name = name_token.literal
                
                self._consume(TokenType.SEMICOLON, error_message="Expected ';' after reference.")
                
                location = Location(name_token.line, name_token.column)
                references.append(ReferenceStatement(name, location))
            else:
                token = self._peek()
                self._error(token, f"Expected REFERENCE in {block_name} block but got '{token.lexeme}'.")
                self._advance()
        
        # Close the block
        self._consume(TokenType.RIGHT_BRACE, error_message=f"Expected '}}' after {block_name} block.")
        
        return references
    
    def _resources_block(self) -> ResourcesBlock:
        """Parse a RESOURCES block."""
        # DEFINE RESOURCES { ... }
        token = self._previous()
        
        # Open the resources block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after RESOURCES.")
        
        declarations: List[Statement] = []
        
        # Parse resource declarations
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.FILE):
                declarations.append(self._file_declaration())
            elif self._match(TokenType.SEARCH_PATH):
                declarations.append(self._search_path_declaration())
            elif self._check(TokenType.IDENTIFIER):
                declarations.append(self._dir_declaration())
            else:
                token = self._peek()
                self._error(token, f"Expected resource declaration but got '{token.lexeme}'.")
                self._advance()
        
        # Close the resources block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after RESOURCES block.")
        
        location = Location(token.line, token.column)
        return ResourcesBlock(declarations, location)
    
    def _file_declaration(self) -> FileDeclaration:
        """Parse a FILE declaration."""
        # FILE name: "path";
        token = self._previous()
        
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected file name identifier.")
        name = name_token.literal
        
        self._consume(TokenType.COLON, error_message="Expected ':' after file name.")
        
        path_token = self._consume(TokenType.STRING, TokenType.PATH, error_message="Expected file path.")
        path = path_token.literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after file path.")
        
        location = Location(token.line, token.column)
        return FileDeclaration(name, path, location)
    
    def _dir_declaration(self) -> DirDeclaration:
        """Parse a directory declaration."""
        # fonts: "path/to/fonts/";
        type_token = self._consume(TokenType.IDENTIFIER, error_message="Expected directory type identifier.")
        path_type = type_token.literal
        
        self._consume(TokenType.COLON, error_message="Expected ':' after directory type.")
        
        path_token = self._consume(TokenType.STRING, TokenType.PATH, error_message="Expected directory path.")
        path = path_token.literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after directory path.")
        
        location = Location(type_token.line, type_token.column)
        return DirDeclaration(path_type, path, location)
    
    def _search_path_declaration(self) -> SearchPathDeclaration:
        """Parse a SEARCH_PATH declaration."""
        # SEARCH_PATH fonts: ["dir1/", "dir2/"];
        token = self._previous()
        
        type_token = self._consume(TokenType.IDENTIFIER, error_message="Expected path type identifier.")
        path_type = type_token.literal
        
        self._consume(TokenType.COLON, error_message="Expected ':' after path type.")
        
        # Parse array of paths
        self._consume(TokenType.LEFT_BRACKET, error_message="Expected '[' for path list.")
        
        paths: List[str] = []
        
        if not self._check(TokenType.RIGHT_BRACKET):
            # First path
            path_token = self._consume(TokenType.STRING, TokenType.PATH, error_message="Expected path string.")
            paths.append(path_token.literal)
            
            # Additional paths
            while self._match(TokenType.COMMA):
                path_token = self._consume(TokenType.STRING, TokenType.PATH, error_message="Expected path string after ','.")
                paths.append(path_token.literal)
        
        self._consume(TokenType.RIGHT_BRACKET, error_message="Expected ']' after path list.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after search path declaration.")
        
        location = Location(token.line, token.column)
        return SearchPathDeclaration(path_type, paths, location)
    
    def _env_block(self) -> EnvBlock:
        """Parse an ENV block."""
        # DEFINE ENV { ... }
        token = self._previous()
        
        # Open the env block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after ENV.")
        
        declarations: List[Statement] = []
        
        # Parse environment variable declarations
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._check(TokenType.IDENTIFIER):
                declarations.append(self._env_declaration())
            else:
                token = self._peek()
                self._error(token, f"Expected environment variable declaration but got '{token.lexeme}'.")
                self._advance()
        
        # Close the env block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after ENV block.")
        
        location = Location(token.line, token.column)
        return EnvBlock(declarations, location)
    
    def _env_declaration(self) -> EnvDeclaration:
        """Parse an environment variable declaration."""
        # APP_HOME: "/home/user/app";
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected environment variable name.")
        name = name_token.literal
        
        self._consume(TokenType.COLON, error_message="Expected ':' after variable name.")
        
        value_token = self._consume(TokenType.STRING, error_message="Expected string value for environment variable.")
        value = value_token.literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after variable value.")
        
        location = Location(name_token.line, name_token.column)
        return EnvDeclaration(name, value, location)
    
    def _macro_declaration(self) -> MacroDeclaration:
        """Parse a MACRO declaration."""
        # DEFINE MACRO SCREEN_WIDTH 128;
        # DEFINE MACRO CENTER_POS(width, height) { x: (SCREEN_WIDTH - width) / 2, y: 10 };
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected macro name.")
        name = name_token.literal
        
        # Check for parameters
        parameters: List[str] = []
        if self._match(TokenType.LEFT_PAREN):
            # Parse parameter list
            if not self._check(TokenType.RIGHT_PAREN):
                # First parameter
                param_token = self._consume(TokenType.IDENTIFIER, error_message="Expected parameter name.")
                parameters.append(param_token.literal)
                
                # Additional parameters
                while self._match(TokenType.COMMA):
                    param_token = self._consume(TokenType.IDENTIFIER, error_message="Expected parameter name after ','.")
                    parameters.append(param_token.literal)
            
            self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after parameter list.")
        
        # Parse macro value
        value = self._expression()
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after macro value.")
        
        location = Location(name_token.line, name_token.column)
        return MacroDeclaration(name, parameters, value, location)
    
    def _display_declaration(self) -> DisplayDeclaration:
        """Parse a DISPLAY declaration."""
        # DEFINE DISPLAY "main" { ... }
        name_token = self._consume(TokenType.STRING, error_message="Expected display name in quotes.")
        name = name_token.literal
        
        # Open the properties block
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after display name.")
        
        properties: Dict[str, Expression] = {}
        interface: Dict[str, Expression] = {}
        
        # Parse properties and INTERFACE block
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.INTERFACE):
                interface = self._interface_block()
            else:
                prop, value = self._property()
                properties[prop] = value
        
        # Close the properties block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after display properties.")
        
        location = Location(name_token.line, name_token.column)
        return DisplayDeclaration(name, properties, interface, location)
    
    def _interface_block(self) -> Dict[str, Expression]:
        """Parse an INTERFACE block."""
        # INTERFACE { ... }
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after INTERFACE.")
        
        properties: Dict[str, Expression] = {}
        
        # Parse properties
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            prop, value = self._property()
            properties[prop] = value
        
        # Close the interface block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after INTERFACE block.")
        
        return properties
    
    def _import_statement(self) -> ImportStatement:
        """Parse an IMPORT statement."""
        # IMPORT widget1, widget2 FROM "file.dsl";
        # IMPORT * FROM "file.dsl";
        token = self._previous()
        
        imports: List[str] = []
        
        # Parse import list
        if self._match(TokenType.STAR):
            imports.append("*")
        else:
            # First import
            name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected identifier name to import.")
            imports.append(name_token.literal)
            
            # Additional imports
            while self._match(TokenType.COMMA):
                name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected identifier name after ','.")
                imports.append(name_token.literal)
        
        self._consume(TokenType.FROM, error_message="Expected 'FROM' after import list.")
        
        source_token = self._consume(TokenType.STRING, TokenType.PATH, error_message="Expected source file path.")
        source = source_token.literal
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after import statement.")
        
        location = Location(token.line, token.column)
        return ImportStatement(imports, source, location)
    
    def _properties_block(self) -> Dict[str, Expression]:
        """Parse a properties block."""
        # { prop1: value1, prop2: value2 }
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' for properties block.")
        
        properties: Dict[str, Expression] = {}
        
        # Parse properties
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            prop, value = self._property()
            properties[prop] = value
        
        # Close the properties block
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after properties.")
        
        return properties
    
    def _property(self) -> Tuple[str, Expression]:
        """Parse a property declaration."""
        # name: value,
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected property name.")
        name = name_token.literal
        
        self._consume(TokenType.COLON, error_message="Expected ':' after property name.")
        
        value = self._expression()
        
        self._consume(TokenType.COMMA, error_message="Expected ',' after property value.")
        
        return name, value
    
    def _expression(self) -> Expression:
        """Parse an expression."""
        # Try to parse special expression types first
        if self._match(TokenType.LEFT_BRACE):
            return self._object_literal()
        elif self._match(TokenType.LEFT_BRACKET):
            return self._array_literal()
        elif self._match(TokenType.AT_SIGN):
            return self._macro_reference()
        
        # Parse a primary expression
        return self._primary()
    
    def _object_literal(self) -> ObjectLiteral:
        """Parse an object literal expression."""
        # { prop1: value1, prop2: value2 }
        token = self._previous()
        
        properties: Dict[str, Expression] = {}
        
        # Parse properties
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected property name.")
            name = name_token.literal
            
            self._consume(TokenType.COLON, error_message="Expected ':' after property name.")
            
            value = self._expression()
            
            properties[name] = value
            
            if not self._check(TokenType.RIGHT_BRACE):
                self._consume(TokenType.COMMA, error_message="Expected ',' after property value.")
        
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after object literal.")
        
        location = Location(token.line, token.column)
        return ObjectLiteral(properties, location)
    
    def _array_literal(self) -> ArrayLiteral:
        """Parse an array literal expression."""
        # [value1, value2, value3]
        token = self._previous()
        
        elements: List[Expression] = []
        
        # Parse elements
        if not self._check(TokenType.RIGHT_BRACKET):
            # First element
            elements.append(self._expression())
            
            # Additional elements
            while self._match(TokenType.COMMA):
                elements.append(self._expression())
        
        self._consume(TokenType.RIGHT_BRACKET, error_message="Expected ']' after array literal.")
        
        location = Location(token.line, token.column)
        return ArrayLiteral(elements, location)
    
    def _macro_reference(self) -> MacroReference:
        """Parse a macro reference."""
        # @SCREEN_WIDTH
        token = self._previous()
        
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected macro name after '@'.")
        name = name_token.literal
        
        # Check for dot access
        while self._match(TokenType.DOT):
            property_token = self._consume(TokenType.IDENTIFIER, error_message="Expected property name after '.'.")
            name += "." + property_token.literal
        
        location = Location(token.line, token.column)
        return MacroReference(name, location)
    
    def _primary(self) -> Expression:
        """Parse a primary expression."""
        token = self._peek()
        
        if self._match(TokenType.INTEGER, TokenType.FLOAT, TokenType.STRING, TokenType.BOOLEAN):
            location = Location(token.line, token.column)
            return Literal(token.literal, location)
        
        if self._match(TokenType.IDENTIFIER):
            name = token.literal
            location = Location(token.line, token.column)
            
            # Check for property access
            if self._match(TokenType.DOT):
                property_token = self._consume(TokenType.IDENTIFIER, error_message="Expected property name after '.'.")
                return PropertyAccess(name, property_token.literal, location)
            
            return Variable(name, location)
        
        # Parenthesized expression
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after expression.")
            return expr
        
        self._error(token, f"Expected expression but got '{token.lexeme}'.")
        return Expression(Location(0, 0))
    
    def _match(self, *types: TokenType) -> bool:
        """Check if the current token matches any of the given types and advance if it does."""
        for type in types:
            if self._check(type):
                self._advance()
                return True
        return False
    
    def _check(self, type: TokenType) -> bool:
        """Check if the current token is of the given type."""
        if self._is_at_end():
            return False
        return self._peek().type == type
    
    def _advance(self) -> Token:
        """Advance to the next token."""
        if not self._is_at_end():
            self.current += 1
        return self._previous()
    
    def _is_at_end(self) -> bool:
        """Check if we have reached the end of the token stream."""
        return self._peek().type == TokenType.EOF
    
    def _peek(self) -> Token:
        """Return the current token."""
        return self.tokens[self.current]
    
    def _previous(self) -> Token:
        """Return the previous token."""
        return self.tokens[self.current - 1]
    
    def _consume(self, *types: TokenType, error_message: str) -> Token:
        """Consume a token of the expected type, or raise an error."""
        for type in types:
            if self._check(type):
                return self._advance()
        
        token = self._peek()
        self._error(token, error_message)
        return token
    
    def _error(self, token: Token, message: str) -> None:
        """Raise a parse error."""
        if token.type == TokenType.EOF:
            error = f"Error at end of file: {message}"
        else:
            error = f"Error at line {token.line}:{token.column}, at '{token.lexeme}': {message}"
        
        self.errors.append(error)
        raise ParseError(error)
    
    def _synchronize(self) -> None:
        """
        Synchronize the parser state after an error.
        Skips tokens until reaching a likely statement boundary.
        """
        self._advance()
        
        while not self._is_at_end():
            # Stop at statement boundaries
            if self._previous().type == TokenType.SEMICOLON:
                return
            
            # Look for statement beginnings
            if self._peek().type in [
                TokenType.DEFINE,
                TokenType.WIDGET,
                TokenType.CANVAS,
                TokenType.STACK,
                TokenType.SEQUENCE,
                TokenType.INDEX,
                TokenType.THEME,
                TokenType.STYLE,
                TokenType.STATE,
                TokenType.DATASOURCE,
                TokenType.APP,
                TokenType.BIND,
                TokenType.IMPORT
            ]:
                return
            
            self._advance() 