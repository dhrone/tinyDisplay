#!/usr/bin/env python3
"""
Test Suite for ImageWidget

Comprehensive tests for image widget functionality including reactive binding,
image loading, caching, scaling, styling, and performance validation.
"""

import pytest
import time
import io
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.tinydisplay.widgets.image import (
    ImageWidget, ImageStyle, ImageCache, ImageLoadResult,
    ScaleMode, ImageFormat, ImageFilter as ImageFilterEnum
)
from src.tinydisplay.widgets.base import ReactiveValue, WidgetBounds

# Mock PIL classes for testing when PIL is not available
class MockPILImage:
    def __init__(self, size=(100, 100), mode='RGB', format='PNG'):
        self.size = size
        self.mode = mode
        self.format = format
    
    def copy(self):
        return MockPILImage(self.size, self.mode, self.format)
    
    def resize(self, size, resample=None):
        return MockPILImage(size, self.mode, self.format)
    
    def crop(self, box):
        width = box[2] - box[0]
        height = box[3] - box[1]
        return MockPILImage((width, height), self.mode, self.format)
    
    def convert(self, mode):
        return MockPILImage(self.size, mode, self.format)
    
    def split(self):
        return [MockPILImage(self.size, 'L', self.format) for _ in range(3)]
    
    def putalpha(self, alpha):
        pass
    
    def point(self, func):
        return self
    
    def filter(self, filter_obj):
        return self
    
    def getbands(self):
        return ['R', 'G', 'B'] if self.mode == 'RGB' else ['R', 'G', 'B', 'A']


class TestImageStyle:
    """Test ImageStyle configuration and validation."""
    
    def test_image_style__default_values__correct_initialization(self):
        """Test ImageStyle with default values."""
        style = ImageStyle()
        assert style.opacity == 1.0
        assert style.brightness == 1.0
        assert style.contrast == 1.0
        assert style.saturation == 1.0
        assert style.border_width == 0
        assert style.border_color == (128, 128, 128)
        assert style.border_radius == 0
        assert style.shadow_offset == (0, 0)
        assert style.shadow_color == (0, 0, 0)
        assert style.shadow_blur == 0
        assert style.filter_effect == ImageFilterEnum.NONE
    
    def test_image_style__custom_values__correct_initialization(self):
        """Test ImageStyle with custom values."""
        style = ImageStyle(
            opacity=0.8,
            brightness=1.2,
            contrast=1.5,
            saturation=0.9,
            border_width=2,
            border_color=(255, 0, 0),
            filter_effect=ImageFilterEnum.BLUR
        )
        assert style.opacity == 0.8
        assert style.brightness == 1.2
        assert style.contrast == 1.5
        assert style.saturation == 0.9
        assert style.border_width == 2
        assert style.border_color == (255, 0, 0)
        assert style.filter_effect == ImageFilterEnum.BLUR
    
    def test_image_style__invalid_opacity__raises_error(self):
        """Test ImageStyle with invalid opacity raises ValueError."""
        with pytest.raises(ValueError, match="Opacity must be between 0.0 and 1.0"):
            ImageStyle(opacity=1.5)
        
        with pytest.raises(ValueError, match="Opacity must be between 0.0 and 1.0"):
            ImageStyle(opacity=-0.1)
    
    def test_image_style__invalid_brightness__raises_error(self):
        """Test ImageStyle with invalid brightness raises ValueError."""
        with pytest.raises(ValueError, match="Brightness must be non-negative"):
            ImageStyle(brightness=-0.5)
    
    def test_image_style__invalid_contrast__raises_error(self):
        """Test ImageStyle with invalid contrast raises ValueError."""
        with pytest.raises(ValueError, match="Contrast must be non-negative"):
            ImageStyle(contrast=-1.0)
    
    def test_image_style__invalid_saturation__raises_error(self):
        """Test ImageStyle with invalid saturation raises ValueError."""
        with pytest.raises(ValueError, match="Saturation must be non-negative"):
            ImageStyle(saturation=-0.2)
    
    def test_image_style__invalid_border_width__raises_error(self):
        """Test ImageStyle with invalid border width raises ValueError."""
        with pytest.raises(ValueError, match="Border width must be non-negative"):
            ImageStyle(border_width=-1)
    
    def test_image_style__invalid_border_color__raises_error(self):
        """Test ImageStyle with invalid border color raises ValueError."""
        with pytest.raises(ValueError, match="Border color values must be between 0 and 255"):
            ImageStyle(border_color=(256, 128, 128))
    
    def test_image_style__invalid_shadow_color__raises_error(self):
        """Test ImageStyle with invalid shadow color raises ValueError."""
        with pytest.raises(ValueError, match="Shadow color values must be between 0 and 255"):
            ImageStyle(shadow_color=(-1, 128, 128))


