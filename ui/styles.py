"""Touch-friendly theme and font constants for low-RAM Pi Zero 2 W.

All touch targets are minimum 48px per accessibility guidelines.
Colors use high-contrast pairs for sunlight readability on Pi touchscreens.
"""

# Touch target sizing
TOUCH_TARGET_SIZE = 48      # px minimum for finger-friendly interaction
TOUCH_TARGET_PADDING = 8    # px inside touch targets
TOUCH_TARGET_SPACING = 12   # px between touch targets

# Colors — high contrast for Pi touchscreens (readable in sunlight)
COLORS = {
    "bg": "#1a1a2e",          # deep navy background
    "fg": "#eeeeee",          # near-white foreground
    "accent": "#00d4aa",      # bright teal for active states
    "accent_hover": "#00ffcc",  # lighter teal on press
    "danger": "#ff4444",      # red for stop/danger
    "warning": "#ffaa00",     # orange for warnings
    "muted": "#888888",       # gray for disabled/inactive
    "card_bg": "#16213e",     # slightly lighter panel background
}

# System font fallbacks for portability across Linux distros
FONTS = {
    "title": ("DejaVu Sans", 28, "bold"),
    "artist": ("DejaVu Sans", 20),
    "album": ("DejaVu Sans", 16),
    "button": ("DejaVu Sans", 14, "bold"),
    "status": ("DejaVu Sans", 12),
    "time": ("DejaVu Sans Mono", 18),
}

# Spacing constants (px)
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
}

# Window defaults
WINDOW = {
    "fullscreen": True,
    "width": 800,
    "height": 480,          # common Pi touchscreen resolution
    "min_width": 640,
    "min_height": 480,
}

__all__ = [
    "TOUCH_TARGET_SIZE",
    "TOUCH_TARGET_PADDING",
    "TOUCH_TARGET_SPACING",
    "COLORS",
    "FONTS",
    "SPACING",
    "WINDOW",
]
