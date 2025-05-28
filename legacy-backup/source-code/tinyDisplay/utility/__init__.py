# -*- coding: utf-8 -*-
# tinyDisplay utility module

"""
Utility package for tinyDisplay - contains various helper functions and classes.
"""

# Import components from their respective modules
from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.evaluator import evaluator, dynamicValue
from tinyDisplay.utility.animation import animate
from tinyDisplay.utility.image_utils import image2Text, compareImage, okPath
from tinyDisplay.utility.misc import getArgDecendents, getNotDynamicDecendents
from tinyDisplay.utility.dynamic import dynamic, dependency_registry
from tinyDisplay.utility.variable_dependencies import VariableDependencyRegistry, variable_registry
from tinyDisplay.utility.dependency_manager import (
    DependencyManager, dependency_manager, 
    register_variable, define_dependency, apply_dependencies,
    create_variable, create_variables_from_config
)
import warnings

# Define what gets exported with wildcard import
__all__ = [
    'dataset', 'evaluator', 'dynamicValue', 'animate', 'image2Text', 'compareImage',
    'okPath', 'getArgDecendents', 'getNotDynamicDecendents',
    'dynamic', 'dependency_registry',
    'VariableDependencyRegistry', 'variable_registry',
    'DependencyManager', 'dependency_manager', 
    'register_variable', 'define_dependency', 'apply_dependencies',
    'create_variable', 'create_variables_from_config'
] 