class TestImageLoadResult:
    """Test ImageLoadResult functionality."""
    
    def test_image_load_result__success__correct_initialization(self):
        """Test successful ImageLoadResult."""
        mock_image = MockPILImage()
        result = ImageLoadResult(
            success=True,
            image=mock_image,
            format="PNG",
            size=(100, 100),
            file_size=1024
        )
        assert result.success is True
        assert result.image is mock_image
        assert result.format == "PNG"
        assert result.size == (100, 100)
        assert result.file_size == 1024
        assert result.error is None
    
    def test_image_load_result__failure__correct_initialization(self):
        """Test failed ImageLoadResult."""
        result = ImageLoadResult(
            success=False,
            error="File not found"
        )
        assert result.success is False
        assert result.image is None
        assert result.error == "File not found"
        assert result.format is None
        assert result.size is None
        assert result.file_size is None


class TestImageCache:
    """Test ImageCache functionality."""
    
    def test_image_cache__initialization__correct_state(self):
        """Test ImageCache initialization."""
        cache = ImageCache(max_cache_size=10, max_memory_mb=50)
        assert len(cache._cache) == 0
        assert cache._max_cache_size == 10
        assert cache._max_memory_bytes == 50 * 1024 * 1024
        assert cache._current_memory_usage == 0
    
    def test_image_cache__get_image_miss__returns_none(self):
        """Test cache miss returns None."""
        cache = ImageCache()
        result = cache.get_image("nonexistent_key")
        assert result is None
        assert cache.get_stats()['misses'] == 1
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_image_cache__put_and_get__caches_correctly(self):
        """Test putting and getting images from cache."""
        cache = ImageCache()
        mock_image = MockPILImage()
        
        cache.put_image("test_key", mock_image, 1024)
        retrieved = cache.get_image("test_key")
        
        assert retrieved is mock_image
        assert cache.get_stats()['hits'] == 1
        assert cache.get_stats()['cache_size'] == 1
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_image_cache__lru_eviction__removes_oldest(self):
        """Test LRU eviction when cache is full."""
        cache = ImageCache(max_cache_size=2, max_memory_mb=100)  # Large memory limit
        
        # Use small images to avoid memory-based eviction
        image1 = MockPILImage(size=(10, 10))
        image2 = MockPILImage(size=(10, 10))
        image3 = MockPILImage(size=(10, 10))
        
        cache.put_image("key1", image1)
        cache.put_image("key2", image2)
        
        # Access key1 to make it more recently used
        cache.get_image("key1")
        
        # Add third image - should evict key2 (oldest)
        cache.put_image("key3", image3)
        
        assert cache.get_image("key1") is image1  # Still in cache
        assert cache.get_image("key2") is None    # Evicted
        assert cache.get_image("key3") is image3  # Newly added
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_image_cache__memory_limit_eviction__removes_items(self):
        """Test memory limit eviction."""
        cache = ImageCache(max_cache_size=10, max_memory_mb=1)  # 1MB limit
        
        # Create large mock image
        large_image = MockPILImage(size=(1000, 1000))  # Should be ~3MB
        
        cache.put_image("large_key", large_image)
        
        # Should trigger eviction due to memory limit
        stats = cache.get_stats()
        assert stats['cache_size'] <= 1
    
    def test_image_cache__clear_cache__empties_cache(self):
        """Test cache clearing."""
        cache = ImageCache()
        mock_image = MockPILImage()
        
        cache.put_image("test_key", mock_image)
        assert cache.get_stats()['cache_size'] == 1
        
        cache.clear_cache()
        assert cache.get_stats()['cache_size'] == 0
        assert cache._current_memory_usage == 0
    
    def test_image_cache__get_stats__returns_correct_metrics(self):
        """Test cache statistics."""
        cache = ImageCache(max_cache_size=5, max_memory_mb=10)
        
        stats = cache.get_stats()
        assert 'cache_size' in stats
        assert 'max_cache_size' in stats
        assert 'memory_usage_mb' in stats
        assert 'max_memory_mb' in stats
        assert 'hit_rate' in stats
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'evictions' in stats
        
        assert stats['max_cache_size'] == 5
        assert stats['max_memory_mb'] == 10


