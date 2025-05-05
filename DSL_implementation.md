# tinyDisplay DSL Implementation Plan

## 1. Context for Future Sessions

This document outlines the implementation plan for two Domain-Specific Languages (DSLs) designed for the tinyDisplay library:

1. **Marquee Animation DSL** (defined in `marquee_class_dsl.md`): A declarative language for defining deterministic animations for resource-constrained displays. It focuses on tick-based timing and pixel-precise movement, enabling efficient animations that can be calculated for any arbitrary tick.

2. **Application Widget DSL** (defined in `application_widget_dsl.md`): A comprehensive language for defining entire tinyDisplay applications, including widget definitions, layouts, animations, state management, themes, data sources, and hardware configuration.

These DSLs will replace the current imperative programming approach to configuring tinyDisplay applications with a declarative, more maintainable approach that:

- Improves developer productivity
- Ensures deterministic rendering
- Enables resource optimization
- Provides clearer separation between UI definition and business logic
- Supports modular, reusable components

The implementation should be treated as a significant refactoring of the tinyDisplay library, focusing on preserving functionality while changing the interface. The existing widget and collection modules provide the underlying functionality, but the way developers interact with them will shift from direct Python instantiation to DSL-based declaration.

## 2. Architectural Overview

The DSL implementation consists of the following major components:

### 2.1 Parser System
- **Lexer**: Transforms DSL text into tokens
- **Parser**: Converts token streams into an Abstract Syntax Tree (AST)
- **Validator**: Ensures DSL semantics are correct before execution

### 2.2 Object Model
- **AST Nodes**: Represent DSL constructs in memory
- **Runtime Objects**: Executable widget and animation components
- **Configuration Objects**: Hold display, resource, and theme settings

### 2.3 Execution Engine
- **Interpreter**: Converts AST into runtime objects
- **Renderer**: Manages the display pipeline and optimization
- **Scheduler**: Handles timing and animation coordination
- **State Manager**: Maintains application state and triggers updates

### 2.4 Resource System
- **Resource Resolver**: Implements path resolution rules
- **Asset Manager**: Loads and caches fonts, images, etc.
- **Import Manager**: Handles DSL imports and dependencies

## 3. Implementation Steps

### Phase 1: Foundational Components

#### Step 1: Parsing Infrastructure
1. **Create Lexer**
   - Implement token definitions for all DSL keywords, identifiers, literals
   - Handle comments and whitespace according to the grammar
   - Setup error reporting with line and column information

2. **Develop Parser**
   - Implement recursive descent parser or use a parser generator
   - Create AST node classes matching the DSL grammar structure
   - Ensure proper error handling with meaningful messages

3. **Build Validator**
   - Type checking for expressions and values
   - Semantic validation (reference checking, scope validation)
   - Cycle detection in dependencies

#### Step 2: Core Runtime Framework
1. **Refactor Base Widget System**
   - Modify the existing widget class to support deterministic rendering
   - Implement tick-based animation timing (PERIOD, POSITION_AT, etc.)
   - Add support for timelines and movement calculations

2. **Develop State Management System**
   - Create observable state objects
   - Implement dependency tracking for efficient updates
   - Set up event propagation system

3. **Build Resource Management System**
   - Implement path resolution rules
   - Create caching and preloading mechanisms
   - Handle search paths and file references

### Phase 2: Marquee Animation Implementation

#### Step 3: Marquee DSL Parser
1. **Implement Marquee-Specific Grammar**
   - Direction constants (LEFT, RIGHT, UP, DOWN)
   - Movement commands (MOVE, PAUSE, RESET_POSITION)
   - Control flow (LOOP, IF/ELSE, BREAK, CONTINUE)
   - Timeline optimization commands (PERIOD, START_AT, POSITION_AT)

2. **Create Animation Timeline System**
   - Implement tick-based animation timeline
   - Add support for synchronization between widgets
   - Handle period-based optimizations

#### Step 4: Animation Engine
1. **Refactor Marquee Classes**
   - Update scroll, slide, and popUp classes
   - Add support for DSL-defined timelines
   - Implement deterministic position calculations

2. **Implement Movement Primitives**
   - Create direct pixel movement with controllable steps
   - Add easing functions support
   - Implement position resets and boundary handling

### Phase 3: Application Widget Implementation

#### Step 5: Application DSL Parser
1. **Implement Application Grammar**
   - Widget definition and properties
   - Collection types (Canvas, Stack, Sequence, Index)
   - Theme and style definitions
   - Resource and import handling

2. **Create Config Object System**
   - Display configuration objects
   - Theme and style registries
   - Resource mapping and search paths

#### Step 6: Widget Factory System
1. **Create Factory Registry**
   - Register widget types and their constructors
   - Set up property mapping between DSL and widget objects
   - Implement parameterized instantiation

2. **Implement Collection Factories**
   - Canvas factory with placement logic
   - Stack factory with orientation handling
   - Sequence and Index factories with item management

### Phase 4: Integration and Utilities

#### Step 7: Import and Resource System
1. **Implement Import Mechanism**
   - Parse and process import statements
   - Resolve file dependencies
   - Handle circular import detection

