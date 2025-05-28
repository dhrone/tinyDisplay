# Project Brief: tinyDisplay Refactor

## Introduction / Problem Statement

tinyDisplay is a specialized display framework designed for Single Board Computers (SBCs) driving small embedded displays, typically under 256x128 pixel resolution. The project addresses a gap in existing display frameworks which assume high-resolution devices and framebuffer-based systems, making them unsuitable for small displays that require specialized interface logic (handled by projects like luma.oled and luma.lcd).

Originally created to replace basic display software for a RaspberryPi-based music player, tinyDisplay has evolved into a sophisticated framework for managing dynamic content through widgets, animations, and data-driven updates. The project serves dual purposes: creating a practical tool for small display applications and providing a platform for experimenting with development methodologies and concepts.

The current challenge is that tinyDisplay is in a mid-refactor state where core architectural improvements are partially implemented. While the system demonstrates strong capabilities in marquee animations and dynamic value management, critical components including widget integration with the dependency management system, the application DSL implementation, and multiprocessing capabilities remain incomplete, with some core components currently failing unit tests.

## Vision & Goals

**Vision:** Create a robust, educational, and community-useful framework that makes sophisticated display programming accessible for small embedded displays, while serving as a platform for exploring advanced development methodologies.

**Primary Goals for Completion (Target: End of June 2025):**
1. **Stabilize Core Architecture:** Restore all unit tests to passing state and complete the widget-dependency management system integration
2. **Complete Application DSL:** Implement the comprehensive application DSL supporting layout, animation, data sources, and validation
3. **Enable Multiprocessing:** Implement multiprocessing capabilities for performance and responsiveness
4. **Achieve Performance Targets:** Render at 60 fps on RaspberryPi Zero 2W with efficient resource utilization
5. **Establish Structured Development:** Use BMAD methodology to create clear roadmap and development processes

**Success Metrics (Research-Informed):**
- All unit tests passing consistently
- 60 fps rendering capability on RaspberryPi Zero 2W (validated as achievable with Ring Buffers + SQLite)
- Memory usage under 200MB during normal operations (170-200MB allocated for hybrid architecture)
- Dynamic value evaluation under 1ms per expression (4-10x improvement with asteval)
- Dependency update propagation under 100μs (RxPY reactive system)
- Partial screen updates: only redraw changed screen portions ("Smart Immediate Mode")
- Application DSL can define complex display scenarios with data integration
- Documentation enables effective development workflow
- Successful PyPI package distribution

## Target Audience / Users

**Primary User:** You (the developer) - for personal education, methodology experimentation, and practical use in embedded display projects.

**Secondary Users:** Embedded systems developers working with small displays who need sophisticated display capabilities for projects such as:
- Music players with dynamic track/playlist displays
- Tap display systems showing current beer selections
- IoT dashboards and status displays
- Industrial monitoring displays
- Maker projects requiring animated interfaces

**User Characteristics:**
- Comfortable with Python programming
- Working with resource-constrained embedded systems (SBCs like RaspberryPi)
- Need performance-critical display rendering on small displays (under 256x128 resolution)
- Value efficient resource usage and smooth animations
- Range from users who want simple declarative interfaces to those interested in advanced concepts like dependency tracking and multiprocessing

**Framework Design Philosophy:** Expose advanced concepts for power users while providing simple, declarative interfaces that don't require deep understanding of the underlying architecture.

## Key Features / Scope (High-Level Ideas for MVP)

**MVP Features (Completion Target):**

- **Stable Widget System:** Core widget types (text, image, progressBar, shape, line, rectangle) and collection types (canvas, stack, index, sequence) fully integrated with dependency management
- **Dynamic Value System:** Efficient dependency tracking that only recomputes changed values and widgets
- **Marquee Animation Engine:** Complete suite of animation types (slide, scroll, popUp) with coordinated multi-widget capabilities
- **Application DSL:** Comprehensive declarative language supporting:
  - Sophisticated layout definitions with animation capabilities
  - Data source definitions and mapping to dataset class
  - Data validation statements, default values, and samples
  - Integration with existing dataset.py infrastructure
- **Multiprocessing Rendering:** Background rendering pipeline for smooth 60fps performance on RaspberryPi Zero 2W
- **Partial Screen Updates:** Intelligent rendering that only updates changed screen regions
- **Hardware Integration:** Seamless integration with luma.oled/luma.lcd for various display types
- **Performance Optimization:** Efficient resource utilization with minimal unnecessary recomputation

## Post MVP Features / Scope and Ideas

**Post-MVP Features (Stretch Goals):**

- **Touch Display Integration:** Support for touch input handling and interactive widgets
- **Web-based Development UI:** Browser-based tool for designing and testing display scripts using the application DSL
- **Extended Widget Library:** Additional specialized widgets including:
  - Swipe animations and gesture-based interactions
  - Fade transitions and alpha blending effects
  - Drop-down menus and expandable content
  - Advanced data visualization widgets (graphs, charts)