class TestImageWidget:
    """Test ImageWidget functionality."""
    
    def test_image_widget__initialization__correct_state(self):
        """Test ImageWidget initialization with default values."""
        widget = ImageWidget()
        
        assert widget.image_source is None
        assert isinstance(widget._image_source, ReactiveValue)
        assert widget.scale_mode == ScaleMode.FIT
        assert isinstance(widget.image_style, ImageStyle)
        assert widget._needs_reload is True
        assert widget._needs_rescale is True
        assert widget.is_loaded is False
    
    def test_image_widget__initialization_with_source__creates_reactive(self):
        """Test ImageWidget initialization with image source."""
        widget = ImageWidget("test_image.png")
        
        assert widget.image_source == "test_image.png"
        assert isinstance(widget._image_source, ReactiveValue)
        assert widget._image_source.value == "test_image.png"
    
    def test_image_widget__initialization_with_reactive__uses_reactive(self):
        """Test ImageWidget initialization with ReactiveValue."""
        reactive_source = ReactiveValue("reactive_image.png")
        widget = ImageWidget(reactive_source)
        
        assert widget.image_source == "reactive_image.png"
        assert widget._image_source is reactive_source
    
    def test_image_widget__set_image_source_string__updates_reactive(self):
        """Test setting image source with string value."""
        widget = ImageWidget("initial.png")
        
        widget.image_source = "updated.png"
        
        assert widget.image_source == "updated.png"
        assert widget._image_source.value == "updated.png"
        assert widget._needs_reload is True
        assert widget._needs_rescale is True
    
    def test_image_widget__set_image_source_reactive__replaces_reactive(self):
        """Test setting image source with ReactiveValue."""
        widget = ImageWidget("initial.png")
        new_reactive = ReactiveValue("new_reactive.png")
        
        widget.image_source = new_reactive
        
        assert widget.image_source == "new_reactive.png"
        assert widget._image_source is new_reactive
    
    def test_image_widget__reactive_source_change__triggers_update(self):
        """Test that reactive source changes trigger widget updates."""
        reactive_source = ReactiveValue("initial.png")
        widget = ImageWidget(reactive_source)
        
        # Mock the mark dirty method
        widget._mark_dirty = Mock()
        
        # Change reactive value
        reactive_source.value = "changed.png"
        
        # Verify widget was marked dirty
        widget._mark_dirty.assert_called()
        assert widget._needs_reload is True
        assert widget._needs_rescale is True
    
    def test_image_widget__scale_mode_property__get_set(self):
        """Test scale mode property getter and setter."""
        widget = ImageWidget()
        
        widget.scale_mode = ScaleMode.STRETCH
        
        assert widget.scale_mode == ScaleMode.STRETCH
        assert widget._needs_rescale is True
    
    def test_image_widget__image_style_property__get_set(self):
        """Test image style property getter and setter."""
        widget = ImageWidget()
        new_style = ImageStyle(opacity=0.8, brightness=1.2)
        
        widget.image_style = new_style
        
        assert widget.image_style is new_style
        assert widget._needs_rescale is True
    
    def test_image_widget__set_opacity__updates_style(self):
        """Test setting image opacity."""
        widget = ImageWidget()
        
        widget.set_opacity(0.7)
        
        assert widget.image_style.opacity == 0.7
        assert widget._needs_rescale is True
    
    def test_image_widget__set_opacity_invalid__raises_error(self):
        """Test setting invalid opacity raises error."""
        widget = ImageWidget()
        
        with pytest.raises(ValueError, match="Opacity must be between 0.0 and 1.0"):
            widget.set_opacity(1.5)
    
    def test_image_widget__set_brightness__updates_style(self):
        """Test setting image brightness."""
        widget = ImageWidget()
        
        widget.set_brightness(1.3)
        
        assert widget.image_style.brightness == 1.3
        assert widget._needs_rescale is True
    
    def test_image_widget__set_brightness_invalid__raises_error(self):
        """Test setting invalid brightness raises error."""
        widget = ImageWidget()
        
        with pytest.raises(ValueError, match="Brightness must be non-negative"):
            widget.set_brightness(-0.5)
    
    def test_image_widget__set_contrast__updates_style(self):
        """Test setting image contrast."""
        widget = ImageWidget()
        
        widget.set_contrast(1.4)
        
        assert widget.image_style.contrast == 1.4
        assert widget._needs_rescale is True
    
    def test_image_widget__set_contrast_invalid__raises_error(self):
        """Test setting invalid contrast raises error."""
        widget = ImageWidget()
        
        with pytest.raises(ValueError, match="Contrast must be non-negative"):
            widget.set_contrast(-1.0)
    
    def test_image_widget__size_change__triggers_rescale(self):
        """Test that size changes trigger rescaling."""
        widget = ImageWidget("test.png")
        widget._needs_rescale = False  # Reset flag
        
        # Mock the mark dirty method
        widget._mark_dirty = Mock()
        
        # Change size
        widget.size = (200, 150)
        
        # Verify rescaling is needed
        assert widget._needs_rescale is True
        widget._mark_dirty.assert_called()


