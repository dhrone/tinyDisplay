#!/usr/bin/env python3
"""
Image Widget Implementation

Provides image rendering with reactive data binding, format support,
caching, scaling, and comprehensive styling for the tinyDisplay framework.
"""

from typing import Union, Optional, Tuple, Dict, Any, BinaryIO
from dataclasses import dataclass
from enum import Enum
import threading
import time
import hashlib
import io
import os
from pathlib import Path

from .base import Widget, ReactiveValue, WidgetBounds
from ..core.reactive import ReactiveDataManager

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Fallback for when PIL is not available
    class Image:
        class Image:
            pass
    class ImageDraw:
        pass
    class ImageFilter:
        pass
    class ImageEnhance:
        pass


class ImageFormat(Enum):
    """Supported image formats."""
    PNG = "PNG"
    JPEG = "JPEG"
    JPG = "JPEG"  # Alias for JPEG
    BMP = "BMP"
    GIF = "GIF"
    WEBP = "WEBP"
    AUTO = "AUTO"  # Auto-detect format


class ScaleMode(Enum):
    """Image scaling modes."""
    FIT = "fit"          # Scale to fit within bounds, maintain aspect ratio
    FILL = "fill"        # Scale to fill bounds, may crop, maintain aspect ratio
    STRETCH = "stretch"  # Stretch to exact bounds, ignore aspect ratio
    NONE = "none"        # No scaling, use original size
    CENTER = "center"    # Center image without scaling


class ImageFilter(Enum):
    """Image filter effects."""
    NONE = "none"
    BLUR = "blur"
    SHARPEN = "sharpen"
    SMOOTH = "smooth"
    EDGE_ENHANCE = "edge_enhance"
    EMBOSS = "emboss"
    CONTOUR = "contour"


