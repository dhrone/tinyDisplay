"""
Parser for the tinyDisplay Marquee Animation DSL.

This module provides a recursive descent parser that converts a stream of tokens 
into an Abstract Syntax Tree (AST).
"""
from typing import List, Dict, Optional, Union, Callable, Any
import sys

from .tokens import Token, TokenType
from .ast import (
    Location, Expression, Literal, Variable, BinaryExpr, PropertyAccess,
    Statement, Block, MoveStatement, PauseStatement, ResetPositionStatement,
    LoopStatement, Condition, IfStatement, BreakStatement, ContinueStatement,
    SyncStatement, WaitForStatement, TimelineStatement, PeriodStatement,
    StartAtStatement, SegmentStatement, PositionAtStatement, ScheduleAtStatement,
    OnVariableChangeStatement, ScrollStatement, ScrollClipStatement, ScrollLoopStatement, 
    ScrollBounceStatement, SlideStatement, PopUpStatement,
    DefineStatement, SequenceInvocationStatement,
    Program, Direction, SlideAction, HighLevelCommandStatement
)


class ParseError(Exception):
    """Exception raised for parsing errors."""
    def __init__(self, token: Token, message: str):
        self.token = token
        self.message = message
        super().__init__(f"Parse error at {token.line}:{token.column}: {message}")


