"""Reusable touchscreen UI components for low-RAM Pi Zero 2 W.

All widgets are built on Tkinter with touch-friendly sizing (48px+ targets),
press visual feedback, and keyboard navigation support.
"""

import tkinter as tk
from typing import Callable, Optional

from ui.styles import COLORS, FONTS, SPACING, TOUCH_TARGET_SIZE


class TouchWidget(tk.Canvas):
    """Base class for touch widgets with press feedback.

    Provides press/release visual feedback via color inversion and
    consistent touch target sizing.
    """

    def __init__(self, parent, **kwargs):
        # Ensure minimum touch target size
        width = kwargs.pop("width", TOUCH_TARGET_SIZE)
        height = kwargs.pop("height", TOUCH_TARGET_SIZE)
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bg=COLORS["bg"],
            bd=0,
            **kwargs,
        )
        self._is_pressed = False
        self._press_color = None
        self._normal_color = None

        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Leave>", self._on_leave)

    def _on_press(self, event):
        self._is_pressed = True
        self._apply_visual_feedback(True)

    def _on_release(self, event):
        was_pressed = self._is_pressed
        self._is_pressed = False
        self._apply_visual_feedback(False)
        return was_pressed

    def is_pressed(self) -> bool:
        """Return whether this widget is currently pressed."""
        return self._is_pressed

    def _on_leave(self, event):
        self._is_pressed = False
        self._apply_visual_feedback(False)

    def _apply_visual_feedback(self, pressed: bool) -> None:
        """Subclasses override to implement press feedback."""
        pass

    def set_pressed_state(self, pressed: bool) -> None:
        """Externally set the pressed visual state."""
        self._is_pressed = pressed
        self._apply_visual_feedback(pressed)


class TouchButton(TouchWidget):
    """Touch-friendly button with press feedback.

    Supports text label, optional icon, and command callback.
    Minimum touch target is 48px.
    """

    def __init__(
        self,
        parent,
        text: str = "",
        command: Optional[Callable] = None,
        font: tuple = None,
        bg: str = COLORS["card_bg"],
        fg: str = COLORS["fg"],
        active_bg: str = COLORS["accent"],
        active_fg: str = COLORS["fg"],
        **kwargs,
    ):
        self._text = text
        self._command = command
        self._font = font or FONTS["button"]
        self._normal_bg = bg
        self._normal_fg = fg
        self._active_bg = active_bg
        self._active_fg = active_fg

        super().__init__(parent, width=TOUCH_TARGET_SIZE, height=TOUCH_TARGET_SIZE, **kwargs)
        # Apply normal background color immediately (CodeRabbit fix)
        self.config(bg=self._normal_bg)

        self._text_id = self.create_text(
            TOUCH_TARGET_SIZE // 2,
            TOUCH_TARGET_SIZE // 2,
            text=text,
            font=self._font,
            fill=self._normal_fg,
            anchor="center",
        )

    def _apply_visual_feedback(self, pressed: bool) -> None:
        bg = self._active_bg if pressed else self._normal_bg
        fg = self._active_fg if pressed else self._normal_fg
        self.config(bg=bg)
        self.itemconfig(self._text_id, fill=fg, font=self._font)

    def _on_release(self, event):
        was_pressed = self._is_pressed
        super()._on_release(event)
        if was_pressed and self._command:
            self._command()

    def set_text(self, text: str) -> None:
        """Update button text."""
        self._text = text
        self.itemconfig(self._text_id, text=text)

    def set_command(self, command: Optional[Callable]) -> None:
        """Update button command."""
        self._command = command


class ProgressBar(TouchWidget):
    """Horizontal progress bar with tap-to-seek support.

    Shows elapsed vs total duration. Color-coded segments:
    - Played portion (accent color)
    - Remaining portion (muted color)
    """

    def __init__(self, parent, width: int = 400, height: int = 20, **kwargs):
        self._progress = 0.0  # 0.0 to 1.0
        self._color = COLORS["accent"]
        self._remaining_color = COLORS["muted"]

        super().__init__(
            parent,
            width=width,
            height=height,
            **kwargs,
        )

        self._bar_id = self.create_rectangle(
            0, 0, 0, height,
            fill=self._color,
            outline="",
        )
        self._remaining_id = self.create_rectangle(
            0, 0, width, height,
            fill=self._remaining_color,
            outline="",
        )

        self.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        """Tap to seek — calculate fraction from click position."""
        if self._command:
            fraction = event.x / max(1, self.winfo_width())
            self._command(fraction)

    def set_progress(self, fraction: float) -> None:
        """Update progress (0.0 to 1.0)."""
        self._progress = max(0.0, min(1.0, fraction))
        width = self.winfo_width()
        self.coords(
            self._bar_id,
            0, 0, int(width * self._progress), self.winfo_height(),
        )
        self.coords(
            self._remaining_id,
            int(width * self._progress), 0, width, self.winfo_height(),
        )

    def set_seek_callback(self, command: Callable[[float], None]) -> None:
        """Set callback for tap-to-seek events."""
        self._command = command


