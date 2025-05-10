#!/usr/bin/env python
"""
Debug script for running the SCROLL_BOUNCE test with full debug logging.
"""

import logging
import sys
import pytest

# Set up logging for the entire tinyDisplay package
logging.basicConfig(level=logging.DEBUG)

# Ensure the marquee_executor logger is set to DEBUG level
executor_logger = logging.getLogger("tinyDisplay.dsl.marquee_executor")
executor_logger.setLevel(logging.DEBUG)

# Configure a stream handler to output to console
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
executor_logger.addHandler(handler)

# Run the test
pytest.main(["-v", "tests/dsl/test_complex_dsl_execution.py::TestComplexDSLExecution::test_scroll_bounce_animation"]) 