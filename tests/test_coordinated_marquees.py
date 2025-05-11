#!/usr/bin/env python3
"""
Test script for coordinated marquee rendering.

This script demonstrates the use of SYNC and WAIT_FOR statements
to coordinate the timelines of multiple marquee widgets, ensuring
deterministic rendering even with interdependencies.
"""

import logging
import time
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.render.new_marquee import new_marquee
from tinyDisplay.render.widget import text
from tinyDisplay.render.coordination import timeline_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('coordinated_marquees.log')
    ]
)

def main():
    """Run the coordinated marquee demonstration."""
    logger = logging.getLogger("test_coordinated_marquees")
    logger.info("Starting coordinated marquee test")
    
    # Create a test image to render to
    display_width, display_height = 256, 64
    display_image = Image.new("RGBA", (display_width, display_height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(display_image)
    
    try:
        # Create font for text widgets
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Create two text widgets with different content lengths
        text1 = text(
            text="This is the first marquee that will trigger a SYNC event",
            size=(200, 20),
            font=font,
            color=(255, 255, 255),
        )
        
        text2 = text(
            text="This is the second marquee that waits for the first one",
            size=(200, 20),
            font=font,
            color=(255, 255, 0),
        )
        
        # Clear the timeline manager to ensure clean state
        timeline_manager.clear()
        
        # Create DSL programs for the marquees
        
        # First marquee: scrolls text and signals with SYNC when it completes one cycle
        # This generates a trigger that the second marquee can wait for
        marquee1_program = """
        LOOP(INFINITE) {
            SCROLL_LOOP(LEFT, widget.width) { step=1, interval=1, gap=20 };
            SYNC(cycle_complete);  # Signal that one cycle is complete
            PAUSE(10);  # Pause briefly at the end of each cycle
        } END;
        """
        
        # Second marquee: waits for the SYNC event from the first marquee
        # This demonstrates the dependency between marquees
        marquee2_program = """
        LOOP(INFINITE) {
            SCROLL_BOUNCE(LEFT, 100) { step=1, interval=1 };
            WAIT_FOR(cycle_complete, 100);  # Wait for first marquee's cycle_complete event
            PAUSE(5);  # Pause briefly after receiving the event
        } END;
        """
        
        # Create the marquee widgets with the DSL programs
        # Using automatic event sharing through the timeline_manager
        marquee1 = new_marquee(
            widget=text1,
            program=marquee1_program,
            size=(200, 20),
            position=(20, 10),
        )
        
        marquee2 = new_marquee(
            widget=text2,
            program=marquee2_program,
            size=(200, 20),
            position=(20, 35),
        )
        
        # Initialize all timelines and resolve dependencies
        logger.info("Initializing all marquee timelines")
        new_marquee.initialize_all_timelines()
        
        # Render frames to demonstrate the coordination
        num_frames = 500
        for frame in range(num_frames):
            # Clear display
            draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
            
            # Render marquees
            img1, changed1 = marquee1.render(tick=frame, move=True)
            img2, changed2 = marquee2.render(tick=frame, move=True)
            
            # Paste into the display image
            display_image.paste(img1, marquee1.position, img1)
            display_image.paste(img2, marquee2.position, img2)
            
            # Save frame (optional)
            if frame % 10 == 0:
                display_image.save(f"frame_{frame:04d}.png")
                logger.info(f"Rendered frame {frame}")
                
                # Log the positions of the widgets
                if hasattr(marquee1, '_curPos'):
                    pos1 = marquee1._curPos
                    x1 = pos1.x if hasattr(pos1, 'x') else pos1[0]
                    y1 = pos1.y if hasattr(pos1, 'y') else pos1[1]
                    logger.info(f"Marquee 1 position: ({x1}, {y1})")
                    
                if hasattr(marquee2, '_curPos'):
                    pos2 = marquee2._curPos
                    x2 = pos2.x if hasattr(pos2, 'x') else pos2[0]
                    y2 = pos2.y if hasattr(pos2, 'y') else pos2[1]
                    logger.info(f"Marquee 2 position: ({x2}, {y2})")
                
            # Interactive rendering simulation
            time.sleep(0.01)  # Slow down to see the animation
        
        logger.info("Test complete")
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)

def test_coordinated_marquees():
    """Pytest-compatible test function that runs the demo for a few frames."""
    # Monkey patch the main function to use fewer frames for testing
    import types
    
    # Store the original main function
    original_main = main
    
    # Create a modified version that runs fewer frames
    def quick_test_main():
        logger = logging.getLogger("test_coordinated_marquees")
        logger.info("Starting coordinated marquee test (pytest mode)")
        
        # Create a test image to render to
        display_width, display_height = 256, 64
        display_image = Image.new("RGBA", (display_width, display_height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(display_image)
        
        # Create font for text widgets
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Create two text widgets with different content lengths
        text1 = text(
            text="This is the first marquee that will trigger a SYNC event",
            size=(200, 20),
            font=font,
            color=(255, 255, 255),
        )
        
        text2 = text(
            text="This is the second marquee that waits for the first one",
            size=(200, 20),
            font=font,
            color=(255, 255, 0),
        )
        
        # Clear the timeline manager to ensure clean state
        timeline_manager.clear()
        
        # Create the marquee widgets with the DSL programs (use shorter programs)
        marquee1_program = """
        LOOP(INFINITE) {
            SCROLL_LOOP(LEFT, widget.width) { step=2, interval=1, gap=10 };
            SYNC(cycle_complete);
            PAUSE(5);
        } END;
        """
        
        marquee2_program = """
        LOOP(INFINITE) {
            SCROLL_BOUNCE(LEFT, 50) { step=2, interval=1 };
            WAIT_FOR(cycle_complete, 20);
            PAUSE(2);
        } END;
        """
        
        # Create the marquee widgets WITHOUT explicit shared collections
        # The system will now use automatic sharing via timeline_manager
        marquee1 = new_marquee(
            widget=text1,
            program=marquee1_program,
            size=(200, 20),
            position=(20, 10),
        )
        
        marquee2 = new_marquee(
            widget=text2,
            program=marquee2_program,
            size=(200, 20),
            position=(20, 35),
        )
        
        # Log the state of timeline manager's shared collections before initialization
        logger.info(f"Before initialization - shared_events: {timeline_manager.shared_events}")
        logger.info(f"Before initialization - shared_sync_events: {timeline_manager.shared_sync_events}")
        
        # Initialize all timelines and resolve dependencies
        logger.info("Initializing all marquee timelines")
        new_marquee.initialize_all_timelines()
        
        # Log the state of timeline manager's shared collections after initialization
        logger.info(f"After initialization - shared_events: {timeline_manager.shared_events}")
        logger.info(f"After initialization - shared_sync_events: {timeline_manager.shared_sync_events}")
        
        # Inspect internal event tracking in the executor contexts
        if hasattr(marquee1, '_executor') and hasattr(marquee1._executor, 'context'):
            logger.info(f"Marquee1 executor events: {marquee1._executor.context.events}")
            logger.info(f"Marquee1 executor defined_sync_events: {marquee1._executor.context.defined_sync_events}")
        
        if hasattr(marquee2, '_executor') and hasattr(marquee2._executor, 'context'):
            logger.info(f"Marquee2 executor events: {marquee2._executor.context.events}")
            logger.info(f"Marquee2 executor defined_sync_events: {marquee2._executor.context.defined_sync_events}")
            
        # Log timeline manager state
        logger.info(f"Timeline manager sync_events: {timeline_manager.sync_events}")
        
        # Render just a few frames for the test
        num_frames = 30  # Reduced from 500 for quick testing
        for frame in range(num_frames):
            # Clear display
            draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
            
            # Render marquees
            img1, changed1 = marquee1.render(tick=frame, move=True)
            img2, changed2 = marquee2.render(tick=frame, move=True)
            
            # Paste into the display image
            display_image.paste(img1, marquee1.position, img1)
            display_image.paste(img2, marquee2.position, img2)
            
            # Save only one frame for verification
            if frame == 20:
                display_image.save("pytest_frame.png")
                logger.info("Saved pytest test frame")
            
            # We don't sleep in test mode to keep it fast
        
        # Log the state of shared events after rendering
        logger.info(f"After rendering - shared_events: {timeline_manager.shared_events}")
        
        # Modified assertion to check in timeline_manager's collections
        if 'cycle_complete' not in timeline_manager.shared_events:
            logger.error(f"SYNC event not created - shared_events content: {timeline_manager.shared_events}")
            # Check if event is in executor context but not in shared_events
            if hasattr(marquee1, '_executor') and hasattr(marquee1._executor, 'context'):
                if 'cycle_complete' in marquee1._executor.context.events:
                    logger.error("Event exists in executor context but not in shared_events!")
            assert False, "SYNC event not created"
            
        assert len(timeline_manager.sync_events) > 0, "No sync events registered"
        
        logger.info("Test complete")

    # Run the quick test version
    quick_test_main()

def test_auto_shared_events():
    """Test automatic event sharing without explicitly providing shared collections."""
    logger = logging.getLogger("test_auto_shared_events")
    logger.info("Starting automatic event sharing test")
    
    # Create a test image to render to
    display_width, display_height = 256, 64
    display_image = Image.new("RGBA", (display_width, display_height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(display_image)
    
    # Create font for text widgets
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Clear the timeline manager to ensure clean state
    timeline_manager.clear()
    
    # Create two text widgets
    text1 = text(
        text="First marquee with automatic event sharing",
        size=(200, 20),
        font=font,
        color=(255, 255, 255),
    )
    
    text2 = text(
        text="Second marquee that uses auto-shared events",
        size=(200, 20),
        font=font,
        color=(255, 255, 0),
    )
    
    # Create DSL programs for the marquees
    marquee1_program = """
    LOOP(INFINITE) {
        SCROLL_LOOP(LEFT, 100) { step=2, interval=1 };
        SYNC(auto_event);  # Signal that should be automatically shared
        PAUSE(5);
    } END;
    """
    
    marquee2_program = """
    LOOP(INFINITE) {
        WAIT_FOR(auto_event, 20);  # Wait for automatically shared event
        SCROLL_LOOP(RIGHT, 50) { step=2, interval=1 };
        PAUSE(2);
    } END;
    """
    
    # Create the marquee widgets WITHOUT passing explicit shared collections
    # This will test our automatic sharing functionality
    marquee1 = new_marquee(
        widget=text1,
        program=marquee1_program,
        size=(200, 20),
        position=(20, 10),
    )
    
    marquee2 = new_marquee(
        widget=text2,
        program=marquee2_program,
        size=(200, 20),
        position=(20, 35),
    )
    
    # Log the state of timeline manager's shared collections before initialization
    logger.info(f"Before initialization - shared_events: {timeline_manager.shared_events}")
    logger.info(f"Before initialization - shared_sync_events: {timeline_manager.shared_sync_events}")
    
    # Initialize all timelines and resolve dependencies
    logger.info("Initializing all marquee timelines")
    new_marquee.initialize_all_timelines()
    
    # Log the state of timeline manager's shared collections after initialization
    logger.info(f"After initialization - shared_events: {timeline_manager.shared_events}")
    logger.info(f"After initialization - shared_sync_events: {timeline_manager.shared_sync_events}")
    
    # Verify that the SYNC event was registered in the timeline manager
    assert 'auto_event' in timeline_manager.shared_events, "SYNC event should be auto-registered in shared_events"
    assert 'auto_event' in timeline_manager.shared_sync_events, "SYNC event should be auto-registered in shared_sync_events"
    
    # Verify that the event is in the timeline manager's sync_events as well
    assert 'auto_event' in timeline_manager.sync_events, "SYNC event should be registered in timeline_manager's sync_events"
    
    # Render some frames to make sure coordination works
    num_frames = 30
    for frame in range(num_frames):
        # Clear display
        draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
        
        # Render marquees
        img1, changed1 = marquee1.render(tick=frame, move=True)
        img2, changed2 = marquee2.render(tick=frame, move=True)
        
        # Paste into the display image
        display_image.paste(img1, marquee1.position, img1)
        display_image.paste(img2, marquee2.position, img2)
        
        # Save one frame for verification
        if frame == 15:
            display_image.save("auto_shared_events_frame.png")
            logger.info("Saved auto-shared events test frame")
    
    # Verify that the executor contexts are using the shared collections
    # They should all reference the same object in memory
    if hasattr(marquee1, '_executor') and hasattr(marquee1._executor, 'context'):
        assert marquee1._executor.context.events is timeline_manager.shared_events, "Marquee1's events should reference timeline_manager's shared_events"
        assert marquee1._executor.context.defined_sync_events is timeline_manager.shared_sync_events, "Marquee1's defined_sync_events should reference timeline_manager's shared_sync_events"
    
    if hasattr(marquee2, '_executor') and hasattr(marquee2._executor, 'context'):
        assert marquee2._executor.context.events is timeline_manager.shared_events, "Marquee2's events should reference timeline_manager's shared_events"
        assert marquee2._executor.context.defined_sync_events is timeline_manager.shared_sync_events, "Marquee2's defined_sync_events should reference timeline_manager's shared_sync_events"
    
    logger.info("Automatic event sharing test completed successfully")

if __name__ == "__main__":
    main() 