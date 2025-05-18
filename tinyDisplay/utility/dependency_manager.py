"""
Dependency manager for tinyDisplay dynamic variables.

This module provides utility functions for managing dependencies between
dynamic variables in a more structured and explicit way.
"""

import logging
from typing import Dict, List, Union, Optional

# Use lazy imports to avoid circular dependencies
# from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.variable_dependencies import variable_registry

logger = logging.getLogger("tinyDisplay")

class DependencyManager:
    """
    Manager for explicitly defining and registering dependencies between dynamic variables.
    
    This class provides a centralized way to define, register, and manage
    dependencies between dynamic variables, making it easier to maintain
    complex dependency relationships.
    """
    
    def __init__(self):
        """Initialize a new dependency manager."""
        self.variables = {}  # name -> dynamicValue mapping
        self.dependencies = {}  # name -> list of names it depends on
        
    def register(self, name: str, variable) -> object:
        """
        Register a dynamic variable with the manager.
        
        Args:
            name: A unique name for the variable
            variable: The dynamicValue instance
            
        Returns:
            The registered dynamicValue for method chaining
        """
        self.variables[name] = variable
        logger.debug(f"Registered variable {name} in dependency manager")
        return variable
        
    def define_dependency(self, dependent: str, dependency: Union[str, List[str]]) -> None:
        """
        Define a dependency relationship between variables.
        
        Args:
            dependent: The name of the dependent variable
            dependency: The name(s) of the variables it depends on
        """
        if dependent not in self.dependencies:
            self.dependencies[dependent] = []
            
        # Convert single dependency to list
        if not isinstance(dependency, list):
            dependency = [dependency]
            
        # Add dependencies
        self.dependencies[dependent].extend(dependency)
        logger.debug(f"Defined dependency: {dependent} depends on {dependency}")
        
    def apply_dependencies(self) -> None:
        """
        Apply all defined dependencies by registering them with the variable registry.
        
        This should be called after all variables have been registered and
        all dependencies have been defined.
        """
        for dependent_name, dependency_names in self.dependencies.items():
            if dependent_name not in self.variables:
                logger.warning(f"Dependent variable {dependent_name} not registered, skipping")
                continue
                
            dependent_var = self.variables[dependent_name]
            
            for dep_name in dependency_names:
                if dep_name not in self.variables:
                    logger.warning(f"Dependency {dep_name} not registered, skipping")
                    continue
                    
                dependency_var = self.variables[dep_name]
                variable_registry.register_variable_to_variable_dependency(dependent_var, dependency_var)
                logger.debug(f"Applied dependency: {dependent_name} depends on {dep_name}")
                
    def create_variable(
        self, 
        name: str, 
        expression: str, 
        depends_on: Optional[Union[str, List[str]]] = None
    ) -> object:
        """
        Create, register, and define dependencies for a dynamic variable in one step.
        
        Args:
            name: The name of the variable
            expression: The expression to evaluate
            depends_on: Optional name(s) of variables this depends on
            
        Returns:
            The created dynamicValue instance
        """
        # Import here to avoid circular imports
        from tinyDisplay.utility.dynamic import dynamic
        
        # Create the dynamic variable
        var = dynamic(expression)
        
        # Register it with the manager
        self.register(name, var)
        
        # Define dependencies if provided
        if depends_on:
            self.define_dependency(name, depends_on)
            
        return var
        
    def create_variables_from_config(self, config: Dict[str, Dict]) -> Dict[str, object]:
        """
        Create multiple variables from a configuration dictionary.
        
        Args:
            config: A dictionary of variable configurations
                Format: {
                    "variable_name": {
                        "expression": "db['value'] * 2",
                        "depends_on": ["other_var1", "other_var2"]  # optional
                    }
                }
                
        Returns:
            Dictionary mapping variable names to their dynamicValue instances
        """
        result = {}
        
        # First pass: create all variables
        for name, settings in config.items():
            if "expression" not in settings:
                logger.warning(f"Missing 'expression' for variable {name}, skipping")
                continue
                
            var = self.create_variable(name, settings["expression"])
            result[name] = var
            
        # Second pass: define dependencies
        for name, settings in config.items():
            if "depends_on" in settings and name in result:
                self.define_dependency(name, settings["depends_on"])
                
        # Apply all dependencies
        self.apply_dependencies()
        
        return result


# Create a global dependency manager instance
dependency_manager = DependencyManager()

# Export convenience functions that use the global manager
def register_variable(name, variable):
    """Register a variable with the global dependency manager."""
    return dependency_manager.register(name, variable)
    
def define_dependency(dependent, dependency):
    """Define a dependency using the global dependency manager."""
    dependency_manager.define_dependency(dependent, dependency)
    
def apply_dependencies():
    """Apply all dependencies using the global dependency manager."""
    dependency_manager.apply_dependencies()
    
def create_variable(name, expression, depends_on=None):
    """Create a variable using the global dependency manager."""
    return dependency_manager.create_variable(name, expression, depends_on)
    
def create_variables_from_config(config):
    """Create variables from config using the global dependency manager."""
    return dependency_manager.create_variables_from_config(config) 