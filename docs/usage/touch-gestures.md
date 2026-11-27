# Touchscreen Gestures Guide

Touch interaction guide for the music player UI on Raspberry Pi Zero 2 W with touchscreen.

> **Target:** Resistive / capacitive touchscreen, X11/Wayland+XWayland
> **Default mode:** Touchscreen-optimized (large touch targets)

---

## Overview

Tkinter receives touch as single-pointer mouse events, so all gestures below are
single-pointer gestures. There is no multi-touch, no pinch-to-zoom, and no
edge-swipe.

Each gesture the recognizer tracks produces events that the UI maps to actions:

| Gesture | Action |
|---------|--------|
| Tap | Click a button, select a row / screen |
| Long press | Clear pressed state (no context menu yet — planned) |
| Drag | Scroll a scrollable list |
| Swipe left/right | Navigate between screens |
| Drag along progress bar | Seek (the progress bar is excluded from swipe navigation) |

---

## Gesture Recognition (Slice 3.1a Touch Toolkit)

Gestures are recognized by `ui.gestures.GestureRecognizer`, a pure-Python state
machine (no Tk imports) that can be unit-tested without a display.

### Input

The recognizer is fed `press(x, y, t)`, `move(x, y, t)` and `release(x, y, t)`
with `t` in seconds from a monotonic clock. A `timeout(t)` callback reports a
long-press timer firing. The recognizer never schedules anything itself.

### Output contract

Per press: zero or more `drag_move(dx, dy)` events, then exactly one final
event:

| Final event | Meaning |
|-------------|---------|
| `tap` | Press stayed under the slop distance and released quickly |
| `long_press` | Hold >= 500 ms without moving past slop |
| `drag_end(vx, vy)` | Drag released without meeting the swipe test |
| `swipe(direction, velocity)` | Fast horizontal drag |

### Thresholds (`ui.styles.GESTURE`)

| Name | Value | Meaning |
|------|-------|---------|
| `tap_slop` | 10 px | Movement ≤ this counts as "not moved" |
| `long_press_ms` | 500 ms | Hold time for long press |
| `swipe_min_px` | 80 px | Minimum horizontal movement for swipe |
| `swipe_max_ms` | 400 ms | Maximum duration for a swipe |
| `swipe_fraction` | 0.10 | Fraction of window width for swipe threshold |
| `friction` | 0.90 | Momentum decay per frame |
| `frame_ms` | 33 ms | Momentum frame interval |

The actual swipe threshold is `max(swipe_min_px, swipe_fraction × width)`.

---

## Swipe Navigation (Slice 3.1a Touch Toolkit)

Swipes navigate between screens:

- **Swipe left:** Now Playing → Stats → Discover (once Slice 3.2 adds Discover)
- **Swipe right:** Stats → Now Playing

The **ProgressBar** is always excluded from swipe recognition so that tapping
and dragging along the progress bar seeks without navigating. Every gesture
action still has an equivalent button, so gestures never remove existing
controls.

---

## Scrollable Lists (ScrollList)

`ui.widget.ScrollList` is a Tk `Frame` wrapping a `Canvas` with an inner frame.
It handles drag scrolling with momentum:

- Drag moves the list 1:1 with the finger.
- Releasing with speed continues scrolling briefly, decaying by `friction` each
  frame until it stops below 0.5 px/frame or reaches a list end.
- A new press cancels momentum immediately.
- `set_items(items, render_row)` populates the list; `on_select(callback)` fires
  on row tap only; `on_swipe(callback)` receives horizontal swipes.
- `<MouseWheel>` (Windows/macOS) and `<Button-4>`/`<Button-5>` (X11) scroll.

For large libraries (~200+ rows), Slice 3.2 shows the first 200 plus a "More"
row rather than building thousands of widgets.

---

## Widget Authors

Use `ui.gestures.bind_gestures(widget, recognizer, on_event, exclude=())` to
connect a `GestureRecognizer` to a Tk widget and all its descendants:

- `exclude` skips a widget and its descendants. Always exclude the
  `ProgressBar` (it seeks on `<Button-1>`).
- Never bind on the root window or the `all` bindtag.
- On a drag or long press, the pressed `TouchButton`/`TouchWidget` has its
  pressed state cleared so its command does **not** fire at the end of a drag
  (without this, scrolling a list of buttons would fire every button touched).

## What's Planned (not yet built)

- Multi-touch gestures — Tkinter exposes single-pointer events only
- Swipe intensity / edge-swipe sections — replaced by threshold-based swipe
- Long press on Play/Pause to show the queue — deferred to Slice 3.2
- Live recolouring of themes — deferred to Slice 5.x