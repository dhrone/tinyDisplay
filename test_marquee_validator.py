#!/usr/bin/env python3
"""
Marquee Timeline Validator

This module provides a class for testing the marquee_executor by validating
that it generates expected timeline behaviors for DSL programs.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple, Optional, Union, Callable
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.render.widget import text
from tinyDisplay.render.new_marquee import new_marquee
from tinyDisplay.dsl.marquee_executor import MarqueeExecutor, Position

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='[%(name)s] %(levelname)s: %(message)s')

@dataclass
class ExpectedSegment:
    """Defines expectations for a segment of a timeline."""
    name: str  # Name/description of the segment
    # Pattern can be a string like "RIGHT", "LEFT", "PAUSE", etc.
    pattern: str
    # Minimum number of positions in this segment
    min_length: int = 1
    # Optional expected exact length
    exact_length: Optional[int] = None
    # Expected position change (dx, dy) over the segment
    expected_delta: Optional[Tuple[int, int]] = None
    # Expected start position (x, y) for the segment
    expected_start: Optional[Tuple[int, int]] = None
    # Expected end position (x, y) for the segment
    expected_end: Optional[Tuple[int, int]] = None
    # For pauses: is this a pause segment?
    is_pause: bool = False
    # Custom validation function
    custom_validator: Optional[Callable[[List[Position]], bool]] = None

class MarqueeTimelineValidator:
    """
    Helper class for testing the MarqueeExecutor.
    
    This class allows specifying expected behaviors for a DSL program
    and verifying that the executor generates a timeline that meets
    those expectations.
    """
    
    def __init__(self, widget_size: Tuple[int, int] = (100, 20), 
                 container_size: Tuple[int, int] = (150, 50),
                 starting_position: Tuple[int, int] = (0, 0),
                 debug: bool = False):
        """
        Initialize the timeline validator.
        
        Args:
            widget_size: Size of the widget being animated
            container_size: Size of the container
            starting_position: Initial position for the timeline
            debug: Whether to enable debug logging
        """
        self.logger = logging.getLogger("MarqueeTimelineValidator")
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
            
        self.widget_size = widget_size
        self.container_size = container_size
        self.starting_position = starting_position
        self.debug = debug
        
        # Initialize the expected segments
        self.expected_segments = []
        
        # Reset test results
        self.reset_results()
    
    def reset_results(self):
        """Reset the test results."""
        self.actual_segments = []
        self.test_passed = False
        self.validation_errors = []
        self.timeline = None
    
    def add_expected_segment(self, segment: ExpectedSegment):
        """
        Add an expected segment to the validation list.
        
        Args:
            segment: The expected segment
        """
        self.expected_segments.append(segment)
        self.logger.debug(f"Added expected segment: {segment.name} ({segment.pattern})")
    
    def execute_program(self, program: str, 
                        variables: Optional[Dict[str, Any]] = None) -> List[Position]:
        """
        Execute a DSL program and return the timeline.
        
        Args:
            program: The DSL program to execute
            variables: Optional initial variables
            
        Returns:
            The generated timeline as a list of Positions
        """
        # Create the executor
        executor = MarqueeExecutor(program, initial_variables=variables)
        
        # Execute the program to generate a timeline
        self.timeline = executor.execute(
            widget_size=self.widget_size,
            container_size=self.container_size,
            starting_position=self.starting_position
        )
        
        self.logger.debug(f"Generated timeline with {len(self.timeline)} positions")
        return self.timeline
    
    def analyze_timeline(self, timeline: Optional[List[Position]] = None) -> List[List[Position]]:
        """
        Analyze a timeline and divide it into logical segments.
        
        Args:
            timeline: The timeline to analyze (uses the last executed timeline if None)
            
        Returns:
            A list of segments, where each segment is a list of positions
        """
        if timeline is None:
            if self.timeline is None:
                raise ValueError("No timeline to analyze. Call execute_program first or provide a timeline.")
            timeline = self.timeline
        
        # Segment the timeline based on movement patterns and pauses
        segments = []
        current_segment = []
        
        for i, pos in enumerate(timeline):
            # Start a new segment?
            is_new_segment = False
            
            # Always start a segment at the beginning
            if i == 0:
                current_segment.append(pos)
                continue
                
            prev_pos = timeline[i-1]
            
            # Check for pause transitions
            is_pause = hasattr(pos, 'pause') and pos.pause
            was_pause = hasattr(prev_pos, 'pause') and prev_pos.pause
            if is_pause != was_pause:
                is_new_segment = True
            
            # Check for position resets
            if (pos.x == 0 and pos.y == 0) and (prev_pos.x != 0 or prev_pos.y != 0):
                is_new_segment = True
            
            # Check for direction changes
            if len(current_segment) > 1:
                second_last = timeline[i-2]
                prev_dx = prev_pos.x - second_last.x
                prev_dy = prev_pos.y - second_last.y
                
                curr_dx = pos.x - prev_pos.x
                curr_dy = pos.y - prev_pos.y
                
                # Direction change?
                if ((prev_dx > 0 and curr_dx < 0) or (prev_dx < 0 and curr_dx > 0) or
                    (prev_dy > 0 and curr_dy < 0) or (prev_dy < 0 and curr_dy > 0) or
                    (prev_dx != 0 and curr_dx == 0) or (prev_dy != 0 and curr_dy == 0) or
                    (prev_dx == 0 and curr_dx != 0) or (prev_dy == 0 and curr_dy != 0)):
                    is_new_segment = True
            
            # Check for terminal positions
            if hasattr(pos, 'terminal') and pos.terminal:
                is_new_segment = True
            
            # Start a new segment or add to current
            if is_new_segment and current_segment:
                segments.append(current_segment)
                current_segment = [pos]  # Start with this position
            else:
                current_segment.append(pos)
        
        # Add the last segment if not empty
        if current_segment:
            segments.append(current_segment)
            
        self.actual_segments = segments
        self.logger.debug(f"Timeline divided into {len(segments)} segments")
        return segments
    
    def categorize_segment(self, segment: List[Position]) -> str:
        """
        Categorize a segment based on its movement pattern.
        
        Args:
            segment: The segment to categorize
            
        Returns:
            A string describing the segment pattern (e.g., "RIGHT", "LEFT", "PAUSE")
        """
        if not segment:
            return "EMPTY"
        
        # Check if this is a pause segment
        if hasattr(segment[0], 'pause') and segment[0].pause:
            return "PAUSE"
        
        # Check if this is a reset segment
        if segment[0].x == 0 and segment[0].y == 0 and len(segment) == 1:
            return "RESET"
        
        # Analyze movement direction
        if len(segment) < 2:
            return "SINGLE_POSITION"
        
        # Calculate overall movement
        start_pos = segment[0]
        end_pos = segment[-1]
        dx = end_pos.x - start_pos.x
        dy = end_pos.y - start_pos.y
        
        # Check dominant direction
        if abs(dx) > abs(dy):
            # Horizontal movement
            if dx > 0:
                return "RIGHT"
            else:
                return "LEFT"
        elif abs(dy) > abs(dx):
            # Vertical movement
            if dy > 0:
                return "DOWN"
            else:
                return "UP"
        elif dx == 0 and dy == 0:
            return "STATIC"
        else:
            # Diagonal movement
            if dx > 0 and dy > 0:
                return "DOWN_RIGHT"
            elif dx > 0 and dy < 0:
                return "UP_RIGHT"
            elif dx < 0 and dy > 0:
                return "DOWN_LEFT"
            else:
                return "UP_LEFT"
    
    def validate_timeline(self) -> bool:
        """
        Validate the timeline against expected segments.
        
        Returns:
            True if validation passes, False otherwise
        """
        if not self.timeline:
            self.validation_errors.append("No timeline to validate")
            return False
            
        # Make sure we have segments
        if not self.actual_segments:
            self.analyze_timeline()
            
        # Check if we have the expected number of segments
        if len(self.expected_segments) > len(self.actual_segments):
            self.validation_errors.append(
                f"Expected at least {len(self.expected_segments)} segments, "
                f"but found only {len(self.actual_segments)}"
            )
            self.logger.warning(
                f"Not enough segments: expected {len(self.expected_segments)}, "
                f"found {len(self.actual_segments)}"
            )
        
        # Validate each expected segment against actual segments
        num_segments_to_check = min(len(self.expected_segments), len(self.actual_segments))
        
        for i in range(num_segments_to_check):
            expected = self.expected_segments[i]
            actual = self.actual_segments[i]
            
            # Get the pattern for this segment
            actual_pattern = self.categorize_segment(actual)
            
            # Check if the patterns match
            if expected.pattern != actual_pattern:
                self.validation_errors.append(
                    f"Segment {i+1} ({expected.name}): Expected pattern '{expected.pattern}', "
                    f"but found '{actual_pattern}'"
                )
                continue
            
            # Check the segment length
            if expected.exact_length is not None and len(actual) != expected.exact_length:
                self.validation_errors.append(
                    f"Segment {i+1} ({expected.name}): Expected exactly {expected.exact_length} positions, "
                    f"but found {len(actual)}"
                )
            elif len(actual) < expected.min_length:
                self.validation_errors.append(
                    f"Segment {i+1} ({expected.name}): Expected at least {expected.min_length} positions, "
                    f"but found {len(actual)}"
                )
            
            # Check start position if specified
            if expected.expected_start is not None:
                start_x, start_y = expected.expected_start
                if actual[0].x != start_x or actual[0].y != start_y:
                    self.validation_errors.append(
                        f"Segment {i+1} ({expected.name}): Expected start position ({start_x}, {start_y}), "
                        f"but found ({actual[0].x}, {actual[0].y})"
                    )
            
            # Check end position if specified
            if expected.expected_end is not None:
                end_x, end_y = expected.expected_end
                if actual[-1].x != end_x or actual[-1].y != end_y:
                    self.validation_errors.append(
                        f"Segment {i+1} ({expected.name}): Expected end position ({end_x}, {end_y}), "
                        f"but found ({actual[-1].x}, {actual[-1].y})"
                    )
            
            # Check position delta if specified
            if expected.expected_delta is not None:
                expected_dx, expected_dy = expected.expected_delta
                actual_dx = actual[-1].x - actual[0].x
                actual_dy = actual[-1].y - actual[0].y
                
                if actual_dx != expected_dx or actual_dy != expected_dy:
                    self.validation_errors.append(
                        f"Segment {i+1} ({expected.name}): Expected position delta ({expected_dx}, {expected_dy}), "
                        f"but found ({actual_dx}, {actual_dy})"
                    )
            
            # Check pause property if applicable
            if expected.is_pause:
                for pos in actual:
                    if not (hasattr(pos, 'pause') and pos.pause):
                        self.validation_errors.append(
                            f"Segment {i+1} ({expected.name}): Expected all positions to be pauses, "
                            f"but found non-pause positions"
                        )
                        break
            
            # Apply custom validator if provided
            if expected.custom_validator is not None:
                if not expected.custom_validator(actual):
                    self.validation_errors.append(
                        f"Segment {i+1} ({expected.name}): Custom validation failed"
                    )
        
        # If we have more expected segments than actual, report those as errors
        for i in range(num_segments_to_check, len(self.expected_segments)):
            expected = self.expected_segments[i]
            self.validation_errors.append(
                f"Missing expected segment {i+1} ({expected.name}): {expected.pattern}"
            )
        
        # If no validation errors, test passes
        self.test_passed = len(self.validation_errors) == 0
        
        return self.test_passed
    
    def print_validation_results(self):
        """Print detailed results of the validation."""
        if self.test_passed:
            self.logger.info("Validation PASSED: All timeline behaviors match expectations")
        else:
            self.logger.warning("Validation FAILED: Timeline doesn't match expectations")
            for error in self.validation_errors:
                self.logger.warning(f"- {error}")
        
        # Print segment details
        self.logger.info("\nTimeline Segment Analysis:")
        for i, segment in enumerate(self.actual_segments):
            if not segment:
                self.logger.info(f"  Segment {i+1}: EMPTY")
                continue
                
            start_pos = segment[0]
            end_pos = segment[-1]
            movement = self.categorize_segment(segment)
            
            # Calculate movement delta
            dx = end_pos.x - start_pos.x
            dy = end_pos.y - start_pos.y
            
            self.logger.info(
                f"  Segment {i+1}: {movement}, Length: {len(segment)}, "
                f"Start: ({start_pos.x}, {start_pos.y}), End: ({end_pos.x}, {end_pos.y}), "
                f"Delta: ({dx}, {dy})"
            )
    
    def visualize_timeline(self, output_dir: str = "test_results", 
                          filename: str = "timeline_visualization.png"):
        """
        Generate a visualization of the timeline.
        
        Args:
            output_dir: Directory to save the visualization
            filename: Filename for the visualization
        """
        if not self.timeline:
            self.logger.warning("No timeline to visualize")
            return
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine the bounds of the timeline
        min_x = min(pos.x for pos in self.timeline)
        max_x = max(pos.x for pos in self.timeline)
        min_y = min(pos.y for pos in self.timeline)
        max_y = max(pos.y for pos in self.timeline)
        
        # Add some padding
        padding = 20
        canvas_width = max(max_x - min_x + 1, self.widget_size[0]) + padding * 2
        canvas_height = max(max_y - min_y + 1, self.widget_size[1]) + padding * 2
        
        # Create a canvas
        canvas = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        
        # Draw a grid for reference
        grid_color = (30, 30, 30)
        grid_spacing = 10
        for x in range(0, canvas_width, grid_spacing):
            draw.line([(x, 0), (x, canvas_height)], fill=grid_color)
        for y in range(0, canvas_height, grid_spacing):
            draw.line([(0, y), (canvas_width, y)], fill=grid_color)
        
        # Draw origin marker
        origin_x = padding - min_x
        origin_y = padding - min_y
        draw.rectangle(
            [(origin_x-3, origin_y-3), (origin_x+3, origin_y+3)],
            outline=(100, 100, 100),
            fill=(50, 50, 50)
        )
        
        # Draw positions in the timeline
        line_points = []
        for i, pos in enumerate(self.timeline):
            # Convert to canvas coordinates
            x = padding + pos.x - min_x
            y = padding + pos.y - min_y
            
            # Add to the line
            line_points.append((x, y))
            
            # Draw position dot
            color = (0, 255, 0)  # Green for normal positions
            
            # Different colors for different position types
            if hasattr(pos, 'pause') and pos.pause:
                color = (0, 0, 255)  # Blue for pauses
            if hasattr(pos, 'terminal') and pos.terminal:
                color = (255, 0, 0)  # Red for terminal positions
            
            # Draw the dot
            draw.ellipse([(x-2, y-2), (x+2, y+2)], fill=color)
            
            # Draw a text label for some key positions
            if i == 0 or i == len(self.timeline) - 1 or i % 10 == 0:
                draw.text((x+5, y-10), str(i), fill=(200, 200, 200))
        
        # Draw line connecting all positions
        if len(line_points) > 1:
            draw.line(line_points, fill=(100, 100, 100), width=1)
        
        # Draw segment boundaries
        if self.actual_segments:
            cumulative_pos = 0
            for segment in self.actual_segments:
                cumulative_pos += len(segment)
                if cumulative_pos < len(self.timeline):
                    # Get the boundary position
                    pos = self.timeline[cumulative_pos]
                    x = padding + pos.x - min_x
                    y = padding + pos.y - min_y
                    
                    # Draw a vertical line at segment boundaries
                    draw.line([(x, 0), (x, canvas_height)], fill=(255, 100, 100), width=1)
        
        # Add a legend
        legend_y = canvas_height - 50
        # Normal position
        draw.ellipse([(10, legend_y), (14, legend_y+4)], fill=(0, 255, 0))
        draw.text((20, legend_y-2), "Normal position", fill=(200, 200, 200))
        
        # Pause position
        draw.ellipse([(10, legend_y+15), (14, legend_y+19)], fill=(0, 0, 255))
        draw.text((20, legend_y+13), "Pause position", fill=(200, 200, 200))
        
        # Terminal position
        draw.ellipse([(10, legend_y+30), (14, legend_y+34)], fill=(255, 0, 0))
        draw.text((20, legend_y+28), "Terminal position", fill=(200, 200, 200))
        
        # Add a title
        draw.text((10, 10), f"Timeline Visualization ({len(self.timeline)} positions, {len(self.actual_segments)} segments)", 
                  fill=(200, 200, 200))
        
        # Save the image
        output_path = os.path.join(output_dir, filename)
        canvas.save(output_path)
        self.logger.info(f"Saved timeline visualization to {output_path}")

def test_program(program_name: str, program: str, 
                expected_segments: List[ExpectedSegment],
                widget_size: Tuple[int, int] = (100, 20),
                container_size: Tuple[int, int] = (150, 50),
                starting_position: Tuple[int, int] = (0, 0),
                debug: bool = False,
                visualize: bool = True) -> bool:
    """
    Test a DSL program against expected segments.
    
    Args:
        program_name: Name of the test program
        program: The DSL program to test
        expected_segments: List of expected segments
        widget_size: Size of the widget
        container_size: Size of the container
        starting_position: Initial position
        debug: Whether to enable debug logging
        visualize: Whether to generate visualization
        
    Returns:
        True if the test passes, False otherwise
    """
    print(f"\n=== Testing program: {program_name} ===")
    
    # Create validator
    validator = MarqueeTimelineValidator(
        widget_size=widget_size,
        container_size=container_size,
        starting_position=starting_position,
        debug=debug
    )
    
    # Add expected segments
    for segment in expected_segments:
        validator.add_expected_segment(segment)
    
    # Execute the program
    validator.execute_program(program)
    
    # Validate the timeline
    validator.analyze_timeline()
    passed = validator.validate_timeline()
    
    # Print the results
    validator.print_validation_results()
    
    # Visualize the timeline if requested
    if visualize:
        validator.visualize_timeline(filename=f"{program_name}_timeline.png")
    
    return passed 