class TestImageWidgetCacheKeyGeneration:
    """Test ImageWidget cache key generation."""
    
    def test_generate_cache_key__file_path__includes_mtime(self):
        """Test cache key generation for file paths."""
        widget = ImageWidget()
        
        # Test with non-existent file
        key1 = widget._generate_cache_key("nonexistent.png")
        assert key1.startswith("file:nonexistent.png")
        
        # Test with mock existing file
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getmtime', return_value=1234567890):
            key2 = widget._generate_cache_key("existing.png")
            assert key2 == "file:existing.png:1234567890"
    
    def test_generate_cache_key__bytes__uses_hash(self):
        """Test cache key generation for bytes data."""
        widget = ImageWidget()
        test_bytes = b"test image data"
        
        key = widget._generate_cache_key(test_bytes)
        
        assert key.startswith("bytes:")
        assert len(key) > 10  # Should include hash
    
    def test_generate_cache_key__file_object__uses_name_or_id(self):
        """Test cache key generation for file objects."""
        widget = ImageWidget()
        
        # Mock file object with name
        mock_file = Mock()
        mock_file.name = "test_file.png"
        mock_file.read = Mock()
        
        key = widget._generate_cache_key(mock_file)
        assert key == "fileobj:test_file.png"
    
    def test_generate_cache_key__pil_image__uses_object_id(self):
        """Test cache key generation for PIL Image objects."""
        widget = ImageWidget()
        mock_image = MockPILImage()
        
        key = widget._generate_cache_key(mock_image)
        
        assert key.startswith("object:")
        assert str(id(mock_image)) in key


