# Marquee Animation DSL (Domain Specific Language)
# ==========================================
#
# This document proposes an enhanced domain-specific language (DSL) for defining
# animations in the tinyDisplay marquee system. This DSL aims to provide a more
# expressive and flexible way to define complex animations while maintaining
# backward compatibility with the existing action tuple system.

# 1. LANGUAGE OVERVIEW
# -------------------
#
# The Marquee Animation DSL is designed to describe the movement and behavior of
# widgets on small displays. It provides a declarative syntax for defining:
#
# - Movement directions and distances
# - Timing and pauses
# - Looping and repetition
# - Conditional behaviors
# - Coordination between multiple animations
# - Transitions and easing functions

# 1.1 Units and Timing Model
# -------------------------
#
# The DSL uses a consistent units model:
#
# - Time: All timing is measured in "ticks" - abstract units of time used by the animation system
#   - A tick is the basic unit of the animation timeline
#   - Each rendering cycle may advance the animation by one tick if movement is allowed
#   - Pauses are measured in ticks (e.g., PAUSE 10 means "pause for 10 ticks")
#
# - Distance: All distances are measured in pixels
#   - Movement commands specify the TOTAL distance to travel, not the per-tick movement
#   - CRITICAL DISTINCTION: In a command like "MOVE LEFT 100":
#     * The "100" is the TOTAL DISTANCE the widget will eventually travel
#     * It is NOT how many pixels move in a single tick
#     * The actual per-tick movement is controlled by the 'step_size' parameter (formerly 'distance')
#   - When no total distance is specified, movement continues until reaching a boundary
#
# - Speed and Step Size Parameters:
#   - The 'step_size' parameter determines how many pixels are moved in a single movement step
#   - The 'speed' parameter determines how many ticks must pass before a movement step occurs
#   - IMPORTANT: The 'step_size' parameter is DIFFERENT from the distance value in MOVE commands:
#     * MOVE LEFT 100 = "Eventually move a total of 100 pixels to the left"
#     * step_size=5 = "When movement occurs, move 5 pixels at a time"
#   - Example: For "MOVE LEFT 100" with speed=2 and step_size=5:
#     - The widget will eventually move a total of 100 pixels leftward
#     - It will move in increments of 5 pixels per movement step
#     - Each movement step occurs every 2 ticks
#     - The complete animation requires 20 movement steps (100÷5) over 40 ticks (20×2)

# 2. SYNTAX DEFINITION
# -------------------
#
# 2.1 Basic Command Structure
# --------------------------
#
# Commands in the DSL follow this general structure:
#
#   COMMAND [PARAMETER] [OPTIONS]
#
# Where:
# - COMMAND: A keyword indicating the type of action
# - PARAMETER: A distance, duration, or other value (optional)
# - OPTIONS: Key-value pairs to modify the command (optional)

# 2.2 Command Types
# ----------------
#
# Movement Commands:
#   MOVE <direction> <total_eventual_distance_in_pixels> [options]
#   
#   Examples:
#     MOVE RIGHT 100             # Eventually move a total of 100 pixels right (not 100 pixels per tick!)
#     MOVE LEFT                  # Move left until boundary
#     MOVE UP 50 SPEED=2 STEP_SIZE=10  # Move a total of 50 pixels up, 10 pixels every 2 ticks
#     MOVE DOWN 30 EASING=CUBIC  # Move a total of 30 pixels down with cubic easing
#
#   Directions:
#     LEFT (same as RTL)
#     RIGHT (same as LTR)
#     UP (same as BTT)
#     DOWN (same as TTB)
#
#   Options:
#     SPEED=<n>      # Number of ticks between movements (higher = slower animation)
#     STEP_SIZE=<n>  # Pixels to move in a single movement step (NOT the same as the total distance)
#     EASING=<type>  # LINEAR, CUBIC, SINE, BOUNCE, etc.
#     RELATIVE=<bool> # True for relative to current position
#     GAP=<n>        # Pixels of empty space to add between repetitions (primarily for scrolling)

# Pause Commands:
#   PAUSE <duration_in_ticks> [options]
#   
#   Examples:
#     PAUSE 20                   # Pause for 20 ticks
#     PAUSE 10 CONDITION=isHovered  # Pause while condition is true, check each tick
#
#   Options:
#     CONDITION=<expr>  # Expression that must be true to continue pausing

