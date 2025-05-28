# tinyDisplay Application DSL Specification

This document defines a domain-specific language (DSL) for declaring complete tinyDisplay applications, including widget definitions, layouts, animations, and data sources. The DSL provides a declarative approach to creating resource-efficient displays for embedded systems.

## 1. Overview

The Application DSL allows you to:

* Define **widget instances** of various types (text, images, progress bars, etc.)
* Organize widgets into **collections** (canvases, stacks, sequences)
* Create **animations** with deterministic behavior
* Manage application **state** and conditional rendering
* Define **themes** and reusable styles
* Configure **data sources** and variable bindings
* Structure your complete **application** in a single specification
* Configure **hardware display** parameters
* Specify file **resource paths** for external assets
* Create **macros** for reusable configuration
* **Import** external DSL files for modular organization

## 2. Lexical Structure

```ebnf
WHITESPACE       ::=  ( " " | "\t" | "\r" | "\n" )+ ;
COMMENT          ::=  
      "#" { any_char_except_newline }*  ( "\n" | EOF )
    | "/*" { any_char_except_end_comment }* "*/"
    ;

KEYWORD          ::=  
      "DEFINE" | "AS" | "WIDGET" | "CANVAS" | "STACK" | "SEQUENCE" | "INDEX"
    | "PLACE" | "APPEND" | "AT" | "Z" | "WHEN" | "ACTIVE" | "DEFAULT"
    | "THEME" | "STYLE" | "STATE" | "DATASOURCE" | "BIND" | "TO" | "APP"
    | "REFERENCE" | "SCREENS" | "DATASOURCES" | "TIMELINE" | "ORIENTATION"
    | "IMPORT" | "FROM" | "MACRO" | "DISPLAY" | "RESOURCES" | "PATH"
    | "INTERFACE" | "COLOR_MODE" | "PINS" | "ENV" | "FILE" | "SEARCH_PATH"
    ;

IDENT            ::=  letter { letter | digit | "_" }* ;
NUMBER           ::=  digit { digit } [ "." { digit }+ ] ;
STRING           ::=  `"` {  ~`"`  | `\"`  }* `"` ;
BOOLEAN          ::=  "true" | "false" ;
PATH             ::=  STRING | [ "$" IDENT "/" ] { IDENT "/" }* { IDENT [ "." IDENT ] } ;
FILE_PATH        ::=  PATH | STRING ;
MACRO_REF        ::=  "@" IDENT [ "." IDENT ]* ;
```

## 3. Import and Resource Management

### 3.1 Import Declaration

```ebnf
ImportStmt       ::=  "IMPORT" ( ImportAll | ImportNames ) "FROM" PATH ";" ;
ImportAll        ::=  "*" ;
ImportNames      ::=  IDENT { "," IDENT } ;
```

**Description:** Imports definitions from external DSL files. This allows you to organize code in multiple files and reuse common configurations.

**Example:**
```dsl
# Import everything from a display configuration file
IMPORT * FROM "displays/ssd1306_128x64.dsl";

# Import specific definitions
IMPORT darkTheme, lightTheme FROM "themes/common.dsl";
```

### 3.2 Resource Paths

```ebnf
ResourcesBlock   ::=  "DEFINE" "RESOURCES" "{" { ResourceDecl } "}" ;
ResourceDecl     ::=  DirDecl | FileDecl | SearchPathDecl ;
DirDecl          ::=  PathType ":" PATH ";" ;
FileDecl         ::=  "FILE" IDENT ":" FILE_PATH ";" ;
SearchPathDecl   ::=  "SEARCH_PATH" PathType ":" "[" PATH { "," PATH } "]" ";" ;
PathType         ::=  "fonts" | "images" | "icons" | "sounds" | "data" | "base";
```

**Description:** Defines paths where external resources can be found. Resources can be defined as:
- Directory paths: Used as base locations for resource types
- Specific file paths: Referenced by name for direct file access
- Search paths: Ordered lists of directories to search for resources

The `SEARCH_PATH` directive defines an ordered list of directories to search when looking for resources of a specific type. This works similarly to how the $PATH environment variable works in Unix-like systems.

