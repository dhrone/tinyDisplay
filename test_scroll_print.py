#!/usr/bin/env python3
# Test script for scroll widget printing

from tinyDisplay.render.widget import scroll, text

# Create a text widget
t = text(value='ABCDEF')

# Create a scroll widget with RTL movement and specific size
s = scroll(
    widget=t, 
    actions=[('rtl',)], 
    size=(15, 8),
    bufferSize=4
)

# Clear any existing buffer entries
s._imageBuffer.clear()

# Render multiple frames with increasing tick values to show scrolling
print("Rendering 6 frames with scrolling:")
for i in range(6):
    s.render(tick=i)
    print(f"\nFrame {i+1} (Tick {i}):")
    s._print_image_as_ascii(s.image)

# Print the buffer contents
print("\nFull buffer contents:")
s.print(4)

# Test that the buffer actually contains different frames
print("\nTesting if animation frames are different:")
buffer = s.get_buffer()
if len(buffer) < 2:
    print("Not enough frames in buffer to compare")
else:
    # Compare first and last frames
    first_img = buffer[0][0]
    last_img = buffer[-1][0]
    
    # Convert to binary for comparison
    first_binary = first_img.convert('1')
    last_binary = last_img.convert('1')
    
    # Check if images are different
    are_different = False
    for y in range(min(first_binary.height, last_binary.height)):
        for x in range(min(first_binary.width, last_binary.width)):
            if first_binary.getpixel((x, y)) != last_binary.getpixel((x, y)):
                are_different = True
                break
        if are_different:
            break
    
    print(f"First and last frames are {'different' if are_different else 'identical'}") 