# Return Commands:
#   RETURN [<axis>] [options]
#   
#   Examples:
#     RETURN                 # Return to start position
#     RETURN HORIZONTAL      # Return to horizontal start position
#     RETURN VERTICAL SPEED=3  # Return to vertical start at speed 3
#
#   Axes:
#     HORIZONTAL (same as H)
#     VERTICAL (same as V)
#     BOTH (default)
#
#   Options:
#     SPEED=<n>      # Speed multiplier
#     EASING=<type>  # Easing function to use

# Loop Control:
#   LOOP <count> <commands...> END
#   
#   Examples:
#     LOOP 3
#       MOVE LEFT 50             # 50 pixels left
#       PAUSE 10                 # 10 ticks pause
#       MOVE RIGHT 50            # 50 pixels right
#     END                        # Repeat the sequence 3 times
#
#     LOOP INFINITE
#       MOVE LEFT 100
#       RETURN
#     END                    # Repeat indefinitely

# Conditional Commands:
#   IF <condition> <commands...> [ELSE <commands...>] END
#   
#   Examples:
#     IF widget.width > 100
#       MOVE LEFT widget.width
#     ELSE
#       MOVE LEFT 100
#     END

# Position Reset Commands:
#   RESET_POSITION [mode=<mode>] [options]
#   
#   Examples:
#     RESET_POSITION                     # Reset to starting position with default mode
#     RESET_POSITION mode=seamless       # Reset position without visual discontinuity
#     RESET_POSITION mode=instant        # Immediately jump to starting position
#     RESET_POSITION mode=fade duration=5  # Fade out and back in over 5 ticks
#
#   Modes:
#     seamless - Repositions content without visual discontinuity (default for scrolling)
#     instant - Immediately jumps to the starting position with visible discontinuity
#     fade - Fades out at current position and fades in at starting position
#
#   Options:
#     duration=<n>  # Duration of transition effects in ticks (for fade, etc.)

# Jump Commands:
#   JUMP_TO <position> [options]
#   
#   Examples:
#     JUMP_TO START            # Jump to starting position
#     JUMP_TO x=10 y=20        # Jump to specific coordinates
#     JUMP_TO NEXT_SCREEN      # Jump to next screen position (for popup)
#
#   Positions:
#     START - Original starting position
#     END - Final position of the last movement
#     OFFSCREEN_LEFT, OFFSCREEN_RIGHT, etc. - Positions outside the viewable area
#     NEXT_SCREEN - Next screen position for multi-screen content (popup)
#     PREV_SCREEN - Previous screen position for multi-screen content (popup)
#
#   Options:
#     transition=<type>  # Type of transition (none, fade, slide)
#     duration=<n>       # Duration of transition in ticks

# 2.3 Combined Command Examples
# ----------------------------
#
# Popup Animation:
#   PAUSE 10                 # Pause at top position for 10 ticks
#   MOVE UP widget.height-container.height  # Move up by calculated pixels
#   PAUSE 10                 # Pause at bottom position for 10 ticks
#   MOVE DOWN widget.height-container.height # Return to top position
#
# Scrolling Text:
#   LOOP INFINITE
#     MOVE LEFT widget.width
#   END
#
# Slide-in Animation:
#   MOVE RIGHT 100           # Move from offscreen to onscreen
#   PAUSE 20                 # Pause onscreen
#   MOVE LEFT 100            # Move offscreen

# 2.4 High-Level Animation Commands
# -------------------------------
#
# The DSL provides high-level commands that expand to sequences of low-level commands.
# These provide simple syntax for common animation patterns while allowing customization.

# Scroll Command:
#   SCROLL <direction> <distance> [options]
#   
#   Examples:
#     SCROLL LEFT widget.width GAP=10 STEP_SIZE=3  # Continuous scrolling left
#     SCROLL UP 100 REPEAT=3                      # Scroll up 100 pixels, repeat 3 times
#
#   Options:
#     GAP=<n>         # Pixels of gap between repetitions
#     STEP_SIZE=<n>   # Pixels per movement step
#     SPEED=<n>       # Ticks between movement steps
#     REPEAT=<n>      # Number of repetitions (INFINITE for continuous)
#     RESET_MODE=<mode> # How to handle reset (seamless, instant, fade)
#
#   Expands to (for SCROLL LEFT with seamless reset):
#     LOOP INFINITE
#       MOVE LEFT distance STEP_SIZE=step_size GAP=gap SPEED=speed
#       RESET_POSITION mode=seamless
#     END

