# Marquee Animation DSL Specification

## 1. Overview

The Marquee Animation DSL is a domain-specific language tailored for defining widget animations on resource-constrained displays (e.g., Raspberry Pi Zero 2W driving 100×16–256×128 pixel panels via bitbang/SPI/I²C). It aims to:

* Provide a **declarative** syntax for movement, timing, loops, and conditions.
* Support **coordination** between multiple animations and **custom easing**.
* Optimize for **ticks-based timing** and **pixel-based distances** under strict memory/CPU constraints.
* Enable **deterministic rendering** for any arbitrary tick without requiring full simulation.

### 1.1 Language Features

* **Movement directions & distances**: Total travel distances in pixels.
* **Timing & pauses**: Measured in integer *ticks*, the atomic time unit of the system.
* **Looping & repetition**: Finite or infinite loops, with named loops for clarity.
* **Conditional behaviors**: IF/ELSEIF/ELSE branches, with BREAK and CONTINUE.
* **Coordination**: SYNC and WAIT\_FOR primitives to synchronize multiple widgets.
* **Transitions & easing**: Built-in (`linear`, `ease_in`, etc.) and parameterized curves (e.g., cubic‑bezier).
* **Deterministic calculations**: Direct mapping of arbitrary ticks to widget states.
* **Timeline optimization**: Loop periods and segment boundaries for efficient rendering.

### 1.2 Units & Timing Model

* **Ticks**: The basic time unit. Each rendering cycle may advance by one tick if allowed.

  * `PAUSE(10)` means "pause for 10 ticks".
  * A tick is the basic unit of the animation timeline; timing only uses ticks (no ms/s).

* **Pixels**: The distance unit for coordinates and MOVE commands.

  * A command `MOVE(start, end)` specifies the **total** distance to travel in pixels.
  * *Important:* This total is not the per-tick movement. The per-tick movement is controlled by the `step` option.
  * When no total distance is specified (future extension), movement continues until hitting a boundary or forever in a loop.

* **Speed and Step Size**:

  * `distance` (literal in MOVE) = total pixels the widget will eventually move.
  * `step` (option) = pixels moved per movement invocation (per step).
  * Example:

    ```dsl
    MOVE(startX, endX) { step=5, interval=2 };
    ```

    * The widget travels from `startX` to `endX` in increments of 5 pixels, advancing every 2 ticks.

* **Gap**:

  * When scrolling content (especially text), it's often desirable to have empty space between the end of the content and the beginning when it repeats.
  * The `gap` parameter creates this visual separation:
    * `gap` (pixels) = empty space added between repetitions of scrolling content.
    * For horizontal scrolling, gap adds horizontal space; for vertical scrolling, gap adds vertical space.
  * Example:
    ```dsl
    MOVE(widget.x, container.width) { step=3, interval=1, gap=10 };
    ```
    * Creates a 10-pixel gap between each repetition of the widget.

### 1.3 Direction Constants

Direction constants provide intuitive movement definitions that are automatically translated to coordinate changes:

* `LEFT`: Decreasing X coordinates (negative X movement)
* `RIGHT`: Increasing X coordinates (positive X movement)
* `UP`: Decreasing Y coordinates (negative Y movement) 
* `DOWN`: Increasing Y coordinates (positive Y movement)

These can be used with both high-level and low-level commands:

```dsl
// High-level with direction constant
SCROLL(LEFT, widget.width) { step=2, gap=5 };

// Low-level with direction constant
MOVE(RIGHT, 100) { step=5 };

// Equivalent to
MOVE(widget.x, widget.x + 100) { step=5 };
```

## 2. Lexical Definitions

