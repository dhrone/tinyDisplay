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
    ;

IDENT            ::=  letter { letter | digit | "_" }* ;
NUMBER           ::=  digit { digit } [ "." { digit }+ ] ;
STRING           ::=  `"` {  ~`"`  | `\"`  }* `"` ;
BOOLEAN          ::=  "true" | "false" ;
```

## 3. Widget Definitions

### 3.1 Basic Widget Declaration

```ebnf
WidgetDecl       ::=  "DEFINE" "WIDGET" STRING "AS" WidgetType WidgetProps ;
WidgetType       ::=  "Text" | "Image" | "ProgressBar" | "Line" | "Rectangle" | "Scroll" | "Slide" | "PopUp" ;
WidgetProps      ::=  "{" { PropDecl } "}" ;
PropDecl         ::=  IDENT ":" PropValue "," ;
PropValue        ::=  STRING | NUMBER | BOOLEAN | Array | ObjectLiteral | VariableRef ;
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

### 3.2 Widget Properties Reference

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

## 4. Collection Definitions

### 4.1 Canvas

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

### 4.2 Stack

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

### 4.3 Sequence

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

### 4.4 Index

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

## 5. Animation

### 5.1 Timeline Definition

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

## 6. State Management

### 6.1 State Declaration

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

## 7. Theme and Style Definitions

### 7.1 Theme Declaration

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

### 7.2 Style Declaration

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

## 8. Data Sources and Bindings

### 8.1 Data Source Declaration

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

### 8.2 Variable Binding

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

## 9. Application Structure

### 9.1 Application Declaration

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

## 10. Complete Example

Below is a complete example demonstrating a weather station application:

```dsl
# Weather Station Application
# For 128x64 OLED Display

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
    font: "roboto.fnt",
    size: (0, 16)
}

DEFINE STYLE "value" {
    foreground: THEME.highlight,
    font: "roboto.fnt",
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
    font: "roboto.fnt",
    just: "lt"
}

DEFINE WIDGET "tempValue" AS Text {
    value: "{temperature}°C",
    size: (60, 16),
    foreground: THEME.highlight,
    background: THEME.background,
    font: "roboto.fnt",
    just: "lt"
}

DEFINE WIDGET "humidityLabel" AS Text {
    value: "Humidity:",
    size: (60, 16),
    foreground: THEME.foreground,
    background: THEME.background,
    font: "roboto.fnt",
    just: "lt"
}

DEFINE WIDGET "humidityValue" AS Text {
    value: "{humidity}%",
    size: (40, 16),
    foreground: THEME.highlight,
    background: THEME.background,
    font: "roboto.fnt",
    just: "lt"
}

DEFINE WIDGET "conditionText" AS Text {
    value: "{condition}",
    size: (128, 16),
    foreground: THEME.accent,
    background: THEME.background,
    font: "roboto.fnt",
    just: "lt"
}

# Define scrolling widgets
DEFINE WIDGET "scrollingCondition" AS Scroll {
    widget: "conditionText",
    size: (128, 16),
    
    TIMELINE {
        MOVE(LEFT, condition_width) { step=1, interval=2, gap=20 };
        RESET_POSITION({ mode=seamless });
        PERIOD(condition_width + 20);
    }
}

# Define layouts
DEFINE STACK "tempSection" {
    orientation: "horizontal",
    gap: 2,
    
    APPEND "tempLabel";
    APPEND "tempValue";
}

DEFINE STACK "humiditySection" {
    orientation: "horizontal",
    gap: 2,
    
    APPEND "humidityLabel";
    APPEND "humidityValue";
}

DEFINE CANVAS "homeScreen" {
    size: (128, 64),
    background: THEME.background,
    activeWhen: "{currentPage == 'home'}",
    
    PLACE "tempSection" AT (5, 10) Z 100;
    PLACE "humiditySection" AT (5, 30) Z 100;
    PLACE "scrollingCondition" AT (0, 48) Z 100;
}

# Define the application
DEFINE APP "weatherStation" {
    theme: "darkMode",
    defaultScreen: "homeScreen",
    size: (128, 64),
    
    SCREENS {
        REFERENCE "homeScreen";
    }
    
    DATASOURCES {
        REFERENCE "weather";
    }
}
```

This DSL enables complete application specification with widgets, layouts, animations, state management, and data binding - all while maintaining deterministic rendering capabilities. 