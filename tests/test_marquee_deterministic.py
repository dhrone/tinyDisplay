import pytest
from PIL import ImageChops

from tinyDisplay.render.widget import text, slide


def images_equal(im1, im2):
    """Return True if two images are pixel-identical."""
    diff = ImageChops.difference(im1.convert('RGB'), im2.convert('RGB'))
    return diff.getbbox() is None


def test_timeline_consistency():
    """Ensure that marquee timelines are identical across instances with the same config."""
    # Create a simple static text inside a slide marquee
    t = text(value="'Hi'", size=(10, 2))
    m1 = slide(widget=t, size=(10, 2), actions=[('ltr', 3), ('pause', 2)])
    m2 = slide(widget=t, size=(10, 2), actions=[('ltr', 3), ('pause', 2)])
    # The precomputed timelines must match exactly
    assert isinstance(m1._timeline, list)
    assert m1._timeline == m2._timeline


def test_synchronize_rotates_timeline():
    """Verify that synchronize() correctly rotates one timeline to match another at an event."""
    t1 = text(value="'A'", size=(5, 1))
    t2 = text(value="'B'", size=(5, 1))
    m1 = slide(widget=t1, size=(5, 1), actions=[('ltr', 2), ('pause', 3)])
    m2 = slide(widget=t2, size=(5, 1), actions=[('ltr', 2), ('pause', 3)])
    orig = list(m2._timeline)
    # Align m2 to m1's first pause
    pause_idx = m1._pauses[0]
    m2.synchronize(m1, at_event='pause')
    # Check that m2's timeline was shifted so its frame 0 equals orig[pause_idx]
    assert m2._timeline[0] == orig[pause_idx]
    # And that it's not identical to the original ordering
    assert m2._timeline != orig


def test_dynamic_content_and_render():
    """Check that dynamic text is stable until data changes, then updates deterministically."""
    # Create a dataset-backed text
    ds = {'val': 1}
    t = text(value='d{val}', size=(5, 1), dataset=ds)
    m = slide(widget=t, size=(5, 1), actions=[('ltr', 1)])

    # Render at tick 0 twice: expect identical images (no data change)
    img1, _ = m.render(force=False, tick=0)
    img2, _ = m.render(force=False, tick=0)
    assert images_equal(img1, img2)

    # Change the underlying data and render with newData=True
    ds['val'] = 2
    img3, _ = m.render(force=False, tick=0, newData=True)
    # The image should now differ
    assert not images_equal(img1, img3)
    # And should contain the new character '2'
    b = img3.tobytes()
    assert ord('2') in b 