class TestImageWidgetLoading:
    """Test ImageWidget image loading functionality."""
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', False)
    def test_load_image__pil_not_available__sets_error(self):
        """Test image loading when PIL is not available."""
        widget = ImageWidget("test.png")
        
        widget._load_image()
        
        assert widget._loading_error == "PIL (Pillow) not available for image loading"
        assert widget._needs_reload is False
        assert widget.is_loaded is False
    
    def test_load_image__none_source__clears_state(self):
        """Test loading with None source clears state."""
        widget = ImageWidget()
        
        widget._load_image()
        
        assert widget._cached_image is None
        assert widget._cache_key is None
        assert widget._loading_error is None
        assert widget._needs_reload is False
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    @patch('src.tinydisplay.widgets.image._image_cache')
    def test_load_image__cache_hit__uses_cached(self, mock_cache):
        """Test loading uses cached image when available."""
        widget = ImageWidget("test.png")
        mock_image = MockPILImage()
        mock_cache.get_image.return_value = mock_image
        
        widget._load_image()
        
        assert widget._cached_image is mock_image
        assert widget._loading_error is None
        assert widget._needs_reload is False
        mock_cache.get_image.assert_called_once()
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    @patch('src.tinydisplay.widgets.image._image_cache')
    def test_load_image__cache_miss__loads_and_caches(self, mock_cache):
        """Test loading loads image and caches when cache miss."""
        widget = ImageWidget("test.png")
        mock_image = MockPILImage()
        
        mock_cache.get_image.return_value = None  # Cache miss
        
        # Mock the load result
        widget._load_image_from_source = Mock(return_value=ImageLoadResult(
            success=True,
            image=mock_image,
            format="PNG",
            size=(100, 100),
            file_size=1024
        ))
        
        widget._load_image()
        
        assert widget._cached_image is mock_image
        assert widget._loading_error is None
        mock_cache.put_image.assert_called_once()
    
    def test_load_image_from_source__unsupported_type__returns_error(self):
        """Test loading from unsupported source type."""
        widget = ImageWidget()
        
        result = widget._load_image_from_source(123)  # Unsupported type
        
        assert result.success is False
        assert "Unsupported image source type" in result.error
    
    def test_load_from_file_path__nonexistent_file__returns_error(self):
        """Test loading from non-existent file path."""
        widget = ImageWidget()
        
        result = widget._load_from_file_path("nonexistent.png")
        
        assert result.success is False
        assert "Image file not found" in result.error
    
    def test_load_from_bytes__valid_data__returns_success(self):
        """Test loading from bytes data."""
        widget = ImageWidget()
        test_bytes = b"fake image data"
        
        with patch('src.tinydisplay.widgets.image.Image') as mock_image_class:
            mock_image = MockPILImage()
            mock_image_class.open.return_value = mock_image
            
            result = widget._load_from_bytes(test_bytes)
            
            assert result.success is True
            assert result.image is mock_image
            assert result.file_size == len(test_bytes)


