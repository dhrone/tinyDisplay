"""
Validator for the tinyDisplay Application Widget DSL.

This module provides a validator that checks the AST for semantic errors before execution.
"""
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass

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

# Import the Marquee validator to use for TIMELINE blocks
from ..marquee.validator import Validator as MarqueeValidator


@dataclass
class ValidationError:
    """A validation error with a location and message."""
    location: Location
    message: str
    
    def __str__(self) -> str:
        """String representation of the validation error."""
        return f"Error at {self.location}: {self.message}"


class Validator:
    """
    Validator for the tinyDisplay Application DSL.
    
    Checks the AST for semantic errors before execution.
    """
    
    def __init__(self, program: Program):
        """
        Initialize the validator with an AST.
        
        Args:
            program: The AST to validate.
        """
        self.program = program
        self.errors: List[ValidationError] = []
        
        # Symbol tables for different declaration types
        self.widgets: Dict[str, WidgetDeclaration] = {}
        self.canvases: Dict[str, CanvasDeclaration] = {}
        self.stacks: Dict[str, StackDeclaration] = {}
        self.sequences: Dict[str, SequenceDeclaration] = {}
        self.indexes: Dict[str, IndexDeclaration] = {}
        self.themes: Dict[str, ThemeDeclaration] = {}
        self.styles: Dict[str, StyleDeclaration] = {}
        self.states: Dict[str, StateDeclaration] = {}
        self.datasources: Dict[str, DataSourceDeclaration] = {}
        self.apps: Dict[str, AppDeclaration] = {}
        self.displays: Dict[str, DisplayDeclaration] = {}
        self.macros: Dict[str, MacroDeclaration] = {}
        
        # Resources and environment variables
        self.resources: Dict[str, str] = {}  # resource_name -> path
        self.env_vars: Dict[str, str] = {}   # var_name -> value
        
        # Reference tracking
        self.referenced_widgets: Set[str] = set()
    
    def validate(self) -> List[ValidationError]:
        """
        Validate the AST and return any errors.
        
        Returns:
            A list of validation errors.
        """
        # First pass: build symbol tables
        for stmt in self.program.statements:
            self._register_declaration(stmt)
        
        # Second pass: validate references and semantics
        for stmt in self.program.statements:
            self._validate_statement(stmt)
        
        # Check for unreferenced widgets
        self._check_unreferenced_widgets()
        
        return self.errors
    
    def _register_declaration(self, stmt: Statement) -> None:
        """
        Register a declaration in the appropriate symbol table.
        
        Args:
            stmt: The statement to register.
        """
        if isinstance(stmt, WidgetDeclaration):
            if stmt.name in self.widgets:
                self._error(stmt.location, f"Widget '{stmt.name}' is already defined.")
            else:
                self.widgets[stmt.name] = stmt
        
        elif isinstance(stmt, CanvasDeclaration):
            if stmt.name in self.canvases:
                self._error(stmt.location, f"Canvas '{stmt.name}' is already defined.")
            else:
                self.canvases[stmt.name] = stmt
        
        elif isinstance(stmt, StackDeclaration):
            if stmt.name in self.stacks:
                self._error(stmt.location, f"Stack '{stmt.name}' is already defined.")
            else:
                self.stacks[stmt.name] = stmt
        
        elif isinstance(stmt, SequenceDeclaration):
            if stmt.name in self.sequences:
                self._error(stmt.location, f"Sequence '{stmt.name}' is already defined.")
            else:
                self.sequences[stmt.name] = stmt
        
        elif isinstance(stmt, IndexDeclaration):
            if stmt.name in self.indexes:
                self._error(stmt.location, f"Index '{stmt.name}' is already defined.")
            else:
                self.indexes[stmt.name] = stmt
        
        elif isinstance(stmt, ThemeDeclaration):
            if stmt.name in self.themes:
                self._error(stmt.location, f"Theme '{stmt.name}' is already defined.")
            else:
                self.themes[stmt.name] = stmt
        
        elif isinstance(stmt, StyleDeclaration):
            if stmt.name in self.styles:
                self._error(stmt.location, f"Style '{stmt.name}' is already defined.")
            else:
                self.styles[stmt.name] = stmt
        
        elif isinstance(stmt, StateDeclaration):
            if stmt.name in self.states:
                self._error(stmt.location, f"State '{stmt.name}' is already defined.")
            else:
                self.states[stmt.name] = stmt
        
        elif isinstance(stmt, DataSourceDeclaration):
            if stmt.name in self.datasources:
                self._error(stmt.location, f"DataSource '{stmt.name}' is already defined.")
            else:
                self.datasources[stmt.name] = stmt
        
        elif isinstance(stmt, AppDeclaration):
            if stmt.name in self.apps:
                self._error(stmt.location, f"App '{stmt.name}' is already defined.")
            else:
                self.apps[stmt.name] = stmt
        
        elif isinstance(stmt, DisplayDeclaration):
            if stmt.name in self.displays:
                self._error(stmt.location, f"Display '{stmt.name}' is already defined.")
            else:
                self.displays[stmt.name] = stmt
        
        elif isinstance(stmt, MacroDeclaration):
            if stmt.name in self.macros:
                self._error(stmt.location, f"Macro '{stmt.name}' is already defined.")
            else:
                self.macros[stmt.name] = stmt
        
        elif isinstance(stmt, ResourcesBlock):
            for decl in stmt.declarations:
                if isinstance(decl, FileDeclaration):
                    if decl.name in self.resources:
                        self._error(decl.location, f"Resource '{decl.name}' is already defined.")
                    else:
                        self.resources[decl.name] = decl.path
                elif isinstance(decl, DirDeclaration):
                    if decl.path_type in self.resources:
                        self._error(decl.location, f"Resource '{decl.path_type}' is already defined.")
                    else:
                        self.resources[decl.path_type] = decl.path
        
        elif isinstance(stmt, EnvBlock):
            for decl in stmt.declarations:
                if isinstance(decl, EnvDeclaration):
                    if decl.name in self.env_vars:
                        self._error(decl.location, f"Environment variable '{decl.name}' is already defined.")
                    else:
                        self.env_vars[decl.name] = decl.value
    
    def _validate_statement(self, stmt: Statement) -> None:
        """
        Validate a statement.
        
        Args:
            stmt: The statement to validate.
        """
        if isinstance(stmt, WidgetDeclaration):
            self._validate_widget_declaration(stmt)
        
        elif isinstance(stmt, CanvasDeclaration):
            self._validate_canvas_declaration(stmt)
        
        elif isinstance(stmt, StackDeclaration):
            self._validate_stack_declaration(stmt)
        
        elif isinstance(stmt, SequenceDeclaration):
            self._validate_sequence_declaration(stmt)
        
        elif isinstance(stmt, IndexDeclaration):
            self._validate_index_declaration(stmt)
        
        elif isinstance(stmt, AppDeclaration):
            self._validate_app_declaration(stmt)
        
        elif isinstance(stmt, BindingStatement):
            self._validate_binding_statement(stmt)
    
    def _validate_widget_declaration(self, widget: WidgetDeclaration) -> None:
        """
        Validate a widget declaration.
        
        Args:
            widget: The widget declaration to validate.
        """
        # Validate required properties based on widget type
        if widget.type == "Text":
            if "value" not in widget.properties:
                self._error(widget.location, f"Text widget '{widget.name}' must have a 'value' property.")
        
        elif widget.type == "Image":
            if "source" not in widget.properties:
                self._error(widget.location, f"Image widget '{widget.name}' must have a 'source' property.")
        
        # Validate expressions in properties
        for prop_name, expr in widget.properties.items():
            self._validate_expression(expr)
        
        # Validate timeline if present
        if widget.timeline is not None:
            self._validate_timeline_block(widget.timeline)
    
    def _validate_timeline_block(self, timeline: TimelineBlock) -> None:
        """
        Validate a timeline block.
        
        Args:
            timeline: The timeline block to validate.
        """
        # Use the MarqueeValidator for the marquee AST
        marquee_validator = MarqueeValidator(timeline.marquee_ast)
        marquee_errors = marquee_validator.validate()
        
        # Convert and add any errors
        for error in marquee_errors:
            self._error(timeline.location, f"In timeline: {error}")
    
    def _validate_canvas_declaration(self, canvas: CanvasDeclaration) -> None:
        """
        Validate a canvas declaration.
        
        Args:
            canvas: The canvas declaration to validate.
        """
        # Check if size is defined
        if "size" not in canvas.properties:
            self._error(canvas.location, f"Canvas '{canvas.name}' must have a 'size' property.")
        
        # Validate expressions in properties
        for prop_name, expr in canvas.properties.items():
            self._validate_expression(expr)
        
        # Validate placements
        for placement in canvas.placements:
            self._validate_placement_statement(placement)
    
    def _validate_placement_statement(self, placement: PlacementStatement) -> None:
        """
        Validate a placement statement.
        
        Args:
            placement: The placement statement to validate.
        """
        # Check if the referenced widget exists
        if placement.widget_name not in self.widgets:
            self._error(placement.location, f"Widget '{placement.widget_name}' is not defined.")
        else:
            # Mark widget as referenced
            self.referenced_widgets.add(placement.widget_name)
        
        # Validate coordinates
        self._validate_expression(placement.x)
        self._validate_expression(placement.y)
        
        # Validate z-index if present
        if placement.z is not None:
            self._validate_expression(placement.z)
    
    def _validate_stack_declaration(self, stack: StackDeclaration) -> None:
        """
        Validate a stack declaration.
        
        Args:
            stack: The stack declaration to validate.
        """
        # Check if orientation is defined
        if "orientation" not in stack.properties:
            self._error(stack.location, f"Stack '{stack.name}' must have an 'orientation' property.")
        
        # Validate expressions in properties
        for prop_name, expr in stack.properties.items():
            self._validate_expression(expr)
        
        # Validate appends
        for append in stack.appends:
            self._validate_append_statement(append)
    
    def _validate_append_statement(self, append: AppendStatement) -> None:
        """
        Validate an append statement.
        
        Args:
            append: The append statement to validate.
        """
        # Check if the referenced widget exists
        if append.widget_name not in self.widgets:
            self._error(append.location, f"Widget '{append.widget_name}' is not defined.")
        else:
            # Mark widget as referenced
            self.referenced_widgets.add(append.widget_name)
        
        # Validate gap if present
        if append.gap is not None:
            self._validate_expression(append.gap)
    
    def _validate_sequence_declaration(self, sequence: SequenceDeclaration) -> None:
        """
        Validate a sequence declaration.
        
        Args:
            sequence: The sequence declaration to validate.
        """
        # Validate expressions in properties
        for prop_name, expr in sequence.properties.items():
            self._validate_expression(expr)
        
        # Validate appends
        for append in sequence.appends:
            self._validate_sequence_append_statement(append)
    
    def _validate_sequence_append_statement(self, append: SequenceAppendStatement) -> None:
        """
        Validate a sequence append statement.
        
        Args:
            append: The sequence append statement to validate.
        """
        # Check if the referenced widget exists
        if append.widget_name not in self.widgets and append.widget_name not in self.canvases:
            self._error(
                append.location, 
                f"Widget or canvas '{append.widget_name}' is not defined."
            )
        else:
            # Mark widget as referenced
            if append.widget_name in self.widgets:
                self.referenced_widgets.add(append.widget_name)
        
        # Validate condition if present
        if append.condition is not None:
            self._validate_expression(append.condition)
    
    def _validate_index_declaration(self, index: IndexDeclaration) -> None:
        """
        Validate an index declaration.
        
        Args:
            index: The index declaration to validate.
        """
        # Check if value is defined
        if "value" not in index.properties:
            self._error(index.location, f"Index '{index.name}' must have a 'value' property.")
        
        # Validate expressions in properties
        for prop_name, expr in index.properties.items():
            self._validate_expression(expr)
        
        # Validate appends
        for append in index.appends:
            self._validate_index_append_statement(append)
    
    def _validate_index_append_statement(self, append: IndexAppendStatement) -> None:
        """
        Validate an index append statement.
        
        Args:
            append: The index append statement to validate.
        """
        # Check if the referenced widget exists
        if append.widget_name not in self.widgets:
            self._error(append.location, f"Widget '{append.widget_name}' is not defined.")
        else:
            # Mark widget as referenced
            self.referenced_widgets.add(append.widget_name)
    
    def _validate_app_declaration(self, app: AppDeclaration) -> None:
        """
        Validate an app declaration.
        
        Args:
            app: The app declaration to validate.
        """
        # Check if theme is defined
        if "theme" not in app.properties:
            self._error(app.location, f"App '{app.name}' must have a 'theme' property.")
        elif isinstance(app.properties["theme"], Literal) and app.properties["theme"].value not in self.themes:
            self._error(app.location, f"Theme '{app.properties['theme'].value}' is not defined.")
        
        # Validate expressions in properties
        for prop_name, expr in app.properties.items():
            self._validate_expression(expr)
        
        # Validate screens
        for screen in app.screens:
            if screen.target_name not in self.canvases and screen.target_name not in self.sequences:
                self._error(
                    screen.location, 
                    f"Canvas or sequence '{screen.target_name}' is not defined."
                )
        
        # Validate datasources
        for ds in app.datasources:
            if ds.target_name not in self.datasources:
                self._error(ds.location, f"DataSource '{ds.target_name}' is not defined.")
    
    def _validate_binding_statement(self, binding: BindingStatement) -> None:
        """
        Validate a binding statement.
        
        Args:
            binding: The binding statement to validate.
        """
        # Check if the target contains a valid path
        parts = binding.target.split('.')
        if len(parts) < 2:
            self._error(binding.location, f"Invalid binding target: '{binding.target}'. Expected format: 'source.property'.")
            return
        
        source = parts[0]
        
        # Check if the source exists
        if source not in self.datasources and source not in self.states:
            self._error(binding.location, f"Binding source '{source}' is not defined as a DataSource or State.")
    
    def _validate_expression(self, expr: Expression) -> None:
        """
        Validate an expression.
        
        Args:
            expr: The expression to validate.
        """
        if isinstance(expr, PropertyAccess):
            # Check theme properties
            if isinstance(expr.object, str) and expr.object == "THEME":
                if expr.property not in ["background", "foreground", "accent"]:
                    self._error(expr.location, f"Unknown theme property: '{expr.property}'.")
        
        elif isinstance(expr, MacroReference):
            # Check if the macro is defined
            if expr.name not in self.macros and not expr.name.startswith("THEME."):
                self._error(expr.location, f"Macro '{expr.name}' is not defined.")
        
        elif isinstance(expr, Variable):
            # We can't reliably validate variables as they could be parameters or come from various sources
            pass
        
        elif isinstance(expr, ObjectLiteral):
            # Validate properties in object literal
            for prop_name, sub_expr in expr.properties.items():
                self._validate_expression(sub_expr)
        
        elif isinstance(expr, ArrayLiteral):
            # The ArrayLiteral implementation is inconsistent - sometimes elements is in the location field
            # and the elements field has a Location object instead.
            
            # Case 1: Normal array with elements in the right field
            if isinstance(expr.elements, list):
                # Validate elements in array literal
                for element in expr.elements:
                    self._validate_expression(element)
            
            # Case 2: Array with elements in location field (parser issue)
            elif isinstance(expr.location, list):
                # Validate elements in array literal
                for element in expr.location:
                    self._validate_expression(element)
            else:
                self._error(expr.location, f"Array literal has invalid structure: elements={type(expr.elements)}, location={type(expr.location)}")
        
        elif isinstance(expr, BinaryExpression):
            # Validate left and right expressions
            self._validate_expression(expr.left)
            self._validate_expression(expr.right)
    
    def _check_unreferenced_widgets(self) -> None:
        """Check for widgets that are defined but not referenced."""
        for name, widget in self.widgets.items():
            if name not in self.referenced_widgets:
                # Add a warning rather than an error
                self.errors.append(ValidationError(
                    widget.location,
                    f"Warning: Widget '{name}' is defined but never used."
                ))
    
    def _error(self, location: Location, message: str) -> None:
        """
        Add a validation error.
        
        Args:
            location: The location of the error.
            message: The error message.
        """
        self.errors.append(ValidationError(location, message)) 