**Example:**
```dsl
DEFINE RESOURCES {
    # Directory paths
    base: "/home/pi/myapp/";
    
    # Specific file paths
    FILE default_font: "resources/fonts/default.fnt";
    FILE logo: "/absolute/path/to/logo.png";
    
    # Search paths
    SEARCH_PATH fonts: [
        "resources/fonts/",
        "/usr/local/share/fonts/",
        "@ENV.USER_FONTS_DIR",
        "/system/fonts/"
    ];
    
    SEARCH_PATH images: [
        "resources/images/",
        "@ENV.APP_HOME/shared/images/",
        "/usr/share/images/"
    ];
}
```

**Usage in widgets:**
```dsl
# When using a resource type with a search path defined:
DEFINE WIDGET "title" AS Text {
    # Will search for "roboto.fnt" in each directory in the fonts search path
    # in the order specified until found
    font: "roboto.fnt",
    // ...
}

# You can still use explicit paths
DEFINE WIDGET "special" AS Text {
    font: "/absolute/path/to/special.fnt",
    // ...
}

# Or direct file references
DEFINE WIDGET "heading" AS Text {
    font: RESOURCES.default_font,
    // ...
}
```

### 3.3 Environment Variables

```ebnf
EnvBlock         ::=  "DEFINE" "ENV" "{" { EnvDecl } "}" ;
EnvDecl          ::=  IDENT ":" STRING ";" ;
```

**Description:** Defines environment variables that can be used in resource paths and configurations.

**Example:**
```dsl
DEFINE ENV {
    APP_HOME: "$HOME/myapp";
    DISPLAY_TYPE: "ssd1306";
}
```

## 4. Macro Definitions

### 4.1 Macro Declaration

```ebnf
MacroDecl        ::=  "DEFINE" "MACRO" IDENT [ "(" [ MacroParams ] ")" ] MacroValue ";" ;
MacroParams      ::=  MacroParam { "," MacroParam } ;
MacroParam       ::=  IDENT [ "=" PropValue ] ;
MacroValue       ::=  PropValue ;
```

**Description:** Defines reusable values that can be referenced throughout the DSL. Macros can be simple constants or parameterized expressions.

**Example:**
```dsl
# Simple value macros
DEFINE MACRO DEFAULT_PADDING 5;
DEFINE MACRO HEADER_HEIGHT 20;
DEFINE MACRO SCREEN_WIDTH 128;
DEFINE MACRO SCREEN_HEIGHT 64;

# Parameterized macros
DEFINE MACRO CENTERED_POS(width, height) {
    x: (SCREEN_WIDTH - width) / 2,
    y: (SCREEN_HEIGHT - height) / 2
};
```

### 4.2 Macro Usage

Macros are referenced using the `@` symbol followed by the macro name. Parameterized macros accept arguments in parentheses.

**Example:**
```dsl
DEFINE WIDGET "header" AS Rectangle {
    xy: [0, 0, @SCREEN_WIDTH, @HEADER_HEIGHT],
    fill: "black",
    outline: "white"
}

DEFINE WIDGET "centeredText" AS Text {
    value: "Hello World",
    size: (80, 20),
    position: @CENTERED_POS(80, 20),
    just: "mm"
}
```

## 5. Display Configuration

### 5.1 Display Declaration

```ebnf
DisplayDecl      ::=  "DEFINE" "DISPLAY" STRING DisplayProps ;
DisplayProps     ::=  "{" { PropDecl | InterfaceBlock } "}" ;
InterfaceBlock   ::=  "INTERFACE" "{" { PropDecl } "}" ;
```

**Description:** Defines the physical display configuration including dimensions, color mode, and hardware interface details.

**Example:**
```dsl
DEFINE DISPLAY "main" {
    width: 128,
    height: 64,
    color_mode: "1",    # 1-bit monochrome
    rotation: 0,        # 0, 90, 180, or 270 degrees
    
    INTERFACE {
        type: "spi",
        bus: 0,
        device: 0,
        reset_pin: 24,
        dc_pin: 23,
        contrast: 128,
        backlight_pin: 18,
        invert: false
    }
}

# Alternative interface example (I2C)
DEFINE DISPLAY "secondary" {
    width: 128,
    height: 32,
    color_mode: "1",
    
    INTERFACE {
        type: "i2c",
        address: "0x3C",
        bus: 1,
        reset_pin: 17
    }
}

# GPIO bitbang example
DEFINE DISPLAY "lcd1602" {
    width: 16,            # characters, not pixels
    height: 2,            # lines
    color_mode: "custom", # Character-based display
    
    INTERFACE {
        type: "gpio_parallel",
        rs_pin: 26,
        e_pin: 19,
        data_pins: [13, 6, 5, 7],  # 4-bit mode
        backlight_pin: 12,
        backlight_mode: "active_high"
    }
}
```