2. **Create Environment and Macro System**
   - Environment variable resolution
   - Macro expansion and parameterization
   - Resource path normalization

#### Step 8: Application Runner
1. **Develop Application Loader**
   - Load and parse application DSL files
   - Instantiate application structure
   - Set up data sources and bindings

2. **Create Command-line Interface**
   - DSL file validation tool
   - Application runner with optional debug mode
   - Resource verification utilities

### Phase 5: Optimization and Testing

#### Step 9: Rendering Optimization
1. **Implement Smart Caching**
   - Cache rendered frames for periodic animations
   - Implement partial screen updates
   - Add dirty region tracking

2. **Add Frame Prediction**
   - Leverage deterministic animations for precomputation
   - Implement on-demand rendering based on viewing window

#### Step 10: Testing Infrastructure
1. **Create DSL Unit Test Framework**
   - Parser test utilities
   - Animation assertion helpers
   - Mock display system

2. **Build Example Applications**
   - Create sample applications using the DSL
   - Document common patterns and best practices
   - Develop tutorials and migration guides

## 4. Classes to Add or Modify

### 4.1 New Classes

#### DSL.Parser
**Requirements:**
- Parse DSL text into AST
- Report syntax errors with line/column information
- Support both marquee and application grammars
- Handle imports and includes

#### DSL.AST
**Requirements:**
- Represent all DSL constructs as node objects
- Maintain source location information
- Support visitor pattern for traversal
- Include serialization/deserialization

#### DSL.Interpreter
**Requirements:**
- Convert AST to runtime objects
- Process macros and environment variables
- Handle variable scoping
- Resolve references and dependencies

#### DSL.ResourceManager
**Requirements:**
- Implement search path resolution
- Load and cache external resources
- Manage resource lifetimes
- Handle file not found and other I/O errors

#### DSL.StateManager
**Requirements:**
- Maintain application state variables
- Track dependencies between state and UI
- Trigger updates when state changes
- Support transactions for atomic updates

#### DSL.Timeline
**Requirements:**
- Represent animation timeline with keyframes
- Calculate widget state for any arbitrary tick
- Support optimization hints (PERIOD, etc.)
- Handle synchronization between widgets

#### DSL.InputManager
**Requirements:**
- Process input device configurations
- Map hardware events to state changes
- Support various input types (buttons, encoders, etc.)
- Handle debouncing and other input processing

#### DSL.Application
**Requirements:**
- Top-level container for the application
- Manage screens and data sources
- Handle application lifecycle
- Coordinate rendering and input processing

### 4.2 Classes to Modify

#### widget
**Current Role:** Base class for all widgets
**Modifications Required:**
- Add support for tick-based rendering
- Implement deterministic state calculation
- Add timeline-based movement
- Support style application from themes
- Add buffer management for rendering optimization

#### marquee, scroll, slide, popUp
**Current Role:** Animation widgets
**Modifications Required:**
- Replace action list with Timeline-based animations
- Add support for PERIOD and other optimization hints
- Implement direct position calculation
- Add synchronization support

#### canvas, stack, sequence, index
**Current Role:** Collection widgets
**Modifications Required:**
- Add support for DSL-based instantiation
- Implement z-ordering and placement from DSL
- Support theme application
- Add state-based visibility control

#### text, image, progressBar, etc.
**Current Role:** Content widgets
**Modifications Required:**
- Add support for style application
- Implement variable binding
- Add theme awareness
- Support animation timeline integration

### 4.3 Classes to Remove (or Deprecate)

While no classes need to be removed immediately, the following patterns should be deprecated in favor of the DSL approach:

- Direct widget instantiation in Python code
- Manual widget placement and sizing
- Imperative animation definition
- Direct manipulation of widget properties

Instead, these should be replaced with DSL declarations and the interpreter-based instantiation system.

## 5. Implementation Considerations

### 5.1 Backward Compatibility

The implementation should maintain backward compatibility where possible:

- Support both DSL and direct instantiation during a transition period
- Provide migration utilities to help convert existing code
- Document deprecation timelines clearly

### 5.2 Performance Optimization

Resource constraints are a primary concern:

- Implement lazy loading for resources
- Use memory pools for frequently created objects
- Optimize rendering path for common cases
- Support precomputation of deterministic animations

### 5.3 Error Handling

Robust error handling is essential:

- Provide clear, actionable error messages
- Include line/column information in syntax errors
- Detect and report common logical errors
- Add validation for resource usage and constraints

### 5.4 Testing Strategy

Comprehensive testing should include:

- Unit tests for each component
- Integration tests for the full pipeline
- Performance benchmarks
- Resource usage monitoring
- Sample application validation

## 6. Documentation Requirements

The implementation should include:

- API documentation for all new classes
- DSL language reference (incorporating existing DSL docs)
- Migration guide for existing applications
- Tutorials for common patterns
- Examples of complete applications

## 7. Phased Rollout Plan

The implementation should follow a phased rollout:

1. **Alpha Release**: Core parsing and marquee animation support
2. **Beta Release**: Full widget DSL support with basic examples
3. **RC Release**: Complete application DSL with optimization
4. **1.0 Release**: Production-ready with documentation and samples

Each phase should include a testing period and feedback loop before proceeding to the next phase. 