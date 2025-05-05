# Marquee Animation DSL Specification

# Overview

The Marquee Animation DSL is a domain-specific language tailored for defining widget animations on resource-constrained displays (e.g., Raspberry Pi Zero 2W driving 100×16–256×128 pixel panels via bitbang/SPI/I²C). It aims to:

* Provide a **declarative** syntax for movement, timing, loops, and conditions.
* Support **coordination** between multiple animations and **custom easing**.
* Optimize for **ticks-based timing** and **pixel-based distances** under strict memory/CPU constraints.