class TestImageWidgetScaling:
    """Test ImageWidget image scaling functionality."""
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', False)
    def test_scale_image__pil_not_available__sets_none(self):
        """Test scaling when PIL is not available."""
        widget = ImageWidget()
        widget._cached_image = MockPILImage()
        
        widget._scale_image()
        
        assert widget._scaled_image is None
        assert widget._needs_rescale is False
    
    def test_scale_image__no_cached_image__sets_none(self):
        """Test scaling with no cached image."""
        widget = ImageWidget()
        widget._cached_image = None
        
        widget._scale_image()
        
        assert widget._scaled_image is None
        assert widget._needs_rescale is False
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_scale_image__no_rescale_needed__skips_processing(self):
        """Test scaling skips processing when not needed."""
        widget = ImageWidget()
        widget._cached_image = MockPILImage()
        widget._scaled_image = MockPILImage()
        widget._needs_rescale = False
        widget._last_scale_size = (100, 100)
        widget.size = (100, 100)
        
        widget._scale_image()
        
        # Should not change scaled image
        assert widget._scaled_image is not None
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_scaling__stretch_mode__resizes_to_exact(self):
        """Test stretch scaling mode."""
        widget = ImageWidget()
        widget._scale_mode = ScaleMode.STRETCH
        
        original_image = MockPILImage(size=(200, 100))
        target_size = (150, 200)
        
        result = widget._apply_scaling(original_image, target_size)
        
        # Should resize to exact target size
        assert result.size == (150, 200)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_scaling__fit_mode__maintains_aspect_ratio(self):
        """Test fit scaling mode maintains aspect ratio."""
        widget = ImageWidget()
        widget._scale_mode = ScaleMode.FIT
        
        original_image = MockPILImage(size=(200, 100))  # 2:1 aspect ratio
        target_size = (150, 150)  # Square target
        
        result = widget._apply_scaling(original_image, target_size)
        
        # Should scale to fit within bounds, maintaining aspect ratio
        # 200x100 scaled to fit in 150x150 should be 150x75
        assert result.size == (150, 75)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_scaling__fill_mode__crops_to_fill(self):
        """Test fill scaling mode crops to fill bounds."""
        widget = ImageWidget()
        widget._scale_mode = ScaleMode.FILL
        
        original_image = MockPILImage(size=(200, 100))
        target_size = (100, 100)
        
        result = widget._apply_scaling(original_image, target_size)
        
        # Should crop to exact target size
        assert result.size == (100, 100)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_scaling__center_mode__no_scaling(self):
        """Test center scaling mode does no scaling."""
        widget = ImageWidget()
        widget._scale_mode = ScaleMode.CENTER
        
        original_image = MockPILImage(size=(200, 100))
        target_size = (150, 150)
        
        result = widget._apply_scaling(original_image, target_size)
        
        # Should return original image unchanged
        assert result.size == (200, 100)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_scaling__none_mode__no_scaling(self):
        """Test none scaling mode does no scaling."""
        widget = ImageWidget()
        widget._scale_mode = ScaleMode.NONE
        
        original_image = MockPILImage(size=(200, 100))
        
        widget._cached_image = original_image
        widget.size = (150, 150)
        widget._scale_image()
        
        # Should not apply scaling
        assert widget._scaled_image.size == (200, 100)


class TestImageWidgetStyleEffects:
    """Test ImageWidget style effects functionality."""
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', False)
    def test_apply_style_effects__pil_not_available__returns_original(self):
        """Test style effects when PIL is not available."""
        widget = ImageWidget()
        original_image = MockPILImage()
        
        result = widget._apply_style_effects(original_image)
        
        assert result is original_image
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    @patch('src.tinydisplay.widgets.image.ImageEnhance')
    def test_apply_style_effects__brightness__applies_enhancement(self, mock_enhance):
        """Test brightness style effect."""
        widget = ImageWidget()
        widget._image_style.brightness = 1.5
        
        mock_enhancer = Mock()
        mock_enhance.Brightness.return_value = mock_enhancer
        mock_enhancer.enhance.return_value = MockPILImage()
        
        original_image = MockPILImage()
        result = widget._apply_style_effects(original_image)
        
        mock_enhance.Brightness.assert_called_once_with(original_image)
        mock_enhancer.enhance.assert_called_once_with(1.5)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    @patch('src.tinydisplay.widgets.image.ImageEnhance')
    def test_apply_style_effects__contrast__applies_enhancement(self, mock_enhance):
        """Test contrast style effect."""
        widget = ImageWidget()
        widget._image_style.contrast = 1.3
        
        mock_enhancer = Mock()
        mock_enhance.Contrast.return_value = mock_enhancer
        mock_enhancer.enhance.return_value = MockPILImage()
        
        original_image = MockPILImage()
        result = widget._apply_style_effects(original_image)
        
        mock_enhance.Contrast.assert_called_once()
        mock_enhancer.enhance.assert_called_once_with(1.3)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    @patch('src.tinydisplay.widgets.image.ImageEnhance')
    def test_apply_style_effects__saturation__applies_enhancement(self, mock_enhance):
        """Test saturation style effect."""
        widget = ImageWidget()
        widget._image_style.saturation = 0.8
        
        mock_enhancer = Mock()
        mock_enhance.Color.return_value = mock_enhancer
        mock_enhancer.enhance.return_value = MockPILImage()
        
        original_image = MockPILImage()
        result = widget._apply_style_effects(original_image)
        
        mock_enhance.Color.assert_called_once()
        mock_enhancer.enhance.assert_called_once_with(0.8)
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_filter_effect__blur__applies_filter(self):
        """Test blur filter effect."""
        widget = ImageWidget()
        widget._image_style.filter_effect = ImageFilterEnum.BLUR
        
        original_image = MockPILImage()
        result = widget._apply_filter_effect(original_image)
        
        # Should call filter method (mocked in MockPILImage)
        assert result is not None
    
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_apply_opacity__converts_to_rgba_and_applies(self):
        """Test opacity application."""
        widget = ImageWidget()
        widget._image_style.opacity = 0.7
        
        original_image = MockPILImage(mode='RGB')
        result = widget._apply_opacity(original_image)
        
        # Should convert to RGBA and apply alpha
        assert result is not None