# Slide Command:
#   SLIDE <action> <direction> <distance> [options]
#   
#   Examples:
#     SLIDE IN RIGHT 100              # Slide in from right, moving 100 pixels
#     SLIDE OUT LEFT                  # Slide out to the left until offscreen
#     SLIDE IN_OUT DOWN 50 PAUSE=20   # Slide in, pause, slide out in downward direction
#
#   Actions:
#     IN - Slide into view
#     OUT - Slide out of view
#     IN_OUT - Slide in, pause, then slide out
#     
#   Options:
#     PAUSE=<n>       # Ticks to pause between in and out (for IN_OUT)
#     STEP_SIZE=<n>   # Pixels per movement step
#     SPEED=<n>       # Ticks between movement steps
#     EASING=<type>   # Easing function
#
#   Expands to (for SLIDE IN_OUT):
#     MOVE direction distance STEP_SIZE=step_size SPEED=speed
#     PAUSE pause_duration
#     MOVE opposite_direction distance STEP_SIZE=step_size SPEED=speed

# Popup Command:
#   POPUP <options>
#   
#   Examples:
#     POPUP top_delay=10 bottom_delay=10                # Basic popup animation
#     POPUP screens=3 delays=[10,15,10] transition=FADE # Multi-screen popup
#
#   Options:
#     top_delay=<n>     # Ticks to delay at top position
#     bottom_delay=<n>  # Ticks to delay at bottom position
#     screens=<n>       # Number of screens to display
#     delays=[n,n,...]  # Delay at each screen position
#     transition=<type> # How to transition between screens
#     
#   Expands to (for basic POPUP):
#     PAUSE top_delay
#     MOVE UP widget.height-container.height
#     PAUSE bottom_delay
#     MOVE DOWN widget.height-container.height

# 3. INTEGRATION WITH EXISTING CODEBASE
# ------------------------------------
#
# 3.1 Backward Compatibility
# -------------------------
#
# For backward compatibility, the existing action tuple format will be supported:
#   [("rtl", 100), ("pause", 20), ...]
#
# These will be automatically converted to the new DSL format:
#   MOVE LEFT 100
#   PAUSE 20
#   ...

# 3.2 Parsing and Execution
# ------------------------
#
# The DSL will be parsed and converted to an execution plan at initialization time.
# This plan will contain all the positions and state changes needed for the animation.
#
# Example Parser Pseudocode:
#
#   function parseDSL(commands):
#       timeline = []
#       position = startPosition
#       
#       for each command in commands:
#           if command is MOVE:
#               calculate new positions
#               add positions to timeline
#           if command is PAUSE:
#               repeat current position
#               add positions to timeline
#           ...
#       
#       return timeline

# 4. SUBCLASS-SPECIFIC EXTENSIONS
# ------------------------------
#
# 4.1 Scroll Extensions
# --------------------
#
# The scroll subclass adds:
#
#   LOOP CONTINUOUS            # Special mode for continuous scrolling
#     MOVE <direction> <distance> GAP=<pixels>
#   END
#
#   Example:
#     LOOP CONTINUOUS
#       MOVE LEFT widget.width GAP=10 STEP_SIZE=3
#     END
#
# The GAP Parameter
# ^^^^^^^^^^^^^^^^^^^^^^
#
# When scrolling content (especially text), it's often desirable to have empty space between 
# the end of the content and the beginning when it repeats. The GAP parameter creates this 
# visual separation:
#
# - GAP=<n> specifies how many pixels of empty space to insert
# - For horizontal scrolling (LEFT/RIGHT), GAP adds horizontal space
# - For vertical scrolling (UP/DOWN), GAP adds vertical space
#
# Visual representation of horizontal scrolling with GAP=10:
#
# Without GAP:
#  [TEXT END][TEXT START][TEXT END][TEXT START]...
#
# With GAP=10:
#  [TEXT END]...(10px space)...[TEXT START][TEXT END]...(10px space)...[TEXT START]...
#
# The GAP parameter is especially useful for:
# - Making scrolling text more readable by separating repetitions
# - Creating ticker-style effects with distinct items
# - Ensuring visual clarity between the end of content and its repeat

