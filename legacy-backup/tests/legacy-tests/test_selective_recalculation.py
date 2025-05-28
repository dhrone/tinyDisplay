#!/usr/bin/env python3
"""
Test script for selective timeline recalculation.

This script demonstrates the performance benefits of selectively recalculating
only the affected widgets and their dependents when content changes.
"""

import logging
import time
import sys
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
        logging.FileHandler('selective_recalculation.log')
    ]
)

def main():
    """Run the selective recalculation demonstration."""
    logger = logging.getLogger("test_selective_recalculation")
    logger.info("Starting selective recalculation test")
    
    # Create a test image to render to
    display_width, display_height = 300, 150
    display_image = Image.new("RGBA", (display_width, display_height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(display_image)
    
    try:
        # Create font for text widgets
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        # Create shared event tracking for all widgets
        shared_events = {}
        shared_sync_events = set()
        
        # Create text widgets and marquees with dependencies
        # We'll create a dependency chain: A -> B -> C -> D
        # When A changes, B, C, and D should recalculate
        # When C changes, only C and D should recalculate
        
        # Widget A - Base widget that others depend on
        text_a = text(
            text="Widget A - When I change, all widgets update",
            size=(250, 16),
            font=font,
            color=(255, 255, 255),
        )
        
        # Widget B - Depends on A
        text_b = text(
            text="Widget B - I depend on Widget A",
            size=(250, 16),
            font=font,
            color=(200, 200, 255),
        )
        
        # Widget C - Depends on B
        text_c = text(
            text="Widget C - I depend on Widget B",
            size=(250, 16),
            font=font,
            color=(255, 200, 200),
        )
        
        # Widget D - Depends on C
        text_d = text(
            text="Widget D - I depend on Widget C",
            size=(250, 16),
            font=font,
            color=(200, 255, 200),
        )
        
        # Widget E - Independent widget
        text_e = text(
            text="Widget E - I'm independent",
            size=(250, 16),
            font=font,
            color=(255, 255, 0),
        )
        
        # Create DSL programs with dependencies
        
        # Widget A generates events for B
        marquee_a_program = """
        LOOP(INFINITE) {
            SCROLL_LOOP(LEFT, widget.width) { step=1, interval=1 };
            SYNC(a_complete);  # Signal completion to B
            PAUSE(10);
        } END;
        """
        
        # Widget B waits for A and signals C
        marquee_b_program = """
        LOOP(INFINITE) {
            SCROLL_LOOP(LEFT, widget.width) { step=1, interval=2 };
            WAIT_FOR(a_complete, 50);  # Wait for A
            SYNC(b_complete);  # Signal completion to C
            PAUSE(5);
        } END;
        """
        
        # Widget C waits for B and signals D
        marquee_c_program = """
        LOOP(INFINITE) {
            SCROLL_BOUNCE(LEFT, 100) { step=1, interval=1 };
            WAIT_FOR(b_complete, 50);  # Wait for B
            SYNC(c_complete);  # Signal completion to D
            PAUSE(5);
        } END;
        """
        
        # Widget D waits for C
        marquee_d_program = """
        LOOP(INFINITE) {
            SCROLL_CLIP(LEFT, widget.width) { step=1, interval=1 };
            WAIT_FOR(c_complete, 50);  # Wait for C
            PAUSE(10);
            RESET_POSITION();
        } END;
        """
        
        # Widget E is independent
        marquee_e_program = """
        LOOP(INFINITE) {
            SLIDE(RIGHT, 100) { step=1, interval=1, easing=ease_in_out };
            PAUSE(20);
            SLIDE(LEFT, 100) { step=1, interval=1, easing=ease_in_out };
            PAUSE(20);
        } END;
        """
        
        # Create the marquee widgets
        marquee_a = new_marquee(
            widget=text_a,
            program=marquee_a_program,
            size=(250, 16),
            position=(20, 10),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        marquee_b = new_marquee(
            widget=text_b,
            program=marquee_b_program,
            size=(250, 16),
            position=(20, 36),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        marquee_c = new_marquee(
            widget=text_c,
            program=marquee_c_program,
            size=(250, 16),
            position=(20, 62),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        marquee_d = new_marquee(
            widget=text_d,
            program=marquee_d_program,
            size=(250, 16),
            position=(20, 88),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        marquee_e = new_marquee(
            widget=text_e,
            program=marquee_e_program,
            size=(250, 16),
            position=(20, 114),
            shared_events=shared_events,
            shared_sync_events=shared_sync_events,
        )
        
        # Store all widgets in a list for rendering
        all_marquees = [marquee_a, marquee_b, marquee_c, marquee_d, marquee_e]
        
        # Initialize all timelines
        logger.info("Initializing all timelines")
        new_marquee.initialize_all_timelines()
        
        # Render initial frames to let things stabilize
        logger.info("Rendering initial frames")
        for frame in range(50):
            # Clear display
            draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
            
            # Render all marquees
            for idx, marquee in enumerate(all_marquees):
                img, _ = marquee.render(tick=frame, move=True)
                display_image.paste(img, marquee.position, img)
            
            # Optional: save frames
            if frame % 10 == 0:
                display_image.save(f"initial_frame_{frame:04d}.png")
                logger.info(f"Rendered initial frame {frame}")
                
            time.sleep(0.01)
        
        # Test 1: Change Widget A content - should update A, B, C, D
        logger.info("TEST 1: Changing Widget A - should affect A, B, C, D")
        text_a.text = "Widget A - UPDATED! All widgets should update"
        
        # Time how long it takes to recalculate all dependents
        start_time = time.time()
        
        # Reset just widget A and let automatic dependency tracking handle the rest
        marquee_a.mark_for_recalculation()
        
        # Now compute all timelines (should only recompute A, B, C, D)
        timeline_manager.resolve_timelines()
        
        end_time = time.time()
        logger.info(f"Recalculation after Widget A change took {end_time - start_time:.4f} seconds")
        
        # Render frames showing the update
        logger.info("Rendering frames after Widget A update")
        for frame in range(50, 100):
            # Clear display
            draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
            
            # Render all marquees
            for idx, marquee in enumerate(all_marquees):
                img, _ = marquee.render(tick=frame, move=True)
                display_image.paste(img, marquee.position, img)
            
            if frame % 10 == 0:
                display_image.save(f"a_update_frame_{frame:04d}.png")
                logger.info(f"Rendered A update frame {frame}")
                
            time.sleep(0.01)
        
        # Test 2: Change Widget C content - should only update C and D
        logger.info("TEST 2: Changing Widget C - should only affect C and D")
        text_c.text = "Widget C - UPDATED! Only C and D should update"
        
        # Time how long it takes to recalculate only C and its dependents
        start_time = time.time()
        
        # Reset just widget C
        marquee_c.mark_for_recalculation()
        
        # Now compute all timelines (should only recompute C and D)
        timeline_manager.resolve_timelines()
        
        end_time = time.time()
        logger.info(f"Recalculation after Widget C change took {end_time - start_time:.4f} seconds")
        
        # Render frames showing the update
        logger.info("Rendering frames after Widget C update")
        for frame in range(100, 150):
            # Clear display
            draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
            
            # Render all marquees
            for idx, marquee in enumerate(all_marquees):
                img, _ = marquee.render(tick=frame, move=True)
                display_image.paste(img, marquee.position, img)
            
            if frame % 10 == 0:
                display_image.save(f"c_update_frame_{frame:04d}.png")
                logger.info(f"Rendered C update frame {frame}")
                
            time.sleep(0.01)
        
        # Test 3: Change Widget E content - should only update E (independent)
        logger.info("TEST 3: Changing Widget E - should only affect E")
        text_e.text = "Widget E - UPDATED! Only E should update"
        
        # Time how long it takes to recalculate only E
        start_time = time.time()
        
        # Reset just widget E
        marquee_e.mark_for_recalculation()
        
        # Now compute all timelines (should only recompute E)
        timeline_manager.resolve_timelines()
        
        end_time = time.time()
        logger.info(f"Recalculation after Widget E change took {end_time - start_time:.4f} seconds")
        
        # For comparison, do a full reset of all timelines
        logger.info("TEST 4: Full timeline reset for comparison")
        
        # Time how long it takes to recalculate everything
        start_time = time.time()
        
        # Force reset of all timelines
        new_marquee.reset_all_timelines(force_full_reset=True)
        
        end_time = time.time()
        logger.info(f"Full recalculation of all timelines took {end_time - start_time:.4f} seconds")
        
        # Render final frames
        logger.info("Rendering final frames")
        for frame in range(150, 200):
            # Clear display
            draw.rectangle((0, 0, display_width, display_height), fill=(0, 0, 0, 255))
            
            # Render all marquees
            for idx, marquee in enumerate(all_marquees):
                img, _ = marquee.render(tick=frame, move=True)
                display_image.paste(img, marquee.position, img)
            
            if frame % 10 == 0:
                display_image.save(f"final_frame_{frame:04d}.png")
                logger.info(f"Rendered final frame {frame}")
                
            time.sleep(0.01)
        
        logger.info("Test complete")
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)

def test_selective_recalculation():
    """Pytest-compatible test function that runs a shortened version of the demonstration."""
    logger = logging.getLogger("test_selective_recalculation")
    logger.info("Starting selective recalculation test (pytest mode)")
    
    # Create a test image to render to
    display_width, display_height = 300, 150
    display_image = Image.new("RGBA", (display_width, display_height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(display_image)
    
    # Create font for text widgets
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    # Create shared event tracking for all widgets
    shared_events = {}
    shared_sync_events = set()
    
    # Create shorter text widgets to speed up test
    text_a = text(
        text="Widget A - Base",
        size=(100, 16),
        font=font,
        color=(255, 255, 255),
    )
    
    text_b = text(
        text="Widget B - Depends on A",
        size=(100, 16),
        font=font,
        color=(200, 200, 255),
    )
    
    text_c = text(
        text="Widget C - Depends on B",
        size=(100, 16),
        font=font,
        color=(255, 200, 200),
    )
    
    # Create simpler DSL programs for faster execution
    marquee_a_program = """
    MOVE(RIGHT, 50) { step=2, interval=1 };
    SYNC(a_complete);
    """
    
    marquee_b_program = """
    WAIT_FOR(a_complete, 10);
    SYNC(b_complete);
    MOVE(LEFT, 50) { step=2, interval=1 };
    """
    
    marquee_c_program = """
    WAIT_FOR(b_complete, 10);
    MOVE(RIGHT, 30) { step=2, interval=1 };
    """
    
    # Create the marquee widgets
    marquee_a = new_marquee(
        widget=text_a,
        program=marquee_a_program,
        size=(100, 16),
        position=(20, 10),
        shared_events=shared_events,
        shared_sync_events=shared_sync_events,
    )
    
    marquee_b = new_marquee(
        widget=text_b,
        program=marquee_b_program,
        size=(100, 16),
        position=(20, 36),
        shared_events=shared_events,
        shared_sync_events=shared_sync_events,
    )
    
    marquee_c = new_marquee(
        widget=text_c,
        program=marquee_c_program,
        size=(100, 16),
        position=(20, 62),
        shared_events=shared_events,
        shared_sync_events=shared_sync_events,
    )
    
    # Store all widgets in a list for rendering
    all_marquees = [marquee_a, marquee_b, marquee_c]
    
    # Initialize all timelines
    logger.info("Initializing all timelines")
    new_marquee.initialize_all_timelines()
    
    # Render a few frames
    for frame in range(10):
        for marquee in all_marquees:
            marquee.render(tick=frame, move=True)
    
    # Test 1: Change Widget A content - should update A, B, C
    logger.info("TEST 1: Changing Widget A - should affect A, B, C")
    text_a.text = "Widget A - Updated"
    
    # Store the initial resolved state
    pre_update_resolved = set(timeline_manager.resolved)
    
    # Reset just widget A and let automatic dependency tracking handle the rest
    marquee_a.mark_for_recalculation()
    assert marquee_a._widget_id not in timeline_manager.resolved, "Widget A should be marked for recalculation"
    
    # Now compute all timelines (should only recompute A, B, C)
    timeline_manager.resolve_timelines()
    
    # Render a few frames with the updated content
    for frame in range(10, 20):
        for marquee in all_marquees:
            marquee.render(tick=frame, move=True)
    
    # Test 2: Change Widget C content - should only update C
    logger.info("TEST 2: Changing Widget C - should only affect C")
    text_c.text = "Widget C - Updated"
    
    # Reset just widget C
    marquee_c.mark_for_recalculation()
    
    # Store IDs before recalculation
    initial_c_widget_id = marquee_c._widget_id
    
    # Verify widget C is marked for recalculation but not A or B
    assert initial_c_widget_id not in timeline_manager.resolved, "Widget C should be marked for recalculation"
    assert marquee_a._widget_id in timeline_manager.resolved, "Widget A should not be affected"
    assert marquee_b._widget_id in timeline_manager.resolved, "Widget B should not be affected"
    
    # Now compute all timelines (should only recompute C)
    timeline_manager.resolve_timelines()
    
    # All widgets should be resolved now
    assert len(timeline_manager.resolved) == 3, "All widgets should be resolved"
    
    logger.info("Selective recalculation test complete")
    # No return statement - test relies on assertions

if __name__ == "__main__":
    main() 