### 5.2 Supported Color Modes

| Mode | Description |
|------|-------------|
| "1" | 1-bit monochrome (black and white) |
| "L" | 8-bit grayscale |
| "RGB" | 24-bit color without alpha |
| "RGBA" | 32-bit color with alpha |
| "custom" | Special mode for character-based displays |

## 6. Widget Definitions

### 6.1 Basic Widget Declaration

```ebnf
WidgetDecl       ::=  "DEFINE" "WIDGET" STRING "AS" WidgetType WidgetProps ;
WidgetType       ::=  "Text" | "Image" | "ProgressBar" | "Line" | "Rectangle" | "Scroll" | "Slide" | "PopUp" ;
WidgetProps      ::=  "{" { PropDecl } "}" ;
PropDecl         ::=  IDENT ":" PropValue "," ;
PropValue        ::=  STRING | NUMBER | BOOLEAN | Array | ObjectLiteral | VariableRef | MACRO_REF ;
Array            ::=  "[" [ PropValue { "," PropValue } ] "]" ;
ObjectLiteral    ::=  "{" { PropDecl } "}" ;
VariableRef      ::=  "{" IDENT [ "." IDENT ]* "}" ;
```

**Description:** Creates a named widget instance with specified properties. Each widget has type-specific properties and common properties inherited from the base widget class.

**Example:**
```dsl
DEFINE WIDGET "temperatureLabel" AS Text {
    value: "Temperature:",
    size: (64, 16),
    foreground: "white",
    background: "black",
    font: "hd44780.fnt",
    just: "lt"
}

DEFINE WIDGET "tempValue" AS Text {
    value: "{temperature} °C",
    size: (40, 16),
    foreground: "#33cc33",
    background: "black",
    font: "hd44780.fnt",
    just: "lt",
    activeWhen: "{temperature != null}"
}

DEFINE WIDGET "dividerLine" AS Line {
    xy: [0, 20, 128, 20],
    fill: "white",
    width: 1
}
```

### 6.2 Widget Properties Reference

Common properties available to all widgets:

| Property | Type | Description |
|----------|------|-------------|
| size | (int, int) | Width and height in pixels |
| activeWhen | bool/expr | Condition for widget visibility |
| duration | int | Ticks to remain active |
| minDuration | int | Minimum ticks to stay active |
| coolingPeriod | int | Ticks before widget can return to active |
| overRun | bool | Should widget remain active past active state |
| foreground | color | Color for foreground elements |
| background | color | Color for background elements |
| just | string | Justification (lt, mt, rt, lm, mm, rm, lb, mb, rb) |
| trim | string | Whether to trim image after render |

Type-specific properties reference each widget type's unique attributes, such as:

**Text Widget:**
- value: The text content (string or variable)
- font: Font to use
- wrap: Whether to wrap text
- lineSpacing: Pixels between lines

**ProgressBar Widget:**
- value: Current value
- range: (min, max) range
- direction: Fill direction (ltr, rtl, ttb, btt)
- fill: Fill color

## 7. Collection Definitions

### 7.1 Canvas

```ebnf
CanvasDecl       ::=  "DEFINE" "CANVAS" STRING CanvasProps ;
CanvasProps      ::=  "{" { PropDecl | PlaceStmt } "}" ;
PlaceStmt        ::=  "PLACE" STRING "AT" Placement [ "Z" NUMBER ] ";" ;
Placement        ::=  Coordinates [ Just ] ;
Coordinates      ::=  "(" NUMBER "," NUMBER ")" ;
Just             ::=  STRING ;
```

**Description:** A canvas is a container for organizing multiple widgets. Widgets can be placed at specific coordinates with z-order control (higher z values appear on top).

**Example:**
```dsl
DEFINE CANVAS "statusScreen" {
    size: (128, 64),
    background: "black",
    
    PLACE "temperatureLabel" AT (10, 5) Z 100;
    PLACE "tempValue" AT (80, 5) Z 100;
    PLACE "dividerLine" AT (0, 20) Z 50;
    PLACE "humiditySection" AT (0, 25) Z 100;
}
```

### 7.2 Stack

```ebnf
StackDecl        ::=  "DEFINE" "STACK" STRING StackProps ;
StackProps       ::=  "{" { PropDecl | AppendStmt } "}" ;
AppendStmt       ::=  "APPEND" STRING [ "GAP" NUMBER ] ";" ;
```

