#!/usr/bin/env python3

import cProfile
import io
import pstats
import timeit
from pathlib import Path

from PIL import Image, ImageFont

from tinyDisplay.render.widget import text
from tinyDisplay.utility import dataset

def test_text_widget_performance():
    """Test the performance of the text widget."""
    
    # Create a text widget
    t = text(size=(200, 50), text="Initial text", wrap=True, width=200)
    
    # Test rendering the same text multiple times
    def test_render_same():
        t.render()
    
    # Test rendering with different text
    def test_render_different():
        for i in range(10):
            t._value = f"This is test text {i}"
            t.render()
    
    # Test word wrapping performance
    def test_word_wrap():
        t._value = "This is a long text that needs to be wrapped across multiple lines to test the word wrapping performance of the text widget"
        t.render()
    
    # Run performance tests
    print("Testing rendering the same text 1000 times:")
    same_time = timeit.timeit(test_render_same, number=1000)
    print(f"Time: {same_time:.4f} seconds")
    
    print("\nTesting rendering with different text 100 times:")
    different_time = timeit.timeit(test_render_different, number=100)
    print(f"Time: {different_time:.4f} seconds")
    
    print("\nTesting word wrapping performance 100 times:")
    wrap_time = timeit.timeit(test_word_wrap, number=100)
    print(f"Time: {wrap_time:.4f} seconds")
    
    # Profile rendering with word wrapping
    print("\nProfiling word wrapping in detail:")
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(50):
        t._value = "This is a long text that needs to be wrapped across multiple lines to test the word wrapping performance of the text widget"
        t.render()
    profiler.disable()
    
    # Print profiling results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumtime')
    ps.print_stats(20)  # Print top 20 functions by cumulative time
    print(s.getvalue())

if __name__ == "__main__":
    test_text_widget_performance() 