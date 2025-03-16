import cProfile
import pstats
from tinyDisplay.render.widget import (
    text,
    image,
    scroll,
)  # import needed widgets


def profile_widget_operations():
    # Create sample widget operations
    text_widget = text(value="Sample Text", size=(100, 30))
    for _ in range(100):
        text_widget.render()

    img_widget = image(file="sample.png", size=(200, 200))
    for _ in range(50):
        img_widget.render()

    scroll_widget = scroll(widget=text_widget)
    for _ in range(200):
        scroll_widget.render()


# Run the profiler
profiler = cProfile.Profile()
profiler.enable()
profile_widget_operations()
profiler.disable()

# Print sorted stats
stats = pstats.Stats(profiler).sort_stats("cumulative")
stats.print_stats(30)  # Print top 30 time-consuming operations
