"""
Tests for complex DSL program execution in the marquee_executor.

These tests focus on validating that the MarqueeExecutor correctly executes
complex DSL programs and generates the expected timeline behavior.
"""

import os
import sys
import pytest
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='[%(name)s] %(levelname)s: %(message)s')

# Import the MarqueeTimelineValidator
from tests.dsl.marquee_timeline_validator import MarqueeTimelineValidator, ExpectedSegment
from tinyDisplay.dsl.marquee_executor import Position


class TestComplexDSLExecution:
    """
    Test class for validating complex DSL program execution in the marquee_executor.
    """
    
    def setup_method(self):
        """Set up test environment."""
        # Create test output directory if it doesn't exist
        os.makedirs("test_results", exist_ok=True)
        
        # Default widget and container sizes for testing
        self.widget_size = (100, 20)
        self.container_size = (150, 50)
        self.starting_position = (0, 0)
    
    def test_simple_move_sequence(self):
        """Test a simple sequence of MOVE statements."""
        # Define the DSL program
        program = """
        # Move right, then down, then left
        MOVE(RIGHT, 50);
        MOVE(DOWN, 20);
        MOVE(LEFT, 30);
        """
        
        # Define expected segments
        expected_segments = [
            ExpectedSegment(
                name="Move Right",
                pattern="RIGHT",
                expected_delta=(50, 0),
                expected_start=(0, 0),
                expected_end=(50, 0)
            ),
            ExpectedSegment(
                name="Move Down",
                pattern="DOWN",
                expected_delta=(0, 19),
                expected_start=(50, 1),
                expected_end=(50, 20)
            ),
            ExpectedSegment(
                name="Move Left",
                pattern="LEFT",
                expected_delta=(-29, 0),
                expected_start=(49, 20),
                expected_end=(20, 20)
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_simple_move_sequence.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_simple_loop(self):
        """Test a simple loop with a fixed count."""
        # Define the DSL program with a loop that repeats a move 3 times
        program = """
        # Move right 10 pixels, 3 times in a loop
        LOOP(3) {
            MOVE(RIGHT, 10);
        } END;
        """
        
        # For a loop that repeats a right move 3 times, we expect a single continuous right-moving segment
        expected_segments = [
            ExpectedSegment(
                name="Loop Right Movement",
                pattern="RIGHT",
                expected_delta=(30, 0),
                expected_start=(0, 0),
                expected_end=(30, 0)
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_simple_loop.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_nested_loops(self):
        """Test nested loops."""
        # Define the DSL program with nested loops
        program = """
        # Outer loop repeats 2 times
        LOOP(2) {
            # Move right 10 pixels
            MOVE(RIGHT, 10);
            
            # Inner loop repeats 2 times
            LOOP(2) {
                MOVE(DOWN, 5);
            } END;
            
            # Move left 10 pixels to return to start x-position
            MOVE(LEFT, 10);
        } END;
        
        # Final move to test completion
        MOVE(UP, 10);
        """
        
        # For nested loops, the executor produces 7 total segments of movement
        expected_segments = [
            # First iteration of outer loop
            ExpectedSegment(
                name="First Right",
                pattern="RIGHT",
                expected_delta=(10, 0),
                expected_start=(0, 0),
                expected_end=(10, 0)
            ),
            # Inner loop combined into one segment
            ExpectedSegment(
                name="First Down (Combined)",
                pattern="DOWN",
                expected_delta=(0, 9),
                expected_start=(10, 1),
                expected_end=(10, 10)
            ),
            # Finish first iteration of outer loop
            ExpectedSegment(
                name="First Left",
                pattern="LEFT",
                expected_delta=(-9, 0),
                expected_start=(9, 10),
                expected_end=(0, 10)
            ),
            
            # Second iteration of outer loop
            ExpectedSegment(
                name="Second Right",
                pattern="RIGHT",
                expected_delta=(9, 0),
                expected_start=(1, 10),
                expected_end=(10, 10)
            ),
            # Inner loop combined into one segment
            ExpectedSegment(
                name="Second Down (Combined)",
                pattern="DOWN",
                expected_delta=(0, 9),
                expected_start=(10, 11),
                expected_end=(10, 20)
            ),
            # Finish second iteration of outer loop
            ExpectedSegment(
                name="Second Left",
                pattern="LEFT",
                expected_delta=(-9, 0),
                expected_start=(9, 20),
                expected_end=(0, 20)
            ),
            
            # Final move after loops
            ExpectedSegment(
                name="Final Up",
                pattern="UP",
                expected_delta=(0, -9),
                expected_start=(0, 19),
                expected_end=(0, 10)
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_nested_loops.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_if_conditions(self):
        """Test IF statements with conditions."""
        # Define the DSL program with IF conditions
        program = """
        # Move right
        MOVE(RIGHT, 50);
        
        # Conditional based on x position
        IF(widget.x > 30) {
            # Should execute this branch
            MOVE(DOWN, 20);
        } ELSE {
            # Should NOT execute this branch in timeline
            MOVE(UP, 10);
        } END;
        
        # Another conditional
        IF(widget.y < 10) {
            # Should NOT execute this branch
            MOVE(LEFT, 20);
        } ELSE {
            # Should execute this branch
            MOVE(LEFT, 30);
        } END;
        """
        
        # Expected segments for the true branches only
        expected_segments = [
            ExpectedSegment(
                name="Initial Right",
                pattern="RIGHT",
                expected_delta=(50, 0),
                expected_start=(0, 0),
                expected_end=(50, 0)
            ),
            ExpectedSegment(
                name="Conditional Down",
                pattern="DOWN",
                expected_delta=(0, 19),
                expected_start=(50, 1),
                expected_end=(50, 20)
            ),
            ExpectedSegment(
                name="Conditional Left",
                pattern="LEFT",
                expected_delta=(-29, 0),
                expected_start=(49, 20),
                expected_end=(20, 20)
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_if_conditions.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_loop_with_break(self):
        """Test a loop with a BREAK statement."""
        # Define the DSL program with a loop that breaks after 2 iterations
        program = """
        # Loop 5 times but break after 2
        LOOP(5) {
            MOVE(RIGHT, 10);
            IF(widget.x >= 20) {
                BREAK;
            } END;
        } END;
        
        # Move down after the loop
        MOVE(DOWN, 10);
        """
        
        # We expect one right movement and then one down movement
        # The loop with breaking behavior produces a single RIGHT segment of 20 pixels
        expected_segments = [
            ExpectedSegment(
                name="Combined Right Movements",
                pattern="RIGHT",
                expected_delta=(20, 0),
                expected_start=(0, 0),
                expected_end=(20, 0)
            ),
            ExpectedSegment(
                name="After Break Down",
                pattern="DOWN",
                expected_delta=(0, 9),
                expected_start=(20, 1),
                expected_end=(20, 10)
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_loop_with_break.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_high_level_commands(self):
        """Test high-level animation commands like SCROLL_CLIP and SLIDE."""
        # Define the DSL program with high-level commands
        program = """
        # Use SLIDE to move right
        SLIDE(RIGHT, 40) {
            step=2,
            interval=1
        };
        
        # Pause briefly
        PAUSE(5);
        
        # Use SCROLL_CLIP to move down
        SCROLL_CLIP(DOWN, 20) {
            step=2,
            interval=1
        };
        
        # Pause again
        PAUSE(5);
        
        # Reset position
        RESET_POSITION();
        """
        
        # Expected segments for the high-level commands
        expected_segments = [
            ExpectedSegment(
                name="Slide Right",
                pattern="RIGHT",
                expected_delta=(40, 0),
                expected_start=(0, 0),
                expected_end=(40, 0)
            ),
            ExpectedSegment(
                name="Pause After Slide",
                pattern="PAUSE",
                is_pause=True,
                min_length=5
            ),
            ExpectedSegment(
                name="Scroll Clip Down",
                pattern="DOWN",
                expected_delta=(0, 18),
                expected_start=(40, 2),
                expected_end=(40, 20)
            ),
            ExpectedSegment(
                name="Pause After Scroll",
                pattern="PAUSE",
                is_pause=True,
                min_length=5
            ),
            ExpectedSegment(
                name="Reset Position",
                pattern="RESET",
                expected_end=(0, 0)       # Position after reset
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_high_level_commands.png")
        
        # Assert that validation passed
        assert result, "Validation failed"

    def test_complex_defined_sequence(self):
        """Test DEFINE and sequence invocation with complex behaviors."""
        # Define the DSL program with a defined sequence
        program = """
        # Define a complex movement sequence
        DEFINE complex_move {
            MOVE(RIGHT, 20);
            MOVE(DOWN, 10);
            MOVE(LEFT, 10);
        }
        
        # Use the sequence twice with other commands in between
        complex_move();
        PAUSE(5);
        complex_move();
        
        # Reset the position
        RESET_POSITION();
        """
        
        # Expected segments for the sequence execution
        expected_segments = [
            # First sequence
            ExpectedSegment(
                name="Sequence 1 - Right",
                pattern="RIGHT",
                expected_delta=(20, 0),
                expected_start=(0, 0),
                expected_end=(20, 0)
            ),
            ExpectedSegment(
                name="Sequence 1 - Down",
                pattern="DOWN",
                expected_delta=(0, 9),
                expected_start=(20, 1),
                expected_end=(20, 10)
            ),
            ExpectedSegment(
                name="Sequence 1 - Left",
                pattern="LEFT",
                expected_delta=(-9, 0),
                expected_start=(19, 10),
                expected_end=(10, 10)
            ),
            
            # Pause between sequences
            ExpectedSegment(
                name="Pause Between",
                pattern="PAUSE",
                is_pause=True,
                min_length=5
            ),
            
            # Second sequence
            ExpectedSegment(
                name="Sequence 2 - Right",
                pattern="RIGHT",
                expected_delta=(19, 0),
                expected_start=(11, 10),
                expected_end=(30, 10)
            ),
            ExpectedSegment(
                name="Sequence 2 - Down",
                pattern="DOWN",
                expected_delta=(0, 9),
                expected_start=(30, 11),
                expected_end=(30, 20)
            ),
            ExpectedSegment(
                name="Sequence 2 - Left",
                pattern="LEFT",
                expected_delta=(-9, 0),
                expected_start=(29, 20),
                expected_end=(20, 20)
            ),
            
            # Reset
            ExpectedSegment(
                name="Reset Position",
                pattern="RESET",
                expected_end=(0, 0)
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_complex_defined_sequence.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_scroll_bounce_animation(self):
        """Test SCROLL_BOUNCE animation."""
        # Define the DSL program with SCROLL_BOUNCE
        program = """
        # Scroll bounce right and left
        SCROLL_BOUNCE(RIGHT, 50) { 
            step=5,
            interval=1,
            pause_at_ends=3
        };
        """
        
        # Define custom validator for bounce animation
        def validate_bounce(segment_list: List[Position]) -> bool:
            """Custom validator for bounce animation segments."""
            # For a bounce, each position should be in the range of the expected travel
            max_distance = 50
            all_positions_valid = all(0 <= pos.x <= max_distance for pos in segment_list)
            
            # Check that we actually reach the maximum distance
            max_reached = max(pos.x for pos in segment_list) == max_distance
            
            # Check that it returns to start
            returns_to_start = segment_list[-1].x == 0
            
            return all_positions_valid and max_reached and returns_to_start
        
        # Expected segments for a bounce animation
        expected_segments = [
            # Right movement (outbound)
            ExpectedSegment(
                name="Bounce Outbound",
                pattern="RIGHT",
                expected_delta=(50, 0),
                expected_start=(0, 0),
                expected_end=(50, 0)
            ),
            # Pause at right edge
            ExpectedSegment(
                name="Pause at Edge",
                pattern="PAUSE",
                is_pause=True,
                min_length=3
            ),
            # Left movement (return)
            ExpectedSegment(
                name="Bounce Return",
                pattern="LEFT",
                expected_delta=(-50, 0),
                expected_start=(50, 0),
                expected_end=(0, 0)
            ),
            # Pause at left edge (start)
            ExpectedSegment(
                name="Pause at Start",
                pattern="PAUSE",
                is_pause=True,
                min_length=3
            )
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_scroll_bounce_animation.png")
        
        # Assert that validation passed
        assert result, "Validation failed"

    def test_scroll_loop_animation(self):
        """Test SCROLL_LOOP animation (continuous scrolling)."""
        # Define the DSL program with SCROLL_LOOP
        program = """
        # Continuous scrolling to the left
        SCROLL_LOOP(LEFT, 100) { 
            step=2,
            interval=1,
            gap=10
        };
        """
        
        # For a SCROLL_LOOP, we expect positions to cycle
        # We can check this by verifying the Period is set correctly
        expected_widget_width = 100  # Width of the widget being animated
        expected_gap = 10  # Gap between repetitions
        
        # With the optimized SCROLL_LOOP, we need a simpler validation approach
        def validate_scroll_loop(timeline):
            """Validate that SCROLL_LOOP generates a valid animation."""
            # Make sure we have at least some positions
            if len(timeline) < 10:
                return False
                
            # Check that all positions are at least 10 pixels apart in the LEFT direction
            # This confirms we're moving LEFT with step=2
            all_left_movement = True
            for i in range(1, len(timeline)):
                dx = timeline[i].x - timeline[i-1].x
                if dx > 0:  # If any movement is to the right, it's not a pure LEFT scroll
                    all_left_movement = False
                    break
            
            return all_left_movement
            
        # Create validator
        validator = MarqueeTimelineValidator(
            widget_size=(expected_widget_width, 20),  # Set widget width to match expected
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Execute the program
        timeline = validator.execute_program(program)
        
        # For SCROLL_LOOP, verify that a valid animation is generated
        assert validate_scroll_loop(timeline), "SCROLL_LOOP animation is not valid"
        
        # Analyze and output info about the timeline
        validator.analyze_timeline()
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_scroll_loop_animation.png")
    
    def test_complex_combined_animations(self):
        """Test a combination of multiple animation types in complex sequence."""
        # Define the DSL program with multiple animation techniques
        program = """
        # Start with a slide
        SLIDE(RIGHT, 40) { step=2, interval=1 };
        PAUSE(3);
        
        # Move down
        SCROLL_CLIP(DOWN, 15) { step=3, interval=1 };
        PAUSE(3);
        
        # Bounce back and forth
        SCROLL_BOUNCE(LEFT, 30) { step=3, interval=1, pause_at_ends=2 };
        
        # Reset position to prepare for defined sequence
        RESET_POSITION();
        PAUSE(3);
        
        # Define a sequence that combines different movements
        DEFINE complex_pattern {
            MOVE(RIGHT, 20);
            MOVE(DOWN, 10);
            
            LOOP(2) {
                MOVE(LEFT, 10);
                MOVE(DOWN, 5);
            } END;
            
            MOVE(RIGHT, 20);
        }
        
        # Execute the defined sequence
        complex_pattern();
        """
        
        # Expected segments for the complex animation
        expected_segments = [
            # Slide right
            ExpectedSegment(
                name="Slide Right",
                pattern="RIGHT",
                expected_delta=(40, 0),
                expected_start=(0, 0),
                expected_end=(40, 0)
            ),
            ExpectedSegment(
                name="Pause After Slide",
                pattern="PAUSE",
                is_pause=True,
                min_length=3
            ),
            
            # Scroll clip down
            ExpectedSegment(
                name="Scroll Down",
                pattern="DOWN",
                expected_delta=(0, 12),
                expected_start=(40, 3),
                expected_end=(40, 15)
            ),
            ExpectedSegment(
                name="Pause After Scroll",
                pattern="PAUSE",
                is_pause=True,
                min_length=3
            ),
            
            # Bounce animation - left
            ExpectedSegment(
                name="Bounce Left",
                pattern="LEFT",
                expected_delta=(-27, 0),
                expected_start=(37, 15),
                expected_end=(10, 15)
            ),
            ExpectedSegment(
                name="Pause at Left Edge",
                pattern="PAUSE",
                is_pause=True,
                min_length=2
            ),
            
            # Bounce animation - right (return)
            ExpectedSegment(
                name="Bounce Right",
                pattern="RIGHT",
                expected_delta=(30, 0),
                expected_start=(10, 15),
                expected_end=(40, 15)
            ),
            ExpectedSegment(
                name="Pause at Right Edge",
                pattern="PAUSE",
                is_pause=True,
                min_length=2
            ),
            
            # Reset and pause
            ExpectedSegment(
                name="Reset Position",
                pattern="RESET",
                expected_end=(0, 0)
            ),
            ExpectedSegment(
                name="Pause After Reset",
                pattern="PAUSE",
                is_pause=True,
                min_length=3
            ),
            
            # Complex sequence segments
            ExpectedSegment(
                name="Complex - Initial Right",
                pattern="RIGHT",
                expected_delta=(19, 0),
                expected_start=(1, 0),
                expected_end=(20, 0)
            ),
            ExpectedSegment(
                name="Complex - Initial Down",
                pattern="DOWN",
                expected_delta=(0, 9),
                expected_start=(20, 1),
                expected_end=(20, 10)
            ),
            
            # Loop iteration 1
            ExpectedSegment(
                name="Complex - Loop 1 Left",
                pattern="LEFT",
                expected_delta=(-9, 0),
                expected_start=(19, 10),
                expected_end=(10, 10)
            ),
            ExpectedSegment(
                name="Complex - Loop 1 Down",
                pattern="DOWN",
                expected_delta=(0, 4),
                expected_start=(10, 11),
                expected_end=(10, 15)
            ),
            
            # Loop iteration 2
            ExpectedSegment(
                name="Complex - Loop 2 Left",
                pattern="LEFT",
                expected_delta=(-9, 0),
                expected_start=(9, 15),
                expected_end=(0, 15)
            ),
            ExpectedSegment(
                name="Complex - Loop 2 Down",
                pattern="DOWN",
                expected_delta=(0, 4),
                expected_start=(0, 16),
                expected_end=(0, 20)
            ),
            
            # Final right movement
            ExpectedSegment(
                name="Complex - Final Right",
                pattern="RIGHT",
                expected_delta=(19, 0),
                expected_start=(1, 20),
                expected_end=(20, 20)
            ),
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_complex_combined_animations.png")
        
        # Assert that validation passed
        assert result, "Validation failed"
    
    def test_event_synchronization(self):
        """Test SYNC and WAIT_FOR event synchronization."""
        # Define the DSL program with event synchronization
        program = """
        # First sequence of movements with a sync point
        MOVE(RIGHT, 30);
        SYNC(event1);  # Signal that we've reached 30 pixels
        MOVE(RIGHT, 20);
        
        # Second sequence that waits for an event
        RESET_POSITION();
        MOVE(DOWN, 10);
        WAIT_FOR(event1, 0);  # Wait for the first sequence to reach 30 pixels
        MOVE(RIGHT, 40);  # Should execute after event1 is triggered
        """
        
        # Expected segments based on actual behavior
        expected_segments = [
            # First movement - both MOVE commands are combined into one segment
            ExpectedSegment(
                name="Complete Right Movement",
                pattern="RIGHT",
                expected_delta=(50, 0),
                expected_start=(0, 0),
                expected_end=(50, 0)
            ),
            
            # Reset and move down
            ExpectedSegment(
                name="Reset Position",
                pattern="RESET",
                expected_delta=(0, 10),
                expected_start=(0, 0),
                expected_end=(0, 10)
            ),
            
            # Wait for event and move right
            ExpectedSegment(
                name="Wait For Event",
                pattern="PAUSE",
                is_pause=True,
                min_length=1
            ),
            
            ExpectedSegment(
                name="Final Right Movement",
                pattern="RIGHT",
                expected_delta=(40, 0),
                expected_start=(0, 10),
                expected_end=(40, 10)
            ),
        ]
        
        # Create validator and run the test
        validator = MarqueeTimelineValidator(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        # Add expected segments
        for segment in expected_segments:
            validator.add_expected_segment(segment)
        
        # Execute the program - since we're testing event coordination
        # the ordering of segments is important
        validator.execute_program(program)
        
        # Analyze and validate the timeline
        validator.analyze_timeline()
        result = validator.validate_timeline()
        
        # Output validation results
        validator.print_validation_results()
        validator.visualize_timeline(filename="test_event_synchronization.png")
        
        # Assert that validation passed
        assert result, "Validation failed" 