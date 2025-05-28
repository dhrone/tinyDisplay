"""
Test for running the SCROLL_BOUNCE test with full debug logging.
"""

import logging
import pytest

@pytest.fixture(scope="function")
def setup_logging():
    """Set up detailed logging for the test."""
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
    
    # Yield to allow test to run
    yield
    
    # Cleanup if needed
    handlers = executor_logger.handlers[:]
    for handler in handlers:
        executor_logger.removeHandler(handler)

@pytest.mark.integration
def test_scroll_bounce_animation(setup_logging):
    """
    This is a wrapper to run the scroll bounce animation test with debug logging.
    It imports and runs the original test directly from the test_complex_dsl_execution module.
    """
    from tests.dsl.test_complex_dsl_execution import TestComplexDSLExecution
    
    # Create an instance of the test class and run the test
    test_instance = TestComplexDSLExecution()
    test_instance.setup_method(None)  # Call setup manually
    test_instance.test_scroll_bounce_animation()
    test_instance.teardown_method(None)  # Call teardown manually
    
    assert True  # Test passes if original test doesn't raise exceptions 