**Description:** A stack arranges widgets sequentially in horizontal or vertical orientation, automatically calculating layout. The container expands to fit its contents.

**Example:**
```dsl
DEFINE STACK "statusRow" {
    orientation: "horizontal",
    gap: 2,
    background: "black",
    
    APPEND "wifiIcon";
    APPEND "batteryIcon" GAP 5;
    APPEND "timeWidget";
}
```

### 7.3 Sequence

```ebnf
SequenceDecl     ::=  "DEFINE" "SEQUENCE" STRING SequenceProps ;
SequenceProps    ::=  "{" { PropDecl | SeqAppendStmt } "}" ;
SeqAppendStmt    ::=  "APPEND" STRING [ "ACTIVE" "WHEN" ConditionExpr ] ";" ;
ConditionExpr    ::=  STRING | VariableRef ;
```

**Description:** A sequence displays one widget at a time from a collection, cycling through active widgets. Used for multi-screen interfaces or alternating displays.

**Example:**
```dsl
DEFINE SEQUENCE "mainScreens" {
    defaultCanvas: "welcomeScreen",
    size: (128, 64),
    
    APPEND "homeScreen" ACTIVE WHEN "{page == 'home'}";
    APPEND "settingsScreen" ACTIVE WHEN "{page == 'settings'}";
    APPEND "graphScreen" ACTIVE WHEN "{page == 'graph'}";
}
```

### 7.4 Index

```ebnf
IndexDecl        ::=  "DEFINE" "INDEX" STRING IndexProps ;
IndexProps       ::=  "{" { PropDecl | IdxAppendStmt } "}" ;
IdxAppendStmt    ::=  "APPEND" STRING ";" ;
```

**Description:** An index displays one widget based on a numeric value (0-based). Useful for state-based displays like volume levels, signal strength, or battery indicators.

**Example:**
```dsl
DEFINE INDEX "volumeDisplay" {
    value: "{volume_level}",  # 0-4 value
    size: (24, 16),
    
    APPEND "volumeMuted";    # index 0
    APPEND "volumeLow";      # index 1
    APPEND "volumeMedium";   # index 2
    APPEND "volumeHigh";     # index 3
    APPEND "volumeMax";      # index 4
}
```

## 8. Animation

### 8.1 Timeline Definition

```ebnf
TimelineBlock    ::=  "TIMELINE" "{" { TimelineStmt } "}" ;
TimelineStmt     ::=  MarqueeStmt ;  # Refer to marquee DSL grammar
```

**Description:** Defines animations using the Marquee Animation DSL. Can be included in scrolling, sliding, or popup widget definitions.

**Example:**
```dsl
DEFINE WIDGET "scrollingHeadline" AS Scroll {
    widget: "headlineText",
    size: (128, 16),
    
    TIMELINE {
        PERIOD(headline_width + 20);
        MOVE(LEFT, headline_width) { step=1, interval=1, gap=20 };
        RESET_POSITION({ mode=seamless });
    }
}
```

## 9. State Management

### 9.1 State Declaration

```ebnf
StateDecl        ::=  "DEFINE" "STATE" STRING "AS" StateType [ "DEFAULT" PropValue ] ";" ;
StateType        ::=  "BOOL" | "NUMBER" | "STRING" | "OBJECT" ;
```

**Description:** Defines application state variables that can be referenced by widgets. States are mutable and can trigger UI updates when changed.

**Example:**
```dsl
DEFINE STATE "showDetails" AS BOOL DEFAULT false;
DEFINE STATE "selectedItem" AS NUMBER DEFAULT 0;
DEFINE STATE "userName" AS STRING DEFAULT "Guest";
```

## 10. Theme and Style Definitions

### 10.1 Theme Declaration

```ebnf
ThemeDecl        ::=  "DEFINE" "THEME" STRING ThemeProps ;
ThemeProps       ::=  "{" { PropDecl } "}" ;
```

**Description:** Defines a collection of styling properties that can be applied across multiple widgets. Themes help maintain consistent appearance and enable easy switching between visual styles.

