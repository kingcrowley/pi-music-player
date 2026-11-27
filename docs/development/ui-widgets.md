# UI Widgets — Reusable Components and Gestures

How screens use the reusable touch widgets and the gesture toolkit added in
Slice 3.1a. New screens (e.g. the Discover screen in Slice 3.2) should build on
these rather than wiring their own drag/scroll handling.

---

## ScrollList

`ui.widget.ScrollList` (a `tk.Frame`) renders a vertical list with drag
scrolling and momentum.

### Basic use

```python
from ui.widget import ScrollList, TouchButton

scroll = ScrollList(parent)
scroll.pack(fill="both", expand=True)

def render_row(parent, item):
    # Return any widget; it is packed into the list's inner frame.
    return TouchButton(parent, text=item["title"],
                       command=lambda: select(item))

scroll.set_items(items, render_row)
scroll.on_select(lambda item: print("tapped", item))
scroll.on_swipe(lambda direction, velocity: print("swiped", direction))
```

### API

| Method | Description |
|--------|-------------|
| `set_items(items, render_row)` | Clear and rebuild rows. `render_row(parent, item)` returns a widget. |
| `scroll_to_top()` | Scroll to the top of the list. |
| `on_select(callback)` | Callback receives the item whose row was **tapped** (not dragged). |
| `on_swipe(callback)` | Callback receives `(direction, velocity)` for horizontal swipes. |

### Behavior

- Drag scrolls 1:1 with the finger (`yview_scroll`, 1 unit = 1 px).
- On release, momentum continues at the release speed and decays by
  `GESTURE["friction"]` (0.90) each frame until below 0.5 px/frame or a list end.
- A new press cancels momentum.
- Mouse wheel: `<MouseWheel>` on Windows/macOS, `<Button-4>`/`<Button-5>` on X11.
- Rows are bound for gestures in `set_items` (X11's implicit grab delivers
  motion/release only to the pressed widget, so binding only the canvas would
  miss drags that start on a row).

---

## bind_gestures

`ui.gestures.bind_gestures(widget, recognizer, on_event, exclude=())` connects a
`GestureRecognizer` to a Tk widget and every descendant.

```python
from ui.gestures import GestureRecognizer, bind_gestures

recognizer = GestureRecognizer(width_fn=lambda: root.winfo_width())

def on_event(name, *args, source=None):
    if name == "swipe":
        direction, velocity = args
        ...

bind_gestures(content_frame, recognizer, on_event, exclude=(progress_bar,))
```

### The `exclude` rule

`exclude` lists widgets (and their descendants) that must keep their own press
handling. **Always exclude the `ProgressBar`** — it seeks on `<Button-1>` and
must not be interpreted as a swipe/drag. Exclude any widget that handles presses
itself and must not be overridden by gesture recognition.

### What the adapter does

- Binds `<ButtonPress-1>`, `<B1-Motion>`, `<ButtonRelease-1>` with `add="+"` on
  the widget and all descendants, so a drag that starts on a child is captured.
- Converts coordinates via `event.x_root` / `event.y_root`.
- Timestamps with `time.monotonic()` (not `event.time`, which wraps at 32 bits
  and is 0 for `event_generate`).
- Starts a long-press timer on press and cancels it on drag/release.
- On a `drag_move` or `long_press`, clears the pressed visual state of the
  widget under the press (`TouchButton`/`TouchWidget.set_pressed_state(False)`),
  so a drag that starts on a button scrolls the list and does **not** fire the
  button.
- Passes the pressed widget to `on_event` as the `source=` keyword, so callers
  can resolve which row was tapped/swiped.

---

## GestureRecognizer

`ui.gestures.GestureRecognizer` is pure Python (no Tk imports) and returns event
lists from `press`, `move`, `release` and `timeout`. See
[`docs/usage/touch-gestures.md`](../usage/touch-gestures.md) for the event
contract and thresholds.

---

## Adding a new screen with gestures

1. Build the screen's widgets in a container frame.
2. For scrolling lists, use `ScrollList`.
3. For swipe navigation, call `bind_gestures` on the screen's content frame,
   passing `exclude` for any widget that handles its own presses (the
   `ProgressBar` on Now Playing).
4. Route `swipe` events to a navigation callback. Keep a visible button for
   every action so gestures are never the only way to do something.