class AlbumArtLabel(TouchWidget):
    """Album art display with placeholder and aspect ratio maintenance.

    Placeholder is a colored circle with music note symbol.
    """

    def __init__(self, parent, size: int = 300, **kwargs):
        self._size = size
        self._art_image = None
        self._image_id = None

        super().__init__(
            parent,
            width=size,
            height=size,
            **kwargs,
        )

        self._draw_placeholder()

    def _draw_placeholder(self) -> None:
        """Draw placeholder circle when no artwork."""
        size = self._size
        margin = SPACING["sm"]
        self.create_oval(
            margin, margin, size - margin, size - margin,
            fill=COLORS["card_bg"],
            outline=COLORS["muted"],
            width=2,
        )
        self.create_text(
            size // 2,
            size // 2,
            text="♪",
            font=("DejaVu Sans", size // 3, "bold"),
            fill=COLORS["muted"],
            anchor="center",
        )

    def clear_art(self) -> None:
        """Remove all artwork and show placeholder."""
        self.delete("all")
        self._art_image = None
        self._image_id = None
        self._draw_placeholder()

    def set_art(self, image: object) -> None:
        """Set album art image.

        Args:
            image: PIL Image or PhotoImage object to display.
        """
        self.clear_art()
        self._art_image = image  # Keep reference to prevent GC
        self._image_id = self.create_image(
            self._size // 2,
            self._size // 2,
            image=image,
            anchor="center",
        )


class VolumeSlider(TouchWidget):
    """Logarithmic volume slider with 48px touch track.

    Supports vertical or horizontal orientation.
    """

    def __init__(self, parent, orientation: str = "horizontal", width: int = 200, height: int = 24, **kwargs):
        self._orientation = orientation
        self._volume = 1.0  # 0.0 to 1.0
        self._color = COLORS["accent"]
        self._track_color = COLORS["muted"]

        super().__init__(
            parent,
            width=width if orientation == "horizontal" else height,
            height=height if orientation == "horizontal" else width,
            **kwargs,
        )

        # Use configured size since winfo_width/height() returns 0 before widget is shown
        w = width if orientation == "horizontal" else height
        h = height if orientation == "horizontal" else width
        self._track_id = self.create_rectangle(
            0, h // 2 - 4,
            w, h // 2 + 4,
            fill=self._track_color,
            outline="",
        )
        self._thumb_id = self.create_rectangle(
            0, h // 2 - 10,
            0, h // 2 + 10,
            fill=self._color,
            outline="",
        )
        self._update_thumb_position()

        self.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        """Tap to set volume."""
        if self._command:
            if self._orientation == "horizontal":
                fraction = event.x / max(1, self.winfo_width())
            else:
                fraction = 1.0 - (event.y / max(1, self.winfo_height()))
            self._command(max(0.0, min(1.0, fraction)))

    def _update_thumb_position(self) -> None:
        w = self.winfo_width() or self.winfo_reqwidth()
        h = self.winfo_height() or self.winfo_reqheight()
        if self._orientation == "horizontal":
            x = int(w * self._volume)
            self.coords(self._thumb_id, x - 10, h // 2 - 10, x + 10, h // 2 + 10)
        else:
            y = int(h * (1.0 - self._volume))
            self.coords(self._thumb_id, w // 2 - 10, y - 10, w // 2 + 10, y + 10)

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        self._update_thumb_position()

    def set_volume_callback(self, command: Callable[[float], None]) -> None:
        """Set callback for volume changes."""
        self._command = command


class StatusLabel(TouchWidget):
    """Status indicator with color-coded states.

    States: playing, paused, stopped, connecting, unknown
    """

    def __init__(self, parent, text: str = "Stopped", **kwargs):
        self._state_text = text
        self._state_color = COLORS["muted"]
        self._text_id = None

        super().__init__(
            parent,
            width=TOUCH_TARGET_SIZE * 3,
            height=TOUCH_TARGET_SIZE,
            **kwargs,
        )
        self._text_id = self.create_text(
            self.winfo_width() // 2,
            self.winfo_height() // 2,
            text=text,
            font=FONTS["status"],
            fill=self._state_color,
            anchor="center",
        )

    def set_state(self, state: str) -> None:
        """Update status text and color.

        Args:
            state: One of "playing", "paused", "stopped", "connecting", "unknown"
        """
        state_map = {
            "playing": ("Playing", COLORS["accent"]),
            "paused": ("Paused", COLORS["warning"]),
            "stopped": ("Stopped", COLORS["muted"]),
            "connecting": ("Connecting…", COLORS["warning"]),
            "unknown": ("Unknown", COLORS["muted"]),
        }
        text, color = state_map.get(state, ("Unknown", COLORS["muted"]))
        self._state_text = text
        self._state_color = color
        self.itemconfig(self._text_id, text=text, fill=color)


__all__ = [
    "TouchWidget",
    "TouchButton",
    "ProgressBar",
    "AlbumArtLabel",
    "VolumeSlider",
    "StatusLabel",
]
