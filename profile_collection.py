import cProfile
import pstats
from PIL import Image
from tinyDisplay.render.collection import canvas, stack, index, sequence
from tinyDisplay.render.widget import image as widget_image


def create_test_image(size=(100, 100), color="white"):
    """Create a test image for profiling.

    :param size: The size of the image.
    :type size: tuple
    :param color: The color of the image.
    :type color: str
    :return: A new RGB image of the specified size and color.
    :rtype: PIL.Image
    """
    return Image.new("RGB", size, color)


def profile_canvas_operations():
    """Profile basic canvas operations."""
    # Create a base canvas
    c = canvas(size=(500, 500))

    # Create test widgets
    test_images = [
        widget_image(
            image=create_test_image(
                size=(50, 50), color=f"rgb({i * 20},{i * 20},{i * 20})"
            )
        )
        for i in range(10)
    ]

    # Profile append operations
    for i, img in enumerate(test_images):
        c.append(img, placement=(i * 60, i * 60))

    # Profile rendering
    for _ in range(100):
        c.render()


def profile_stack_operations():
    """Profile stack widget operations."""
    s = stack(orientation="horizontal", gap=5, size=(800, 200))

    # Create and add test widgets
    for i in range(10):
        img = widget_image(image=create_test_image(size=(70, 70)))
        s.append(img)

    # Profile rendering
    for _ in range(100):
        s.render()


def profile_index_operations():
    """Profile index widget operations."""
    idx = index(size=(200, 200))

    # Add multiple images to index
    for i in range(5):
        img = widget_image(
            image=create_test_image(
                size=(100, 100), color=f"rgb({i * 50},{i * 50},{i * 50})"
            )
        )
        idx.append(img)

    # Profile switching between indices
    for i in range(100):
        idx._value = i % 5
        idx.render()


def profile_sequence_operations():
    """Profile sequence widget operations."""
    seq = sequence(size=(300, 300))

    # Create test canvases
    for i in range(5):
        c = canvas(size=(200, 200))
        img = widget_image(image=create_test_image(size=(150, 150)))
        c.append(img)
        seq.append(c)

    # Profile sequence transitions
    for _ in range(100):
        seq.render()


def main():
    # Create profiler
    profiler = cProfile.Profile()

    print("Starting profiling...")

    # Profile each component
    print("\nProfiling canvas operations...")
    profiler.enable()
    profile_canvas_operations()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(20)

    print("\nProfiling stack operations...")
    profiler.enable()
    profile_stack_operations()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(20)

    print("\nProfiling index operations...")
    profiler.enable()
    profile_index_operations()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(20)

    print("\nProfiling sequence operations...")
    profiler.enable()
    profile_sequence_operations()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(20)


if __name__ == "__main__":
    main()
