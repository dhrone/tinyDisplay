import pytest
import logging
from tinyDisplay.render.coordination import timeline_manager
from tinyDisplay.render.new_marquee import new_marquee

# Configure logging for tests
logging.basicConfig(level=logging.INFO)

@pytest.fixture(autouse=True, scope="function")
def reset_timeline_state():
    """
    Reset all timeline and coordination manager state before and after each test.
    
    This fixture runs automatically for each test function to ensure
    that tests don't affect each other due to shared state.
    
    The timeline_manager is a singleton that maintains state across test runs.
    Without proper cleanup, tests that rely on this state (like test_selective_recalculation.py)
    can fail when run as part of the full test suite because:
    
    1. Earlier tests leave their widgets registered in the timeline_manager
    2. The state of resolved timelines persists between tests
    3. The new_marquee._timelines_initialized flag stays set to True
    
    By resetting all these values before and after each test, we ensure tests
    remain isolated and don't affect each other.
    """
    # Before test: Clear the timeline state
    timeline_manager.clear()
    new_marquee._timelines_initialized = False
    
    # Run the test
    yield
    
    # After test: Clear the timeline state again
    timeline_manager.clear()
    new_marquee._timelines_initialized = False 