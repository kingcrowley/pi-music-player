"""Gesture recognition for the Tkinter touch UI — pure Python, no Tk imports.

Pure Python so it can be unit-tested without a display. The Tk adapter
`bind_gestures` connects this logic to actual Tk widgets.

Output contract per press: zero or more ``drag_move`` events, then exactly
one final event: ``tap``, ``long_press``, ``drag_end`` or ``swipe``.
Every recognizer method returns a list of event tuples, so it never calls
into Tk and never schedules timers itself.
"""

import time
from typing import Callable, List, Optional, Tuple

from ui.styles import GESTURE

# An event is (name, *args):
#   ("tap",)
#   ("long_press",)
#   ("drag_move", dx, dy)      # incremental movement since previous event
#   ("drag_end", vx, vy)       # velocity in px/s
#   ("swipe", direction, velocity)  # direction "left"/"right", velocity px/s


class GestureRecognizer:
    """Pure-Python single-pointer gesture recognizer.

    The caller supplies monotonic timestamps (seconds) and a ``width_fn``
    returning the current window width in pixels (read at release time, so a
    resized window is handled). The Tk adapter calls ``timeout(t)`` when its
    long-press timer fires; the recognizer never schedules anything itself.
    """

    def __init__(
        self,
        width_fn: Callable[[], int],
        tap_slop: int = GESTURE["tap_slop"],
        long_press_ms: int = GESTURE["long_press_ms"],
        swipe_min_px: int = GESTURE["swipe_min_px"],
        swipe_max_ms: int = GESTURE["swipe_max_ms"],
        swipe_fraction: float = GESTURE["swipe_fraction"],
    ):
        self._width_fn = width_fn
        self._tap_slop = tap_slop
        self._long_press_ms = long_press_ms
        self._swipe_min_px = swipe_min_px
        self._swipe_max_ms = swipe_max_ms
        self._swipe_fraction = swipe_fraction
        self._reset()

    # ------------------------------------------------------------------
    # state helpers
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._active = False
        self._x0 = 0.0
        self._y0 = 0.0
        self._t0 = 0.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._drag_started = False
        self._long_press_fired = False

    def _moved_past_slop(self, x: float, y: float) -> bool:
        dx = x - self._x0
        dy = y - self._y0
        return (dx * dx + dy * dy) ** 0.5 > self._tap_slop

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def press(self, x: float, y: float, t: float) -> List[Tuple]:
        """Begin a press sequence. Returns [] (contract: nothing emitted yet)."""
        self._reset()
        self._active = True
        self._x0 = x
        self._y0 = y
        self._t0 = t
        self._last_x = x
        self._last_y = y
        return []

    def move(self, x: float, y: float, t: float) -> List[Tuple]:
        """Move while pressed. Emits incremental ``drag_move`` once past slop."""
        if not self._active:
            return []

        if not self._drag_started and self._moved_past_slop(x, y):
            # Crossing the slop boundary starts a drag; no tap/long-press after.
            self._drag_started = True

        if not self._drag_started:
            return []

        dx = x - self._last_x
        dy = y - self._last_y
        self._last_x = x
        self._last_y = y
        if dx == 0 and dy == 0:
            return []
        return [("drag_move", dx, dy)]

    def release(self, x: float, y: float, t: float) -> List[Tuple]:
        """Release the press. Emits exactly one final event (or nothing)."""
        if not self._active:
            return []

        self._active = False

        if self._drag_started:
            return self._finalize_drag(x, y, t)

        if self._long_press_fired:
            # Long press already fired while the finger was down.
            return []

        # Not a drag and no long press has fired yet: classify on release.
        if t - self._t0 >= self._long_press_ms / 1000.0:
            return [("long_press",)]
        return [("tap",)]

    def timeout(self, t: float) -> List[Tuple]:
        """The long-press timer fired (called by the adapter)."""
        if not self._active:
            # A timeout that arrives after release (or with no press) does nothing.
            return []
        if self._drag_started or self._long_press_fired:
            return []
        if self._moved_past_slop(self._last_x, self._last_y):
            return []
        if t - self._t0 >= self._long_press_ms / 1000.0:
            self._long_press_fired = True
            return [("long_press",)]
        return []

    def _finalize_drag(self, x: float, y: float, t: float) -> List[Tuple]:
        dx = x - self._x0
        dy = y - self._y0
        duration = t - self._t0
        width = self._width_fn()

        vx = dx / duration if duration > 0 else 0.0
        vy = dy / duration if duration > 0 else 0.0

        swipe_threshold = max(self._swipe_min_px, self._swipe_fraction * width)
        is_swipe = (
            abs(dx) >= swipe_threshold
            and duration < self._swipe_max_ms / 1000.0
            and abs(dx) > 2 * abs(dy)
        )
        if is_swipe:
            direction = "left" if dx > 0 else "right"
            return [("swipe", direction, abs(vx))]
        return [("drag_end", vx, vy)]