```ebnf
WHITESPACE       ::=  ( " " | "\t" | "\r" | "\n" )+ ;
COMMENT          ::=  
      "#" { any_char_except_newline }*  ( "\n" | EOF )
    | "/*" { any_char_except_end_comment }* "*/"
    ;

KEYWORD          ::=  
      "MOVE" | "PAUSE" | "RESET_POSITION"
    | "LOOP" | "END" | "INFINITE"
    | "IF" | "ELSEIF" | "ELSE"
    | "BREAK" | "CONTINUE"
    | "SYNC" | "WAIT_FOR"
    | "SCROLL" | "SLIDE" | "POPUP"
    | "LEFT" | "RIGHT" | "UP" | "DOWN"
    | "PERIOD" | "START_AT" | "SEGMENT"
    | "POSITION_AT" | "SCHEDULE_AT"
    | "ON_VARIABLE_CHANGE"
    ;

IDENT            ::=  letter { letter | digit | "_" }* ;
NUMBER           ::=  digit { digit } ;          (* integer ticks or pixels *)
STRING           ::=  `"` {  ~`"`  | `\"`  }* `"` ;
BOOLEAN          ::=  "true" | "false" ;
```

* **All numeric literals** are integers: ticks (timing) or pixels (coordinates/distance).

## 3. Grammar (EBNF)

```ebnf
Program          ::=  { Statement } EOF ;

Statement        ::=  
      CommandStmt
    | LoopStmt
    | IfStmt
    | SyncStmt
    | BreakStmt
    | ContinueStmt
    | HighLevelStmt
    | TimelineStmt
    | ";"              (* empty/placeholder *)
    ;

CommandStmt      ::=  
      MOVEStmt
    | PAUSEStmt
    | RESETStmt
    ;

MOVEStmt         ::=  
      "MOVE" "(" Expr "," Expr [ "," Expr "," Expr ] ")" [ Options ] ";"
    | "MOVE" "(" Direction "," Expr ")" [ Options ] ";"
    ;

PAUSEStmt        ::=  
      "PAUSE" "(" Expr ")" ";"
    ;

RESETStmt        ::=  
      "RESET_POSITION" "(" [ Options ] ")" ";"
    ;

LoopStmt         ::=  
      "LOOP" "(" ( Expr | "INFINITE" ) [ "AS" IDENT ] ")" Block "END" ";"
    ;

IfStmt           ::=  
      "IF" "(" Condition ")" Block
      { "ELSEIF" "(" Condition ")" Block }
      [ "ELSE" Block ]
      "END" ";"
    ;

SyncStmt         ::=  
      "SYNC" "(" IDENT ")" ";"
    | "WAIT_FOR" "(" IDENT "," Expr ")" ";"
    ;

BreakStmt        ::=  "BREAK" ";" ;
ContinueStmt     ::=  "CONTINUE" ";" ;

HighLevelStmt    ::=  
      SCROLLStmt
    | SLIDEStmt
    | POPUPStmt
    ;

SCROLLStmt       ::=  
      "SCROLL" "(" Direction "," Expr ")" [ Options ] ";"
    ;

SLIDEStmt        ::=  
      "SLIDE" "(" SlideAction "," Direction "," Expr ")" [ Options ] ";"
    ;

POPUPStmt        ::=  
      "POPUP" "(" [ Options ] ")" ";"
    ;

SlideAction      ::=  "IN" | "OUT" | "IN_OUT" ;

Block            ::=  "{" { Statement } "}" ;

Options          ::=  "{" Option { "," Option } "}" ;
Option           ::=  IDENT "=" Value ;
Value            ::=  Expr | STRING | BOOLEAN | EasingFunction ;

Condition        ::=  Expr ( ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) Expr ) ;

Expr             ::=  Term { ( "+" | "-" ) Term } ;
Term             ::=  Factor { ( "*" | "/" ) Factor } ;
Factor           ::=  
      NUMBER
    | STRING
    | IDENT [ "(" ArgList? ")" ]
    | "(" Expr ")"
    ;
ArgList          ::=  Expr { "," Expr } ;

EasingFunction   ::=  
      "linear"
    | "ease_in" | "ease_out" | "ease_in_out"
    | IDENT "(" NUMBER "," NUMBER "," NUMBER "," NUMBER ")"
      (* e.g. cubic_bezier(0,0,1,1) *)
    ;

Direction        ::=  "LEFT" | "RIGHT" | "UP" | "DOWN" ;

TimelineStmt     ::=  
      PeriodStmt
    | StartAtStmt
    | SegmentStmt
    | PositionAtStmt
    | ScheduleStmt
    | VariableChangeStmt
    ;

PeriodStmt       ::=  "PERIOD" "(" Expr ")" ";" ;

StartAtStmt      ::=  "START_AT" "(" Expr ")" ";" ;

SegmentStmt      ::=  
      "SEGMENT" "(" IDENT "," Expr "," Expr ")" Block "END" ";"
    ;

PositionAtStmt   ::=  
      "POSITION_AT" "(" Expr ")" "=>" Block "END" ";"
    ;

ScheduleStmt     ::=  
      "SCHEDULE_AT" "(" Expr "," IDENT ")" ";"
    ;

VariableChangeStmt ::=  
      "ON_VARIABLE_CHANGE" "(" IDENT ")" Block "END" ";"
    | "ON_VARIABLE_CHANGE" "(" "[" IDENT { "," IDENT } "]" ")" Block "END" ";"
    ;
```

