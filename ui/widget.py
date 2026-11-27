"""Reusable touchscreen UI components for low-RAM Pi Zero 2 W.

All widgets are built on Tkinter with touch-friendly sizing (48px+ targets),
press visual feedback, and keyboard navigation support.
"""

import tkinter as tk
from typing import Callable, Optional

from ui.styles import COLORS, FONTS, SPACING, TOUCH_TARGET_SIZE, GESTURE
from ui.gestures import GestureRecognizer, bind_gestures, momentum_step


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

        # Allow callers to override the fixed touch-target dimensions so
        # labeled actions (e.g. "← Back", "Export CSV") fit without clipping.
        btn_width = kwargs.pop("width", TOUCH_TARGET_SIZE)
        btn_height = kwargs.pop("height", TOUCH_TARGET_SIZE)
        super().__init__(parent, width=btn_width, height=btn_height, **kwargs)
        # Apply normal background color immediately (CodeRabbit fix)
        self.config(bg=self._normal_bg)

        self._text_id = self.create_text(
            btn_width // 2,
            btn_height // 2,
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
        # Draw track in selected orientation
        if orientation == "horizontal":
            self._track_id = self.create_rectangle(
                0, h // 2 - 4,
                w, h // 2 + 4,
                fill=self._track_color,
                outline="",
            )
        else:  # vertical
            self._track_id = self.create_rectangle(
                w // 2 - 4, 0,
                w // 2 + 4, h,
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
        # Use requested/configured dimensions; winfo_width/height() can return 1
        # before the widget is mapped, which would place the thumb at the edge.
        # Treat a dimension of 1 as uninitialized and use the requested size.
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = self.winfo_reqwidth()
        if h <= 1:
            h = self.winfo_reqheight()
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

        # Use configured size since winfo_width/height() returns 1 before widget is mapped
        width = TOUCH_TARGET_SIZE * 3
        height = TOUCH_TARGET_SIZE

        super().__init__(
            parent,
            width=width,
            height=height,
            **kwargs,
        )
        self._text_id = self.create_text(
            width // 2,
            height // 2,
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


# ------------------------------------------------------------------
# ScrollList: vertical list with drag scrolling and momentum
# ------------------------------------------------------------------
class ScrollList(tk.Frame):
    """A touch‑friendly scrollable list that uses GestureRecognizer.

    On drag: scrolling via yview_scroll (units are pixels).
    On drag_end: momentum carry using FRICTION.
    On tap: calls on_select with the matching item.
    On swipe: calls on_swipe with direction and velocity.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)

        # --- Canvas + inner frame ---
        self._canvas = tk.Canvas(
            self, bg=COLORS["bg"], highlightthickness=0, yscrollincrement=1,
        )
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._inner = tk.Frame(self._canvas, bg=COLORS["bg"])
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw",
                                 tags="inner")
        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._items = []
        self._row_items = {}          # row widget -> item dict
        self._select_cb = None
        self._swipe_cb = None
        self._press_widget = None

        # Momentum state
        self._mom_speed = 0.0  # scroll units per frame (float)
        self._carry = 0.0
        self._mom_job = None

        # Gesture recognizer (pure Python, Tk‑driven)
        self._recognizer = GestureRecognizer(
            width_fn=lambda: self.winfo_width(),
        )
        bind_gestures(
            self._canvas,
            self._recognizer,
            self._on_gesture,
        )

        # Mouse wheel (Windows/macOS X11)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", self._on_wheel_x11)
        self._canvas.bind("<Button-5>", self._on_wheel_x11)

        # Press‑position tracking for tap‑to‑select
        self.bind("<ButtonPress-1>", self._record_press, add="+")

    # --- API ---
    def set_items(self, items, render_row):
        """Render the given items into the inner frame.

        *items* is a sequence of data. *render_row* receives
        ``(parent_frame, item)* and returns a widget that will be packed
        into *inner*.
        """
        self._stop_momentum()
        for w in self._inner.winfo_children():
            w.destroy()
        self._items = list(items)
        self._row_items = {}
        for item in self._items:
            row = render_row(self._inner, item)
            row.pack(fill=tk.X, expand=False)
            self._row_items[row] = item
        self._update_scrollregion()
        self.scroll_to_top()

    def scroll_to_top(self):
        self._canvas.yview_moveto(0)

    def on_select(self, callback):
        self._select_cb = callback

    def on_swipe(self, callback):
        self._swipe_cb = callback

    # --- Layout ---
    def _on_inner_configure(self, event=None):
        self._update_scrollregion()

    def _on_canvas_configure(self, event):
        self._canvas.itemconfigure("inner", width=event.width)

    def _update_scrollregion(self):
        bb = self._canvas.bbox("all")
        if bb:
            self._canvas.configure(scrollregion=bb)

    # --- Gesture handling (via bind_gestures / recognizer) ---
    def _record_press(self, event):
        """Remember the widget under the press for tap‑to‑select."""
        self._press_widget = event.widget

    def _on_gesture(self, name, *args):
        if name == "drag_move":
            dx, dy = args
            # dy > 0 → finger down → content should scroll up → yview_scroll(-dy)
            #   negative dy → drag up → should scroll down → -dy is positive
            self._scroll_units(-dy)
        elif name == "drag_end":
            vx, vy = args
            # vy px/s → scroll units per frame = -vy * (frame_ms/1000)
            self._start_momentum(-vy)
        elif name == "tap":
            self._handle_tap()
        elif name == "swipe":
            direction, velocity = args
            if self._swipe_cb:
                self._swipe_cb(direction, velocity)

    def _handle_tap(self):
        if not self._select_cb or self._press_widget is None:
            return
        row = self._row_for_widget(self._press_widget)
        if row is not None and row in self._row_items:
            self._select_cb(self._row_items[row])

    def _row_for_widget(self, w):
        seen = 0
        while w is not None and seen < 16:
            if w in self._row_items:
                return w
            try:
                w = w.master
            except Exception:
                break
            seen += 1
        return None

    # --- Mouse wheel ---
    def _on_mousewheel(self, event):
        # Windows/macOS: delta is a multiple of 120
        step = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(step, "units")

    def _on_wheel_x11(self, event):
        # X11: Button-4 = scroll up, Button-5 = scroll down
        step = -1 if event.num == 4 else 1
        self._canvas.yview_scroll(step, "units")

    # --- Momentum ---
    def _stop_momentum(self):
        if self._mom_job is not None:
            try:
                self.after_cancel(self._mom_job)
            except Exception:
                pass
            self._mom_job = None
        self._mom_speed = 0.0
        self._carry = 0.0

    def _do_scroll(self, units):
        """Scroll the canvas by *units* (integer) and return True if moved."""
        self._canvas.yview_scroll(int(units) if units else 0, "units")
        # Detect if we've reached a scroll limit
        frac = self._canvas.yview()[0]
        at_top = frac <= 0.0
        at_bottom = self._canvas.yview()[1] >= 1.0
        return not (at_top or at_bottom)

    def _start_momentum(self, speed):
        """Start momentum scrolling. *speed* is scroll units per frame."""
        self._stop_momentum()
        if abs(speed) < 1:
            return
        self._mom_speed = speed
        self._carry = 0.0
        self._mom_job = self.after(GESTURE["frame_ms"], self._momentum_tick)

    def _stop_momentum(self):
        if self._mom_job is not None:
            try:
                self.after_cancel(self._mom_job)
            except Exception:
                pass
            self._mom_job = None
        self._mom_speed = 0.0
        self._carry = 0.0

    def _momentum_tick(self):
        if abs(self._mom_speed) < 0.5:
            # Stop when below 0.5 px/frame
            self._mom_speed = 0.0
            self._mom_job = None
            return
        # Apply friction (GESTURE["friction"] ≈ 0.90)
        self._mom_speed = momentum_step(self._mom_speed)
        # Convert to scroll units: one scroll unit = 1 pixel
        units = self._mom_speed
        # Keep fractional part for the next frame
        self._carry += units
        step = int(self._carry)
        self._carry -= step
        self._canvas.yview_scroll(step, "units")
        # Check scroll limits
        frac = self._canvas.yview()[0]
        at_top = frac <= 0.0
        at_bottom = self._canvas.yview()[1] >= 1.0
        if at_top or at_bottom:
            # Snap to the nearest limit and stop
            self._stop_momentum()
            if at_top:
                self._canvas.yview_moveto(0.0)
            elif at_bottom:
                self._canvas.yview_moveto(1.0)
            return
        self._mom_job = self.after(GESTURE["frame_ms"], self._momentum_tick)

    # --- Helpers ---
    def _stop_momentum(self):
        if self._mom_job is not None:
            try:
                self.after_cancel(self._mom_job)
            except Exception:
                pass
            self._mom_job = None
        self._mom_speed = 0.0
        self._carry = 0.0

    def _record_press(self, event):
        self._press_widget = event.widget

    def _on_gesture(self, name, *args):
        if name == "drag_move":
            dx, dy = args
            self._scroll_units(-dy)
        elif name == "drag_end":
            vx, vy = args
            self._start_momentum(-vy)
        elif name == "tap":
            self._handle_tap()
        elif name == "swipe":
            direction, velocity = args
            if self._swipe_cb:
                self._swipe_cb(direction, velocity)

    def _handle_tap(self):
        if not self._select_cb or self._press_widget is None:
            return
        row = self._row_for_widget(self._press_widget)
        if row is not None and row in self._row_items:
            self._select_cb(self._row_items[row])

    def _row_for_widget(self, w):
        seen = 0
        while w is not None and seen < 16:
            if w in self._row_items:
                return w
            try:
                w = w.master
            except Exception:
                break
            seen += 1
        return None

    # --- Mouse wheel ---
    def _on_mousewheel(self, event):
        # Windows/macOS: delta is a multiple of 120
        step = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(step, "units")

    def _on_wheel_x11(self, event):
        # X11: Button-4 = scroll up, Button-5 = scroll down
        step = -1 if event.num == 4 else 1
        self._canvas.yview_scroll(step, "units")

    # --- Exports ---
    __all__ = [
        "TouchWidget",
        "TouchButton",
        "ProgressBar",
        "AlbumArtLabel",
        "VolumeSlider",
        "StatusLabel",
        "ScrollList",
    ]