**Example:**
```dsl
DEFINE THEME "darkMode" {
    background: "#000000",
    foreground: "#ffffff",
    accent: "#33cc33",
    highlight: "#ff9900",
    fontPrimary: "roboto.fnt",
    fontSecondary: "smallFont.fnt"
}

DEFINE THEME "lightMode" {
    background: "#ffffff",
    foreground: "#000000",
    accent: "#0066cc",
    highlight: "#ff6600",
    fontPrimary: "roboto.fnt",
    fontSecondary: "smallFont.fnt"
}
```

### 10.2 Style Declaration

```ebnf
StyleDecl        ::=  "DEFINE" "STYLE" STRING StyleProps ;
StyleProps       ::=  "{" { PropDecl } "}" ;
```

**Description:** Defines reusable property sets that can be applied to widgets. Styles can reference theme properties using dot notation.

**Example:**
```dsl
DEFINE STYLE "heading" {
    foreground: THEME.accent,
    font: THEME.fontPrimary,
    size: (0, 16),  # Auto-width
    just: "mt"
}

DEFINE STYLE "normalText" {
    foreground: THEME.foreground,
    font: THEME.fontSecondary,
    size: (0, 12),  # Auto-width
    just: "lt"
}
```

## 11. Data Sources and Bindings

### 11.1 Data Source Declaration

```ebnf
DatasourceDecl   ::=  "DEFINE" "DATASOURCE" STRING DatasourceProps ;
DatasourceProps  ::=  "{" { PropDecl } "}" ;
```

**Description:** Defines external data sources that can provide values to widgets. Supports various types like HTTP APIs, sensor readings, or system information.

**Example:**
```dsl
DEFINE DATASOURCE "weather" {
    type: "http",
    url: "https://api.example.com/weather?location={location}",
    refresh: 300,  # Seconds
    mapping: {
        "temperature": "$.current.temp_c",
        "humidity": "$.current.humidity",
        "condition": "$.current.condition.text"
    }
}

DEFINE DATASOURCE "system" {
    type: "system",
    refresh: 10,  # Seconds
    properties: ["batteryLevel", "wifiSignal", "memoryUsage"]
}
```

### 11.2 Variable Binding

```ebnf
BindingDecl      ::=  "BIND" VariableRef "TO" BindTarget ";" ;
BindTarget       ::=  IDENT [ "." IDENT ]* ;
```

**Description:** Creates a binding between a variable reference and a data source property. When the data source updates, all widgets using the bound variable will update.

**Example:**
```dsl
BIND "{temperature}" TO "weather.temperature";
BIND "{humidity}" TO "weather.humidity";
BIND "{batteryLevel}" TO "system.batteryLevel";
```

## 12. Application Structure

### 12.1 Application Declaration

```ebnf
AppDecl          ::=  "DEFINE" "APP" STRING AppProps ;
AppProps         ::=  "{" { PropDecl | ScreensBlock | DatasourcesBlock } "}" ;
ScreensBlock     ::=  "SCREENS" "{" { ReferenceStmt } "}" ;
DatasourcesBlock ::=  "DATASOURCES" "{" { ReferenceStmt } "}" ;
ReferenceStmt    ::=  "REFERENCE" STRING ";" ;
```

**Description:** Defines the overall application structure, including which screens and data sources to use. This is the top-level container for a tinyDisplay application.

**Example:**
```dsl
DEFINE APP "weatherStation" {
    theme: "darkMode",
    defaultScreen: "homeScreen",
    size: (128, 64),
    refreshRate: 30,  # FPS
    
    SCREENS {
        REFERENCE "homeScreen";
        REFERENCE "detailsScreen";
        REFERENCE "settingsScreen";
    }
    
    DATASOURCES {
        REFERENCE "weather";
        REFERENCE "system";
    }
}
```

## 13. Platform and Input Configuration

### 13.1 Input Device Configuration

```ebnf
InputDecl        ::=  "DEFINE" "INPUT" STRING InputProps ;
InputProps       ::=  "{" { PropDecl | InputEventBlock } "}" ;
InputEventBlock  ::=  "EVENT" STRING "{" { PropDecl } "}" ;
```

**Description:** Defines input devices like buttons, rotary encoders, or touch screens and their event mappings.