# Seamless Scrolling
# ^^^^^^^^^^^^^^^^^^^
#
# The seamless scrolling effect is achieved through the RESET_POSITION command with mode=seamless.
# This creates continuous scrolling with no visual interruption when content wraps around.
#
# How Seamless Mode Works:
#
# 1. **Visual Continuity**: When the end of the content (plus any gap) scrolls fully into view, 
#    the widget's position is instantly reset to its starting position without any visible change.
#
# 2. **No Visual Jump**: Users should not perceive any "jump" or flicker when the reset occurs.
#
# 3. **Implementation Method**: This is typically achieved by ensuring that a duplicate of the 
#    beginning of the content is positioned immediately after the end (and gap). When this duplicate 
#    scrolls into view, the widget can be repositioned without any visible change to what's on screen.
#
# Visual example of seamless scrolling for "Hello World" moving right to left:
#
# ```
# Frame 1: [    Hello World    ]
# Frame 2: [Hello World    ]
# Frame 3: [ello World    H]
# ...
# Last Frame: [d    Hello Worl]
# Reset (seamless) back to: [    Hello World]
# ```
#
# The reset happens when the beginning of the content has wrapped around and is about
# to appear for the second time, creating a continuous loop with no visible interruption.
#
# Other Reset Modes:
#
# - **instant**: Content immediately jumps back to start position with a visible discontinuity
# - **fade**: Content fades out at end position and fades in at start position
# - **none**: No reset occurs; content moves off-screen and doesn't reappear

# 4.2 Slide Extensions
# ------------------
#
# The slide subclass adds:
#
#   SLIDE IN <direction> [<distance>] [options]  # Slide into view
#   SLIDE OUT <direction> [<distance>] [options] # Slide out of view
#
#   Example:
#     SLIDE IN RIGHT           # Slide in from right
#     PAUSE 20
#     SLIDE OUT LEFT           # Slide out to left

# 4.3 PopUp Extensions
# ------------------
#
# The popUp subclass adds:
#
#   POPUP <top_delay_ticks> <bottom_delay_ticks> [options]  # PopUp animation pattern
#
#   Example:
#     POPUP 10 10             # Popup with 10 tick delays at top and bottom positions
#
#   This expands to:
#     PAUSE 10                # 10 ticks at top position
#     MOVE UP widget.height-container.height
#     PAUSE 10                # 10 ticks at bottom position
#     MOVE DOWN widget.height-container.height

# 5. ADVANCED FEATURES
# ------------------
#
# 5.1 Synchronization Points
# ------------------------
#
# For coordinating multiple animated widgets:
#
#   SYNC <point_name>          # Define a synchronization point
#
#   Example:
#     MOVE LEFT 50
#     SYNC midpoint            # Other widgets can wait for this point
#     MOVE LEFT 50

# 5.2 Wait Points
# -------------
#
# For waiting on events or other widgets:
#
#   WAIT <condition>           # Wait until condition is true
#
#   Example:
#     WAIT other_widget.atSync(midpoint)
#     MOVE RIGHT 100

# 5.3 Mathematical Expressions
# --------------------------
#
# Support for expressions in parameters:
#
#   MOVE LEFT widget.width * 2 + 10
#   PAUSE container.width / 10

# 6. EXAMPLES BY SUBCLASS
# ---------------------
#
# 6.1 Complete Scroll Examples
# --------------------------
#
# Basic horizontal scroll with gap (high-level):
#
#   SCROLL LEFT widget.width GAP=5 STEP_SIZE=3
#   # Creates a continuous scrolling effect with 5-pixel gap between repetitions
#
# Basic horizontal scroll with gap (low-level):
#
#   LOOP INFINITE
#     MOVE LEFT widget.width GAP=5 STEP_SIZE=3
#     RESET_POSITION mode=seamless
#   END
#   # This creates a 5-pixel gap between each repetition of the widget
#
# Complex bidirectional scroll:
#
#   LOOP 3
#     MOVE LEFT widget.width STEP_SIZE=3
#     PAUSE 5
#     MOVE RIGHT widget.width STEP_SIZE=3
#     PAUSE 5
#   END
#   WAIT user.interaction
#   LOOP INFINITE
#     MOVE LEFT widget.width STEP_SIZE=3
#     RESET_POSITION mode=seamless
#   END

# 6.2 Complete Slide Examples
# -------------------------
#
# Simple entrance/exit (high-level):
#
#   SLIDE IN_OUT RIGHT 100 PAUSE=20
#   # Slides in from right, pauses 20 ticks, slides out to right
#
# Simple entrance/exit (low-level):
#
#   JUMP_TO OFFSCREEN_RIGHT
#   MOVE LEFT 100                # Move from offscreen right to onscreen
#   PAUSE 20                     # Pause onscreen
#   MOVE RIGHT 100               # Move from onscreen back to offscreen right
#
# Complex movement pattern:
#
#   MOVE RIGHT 50
#   MOVE DOWN 30
#   MOVE LEFT 50
#   MOVE UP 30
#   PAUSE 10
#   RETURN
#
# Enter-and-stay with different exit trigger:
#
#   SLIDE IN RIGHT 100
#   WAIT user.interaction
#   SLIDE OUT LEFT 100

