#!/usr/bin/env python3
"""
Test script to check text rendering in mode "1" with Pillow.
"""

import os
from PIL import Image, ImageDraw, ImageFont

def create_font(size=14):
    """Create a font for text rendering."""
    try:
        # Try common system fonts
        for font_name in ["Arial.ttf", "DejaVuSans.ttf", "Helvetica.ttf", "Verdana.ttf"]:
            try:
                return ImageFont.truetype(font_name, size)
            except:
                pass
        
        # Fallback to default font
        return ImageFont.load_default()
    except:
        return None

def test_mode1_text():
    """Test rendering text in mode "1" (black and white)."""
    # Create output directory
    os.makedirs("test_results", exist_ok=True)
    
    # Create a mode "1" image with black background (0)
    img = Image.new("1", (120, 20), 0)
    draw = ImageDraw.Draw(img)
    
    # Get a font
    font = create_font(16)
    print(f"Using font: {font}")
    
    # Draw text in white (1)
    text = "SLIDE Text"
    draw.text((10, 2), text, fill=1, font=font)
    
    # Save the image
    output_path = "test_results/direct_text_test.png"
    img.save(output_path)
    print(f"Saved black and white text image to {output_path}")
    
    # Count white pixels
    white_pixels = 0
    for y in range(img.height):
        for x in range(img.width):
            if img.getpixel((x, y)) == 1:
                white_pixels += 1
    
    print(f"Image analysis: Size={img.size}, Mode={img.mode}, White pixels={white_pixels}")
    
    # Create a color version for better viewing
    rgb_img = Image.new("RGB", img.size, (0, 0, 0))
    for y in range(img.height):
        for x in range(img.width):
            if img.getpixel((x, y)) == 1:  # White in mode "1"
                rgb_img.putpixel((x, y), (255, 255, 255))
    
    rgb_output = "test_results/direct_text_test_rgb.png"
    rgb_img.save(rgb_output)
    print(f"Saved RGB version to {rgb_output}")

if __name__ == "__main__":
    test_mode1_text() 