class TestImageWidgetRendering:
    """Test ImageWidget rendering functionality."""
    
    def test_render__invisible_widget__skipped(self):
        """Test that invisible widgets are not rendered."""
        widget = ImageWidget("test.png")
        widget.visible = False
        canvas = Mock()
        
        widget.render(canvas)
        
        # Should not call any canvas methods
        assert not canvas.method_calls
    
    def test_render__zero_alpha__skipped(self):
        """Test that widgets with zero alpha are not rendered."""
        widget = ImageWidget("test.png")
        widget.alpha = 0.0
        canvas = Mock()
        
        widget.render(canvas)
        
        # Should not call any canvas methods
        assert not canvas.method_calls
    
    def test_render__needs_reload__triggers_loading(self):
        """Test that rendering triggers loading if needed."""
        widget = ImageWidget("test.png")
        widget._needs_reload = True
        widget._load_image = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget._load_image.assert_called_once()
    
    def test_render__needs_rescale__triggers_scaling(self):
        """Test that rendering triggers scaling if needed."""
        widget = ImageWidget("test.png")
        widget._needs_rescale = True
        widget._cached_image = MockPILImage()
        widget._needs_reload = False  # Ensure reload doesn't interfere
        widget._scale_image = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget._scale_image.assert_called_once()
    
    def test_render__marks_widget_clean(self):
        """Test that rendering marks widget as clean."""
        widget = ImageWidget("test.png")
        widget.mark_clean = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget.mark_clean.assert_called_once()


class TestImageWidgetProperties:
    """Test ImageWidget property methods."""
    
    def test_loading_error__returns_error_string(self):
        """Test loading_error property."""
        widget = ImageWidget()
        widget._loading_error = "Test error"
        
        assert widget.loading_error == "Test error"
    
    def test_is_loaded__with_cached_image__returns_true(self):
        """Test is_loaded property with cached image."""
        widget = ImageWidget()
        widget._cached_image = MockPILImage()
        widget._loading_error = None
        
        assert widget.is_loaded is True
    
    def test_is_loaded__with_error__returns_false(self):
        """Test is_loaded property with error."""
        widget = ImageWidget()
        widget._cached_image = None
        widget._loading_error = "Error"
        
        assert widget.is_loaded is False
    
    def test_original_size__with_cached_image__returns_size(self):
        """Test original_size property."""
        widget = ImageWidget()
        widget._cached_image = MockPILImage(size=(200, 150))
        
        assert widget.original_size == (200, 150)
    
    def test_original_size__no_cached_image__returns_none(self):
        """Test original_size property with no image."""
        widget = ImageWidget()
        widget._cached_image = None
        
        assert widget.original_size is None
    
    def test_get_scaled_size__with_scaled_image__returns_size(self):
        """Test get_scaled_size method."""
        widget = ImageWidget()
        widget._scaled_image = MockPILImage(size=(100, 75))
        
        assert widget.get_scaled_size() == (100, 75)
    
    def test_get_scaled_size__no_scaled_image__returns_none(self):
        """Test get_scaled_size method with no scaled image."""
        widget = ImageWidget()
        widget._scaled_image = None
        
        assert widget.get_scaled_size() is None
    
    def test_reload_image__forces_reload_and_rescale(self):
        """Test reload_image method."""
        widget = ImageWidget("test.png")
        widget._needs_reload = False
        widget._needs_rescale = False
        widget._load_image = Mock()
        
        result = widget.reload_image()
        
        assert widget._needs_reload is True
        assert widget._needs_rescale is True
        widget._load_image.assert_called_once()