**Example:**
```dsl
DEFINE INPUT "buttons" {
    type: "gpio",
    
    EVENT "button_up" {
        pin: 5,
        mode: "pullup",
        active: "low",
        action: "SET_STATE(currentPage, 'prev')"
    }
    
    EVENT "button_down" {
        pin: 6,
        mode: "pullup",
        active: "low",
        action: "SET_STATE(currentPage, 'next')"
    }
    
    EVENT "button_select" {
        pin: 13,
        mode: "pullup",
        active: "low",
        action: "SET_STATE(showDetails, true)"
    }
}

DEFINE INPUT "rotary" {
    type: "encoder",
    clk_pin: 17,
    dt_pin: 18,
    sw_pin: 27,
    
    EVENT "rotate_cw" {
        action: "ADJUST_VALUE(volume, +1)"
    }
    
    EVENT "rotate_ccw" {
        action: "ADJUST_VALUE(volume, -1)"
    }
    
    EVENT "press" {
        action: "TOGGLE_STATE(muted)"
    }
}
```

### 13.2 Localization

```ebnf
LocalizationDecl ::=  "DEFINE" "LOCALIZATION" "{" { LocaleBlock } "}" ;
LocaleBlock      ::=  "LOCALE" STRING "{" { StringDecl } "}" ;
StringDecl       ::=  IDENT ":" STRING ";" ;
```

**Description:** Defines localized strings that can be referenced in widgets.

**Example:**
```dsl
DEFINE LOCALIZATION {
    LOCALE "en" {
        temp_label: "Temperature:";
        humidity_label: "Humidity:";
        pressure_label: "Pressure:";
    }
    
    LOCALE "fr" {
        temp_label: "Température:";
        humidity_label: "Humidité:";
        pressure_label: "Pression:";
    }
}

# Reference in widgets
DEFINE WIDGET "tempLabel" AS Text {
    value: "{strings.temp_label}",
    // ...
}
```

## 14. Complete Example

Below is an extended complete example with the new features:

```dsl
# Weather Station Application for Raspberry Pi
# For SSD1306 128x64 OLED Display

# Resource paths
DEFINE RESOURCES {
    base: "@ENV.APP_HOME";
    
    # Specific file resources
    FILE default_font: "resources/fonts/roboto.fnt";
    FILE weather_icons: "resources/images/weather_icons.png";
    FILE logo: "@ENV.APP_HOME/logo.png";
    
    # Search paths
    SEARCH_PATH fonts: [
        "resources/fonts/",
        "@ENV.USER_FONTS_DIR",
        "/usr/share/fonts/"
    ];
    
    SEARCH_PATH images: [
        "resources/images/",
        "@ENV.APP_HOME/shared/images/"
    ];
}

# Environment variables
DEFINE ENV {
    APP_HOME: "/home/pi/weatherstation";
    USER_FONTS_DIR: "/home/pi/.fonts";
}

# Common macros
DEFINE MACRO SCREEN_WIDTH 128;
DEFINE MACRO SCREEN_HEIGHT 64;
DEFINE MACRO HEADER_HEIGHT 16;
DEFINE MACRO CONTENT_Y @HEADER_HEIGHT + 2;
DEFINE MACRO CONTENT_HEIGHT @SCREEN_HEIGHT - @CONTENT_Y;

# Display configuration
DEFINE DISPLAY "oled" {
    width: @SCREEN_WIDTH,
    height: @SCREEN_HEIGHT,
    color_mode: "1",
    
    INTERFACE {
        type: "spi",
        bus: 0,
        device: 0,
        reset_pin: 24,
        dc_pin: 23
    }
}

# Input configuration
DEFINE INPUT "controls" {
    type: "gpio",
    
    EVENT "next_page" {
        pin: 5,
        mode: "pullup",
        active: "low",
        action: "SET_STATE(currentPage, 'next')"
    }
    
    EVENT "prev_page" {
        pin: 6,
        mode: "pullup",
        active: "low",
        action: "SET_STATE(currentPage, 'prev')"
    }
}

# Define themes
DEFINE THEME "darkMode" {
    background: "#000000",
    foreground: "#ffffff",
    accent: "#33cc33",
    highlight: "#ff9900"
}

# Define styles
DEFINE STYLE "heading" {
    foreground: THEME.accent,
    font: RESOURCES.fonts + "roboto.fnt",
    size: (0, 16)
}

DEFINE STYLE "value" {
    foreground: THEME.highlight,
    font: RESOURCES.fonts + "roboto.fnt",
    size: (0, 16)
}

# Define data sources
DEFINE DATASOURCE "weather" {
    type: "http",
    url: "https://api.example.com/weather?location=London",
    refresh: 300,
    mapping: {
        "temperature": "$.current.temp_c",
        "humidity": "$.current.humidity",
        "condition": "$.current.condition.text"
    }
}

# Define state
DEFINE STATE "currentPage" AS STRING DEFAULT "home";

# Bind variables
BIND "{temperature}" TO "weather.temperature";
BIND "{humidity}" TO "weather.humidity";
BIND "{condition}" TO "weather.condition";

# Define basic widgets
DEFINE WIDGET "tempLabel" AS Text {
    value: "Temp:",
    size: (40, 16),
    foreground: THEME.foreground,
    background: THEME.background,
    font: RESOURCES.fonts + "roboto.fnt",
    just: "lt"
}

DEFINE WIDGET "tempValue" AS Text {
    value: "{temperature}°C",
    size: (60, 16),
    foreground: THEME.highlight,
    background: THEME.background,
    font: RESOURCES.fonts + "roboto.fnt",
    just: "lt"
}

# ...rest of widgets as before...

# Define the application
DEFINE APP "weatherStation" {
    theme: "darkMode",
    defaultScreen: "homeScreen",
    size: (@SCREEN_WIDTH, @SCREEN_HEIGHT),
    display: "oled",
    
    SCREENS {
        REFERENCE "homeScreen";
    }
    
    DATASOURCES {
        REFERENCE "weather";
    }
    
    INPUTS {
        REFERENCE "controls";
    }
}
```