- **Configuration Management:** Hot-reloading of display configurations without restart
- **Performance Analytics:** Built-in profiling and optimization tools
- **Community Templates:** Shareable display templates for common embedded display scenarios

## Known Technical Constraints or Preferences

**Constraints:**
- **Timeline:** Complete refactor by end of June 2025
- **Performance Target:** 60 fps rendering on RaspberryPi Zero 2W
- **Hardware Platform:** Single Board Computers with small displays (under 256x128 resolution)
- **Display Interface:** Integration with luma.oled/luma.lcd for specialized display hardware
- **Current State:** Mid-refactor with some core components failing unit tests

**Initial Architectural Preferences (Research-Informed):**
- **Language:** Python 3 framework
- **Development Environment:** Cursor IDE (with Windsurf trial), pytest testing framework
- **Distribution:** PyPI package for community distribution
- **Rendering Architecture:** "Smart Immediate Mode" combining immediate mode simplicity with retained mode optimization
- **Data Layer:** Hybrid Ring Buffers + SQLite + RxPY architecture for memory efficiency and performance
- **Dynamic Values:** AST-based evaluation (asteval) with RxPY dependency tracking for 4-10x performance improvement
- **Memory Allocation:** Fixed allocation model (Ring Buffers: 50-100MB, SQLite: 8-16MB, RxPY: 10-20MB)
- **Dependency Management:** RxPY-based reactive system to eliminate redundant calculations
- **DSL Integration:** Deep integration between application DSL and hybrid data architecture
- **Modular Design:** Clear separation between rendering engine, widget system, and application layer

**Risks (Research-Updated):**
- **Technical Complexity:** Integrating widgets with RxPY dependency management system (Medium risk - research shows 2-4 week integration timeline)
- **Performance Targets:** Achieving 60fps on resource-constrained hardware (Low risk - research validates Ring Buffers + SQLite can guarantee 60fps)
- **Memory Management:** Staying within 512MB constraint during complex operations (Low-Medium risk - hybrid architecture allocates 170-200MB with deterministic patterns)
- **DSL Scope:** Balancing comprehensive DSL features with implementation complexity (Medium risk - asteval provides clear migration path)
- **Testing Stability:** Restoring failing unit tests while implementing new features (Medium risk - phased migration allows incremental validation)
- **Migration Complexity:** Moving from current dataset.py to hybrid architecture (Low-Medium risk - research provides detailed migration strategy)

**User Preferences:**
- **Educational Value:** Framework should serve as learning platform for development methodologies
- **Community Potential:** Design for eventual community use while prioritizing personal learning
- **BMAD Integration:** Use this project as pilot for BMAD methodology validation
- **Breaking Changes Acceptable:** No backward compatibility constraints - clean slate refactor encouraged

## Relevant Research

**Comprehensive research conducted on three critical architectural areas:**

### Competitive Analysis Key Findings
- **Market Gap Validated:** No existing framework provides 60fps performance at 256x128 resolution with pure Python development
- **Performance Benchmarks:** Hardware-optimized libraries (luma.oled) achieve 100+ FPS but lack animation systems; desktop frameworks (Kivy) cap at 30 FPS on Pi Zero 2W
- **Architectural Opportunity:** "Smart Immediate Mode" combining immediate mode simplicity with retained mode optimization represents unexplored territory
- **Unique Positioning Confirmed:** tinyDisplay addresses genuine gap between hardware optimization and developer experience

### Data Layer Architecture Findings
- **Memory Efficiency:** Hybrid approach using Ring Buffers (50-100MB fixed allocation) + SQLite (8-16MB cache) + RxPY (10-20MB) fits within 512MB constraint
- **Performance Validation:** Ring Buffers + SQLite can guarantee 60fps capability with deterministic latency patterns
- **Migration Strategy:** Phased approach starting with Ring Buffers provides immediate memory control and performance gains
- **Integration Complexity:** Low-medium complexity integration (2-4 weeks) with existing tinyDisplay architecture

### Dynamic Value System Findings  
- **Performance Improvement Potential:** AST-based evaluation (asteval) provides 4-10x performance improvement over current system
- **60fps Viability:** Target metrics achievable: <1ms per expression, <5ms for complex templates, <100μs for dependency updates
- **Migration Path:** Low-risk drop-in replacement possible, maintaining API compatibility while gaining significant performance
- **Advanced Features:** RxPY integration for dependency tracking eliminates redundant calculations and scales to complex dependency networks

**Research Impact:** Findings validate technical approach and provide clear implementation roadmap with specific performance targets and migration strategies.

## PM Prompt

This Project Brief provides the full context for tinyDisplay Refactor. Please start in 'PRD Generation Mode', review the brief thoroughly to work with the user to create the PRD section by section 1 at a time, asking for any necessary clarification or suggesting improvements as your mode 1 programming allows. 