class TestImageWidgetPerformance:
    """Test ImageWidget performance characteristics."""
    
    @pytest.mark.performance
    def test_image_widget__creation_performance__meets_target(self):
        """Test widget creation performance."""
        start_time = time.perf_counter()
        
        widgets = []
        for i in range(50):  # Fewer widgets due to image complexity
            widget = ImageWidget(f"image_{i}.png")
            widgets.append(widget)
        
        creation_time = time.perf_counter() - start_time
        
        # Should create 50 widgets in under 100ms
        assert creation_time < 0.1
        assert len(widgets) == 50
    
    @pytest.mark.performance
    @patch('src.tinydisplay.widgets.image.PIL_AVAILABLE', True)
    def test_image_widget__scaling_performance__meets_target(self):
        """Test image scaling performance."""
        widget = ImageWidget()
        widget._cached_image = MockPILImage(size=(1000, 1000))
        widget.size = (200, 200)
        
        start_time = time.perf_counter()
        
        for _ in range(50):
            widget._needs_rescale = True
            widget._scale_image()
        
        scaling_time = time.perf_counter() - start_time
        
        # Should perform 50 scaling operations in under 100ms
        assert scaling_time < 0.1
    
    @pytest.mark.performance
    def test_image_widget__reactive_update_performance__meets_target(self):
        """Test reactive update performance."""
        reactive_source = ReactiveValue("initial.png")
        widget = ImageWidget(reactive_source)
        
        start_time = time.perf_counter()
        
        for i in range(500):
            reactive_source.value = f"image_{i}.png"
        
        update_time = time.perf_counter() - start_time
        
        # Should handle 500 reactive updates in under 100ms
        assert update_time < 0.1


class TestImageWidgetIntegration:
    """Test ImageWidget integration with other systems."""
    
    def test_image_widget__reactive_data_manager_integration(self):
        """Test integration with ReactiveDataManager."""
        from src.tinydisplay.core.reactive import ReactiveDataManager
        
        manager = ReactiveDataManager()
        binding = manager.create_direct_binding("test_image", "initial.png")
        
        # Create reactive value and bind to the binding
        reactive_source = ReactiveValue("initial.png")
        widget = ImageWidget(reactive_source)
        
        # Simulate binding update by directly setting reactive value
        reactive_source.value = "updated.png"
        
        # Widget should reflect the change
        assert widget.image_source == "updated.png"
    
    def test_image_widget__multiple_reactive_bindings(self):
        """Test widget with multiple reactive bindings."""
        source_reactive = ReactiveValue("image.png")
        opacity_reactive = ReactiveValue(0.8)
        
        widget = ImageWidget(source_reactive)
        
        # Bind opacity to reactive value
        opacity_reactive.bind(lambda old, new: widget.set_opacity(new))
        
        # Update both values
        source_reactive.value = "new_image.png"
        opacity_reactive.value = 0.6
        
        assert widget.image_source == "new_image.png"
        assert widget.image_style.opacity == 0.6
    
    def test_image_widget__canvas_integration(self):
        """Test ImageWidget integration with canvas system."""
        widget = ImageWidget("canvas_test.png")
        mock_canvas = Mock()
        
        # Should not raise errors
        widget.render(mock_canvas)
        
        # Verify widget state is correct
        assert widget.image_source == "canvas_test.png"
        assert widget.visible is True
    
    def test_image_widget__repr__returns_useful_string(self):
        """Test widget string representation."""
        widget = ImageWidget("test_image.png", scale_mode=ScaleMode.STRETCH)
        
        repr_str = repr(widget)
        
        assert "ImageWidget" in repr_str
        assert "test_image.png" in repr_str
        assert "stretch" in repr_str
        assert "loaded=False" in repr_str
        assert "visible=True" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 