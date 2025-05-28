# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Image utility functions for tinyDisplay.
"""

import logging
import os
import pathlib
import sys
from urllib.request import urlopen

from PIL import Image, ImageChops, ImageColor

def compareImage(baseImage, testImage, useAlpha=True):
    """
    Compare two images and return the differences.

    :param baseImage: The known good image to compare against
    :type baseImage: PIL.Image
    :param testImage: The second image to compare with the baseImage
    :type testImage: PIL.Image
    :param useAlpha: Whether to consider the alpha channel in the comparison (Default: True)
    :type useAlpha: bool
    :returns: A tuple containing (diff_image, the percentage of pixels that differ, total number of pixels that differ)
    :rtype: tuple
    """
    if baseImage.mode != testImage.mode:
        testImage = testImage.convert(baseImage.mode)
        
    if baseImage.size != testImage.size:
        testImage = testImage.resize(baseImage.size)
    
    diff = ImageChops.difference(baseImage, testImage)
    
    if useAlpha and baseImage.mode == 'RGBA' and testImage.mode == 'RGBA':
        # For RGBA images, compare each channel separately
        r, g, b, a = diff.split()
        diff = Image.merge('RGB', (r, g, b))  # Exclude alpha from diff image display
    
    # Count different pixels
    stat = diff.convert("L").getdata()
    diff_pixels = sum(1 for p in stat if p > 0)
    total_pixels = baseImage.width * baseImage.height
    
    # Calculate percentage that differs
    percentage = (diff_pixels / total_pixels) * 100 if total_pixels > 0 else 0
    
    return diff, percentage, diff_pixels

def _supports_color():
    """
    Determine if the terminal supports color output.
    
    :returns: True if the terminal supports color, False otherwise
    :rtype: bool
    """
    # Check if output is redirected to a file or pipe
    if not sys.stdout.isatty():
        return False
    
    # Check for common environment variables indicating color support
    color_terms = ["xterm-color", "xterm-256color", "screen", "screen-256color", "tmux", "tmux-256color"]
    term = os.environ.get("TERM", "")
    colorterm = os.environ.get("COLORTERM", "")
    
    if colorterm:
        return True
    
    if term in color_terms:
        return True
    
    # Check for specific environment variables that might indicate color support
    if os.environ.get("CLICOLOR", "") != "0":
        return True
    
    if os.environ.get("FORCE_COLOR", ""):
        return True
    
    # Fallback to basic check - most modern terminals support color
    if sys.platform != "win32" or "ANSICON" in os.environ:
        return True
    
    return False

def image2Text(img, background="black", use_color=True, char_map=" ▒█", use_block_chars=False):
    """
    Convert an image to ASCII or colored terminal art.

    :param img: The image to convert
    :type img: PIL.Image
    :param background: The background color for the image
    :type background: str, int or tuple
    :param use_color: Whether to use ANSI color codes in the output (default: True)
    :type use_color: bool
    :param char_map: Characters to use for different brightness levels (dark to bright)
    :type char_map: str
    :param use_block_chars: Use Unicode block characters instead of ASCII
    :type use_block_chars: bool
    :returns: ASCII/ANSI text representation of the image
    :rtype: str
    """
    # Check if terminal supports color - if not, force monochrome
    terminal_supports_color = _supports_color()
    
    # Force monochrome for mode '1' images (bitmap)
    mono_mode = img.mode == '1'
    if mono_mode:
        use_color = False
    
    # Only use color if terminal supports it and use_color is True
    use_color = use_color and terminal_supports_color
    
    # Prepare the image for processing
    working_img = img
    if use_color and img.mode not in ["RGB", "RGBA"]:
        working_img = img.convert("RGB")
    
    # Process background color
    if type(background) is str:
        try:
            bg_mode = "RGB" if use_color else working_img.mode
            background = ImageColor.getcolor(background, bg_mode)
        except:
            # If color conversion fails, use default approach
            background = (0, 0, 0) if use_color else 0
    
    # For mode '1' images, ensure defaults are: black background (0), white foreground (1)
    if mono_mode:
        fg_value = 1  # White in mode '1'
        bg_value = 0  # Black in mode '1'
    
    # If present, strip alpha channel for comparison
    bg_for_comparison = background
    if type(background) is not int and len(background) in [2, 4]:
        bg_for_comparison = background[0:-1]

    # Define block characters for enhanced display if requested
    block_chars = " ░▒▓█" if use_block_chars else char_map
    
    # In color mode with block chars, always use █ (full block) for better visibility
    full_block = '█' if use_block_chars else block_chars[-1]
    
    # Create top border - ensure it spans the full width of the image
    width = working_img.size[0]
    border = "-" * (width + 2)
    retval = border
    
    # Process each row of the image
    for j in range(working_img.size[1]):
        row = "|"  # Start with left border
        
        for i in range(width):
            pixel = working_img.getpixel((i, j))
            
            if use_color:
                # Extract RGB components, handling different image modes
                if type(pixel) is int:
                    r = g = b = pixel
                elif len(pixel) == 1:
                    r = g = b = pixel[0]
                elif len(pixel) >= 3:
                    r, g, b = pixel[0:3]
                else:
                    r = g = b = pixel[0]
                
                # For color mode, just use full block with the pixel's color
                row += f"\033[38;2;{r};{g};{b}m{full_block}\033[0m"
            else:
                # Original monochrome behavior
                if mono_mode:
                    # For mode '1', 0 is black (background) and 1 is white (foreground)
                    v = " " if pixel == bg_value else "*"
                else:
                    if type(pixel) is not int and len(pixel) in [2, 4]:
                        pixel_for_comparison = pixel[0:-1]
                    else:
                        pixel_for_comparison = pixel
                    
                    v = " " if pixel_for_comparison == bg_for_comparison else "*"
                row += v
        
        # Add right border and append to result
        row += "|"
        retval += f"\n{row}"
    
    # Add bottom border
    retval += f"\n{border}"
    return retval

def okPath(path, workingDir=None):
    """
    Normalize and validate a file path.

    :param path: The path to check and normalize
    :type path: str
    :param workingDir: The working directory to use as a base for relative paths
    :type workingDir: str
    :returns: The normalized path
    :rtype: str
    :raises FileNotFoundError: If the path doesn't exist
    """
    if workingDir is None:
        workingDir = os.getcwd()

    # Handle URLs
    if path.startswith(('http://', 'https://')):
        try:
            response = urlopen(path)
            if response.getcode() != 200:
                raise FileNotFoundError(f"URL not accessible: {path}")
            return path
        except Exception as e:
            raise FileNotFoundError(f"URL error: {path} - {str(e)}")

    # Handle local files
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = pathlib.Path(workingDir) / p

    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    return str(p.resolve()) 