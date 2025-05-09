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
        
        # Create shared event tracking dictionaries
        shared_events = {}
        shared_sync_events = set()
        
        # Create the marquee widgets with the DSL programs
        marquee1 = new_marquee(
            widget=text1,
            program=marquee1_program,
            size=(200, 20),
            position=(20, 10),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        marquee2 = new_marquee(
            widget=text2,
            program=marquee2_program,
            size=(200, 20),
            position=(20, 35),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
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
        
        # Create shared event tracking dictionaries
        shared_events = {}
        shared_sync_events = set()
        
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
        
        # Create the marquee widgets
        marquee1 = new_marquee(
            widget=text1,
            program=marquee1_program,
            size=(200, 20),
            position=(20, 10),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        marquee2 = new_marquee(
            widget=text2,
            program=marquee2_program,
            size=(200, 20),
            position=(20, 35),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        # Initialize all timelines and resolve dependencies
        logger.info("Initializing all marquee timelines")
        new_marquee.initialize_all_timelines()
        
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
        
        # Verify that events are functioning
        assert 'cycle_complete' in shared_events, "SYNC event not created"
        assert len(timeline_manager.sync_events) > 0, "No sync events registered"
        
        logger.info("Test complete")
        # Test ends - assertions verify functionality, no return value needed

    # Run the quick test version
    quick_test_main()

if __name__ == "__main__":
    main() 