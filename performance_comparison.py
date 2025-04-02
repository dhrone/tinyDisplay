#!/usr/bin/env python3

import time
import copy
from PIL import Image, ImageFont, ImageDraw

from tinyDisplay.render.widget import text
from tinyDisplay.utility import dataset

class TextWidgetWithoutCache(text):
    """A subclass that disables caching to simulate pre-optimization behavior."""
    
    def _sizeLine(self, value):
        # Skip all caching
        if value == "" or value is None:
            return (0, 0)

        if "getmetrics" in dir(self._font):
            # Bitmap font path
            ascent, descent = self._font.getmetrics()
            h = 0
            w = 0
            for v in value.split("\n"):
                try:
                    bbox = self._tsDraw.textbbox((0, 0), v, font=self._font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1] + descent
                    w = max(w, tw)
                    h += th
                except TypeError:
                    pass
            tSize = (w, h)
        else:
            # TrueType font path
            bbox = self._tsDraw.textbbox(
                (0, 0), value, font=self._font, spacing=self._lineSpacing
            )
            tSize = (bbox[2] - bbox[0], bbox[3] - bbox[1])

        tSize = (0, 0) if tSize[0] == 0 else tSize
        return tSize
    
    def _makeWrapped(self, value, width):
        vl = value.split(" ")
        lines = []
        line = ""
        for w in vl:
            tl = line + " " + w if len(line) > 0 else w
            if self._sizeLine(tl)[0] <= width:
                line = tl
            else:
                if len(line) == 0:
                    lines.append(tl)
                else:
                    lines.append(line)
                    line = w
        if len(line) > 0:
            lines.append(line)

        return "\n".join(lines)
    
    def _render(self, force=False, newData=False, *args, **kwargs):
        # Always render regardless of cache
        value = str(self._value)
        self._reprVal = f"'{value}'"

        if self._wrap and self._width is not None:
            value = self._makeWrapped(value, self._width)

        tSize = self._sizeLine(value)
        
        img = Image.new(self._mode, tSize, self._background)
        if img.size[0] != 0:
            d = ImageDraw.Draw(img)
            d.fontmode = self._fontMode
            just = {"l": "left", "r": "right", "m": "center"}.get(self.just[0])
            d.text(
                (0, 0),
                value,
                font=self.font,
                fill=self._foreground,
                spacing=self._lineSpacing,
                align=just,
            )

        size = (
            self._width if self._width is not None else img.size[0],
            self._height if self._height is not None else img.size[1],
        )
        self.clear(size)
        self._place(wImage=img, just=self.just)
        return (self.image, True)


def run_comparison():
    print("Performance comparison between optimized and non-optimized text widget\n")
    
    # Test parameters
    test_cases = [
        ("Short text", "Hello World"),
        ("Medium text", "This is a somewhat longer text that will require more processing"),
        ("Long text with wrapping", "This is a very long text that needs to be wrapped across multiple lines to test the word wrapping performance of the text widget system. It contains many words of different lengths to thoroughly test the wrapping algorithm efficiency."),
    ]
    iterations = 100
    
    # Create widgets
    optimized = text(size=(200, 100), text="", wrap=True, width=180)
    non_optimized = TextWidgetWithoutCache(size=(200, 100), text="", wrap=True, width=180)
    
    # Run tests
    for name, content in test_cases:
        print(f"\n=== Testing: {name} ===")
        
        # Test optimized version
        optimized._value = content
        start = time.time()
        for _ in range(iterations):
            optimized.render()
        optimized_time = time.time() - start
        print(f"Optimized:     {optimized_time:.6f} seconds ({optimized_time/iterations*1000:.3f} ms per render)")
        
        # Test non-optimized version
        non_optimized._value = content
        start = time.time()
        for _ in range(iterations):
            non_optimized.render()
        non_optimized_time = time.time() - start
        print(f"Non-optimized: {non_optimized_time:.6f} seconds ({non_optimized_time/iterations*1000:.3f} ms per render)")
        
        # Calculate improvement
        improvement = (non_optimized_time - optimized_time) / non_optimized_time * 100
        print(f"Improvement:   {improvement:.1f}%")
        
        # Compare same text multiple times
        print("\n  Rendering same text repeatedly:")
        
        # Optimized
        start = time.time()
        for _ in range(iterations * 5):  # More iterations for this test
            optimized.render(force=False)
        optimized_repeat_time = time.time() - start
        print(f"  Optimized:     {optimized_repeat_time:.6f} seconds ({optimized_repeat_time/(iterations*5)*1000:.3f} ms per render)")
        
        # Non-optimized
        start = time.time()
        for _ in range(iterations * 5):
            non_optimized.render(force=False)
        non_optimized_repeat_time = time.time() - start
        print(f"  Non-optimized: {non_optimized_repeat_time:.6f} seconds ({non_optimized_repeat_time/(iterations*5)*1000:.3f} ms per render)")
        
        # Calculate improvement for repeated rendering
        repeat_improvement = (non_optimized_repeat_time - optimized_repeat_time) / non_optimized_repeat_time * 100
        print(f"  Improvement:   {repeat_improvement:.1f}%")

if __name__ == "__main__":
    run_comparison() 