## 4. Key Features

* **Ticks-based timing**: All durations in ticks; rendering layer maps ticks→ms or fps.
* **Named loops**: `LOOP(INFINITE AS name) { … } END;`
* **Full control flow**: `ELSEIF`, `BREAK;`, `CONTINUE;`.
* **Custom easing**: Supports built-in (`linear`, `ease_in`, etc.) and parameterized curves.
* **Two-dimensional movement**: `MOVE` now optionally accepts four expressions to move X and Y concurrently.
* **Deterministic optimization**: Features that enhance timeline predictability:
  * Loop periods for efficient repeating patterns
  * Position calculation for arbitrary ticks
  * Timeline segments for modular animation definition
  * Variable change handling for declarative recalculation policies

## 5. Command Reference

Below is a detailed description of each DSL command and its attributes:

### 5.1 Basic Commands

#### MOVE

**Syntax:** `MOVE(startX, endX[, startY, endY]) [Options];`
**Description:** Moves a widget from a starting coordinate to a target coordinate, optionally in two dimensions.

* **startX**, **endX** (`Expr`): X-axis start and end positions.
* **startY**, **endY** (`Expr`, optional): Y-axis start and end positions.
* **step** (integer): Pixels moved per movement step. Default: 1.
* **interval** (integer): Ticks between movement steps. Default: 1.
* **easing** (easingFunction): Transition curve to apply. Default: linear.

#### PAUSE

**Syntax:** `PAUSE(ticks);`
**Description:** Halts animation for a specified number of ticks.

* **ticks** (`Expr`): Number of ticks to pause execution.

#### RESET\_POSITION

**Syntax:** `RESET_POSITION([Options]);`
**Description:** Resets the widget's position to its initial coordinates with optional transition modes.

* **mode** (`IDENT`, default `seamless`): Specifies how the reset occurs:

  * `seamless`: Repositions content without visual discontinuity (ideal for continuous scrolling).
  * `instant`: Immediately jumps to the starting position with visible discontinuity.
  * `fade`: Fades out at the current position and fades in at the starting position.
* **duration** (`Expr`): Number of ticks for transition effects (used for `fade` mode). Default: 0 (immediate).

### 5.2 Control Flow Commands

#### LOOP

**Syntax:** `LOOP(count [AS name]) { ... } END;`
**Description:** Repeats the enclosed block either a finite number of times or indefinitely.

* **count** (`Expr` or `INFINITE`): Number of iterations or infinite loop.
* **name** (`IDENT`, optional): Identifier for the loop to use with `BREAK`/`CONTINUE`.

#### IF / ELSEIF / ELSE

**Syntax:** `IF(condition) { ... } [ELSEIF(condition) { ... }] [ELSE { ... }] END;`
**Description:** Executes blocks based on boolean conditions.

