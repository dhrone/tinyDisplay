"""
Lexer for the tinyDisplay Application Widget DSL.

This module provides a lexer that tokenizes DSL source code into a stream of tokens.
"""
from typing import List, Optional
import re
from .tokens import Token, TokenType, KEYWORDS


class Lexer:
    """
    Lexer for the tinyDisplay Application DSL.
    
    Converts a string of DSL source code into a list of tokens.
    """
    
    def __init__(self, source: str):
        """
        Initialize the lexer with the source code.
        
        Args:
            source: The DSL source code to tokenize.
        """
        self.source = source
        self.tokens: List[Token] = []
        
        # Current position in the source
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        
        # Track start column for multi-character tokens
        self.start_column = 1
        
        # Path pattern for detecting file paths
        self.path_pattern = re.compile(r'^(\$[A-Za-z_][A-Za-z0-9_]*\/)?([A-Za-z0-9_\-\/\.]+)')

    def scan_tokens(self) -> List[Token]:
        """
        Scan all tokens in the source.
        
        Returns:
            A list of tokens representing the source.
        """
        while not self._is_at_end():
            # We are at the beginning of the next lexeme
            self.start = self.current
            self.start_column = self.column
            self._scan_token()
            
        # Add EOF token
        self.tokens.append(Token(
            TokenType.EOF, "", None, self.line, self.column
        ))
        return self.tokens
    
    def _scan_token(self) -> None:
        """Scan a single token."""
        c = self._advance()
        
        # Handle single-character tokens
        if c == '(':
            self._add_token(TokenType.LEFT_PAREN)
        elif c == ')':
            self._add_token(TokenType.RIGHT_PAREN)
        elif c == '{':
            self._add_token(TokenType.LEFT_BRACE)
        elif c == '}':
            self._add_token(TokenType.RIGHT_BRACE)
        elif c == '[':
            self._add_token(TokenType.LEFT_BRACKET)
        elif c == ']':
            self._add_token(TokenType.RIGHT_BRACKET)
        elif c == ',':
            self._add_token(TokenType.COMMA)
        elif c == '.':
            self._add_token(TokenType.DOT)
        elif c == ';':
            self._add_token(TokenType.SEMICOLON)
        elif c == ':':
            self._add_token(TokenType.COLON)
        elif c == '@':
            self._add_token(TokenType.AT_SIGN)
        elif c == '$':
            self._add_token(TokenType.DOLLAR_SIGN)
        elif c == '/':
            self._add_token(TokenType.SLASH)
        elif c == '+':
            self._add_token(TokenType.PLUS)
        elif c == '-':
            # Check if this is a negative number
            if self._is_digit(self._peek()):
                self._number_with_sign(negative=True)
            else:
                self._add_token(TokenType.MINUS)
        elif c == '*':
            # Check for comments
            if self._match('*'):
                self._multi_line_comment()
            else:
                self._add_token(TokenType.STAR)
        elif c == '=':
            self._add_token(TokenType.EQUALS)
        
        # Ignore whitespace
        elif c in [' ', '\r', '\t']:
            pass
        
        # Handle newlines
        elif c == '\n':
            self.line += 1
            self.column = 1
        
        # Handle comments
        elif c == '#':
            # Single-line comment
            while self._peek() != '\n' and not self._is_at_end():
                self._advance()
        
        # Handle literals and identifiers
        elif c == '"':
            self._string()
        elif self._is_digit(c):
            self._number()
        elif self._is_alpha(c):
            self._identifier()
        elif c == '{':
            self._variable_reference()
        else:
            # Try to parse a path
            if self._is_path_start(c):
                self._path()
            else:
                # Unrecognized character
                self._error(f"Unexpected character: '{c}'")
    
    def _multi_line_comment(self) -> None:
        """Handle multi-line comments /* ... */"""
        # Keep track of nesting level
        nesting = 1
        
        while nesting > 0 and not self._is_at_end():
            if self._peek() == '/' and self._peek_next() == '*':
                self._advance()  # /
                self._advance()  # *
                nesting += 1
            elif self._peek() == '*' and self._peek_next() == '/':
                self._advance()  # *
                self._advance()  # /
                nesting -= 1
            elif self._peek() == '\n':
                self._advance()
                self.line += 1
                self.column = 1
            else:
                self._advance()
    
    def _string(self) -> None:
        """Handle string literals."""
        # Scan until closing quote
        while self._peek() != '"' and not self._is_at_end():
            if self._peek() == '\n':
                self.line += 1
                self.column = 1
            elif self._peek() == '\\' and self._peek_next() == '"':
                self._advance()  # Consume the backslash
            self._advance()
        
        if self._is_at_end():
            self._error("Unterminated string.")
            return
        
        # Consume the closing "
        self._advance()
        
        # Trim the surrounding quotes
        value = self.source[self.start + 1:self.current - 1]
        # Handle escaped quotes
        value = value.replace('\\"', '"')
        self._add_token(TokenType.STRING, value)
    
    def _path(self) -> None:
        """Handle file path literals."""
        # Go back to the start of the path
        self.current = self.start
        
        # Try to match the path pattern
        match = self.path_pattern.match(self.source[self.current:])
        if match:
            # Consume the path
            path = match.group(0)
            for _ in range(len(path)):
                self._advance()
            
            self._add_token(TokenType.PATH_LITERAL, path)
        else:
            # Not a valid path, advance and report error
            self._advance()
            self._error("Invalid path format.")
    
    def _variable_reference(self) -> None:
        """Handle variable references enclosed in curly braces."""
        # Consume the opening {
        while self._peek() != '}' and not self._is_at_end():
            if self._peek() == '\n':
                self.line += 1
                self.column = 1
            self._advance()
        
        if self._is_at_end():
            self._error("Unterminated variable reference.")
            return
        
        # Consume the closing }
        self._advance()
        
        # Extract the variable name (without braces)
        var_name = self.source[self.start + 1:self.current - 1].strip()
        self._add_token(TokenType.STRING, var_name)  # We'll handle this as a special kind of string
    
    def _number(self) -> None:
        """Handle numeric literals."""
        # Consume all digits
        while self._is_digit(self._peek()):
            self._advance()
        
        # Look for a decimal point
        if self._peek() == '.' and self._is_digit(self._peek_next()):
            # Consume the decimal point
            self._advance()
            
            # Consume the fraction part
            while self._is_digit(self._peek()):
                self._advance()
            
            # Add float token
            value = float(self.source[self.start:self.current])
            self._add_token(TokenType.FLOAT, value)
        else:
            # Add integer token
            value = int(self.source[self.start:self.current])
            self._add_token(TokenType.INTEGER, value)
    
    def _identifier(self) -> None:
        """Handle identifiers and keywords."""
        # Consume all alphanumeric characters
        while self._is_alphanumeric(self._peek()):
            self._advance()
        
        # Check if identifier is a keyword
        text = self.source[self.start:self.current]
        
        # Handle boolean literals
        if text.lower() == "true":
            self._add_token(TokenType.BOOLEAN, True)
            return
        elif text.lower() == "false":
            self._add_token(TokenType.BOOLEAN, False)
            return
        
        # Check for other keywords
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        
        # For normal identifiers, the literal value is the identifier text
        literal = text if token_type == TokenType.IDENTIFIER else None
        self._add_token(token_type, literal)
    
    def _number_with_sign(self, negative: bool = False) -> None:
        """
        Handle numeric literals with an optional sign.
        
        Args:
            negative: Whether the number is negative.
        """
        # Consume all digits
        while self._is_digit(self._peek()):
            self._advance()
        
        # Look for a decimal point
        if self._peek() == '.' and self._is_digit(self._peek_next()):
            # Consume the decimal point
            self._advance()
            
            # Consume the fraction part
            while self._is_digit(self._peek()):
                self._advance()
            
            # Add float token
            value = float(self.source[self.start:self.current])
            if negative:
                value = -value
            self._add_token(TokenType.FLOAT, value)
        else:
            # Add integer token
            value = int(self.source[self.start+1:self.current])  # Skip the negative sign
            if negative:
                value = -value
            self._add_token(TokenType.INTEGER, value)
    
    def _advance(self) -> str:
        """
        Advance one character in the source.
        
        Returns:
            The current character before advancing.
        """
        c = self.source[self.current]
        self.current += 1
        self.column += 1
        return c
    
    def _match(self, expected: str) -> bool:
        """
        Check if the current character matches the expected one, and advance if it does.
        
        Args:
            expected: The character to match.
            
        Returns:
            True if the current character matches the expected one, False otherwise.
        """
        if self._is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        
        self.current += 1
        self.column += 1
        return True
    
    def _peek(self) -> str:
        """
        Return the current character without advancing.
        
        Returns:
            The current character, or an empty string if at the end of the source.
        """
        if self._is_at_end():
            return '\0'
        return self.source[self.current]
    
    def _peek_next(self) -> str:
        """
        Return the next character without advancing.
        
        Returns:
            The next character, or an empty string if at the end of the source.
        """
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]
    
    def _is_at_end(self) -> bool:
        """
        Check if we have reached the end of the source.
        
        Returns:
            True if we are at the end of the source, False otherwise.
        """
        return self.current >= len(self.source)
    
    def _is_digit(self, c: str) -> bool:
        """
        Check if a character is a digit.
        
        Args:
            c: The character to check.
            
        Returns:
            True if the character is a digit, False otherwise.
        """
        return c.isdigit()
    
    def _is_alpha(self, c: str) -> bool:
        """
        Check if a character is alphabetic or underscore.
        
        Args:
            c: The character to check.
            
        Returns:
            True if the character is alphabetic or underscore, False otherwise.
        """
        return c.isalpha() or c == '_'
    
    def _is_alphanumeric(self, c: str) -> bool:
        """
        Check if a character is alphanumeric or underscore.
        
        Args:
            c: The character to check.
            
        Returns:
            True if the character is alphanumeric or underscore, False otherwise.
        """
        return c.isalnum() or c == '_'
    
    def _is_path_start(self, c: str) -> bool:
        """
        Check if a character could be the start of a path.
        
        Args:
            c: The character to check.
            
        Returns:
            True if the character could start a path, False otherwise.
        """
        return c.isalpha() or c == '_' or c == '$' or c == '/' or c == '.'
    
    def _add_token(self, token_type: TokenType, literal: Optional[object] = None) -> None:
        """
        Add a token to the list of tokens.
        
        Args:
            token_type: The type of the token.
            literal: The literal value of the token, if applicable.
        """
        text = self.source[self.start:self.current]
        self.tokens.append(Token(
            token_type, text, literal, self.line, self.start_column
        ))
    
    def _error(self, message: str) -> None:
        """
        Handle a lexical error.
        
        Args:
            message: The error message.
        """
        self.tokens.append(Token(
            TokenType.ERROR, message, None, self.line, self.start_column
        )) 