class Parser:
    """
    Recursive descent parser for the tinyDisplay DSL.
    
    Converts a list of tokens into an AST.
    """
    
    def __init__(self, tokens: List[Token]):
        """
        Initialize the parser with a list of tokens.
        
        Args:
            tokens: The tokens to parse.
        """
        self.tokens = tokens
        self.current = 0
        self.errors: List[ParseError] = []
    
    def parse(self) -> Program:
        """
        Parse the tokens into a Program.
        
        Returns:
            A Program representing the parsed tokens.
        
        Raises:
            ParseError: If the input is not valid according to the grammar.
        """
        statements: List[Statement] = []
        
        try:
            while not self._is_at_end():
                try:
                    statements.append(self._statement())
                except Exception as e:
                    print(f"Error while parsing statement: {e}")
                    self._synchronize()
            
            return Program(statements)
        except ParseError as e:
            print(f"Parse error: {e}")
            self.errors.append(e)
            self._synchronize()
            return Program(statements)
        except Exception as e:
            print(f"Unexpected error in parser: {e}")
            return Program(statements)
    
    def _statement(self) -> Statement:
        """Parse any statement."""
        
        current_token = self._peek()
        print(f"Parsing marquee statement starting with token: {current_token}")
        
        # Sequence invocation (an identifier followed by a left paren)
        if self._check(TokenType.IDENTIFIER) and self._check_next(TokenType.LEFT_PAREN):
            return self._sequence_invocation()
        
        # Movement statements
        if self._match(TokenType.MOVE):
            print("Matched MOVE token, calling _move_statement")
            return self._move_statement()
        if self._match(TokenType.PAUSE):
            return self._pause_statement()
        if self._match(TokenType.RESET_POSITION):
            return self._reset_statement()
        
        # Control flow statements
        if self._match(TokenType.LOOP):
            return self._loop_statement()
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.BREAK):
            return self._break_statement()
        if self._match(TokenType.CONTINUE):
            return self._continue_statement()
        
        # Synchronization statements
        if self._match(TokenType.SYNC):
            return self._sync_statement()
        if self._match(TokenType.WAIT_FOR):
            return self._wait_for_statement()
        
        # Timeline statements
        if self._match(TokenType.PERIOD):
            return self._period_statement()
        if self._match(TokenType.START_AT):
            return self._start_at_statement()
        if self._match(TokenType.SEGMENT):
            return self._segment_statement()
        if self._match(TokenType.POSITION_AT):
            return self._position_at_statement()
        if self._match(TokenType.SCHEDULE_AT):
            return self._schedule_at_statement()
        if self._match(TokenType.ON_VARIABLE_CHANGE):
            return self._on_variable_change_statement()
        
        # High-level commands
        if self._match(TokenType.SCROLL):
            return self._scroll_statement()
        if self._match(TokenType.SCROLL_CLIP):
            return self._scroll_clip_statement()
        if self._match(TokenType.SCROLL_LOOP):
            return self._scroll_loop_statement()
        if self._match(TokenType.SCROLL_BOUNCE):
            return self._scroll_bounce_statement()
        if self._match(TokenType.SLIDE):
            return self._slide_statement()
        if self._match(TokenType.POPUP):
            return self._popup_statement()
            
        # Sequence definition
        if self._match(TokenType.DEFINE):
            return self._define_statement()
        
        # Empty statement (semicolon)
        if self._match(TokenType.SEMICOLON):
            return self._empty_statement()
        
        # If no statement matched, report error
        token = self._peek()
        try:
            self._error(token, f"Expected statement, got {token.type.name}.")
        except ParseError as e:
            print(f"Error while parsing statement: {e}")
            self._synchronize()
            return None
    
    def _move_statement(self) -> MoveStatement:
        """Parse a MOVE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        # Parse the parameters
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after MOVE.")
        
        # Check for a direction constant
        direction = None
        if self._match(TokenType.LEFT, TokenType.RIGHT, TokenType.UP, TokenType.DOWN):
            direction_token = self._previous()
            if direction_token.type == TokenType.LEFT:
                direction = Direction.LEFT
            elif direction_token.type == TokenType.RIGHT:
                direction = Direction.RIGHT
            elif direction_token.type == TokenType.UP:
                direction = Direction.UP
            elif direction_token.type == TokenType.DOWN:
                direction = Direction.DOWN
            
            self._consume(TokenType.COMMA, error_message="Expected ',' after direction.")
            distance = self._expression()
            
            self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after parameters.")
            
            # Parse options if present
            options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
            
            self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
            
            return MoveStatement(
                location=location,
                direction=direction,
                distance=distance,
                options=options
            )
        
        # Parse as MOVE(startX, endX) or MOVE(startX, endX, startY, endY)
        start_x = self._expression()
        self._consume(TokenType.COMMA, error_message="Expected ',' after startX.")
        end_x = self._expression()
        
        start_y = None
        end_y = None
        
        # Check for startY and endY
        if self._match(TokenType.COMMA):
            start_y = self._expression()
            self._consume(TokenType.COMMA, error_message="Expected ',' after startY.")
            end_y = self._expression()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after parameters.")
        
        # Parse options if present
        options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return MoveStatement(
            location=location,
            start_x=start_x,
            end_x=end_x,
            start_y=start_y,
            end_y=end_y,
            options=options
        )
    
    def _pause_statement(self) -> PauseStatement:
        """Parse a PAUSE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after PAUSE.")
        duration = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after duration.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return PauseStatement(location=location, duration=duration)
    
    def _reset_statement(self) -> ResetPositionStatement:
        """Parse a RESET_POSITION statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after RESET_POSITION.")
        
        # Parse options if present
        options = {}
        if not self._check(TokenType.RIGHT_PAREN):
            options = self._options()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after options.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return ResetPositionStatement(location=location, options=options)
    
    def _loop_statement(self) -> LoopStatement:
        """Parse a LOOP statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after LOOP.")
        
        # Parse count or INFINITE
        count = None
        if self._match(TokenType.INFINITE):
            count = "INFINITE"
        else:
            count = self._expression()
        
        # Parse optional AS name
        name = None
        if self._match(TokenType.AS):
            name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected identifier after AS.")
            name = name_token.lexeme
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after count.")
        
        # Parse body
        body = self._block()
        
        self._consume(TokenType.END, error_message="Expected 'END' after loop body.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after END.")
        
        return LoopStatement(
            location=location,
            count=count,
            name=name,
            body=body
        )
    
    def _if_statement(self) -> IfStatement:
        """Parse an IF statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after IF.")
        condition = self._condition()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after condition.")
        
        then_branch = self._block()
        
        elseif_branches = []
        else_branch = None
        
        # Parse ELSEIF branches
        while self._match(TokenType.ELSEIF):
            self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after ELSEIF.")
            elseif_condition = self._condition()
            self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after condition.")
            
            elseif_branch = self._block()
            elseif_branches.append((elseif_condition, elseif_branch))
        
        # Parse optional ELSE branch
        if self._match(TokenType.ELSE):
            else_branch = self._block()
        
        self._consume(TokenType.END, error_message="Expected 'END' after if statement.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after END.")
        
        return IfStatement(
            location=location,
            condition=condition,
            then_branch=then_branch,
            elseif_branches=elseif_branches,
            else_branch=else_branch
        )
    
    def _break_statement(self) -> BreakStatement:
        """Parse a BREAK statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after BREAK.")
        
        return BreakStatement(location=location)
    
    def _continue_statement(self) -> ContinueStatement:
        """Parse a CONTINUE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after CONTINUE.")
        
        return ContinueStatement(location=location)
    
    def _sync_statement(self) -> SyncStatement:
        """Parse a SYNC statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SYNC.")
        event_token = self._consume(TokenType.IDENTIFIER, error_message="Expected event name after SYNC(.")
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after event name.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return SyncStatement(location=location, event=event_token.lexeme)
    
    def _wait_for_statement(self) -> WaitForStatement:
        """Parse a WAIT_FOR statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after WAIT_FOR.")
        event_token = self._consume(TokenType.IDENTIFIER, error_message="Expected event name after WAIT_FOR(.")
        self._consume(TokenType.COMMA, error_message="Expected ',' after event name.")
        ticks = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after ticks.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return WaitForStatement(location=location, event=event_token.lexeme, ticks=ticks)
    
    def _period_statement(self) -> PeriodStatement:
        """Parse a PERIOD statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after PERIOD.")
        ticks = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after ticks.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return PeriodStatement(location=location, ticks=ticks)
    
    def _start_at_statement(self) -> StartAtStatement:
        """Parse a START_AT statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after START_AT.")
        tick = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after tick.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return StartAtStatement(location=location, tick=tick)
    
    def _segment_statement(self) -> SegmentStatement:
        """Parse a SEGMENT statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SEGMENT.")
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected name after SEGMENT(.")
        self._consume(TokenType.COMMA, error_message="Expected ',' after name.")
        start_tick = self._expression()
        self._consume(TokenType.COMMA, error_message="Expected ',' after startTick.")
        end_tick = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after endTick.")
        
        body = self._block()
        
        self._consume(TokenType.END, error_message="Expected 'END' after segment body.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after END.")
        
        return SegmentStatement(
            location=location,
            name=name_token.lexeme,
            start_tick=start_tick,
            end_tick=end_tick,
            body=body
        )
    
    def _position_at_statement(self) -> PositionAtStatement:
        """Parse a POSITION_AT statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after POSITION_AT.")
        tick = self._expression()
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after tick.")
        self._consume(TokenType.ARROW, error_message="Expected '=>' after POSITION_AT(tick).")
        
        body = self._block()
        
        self._consume(TokenType.END, error_message="Expected 'END' after position_at body.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after END.")
        
        return PositionAtStatement(location=location, tick=tick, body=body)
    
    def _schedule_at_statement(self) -> ScheduleAtStatement:
        """Parse a SCHEDULE_AT statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SCHEDULE_AT.")
        tick = self._expression()
        self._consume(TokenType.COMMA, error_message="Expected ',' after tick.")
        action_token = self._consume(TokenType.IDENTIFIER, error_message="Expected action name after tick.")
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after action.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return ScheduleAtStatement(location=location, tick=tick, action=action_token.lexeme)
    
    def _on_variable_change_statement(self) -> OnVariableChangeStatement:
        """Parse an ON_VARIABLE_CHANGE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after ON_VARIABLE_CHANGE.")
        
        variables = []
        
        # Check if it's a list of variables [var1, var2, ...]
        if self._match(TokenType.LEFT_BRACKET):
            # Parse first variable
            var_token = self._consume(TokenType.IDENTIFIER, error_message="Expected variable name.")
            variables.append(var_token.lexeme)
            
            # Parse additional variables
            while self._match(TokenType.COMMA):
                var_token = self._consume(TokenType.IDENTIFIER, error_message="Expected variable name after ','.")
                variables.append(var_token.lexeme)
            
            self._consume(TokenType.RIGHT_BRACKET, error_message="Expected ']' after variable list.")
        else:
            # Single variable
            var_token = self._consume(TokenType.IDENTIFIER, error_message="Expected variable name.")
            variables.append(var_token.lexeme)
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after variables.")
        
        body = self._block()
        
        self._consume(TokenType.END, error_message="Expected 'END' after block.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after END.")
        
        return OnVariableChangeStatement(location=location, variables=variables, body=body)
    
    def _scroll_statement(self) -> ScrollStatement:
        """Parse a SCROLL statement (legacy version)."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SCROLL.")
        
        # Parse direction
        direction = None
        if self._match(TokenType.LEFT):
            direction = Direction.LEFT
        elif self._match(TokenType.RIGHT):
            direction = Direction.RIGHT
        elif self._match(TokenType.UP):
            direction = Direction.UP
        elif self._match(TokenType.DOWN):
            direction = Direction.DOWN
        else:
            self._error(self._peek(), "Expected direction (LEFT, RIGHT, UP, DOWN).")
        
        self._consume(TokenType.COMMA, error_message="Expected ',' after direction.")
        distance = self._expression()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after distance.")
        
        # Parse options if present
        options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return ScrollStatement(
            location=location,
            direction=direction,
            distance=distance,
            options=options
        )
    
    def _scroll_clip_statement(self) -> ScrollClipStatement:
        """Parse a SCROLL_CLIP statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SCROLL_CLIP.")
        
        # Parse direction
        direction = None
        if self._match(TokenType.LEFT):
            direction = Direction.LEFT
        elif self._match(TokenType.RIGHT):
            direction = Direction.RIGHT
        elif self._match(TokenType.UP):
            direction = Direction.UP
        elif self._match(TokenType.DOWN):
            direction = Direction.DOWN
        else:
            self._error(self._peek(), "Expected direction (LEFT, RIGHT, UP, DOWN).")
        
        self._consume(TokenType.COMMA, error_message="Expected ',' after direction.")
        distance = self._expression()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after distance.")
        
        # Parse options if present
        options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return ScrollClipStatement(
            location=location,
            direction=direction,
            distance=distance,
            options=options
        )
    
    def _scroll_loop_statement(self) -> ScrollLoopStatement:
        """Parse a SCROLL_LOOP statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SCROLL_LOOP.")
        
        # Parse direction
        direction = None
        if self._match(TokenType.LEFT):
            direction = Direction.LEFT
        elif self._match(TokenType.RIGHT):
            direction = Direction.RIGHT
        elif self._match(TokenType.UP):
            direction = Direction.UP
        elif self._match(TokenType.DOWN):
            direction = Direction.DOWN
        else:
            self._error(self._peek(), "Expected direction (LEFT, RIGHT, UP, DOWN).")
        
        self._consume(TokenType.COMMA, error_message="Expected ',' after direction.")
        distance = self._expression()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after distance.")
        
        # Parse options if present
        options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return ScrollLoopStatement(
            location=location,
            direction=direction,
            distance=distance,
            options=options
        )
    
    def _scroll_bounce_statement(self) -> ScrollBounceStatement:
        """Parse a SCROLL_BOUNCE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SCROLL_BOUNCE.")
        
        # Parse direction
        direction = None
        if self._match(TokenType.LEFT):
            direction = Direction.LEFT
        elif self._match(TokenType.RIGHT):
            direction = Direction.RIGHT
        elif self._match(TokenType.UP):
            direction = Direction.UP
        elif self._match(TokenType.DOWN):
            direction = Direction.DOWN
        else:
            self._error(self._peek(), "Expected direction (LEFT, RIGHT, UP, DOWN).")
        
        self._consume(TokenType.COMMA, error_message="Expected ',' after direction.")
        distance = self._expression()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after distance.")
        
        # Parse options if present
        options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return ScrollBounceStatement(
            location=location,
            direction=direction,
            distance=distance,
            options=options
        )
    
    def _slide_statement(self) -> SlideStatement:
        """Parse a SLIDE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after SLIDE.")
        
        # Parse direction
        direction = None
        if self._match(TokenType.LEFT):
            direction = Direction.LEFT
        elif self._match(TokenType.RIGHT):
            direction = Direction.RIGHT
        elif self._match(TokenType.UP):
            direction = Direction.UP
        elif self._match(TokenType.DOWN):
            direction = Direction.DOWN
        elif self._match(TokenType.TOP):
            direction = Direction.TOP
        elif self._match(TokenType.BOTTOM):
            direction = Direction.BOTTOM
        else:
            self._error(self._peek(), "Expected direction (LEFT, RIGHT, UP, DOWN, TOP, BOTTOM).")
        
        self._consume(TokenType.COMMA, error_message="Expected ',' after direction.")
        distance = self._expression()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after distance.")
        
        # Parse options if present
        options = self._options() if self._check(TokenType.LEFT_BRACE) else {}
        
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return SlideStatement(
            location=location,
            direction=direction,
            distance=distance,
            options=options
        )
    
    def _popup_statement(self) -> PopUpStatement:
        """Parse a POPUP statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after POPUP.")
        
        # Parse options if present
        options = {}
        if not self._check(TokenType.RIGHT_PAREN):
            options = self._options()
        
        self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after options.")
        self._consume(TokenType.SEMICOLON, error_message="Expected ';' after statement.")
        
        return PopUpStatement(location=location, options=options)
    
    def _empty_statement(self) -> Statement:
        """Parse an empty statement (;)."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        return Block(location=location, statements=[])
    
    def _block(self) -> Block:
        """Parse a block of statements."""
        token = self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' to start block.")
        location = Location(token.line, token.column)
        
        statements = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            statements.append(self._statement())
        
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' to end block.")
        
        return Block(location=location, statements=statements)
    
    def _options(self) -> Dict[str, Expression]:
        """Parse options in curly braces."""
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' to start options.")
        
        options = {}
        
        # Parse option pairs
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            # Parse option name
            name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected option name.")
            
            self._consume(TokenType.EQUALS, error_message="Expected '=' after option name.")
            
            # Parse option value
            value = self._expression()
            
            options[name_token.lexeme] = value
            
            # Parse comma or end of options
            if not self._check(TokenType.RIGHT_BRACE):
                self._consume(TokenType.COMMA, error_message="Expected ',' after option.")
        
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' to end options.")
        
        return options
    
    def _condition(self) -> Condition:
        """Parse a condition."""
        left = self._expression()
        
        # Get operator
        operator_token = self._consume(
            TokenType.EQUAL_EQUAL,
            TokenType.NOT_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            error_message="Expected comparison operator."
        )
        operator = operator_token.lexeme
        
        right = self._expression()
        
        location = Location(operator_token.line, operator_token.column)
        
        return Condition(left=left, operator=operator, right=right, location=location)
    
    def _expression(self) -> Expression:
        """Parse an expression."""
        return self._addition()
    
    def _addition(self) -> Expression:
        """Parse addition and subtraction."""
        expr = self._multiplication()
        
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous().lexeme
            right = self._multiplication()
            location = Location(self._previous().line, self._previous().column)
            expr = BinaryExpr(left=expr, operator=operator, right=right, location=location)
        
        return expr
    
    def _multiplication(self) -> Expression:
        """Parse multiplication and division."""
        expr = self._unary()
        
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            operator = self._previous().lexeme
            right = self._unary()
            location = Location(self._previous().line, self._previous().column)
            expr = BinaryExpr(left=expr, operator=operator, right=right, location=location)
        
        return expr
    
    def _unary(self) -> Expression:
        """Parse unary operations like negation."""
        if self._match(TokenType.MINUS):
            token = self._previous()
            location = Location(token.line, token.column)
            
            # Special case: if the next token is a literal number, create a negative literal
            if self._check(TokenType.INTEGER):
                number_token = self._advance()
                value = -number_token.literal  # Negate the value
                return Literal(value=value, location=location)
            elif self._check(TokenType.FLOAT):
                number_token = self._advance()
                value = -number_token.literal  # Negate the value
                return Literal(value=value, location=location)
            
            # Otherwise, create a unary expression: 0 - expr
            expr = self._primary()
            zero = Literal(value=0, location=location)
            return BinaryExpr(left=zero, operator="-", right=expr, location=location)
        
        return self._primary()
    
    def _primary(self) -> Expression:
        """Parse primary expressions."""
        token = self._peek()
        location = Location(token.line, token.column)
        
        # Literals
        if self._match(TokenType.INTEGER, TokenType.FLOAT):
            return Literal(value=self._previous().literal, location=location)
        
        if self._match(TokenType.STRING):
            return Literal(value=self._previous().literal, location=location)
        
        # Identifiers and property access
        if self._match(TokenType.IDENTIFIER):
            identifier = self._previous().lexeme
            
            # Check for property access
            if self._match(TokenType.DOT):
                property_token = self._consume(TokenType.IDENTIFIER, error_message="Expected property name after '.'.")
                return PropertyAccess(
                    object=Variable(name=identifier, location=location),
                    property=property_token.lexeme,
                    location=location
                )
            
            return Variable(name=identifier, location=location)
        
        # Parenthesized expressions
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after expression.")
            return expr
        
        # Error for unexpected tokens
        self._error(token, f"Expected expression, got {token.type.name}.")
    
    def _consume(self, *types, error_message):
        """
        Consume a token of the expected type, or raise an error.
        
        Args:
            types: The expected token types.
            error_message: The error message to display if the token doesn't match.
            
        Returns:
            The consumed token.
            
        Raises:
            ParseError: If the token doesn't match the expected type.
        """
        for type in types:
            if self._check(type):
                return self._advance()
        
        token = self._peek()
        self._error(token, error_message)
    
    def _match(self, *types) -> bool:
        """
        Check if the current token matches any of the expected types, and advance if it does.
        
        Args:
            types: The expected token types.
            
        Returns:
            True if the token matches, False otherwise.
        """
        for type in types:
            if self._check(type):
                self._advance()
                return True
        
        return False
    
    def _check(self, type) -> bool:
        """
        Check if the current token is of the given type.
        
        Args:
            type: The token type to check.
            
        Returns:
            True if the current token has the given type, False otherwise.
        """
        if self._is_at_end():
            return False
        return self._peek().type == type
    
    def _check_next(self, type) -> bool:
        """
        Check if the token after the current one is of the given type.
        
        Args:
            type: The token type to check.
            
        Returns:
            True if the token after the current one has the given type, False otherwise.
        """
        if self._is_at_end() or self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].type == type
    
    def _advance(self) -> Token:
        """
        Advance to the next token.
        
        Returns:
            The token that was just consumed.
        """
        if not self._is_at_end():
            self.current += 1
        return self._previous()
    
    def _is_at_end(self) -> bool:
        """
        Check if we have reached the end of the token stream.
        
        Returns:
            True if we are at the end of the token stream, False otherwise.
        """
        return self._peek().type == TokenType.EOF
    
    def _peek(self) -> Token:
        """
        Return the current token without advancing.
        
        Returns:
            The current token.
        """
        return self.tokens[self.current]
    
    def _previous(self) -> Token:
        """
        Return the previous token.
        
        Returns:
            The previous token.
        """
        return self.tokens[self.current - 1]
    
    def _error(self, token, message):
        """
        Report a parsing error.
        
        Args:
            token: The token where the error occurred.
            message: The error message.
            
        Returns:
            A ParseError.
            
        Raises:
            ParseError: Always raises this exception.
        """
        error = ParseError(token, message)
        self.errors.append(error)
        print(f"Parse error at {token.line}:{token.column}: {message} Token: {token}")
        # Print context of surrounding tokens (up to 3 before and after if available)
        idx = self.current
        start_idx = max(0, idx - 3)
        end_idx = min(len(self.tokens), idx + 3)
        context_tokens = self.tokens[start_idx:end_idx]
        print("Context tokens:")
        for i, ctx_token in enumerate(context_tokens):
            marker = "  "
            if start_idx + i == idx:
                marker = "->"
            print(f"{marker} {ctx_token}")
        raise error
    
    def _synchronize(self):
        """
        Skip tokens until the start of the next statement.
        Used for error recovery.
        """
        self._advance()
        
        while not self._is_at_end():
            if self._previous().type == TokenType.SEMICOLON:
                return
            
            token_type = self._peek().type
            if token_type in {
                TokenType.MOVE,
                TokenType.PAUSE,
                TokenType.RESET_POSITION,
                TokenType.LOOP,
                TokenType.IF,
                TokenType.BREAK,
                TokenType.CONTINUE,
                TokenType.SYNC,
                TokenType.WAIT_FOR,
                TokenType.PERIOD,
                TokenType.START_AT,
                TokenType.SEGMENT,
                TokenType.POSITION_AT,
                TokenType.SCHEDULE_AT,
                TokenType.ON_VARIABLE_CHANGE,
                TokenType.SCROLL,
                TokenType.SCROLL_CLIP,
                TokenType.SCROLL_LOOP,
                TokenType.SCROLL_BOUNCE,
                TokenType.SLIDE,
                TokenType.POPUP
            }:
                return
            
            self._advance() 
    
    def _define_statement(self) -> DefineStatement:
        """Parse a DEFINE statement."""
        token = self._previous()
        location = Location(token.line, token.column)
        
        # Parse the name
        name_token = self._consume(TokenType.IDENTIFIER, error_message="Expected sequence name after DEFINE.")
        name = name_token.lexeme
        print(f"Parsing DEFINE statement for sequence '{name}'")
        
        # Parse the body
        self._consume(TokenType.LEFT_BRACE, error_message="Expected '{' after sequence name.")
        statements: List[Statement] = []
        
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            stmt = self._statement()
            if stmt is not None:
                statements.append(stmt)
        
        print(f"Found {len(statements)} statements in DEFINE block for '{name}'")
        
        self._consume(TokenType.RIGHT_BRACE, error_message="Expected '}' after sequence body.")
        print(f"Found closing brace for DEFINE block '{name}'")
        
        try:
            self._consume(TokenType.SEMICOLON, error_message="Expected ';' after sequence definition.")
            print(f"Found semicolon after DEFINE block '{name}'")
        except ParseError as e:
            print(f"Error consuming semicolon: {e}")
            # Try to recover - maybe there is no semicolon after the DEFINE block?
        
        return DefineStatement(
            location=location,
            name=name,
            body=Block(location=location, statements=statements)
        )
    
    def _sequence_invocation(self) -> SequenceInvocationStatement:
        """Parse a sequence invocation."""
        name_token = self._advance()  # Consume the identifier token
        location = Location(name_token.line, name_token.column)
        name = name_token.lexeme
        print(f"Parsing sequence invocation for '{name}'")
        
        try:
            self._consume(TokenType.LEFT_PAREN, error_message="Expected '(' after sequence name.")
            
            # Parse optional arguments
            arguments = []
            if not self._check(TokenType.RIGHT_PAREN):
                arguments.append(self._expression())
                
                while self._match(TokenType.COMMA):
                    arguments.append(self._expression())
            
            self._consume(TokenType.RIGHT_PAREN, error_message="Expected ')' after arguments.")
            self._consume(TokenType.SEMICOLON, error_message="Expected ';' after sequence invocation.")
            
            print(f"Successfully parsed sequence invocation for '{name}' with {len(arguments)} arguments")
            
            return SequenceInvocationStatement(
                location=location,
                name=name,
                arguments=arguments
            )
        except ParseError as e:
            print(f"Error parsing sequence invocation: {e}")
            self._synchronize()
            
            # Return a placeholder statement to avoid null reference exceptions
            return SequenceInvocationStatement(
                location=location,
                name=name,
                arguments=[]
            ) 