@dataclass
class ImageStyle:
    """Image styling configuration."""
    opacity: float = 1.0
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    border_width: int = 0
    border_color: Tuple[int, int, int] = (128, 128, 128)
    border_radius: int = 0
    shadow_offset: Tuple[int, int] = (0, 0)
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_blur: int = 0
    filter_effect: ImageFilter = ImageFilter.NONE
    
    def __post_init__(self):
        """Validate image style parameters."""
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("Opacity must be between 0.0 and 1.0")
        if self.brightness < 0.0:
            raise ValueError("Brightness must be non-negative")
        if self.contrast < 0.0:
            raise ValueError("Contrast must be non-negative")
        if self.saturation < 0.0:
            raise ValueError("Saturation must be non-negative")
        if self.border_width < 0:
            raise ValueError("Border width must be non-negative")
        if not all(0 <= c <= 255 for c in self.border_color):
            raise ValueError("Border color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.shadow_color):
            raise ValueError("Shadow color values must be between 0 and 255")


@dataclass
class ImageLoadResult:
    """Result of image loading operation."""
    success: bool
    image: Optional['Image.Image'] = None
    error: Optional[str] = None
    format: Optional[str] = None
    size: Optional[Tuple[int, int]] = None
    file_size: Optional[int] = None


class ImageCache:
    """Image caching system for memory and performance optimization."""
    
    def __init__(self, max_cache_size: int = 50, max_memory_mb: int = 100):
        self._cache: Dict[str, 'Image.Image'] = {}
        self._cache_info: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._max_cache_size = max_cache_size
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._current_memory_usage = 0
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_usage': 0
        }
    
    def get_image(self, cache_key: str) -> Optional['Image.Image']:
        """Get cached image."""
        with self._lock:
            if cache_key in self._cache:
                self._access_times[cache_key] = time.time()
                self._stats['hits'] += 1
                return self._cache[cache_key]
            
            self._stats['misses'] += 1
            return None
    
    def put_image(self, cache_key: str, image: 'Image.Image', 
                  file_size: Optional[int] = None) -> None:
        """Add image to cache."""
        if not PIL_AVAILABLE:
            return
        
        with self._lock:
            # Calculate image memory usage
            if hasattr(image, 'size') and hasattr(image, 'mode'):
                channels = len(image.getbands()) if hasattr(image, 'getbands') else 3
                memory_size = image.size[0] * image.size[1] * channels
            else:
                memory_size = file_size or 1024  # Fallback estimate
            
            # Check if we need to evict items
            self._evict_if_needed(memory_size)
            
            # Add to cache
            self._cache[cache_key] = image
            self._cache_info[cache_key] = {
                'memory_size': memory_size,
                'file_size': file_size,
                'added_time': time.time()
            }
            self._access_times[cache_key] = time.time()
            self._current_memory_usage += memory_size
            self._stats['memory_usage'] = self._current_memory_usage
    
    def _evict_if_needed(self, new_item_size: int) -> None:
        """Evict items if cache limits would be exceeded."""
        # Check memory limit
        while (self._current_memory_usage + new_item_size > self._max_memory_bytes 
               and self._cache):
            self._evict_lru_item()
        
        # Check count limit
        while len(self._cache) >= self._max_cache_size and self._cache:
            self._evict_lru_item()
    
    def _evict_lru_item(self) -> None:
        """Evict least recently used item."""
        if not self._cache:
            return
        
        # Find LRU item
        lru_key = min(self._access_times.keys(), 
                     key=lambda k: self._access_times[k])
        
        # Remove from cache
        self._cache.pop(lru_key, None)
        cache_info = self._cache_info.pop(lru_key, {})
        self._access_times.pop(lru_key, None)
        
        # Update memory usage
        memory_size = cache_info.get('memory_size', 0)
        self._current_memory_usage -= memory_size
        self._stats['evictions'] += 1
        self._stats['memory_usage'] = self._current_memory_usage
    
    def clear_cache(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()
            self._cache_info.clear()
            self._access_times.clear()
            self._current_memory_usage = 0
            self._stats['memory_usage'] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
            
            return {
                'cache_size': len(self._cache),
                'max_cache_size': self._max_cache_size,
                'memory_usage_mb': self._current_memory_usage / (1024 * 1024),
                'max_memory_mb': self._max_memory_bytes / (1024 * 1024),
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions']
            }


# Global image cache instance
_image_cache = ImageCache()


class ImageWidget(Widget):
    """Image widget with reactive data binding and comprehensive image handling.
    
    Supports multiple image formats, caching, scaling modes, and styling effects.
    Integrates with the reactive system for dynamic image source updates.
    
    Args:
        image_source: Image source (file path, bytes, PIL Image, or reactive value)
        scale_mode: How to scale the image within widget bounds
        image_style: Image styling configuration
        **kwargs: Additional widget arguments
        
    Example:
        >>> widget = ImageWidget("path/to/image.png", 
        ...                      scale_mode=ScaleMode.FIT,
        ...                      image_style=ImageStyle(opacity=0.8))
        >>> widget.bind_data("image_source", reactive_data_source)
    """
    
    __slots__ = (
        '_image_source', '_scale_mode', '_image_style', '_cached_image',
        '_cache_key', '_load_result', '_scaled_image', '_needs_reload',
        '_needs_rescale', '_last_scale_size', '_loading_error'
    )
    
    def __init__(
        self,
        image_source: Union[str, bytes, 'Image.Image', ReactiveValue, None] = None,
        scale_mode: ScaleMode = ScaleMode.FIT,
        image_style: Optional[ImageStyle] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        
        # Image source and configuration
        self._image_source = self._ensure_reactive(image_source)
        self._image_source.bind(self._on_image_source_changed)
        self._scale_mode = scale_mode
        self._image_style = image_style or ImageStyle()
        
        # Caching and loading state
        self._cached_image: Optional['Image.Image'] = None
        self._cache_key: Optional[str] = None
        self._load_result: Optional[ImageLoadResult] = None
        self._scaled_image: Optional['Image.Image'] = None
        self._loading_error: Optional[str] = None
        
        # State flags
        self._needs_reload = True
        self._needs_rescale = True
        self._last_scale_size: Optional[Tuple[int, int]] = None
        
        # Bind to size changes for re-scaling
        self._size.bind(self._on_size_changed)
    
    @property
    def image_source(self) -> Any:
        """Get current image source."""
        return self._image_source.value
    
    @image_source.setter
    def image_source(self, value: Union[str, bytes, 'Image.Image', ReactiveValue, None]) -> None:
        """Set image source."""
        if isinstance(value, ReactiveValue):
            self._image_source.unbind(self._on_image_source_changed)
            self._image_source = value
            self._image_source.bind(self._on_image_source_changed)
        else:
            self._image_source.value = value
        self._needs_reload = True
        self._needs_rescale = True
        self._mark_dirty()
    
    @property
    def scale_mode(self) -> ScaleMode:
        """Get current scale mode."""
        return self._scale_mode
    
    @scale_mode.setter
    def scale_mode(self, mode: ScaleMode) -> None:
        """Set scale mode."""
        self._scale_mode = mode
        self._needs_rescale = True
        self._mark_dirty()
    
    @property
    def image_style(self) -> ImageStyle:
        """Get current image style."""
        return self._image_style
    
    @image_style.setter
    def image_style(self, style: ImageStyle) -> None:
        """Set image style."""
        self._image_style = style
        self._needs_rescale = True  # Style changes may require re-processing
        self._mark_dirty()
    
    @property
    def loading_error(self) -> Optional[str]:
        """Get last loading error, if any."""
        return self._loading_error
    
    @property
    def is_loaded(self) -> bool:
        """Check if image is successfully loaded."""
        return self._cached_image is not None and self._loading_error is None
    
    @property
    def original_size(self) -> Optional[Tuple[int, int]]:
        """Get original image size."""
        if self._cached_image and hasattr(self._cached_image, 'size'):
            return self._cached_image.size
        return None
    
    def set_opacity(self, opacity: float) -> None:
        """Set image opacity."""
        if not 0.0 <= opacity <= 1.0:
            raise ValueError("Opacity must be between 0.0 and 1.0")
        self._image_style.opacity = opacity
        self._needs_rescale = True
        self._mark_dirty()
    
    def set_brightness(self, brightness: float) -> None:
        """Set image brightness."""
        if brightness < 0.0:
            raise ValueError("Brightness must be non-negative")
        self._image_style.brightness = brightness
        self._needs_rescale = True
        self._mark_dirty()
    
    def set_contrast(self, contrast: float) -> None:
        """Set image contrast."""
        if contrast < 0.0:
            raise ValueError("Contrast must be non-negative")
        self._image_style.contrast = contrast
        self._needs_rescale = True
        self._mark_dirty()
    
    def reload_image(self) -> bool:
        """Force reload of the image from source.
        
        Returns:
            True if reload was successful, False otherwise
        """
        self._needs_reload = True
        self._needs_rescale = True
        self._load_image()
        return self.is_loaded
    
    def get_scaled_size(self) -> Optional[Tuple[int, int]]:
        """Get the size of the scaled image."""
        if self._scaled_image and hasattr(self._scaled_image, 'size'):
            return self._scaled_image.size
        return None
    
    def render(self, canvas: 'Canvas') -> None:
        """Render the image widget to the canvas."""
        if not self.visible or self.alpha <= 0:
            return
        
        # Load image if needed
        if self._needs_reload:
            self._load_image()
        
        # Scale image if needed
        if self._needs_rescale and self._cached_image:
            self._scale_image()
        
        # Render image if available
        if self._scaled_image:
            self._render_image(canvas)
        elif self._loading_error:
            self._render_error_placeholder(canvas)
        else:
            self._render_loading_placeholder(canvas)
        
        # Mark as clean
        self.mark_clean()
    
    def _ensure_reactive(self, value: Any) -> ReactiveValue:
        """Convert values to ReactiveValue instances."""
        if isinstance(value, ReactiveValue):
            return value
        return ReactiveValue(value)
    
    def _on_image_source_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive image source updates."""
        self._needs_reload = True
        self._needs_rescale = True
        self._mark_dirty()
    
    def _on_size_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle size changes that require re-scaling."""
        self._needs_rescale = True
        self._mark_dirty()
    
    def _load_image(self) -> None:
        """Load image from source with caching."""
        if not PIL_AVAILABLE:
            self._loading_error = "PIL (Pillow) not available for image loading"
            self._needs_reload = False
            return
        
        source = self._image_source.value
        if source is None:
            self._cached_image = None
            self._cache_key = None
            self._loading_error = None
            self._needs_reload = False
            return
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(source)
            
            # Check cache first
            cached_image = _image_cache.get_image(cache_key)
            if cached_image:
                self._cached_image = cached_image
                self._cache_key = cache_key
                self._loading_error = None
                self._needs_reload = False
                return
            
            # Load image
            load_result = self._load_image_from_source(source)
            
            if load_result.success and load_result.image:
                # Cache the loaded image
                _image_cache.put_image(cache_key, load_result.image, load_result.file_size)
                
                self._cached_image = load_result.image
                self._cache_key = cache_key
                self._load_result = load_result
                self._loading_error = None
            else:
                self._cached_image = None
                self._cache_key = None
                self._loading_error = load_result.error or "Unknown loading error"
            
            self._needs_reload = False
            
        except Exception as e:
            self._cached_image = None
            self._cache_key = None
            self._loading_error = f"Image loading error: {str(e)}"
            self._needs_reload = False
    
    def _generate_cache_key(self, source: Any) -> str:
        """Generate cache key for image source."""
        if isinstance(source, str):
            # File path - include modification time if file exists
            if os.path.exists(source):
                mtime = os.path.getmtime(source)
                return f"file:{source}:{mtime}"
            else:
                return f"file:{source}"
        elif isinstance(source, bytes):
            # Bytes data - use hash
            hash_obj = hashlib.md5(source)
            return f"bytes:{hash_obj.hexdigest()}"
        elif hasattr(source, 'read'):
            # File-like object - try to get name or use object id
            name = getattr(source, 'name', str(id(source)))
            return f"fileobj:{name}"
        else:
            # PIL Image or other - use object id
            return f"object:{id(source)}"
    
    def _load_image_from_source(self, source: Any) -> ImageLoadResult:
        """Load image from various source types."""
        try:
            if isinstance(source, str):
                return self._load_from_file_path(source)
            elif isinstance(source, bytes):
                return self._load_from_bytes(source)
            elif hasattr(source, 'read'):
                return self._load_from_file_object(source)
            elif hasattr(source, 'size') and hasattr(source, 'mode'):
                # Assume it's already a PIL Image
                return ImageLoadResult(
                    success=True,
                    image=source,
                    format=getattr(source, 'format', 'UNKNOWN'),
                    size=source.size
                )
            else:
                return ImageLoadResult(
                    success=False,
                    error=f"Unsupported image source type: {type(source)}"
                )
        
        except Exception as e:
            return ImageLoadResult(
                success=False,
                error=f"Error loading image: {str(e)}"
            )
    
    def _load_from_file_path(self, file_path: str) -> ImageLoadResult:
        """Load image from file path."""
        if not os.path.exists(file_path):
            return ImageLoadResult(
                success=False,
                error=f"Image file not found: {file_path}"
            )
        
        try:
            file_size = os.path.getsize(file_path)
            image = Image.open(file_path)
            
            return ImageLoadResult(
                success=True,
                image=image,
                format=image.format,
                size=image.size,
                file_size=file_size
            )
        
        except Exception as e:
            return ImageLoadResult(
                success=False,
                error=f"Error loading image from {file_path}: {str(e)}"
            )
    
    def _load_from_bytes(self, image_bytes: bytes) -> ImageLoadResult:
        """Load image from bytes data."""
        try:
            image_io = io.BytesIO(image_bytes)
            image = Image.open(image_io)
            
            return ImageLoadResult(
                success=True,
                image=image,
                format=image.format,
                size=image.size,
                file_size=len(image_bytes)
            )
        
        except Exception as e:
            return ImageLoadResult(
                success=False,
                error=f"Error loading image from bytes: {str(e)}"
            )
    
    def _load_from_file_object(self, file_obj: BinaryIO) -> ImageLoadResult:
        """Load image from file-like object."""
        try:
            image = Image.open(file_obj)
            
            return ImageLoadResult(
                success=True,
                image=image,
                format=image.format,
                size=image.size
            )
        
        except Exception as e:
            return ImageLoadResult(
                success=False,
                error=f"Error loading image from file object: {str(e)}"
            )
    
    def _scale_image(self) -> None:
        """Scale and process image according to current settings."""
        if not self._cached_image or not PIL_AVAILABLE:
            self._scaled_image = None
            self._needs_rescale = False
            return
        
        try:
            current_size = self.size
            
            # Check if rescaling is actually needed
            if (not self._needs_rescale and 
                self._last_scale_size == current_size and 
                self._scaled_image):
                return
            
            # Start with original image
            processed_image = self._cached_image.copy()
            
            # Apply scaling
            if self._scale_mode != ScaleMode.NONE:
                processed_image = self._apply_scaling(processed_image, current_size)
            
            # Apply style effects
            processed_image = self._apply_style_effects(processed_image)
            
            self._scaled_image = processed_image
            self._last_scale_size = current_size
            self._needs_rescale = False
            
        except Exception as e:
            self._loading_error = f"Error processing image: {str(e)}"
            self._scaled_image = None
            self._needs_rescale = False
    
    def _apply_scaling(self, image: 'Image.Image', target_size: Tuple[int, int]) -> 'Image.Image':
        """Apply scaling based on scale mode."""
        if not hasattr(image, 'size'):
            return image
        
        original_size = image.size
        target_width, target_height = target_size
        
        if self._scale_mode == ScaleMode.STRETCH:
            # Stretch to exact size
            return image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        elif self._scale_mode == ScaleMode.FIT:
            # Scale to fit within bounds, maintain aspect ratio
            scale_x = target_width / original_size[0]
            scale_y = target_height / original_size[1]
            scale = min(scale_x, scale_y)
            
            new_width = int(original_size[0] * scale)
            new_height = int(original_size[1] * scale)
            
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        elif self._scale_mode == ScaleMode.FILL:
            # Scale to fill bounds, may crop, maintain aspect ratio
            scale_x = target_width / original_size[0]
            scale_y = target_height / original_size[1]
            scale = max(scale_x, scale_y)
            
            new_width = int(original_size[0] * scale)
            new_height = int(original_size[1] * scale)
            
            scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop to target size
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            
            return scaled_image.crop((left, top, right, bottom))
        
        elif self._scale_mode == ScaleMode.CENTER:
            # Center without scaling
            return image
        
        return image
    
    def _apply_style_effects(self, image: 'Image.Image') -> 'Image.Image':
        """Apply style effects to image."""
        if not PIL_AVAILABLE:
            return image
        
        processed_image = image
        
        try:
            # Apply brightness
            if self._image_style.brightness != 1.0:
                enhancer = ImageEnhance.Brightness(processed_image)
                processed_image = enhancer.enhance(self._image_style.brightness)
            
            # Apply contrast
            if self._image_style.contrast != 1.0:
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(self._image_style.contrast)
            
            # Apply saturation
            if self._image_style.saturation != 1.0:
                enhancer = ImageEnhance.Color(processed_image)
                processed_image = enhancer.enhance(self._image_style.saturation)
            
            # Apply filter effects
            if self._image_style.filter_effect != ImageFilter.NONE:
                processed_image = self._apply_filter_effect(processed_image)
            
            # Apply opacity
            if self._image_style.opacity != 1.0:
                processed_image = self._apply_opacity(processed_image)
            
        except Exception as e:
            # If style processing fails, return original
            print(f"Warning: Image style processing failed: {e}")
            return image
        
        return processed_image
    
    def _apply_filter_effect(self, image: 'Image.Image') -> 'Image.Image':
        """Apply filter effects to image."""
        filter_effect = self._image_style.filter_effect
        
        if filter_effect == ImageFilter.BLUR:
            return image.filter(ImageFilter.BLUR)
        elif filter_effect == ImageFilter.SHARPEN:
            return image.filter(ImageFilter.SHARPEN)
        elif filter_effect == ImageFilter.SMOOTH:
            return image.filter(ImageFilter.SMOOTH)
        elif filter_effect == ImageFilter.EDGE_ENHANCE:
            return image.filter(ImageFilter.EDGE_ENHANCE)
        elif filter_effect == ImageFilter.EMBOSS:
            return image.filter(ImageFilter.EMBOSS)
        elif filter_effect == ImageFilter.CONTOUR:
            return image.filter(ImageFilter.CONTOUR)
        
        return image
    
    def _apply_opacity(self, image: 'Image.Image') -> 'Image.Image':
        """Apply opacity to image."""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create alpha mask
        alpha = image.split()[-1]
        alpha = alpha.point(lambda p: int(p * self._image_style.opacity))
        
        # Apply alpha mask
        image.putalpha(alpha)
        return image
    
    def _render_image(self, canvas: 'Canvas') -> None:
        """Render the processed image to canvas."""
        # This is a placeholder for actual canvas integration
        # Real implementation would integrate with the canvas rendering backend
        pass
    
    def _render_error_placeholder(self, canvas: 'Canvas') -> None:
        """Render error placeholder when image loading fails."""
        # This would render an error icon or message
        pass
    
    def _render_loading_placeholder(self, canvas: 'Canvas') -> None:
        """Render loading placeholder while image is being loaded."""
        # This would render a loading indicator
        pass
    
    def __repr__(self) -> str:
        source_str = str(self._image_source.value)[:30] + "..." if len(str(self._image_source.value)) > 30 else str(self._image_source.value)
        return (f"ImageWidget(id={self.widget_id}, source='{source_str}', "
                f"scale_mode={self._scale_mode.value}, loaded={self.is_loaded}, visible={self.visible})") 