* **condition** (`Expr relational Expr`): Comparison to decide which block runs.

#### BREAK

**Syntax:** `BREAK;`
**Description:** Immediately exits the nearest surrounding loop.

#### CONTINUE

**Syntax:** `CONTINUE;`
**Description:** Skips the remainder of the current loop iteration and begins the next one.

### 5.3 Synchronization Commands

#### SYNC

**Syntax:** `SYNC(event);`
**Description:** Pauses execution until another animation signals the named event.

* **event** (`IDENT`): Name of the synchronization point.

#### WAIT\_FOR

**Syntax:** `WAIT_FOR(event, ticks);`
**Description:** Waits for the specified event up to a maximum number of ticks, then proceeds regardless.

* **event** (`IDENT`): Event to wait for.
* **ticks** (`Expr`): Maximum ticks to wait before timing out.

### 5.4 High-Level Commands

#### SCROLL

**Syntax:** `SCROLL(direction, distance) [Options];`

**Description:** Creates continuous scrolling animation in the specified direction.

**Options:**
* **step** (integer): Pixels moved per step. Default: 1.
* **interval** (integer): Ticks between steps. Default: 1.
* **gap** (integer): Pixels of empty space between repetitions of content. Default: 0.
* **repeat** (`Expr` or `INFINITE`): Number of scroll cycles to perform. Default: INFINITE.
* **reset_mode** (`IDENT`): How to handle returning to start position. Default: seamless.

**Expands to (for seamless scrolling):**
```dsl
LOOP(repeat) {
    MOVE(direction, distance) { step=step, interval=interval, gap=gap };
    RESET_POSITION({ mode=reset_mode });
} END;
```

#### SLIDE

**Syntax:** `SLIDE(action, direction, distance) [Options];`

**Description:** Creates entrance, exit, or combined animations.

* **action** (`SlideAction`): The type of slide (IN, OUT, IN_OUT).
* **direction** (`Direction`): Direction to slide.
* **distance** (`Expr`): Total distance to slide.

**Options:**
* **step** (integer): Pixels moved per step. Default: 1.
* **interval** (integer): Ticks between steps. Default: 1.
* **pause** (integer): Ticks to pause between IN and OUT phases (for IN_OUT). Default: 0.
* **easing** (easingFunction): Transition curve to apply. Default: linear.

#### POPUP

**Syntax:** `POPUP([Options]);`

**Description:** Creates a popup animation showing alternating portions of tall content.

**Options:**
* **top_delay** (integer): Ticks to delay at top position. Default: 10.
* **bottom_delay** (integer): Ticks to delay at bottom position. Default: 10.
* **screens** (integer): Number of content screens to cycle through. Default: 2.
* **step** (integer): Pixels moved per step. Default: 1.
* **interval** (integer): Ticks between steps. Default: 1.

### 5.5 Timeline Optimization Commands

#### PERIOD

**Syntax:** `PERIOD(ticks);`
**Description:** Declares that an animation repeats its state every specified number of ticks.

* **ticks** (`Expr`): Number of ticks in the repeating cycle.

This command helps the rendering engine optimize calculations. For example:

```dsl
LOOP(INFINITE) {
    MOVE(LEFT, 100) { step=2, interval=1 };
    RESET_POSITION({ mode=seamless });
} END;
PERIOD(50);  // States repeat every 50 ticks
```

#### START_AT

**Syntax:** `START_AT(tick);`
**Description:** Explicitly sets when an animation sequence begins.

* **tick** (`Expr`): The tick number when animation begins.

Useful for synchronizing multiple widgets without explicit SYNC calls:

```dsl
START_AT(10);  // This animation starts at tick 10
MOVE(RIGHT, 50) { step=1, interval=1 };
```

#### SEGMENT

**Syntax:** `SEGMENT(name, startTick, endTick) { ... } END;`
**Description:** Defines a named segment of animation between specific ticks.

