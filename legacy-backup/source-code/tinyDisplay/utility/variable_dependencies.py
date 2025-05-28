"""
Variable dependency tracking system for tinyDisplay.

This module provides fine-grained dependency tracking between dynamic variables
and specific dataset fields, allowing for optimized re-evaluation of expressions.
"""
import re
import logging
from collections import defaultdict

class VariableDependencyRegistry:
    """Tracks dependencies between dynamic variables and specific dataset fields."""
    
    def __init__(self):
        self.field_to_variables = defaultdict(set)  # field_path -> set(dynamic_variables)
        self.variable_to_fields = defaultdict(set)  # dynamic_variable -> set(field_paths)
        self.variable_dependencies = defaultdict(set)  # variable -> set(dependent_variables)
        self.logger = logging.getLogger("tinyDisplay")
    
    def register_variable_dependency(self, variable, field_path):
        """Register a dependency between a variable and a specific field.
        
        Args:
            variable: The dynamic variable object
            field_path: String like "db.key" or "db['key']" representing the specific field
        """
        normalized_path = self._normalize_field_path(field_path)
        var_name = getattr(variable, 'name', str(variable))
        
        self.logger.debug(f"Registering variable {var_name} dependency on field: {field_path} (normalized: {normalized_path})")
        
        # Skip registration if already registered
        if normalized_path in self.variable_to_fields.get(variable, set()):
            self.logger.debug(f"Dependency already registered for {var_name} on {normalized_path}")
            return
            
        self.field_to_variables[normalized_path].add(variable)
        
        if variable not in self.variable_to_fields:
            self.variable_to_fields[variable] = set()
        self.variable_to_fields[variable].add(normalized_path)
        
        # Log all current dependencies for this variable
        all_deps = self.variable_to_fields.get(variable, set())
        self.logger.debug(f"Variable {var_name} now has {len(all_deps)} field dependencies: {all_deps}")
        
        # Extract the database name for backward compatibility with widget system
        db_name = self._extract_db_name(normalized_path)
        if db_name:
            self.logger.debug(f"Registered variable dependency: {var_name} depends on {normalized_path} (db: {db_name})")
            
        # Log all current registrations for this path
        deps = self.field_to_variables.get(normalized_path, set())
        self.logger.debug(f"Field {normalized_path} now has {len(deps)} dependent variables")
    
    def register_variable_to_variable_dependency(self, dependent_var, dependency_var):
        """Register a dependency between two variables.
        
        Args:
            dependent_var: The variable that depends on another
            dependency_var: The variable being depended on
        """
        if dependent_var == dependency_var:
            return  # Avoid self-dependencies
            
        self.variable_dependencies[dependency_var].add(dependent_var)
        self.logger.debug(f"Registered variable-to-variable dependency: {dependent_var} depends on {dependency_var}")
    
    def get_dependent_variables(self, field_path):
        """Get all variables that directly depend on a specific field.
        
        Args:
            field_path: The field path in format "db.key" or "db['key']"
            
        Returns:
            Set of variables directly dependent on this field
        """
        normalized_path = self._normalize_field_path(field_path)
        return self.field_to_variables.get(normalized_path, set())
    
    def get_all_affected_variables(self, field_path):
        """Get all variables affected by a change to a field, including indirect dependencies.
        
        Args:
            field_path: The field path in format "db.key" or "db['key']"
            
        Returns:
            Set of all variables (direct and indirect) dependent on this field
        """
        normalized_path = self._normalize_field_path(field_path)
        direct_deps = self.get_dependent_variables(normalized_path)
        
        self.logger.debug(f"Direct dependencies for {normalized_path}: {len(direct_deps)} vars")
        for var in direct_deps:
            if hasattr(var, 'name'):
                self.logger.debug(f" - Dependent var: {var.name}")
            else:
                self.logger.debug(f" - Dependent var: {var}")
        
        all_deps = set(direct_deps)
        
        # Process transitive dependencies
        to_process = list(direct_deps)
        while to_process:
            var = to_process.pop(0)
            for dependent in self.variable_dependencies.get(var, set()):
                if dependent not in all_deps:
                    all_deps.add(dependent)
                    to_process.append(dependent)
                    if hasattr(dependent, 'name'):
                        self.logger.debug(f" - Indirect dependent: {dependent.name}")
                    else:
                        self.logger.debug(f" - Indirect dependent: {dependent}")
        
        return all_deps
    
    def notify_field_change(self, field_path):
        """Mark all variables dependent on this field for update.
        
        Args:
            field_path: The field path that changed
            
        Returns:
            Set of variables that need to be updated
        """
        self.logger.debug(f"notify_field_change called for: {field_path}")
        normalized_path = self._normalize_field_path(field_path)
        self.logger.debug(f"Normalized path: {normalized_path}")
        
        # Get direct dependents
        direct_deps = self.get_dependent_variables(normalized_path)
        self.logger.debug(f"Direct dependencies for {normalized_path}: {len(direct_deps)} variables")
        for var in direct_deps:
            var_name = getattr(var, 'name', str(var))
            self.logger.debug(f" - Direct dependent: {var_name}")
        
        # Get all affected variables (direct + indirect)
        affected_vars = self.get_all_affected_variables(field_path)
        self.logger.debug(f"Field change in {field_path} affects {len(affected_vars)} variables total")
        
        # Mark all affected variables for update
        for var in affected_vars:
            var_name = getattr(var, 'name', str(var))
            if hasattr(var, 'mark_for_update'):
                self.logger.debug(f"Marking for update: {var_name}")
                var.mark_for_update()
            else:
                self.logger.debug(f"Variable doesn't have mark_for_update method: {var_name}")
            
        return affected_vars
    
    def parse_dependencies_from_expression(self, expression):
        """Extract field dependencies from an expression string.
        
        Args:
            expression: String expression to analyze
            
        Returns:
            List of field paths found in the expression
        """
        dependencies = []
        
        if not isinstance(expression, str):
            return dependencies
            
        self.logger.debug(f"Parsing dependencies from: {expression}")
        
        # Updated pattern to handle nested field access with bracket notation
        # This pattern will match patterns like db['key'] as well as db['nested']['inner']
        bracket_pattern = r"""
            ([a-zA-Z_][a-zA-Z0-9_]*)      # Database name
            (?:                            # Start non-capturing group
                \[['"]([^'"]*)['"]\]       # First bracket with key
                (?:                        # Start non-capturing group for nested keys
                    \[['"]([^'"]*)['"]\]   # Nested bracket with key
                )*                         # Zero or more nested keys
            )
        """
        
        # Use verbose mode for the regex to make it more readable
        bracket_regex = re.compile(bracket_pattern, re.VERBOSE)
        
        # Find all matches for bracket patterns
        for match in bracket_regex.finditer(expression):
            # Get the full matched text which includes the entire path
            full_match = match.group(0)
            db_name = match.group(1)
            
            # Add the full path as a dependency
            dependencies.append(full_match)
            self.logger.debug(f"Found bracket dependency: {full_match}")
            
            # Also add the parent path(s) for nested access
            parts = re.findall(r"\[['\"](.*?)['\"]", full_match)
            if len(parts) > 1:
                # Add parent path(s)
                for i in range(1, len(parts)):
                    parent_path = f"{db_name}"
                    for j in range(i):
                        parent_path += f"['{parts[j]}']"
                    dependencies.append(parent_path)
                    self.logger.debug(f"Found parent dependency: {parent_path}")
        
        # Also handle dot notation for completeness
        dot_pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)"
        
        # Find all matches for dot notation
        for match in re.finditer(dot_pattern, expression):
            db_name = match.group(1)
            key = match.group(2)
            field_path = f"{db_name}.{key}"
            dependencies.append(field_path)
            self.logger.debug(f"Found dot notation dependency: {field_path}")
        
        # Look for method calls like db.get('key', default_value)
        method_call_pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)\.get\(['\"]([^'\"]+)['\"]"
        
        # Find all matches for method calls
        for match in re.finditer(method_call_pattern, expression):
            db_name = match.group(1)
            key = match.group(2)
            
            # Add as field dependency - this is the database itself
            dependencies.append(db_name)
            
            # Also add the specific field since get() is looking up a field
            field_path = f"{db_name}['{key}']"
            dependencies.append(field_path)
            self.logger.debug(f"Found get() method call dependency: {field_path}")
            
        return dependencies
    
    def _normalize_field_path(self, field_path):
        """Normalize field path to a consistent format.
        
        This allows us to handle both db['key'] and db.key formats.
        
        Args:
            field_path: Field path string
            
        Returns:
            Normalized field path
        """
        # If it's already in bracket notation, return as is
        if "[" in field_path and "]" in field_path:
            return field_path
            
        # Convert dot notation to bracket notation
        if "." in field_path:
            parts = field_path.split(".", 1)
            if len(parts) == 2:
                return f"{parts[0]}['{parts[1]}']"
                
        return field_path
    
    def _extract_db_name(self, field_path):
        """Extract database name from a field path.
        
        Args:
            field_path: Field path string like "db['key']" or "db.key"
            
        Returns:
            Database name or None if not found
        """
        # Handle bracket notation
        bracket_match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\[", field_path)
        if bracket_match:
            return bracket_match.group(1)
            
        # Handle dot notation
        dot_match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\.", field_path)
        if dot_match:
            return dot_match.group(1)
            
        return None
    
    def clear_variable_dependencies(self, variable):
        """Remove all dependencies for a variable (used when recreating a variable).
        
        Args:
            variable: The variable to clear dependencies for
        """
        # Remove from field_to_variables
        for field in self.variable_to_fields.get(variable, set()):
            if variable in self.field_to_variables[field]:
                self.field_to_variables[field].remove(variable)
                
        # Remove from variable_dependencies
        for dep_var, dependents in self.variable_dependencies.items():
            if variable in dependents:
                dependents.remove(variable)
                
        # Remove all dependencies
        if variable in self.variable_to_fields:
            del self.variable_to_fields[variable]
            
        # Remove as a dependency source
        if variable in self.variable_dependencies:
            del self.variable_dependencies[variable]

# Create global registry
variable_registry = VariableDependencyRegistry() 