def _bind_recursive(widget, on_press, on_move, on_release, exclude) -> None:
    """Bind the three pointer events on ``widget`` and every descendant."""
    if widget in exclude:
        # Skip the widget and all of its descendants.
        return
    widget.bind("<ButtonPress-1>", on_press, add="+")
    widget.bind("<B1-Motion>", on_move, add="+")
    widget.bind("<ButtonRelease-1>", on_release, add="+")
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        _bind_recursive(child, on_press, on_move, on_release, exclude)


def _clear_pressed_state(widget) -> None:
    """Clear the pressed visual state on ``widget`` and its ancestors.

    TouchButton._on_release fires its command whenever ``_is_pressed`` is still
    set (only ``_on_leave`` clears it normally). In a scrolling list the button
    moves with the finger, so the finger never "leaves" it — without this the
    command would fire at the end of every drag. We clear the widget that was
    pressed and any TouchWidget ancestors.
    """
    w = widget
    seen = 0
    while w is not None and seen < 8:
        setter = getattr(w, "set_pressed_state", None)
        if callable(setter):
            try:
                setter(False)
            except Exception:
                pass
        try:
            w = w.master
        except Exception:
            break
        seen += 1


def bind_gestures(
    widget,
    recognizer: GestureRecognizer,
    on_event: Callable[..., None],
    exclude: tuple = (),
) -> None:
    """Connect a ``GestureRecognizer`` to a Tk widget and its descendants.

    - Binds ``<ButtonPress-1>``, ``<B1-Motion>`` and ``<ButtonRelease-1>`` with
      ``add="+"`` on ``widget`` and every descendant (X11's implicit grab sends
      motion/release only to the widget that was pressed).
    - Never binds on the root window or the ``all`` bindtag.
    - Widgets in ``exclude`` and their descendants are skipped (the
      ``ProgressBar``, which seeks on ``<Button-1>``, is always excluded).
    - Converts via ``event.x_root`` / ``event.y_root``.
    - Uses ``time.monotonic()`` (not ``event.time``, which wraps at 32 bits and
      is 0 for ``event_generate``).
    - Starts a ``widget.after(LONG_PRESS_MS, ...)`` timer on press and cancels
      it on drag or release.
    - On a ``drag_move`` or ``long_press`` event, clears the pressed visual
      state of the widget under the press so button commands do not fire.
    """
    # Do not bind on the Tk root or the "all" bindtag.
    try:
        if widget.winfo_toplevel() is widget:
            pass  # still allowed to bind descendants of a Toplevel
    except Exception:
        pass

    state = {"pressed": None, "timer": None}

    def _dispatch(events) -> None:
        for evt in events:
            name = evt[0]
            if name in ("drag_move", "long_press"):
                if state["pressed"] is not None:
                    _clear_pressed_state(state["pressed"])
            on_event(*evt)

    def _cancel_timer() -> None:
        if state["timer"] is not None and state["pressed"] is not None:
            try:
                state["pressed"].after_cancel(state["timer"])
            except Exception:
                pass
        state["timer"] = None

    def _fire_long_press() -> None:
        _dispatch(recognizer.timeout(time.monotonic()))

    def on_press(event) -> None:
        state["pressed"] = event.widget
        # Start the long-press timer on the widget that received the press.
        widget_after = getattr(event.widget, "after", None)
        if callable(widget_after):
            try:
                state["timer"] = widget_after(
                    recognizer._long_press_ms, _fire_long_press
                )
            except Exception:
                state["timer"] = None
        _dispatch(recognizer.press(event.x_root, event.y_root, time.monotonic()))

    def on_move(event) -> None:
        events = recognizer.move(event.x_root, event.y_root, time.monotonic())
        if any(evt[0] == "drag_move" for evt in events):
            _cancel_timer()
        _dispatch(events)

    def on_release(event) -> None:
        _cancel_timer()
        _dispatch(recognizer.release(event.x_root, event.y_root, time.monotonic()))
        state["pressed"] = None

    _bind_recursive(widget, on_press, on_move, on_release, exclude)


def momentum_step(speed: float, friction: float = GESTURE["friction"]) -> float:
    """Return the next momentum speed. Pure function, tested without a display."""
    return speed * friction


__all__ = [
    "GestureRecognizer",
    "bind_gestures",
    "momentum_step",
]
