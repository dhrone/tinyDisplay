#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Demo for the enhanced image2Text function with color support.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import tinyDisplay
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont, ImageColor

from tinyDisplay.utility.image_utils import image2Text
from tinyDisplay.render.widget import text

def create_gradient_image(size=(20, 10), horizontal=True):
    """Create a gradient test image."""
    img = Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for i in range(size[0]):
        for j in range(size[1]):
            if horizontal:
                # Horizontal RGB gradient
                r = int(255 * i / size[0])
                g = int(255 * (size[0] - i) / size[0])
                b = int(128 * j / size[1])
            else:
                # Vertical RGB gradient
                r = int(255 * j / size[1])
                g = int(255 * (size[1] - j) / size[1])
                b = int(128 * i / size[0])
                
            draw.point((i, j), fill=(r, g, b))
    
    return img

def create_monochrome_image(size=(20, 10)):
    """Create a simple monochrome test image."""
    img = Image.new('1', size, 0)  # Black background
    draw = ImageDraw.Draw(img)
    
    # Draw a pattern
    draw.rectangle((5, 2, 15, 7), fill=1)  # White rectangle
    draw.line((0, 0, size[0], size[1]), fill=1)  # Diagonal line
    
    return img

def main():
    """Show various examples of the image2Text function."""
    print("\n=== Enhanced image2Text Demo ===\n")
    
    # Example 1: Gradient image with default settings
    gradient_img = create_gradient_image()
    print("1. Default color rendering (horizontal gradient):")
    print(image2Text(gradient_img))
    print()
    
    # Example 2: Gradient with block characters
    print("2. With block characters (horizontal gradient):")
    print(image2Text(gradient_img, use_block_chars=True))
    print()
    
    # Example 3: Vertical gradient with custom char map
    vertical_gradient = create_gradient_image(horizontal=False)
    print("3. Vertical gradient with custom character map:")
    print(image2Text(vertical_gradient, char_map=" .:;+*#@"))
    print()
    
    # Example 4: Monochrome image (should auto-disable color)
    mono_img = create_monochrome_image()
    print("4. Monochrome image (should auto-disable color):")
    print(image2Text(mono_img))
    print()
    
    # Example 5: Forcing monochrome for color image
    print("5. Color gradient with color disabled:")
    print(image2Text(gradient_img, use_color=False))
    print()
    
    # Example 6: Text with white on blue background using tinyDisplay text widget
    print("6. Text widget with white text on blue background:")
    # Create text widget with white foreground, blue background
    text_widget = text(
        value="Color Test", 
        foreground="white", 
        background="blue",
        size=(100, 20)  # Make it large enough to fit the text
    )
    # Render the widget to get its image
    text_img, _ = text_widget.render()
    # Display the text widget image using our enhanced image2Text
    print(image2Text(text_img, use_block_chars=True))
    print()
    
    # Example 7: Try with a real image if available
    test_img_path = Path(__file__).parent / "reference/images/pydPiper_splash.png"
    if test_img_path.exists():
        print("7. Real image example:")
        img = Image.open(test_img_path)
        # Resize to reasonable terminal dimensions
        img = img.resize((60, 20))
        print(image2Text(img, use_block_chars=True))
    
if __name__ == "__main__":
    main() 