# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
tinyDisplay package.

.. versionadded:: 0.0.1
"""

__version__ = "0.1.2"

import logging
import os
import sys
from tinyDisplay.utility.variable_dependencies import variable_registry
import tinyDisplay.global_dataset as global_dataset

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Configure logging for the tinyDisplay application.
    
    Args:
        log_level: The logging level to use (default: logging.INFO)
        log_file: Optional file path to write logs to (default: None, logs to console only)
    
    Returns:
        Logger: The configured logger
    """
    logger = logging.getLogger("tinyDisplay")
    logger.setLevel(log_level)
    
    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Initialize default logger
setup_logging()

# Make globally accessible modules available
__all__ = ['variable_registry', 'global_dataset']
