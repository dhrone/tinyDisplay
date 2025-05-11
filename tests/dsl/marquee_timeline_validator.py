"""
Marquee Timeline Validator

This module provides a class for testing the marquee_executor by validating
that it generates expected timeline behaviors for DSL programs.
"""

import os
import logging
from typing import List, Dict, Any, Tuple, Optional, Union, Callable
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from tinyDisplay.dsl.marquee_executor import MarqueeExecutor, Position

# Configure logging
logger = logging.getLogger(__name__)

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
        self.logger = logger
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
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
        
        # Special handling for direction changes to detect segment boundaries
        prev_dx, prev_dy = 0, 0
        
        # Create an initial segment for the starting position if the timeline has entries
        if timeline and not hasattr(timeline[0], 'pause'):
            # Add the initial position as its own implicit segment
            initial_segment = [timeline[0]]
            segments.append(initial_segment)
            
            # First real segment starts with position 1
            if len(timeline) > 1:
                current_segment = [timeline[1]]  # Start with the second position
            else:
                current_segment = []
        else:
            # If no starting position (unlikely), start with first position
            if timeline:
                current_segment = [timeline[0]]
        
        for i, pos in enumerate(timeline):
            # Skip the first position (already handled) 
            # and second position (already added to current_segment if exists)
            if i == 0 or i == 1:
                continue
                
            prev_pos = timeline[i-1]
            
            # Calculate movement delta
            curr_dx = pos.x - prev_pos.x
            curr_dy = pos.y - prev_pos.y
            
            # Check for pause transitions (start/end of pause)
            is_pause = hasattr(pos, 'pause') and pos.pause
            was_pause = hasattr(prev_pos, 'pause') and prev_pos.pause
            if is_pause != was_pause:
                self.logger.debug(f"Detected PAUSE transition at position {i}")
                # Complete current segment
                if current_segment:
                    segments.append(current_segment)
                
                # Start a new segment with this position
                current_segment = [pos]
                continue
            
            # Check for reset flag - explicit reset positions start a new segment
            if hasattr(pos, 'reset') and pos.reset:
                self.logger.debug(f"Detected RESET at position {i}")
                # Complete the current segment
                if current_segment:
                    segments.append(current_segment)
                
                # Start a new segment with this reset position
                current_segment = [pos]
                continue
            
            # Check for direction changes - the crucial part for detecting transitions between MOVE statements
            if i > 2 and len(current_segment) > 1:  # Need at least 2 positions to determine a direction
                # Check for non-zero movement in a different direction
                direction_changed = False
                
                # First, is there a change between horizontal and vertical movement?
                if (prev_dx != 0 and curr_dx == 0 and curr_dy != 0) or (prev_dy != 0 and curr_dy == 0 and curr_dx != 0):
                    self.logger.debug(f"Detected axis change at position {i}: ({prev_dx}, {prev_dy}) → ({curr_dx}, {curr_dy})")
                    direction_changed = True
                
                # Check for sign changes (reversals) in movement
                elif (prev_dx > 0 and curr_dx < 0) or (prev_dx < 0 and curr_dx > 0) or \
                     (prev_dy > 0 and curr_dy < 0) or (prev_dy < 0 and curr_dy > 0):
                    self.logger.debug(f"Detected direction reversal at position {i}")
                    direction_changed = True
                
                # Start a new segment if direction changed
                if direction_changed:
                    if current_segment:
                        segments.append(current_segment)
                    
                    # Start a new segment with this position
                    # This is the first position that the new segment adds to the timeline
                    current_segment = [pos]
                    continue
            
            # Check for terminal positions (marks end of a high-level animation)
            if hasattr(pos, 'terminal') and pos.terminal:
                self.logger.debug(f"Detected terminal position at {i}")
                # Add the terminal position to complete the current segment
                current_segment.append(pos)
                
                # End current segment and start a new one for the next positions
                segments.append(current_segment)
                current_segment = []
                continue
            
            # If we reach here, add the position to the current segment
            current_segment.append(pos)
            
            # Update the previous direction for the next iteration
            prev_dx, prev_dy = curr_dx, curr_dy
        
        # Add the last segment if not empty
        if current_segment:
            segments.append(current_segment)
            
        self.actual_segments = segments
        self.logger.debug(f"Timeline divided into {len(segments)} segments")
        
        # Debug segment detections
        for i, segment in enumerate(segments):
            if not segment:
                continue
            start_pos = segment[0]
            end_pos = segment[-1]
            delta_x = end_pos.x - start_pos.x
            delta_y = end_pos.y - start_pos.y
            pattern = self.categorize_segment(segment)
            self.logger.debug(f"Segment {i+1}: {pattern}, Start: {start_pos}, End: {end_pos}, Delta: ({delta_x}, {delta_y})")
            
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
        
        # Check if this is an explicit reset segment (not just based on coordinates)
        if hasattr(segment[0], 'reset') and segment[0].reset:
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
        
        # Log the timeline coordinates in a concise format
        coords = [(pos.x, pos.y) for pos in self.timeline]
        self.logger.info(f"Timeline coordinates: {coords}")
            
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
        
        # Skip the initial position segment if it exists and isn't explicitly expected
        # This allows for backward compatibility with tests that don't expect the initial segment
        start_index = 0
        if (len(self.actual_segments) > len(self.expected_segments) and 
            len(self.actual_segments) > 0 and len(self.actual_segments[0]) == 1):
            # Check if this looks like an implicit initial position segment
            initial_pos = self.actual_segments[0][0]
            if initial_pos.x == self.starting_position[0] and initial_pos.y == self.starting_position[1]:
                self.logger.debug("Detected initial position segment, adjusting validation accordingly")
                start_index = 1
        
        # Validate each expected segment against actual segments
        num_segments_to_check = min(len(self.expected_segments), len(self.actual_segments) - start_index)
        
        for i in range(num_segments_to_check):
            expected = self.expected_segments[i]
            actual = self.actual_segments[i + start_index]
            
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
                
                # For animation consistency, segments don't duplicate their start position
                # If expected_start doesn't match the actual start, check if it's the starting position
                if (actual[0].x != start_x or actual[0].y != start_y):
                    # Only report an error if this isn't a boundary transition
                    # (where the segment naturally starts at a different position)
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
        
        # If we have more expected segments than actual (accounting for the initial segment),
        # report those as errors
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
        
        # Define sizes and parameters
        padding = 70  # Increased padding further
        left_padding = 180  # Further increased left padding for grid labels
        top_padding = 20   # Additional padding for top grid labels
        legend_width = 220  # Width of the legend section (increased)
        title_height = 60  # Height for the title
        # More generous segment list height calculation - at least 35px per segment plus some extra
        segment_list_height = max(35 * max(len(self.actual_segments), 1) + 50, 150)
        dot_size = 5  # Dot size
        grid_spacing = 20  # Grid spacing
        font_size = 12  # Define a standard font size
        
        # Generate segment colors - use distinct colors for each segment
        segment_colors = [
            (255, 50, 50),    # Red
            (50, 150, 255),   # Blue
            (50, 255, 50),    # Green
            (255, 200, 50),   # Yellow
            (200, 50, 255),   # Purple
            (255, 150, 50),   # Orange
            (50, 200, 200),   # Teal
            (200, 200, 50),   # Lime
            (255, 100, 150),  # Pink
            (150, 100, 200),  # Lavender
        ]
        # If we have more segments than colors, cycle through colors
        while len(segment_colors) < len(self.actual_segments):
            segment_colors.extend(segment_colors)
        
        # Try to load a system font for better clarity
        try:
            # Try to use a clear system font - fallback to default if not available
            font = ImageFont.truetype("Arial", font_size)
            large_font = ImageFont.truetype("Arial", font_size + 2)
        except IOError:
            # If Arial is not available, use default
            font = ImageFont.load_default()
            large_font = font
        
        # Calculate main visualization area size with extra space
        viz_width = max(max_x - min_x + 1, self.widget_size[0]) * 1.5 + padding * 2 + left_padding
        viz_height = max(max_y - min_y + 1, self.widget_size[1]) * 1.5 + padding * 2
        
        # Add space for legend on the right and segment list at the bottom
        canvas_width = int(viz_width + legend_width)
        canvas_height = int(viz_height + title_height + segment_list_height)
        
        # Create a larger canvas with improved background color
        canvas = Image.new("RGB", (canvas_width, canvas_height), (15, 15, 30))  # Slightly lighter background
        draw = ImageDraw.Draw(canvas)
        
        # STEP 1: Draw background elements first
        # -----------------------------------------------------
        
        # Draw title area background
        draw.rectangle([(0, 0), (canvas_width, title_height)], fill=(30, 30, 50))
        
        # Draw segment list area background
        draw.rectangle(
            [(0, title_height + viz_height), (canvas_width, canvas_height)],
            fill=(25, 25, 40)  # Slightly darker than main background
        )
        
        # Define the visualization area boundaries for easier reference
        viz_area_left = left_padding
        viz_area_top = title_height + top_padding
        viz_area_right = viz_area_left + viz_width - left_padding
        viz_area_bottom = viz_area_top + viz_height - top_padding
        
        # Calculate the center point (origin) in canvas coordinates
        # This ensures the origin (0,0) is centered in the visualization area
        origin_x = viz_area_left + (viz_area_right - viz_area_left) / 2
        origin_y = viz_area_top + (viz_area_bottom - viz_area_top) / 2
        
        # Calculate scale factor to fit all points in the visualization area
        # Allow for both positive and negative coordinates
        max_abs_x = max(abs(min_x), abs(max_x), 1)  # Ensure at least 1 to avoid division by zero
        max_abs_y = max(abs(min_y), abs(max_y), 1)  # Ensure at least 1 to avoid division by zero
        
        # Determine the scale based on the maximum range in either direction
        # We need to leave some padding, so we use a slightly smaller scale
        scale_x = (viz_area_right - viz_area_left) / (max_abs_x * 2.2)
        scale_y = (viz_area_bottom - viz_area_top) / (max_abs_y * 2.2)
        
        # Use the smaller of the two scales to maintain aspect ratio
        scale = min(scale_x, scale_y)
        if scale == 0:
            scale = 1  # Default if no points
            
        # Draw a border around the visualization area
        draw.rectangle(
            [(viz_area_left, viz_area_top), (viz_area_right, viz_area_bottom)],
            outline=(80, 80, 100),
            width=2
        )
        
        # Draw a grid for reference in main visualization area
        grid_color = (40, 40, 60)
        
        # Draw vertical grid lines (for x coordinates)
        # Start from origin and go outward in both directions
        # Negative grid lines
        x = 0
        while True:
            x -= grid_spacing
            grid_x = origin_x + x * scale
            if grid_x < viz_area_left:
                break
            draw.line([(grid_x, viz_area_top), (grid_x, viz_area_bottom)], fill=grid_color)
        
        # Positive grid lines
        x = 0
        while True:
            x += grid_spacing
            grid_x = origin_x + x * scale
            if grid_x > viz_area_right:
                break
            draw.line([(grid_x, viz_area_top), (grid_x, viz_area_bottom)], fill=grid_color)
        
        # Draw horizontal grid lines (for y coordinates)
        # Start from origin and go outward in both directions
        # Negative grid lines
        y = 0
        while True:
            y -= grid_spacing
            # Positive Y is downward in Pillow coordinates
            grid_y = origin_y + y * scale
            if grid_y < viz_area_top:
                break
            draw.line([(viz_area_left, grid_y), (viz_area_right, grid_y)], fill=grid_color)
        
        # Positive grid lines
        y = 0
        while True:
            y += grid_spacing
            # Positive Y is downward in Pillow coordinates
            grid_y = origin_y + y * scale
            if grid_y > viz_area_bottom:
                break
            draw.line([(viz_area_left, grid_y), (viz_area_right, grid_y)], fill=grid_color)
        
        # Draw the center grid line (x=0 and y=0) with a slightly more visible color
        center_grid_color = (60, 60, 80)
        # Vertical center line (x=0)
        draw.line([(origin_x, viz_area_top), (origin_x, viz_area_bottom)], fill=center_grid_color, width=1)
        # Horizontal center line (y=0)
        draw.line([(viz_area_left, origin_y), (viz_area_right, origin_y)], fill=center_grid_color, width=1)
        
        # Draw a separator for the legend
        draw.line([(viz_width, 0), (viz_width, canvas_height)], fill=(100, 100, 130), width=2)
        
        # Draw a separator for the segment list
        draw.line([(0, title_height + viz_height), (canvas_width, title_height + viz_height)], 
                 fill=(100, 100, 130), width=2)
        
        # Define function to convert timeline position to canvas coordinates
        def timeline_to_canvas(pos_x, pos_y):
            canvas_x = origin_x + pos_x * scale
            # In Pillow, positive Y is downward, so we add instead of subtract
            canvas_y = origin_y + pos_y * scale
            return canvas_x, canvas_y
        
        # STEP 2: Draw segment paths with different colors
        # -----------------------------------------------------
        
        # We'll draw each segment's path separately with its own color
        if self.actual_segments:
            cumulative_pos = 0
            
            for i, segment in enumerate(self.actual_segments):
                if not segment:
                    cumulative_pos += 0
                    continue
                    
                # Get the segment color
                segment_color = segment_colors[i % len(segment_colors)]
                
                # Calculate start and end indices for this segment
                start_idx = cumulative_pos
                end_idx = cumulative_pos + len(segment)
                
                # Get positions for this segment
                segment_positions = self.timeline[start_idx:end_idx]
                
                # Create line points for this segment
                segment_line_points = []
                for pos in segment_positions:
                    # Convert to canvas coordinates with scaling
                    x, y = timeline_to_canvas(pos.x, pos.y)
                    segment_line_points.append((x, y))
                
                # Draw the segment line with its color if there are at least 2 points
                if len(segment_line_points) > 1:
                    # Using thinner lines (width=1) for the paths
                    draw.line(segment_line_points, fill=segment_color, width=1)
                
                # Update cumulative position
                cumulative_pos += len(segment)
        
        # STEP 3: Draw coordinate grid values
        # -----------------------------------------------------
        # Draw coordinate values along the top and left edges
        coord_color = (180, 180, 200)  # Light color for coordinate text
        
        # X-axis coordinates
        # Display coordinates at each grid line
        x = 0
        while True:
            x -= grid_spacing
            grid_x = origin_x + x * scale
            if grid_x < viz_area_left:
                break
            # Draw coordinate value above the visualization area
            draw.text((grid_x - 8, viz_area_top - 20), 
                      str(x), fill=coord_color, font=font)
                      
        x = 0  # Reset to draw positive values
        draw.text((origin_x - 8, viz_area_top - 20), 
                  "0", fill=coord_color, font=font)  # Draw 0 at origin
                  
        while True:
            x += grid_spacing
            grid_x = origin_x + x * scale
            if grid_x > viz_area_right:
                break
            # Draw coordinate value above the visualization area
            draw.text((grid_x - 8, viz_area_top - 20), 
                      str(x), fill=coord_color, font=font)
        
        # Y-axis coordinates
        # Display coordinates at each grid line
        y = 0
        while True:
            y -= grid_spacing
            # Positive Y is downward in Pillow coordinates
            grid_y = origin_y + y * scale
            if grid_y < viz_area_top:
                break
            # Draw coordinate value to the left of the visualization area
            text = str(y)
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
            draw.text((viz_area_left - text_width - 10, grid_y - text_height//2), 
                      text, fill=coord_color, font=font)
                      
        y = 0  # Reset to draw positive values
        draw.text((viz_area_left - 15, origin_y - 7), 
                  "0", fill=coord_color, font=font)  # Draw 0 at origin
                  
        while True:
            y += grid_spacing
            # Positive Y is downward in Pillow coordinates
            grid_y = origin_y + y * scale
            if grid_y > viz_area_bottom:
                break
            # Draw coordinate value to the left of the visualization area
            text = str(y)
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
            draw.text((viz_area_left - text_width - 10, grid_y - text_height//2), 
                      text, fill=coord_color, font=font)
                      
        # Draw axis labels
        draw.text((viz_area_left + (viz_area_right - viz_area_left)//2 - 5, viz_area_top - 40), 
                  "X", fill=coord_color, font=font)
        draw.text((viz_area_left - 40, viz_area_top + (viz_area_bottom - viz_area_top)//2 - 5), 
                  "Y", fill=coord_color, font=font)
        
        # STEP 4: Draw position dots and segment lines
        # -----------------------------------------------------
        # Draw segment paths with different colors
        if self.actual_segments:
            cumulative_pos = 0
            
            for i, segment in enumerate(self.actual_segments):
                if not segment:
                    cumulative_pos += 0
                    continue
                    
                # Get the segment color
                segment_color = segment_colors[i % len(segment_colors)]
                
                # Calculate start and end indices for this segment
                start_idx = cumulative_pos
                end_idx = cumulative_pos + len(segment)
                
                # Get positions for this segment
                segment_positions = self.timeline[start_idx:end_idx]
                
                # Create line points for this segment
                segment_line_points = []
                for pos in segment_positions:
                    x, y = timeline_to_canvas(pos.x, pos.y)
                    segment_line_points.append((x, y))
                
                # Draw the segment line with its color if there are at least 2 points
                if len(segment_line_points) > 1:
                    # Using thinner lines (width=1) for the paths
                    draw.line(segment_line_points, fill=segment_color, width=1)
                
                # Update cumulative position
                cumulative_pos += len(segment)
        
        # Draw position dots
        for i, pos in enumerate(self.timeline):
            x, y = timeline_to_canvas(pos.x, pos.y)
            
            # Different colors for different position types
            color = (230, 230, 230)  # White-ish for normal positions
            
            if hasattr(pos, 'pause') and pos.pause:
                color = (50, 50, 255)  # Blue for pauses
            if hasattr(pos, 'terminal') and pos.terminal:
                color = (255, 50, 50)  # Red for terminal positions
            
            # Draw the dot
            draw.ellipse([(x-dot_size, y-dot_size), (x+dot_size, y+dot_size)], fill=color)
        
        # Draw origin marker at (0,0)
        draw.rectangle(
            [(origin_x-6, origin_y-6), (origin_x+6, origin_y+6)],
            outline=(200, 200, 200),
            fill=(100, 100, 100)
        )
        
        # STEP 5: Draw all text elements on top
        # -----------------------------------------------------
        
        # Draw title text
        title = f"Timeline Visualization ({len(self.timeline)} positions, {len(self.actual_segments)} segments)"
        draw.text((padding, padding//2), title, fill=(255, 255, 255), font=large_font)
        
        # Draw origin label with background
        text = "Origin (0,0)"
        text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
        
        # Draw text background slightly offset from the origin marker
        # Position it below the origin marker for better visibility
        label_x = origin_x - text_width//2
        label_y = origin_y + 15
        
        # Ensure the label stays within the visualization area
        if label_x < viz_area_left + 10:
            label_x = viz_area_left + 10
        if label_x + text_width > viz_area_right - 10:
            label_x = viz_area_right - text_width - 10
            
        # Draw text background
        draw.rectangle(
            [(label_x - 2, label_y - 2), (label_x + text_width + 2, label_y + text_height + 2)],
            fill=(40, 40, 60)
        )
        draw.text((label_x, label_y), text, fill=(255, 255, 255), font=font)
        
        # STEP 6: Draw segment list at the bottom
        # -----------------------------------------------------
        if self.actual_segments:
            # Draw "Segments:" header
            segment_list_x = 20
            segment_list_y = title_height + viz_height + 10
            draw.text((segment_list_x, segment_list_y), 
                     "SEGMENTS:", fill=(255, 255, 255), font=large_font)
            segment_list_y += 30
            
            # Draw each segment in the list
            for i, segment in enumerate(self.actual_segments):
                if not segment or i >= len(self.expected_segments):
                    continue
                
                # Get segment color
                segment_color = segment_colors[i % len(segment_colors)]
                
                # Get segment name and pattern
                segment_name = self.expected_segments[i].name
                segment_pattern = self.expected_segments[i].pattern
                
                # Draw colored square for this segment
                square_size = 12
                draw.rectangle(
                    [(segment_list_x, segment_list_y), 
                     (segment_list_x + square_size, segment_list_y + square_size)],
                    fill=segment_color
                )
                
                # Segment description - potentially long so we need to handle it carefully
                if segment:
                    start_pos = segment[0]
                    end_pos = segment[-1]
                    dx = end_pos.x - start_pos.x
                    dy = end_pos.y - start_pos.y
                    
                    # Format text with clear spacing
                    text = f"Segment {i+1}: {segment_name} ({segment_pattern})"
                    text += f"  -  Start: ({start_pos.x}, {start_pos.y}), End: ({end_pos.x}, {end_pos.y}), Delta: ({dx}, {dy})"
                else:
                    text = f"Segment {i+1}: {segment_name} ({segment_pattern}) - EMPTY"
                
                # Ensure text doesn't overflow into legend area
                max_text_width = viz_width - segment_list_x - 40
                
                # Check if we need to truncate the text
                text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
                if text_width > max_text_width:
                    # Truncate with ellipsis
                    truncated = True
                    while text_width > max_text_width and len(text) > 10:
                        text = text[:-1]
                        text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
                    text = text[:-3] + "..."
                
                draw.text((segment_list_x + square_size + 10, segment_list_y), 
                         text, fill=(255, 255, 255), font=font)
                
                # Move to next line with more spacing
                segment_list_y += 30
                
        # STEP 7: Draw legend section
        # -----------------------------------------------------
        
        # Add a legend header
        legend_x = viz_width + 20
        legend_y = title_height + 20
        draw.text((legend_x, legend_y), "LEGEND", fill=(255, 255, 255), font=large_font)
        legend_y += 30
        
        # Draw the legend items with bigger dots and better spacing
        legend_items = [
            ("Position", (230, 230, 230)),
            ("Pause position", (50, 50, 255)),
            ("Terminal position", (255, 50, 50))
        ]
        
        for text, color in legend_items:
            # Draw dot
            draw.ellipse(
                [(legend_x, legend_y), (legend_x + 2*dot_size, legend_y + 2*dot_size)], 
                fill=color
            )
            # Draw text
            draw.text((legend_x + 2*dot_size + 10, legend_y), 
                      text, fill=(255, 255, 255), font=font)
            legend_y += 30
        
        # Add spacing before shape examples
        legend_y += 10
        
        # Draw origin marker example
        draw.rectangle(
            [(legend_x, legend_y), (legend_x + 12, legend_y + 12)],
            outline=(200, 200, 200),
            fill=(100, 100, 100)
        )
        draw.text((legend_x + 30, legend_y), 
                  "Origin marker", fill=(255, 255, 255), font=font)
        legend_y += 30
        
        # Add widget and container size information in a separate section
        # Draw a dividing line
        legend_y += 40
        divider_y = legend_y - 20
        draw.line([(legend_x, divider_y), (canvas_width - 20, divider_y)], 
                 fill=(100, 100, 130), width=1)
        
        # Add section title
        draw.text((legend_x, legend_y), "SIZE INFORMATION:", 
                 fill=(255, 255, 255), font=large_font)
        legend_y += 30
        
        # Draw size information
        draw.text((legend_x, legend_y), f"Widget size: {self.widget_size[0]}x{self.widget_size[1]}", 
                  fill=(255, 255, 255), font=font)
        legend_y += 25
        draw.text((legend_x, legend_y), f"Container size: {self.container_size[0]}x{self.container_size[1]}", 
                  fill=(255, 255, 255), font=font)
        
        # Save the image
        output_path = os.path.join(output_dir, filename)
        canvas.save(output_path)
        self.logger.info(f"Saved timeline visualization to {output_path}") 