# 6.3 Complete PopUp Examples
# -------------------------
#
# Basic popup (high-level):
#
#   POPUP top_delay=10 bottom_delay=10
#
# Basic popup (low-level):
#
#   PAUSE 10                # 10 ticks at top position
#   MOVE UP widget.height-container.height
#   PAUSE 10                # 10 ticks at bottom position
#   MOVE DOWN widget.height-container.height
#
# Multi-screen popup:
#
#   POPUP screens=3 delays=[10,15,10]
#   # Shows 3 screens, pausing 10, 15, and 10 ticks at each
#
# Custom popup with different timing and transitions (low-level):
#
#   PAUSE 20
#   JUMP_TO NEXT_SCREEN transition=fade duration=5
#   PAUSE 30
#   JUMP_TO NEXT_SCREEN transition=fade duration=5
#   PAUSE 20
#   JUMP_TO START transition=fade duration=5

# 7. CONFIGURATION EXAMPLES
# -----------------------
#
# Example: Creating a scrolling text in YAML configuration:
#
# ```yaml
# myScrollingText:
#   type: text
#   value: "This is a long scrolling message"
#   effect:
#     type: scroll
#     animation: |
#       LOOP INFINITE
#         MOVE LEFT widget.width GAP=10 STEP_SIZE=2
#       END
# ```
# # This creates a 10-pixel gap between repetitions of the text
#
# Example: Creating a popup effect in code:
#
# ```python
# text_widget = text(value="Weather: Sunny\nTemp: 72°F")
# popup_info = popUp(
#     widget=text_widget,
#     size=(100, 8),
#     animation="""
#     PAUSE 10
#     MOVE UP widget.height-container.height
#     PAUSE 10
#     MOVE DOWN widget.height-container.height
#     """
# )
# ```

# 8. IMPLEMENTATION CONSIDERATIONS
# ------------------------------
#
# 8.1 Tick-Based Timing System
# --------------------------
#
# The animation system operates on a tick-based model:
#
# - The renderer calls the widget's render method regularly
# - Each call may increment the tick counter (if movement is allowed)
# - The timeline index is calculated as (tick % timeline_length)
# - The animation speed is controlled by three distinct factors:
#   1. The total distance specified in movement commands (final destination)
#   2. The 'step_size' parameter (pixels per movement step)
#   3. The 'speed' parameter (ticks between movement steps)
#
# Movement Calculation Example:
# 
# For "MOVE LEFT 100" with speed=2 and step_size=5:
# - The command specifies the widget will eventually move 100 pixels leftward in total
# - The step_size parameter (5) specifies each individual movement will be 5 pixels
# - The speed parameter (2) specifies each movement happens every 2 ticks
# - The timeline will contain a sequence of positions:
#   - Starting position (x, y)
#   - (x-5, y) after 2 ticks  [1st movement step]
#   - (x-10, y) after 4 ticks [2nd movement step]
#   - (x-15, y) after 6 ticks [3rd movement step]
#   - ...and so on until (x-100, y) after 40 ticks [20th movement step]
#
# IMPORTANT DISTINCTION:
# - The value in the MOVE command (e.g., 100 in "MOVE LEFT 100") is the TOTAL travel distance
# - The 'step_size' parameter (e.g., step_size=5) is how far each INDIVIDUAL MOVEMENT STEP moves the widget

# 8.2 Error Handling and Validation
# -------------------------------
#
# The DSL implementation should include:
#
# - Syntax validation at parse time
# - Semantic validation (boundary checks, reasonableness of values)
# - Clear error messages with line numbers
# - Warnings for potentially problematic animations
#
# Example validation checks:
# - Distance values are reasonable for the display size
# - Movement doesn't exceed display boundaries (unless intentional)
# - Animation sequence lengths are reasonable for memory constraints
# - Expressions reference valid properties and use valid operators

# 9. FUTURE EXTENSIONS
# ------------------
#
# - Path-based animations (curves, arcs)
# - Color transitions
# - Direct property animations (size, opacity, etc.)
# - Event triggers (onClick, onHover)
# - Physics-based animations (gravity, bounce)
#
# These extensions would build on the core DSL syntax while adding specialized commands
# for more advanced animation needs. 