* **name** (`IDENT`): Identifier for the segment.
* **startTick** (`Expr`): Tick when segment begins.
* **endTick** (`Expr`): Tick when segment ends.

Enables modular animation definition and optimization:

```dsl
SEGMENT(intro, 0, 20) {
    MOVE(RIGHT, 50) { step=5, interval=1 };
} END;

SEGMENT(main, 20, 100) {
    LOOP(8) {
        MOVE(LEFT, 10) { step=1, interval=1 };
        MOVE(RIGHT, 10) { step=1, interval=1 };
    } END;
} END;
```

#### POSITION_AT

**Syntax:** `POSITION_AT(tick) => { ... } END;`
**Description:** Defines a direct formula to calculate widget state at any tick.

* **tick** (`Expr`): The tick to calculate position for.

Provides deterministic positioning without simulation:

```dsl
// Direct calculation for scrolling text position
POSITION_AT(t) => {
    // Calculate x position based on tick number
    x = (startX - (t * stepSize) % (textWidth + gap));
    y = startY;
} END;
```

#### SCHEDULE_AT

**Syntax:** `SCHEDULE_AT(tick, action);`
**Description:** Schedules a specific action to occur at an absolute tick.

* **tick** (`Expr`): The tick when the action should occur.
* **action** (`IDENT`): The action to perform.

Provides absolute timing control:

```dsl
SCHEDULE_AT(50, reset_position);
SCHEDULE_AT(100, change_direction);
```

#### ON_VARIABLE_CHANGE

**Syntax:** 
```
ON_VARIABLE_CHANGE(variable) { ... } END;
ON_VARIABLE_CHANGE([var1, var2, ...]) { ... } END;
```

**Description:** Defines behavior when referenced variables change.

* **variable** (`IDENT` or array of `IDENT`): Variable(s) to monitor.

Example:

```dsl
// Handle when text content changes
ON_VARIABLE_CHANGE(content_text) {
    RECALCULATE_TIMELINE;
    RESET_POSITION();
} END;

// Monitor multiple variables
ON_VARIABLE_CHANGE([temperature, humidity]) {
    RECALCULATE_TIMELINE;
} END;
```

Note: The system automatically analyzes widget configurations to determine variable dependencies, making explicit declarations optional in most cases.

## 6. Widget State Access

The DSL provides access to widget and container properties through dot notation:

* **widget.x**, **widget.y**: Current widget position coordinates
* **widget.width**, **widget.height**: Current widget dimensions
* **widget.opacity**: Current opacity (if supported)
* **container.width**, **container.height**: Dimensions of the containing element
* **container.x**, **container.y**: Position of the container
* **current_tick**: The current tick count in the animation

## 7. Example Scripts

### A. Forever Marquee with Named Loop & Break

```dsl
LOOP(INFINITE AS marqueeLoop) {
    MOVE(widget.x, 0) { step=1, interval=10, easing=cubic_bezier(0.42,0,0.58,1) };
    IF(widget.x <= -widget.width) {
        BREAK;
    } END;
    PAUSE(2);
} END;
```

### B. Blink with Continue

```dsl
LOOP(3) {
    RESET_POSITION();
    PAUSE(20);
    SYNC(blink_complete);
    CONTINUE;   # skip any following statements in this iteration
} END;
```

### C. Complex Conditional

```dsl
IF(widget.x > container.width) {
    RESET_POSITION();
} ELSEIF(widget.opacity < 0.5) {
    MOVE(widget.x, container.height) { interval=5, easing=ease_out };
} ELSE {
    PAUSE(15);
} END;
```

### D. Scrolling Widget with Gap & Pauses

```dsl
/* 
 * Continuous scrolling with gap
 * - Scrolls from right to left
 * - Adds 10-pixel gap between repetitions
 */

// High-level approach:
SCROLL(LEFT, widget.width) { step=1, interval=1, gap=10 };

// Equivalent low-level approach:
LOOP(INFINITE) {
    MOVE(LEFT, widget.width) { step=1, interval=1, gap=10 };
    RESET_POSITION({ mode=seamless });
} END;
```

