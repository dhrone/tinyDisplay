# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Utility module for tinyDisplay - re-exports all utility functionality from the 
new utility package structure for backward compatibility.
"""

# Import all utility components from the utility package
from tinyDisplay.utility import (
    dataset, evaluator, dynamicValue, animate, 
    image2Text, compareImage, okPath,
    getArgDecendents, getNotDynamicDecendents,
    dynamic, DynamicValue, dependency_registry
)

# Export all imported components
__all__ = [
    'dataset', 'evaluator', 'dynamicValue', 'animate', 
    'image2Text', 'compareImage', 'okPath',
    'getArgDecendents', 'getNotDynamicDecendents',
    'dynamic', 'DynamicValue', 'dependency_registry'
]

# Backwards compatibility alias
Dataset = dataset 