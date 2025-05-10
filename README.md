# Marquee Animation Demo

This program demonstrates the various animation capabilities of the tinyDisplay marquee class by creating animated GIFs for different animation types.

## Features

- Demonstrates various marquee animation types:
  - SLIDE: Smooth sliding animations with easing
  - SCROLL: Continuous scrolling text (ticker)
  - SCROLL_BOUNCE: Text that bounces back and forth
  - SCROLL_CLIP: Text that scrolls to a specific point and stops
  - Complex animations combining multiple effects
  - Multi-widget coordinated animations using SYNC and WAIT_FOR

- All animations are saved as animated GIFs at 30 FPS
- Animations show 5 seconds of each effect
- Results are saved to a `test_results` directory
- Includes a cleanup option to remove test results

## Requirements

- Python 3.6+
- tinyDisplay library
- PIL/Pillow for image processing

## Usage

Run the program with:

```
./marquee_demo.py
```

### Command-line options:

- `--animation [type]`: Specify which animation to run
  - Available types: slide, scroll, bounce, clip, complex, multi
  - Default: all (runs all animations)

- `--cleanup`: Remove test results directory and exit

### Examples:

Run all animations:
```
./marquee_demo.py
```

Run only the SLIDE animation:
```
./marquee_demo.py --animation slide
```

Run only the multi-widget coordinated animation:
```
./marquee_demo.py --animation multi
```

Clean up test results:
```
./marquee_demo.py --cleanup
```

## Output

The program creates a `test_results` directory and saves animated GIFs inside it:

- `slide_animation.gif`: SLIDE effect demonstration
- `scroll_animation.gif`: SCROLL_LOOP effect demonstration
- `scroll_bounce_animation.gif`: SCROLL_BOUNCE effect demonstration
- `scroll_clip_animation.gif`: SCROLL_CLIP effect demonstration
- `complex_animation.gif`: Complex animation combining multiple effects
- `multi_widget_animation.gif`: Multiple widgets with coordinated animations

## Customization

You can modify the program to:

- Change animation duration by adjusting `ANIMATION_SECONDS` and `FPS` constants
- Add or modify animation types by creating new demo functions
- Customize text, colors, speeds, and other parameters 