### E. Diagonal Movement (2D)

```dsl
# Move from top-left to bottom-right diagonally
MOVE(0, container.width, 0, container.height) { step=2, interval=1, easing=linear };
```

### F. Popup Animation Example

```dsl
// High-level popup (alternates between top and bottom content)
POPUP({ top_delay=20, bottom_delay=20, step=2 });

// Equivalent low-level implementation:
LOOP(INFINITE) {
    PAUSE(20);  // Pause at top
    MOVE(UP, widget.height - container.height) { step=2, interval=1 };
    PAUSE(20);  // Pause at bottom
    MOVE(DOWN, widget.height - container.height) { step=2, interval=1 };
} END;
```

### G. Slide Animation Example

```dsl
// High-level slide-in/out animation
SLIDE(IN_OUT, RIGHT, 100) { step=2, interval=1, pause=30 };

// Equivalent low-level implementation:
MOVE(LEFT, 100) { step=2, interval=1 };  // Move in from right
PAUSE(30);                              // Pause when fully visible
MOVE(RIGHT, 100) { step=2, interval=1 }; // Move out to right
```

### H. Optimized Looping Animation

```dsl
// Scrolling text with automatic tick calculation
LOOP(INFINITE) {
    MOVE(LEFT, text.width) { step=1, interval=1, gap=10 };
    RESET_POSITION({ mode=seamless });
} END;
PERIOD(text.width + 10);  // Period = content width + gap

// Direct calculation alternative
POSITION_AT(t) => {
    cycle_length = text.width + 10;
    cycle_position = t % cycle_length;
    
    // Initial position is at container right edge
    if (cycle_position == 0) {
        x = container.width;
    } else {
        x = container.width - cycle_position;
    }
} END;
```

### I. Synchronized Animations with Timeline Control

```dsl
// Widget 1: Title animation
SEGMENT(intro, 0, 50) {
    SLIDE(IN, LEFT, 100) { step=2, interval=1 };
} END;

// Widget 2: Automatically synchronized with Widget 1
START_AT(50);  // Starts when Widget 1's intro completes
SLIDE(IN, UP, 50) { step=1, interval=1 };

// Alternative to SYNC primitive
// System automatically derives relationship between widgets
```

## 8. Error Handling

The DSL processor should provide clear error messages for common issues:

* **Syntax errors**: Invalid command structures, missing parameters, unclosed blocks
* **Semantic errors**: Invalid property access, incompatible easing functions
* **Runtime errors**: Animations that would move widgets beyond valid boundaries
* **Performance warnings**: Animations that might cause performance issues (many widgets, complex easing)

Example validation checks:
1. Distance values are reasonable for the display size
2. Widget will remain at least partially visible during animation (unless intentionally moving off-screen)
3. Animation sequence lengths are reasonable for memory constraints
4. Expressions reference valid properties

## 9. Deterministic Rendering

The DSL is designed to enable deterministic rendering, allowing the system to:

1. **Calculate widget state for any arbitrary tick** without simulating all previous ticks
2. **Optimize repeating patterns** through period declarations
3. **Handle variable changes** by clearly defining timeline recalculation boundaries
4. **Coordinate multiple animations** through deterministic timelines

### 9.1 Automatic Dependency Analysis

The system automatically:

* Builds dependency graphs between widgets based on SYNC relationships
* Identifies variable references that affect widget state or content
* Creates widget clusters that must be calculated together
* Determines which calculations can be cached vs. recalculated

### 9.2 Timeline Optimization

For efficient rendering, the system:

* Identifies repeating patterns and period boundaries
* Uses direct POSITION_AT formulas when available
* Falls back to incremental simulation when necessary
* Caches rendered frames strategically

### 9.3 Handling Dynamic Events

When dynamic events occur (like variable changes):

1. The system identifies affected widgets
2. Invalidates cached frames in the affected timelines
3. Recalculates new deterministic timelines from that point forward