## 15. Implementation Considerations

### 15.1 Deterministic Rendering

The DSL is designed to support deterministic rendering, which means:

1. Widget positions and states can be calculated for any arbitrary tick
2. Timeline-based animations use the tick as their core timing mechanism
3. System can optimize rendering by pre-calculating or caching commonly used frames
4. State changes trigger predictable UI updates with proper invalidation of affected regions

### 15.2 Resource Management

Resource loading follows these principles:

1. Resources are loaded at application initialization when possible
2. External fonts and images should be cached to minimize I/O operations
3. Path resolution follows a deterministic search order:
   - Explicit resource files defined with `FILE` are used directly
   - For concatenated paths (RESOURCES.dir + "filename"):
     - Absolute paths (starting with "/" or drive letter) are used as-is
     - Relative paths are resolved against the specified resource directory
     - If resource directory is not found, paths are resolved relative to the importing DSL file
     - If still not found, default resource locations are checked
   - For resource types with a `SEARCH_PATH` defined, when a filename without a path is specified:
     - Each directory in the search path is checked in order
     - The first matching file found is used
     - If no match is found in any search path directory, an error is reported
4. Environment variables in paths (prefixed with "$" or "@ENV.") are expanded before resolution
5. Path normalization removes redundant elements like ".." and "."

**Example of path resolution with search paths:**
```dsl
# Given these resource definitions:
DEFINE ENV {
    APP_HOME: "/home/pi/myapp";
    USER_FONTS_DIR: "/home/pi/.fonts";
}

DEFINE RESOURCES {
    base: "@ENV.APP_HOME";
    FILE special_font: "/opt/fonts/special.fnt";
    
    SEARCH_PATH fonts: [
        "resources/fonts/",
        "@ENV.USER_FONTS_DIR",
        "/usr/share/fonts/"
    ];
}

# These paths resolve as follows:
# RESOURCES.special_font → "/opt/fonts/special.fnt" (direct file reference)
#
# For a widget with font: "roboto.fnt", search:
# 1. "/home/pi/myapp/resources/fonts/roboto.fnt"
# 2. "/home/pi/.fonts/roboto.fnt"
# 3. "/usr/share/fonts/roboto.fnt"
# Use the first one found
#
# For a widget with font: "/absolute/path/roboto.fnt"
# → "/absolute/path/roboto.fnt" (absolute path used directly)
```

### 15.3 Error Handling

The DSL processor should provide clear error messages for:

1. Syntax errors in the DSL code
2. Missing or invalid resources
3. Hardware configuration errors
4. Data binding errors
5. Invalid state references

Error messages should include file and line numbers to assist in debugging.

## 16. Extensions

The DSL is designed to be extensible for future capabilities:

1. **Custom Widget Types**: Framework allows defining new widget types with custom rendering
2. **Animations**: The animation system can be extended with new movement types
3. **Data Sources**: New data source types can be added to connect to different systems
4. **Display Drivers**: Support for additional display hardware can be added
5. **Input Methods**: New input device types can be supported

This DSL enables complete application specification with widgets, layouts, animations, state management, and data binding - all while maintaining deterministic rendering capabilities. 